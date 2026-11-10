"""Foreground, confirmed stop of one observed local Omarchy container. No force/removal."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

spec = importlib.util.spec_from_file_location('stop_sessions', Path(__file__).with_name('sessions.py'))
sessions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sessions)
status = sessions.status
Unavailable = status.Unavailable
CID = re.compile(r'[a-f0-9]{64}\Z')
BOOT = re.compile(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\Z')


def validate_target(cid, boot, pid, start):
  if not isinstance(cid, str) or not CID.fullmatch(cid) or not isinstance(boot, str) or not BOOT.fullmatch(boot):
    raise Unavailable('An exact container ID and boot identity are required')
  if any(not isinstance(n, int) or isinstance(n, bool) or n < 1 or n > 9007199254740991 for n in (pid, start)):
    raise Unavailable('A valid observed process identity is required')


def observe(target, proc, query):
  cid, boot, pid, start = target
  validate_target(*target)
  if os.getuid() == 0 or proc.container_observer or not proc.namespaces or proc.boot_id != boot:
    raise Unavailable('Use the original host desktop user and boot; refresh the widget')
  if query(['podman', '--remote=false', 'info', '--format', '{{.Host.Security.Rootless}}'], json_output=False) != 'true':
    raise Unavailable('Local rootless Podman is required')
  containers = status.container_snapshot(query, proc)
  matches = [c for c in containers if c['id'] == cid]
  if len(matches) != 1:
    raise Unavailable('Selected container is absent or ambiguous; refresh the widget')
  container = matches[0]
  if sum(c['namespaces'] == container['namespaces'] for c in containers) != 1:
    raise Unavailable('Container namespace association is ambiguous')
  process = proc.process(pid)
  recognized = proc.recognize(process)
  if (process['start_ticks'] != start or not recognized or recognized[1] == 'process-name-only'
    or process['namespaces'] != container['namespaces'] or not sessions.fresh_container(proc, container)):
    raise Unavailable('Observed agent/container identity changed; nothing stopped')
  template = '\t'.join(('{{json .ID}}', '{{json .State.Running}}', '{{json .State.StartedAt}}',
    '{{json .Config.StopSignal}}', '{{json (index .Config.Labels "org.omarchy.instance")}}'))
  data = query(['podman', '--remote=false', 'inspect', '--format', template, cid], json_output=False)
  try:
    inspected, running, started, stop_signal, instance = [json.loads(v) for v in data.split('\t')]
  except (ValueError, TypeError):
    raise Unavailable('Unverified container stop metadata') from None
  if inspected != cid or running is not True or not isinstance(started, str) or not started:
    raise Unavailable('Container is not the selected running instance')
  if stop_signal not in (None, '', '15', 15, 'TERM', 'SIGTERM'):
    raise Unavailable('Container does not have a verified graceful TERM stop policy')
  workspace = None
  if container['kind'] == 'workspace':
    wid = container['workspace_id']
    try:
      workspace = status.workspace_snapshot().get(wid)
    except (OSError, RuntimeError, ValueError, KeyError, TypeError):
      raise Unavailable('Workspace registry is unavailable or unsafe') from None
    if not workspace or container['name'] != 'omarchy-workspace-'+wid:
      raise Unavailable('Workspace registry/container identity disagreement')
    owner = ('workspace', wid, workspace['name'], workspace['mode'], workspace['directory'])
  elif container['kind'] == 'agent':
    agent = container['declared_agent']
    if not agent or not isinstance(instance, str) or not sessions.UUID.fullmatch(instance):
      raise Unavailable('Managed harness identity is unavailable')
    if container['name'] != 'omarchy-agent-'+agent+'-'+instance.replace('-', '')[:12]:
      raise Unavailable('Harness name/instance identity disagreement')
    owner = ('agent', instance, agent)
  else:
    raise Unavailable('Only registered workspaces and managed agent containers can be stopped')
  after = proc.process(pid)
  if after != process or not sessions.fresh_container(proc, container):
    raise Unavailable('Process identity changed during selection')
  return {'cid': cid, 'boot': boot, 'pid': pid, 'start': start, 'process': process, 'recognition': recognized,
    'init_pid': container['init_pid'], 'init_start': container['init_start'],
    'namespaces': container['namespaces'], 'started': started, 'stop_signal': stop_signal,
    'name': container['name'], 'owner': owner}


def request_stop(target, proc, query_factory, confirm, action, notify, clock=time.monotonic):
  before = observe(target, proc, query_factory())
  deadline = clock() + 120
  if confirm(before) is not True:
    return 'cancelled'
  if clock() >= deadline:
    raise Unavailable('Confirmation expired; refresh and select again')
  current = observe(target, proc, query_factory())
  if current != before:
    raise Unavailable('Container changed during confirmation; nothing stopped')
  if clock() >= deadline:
    raise Unavailable('Confirmation expired during revalidation; nothing stopped')
  # The immutable ID, never a name/PID, is the action target. -1 explicitly
  # prevents Podman's default timeout-to-KILL. An ignored TERM can keep the
  # foreground command pending; never retry, remove, restart or escalate.
  try:
    action(['podman', '--remote=false', 'stop', '--time=-1', current['cid']])
    remaining = query_factory()(['podman', '--remote=false', 'ps', '--no-trunc', '--filter', 'id='+current['cid'], '--format', '{{json .ID}}'], json_output=False)
    if remaining.strip():
      raise Unavailable('Stop outcome is not confirmed; no force or retry attempted')
  finally:
    # Refresh is observation only. Its failure cannot rewrite the stop outcome.
    try:
      notify()
    except (OSError, subprocess.SubprocessError):
      print('Widget refresh unavailable; reopen its panel to check status.', file=sys.stderr)
  return 'stopped'


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('container_id')
  parser.add_argument('boot_id')
  parser.add_argument('pid', type=int)
  parser.add_argument('start_ticks', type=int)
  args = parser.parse_args()
  target = (args.container_id, args.boot_id, args.pid, args.start_ticks)
  validate_target(*target)
  if not all(s.isatty() for s in (sys.stdin, sys.stdout, sys.stderr)) or os.tcgetpgrp(sys.stdin.fileno()) != os.getpgrp():
    raise Unavailable('Foreground terminal confirmation is required; no stop requested')
  def confirm(row):
    print('Container: '+status.display(row['name']))
    print('Exact ID: '+row['cid'])
    print(('Workspace: ' if row['owner'][0] == 'workspace' else 'Harness: ')+status.display(row['owner'][2]))
    print('All processes inside will stop. Unsaved work may be lost. No file or volume deletion is requested.')
    print('Graceful TERM only: no automatic force-kill. If it ignores TERM, this terminal can remain waiting.', flush=True)
    return subprocess.run(['gum', 'confirm', '--default=false', 'Stop this exact container?']).returncode == 0
  env = dict(os.environ)
  for key in ('CONTAINER_HOST', 'CONTAINER_CONNECTION', 'DOCKER_HOST', 'DOCKER_CONTEXT', 'SSH_AUTH_SOCK'):
    env.pop(key, None)
  def action(command):
    if subprocess.run(command, env=env, stdin=subprocess.DEVNULL, check=False).returncode:
      raise Unavailable('Stop was not confirmed; no automatic retry or force attempted')
  def notify():
    if subprocess.run(['omarchy-shell', '-q', 'omarchy.agent-overview', 'refresh'], check=False).returncode:
      print('Widget refresh unavailable; reopen its panel to check status.', file=sys.stderr)
  result = request_stop(target, status.Proc(), status.Query, confirm, action, notify)
  print('Cancelled; no stop requested.' if result == 'cancelled' else 'Container is no longer running. No file or volume deletion was requested.')
  return 0


if __name__ == '__main__':
  try:
    sys.exit(main())
  except KeyboardInterrupt:
    sys.exit('Interrupted; stop outcome may be unconfirmed. Check status; no retry or force attempted.')
  except (Unavailable, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
    sys.exit(str(error) if isinstance(error, Unavailable) else 'Container stop unavailable or unconfirmed; no automatic retry, force or removal attempted.')
