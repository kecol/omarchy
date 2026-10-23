import importlib.util
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(os.environ['ROOT'])
spec = importlib.util.spec_from_file_location('workspace_menu', ROOT/'default/workspaces/menu.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class MenuTests(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    self.source = Path(self.temp.name)/'project $(touch UNEXPECTED); "quoted"'
    self.source.mkdir()
    self.records = []
    self.answers = []
    self.calls = []
    self.file_status = 0
    self.input_status = 0
    self.code_present = True
    self.name = 'new-project'
    env = patch.dict(os.environ, OMARCHY_PATH=str(ROOT))
    env.start()
    self.addCleanup(env.stop)
    runner = patch.object(m.subprocess, 'run', side_effect=self.run_command)
    runner.start()
    self.addCleanup(runner.stop)

  def run_command(self, args, **kwargs):
    self.calls.append(args)
    status, text = 0, ''
    if args[0] == 'omarchy-cmd-present':
      status = 0 if self.code_present else 1
    elif args[0] == 'omarchy-workspace-list':
      self.assertEqual(args[1:], ['--json'])
      text = json.dumps({'workspaces': self.records})
    elif args[0] == 'omarchy-menu-select':
      answer = self.answers.pop(0)
      if answer is None:
        status = 1
      elif answer == 'forged':
        text = 'not a real option'
      else:
        text = [a[1:] for a in args if a.startswith('\t')][answer]+'\n'
    elif args[0] == 'omarchy-file-select':
      status, text = self.file_status, str(self.source)+'\n'
    elif args[0] == 'omarchy-menu-input':
      status, text = self.input_status, self.name+'\n'
    elif args[0] != 'omarchy-launch-floating-terminal-with-presentation':
      self.fail('unexpected command: '+repr(args))
    return subprocess.CompletedProcess(args, status, stdout=text)

  def launches(self):
    return [shlex.split(args[1]) for args in self.calls if args[0] == 'omarchy-launch-floating-terminal-with-presentation']

  def test_create_clone_uses_exact_arguments_after_confirmation(self):
    self.answers = [0, 0]
    m.open_menu()
    self.assertEqual(self.launches()[0], ['python3', str(ROOT/'default/workspaces/menu.py'), '--create', 'new-project', str(self.source), 'clone'])
    self.assertFalse(Path('UNEXPECTED').exists())
    self.assertFalse(any(args[0] in ('omarchy-workspace-create', 'omarchy-workspace-code', 'podman') for args in self.calls))

  def test_live_mount_requires_explicit_access_and_final_confirmation(self):
    self.answers = [0, 1]
    m.open_menu()
    self.assertEqual(self.launches()[0][-1], 'mount')
    prompts = [args for args in self.calls if args[0] == 'omarchy-menu-select']
    self.assertTrue(any('WARNING: immediate host writes' in arg for arg in prompts[-1]))

  def test_existing_workspace_selection_uses_name_not_display_path(self):
    self.records = [dict(name='one', source='/original\tpath', directory='/isolated repo', mode='clone', state='stopped')]
    self.answers = [1]
    m.open_menu()
    self.assertEqual(self.launches()[0][-2:], ['--open', 'one'])
    self.assertFalse(any(args[0] == 'omarchy-file-select' for args in self.calls))
    self.assertTrue(any('/original path' in arg for arg in self.calls[2]))

  def test_every_creation_cancellation_has_no_workspace_side_effects(self):
    for stage in ('first', 'folder', 'name', 'access'):
      with self.subTest(stage=stage):
        self.calls = []
        self.file_status = 1 if stage == 'folder' else 0
        self.input_status = 1 if stage == 'name' else 0
        self.answers = {'first': [None], 'folder': [0], 'name': [0], 'access': [0, None]}[stage]
        with self.assertRaises(m.Cancelled):
          m.open_menu()
        self.assertEqual(self.launches(), [])
        self.assertFalse(any(args[0] in ('omarchy-workspace-create', 'omarchy-workspace-code', 'podman') for args in self.calls))

  def test_errors_do_not_become_cancellation_or_fallbacks(self):
    for problem in ('chooser', 'invalid-name', 'duplicate', 'missing-vscode', 'forged-choice'):
      with self.subTest(problem=problem):
        self.calls = []
        self.file_status = 2 if problem == 'chooser' else 0
        self.name = 'bad; command' if problem == 'invalid-name' else 'one'
        self.records = [dict(name='one', source='/source', directory='/repo', mode='clone', state='running')] if problem == 'duplicate' else []
        self.code_present = problem != 'missing-vscode'
        self.answers = ['forged'] if problem == 'forged-choice' else [0]
        with self.assertRaises(RuntimeError):
          m.open_menu()
        self.assertEqual(self.launches(), [])

  def test_worker_preserves_paths_and_only_opens_after_successful_creation(self):
    with patch.object(m, 'confirm_terminal'), patch.object(m, 'command') as run:
      m.worker(['--create', 'one', str(self.source), 'mount'])
      self.assertEqual([call.args[0] for call in run.call_args_list], [
        ['omarchy-workspace-create', 'one', str(self.source), '--mount'], ['omarchy-workspace-code', 'one']])
    with patch.object(m, 'confirm_terminal'), patch.object(m, 'command', side_effect=subprocess.CalledProcessError(1, 'create')) as run:
      with self.assertRaises(subprocess.CalledProcessError):
        m.worker(['--create', 'one', str(self.source), 'clone'])
      self.assertEqual(run.call_count, 1)

  def test_editor_failure_does_not_attempt_to_remove_created_workspace(self):
    with patch.object(m, 'confirm_terminal'), patch.object(m, 'command', side_effect=[subprocess.CompletedProcess([], 0), subprocess.CalledProcessError(1, 'code')]) as run:
      with self.assertRaises(subprocess.CalledProcessError):
        m.worker(['--create', 'one', str(self.source), 'clone'])
      self.assertEqual([call.args[0][0] for call in run.call_args_list], ['omarchy-workspace-create', 'omarchy-workspace-code'])

  def test_confirmation_defaults_to_cancel_and_precedes_all_writes(self):
    for mode in ('clone', 'mount'):
      for status in (1, 130):
        with self.subTest(mode=mode, status=status), patch.object(m.subprocess, 'run', return_value=subprocess.CompletedProcess([], status)) as run, patch.object(m, 'command') as backend, patch('sys.stdout', new_callable=io.StringIO) as output:
          with self.assertRaises(m.Cancelled):
            m.worker(['--create', 'one', str(self.source), mode])
          backend.assert_not_called()
          self.assertIn('--default=false', run.call_args.args[0])
          self.assertIn(str(self.source), output.getvalue())
          if mode == 'mount':
            self.assertIn('LIVE HOST DIRECTORY', output.getvalue())
          else:
            self.assertIn('uncommitted or untracked', output.getvalue())

  def test_newline_in_selected_path_is_not_stripped_into_another_directory(self):
    self.source = Path(self.temp.name)/'unsafe\n'
    self.source.mkdir()
    self.answers = [0]
    with self.assertRaises(RuntimeError):
      m.open_menu()
    self.assertEqual(self.launches(), [])


if __name__ == '__main__':
  unittest.main(verbosity=2)
