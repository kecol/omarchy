"""Local harness diagnostics and explicit exact-instance closure. No abandonment guesses."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

spec = importlib.util.spec_from_file_location('session_status', Path(__file__).with_name('status.py'))
status = importlib.util.module_from_spec(spec)
spec.loader.exec_module(status)
UUID = re.compile(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\Z')
SELECTOR = re.compile(r'[a-f0-9][a-f0-9-]{7,35}\Z')
TOKENS = {b'login': 'explicit-login-command', b'--approve-for-me': 'interactive-launch-option',
  b'app-server': 'app-server-command', b'exec': 'exec-command'}


def entry_kind(path):
  # Discard argv[0]. Match only a known second token, stopping as soon as its
  # prefix is unknown. Never consume a whole unknown token or later prompt.
  with path.open('rb', buffering=0) as stream:
    for _ in range(4096):
      byte = stream.read(1)
      if byte == b'\0':
        break
      if not byte:
        return 'unknown'
    else:
      return 'unavailable'
    prefix = b''
    for _ in range(32):
      byte = stream.read(1)
      if byte == b'\0':
        return TOKENS.get(prefix, 'unknown')
      if not byte:
        return 'unknown'
      prefix += byte
      if not any(token.startswith(prefix) for token in TOKENS):
        return 'unknown'
  return 'unknown'


def callback_listener(root):
  """Owned TCP listener on Codex's conventional callback port, not auth state."""
  inodes, partial = set(), False
  deadline = time.monotonic() + .3
  with os.scandir(root/'fd') as entries:
    for index, fd in enumerate(entries):
      if index >= 512 or time.monotonic() > deadline:
        partial = True
        break
      try:
        link = os.readlink(fd.path)
        if link.startswith('socket:['):
          inodes.add(link[8:-1])
      except OSError:
        partial = True
  found = False
  for name in ('tcp', 'tcp6'):
    with (root/'net'/name).open() as stream:
      next(stream, None)
      for index, line in enumerate(stream):
        if index >= 8192 or len(line) > 4096 or time.monotonic() > deadline:
          partial = True
          break
        fields = line.split()
        if len(fields) < 10:
          partial = True
          continue
        if fields[3] == '0A' and fields[1].split(':')[-1] == '05AF' and fields[9] in inodes:
          found = True
  return 'present' if found else 'partial' if partial else 'absent'


def login_evidence(proc, container):
  result = {'entry': 'unsupported', 'callback_listener': 'not-queried'}
  pid = container['init_pid']
  if container['declared_agent'] != 'codex':
    return result
  root = proc.root/str(pid)
  try:
    if Path(os.readlink(root/'exe')).name != 'codex':
      return {**result, 'entry': 'unknown'}
    result['entry'] = entry_kind(root/'cmdline')
    result['callback_listener'] = callback_listener(root)
  except (OSError, ValueError, IndexError):
    result['callback_listener'] = 'unavailable'
  return result


def fingerprint(row):
  return (row['instance'], row['agent'], row['container_id'], row['container_name'], row['pid'],
    row['identity']['boot_id'], row['identity']['start_ticks'], tuple(row['namespaces']))


def fresh_container(proc, container):
  try:
    return (container['init_start'] is not None
      and proc.identity(container['init_pid'])['start_ticks'] == container['init_start']
      and container['namespaces'] and container['namespaces'] != proc.namespaces
      and proc.namespace(container['init_pid']) == container['namespaces'])
  except (OSError, ValueError, IndexError):
    return False


def inventory(query, proc, diagnostics=True):
  if os.getuid() == 0 or proc.container_observer:
    raise status.Unavailable('Run this command on the host as your desktop user')
  if query(['podman', '--remote=false', 'info', '--format', '{{.Host.Security.Rootless}}'], json_output=False).strip() != 'true':
    raise status.Unavailable('Local rootless Podman is required')
  containers = [c for c in status.container_snapshot(query, proc) if c['kind'] == 'agent']
  if not containers:
    return []
  template = '\t'.join(('{{json .ID}}', '{{json (index .Config.Labels "org.omarchy.instance")}}',
    '{{json .State.StartedAt}}', '{{json .State.Running}}', '{{json (index .Config.Labels "org.omarchy.agent")}}'))
  data = query(['podman', '--remote=false', 'inspect', '--format', template,
    *[c['id'] for c in containers]], json_output=False)
  details = {}
  for line in data.splitlines():
    try:
      cid, instance, started, running, agent = [json.loads(field) for field in line.split('\t')]
    except (ValueError, TypeError):
      raise status.Unavailable('Unsupported instance metadata') from None
    if cid in details or running is not True or not isinstance(instance, str) or not UUID.fullmatch(instance):
      raise status.Unavailable('Ambiguous or changed instance metadata')
    if not isinstance(agent, str) or not re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,95}', agent):
      raise status.Unavailable('Invalid declared harness agent')
    details[cid] = (instance, started, agent)
  if set(details) != {c['id'] for c in containers}:
    raise status.Unavailable('Incomplete instance metadata')
  result = []
  evidence_deadline = time.monotonic() + 4
  for container in containers:
    instance, started, agent = details[container['id']]
    expected = 'omarchy-agent-'+agent+'-'+instance.replace('-', '')[:12]
    if container['name'] != expected:
      raise status.Unavailable('Instance name/label disagreement')
    # Validate current-user ownership/start/ns before reading even limited argv
    # or fd metadata, then recheck after those observations.
    if not fresh_container(proc, container):
      raise status.Unavailable('Instance identity/ownership or container boundary is not verified')
    evidence = {'entry': 'not-queried', 'callback_listener': 'not-queried'}
    if diagnostics:
      evidence = (login_evidence(proc, container) if time.monotonic() < evidence_deadline else
        {'entry': 'unavailable', 'callback_listener': 'unavailable'})
    if not fresh_container(proc, container):
      raise status.Unavailable('Instance process disappeared or changed identity during observation')
    result.append({'instance': instance, 'agent': agent, 'container_id': container['id'],
      'container_name': container['name'], 'pid': container['init_pid'],
      'identity': {'boot_id': proc.boot_id, 'start_ticks': container['init_start']},
      'namespaces': list(container['namespaces']), 'started_at': started,
      'project': container['project'], 'login_evidence': evidence, 'shared_project_instances': [], 'findings': []})
  for row in result:
    if row['project']['state'] == 'matched':
      peers = [r['instance'] for r in result if r['agent'] == row['agent']
        and r['project']['state'] == 'matched' and r['project']['host_path'] == row['project']['host_path']]
      if len(peers) > 1:
        row['shared_project_instances'] = peers
        row['findings'].append('shared-project-launches')
    if row['login_evidence']['entry'] == 'explicit-login-command':
      row['findings'].append('login-command-present-not-proof-of-stall')
    if row['login_evidence']['callback_listener'] == 'present':
      row['findings'].append('possible-browser-login-callback-not-proof-of-abandonment')
  return result


def select(rows, selector):
  if not SELECTOR.fullmatch(selector):
    raise status.Unavailable('Use an exact instance UUID or unique UUID prefix of at least eight characters, not an agent name or PID')
  matches = [row for row in rows if row['instance'].startswith(selector)]
  if len(matches) != 1:
    raise status.Unavailable('Instance selector is absent or ambiguous; run omarchy agent diagnose again')
  return matches[0]


def close_instance(before, query_factory, proc, force, action):
  # This function is called only after explicit user confirmation or --yes.
  # Inspect again after the prompt, not using an old pre-confirmation snapshot.
  rows = inventory(query_factory(), proc, diagnostics=False)
  current = select(rows, before['instance'])
  if fingerprint(current) != fingerprint(before):
    raise status.Unavailable('Instance identity changed after selection; nothing was signalled')
  if (proc.identity(current['pid'])['start_ticks'] != current['identity']['start_ticks']
      or proc.namespace(current['pid']) != tuple(current['namespaces'])):
    raise status.Unavailable('Process identity changed immediately before closure; no signal sent')
  cid = current['container_id']
  if not re.fullmatch(r'[a-f0-9]{64}', cid):
    raise status.Unavailable('A full immutable container ID is required')
  command = (['podman', '--remote=false', 'kill', '--signal=KILL', cid] if force else
    ['podman', '--remote=false', 'stop', '--time=10', cid])
  # Only the immutable container ID is signalled. Never remove a volume, image,
  # workspace, editor container, or host PID; never infer "safe to close".
  action(command)
  return current


def render(rows):
  print('Local Omarchy harness instances (not a completeness or abandonment claim)')
  for row in rows:
    print('\nInstance: '+row['instance'])
    print('  '+str(row['agent'])+' · PID '+str(row['pid'])+' · '+status.display(row['container_name']))
    print('  Started: '+status.display(row['started_at']))
    project = row['project']
    print('  Project: '+status.display(project['host_path'])+' · '+project['access'])
    print('  Container path: '+status.display(project['container_path'])+' · key '+status.display(project['project_id']))
    print('  Entry evidence: '+row['login_evidence']['entry'])
    print('  Owned port-1455 listener: '+row['login_evidence']['callback_listener'])
    if row['findings']:
      print('  Findings: '+', '.join(row['findings']))
    if row['shared_project_instances']:
      print('  Same-agent launches sharing these files: '+str(len(row['shared_project_instances'])))
  if not rows:
    print('No matching managed harness containers were returned by the checked local engine.')
  print('\nA running process, age, shared project, login command, or callback listener does not prove a stalled login or abandoned work.')
  print('No prompts, terminal buffers, credential files, process environments, or histories were read.')
  if rows:
    print('\n'+status.SESSION_HINT)


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  sub = parser.add_subparsers(dest='operation', required=True)
  diagnose = sub.add_parser('diagnose')
  diagnose.add_argument('--json', action='store_true')
  close = sub.add_parser('close')
  close.add_argument('instance')
  close.add_argument('--force', action='store_true', help='Send SIGKILL rather than graceful stop; may discard work')
  close.add_argument('--yes', action='store_true', help='Explicitly authorize closure without a terminal prompt')
  close.add_argument('--check', action='store_true', help='Validate selection without signalling or prompting')
  args = parser.parse_args()
  proc = status.Proc()
  rows = inventory(status.Query(), proc, diagnostics=args.operation == 'diagnose')
  if args.operation == 'diagnose':
    if args.json:
      print(json.dumps({'schema_version': 1, 'instances': rows,
        'notes': ['Observations only; abandonment and authentication state are not established.',
          'A shared-project finding means concurrent launches, not duplicate counting or independent clones.']}))
    else:
      render(rows)
    return
  before = select(rows, args.instance)
  if args.check:
    print('Selected '+before['instance']+' · PID '+str(before['pid'])+'; no signal sent.')
    return
  print('Selected '+before['instance']+' · '+str(before['agent'])+' · PID '+str(before['pid']), file=sys.stderr)
  print('Container: '+status.display(before['container_name'])+' · project '+status.display(before['project']['host_path']), file=sys.stderr)
  print('Closing may discard work. Shared home volumes and project files will not be deleted.', file=sys.stderr)
  if not args.yes:
    if not sys.stdin.isatty() or not sys.stderr.isatty():
      raise status.Unavailable('Closure needs terminal confirmation or explicit --yes; no signal sent')
    prompt = 'Force-kill this exact instance?' if args.force else 'Stop this exact instance (10-second grace, then kill)?'
    if subprocess.run(['gum', 'confirm', '--default=false', prompt]).returncode:
      raise SystemExit(130)
  def action(command):
    completed = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
      stderr=subprocess.DEVNULL, timeout=20)
    if completed.returncode:
      raise status.Unavailable('Engine did not confirm closure; no automatic retry or broader signal was attempted')
  current = close_instance(before, status.Query, proc, args.force, action)
  print('Force-kill requested for ' if args.force else 'Stop requested for ', end='')
  print(current['instance']+'. Shared volumes were not removed.')


if __name__ == '__main__':
  try:
    main()
  except status.Unavailable as error:
    sys.exit(str(error))
  except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
    # Do not echo adapter stderr, raw metadata, or argv in errors.
    sys.exit('Agent session operation unavailable or identity/selection not verified. No automatic cleanup or retry. Use omarchy agent diagnose to refresh.')
