"""One-shot local process inventory. Never an agent controller or completeness claim."""
import argparse
from datetime import datetime, timezone
import json
import importlib.util
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import socket
import stat
import subprocess
import sys
import time
import unicodedata

AGENTS = frozenset(('pi', 'claude', 'codex', 'opencode', 'aider', 'gemini', 'copilot', 'crush', 'hermes', 'kimi', 'amp', 'goose', 'qwen', 'omp', 'openclaw'))
ALIASES = {'claude-code': 'claude', 'pi-coding-agent': 'pi', 'github-copilot': 'copilot'}
SCRIPT_PACKAGES = {'pi-coding-agent': 'pi', 'claude-code': 'claude', '@openai/codex': 'codex', '@github/copilot': 'copilot', 'gemini-cli': 'gemini'}
IDENTIFIER = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}\Z')
CONTAINER_ID = re.compile(r'[a-f0-9]{12,64}\Z')
LIMIT = 2 * 1024 * 1024


class Unavailable(Exception):
  pass


class Query:
  """Bound our own metadata queries, not other agents. Never include stderr/argv in errors."""
  def __init__(self, seconds=8):
    self.deadline = time.monotonic() + seconds

  def __call__(self, args, json_output=True):
    remaining = min(1.5, self.deadline - time.monotonic())
    if remaining <= 0:
      raise Unavailable('report query budget exhausted')
    if not shutil.which(args[0]):
      raise Unavailable('command not installed')
    env = dict(os.environ)
    for name in ('CONTAINER_HOST', 'CONTAINER_CONNECTION', 'DOCKER_HOST', 'DOCKER_CONTEXT', 'SSH_AUTH_SOCK', 'HERDR_MACHINE', 'HERDR_MACHINE_ID', 'HERDR_REMOTE', 'HERDR_SESSION'):
      env.pop(name, None)
    env['HERDR_ENV'] = '1'
    process = None
    try:
      process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env, start_new_session=True)
      data = bytearray()
      with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ)
        end = time.monotonic() + remaining
        while selector.get_map():
          left = end - time.monotonic()
          if left <= 0:
            raise Unavailable('metadata query timed out')
          for key, _ in selector.select(min(left, .1)):
            chunk = os.read(key.fd, 65536)
            if not chunk:
              selector.unregister(key.fileobj)
            else:
              data.extend(chunk)
              if len(data) > LIMIT:
                raise Unavailable('metadata response exceeded limit')
        try:
          code = process.wait(timeout=max(.01, end - time.monotonic()))
        except subprocess.TimeoutExpired:
          raise Unavailable('metadata query timed out') from None
      if code:
        raise Unavailable('metadata query failed')
      text = data.decode('utf-8')
      return json.loads(text) if json_output else text.strip()
    except (OSError, ValueError, UnicodeError):
      raise Unavailable('metadata unavailable or malformed') from None
    finally:
      if process is not None:
        if process.poll() is None:
          try:
            os.killpg(process.pid, signal.SIGKILL)
          except ProcessLookupError:
            pass
          process.wait()
        process.stdout.close()


def read(path, limit=8192):
  with path.open('rb') as stream:
    data = stream.read(limit + 1)
  if len(data) > limit:
    raise ValueError('oversized proc metadata')
  return data.decode('utf-8', errors='replace')


def canonical(value):
  return ALIASES.get(value, value) if isinstance(value, str) else None


class Proc:
  def __init__(self, root=Path('/proc'), uid=None):
    self.root = root
    self.uid = os.getuid() if uid is None else uid
    self.namespaces = self.namespace('self')
    try:
      self.boot_id = read(root/'sys/kernel/random/boot_id', 64).strip()
    except (OSError, ValueError):
      self.boot_id = None
    self.container_observer = Path('/run/.containerenv').exists() or Path('/.dockerenv').exists()

  def namespace(self, pid):
    try:
      return tuple(os.readlink(self.root/str(pid)/'ns'/name) for name in ('pid', 'mnt'))
    except OSError:
      return None

  def identity(self, pid):
    directory = self.root/str(pid)
    if directory.stat().st_uid != self.uid:
      raise PermissionError()
    # comm can contain spaces and parentheses. Fields after its final ')' start at state.
    fields = read(directory/'stat').rsplit(')', 1)[1].split()
    return {'pid': pid, 'ppid': int(fields[1]), 'start_ticks': int(fields[19])}

  def process(self, pid):
    before = self.identity(pid)
    directory = self.root/str(pid)
    try:
      exe = os.readlink(directory/'exe').removesuffix(' (deleted)')
    except OSError:
      exe = ''
    result = {**before, 'comm': read(directory/'comm', 256).strip(), 'exe': exe, 'namespaces': self.namespace(pid)}
    if before['start_ticks'] != self.identity(pid)['start_ticks']:
      raise ProcessLookupError()
    return result

  def recognize(self, process):
    binary = Path(process['exe']).name
    if binary in AGENTS:
      return binary, 'executable-name'
    # Only inspect argv[0] and an interpreter's first option/script token.
    # Never inspect later arguments, prompts, /proc/environ, or terminal contents.
    if binary in ('node', 'nodejs', 'bun') or re.fullmatch(r'python[0-9.]*', binary):
      try:
        with (self.root/str(process['pid'])/'cmdline').open('rb') as stream:
          def token():
            value = bytearray()
            for _ in range(4096):
              char = stream.read(1)
              if not char or char == b'\0':
                return value.decode('utf-8', errors='replace')
              value.extend(char)
            raise ValueError('oversized interpreter entrypoint')
          token()
          script = token()
        if script and not script.startswith('-'):
          for package, agent in SCRIPT_PACKAGES.items():
            if '/'+package+'/' in script:
              return agent, 'interpreter-entrypoint'
          if Path(script).name in ('aider', 'hermes', 'kimi', 'omp'):
            return Path(script).name, 'interpreter-entrypoint'
      except (OSError, ValueError):
        pass
    name = canonical(process['comm'])
    if name in AGENTS:
      return name, 'process-name-only'
    return None

  def scan(self):
    processes, issues = {}, {'unreadable': 0, 'restricted_details': 0, 'vanished': 0, 'limited': False}
    end = time.monotonic() + 2
    try:
      entries = list(self.root.iterdir())
    except OSError:
      return {}, {'state': 'unavailable', 'detail': 'procfs not readable'}
    for i, path in enumerate(p for p in entries if p.name.isascii() and p.name.isdigit()):
      if i >= 8192 or time.monotonic() > end:
        issues['limited'] = True
        break
      try:
        if path.stat().st_uid != self.uid:
          continue
        value = self.process(int(path.name))
        if not value['exe'] or not value['namespaces']:
          issues['restricted_details'] += 1
        match = self.recognize(value)
        if match:
          value['agent'], value['identification'] = match
        processes[value['pid']] = value
      except (FileNotFoundError, ProcessLookupError):
        issues['vanished'] += 1
      except (OSError, ValueError, IndexError):
        issues['unreadable'] += 1
    state = 'partial' if issues['unreadable'] or issues['restricted_details'] or issues['limited'] or not self.namespaces else 'ok'
    return processes, {'state': state, 'scope': 'current UID and visible procfs', 'visible_processes': len(processes), **issues}

  def cwd(self, pid):
    try:
      return os.readlink(self.root/str(pid)/'cwd')[:4096]
    except OSError:
      return None


def container_snapshot(query, proc):
  rows = query(['podman', '--remote=false', 'ps', '--format=json'])
  if not isinstance(rows, list):
    raise Unavailable('unsupported container response')
  ids = [row.get('Id') for row in rows if isinstance(row, dict)]
  if any(not isinstance(cid, str) or not CONTAINER_ID.fullmatch(cid) for cid in ids):
    raise Unavailable('invalid container identifiers')
  if len(ids) > 64:
    raise Unavailable('too many containers for bounded snapshot')
  if len(set(ids)) != len(ids):
    raise Unavailable('ambiguous container snapshot')
  if not ids:
    return []
  keys = ('org.omarchy.managed', 'org.omarchy.agent', 'org.omarchy.workspace.id')
  template = '\t'.join(['{{json .ID}}', '{{json .Name}}', '{{json .State.Pid}}'] + ['{{json (index .Config.Labels "'+key+'")}}' for key in keys])
  output = query(['podman', '--remote=false', 'inspect', '--format', template, *ids], json_output=False)
  result = []
  for line in output.splitlines():
    try:
      cid, name, pid, managed, agent, workspace = [json.loads(part) for part in line.split('\t')]
    except (ValueError, TypeError):
      raise Unavailable('unsupported container details') from None
    if cid not in ids or not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0 or not isinstance(name, str):
      raise Unavailable('container changed during query')
    result.append({'id': cid, 'name': name[:256], 'init_pid': pid, 'namespaces': proc.namespace(pid), 'kind': 'agent' if managed == 'agent' else 'workspace' if workspace else 'other', 'declared_agent': canonical(agent) if canonical(agent) in AGENTS else None, 'workspace_id': workspace if isinstance(workspace, str) else None})
  if {r['id'] for r in result} != set(ids):
    raise Unavailable('incomplete container snapshot')
  return result


def herdr_snapshot(query):
  listing = query(['herdr', 'session', 'list', '--json'])
  sessions = listing.get('sessions') if isinstance(listing, dict) else None
  if not isinstance(sessions, list) or len(sessions) > 16:
    raise Unavailable('unsupported local session response')
  observations, errors = [], 0
  for session in sessions:
    if not isinstance(session, dict) or not isinstance(session.get('running'), bool):
      errors += 1
      continue
    if not session['running']:
      continue
    name, path = session.get('name'), session.get('socket_path')
    if not isinstance(name, str) or not IDENTIFIER.fullmatch(name) or not isinstance(path, str):
      errors += 1
      continue
    try:
      # Do not ask Herdr to create, attach, or connect to a remote session.
      if not stat.S_ISSOCK(Path(path).stat().st_mode):
        raise Unavailable('local session socket unavailable')
      prefix = ['herdr', '--session', name]
      response = query([*prefix, 'agent', 'list'])
      agents = response['result']['agents']
      if not isinstance(agents, list) or len(agents) > 64:
        raise Unavailable('unsupported agent response')
      for row in agents:
        agent = canonical(row.get('agent')) if isinstance(row, dict) else None
        if not isinstance(agent, str) or not IDENTIFIER.fullmatch(agent):
          errors += 1
          continue
        pane = row.get('pane_id')
        if not isinstance(pane, str) or not IDENTIFIER.fullmatch(pane):
          errors += 1
          continue
        remote = row.get('is_remote') is True or any(row.get(key) for key in ('machine_id', 'remote_machine_id', 'remote_target', 'machine'))
        activity = row.get('agent_status')
        activity = activity if activity in ('working', 'idle', 'waiting', 'unknown', 'attention', 'needs_input', 'needs-input', 'exited') else 'unknown'
        observation = {'agent': agent, 'session': name, 'pane': pane, 'activity': activity, 'remote': bool(remote), 'pids': []}
        if not remote:
          try:
            info = query([*prefix, 'pane', 'process-info', '--pane', pane])['result']['process_info']
            # Drop argv/cmdline, titles, agent-session paths, and all other fields.
            foreground = info.get('foreground_processes', [])
            if not isinstance(foreground, list) or len(foreground) > 128:
              raise Unavailable('unsupported foreground process metadata')
            candidates = [info.get('foreground_process_group_id')]
            candidates += [r.get('pid') for r in foreground if isinstance(r, dict)]
            observation['pids'] = sorted({pid for pid in candidates if isinstance(pid, int) and not isinstance(pid, bool) and pid > 0})[:32]
          except (Unavailable, KeyError, TypeError, AttributeError):
            errors += 1
        observations.append(observation)
    except (Unavailable, OSError, KeyError, TypeError, AttributeError):
      errors += 1
  return observations, {'state': 'partial' if errors else 'ok', 'errors': errors, 'observations': len(observations)}


def workspace_names():
  # Reuse the backend's read-only registry API; do not invoke its engine snapshot
  # (which could honor a user's remote Podman configuration).
  path = Path(os.environ['OMARCHY_PATH'])/'default/workspaces/manager.py'
  spec = importlib.util.spec_from_file_location('omarchy_status_workspaces', path)
  backend = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(backend)
  rows = backend.list_workspaces(backend.state_root(create=False), runtime=False)
  if len(rows) > 512:
    raise Unavailable('too many registered workspaces')
  return {row['id']: row['name'] for row in rows}


def build_report(proc, query, use_herdr=True, use_podman=True, workspace_reader=None):
  processes, proc_coverage = proc.scan()
  coverage = {'processes': proc_coverage, 'remote': {'state': 'not-queried'}}
  containers, observations = [], []
  if use_podman:
    try:
      containers = container_snapshot(query, proc)
      coverage['podman'] = {'state': 'partial' if any(not c['namespaces'] for c in containers) else 'ok', 'running_containers': len(containers)}
    except Unavailable as error:
      coverage['podman'] = {'state': 'unavailable', 'detail': str(error)}
  else:
    coverage['podman'] = {'state': 'disabled'}
  workspaces = {}
  if any(c['workspace_id'] for c in containers):
    try:
      workspaces = (workspace_reader or workspace_names)()
      coverage['workspaces'] = {'state': 'ok'}
    except (Unavailable, OSError, RuntimeError, ValueError, KeyError, TypeError):
      coverage['workspaces'] = {'state': 'unavailable'}
  else:
    coverage['workspaces'] = {'state': 'not-needed'}
  if use_herdr:
    try:
      observations, coverage['herdr'] = herdr_snapshot(query)
    except Unavailable as error:
      coverage['herdr'] = {'state': 'unavailable', 'detail': str(error)}
  else:
    coverage['herdr'] = {'state': 'disabled'}
  mode = 'unknown'
  try:
    value = query(['omarchy-agent-mode'], json_output=False)
    if value not in ('host', 'container'):
      raise Unavailable('invalid default')
    mode = value
    coverage['default'] = {'state': 'ok'}
  except Unavailable:
    coverage['default'] = {'state': 'unavailable'}

  records = {}
  for pid, process in processes.items():
    if 'agent' in process:
      records[pid] = {**process, 'herdr': []}
  unverified = []
  for observation in observations:
    matches = []
    if not observation['remote']:
      for pid in observation['pids']:
        process = records.get(pid)
        if process and process['agent'] == observation['agent']:
          try:
            if proc.identity(pid)['start_ticks'] == process['start_ticks']:
              matches.append(process)
          except (OSError, ValueError, IndexError):
            pass
    evidence = {key: observation[key] for key in ('session', 'pane', 'activity')}
    if matches:
      for process in matches:
        process['herdr'].append(evidence)
    else:
      unverified.append({**evidence, 'agent': observation['agent'], 'boundary': 'remote-unverified' if observation['remote'] else 'unverified', 'reason': 'no matching live recognized process; not counted as an additional process'})

  identified, candidates, vanished = [], [], 0
  for pid, process in records.items():
    try:
      live = proc.identity(pid)['start_ticks'] == process['start_ticks']
    except (OSError, ValueError, IndexError):
      live = False
    if not live:
      vanished += 1
      for evidence in process['herdr']:
        unverified.append({**evidence, 'agent': process['agent'], 'boundary': 'unverified', 'reason': 'process disappeared or PID was reused during collection'})
      continue
    ns = process['namespaces']
    matches = [c for c in containers if ns and c['namespaces'] == ns]
    container = matches[0] if len(matches) == 1 else None
    # A host-PID container is not a match for every host process: mount and PID
    # namespaces must both match. Unknown boundaries never become 'safe'.
    if ns and ns == proc.namespaces and not proc.container_observer:
      boundary, container = 'host', None
    elif container:
      boundary = 'container'
    elif ns and ns == proc.namespaces:
      boundary = 'observer'
    else:
      boundary = 'unknown'
    associated = '/extensions/' in process['exe'] and process['agent'] == 'codex'
    sources = ['procfs'] + (['herdr'] if process['herdr'] else []) + (['podman'] if container else [])
    activity = {'state': 'process-observed', 'source': 'procfs'}
    states = {entry['activity'] for entry in process['herdr']}
    if len(states) == 1:
      activity = {'state': next(iter(states)), 'source': 'herdr'}
    elif len(states) > 1:
      activity = {'state': 'conflicting-reports', 'source': 'herdr'}
    record = {'identity': {'boot_id': proc.boot_id, 'pid': pid, 'start_ticks': process['start_ticks']}, 'agent': process['agent'], 'boundary': boundary, 'role': 'extension-associated process' if associated else 'agent process', 'identification': process['identification'], 'corroborated': bool(process['herdr']), 'activity': activity, 'cwd': proc.cwd(pid), 'executable': process['exe'] or None, 'sources': sources, 'herdr': process['herdr'], 'container': None}
    if container:
      record['container'] = {key: container[key] for key in ('id', 'name', 'kind', 'workspace_id')}
      record['container']['workspace_name'] = workspaces.get(container['workspace_id'])
    target = candidates if process['identification'] == 'process-name-only' and not process['herdr'] else identified
    target.append(record)
  order = {'host': 0, 'unknown': 1, 'observer': 1, 'container': 2}
  for rows in (identified, candidates):
    rows.sort(key=lambda r: (order[r['boundary']], r['agent'], r['identity']['pid']))
  return {'schema_version': 1, 'observed_at': datetime.now(timezone.utc).isoformat(), 'hostname': socket.gethostname(), 'scope': 'current UID; observer-visible procfs; local rootless Podman and running local Herdr sessions', 'observer': {'uid': proc.uid, 'namespaces': proc.namespaces, 'container_marker': proc.container_observer}, 'launch_default': mode, 'processes': identified, 'candidates': candidates, 'unverified_observations': unverified, 'runtimes': [{key: c[key] for key in ('id', 'name', 'kind', 'declared_agent', 'workspace_id')} for c in containers], 'coverage': coverage, 'vanished_identifications': vanished, 'notes': ['Process presence is not proof of active work. Herdr activity is reported, not independently verified.', 'Host means the observer PID and mount namespaces, not a proof of unrestricted authority. Run this command on the host.', 'Container boundaries do not prove isolation or absence of writable host mounts.', 'This is not a complete inventory. Remote hosts, other users, hidden agents, and unsupported entrypoints are not inspected.']}


def display(value, limit=140):
  value = str(value) if value is not None else '-'
  escaped = ''.join(f'\\u{ord(c):04x}' if unicodedata.category(c).startswith('C') else c for c in value)
  return escaped if len(escaped) <= limit else escaped[:limit-3]+'...'


def print_report(report):
  print('Identified local agent processes (host first)')
  print(f"{'BOUNDARY':<11} {'AGENT':<12} {'ACTIVITY':<23} {'PID':<9} LOCATION / EVIDENCE")
  for section, rows in (('', report['processes']), ('Possible candidates (not counted as identified)', report['candidates'])):
    if section and rows:
      print('\n'+section)
    for row in rows:
      activity = row['activity']['state'] + (' [Herdr]' if row['activity']['source'] == 'herdr' else '')
      container = row['container']
      location = 'workspace:'+container['workspace_name'] if container and container.get('workspace_name') else container['name'] if container else row['cwd']
      panes = ', '.join(f"{e['session']}/{e['pane']}" for e in row['herdr'])
      extra = ' · '+panes if panes else ''
      if row['role'] == 'extension-associated process':
        extra += ' · extension process; work unverified'
      print(f"{row['boundary'].upper():<11} {display(row['agent']):<12} {display(activity):<23} {row['identity']['pid']:<9} {display(location)}{display(extra, 180)}")
  if not report['processes']:
    print('No identified agent processes within the inspected scope.')
  if report['unverified_observations']:
    print('\nUnverified Herdr observations (not additional process counts)')
    for row in report['unverified_observations']:
      print(f"  {row['agent']} · {display(row['session'])}/{display(row['pane'])} · {row['activity']} · {row['boundary']}")
  if report['coverage']['podman']['state'] in ('ok', 'partial'):
    runtimes = report['runtimes']
    kinds = {kind: sum(r['kind'] == kind for r in runtimes) for kind in ('agent', 'workspace', 'other')}
    print(f"\nRunning local containers: {len(runtimes)} (managed harnesses: {kinds['agent']}; editor workspaces: {kinds['workspace']}; other: {kinds['other']})")
  print('\nLaunch default: '+report['launch_default'].capitalize()+' (future launches only)')
  print('Coverage: '+', '.join(f"{name}={value['state']}" for name, value in report['coverage'].items()))
  proc = report['coverage']['processes']
  if proc['state'] == 'partial':
    print(f"  Procfs gaps: {proc.get('unreadable', 0)} unreadable, {proc.get('restricted_details', 0)} restricted details; scan capped: {proc.get('limited', False)}")
  for note in report['notes']:
    print('Note: '+note)


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--json', action='store_true', help='print versioned structured metadata')
  parser.add_argument('--no-herdr', action='store_true', help='skip local Herdr queries')
  parser.add_argument('--no-podman', action='store_true', help='skip rootless Podman queries')
  args = parser.parse_args()
  if os.getuid() == 0:
    parser.error('Run as the desktop user, not under sudo; rootful engines and other users are outside this report.')
  report = build_report(Proc(), Query(), not args.no_herdr, not args.no_podman)
  if args.json:
    print(json.dumps(report, ensure_ascii=True, indent=2))
  else:
    print_report(report)


if __name__ == '__main__':
  main()
