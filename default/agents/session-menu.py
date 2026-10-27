"""Explicit user terminal access to existing harnesses; never collect their output."""
import argparse
import importlib.util
from pathlib import Path
import re
import subprocess
import sys
import json
import os

spec = importlib.util.spec_from_file_location('harness_sessions', Path(__file__).with_name('sessions.py'))
sessions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sessions)
Unavailable = sessions.status.Unavailable


def terminal_required():
  if not all(stream.isatty() for stream in (sys.stdin, sys.stdout, sys.stderr)):
    raise Unavailable('Run this command in an interactive host terminal; no attachment was attempted')
  try:
    foreground = os.tcgetpgrp(sys.stdin.fileno()) == os.getpgrp()
  except OSError:
    foreground = False
  if not foreground:
    raise Unavailable('A foreground controlling terminal is required for reliable detach keys; no attachment was attempted')


def screen():
  # Clear the visible menu area, not terminal scrollback. No child process.
  if sys.stdout.isatty():
    print('\033[H\033[2J', end='', flush=True)


def details(row):
  print('\nInstance: '+row['instance'])
  print('Agent: '+row['agent']+' · PID '+str(row['pid']))
  print('Container: '+sessions.status.display(row['container_name']))
  print('Started: '+sessions.status.display(row['started_at']))
  for label, key in (('Project', 'host_path'), ('Internal path', 'container_path'), ('Project key', 'project_id')):
    print(label+': '+sessions.status.display(row['project'][key]))
  print('Observed mount access: '+row['project']['access'])


def verify_attach(before, proc):
  query = sessions.status.Query()
  current = sessions.select(sessions.inventory(query, proc, diagnostics=False), before['instance'])
  if sessions.fingerprint(current) != sessions.fingerprint(before):
    raise Unavailable('Selected instance changed; refresh before attaching')
  cid = current['container_id']
  if not re.fullmatch(r'[a-f0-9]{64}', cid):
    raise Unavailable('A full immutable container ID is required')
  template = '\t'.join(('{{json .State.Pid}}', '{{json .State.Running}}',
    '{{json .Config.Tty}}', '{{json .Config.OpenStdin}}'))
  data = query(['podman', '--remote=false', 'inspect', '--format', template, cid], json_output=False)
  try:
    pid, running, tty, stdin = [json.loads(field) for field in data.strip().split('\t')]
  except (ValueError, TypeError):
    raise Unavailable('Attachment capabilities unavailable; no fallback shell will be started') from None
  if pid != current['pid'] or running is not True or tty is not True or stdin is not True:
    raise Unavailable('Instance is no longer running or lacks an interactive terminal; no agent will be started')
  if (proc.identity(current['pid'])['start_ticks'] != current['identity']['start_ticks']
      or proc.namespace(current['pid']) != tuple(current['namespaces'])):
    raise Unavailable('Instance identity changed before attachment')
  return current


def attach(before, proc, check=False):
  if not check:
    terminal_required()
  current = verify_attach(before, proc)
  if check:
    print('Attachment target verified: '+current['instance']+'; no terminal stream opened.')
    return 0
  details(current)
  print('\nAttach to the EXISTING harness. Input and terminal resizing may affect another attached terminal.')
  print('Detach without stopping: Ctrl+P, then Ctrl+Q. Ctrl+C may interrupt the agent.')
  print('No new shell/agent, log replay, screen scraping, or output recording is performed by this controller.', flush=True)
  # Inherit the user's terminal directly. Never PIPE/capture/replay the agent's
  # output or send programmatic input. No automatic restart, exec, or retry.
  result = subprocess.run(['podman', '--remote=false', 'attach', '--sig-proxy=false',
    '--detach-keys=ctrl-p,ctrl-q', current['container_id']], check=False)
  print('\nAttachment ended. This controller did not request a container stop.', flush=True)
  return result.returncode


def choose(header, choices):
  result = subprocess.run(['gum', 'choose', '--header', header, '--', *choices],
    stdout=subprocess.PIPE, text=True, check=False)
  if result.returncode:
    return None
  # Only menu labels are captured. This function never wraps harness I/O.
  value = result.stdout.rstrip('\n')
  if value not in choices:
    raise Unavailable('Invalid menu selection')
  return value


def close_selected(before, proc, force):
  screen()
  details(before)
  print('Closing can discard work or interrupt writes. Shared homes are not deleted.', flush=True)
  question = 'Force-kill this exact instance?' if force else 'Stop this exact instance (10-second grace, then kill)?'
  if subprocess.run(['gum', 'confirm', '--default=false', question]).returncode:
    return False
  def action(command):
    result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
      stderr=subprocess.DEVNULL, timeout=20, check=False)
    if result.returncode:
      raise Unavailable('Engine did not confirm closure; no automatic retry was attempted')
  sessions.close_instance(before, sessions.status.Query, proc, force, action)
  print('Closure requested for '+before['instance']+'. Shared homes were not removed.')
  return True


def menu(proc):
  terminal_required()
  while True:
    screen()
    rows = sessions.inventory(sessions.status.Query(), proc, diagnostics=False)
    labels = {}
    for row in rows:
      directory = sessions.status.display(row['project']['host_path'])
      if len(directory) > 48:
        directory = '…'+directory[-47:]
      label = row['agent'][:16]+' | '+row['instance'][:8]+' | PID '+str(row['pid'])+' | '+directory
      if label in labels:
        raise Unavailable('Ambiguous instance list; no action attempted')
      labels[label] = row
    if not rows:
      print('No running managed harness instances were returned. Nothing will be restarted.')
    selected = choose('Running harnesses — choose an instance; no automatic cleanup', ['Exit', 'Refresh', *labels])
    if selected in (None, 'Exit'):
      return 0
    if selected == 'Refresh':
      continue
    before = labels[selected]
    while True:
      screen()
      details(before)
      action = choose('Exact selected instance — attach shares input; closing can discard work',
        ['Back', 'Attach existing harness', 'Close (10-second grace)', 'Force close'])
      if action in (None, 'Back'):
        break
      try:
        if action == 'Attach existing harness':
          if attach(before, proc):
            input('Attachment did not confirm success. Press Enter to return to the selected instance. ')
        elif action in ('Close (10-second grace)', 'Force close'):
          if close_selected(before, proc, action == 'Force close'):
            break
      except (Unavailable, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        print('Instance unavailable, changed, or operation not confirmed. No restart or broader retry. Refresh to select again.')
        input('Press Enter to return to the list. ')
        break


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  sub = parser.add_subparsers(dest='operation', required=True)
  sub.add_parser('menu')
  command = sub.add_parser('attach')
  command.add_argument('instance')
  command.add_argument('--check', action='store_true', help='Validate the target without opening its terminal stream')
  args = parser.parse_args()
  proc = sessions.status.Proc()
  if args.operation == 'menu':
    return menu(proc)
  if not args.check:
    terminal_required()
  before = sessions.select(sessions.inventory(sessions.status.Query(), proc, diagnostics=False), args.instance)
  return attach(before, proc, args.check)


if __name__ == '__main__':
  try:
    sys.exit(main())
  except Unavailable as error:
    sys.exit(str(error))
  except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
    sys.exit('Harness attachment unavailable. No new agent, automatic restart, or broader retry was attempted.')
