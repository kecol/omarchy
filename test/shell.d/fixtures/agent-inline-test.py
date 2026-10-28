"""Public inline route with a synthetic terminal and a fail-closed fake engine."""
import json
import os
from pathlib import Path
import pty
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(os.environ.get('ROOT', '.'))
IMAGE = 'sha256:'+'a'*64


def stub():
  name, *args = sys.argv[2:]
  row = {'name': name, 'args': args, 'cwd': os.getcwd(), 'stdin_tty': os.isatty(0), 'stdout_tty': os.isatty(1),
         'herdr_agent': os.environ.get('HERDR_AGENT'), 'herdr_agent_set': 'HERDR_AGENT' in os.environ}
  if os.isatty(0):
    row['terminal'] = os.ttyname(0)
  with open(os.environ['OFFLINE_LOG'], 'a') as stream:
    stream.write(json.dumps(row)+'\n')
  if name == 'omarchy-agent-mode':
    print(os.environ.get('OFFLINE_MODE', 'host'))
  elif name == 'omarchy-default-agent':
    print('pi')
  elif name == 'omarchy-agent-container-doctor':
    pass
  elif name == 'omarchy-harness-select-image':
    if os.environ.get('OFFLINE_CANCEL') == '1':
      return 130
    print(IMAGE)
  elif name == 'omarchy-agent-policy':
    print(json.dumps({'resources': {'memory': '4g', 'pids': 1024}}))
  elif name == 'omarchy-agent-state':
    pass
  elif name == 'podman' and args == ['--remote=false', 'volume', 'exists', 'omarchy-agent-pi-home']:
    pass
  elif name == 'podman' and args[:3] == ['--remote=false', 'run', '--rm']:
    return int(os.environ.get('OFFLINE_EXIT', '0'))
  else:
    print('Unexpected offline operation: '+name, file=sys.stderr)
    return 99
  return 0


class InlineTests(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory(prefix='agent-inline-')
    self.addCleanup(temporary.cleanup)
    self.root = Path(temporary.name)
    self.stage = self.root/'source'
    self.bin = self.stage/'bin'
    self.bin.mkdir(parents=True)
    for name in ('omarchy', 'omarchy-agent', 'omarchy-agent-exec', 'omarchy-agent-run-podman'):
      shutil.copy2(ROOT/'bin'/name, self.bin/name)
    for asset in ('definitions/pi.json', 'pi/model-recovery.ts'):
      target = self.stage/'default/agents'/asset
      target.parent.mkdir(parents=True, exist_ok=True)
      shutil.copy2(ROOT/'default/agents'/asset, target)
    self.log = self.root/'calls.jsonl'
    self.home = self.root/'home'
    self.home.mkdir()
    self.project = self.root/'project with spaces ; $(touch should-not-exist)'
    self.project.mkdir()
    self.mode = self.home/'.config/omarchy/agents/mode'
    self.mode.parent.mkdir(parents=True)
    self.mode.write_text('host\n')
    # No inherited authentication, display sockets, engine context, or real HOME.
    self.env = {'HOME': str(self.home), 'PATH': str(self.bin)+':/usr/bin:/bin',
                'OMARCHY_PATH': str(self.stage), 'TERM': 'xterm-256color',
                'OFFLINE_FIXTURE': str(Path(__file__).resolve()), 'OFFLINE_LOG': str(self.log),
                'HERDR_AGENT': 'pi'}
    for key, directory in (('XDG_CONFIG_HOME', '.config'), ('XDG_DATA_HOME', '.local/share'), ('XDG_STATE_HOME', '.local/state'), ('XDG_CACHE_HOME', '.cache')):
      self.env[key] = str(self.home/directory)
    for name in ('omarchy-agent-mode', 'omarchy-default-agent', 'omarchy-agent-container-doctor', 'omarchy-harness-select-image', 'omarchy-agent-policy', 'omarchy-agent-state', 'omarchy-launch-tui', 'podman', 'pi', 'ssh', 'sudo', 'gum'):
      path = self.bin/name
      path.write_text('#!/bin/bash\nexec /usr/bin/python3 -I -B "$OFFLINE_FIXTURE" stub "${0##*/}" "$@"\n')
      path.chmod(0o755)

  def launch(self, options, terminal=True, **env):
    command = [str(self.bin/'omarchy'), 'agent', *options]
    if terminal:
      master, slave = pty.openpty()
      expected = os.ttyname(slave)
      self.addCleanup(os.close, master)
      self.addCleanup(os.close, slave)
      process = subprocess.Popen(command, stdin=slave, stdout=slave, stderr=slave, env={**self.env, **env}, cwd=self.root)
      try:
        code = process.wait(timeout=10)
      finally:
        if process.poll() is None:
          process.kill(); process.wait()
    else:
      expected = None
      result = subprocess.run(command, input=b'', capture_output=True, env={**self.env, **env}, cwd=self.root, timeout=10)
      code = result.returncode
    rows = [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []
    self.assertEqual(self.mode.read_text(), 'host\n')
    self.assertFalse(any(r['name'] in ('omarchy-launch-tui', 'pi', 'ssh', 'sudo', 'gum') for r in rows))
    self.assertFalse((self.root/'should-not-exist').exists())
    return code, rows, expected

  def test_inline_public_route_preserves_terminal_cwd_and_isolation_arguments(self):
    code, rows, terminal = self.launch(['--inline', '--container', '--agent', 'pi', '--directory', str(self.project)])
    self.assertEqual(code, 0)
    run = next(r for r in rows if r['name'] == 'podman' and r['args'][1] == 'run')
    self.assertEqual(run['args'][0], '--remote=false')
    self.assertEqual(run['terminal'], terminal)
    self.assertTrue(run['stdin_tty'] and run['stdout_tty'])
    self.assertEqual(run['cwd'], str(self.project))
    for option in ('--interactive', '--tty', '--pull=never', '--read-only', '--cap-drop=all', IMAGE):
      self.assertIn(option, run['args'])
    mounts = [arg for arg in run['args'] if arg.startswith('--volume=')]
    self.assertEqual(len(mounts), 3)
    self.assertTrue(any(arg.startswith('--volume='+str(self.project)+':') and arg.endswith(':rw,rprivate') for arg in mounts))
    self.assertFalse(any(str(self.home) in arg or 'SSH_AUTH_SOCK' in arg or 'podman.sock' in arg or 'docker.sock' in arg for arg in run['args']))
    selector = next(r for r in rows if r['name'] == 'omarchy-harness-select-image')
    self.assertEqual(selector['args'], ['--interactive', 'pi', 'pi'])
    self.assertEqual(selector['terminal'], terminal)
    self.assertEqual(rows[-1]['args'][0], 'finish')

  def test_inline_uses_default_container_mode_and_equals_options(self):
    code, rows, _ = self.launch(['--inline', '--agent=pi', '--directory='+str(self.project)], OFFLINE_MODE='container')
    self.assertEqual(code, 0)
    self.assertTrue(any(r['name'] == 'omarchy-agent-mode' for r in rows))
    self.assertTrue(any(r['name'] == 'podman' and r['args'][:2] == ['--remote=false', 'run'] for r in rows))

  def test_non_tty_inline_does_not_allocate_tty_or_show_interactive_selector(self):
    code, rows, _ = self.launch(['--inline', '--container', '--agent=pi', '--directory='+str(self.project)], terminal=False)
    self.assertEqual(code, 0)
    run = next(r for r in rows if r['name'] == 'podman' and r['args'][1] == 'run')
    self.assertIn('--interactive', run['args'])
    self.assertNotIn('--tty', run['args'])
    selector = next(r for r in rows if r['name'] == 'omarchy-harness-select-image')
    self.assertEqual(selector['args'], ['pi', 'pi'])

  def test_automatic_herdr_hint_reaches_host_wrapper_not_container_environment(self):
    self.env.pop('HERDR_AGENT')
    code, rows, _ = self.launch(['--inline', '--container', '--agent=pi'], HERDR_ENV='1')
    self.assertEqual(code, 0)
    run = next(r for r in rows if r['name'] == 'podman' and r['args'][1] == 'run')
    self.assertEqual(run['herdr_agent'], 'pi')
    self.assertFalse(any('HERDR_' in arg for arg in run['args']))
    self.assertFalse(any('herdr.sock' in arg for arg in run['args']))

  def test_unhinted_launch_outside_herdr_does_not_gain_a_hint(self):
    self.env.pop('HERDR_AGENT')
    code, rows, _ = self.launch(['--inline', '--container', '--agent=pi'])
    self.assertEqual(code, 0)
    run = next(r for r in rows if r['name'] == 'podman' and r['args'][1] == 'run')
    self.assertFalse(run['herdr_agent_set'])

  def test_image_cancellation_never_reaches_engine_or_lifecycle(self):
    code, rows, _ = self.launch(['--inline', '--container', '--agent=pi'], OFFLINE_CANCEL='1')
    self.assertEqual(code, 0)
    self.assertFalse(any(r['name'] in ('podman', 'omarchy-agent-state') for r in rows))

  def test_inline_propagates_container_failure_without_new_terminal(self):
    code, rows, _ = self.launch(['--inline', '--container', '--agent=pi'], OFFLINE_EXIT='17')
    self.assertEqual(code, 17)
    self.assertEqual(rows[-1]['args'][-2:], ['failed', '17'])


if __name__ == '__main__':
  if len(sys.argv) > 1 and sys.argv[1] == 'stub':
    sys.exit(stub())
  unittest.main()
