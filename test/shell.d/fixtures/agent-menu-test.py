import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(os.environ['ROOT'])
spec = importlib.util.spec_from_file_location('agent_menu', ROOT/'default/agents/launch-menu.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class MenuTests(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    self.base = Path(self.temp.name)
    self.home = self.base/'home'
    self.home.mkdir()
    self.source = self.home/'project $(touch INJECTED); "quoted"'
    self.source.mkdir()
    env = patch.dict(os.environ, HOME=str(self.home), XDG_STATE_HOME=str(self.base/'state'), XDG_DATA_HOME=str(self.base/'data'), OMARCHY_PATH=str(ROOT))
    env.start()
    self.addCleanup(env.stop)

  def test_recent_state_is_private_bounded_and_does_not_modify_defaults(self):
    self.assertEqual(m.recent_projects(), [])
    self.assertFalse((self.base/'state').exists())
    for i in range(12):
      source = self.home/str(i)
      source.mkdir()
      m.remember(source)
    self.assertEqual(len(m.recent_projects()), 10)
    self.assertEqual(m.recent_projects()[0], str(self.home/'11'))
    self.assertEqual(m.recent_file().stat().st_mode & 0o777, 0o600)
    self.assertEqual(m.recent_file().parent.stat().st_mode & 0o777, 0o700)
    self.assertFalse((self.home/'.config').exists())
    m.recent_file().unlink()
    m.recent_file().symlink_to(self.source)
    with self.assertRaises(OSError):
      m.recent_projects()

  def test_recents_reject_corruption_oversize_and_unsafe_permissions(self):
    m.remember(self.source)
    for content in ('{}', ' ' * 65537, json.dumps(['relative/path']), json.dumps(['/bad\npath'])):
      m.recent_file().write_text(content)
      with self.assertRaises((ValueError, RuntimeError)):
        m.recent_projects()
    m.recent_file().write_text('[]')
    m.recent_file().chmod(0o644)
    with self.assertRaises(RuntimeError):
      m.recent_projects()

  def test_flow_pins_per_launch_choices_without_writing_defaults_or_preparing_project(self):
    record = dict(name='pi', label='Pi', host=True, container=True)
    with patch.object(m, 'recent_projects', return_value=[str(self.source)]), patch.object(m, 'agent_choices', return_value=([record], 'pi')), patch.object(m, 'value', return_value='host'), patch.object(m.ui, 'choose', side_effect=[str(self.source), record, 'container', 'clone']), patch.object(m, 'input_value', return_value='agent-copy'), patch.object(m, 'launch') as launch:
      m.open_menu()
      launch.assert_called_once_with('--start', 'pi', 'container', str(self.source), 'clone', 'agent-copy')
    self.assertFalse((self.base/'state').exists())
    self.assertFalse((self.base/'data').exists())
    self.assertFalse((self.home/'.config').exists())

  def test_cancellation_at_each_picker_does_not_launch_prepare_or_remember(self):
    record = dict(name='pi', label='Pi', host=True, container=True)
    for step in range(4):
      answers = [str(self.source), record, 'container', 'clone'][:step]+[m.ui.Cancelled()]
      with self.subTest(step=step), patch.object(m, 'recent_projects', return_value=[str(self.source)]), patch.object(m, 'agent_choices', return_value=([record], 'pi')), patch.object(m, 'value', return_value='host'), patch.object(m.ui, 'choose', side_effect=answers), patch.object(m, 'launch') as launch, patch.object(m, 'remember') as remember:
        with self.assertRaises(m.ui.Cancelled):
          m.open_menu()
        launch.assert_not_called()
        remember.assert_not_called()

  def test_unsupported_mode_does_not_fall_back(self):
    record = dict(name='codex', label='Codex', host=True, container=False)
    with patch.object(m, 'recent_projects', return_value=[str(self.source)]), patch.object(m, 'agent_choices', return_value=([record], 'codex')), patch.object(m, 'value', return_value='container'), patch.object(m.ui, 'choose', side_effect=[str(self.source), record, 'container']), patch.object(m, 'launch') as launch:
      with self.assertRaisesRegex(RuntimeError, 'No usable|unavailable'):
        m.open_menu()
      launch.assert_not_called()

  def test_final_cancel_precedes_every_write(self):
    for mode, access, name in [('host', 'host', ''), ('container', 'mount', ''), ('container', 'clone', 'copy')]:
      for status in (1, 130):
        with self.subTest(mode=mode, access=access, status=status), patch.object(m, 'ready', return_value=True), patch.object(m, 'value', return_value='{"workspaces":[]}'), patch.object(m.subprocess, 'run', return_value=subprocess.CompletedProcess([], status)) as run, patch.object(m, 'execute') as execute, patch.object(m, 'remember') as remember, patch('sys.stdout', new_callable=io.StringIO) as out:
          with self.assertRaises(m.ui.Cancelled):
            m.worker(['--start', 'pi', mode, str(self.source), access, name])
          execute.assert_not_called()
          remember.assert_not_called()
          self.assertIn('--default=false', run.call_args.args[0])
          if mode == 'host':
            self.assertIn('not a sandbox', out.getvalue())
          elif access == 'mount':
            self.assertIn('immediately modify host files', out.getvalue())
          else:
            self.assertIn('uncommitted/untracked', out.getvalue())

  def test_confirmed_live_launch_has_exact_arguments_and_no_default_changes(self):
    for mode, access in [('host', 'host'), ('container', 'mount')]:
      with self.subTest(mode=mode), patch.object(m, 'ready', return_value=True), patch.object(m.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)), patch.object(m, 'execute') as execute, patch('sys.stdout', new_callable=io.StringIO):
        m.worker(['--start', 'pi', mode, str(self.source), access, ''])
        execute.assert_called_once_with(['omarchy-agent', '--inline', '--agent', 'pi', '--directory', str(self.source), '--'+mode, '--installed-only'])
    self.assertEqual(m.recent_projects(), [str(self.source)])
    self.assertFalse((self.home/'.config').exists())
    self.assertFalse((self.base/'data').exists())

  def test_existing_workspace_files_require_explicit_selection_and_do_not_start_editor(self):
    directory = self.base/'isolated repo'
    directory.mkdir()
    record = dict(name='saved-copy', mode='clone', source=str(self.source), directory=str(directory))
    with patch.object(m, 'ready', return_value=True), patch.object(m, 'value', return_value=json.dumps({'workspaces':[record]})), patch.object(m.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)), patch.object(m, 'execute') as execute, patch('sys.stdout', new_callable=io.StringIO) as out:
      m.worker(['--start', 'pi', 'container', 'workspace:saved-copy', 'workspace', 'saved-copy'])
      execute.assert_called_once_with(['omarchy-agent', '--inline', '--agent', 'pi', '--directory', str(directory), '--container', '--installed-only'])
      self.assertIn('SAME files', out.getvalue())
      self.assertFalse(m.recent_file().exists())
    directory.rmdir()
    directory.symlink_to(self.source, target_is_directory=True)
    with patch.object(m, 'value', return_value=json.dumps({'workspaces':[record]})):
      with self.assertRaises(RuntimeError):
        m.workspace_project('saved-copy')

  def test_unsupported_runtime_and_invalid_access_fail_before_confirmation(self):
    with patch.object(m, 'ready', return_value=False), patch.object(m.subprocess, 'run') as run:
      with self.assertRaisesRegex(RuntimeError, 'unavailable'):
        m.worker(['--start', 'pi', 'container', str(self.source), 'mount', ''])
      run.assert_not_called()
    for mode, access in [('other', 'mount'), ('host', 'clone'), ('container', 'host')]:
      with self.assertRaises(RuntimeError):
        m.checked_source(str(self.source), mode, access)

  def test_project_permissions_reject_broad_sensitive_active_and_control_paths(self):
    for path in (self.home, Path('/'), self.base/'state/omarchy/agent-menu'):
      path.mkdir(parents=True, exist_ok=True)
      with self.assertRaises(RuntimeError):
        m.checked_source(str(path), 'container', 'mount')
    with patch.dict(os.environ, OMARCHY_PATH=str(self.source)):
      with self.assertRaises(RuntimeError):
        m.checked_source(str(self.source), 'container', 'mount')
    with self.assertRaises(RuntimeError):
      m.checked_source('/bad\npath', 'host', 'host')

  def test_clone_uses_existing_backend_and_retains_prepared_copy_after_launch_failure(self):
    # Real local Git/key creation in an isolated home; no engine/model invocation.
    env = dict(os.environ, GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1', GIT_TERMINAL_PROMPT='0')
    for args in [['git', 'init', '-q', str(self.source)], ['git', '-C', str(self.source), 'config', 'user.name', 'Agent Menu Test'], ['git', '-C', str(self.source), 'config', 'user.email', 'test@example.invalid']]:
      subprocess.run(args, check=True, env=env)
    (self.source/'tracked').write_text('original\n')
    subprocess.run(['git', '-C', str(self.source), 'add', '.'], check=True, env=env)
    subprocess.run(['git', '-C', str(self.source), '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'fixture'], check=True, env=env)
    (self.source/'untracked').write_text('excluded\n')
    actual_run = subprocess.run
    calls = []
    def run(args, **kwargs):
      if args[0] == 'gum':
        return subprocess.CompletedProcess(args, 0)
      if args[0] == 'podman':
        self.assertEqual(args[1], 'ps')
        return subprocess.CompletedProcess(args, 0, stdout='[]')
      return actual_run(args, **kwargs)
    def backend(args, capture=False, **kwargs):
      calls.append(args)
      if args[0] == 'omarchy-agent':
        raise subprocess.CalledProcessError(1, 'synthetic agent failure')
      operation = 'create' if args[0] == 'omarchy-workspace-create' else 'list'
      with patch.object(sys, 'argv', ['workspace', operation, *args[1:]]), patch('sys.stdout', new_callable=io.StringIO) as out:
        m.workspaces.main()
        return subprocess.CompletedProcess(args, 0, stdout=out.getvalue())
    with patch.dict(os.environ, env), patch.object(m, 'ready', return_value=True), patch.object(m.subprocess, 'run', side_effect=run), patch.object(m, 'execute', side_effect=backend), patch('sys.stdout', new_callable=io.StringIO):
      with self.assertRaises(subprocess.CalledProcessError):
        m.worker(['--start', 'pi', 'container', str(self.source), 'clone', 'copy'])
    repo = self.base/'data/omarchy/workspaces/copy/repo'
    self.assertTrue(repo.is_dir())
    self.assertFalse((repo/'untracked').exists())
    self.assertEqual(subprocess.check_output(['git', '-C', str(repo), 'remote'], env=env, text=True), '')
    self.assertIn(str(repo), calls[-1])
    self.assertEqual((self.source/'tracked').read_text(), 'original\n')
    self.assertFalse(any('workspace-code' in args[0] for args in calls))


if __name__ == '__main__':
  unittest.main(verbosity=2)
