"""Host-wrapper hints only: real launcher, inert executors, no Herdr/engine/provider calls."""
import json
import os
from pathlib import Path
import pty
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(os.environ.get('ROOT', '.')).resolve()
STUB = '''#!/usr/bin/python3
import json, os, pathlib, sys
name = pathlib.Path(sys.argv[0]).name
if name == 'omarchy-default-agent':
  print(os.environ.get('TEST_AGENT', 'pi'))
elif name == 'omarchy-agent-mode':
  print(os.environ.get('TEST_MODE', 'container'))
elif name == 'omarchy-cmd-missing':
  sys.exit(1)
else:
  row = {'name': name, 'args': sys.argv[1:], 'cwd': os.getcwd(),
         'hint_set': 'HERDR_AGENT' in os.environ, 'hint': os.environ.get('HERDR_AGENT'),
         'herdr_env': os.environ.get('HERDR_ENV'),
         'stdin_tty': os.isatty(0), 'stdout_tty': os.isatty(1)}
  pathlib.Path(os.environ['TEST_LOG']).write_text(json.dumps(row))
  sys.exit(int(os.environ.get('TEST_EXIT', '0')))
'''


class HerdrHintTests(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory(prefix='agent-herdr-hint-')
    self.addCleanup(temporary.cleanup)
    self.root = Path(temporary.name)
    self.bin = self.root/'bin'
    self.bin.mkdir()
    shutil.copy2(ROOT/'bin/omarchy-agent', self.bin/'omarchy-agent')
    self.home = self.root/'home'
    self.home.mkdir()
    self.project = self.root/'project with spaces ; $(touch escaped)'
    self.project.mkdir()
    self.log = self.root/'result.json'
    self.env = {'PATH': str(self.bin)+':/usr/bin:/bin', 'HOME': str(self.home),
                'OMARCHY_PATH': str(self.root), 'TEST_LOG': str(self.log),
                'HERDR_ENV': '1', 'TERM': 'xterm-256color'}
    for key, directory in [('XDG_CONFIG_HOME', '.config'), ('XDG_DATA_HOME', '.local/share'),
                           ('XDG_STATE_HOME', '.local/state'), ('XDG_CACHE_HOME', '.cache')]:
      self.env[key] = str(self.home/directory)
    for name in ('omarchy-default-agent', 'omarchy-agent-mode', 'omarchy-cmd-missing',
                 'omarchy-agent-exec', 'omarchy-launch-tui', 'pi'):
      path = self.bin/name
      path.write_text(STUB)
      path.chmod(0o755)

  def launch(self, options=(), terminal=True, environment=None):
    env = dict(self.env)
    for key, value in (environment or {}).items():
      if value is None:
        env.pop(key, None)
      else:
        env[key] = value
    command = [str(self.bin/'omarchy-agent'), *options]
    if terminal:
      master, slave = pty.openpty()
      try:
        process = subprocess.Popen(command, stdin=slave, stdout=slave, stderr=slave,
                                   env=env, cwd=self.root)
        try:
          code = process.wait(timeout=10)
        finally:
          if process.poll() is None:
            process.kill()
            process.wait()
      finally:
        os.close(master)
        os.close(slave)
    else:
      result = subprocess.run(command, input=b'', capture_output=True, env=env,
                              cwd=self.root, timeout=10)
      code = result.returncode
    self.assertTrue(self.log.is_file(), 'inert executor must be reached, not a real runtime')
    self.assertFalse((self.root/'escaped').exists())
    return code, json.loads(self.log.read_text())

  def test_inline_pi_gets_host_wrapper_hint(self):
    code, row = self.launch(['--inline', '--container', '--agent=pi', '--directory', str(self.project)])
    self.assertEqual(code, 0)
    self.assertEqual(row['name'], 'omarchy-agent-exec')
    self.assertEqual(row['hint'], 'pi')
    self.assertEqual(row['cwd'], str(self.project))
    self.assertEqual(row['args'], ['--container', '--select-image', 'pi', '--', 'pi'])
    self.assertTrue(row['stdin_tty'] and row['stdout_tty'])

  def test_codex_gets_selected_agent_not_default_pi(self):
    code, row = self.launch(['--inline', '--container', '--agent=codex'])
    self.assertEqual(code, 0)
    self.assertEqual(row['hint'], 'codex')
    self.assertEqual(row['args'][:3], ['--container', '--select-image', 'codex'])

  def test_configured_container_mode_and_default_agent(self):
    code, row = self.launch(['--inline'])
    self.assertEqual(code, 0)
    self.assertEqual(row['hint'], 'pi')

  def test_supported_selected_agent_names(self):
    for agent in ('omp', 'claude', 'opencode', 'agy', 'copilot', 'grok', 'hermes', 'muse', 'kimi'):
      with self.subTest(agent=agent):
        code, row = self.launch(['--inline', '--container', '--agent='+agent])
        self.assertEqual(code, 0)
        self.assertEqual(row['hint'], agent)

  def test_cursor_executable_maps_to_herdr_kind(self):
    code, row = self.launch(['--inline', '--container', '--agent=cursor-agent'])
    self.assertEqual(code, 0)
    self.assertEqual(row['hint'], 'cursor')

  def test_unsupported_herdr_agents_are_not_invented(self):
    for agent in ('openclaw', 'crush', 'ori'):
      with self.subTest(agent=agent):
        code, row = self.launch(['--inline', '--container', '--agent='+agent])
        self.assertEqual(code, 0)
        self.assertFalse(row['hint_set'])

  def test_explicit_hint_is_preserved(self):
    code, row = self.launch(['--inline', '--container', '--agent=pi'], environment={'HERDR_AGENT': 'codex'})
    self.assertEqual(code, 0)
    self.assertEqual(row['hint'], 'codex')

  def test_explicit_empty_hint_is_an_opt_out(self):
    code, row = self.launch(['--inline', '--container'], environment={'HERDR_AGENT': ''})
    self.assertEqual(code, 0)
    self.assertTrue(row['hint_set'])
    self.assertEqual(row['hint'], '')

  def test_no_automatic_hint_outside_herdr(self):
    for value in (None, '', '0', 'yes'):
      with self.subTest(value=value):
        code, row = self.launch(['--inline', '--container'], environment={'HERDR_ENV': value})
        self.assertEqual(code, 0)
        self.assertFalse(row['hint_set'])

  def test_host_launch_is_not_wrapped(self):
    code, row = self.launch(['--inline', '--host', '--agent=pi'])
    self.assertEqual(code, 0)
    self.assertEqual(row['name'], 'pi')
    self.assertFalse(row['hint_set'])

  def test_new_terminal_does_not_label_callers_pane(self):
    code, row = self.launch(['--container', '--agent=pi'])
    self.assertEqual(code, 0)
    self.assertEqual(row['name'], 'omarchy-launch-tui')
    self.assertFalse(row['hint_set'])
    self.assertEqual(row['args'][:2], ['--app-id=org.omarchy.agent', str(self.bin/'omarchy-agent-exec')])

  def test_batch_stdin_stdout_does_not_get_tui_hint(self):
    code, row = self.launch(['--inline', '--container'], terminal=False)
    self.assertEqual(code, 0)
    self.assertFalse(row['hint_set'])

  def test_one_shot_does_not_get_interactive_hint(self):
    code, row = self.launch(['--container', '--agent=pi', '--oneshot', '--prompt', 'inert fixture'])
    self.assertEqual(code, 0)
    self.assertFalse(row['hint_set'])
    self.assertIn('--print', row['args'])

  def test_check_does_not_set_hint(self):
    code, row = self.launch(['--check', '--inline', '--container', '--agent=pi'])
    self.assertEqual(code, 0)
    self.assertFalse(row['hint_set'])
    self.assertIn('--check', row['args'])

  def test_exit_status_is_not_hidden(self):
    code, row = self.launch(['--inline', '--container'], environment={'TEST_EXIT': '23'})
    self.assertEqual(code, 23)
    self.assertEqual(row['hint'], 'pi')


if __name__ == '__main__':
  unittest.main()
