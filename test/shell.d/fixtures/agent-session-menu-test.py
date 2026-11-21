import contextlib
import importlib.util
import io
import os
import json
import signal
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(os.environ['ROOT'])
spec = importlib.util.spec_from_file_location('session_menu', ROOT/'default/agents/session-menu.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
TERMINAL_REQUIRED = m.terminal_required


class Proc:
  boot_id = 'fixture-boot'
  def identity(self, pid):
    return {'start_ticks': 100}
  def namespace(self, pid):
    return ('pid:fixture', 'mnt:fixture')


class MenuTests(unittest.TestCase):
  def setUp(self):
    self.proc = Proc()
    self.row = {'instance': '11111111-2222-4333-8444-555555555555', 'agent': 'codex',
      'container_id': 'a'*64, 'container_name': 'omarchy-agent-codex-111111112222', 'pid': 20,
      'identity': {'boot_id': 'fixture-boot', 'start_ticks': 100},
      'namespaces': ['pid:fixture', 'mnt:fixture'], 'started_at': '2026-10-26',
      'project': {'host_path': '/fixture/project', 'container_path': '/workspace/key', 'project_id': 'key', 'access': 'read-write'}}
    for target, value in [('inventory', [self.row])]:
      p = patch.object(m.sessions, target, return_value=value)
      p.start(); self.addCleanup(p.stop)
    p = patch.object(m.sessions.status, 'Query', return_value=self.query)
    p.start(); self.addCleanup(p.stop)
    p = patch.object(m, 'terminal_required')
    self.terminal = p.start(); self.addCleanup(p.stop)
    self.capabilities = '20\ttrue\ttrue\ttrue'
    self.shell_metadata = json.dumps('a'*64)+'\t20\ttrue'
    self.stdout = io.StringIO()
    p = contextlib.redirect_stdout(self.stdout)
    p.__enter__(); self.addCleanup(p.__exit__, None, None, None)
  def query(self, args, json_output=True):
    self.assertEqual(args[:3], ['podman', '--remote=false', 'inspect'])
    self.assertEqual(args[-1], self.row['container_id'])
    self.assertNotIn('Env', args[4]); self.assertNotIn('Mount', args[4])
    if '{{json .ID}}' in args[4]:
      self.assertNotIn('Tty', args[4]); self.assertNotIn('OpenStdin', args[4])
      return self.shell_metadata
    return self.capabilities
  def label(self):
    return 'codex | '+self.row['instance'][:8]+' | PID 20 | /fixture/project | 2026-10-26'
  def test_actual_terminal_guard_requires_foreground_controlling_terminal(self):
    class Tty:
      def isatty(self): return True
      def fileno(self): return 0
    with patch.object(m.sys, 'stdin', Tty()), patch.object(m.sys, 'stdout', Tty()), patch.object(m.sys, 'stderr', Tty()):
      with patch.object(m.os, 'tcgetpgrp', return_value=os.getpgrp()):
        TERMINAL_REQUIRED()
      with patch.object(m.os, 'tcgetpgrp', return_value=-1):
        with self.assertRaises(m.Unavailable): TERMINAL_REQUIRED()
      with patch.object(m.os, 'tcgetpgrp', side_effect=OSError('no controlling tty')):
        with self.assertRaises(m.Unavailable): TERMINAL_REQUIRED()

  def test_cancelled_menu_close_returns_to_selected_actions(self):
    with patch.object(m, 'choose', side_effect=[self.label(), 'Force close', 'Back', 'Exit']) as choose, \
      patch.object(m, 'close_selected', return_value=False) as close:
      m.menu(self.proc)
      close.assert_called_once_with(self.row, self.proc, True)
      self.assertEqual(choose.call_count, 4)

  def test_attach_inherits_only_user_terminal_with_exact_full_cid(self):
    with patch.object(m.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)) as run:
      self.assertEqual(m.attach(self.row, self.proc), 0)
    self.assertEqual(run.call_args.args[0], ['podman', '--remote=false', 'attach', '--sig-proxy=false',
      '--detach-keys=ctrl-p,ctrl-q', 'a'*64])
    self.assertEqual(run.call_args.kwargs, {'check': False})
    self.assertIn('Ctrl+P, then Ctrl+Q', self.stdout.getvalue())
  def test_check_never_opens_terminal_stream(self):
    with patch.object(m.subprocess, 'run') as run:
      m.attach(self.row, self.proc, check=True)
      run.assert_not_called()
    self.terminal.assert_not_called()
  def test_no_tty_blocks_attachment(self):
    self.terminal.side_effect = m.Unavailable('no tty')
    with patch.object(m.subprocess, 'run') as run:
      with self.assertRaises(m.Unavailable): m.attach(self.row, self.proc)
      run.assert_not_called()
  def test_no_stopped_or_noninteractive_fallback(self):
    for capabilities in ('20\tfalse\ttrue\ttrue', '20\ttrue\tfalse\ttrue', '20\ttrue\ttrue\tfalse', 'unsupported'):
      self.capabilities = capabilities
      with patch.object(m.subprocess, 'run') as run:
        with self.assertRaises(m.Unavailable): m.attach(self.row, self.proc)
        run.assert_not_called()
  def test_changed_selected_container_is_not_attached(self):
    before = {**self.row, 'container_id': 'b'*64}
    with patch.object(m.subprocess, 'run') as run:
      with self.assertRaises(m.Unavailable): m.attach(before, self.proc)
      run.assert_not_called()
  def test_changed_pid_or_namespace_is_not_attached(self):
    self.capabilities = '21\ttrue\ttrue\ttrue'
    with self.assertRaises(m.Unavailable): m.attach(self.row, self.proc)
    self.capabilities = '20\ttrue\ttrue\ttrue'
    with patch.object(self.proc, 'namespace', return_value=('changed', 'changed')):
      with self.assertRaises(m.Unavailable): m.attach(self.row, self.proc)
  def test_full_immutable_id_is_required(self):
    self.row['container_id'] = 'a'*12
    with self.assertRaises(m.Unavailable): m.attach(self.row, self.proc)
  def test_menu_defaults_to_exit_and_does_not_attach_or_close(self):
    with patch.object(m, 'choose', return_value='Exit') as choose, patch.object(m, 'attach') as attach, patch.object(m, 'close_selected') as close:
      self.assertEqual(m.menu(self.proc), 0)
      self.assertEqual(choose.call_args.args[1][0], 'Exit')
      attach.assert_not_called(); close.assert_not_called()
  def test_menu_attach_returns_to_selected_instance_not_automatic_close(self):
    with patch.object(m, 'choose', side_effect=[self.label(), 'Attach existing harness', 'Back', 'Exit']), \
      patch.object(m, 'attach', return_value=0) as attach, patch.object(m, 'close_selected') as close:
      m.menu(self.proc)
      attach.assert_called_once_with(self.row, self.proc)
      close.assert_not_called()
  def test_cancelled_close_does_not_reach_controller(self):
    with patch.object(m.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1)) as run, \
      patch.object(m.sessions, 'close_instance') as close:
      m.close_selected(self.row, self.proc, True)
      close.assert_not_called()
      self.assertEqual(run.call_args.args[0][:3], ['gum', 'confirm', '--default=false'])
  def test_confirmed_force_close_reuses_identity_checked_controller(self):
    with patch.object(m.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)) as run:
      m.close_selected(self.row, self.proc, True)
      self.assertEqual(run.call_count, 2)
      self.assertEqual(run.call_args.args[0], ['podman', '--remote=false', 'kill', '--signal=KILL', 'a'*64])
  def test_changed_identity_after_confirmation_never_signals(self):
    before = {**self.row, 'container_id': 'b'*64}
    with patch.object(m.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)) as run:
      with self.assertRaises(m.Unavailable): m.close_selected(before, self.proc, False)
      self.assertEqual(run.call_count, 1)
  def test_empty_menu_never_restarts_anything(self):
    with patch.object(m.sessions, 'inventory', return_value=[]), patch.object(m, 'choose', return_value='Exit'), patch.object(m.subprocess, 'run') as run:
      m.menu(self.proc); run.assert_not_called()
      self.assertIn('Nothing will be restarted', self.stdout.getvalue())
  def test_unavailable_inventory_is_not_an_empty_list(self):
    with patch.object(m.sessions, 'inventory', side_effect=m.Unavailable('unavailable')), patch.object(m, 'choose') as choose:
      with self.assertRaises(m.Unavailable): m.menu(self.proc)
      choose.assert_not_called()
  def test_shell_exec_inherits_terminal_and_only_removes_child_remote_selectors(self):
    previous = signal.getsignal(signal.SIGINT)
    with patch.dict(os.environ, {'CONTAINER_HOST': 'unix:///fixture/remote', 'CONTAINER_CONNECTION': 'fixture'}), \
      patch.object(m.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)) as run:
      self.assertEqual(m.open_shell(self.row, self.proc), 0)
      self.assertEqual(run.call_args.args[0], ['podman', '--remote=false', 'exec', '--interactive', '--tty',
        'a'*64, '/bin/bash', '-i'])
      self.assertEqual(set(run.call_args.kwargs), {'env', 'check'})
      self.assertFalse(run.call_args.kwargs['check'])
      self.assertEqual(run.call_args.kwargs['env'], {key: value for key, value in os.environ.items()
        if key not in ('CONTAINER_HOST', 'CONTAINER_CONNECTION')})
      self.assertEqual(os.environ['CONTAINER_CONNECTION'], 'fixture')
      self.assertEqual(os.environ['CONTAINER_HOST'], 'unix:///fixture/remote')
    self.assertEqual(signal.getsignal(signal.SIGINT), previous)
    self.assertIn('concurrent writes', self.stdout.getvalue())

  def test_shell_check_does_not_execute_or_require_terminal(self):
    with patch.object(m.subprocess, 'run') as run:
      self.assertEqual(m.open_shell(self.row, self.proc, check=True), 0)
      run.assert_not_called()
    self.terminal.assert_not_called()
    self.assertIn('Bash availability was not checked', self.stdout.getvalue())

  def test_shell_refuses_replacement_or_missing_instance_without_exec(self):
    before = dict(self.row)
    for rows in ([], [{**self.row, 'container_id': 'b'*64}], [self.row, self.row]):
      with self.subTest(rows=rows), patch.object(m.sessions, 'inventory', return_value=rows), \
        patch.object(m.subprocess, 'run') as run:
        with self.assertRaises(m.Unavailable): m.open_shell(before, self.proc)
        run.assert_not_called()

  def test_shell_requires_full_id_and_valid_running_metadata(self):
    for cid, data in (('a'*12, self.shell_metadata), ('a'*64, 'unsupported'),
      ('a'*64, json.dumps('b'*64)+'\t20\ttrue'), ('a'*64, json.dumps('a'*64)+'\t21\ttrue'),
      ('a'*64, json.dumps('a'*64)+'\t20\tfalse'), ('a'*64, json.dumps('a'*64)+'\ttrue\ttrue')):
      with self.subTest(cid=cid, data=data), patch.object(m.subprocess, 'run') as run:
        self.row['container_id'] = cid
        self.shell_metadata = data
        with self.assertRaises(m.Unavailable): m.open_shell(self.row, self.proc)
        run.assert_not_called()

  def test_shell_rechecks_process_start_namespaces_and_boot(self):
    for method, value in (('identity', lambda pid: {'start_ticks': 101}),
      ('namespace', lambda pid: ('changed', 'changed')), ('boot_id', 'changed-boot')):
      with self.subTest(method=method), patch.object(self.proc, method, value), \
        patch.object(m.subprocess, 'run') as run:
        with self.assertRaises(m.Unavailable): m.open_shell(self.row, self.proc)
        run.assert_not_called()

  def test_shell_does_not_require_init_tty_or_open_stdin(self):
    self.capabilities = '20\ttrue\tfalse\tfalse'
    with patch.object(m.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)) as run:
      self.assertEqual(m.open_shell(self.row, self.proc), 0)
      self.assertEqual(run.call_count, 1)
      with self.assertRaises(m.Unavailable): m.attach(self.row, self.proc)
      self.assertEqual(run.call_count, 1)

  def test_shell_unavailable_inventory_or_terminal_never_executes(self):
    with patch.object(m.sessions, 'inventory', side_effect=m.Unavailable('unavailable')), \
      patch.object(m.subprocess, 'run') as run:
      with self.assertRaises(m.Unavailable): m.open_shell(self.row, self.proc)
      run.assert_not_called()
    self.terminal.side_effect = m.Unavailable('no terminal')
    with patch.object(m.subprocess, 'run') as run:
      with self.assertRaises(m.Unavailable): m.open_shell(self.row, self.proc)
      run.assert_not_called()

  def test_shell_failure_is_returned_once_and_signal_handler_restored(self):
    previous = signal.getsignal(signal.SIGINT)
    def result(*args, **kwargs):
      signal.getsignal(signal.SIGINT)(signal.SIGINT, None)
      return subprocess.CompletedProcess([], 127)
    with patch.object(m.subprocess, 'run', side_effect=result) as run:
      self.assertEqual(m.open_shell(self.row, self.proc), 127)
      self.assertEqual(run.call_count, 1)
    self.assertEqual(signal.getsignal(signal.SIGINT), previous)
    with patch.object(m.subprocess, 'run', side_effect=OSError('exec unavailable')) as run:
      with self.assertRaises(OSError): m.open_shell(self.row, self.proc)
      self.assertEqual(run.call_count, 1)
    self.assertEqual(signal.getsignal(signal.SIGINT), previous)

  def test_shell_cli_check_routes_prefix_without_execution(self):
    with patch.object(m.sys, 'argv', ['session-menu.py', 'shell', '11111111', '--check']), \
      patch.object(m.sessions.status, 'Proc', return_value=self.proc), patch.object(m.subprocess, 'run') as run:
      self.assertEqual(m.main(), 0)
      run.assert_not_called()
    self.terminal.assert_not_called()

  def test_shell_cli_without_selector_opens_shell_picker(self):
    with patch.object(m.sys, 'argv', ['session-menu.py', 'shell']), \
      patch.object(m.sessions.status, 'Proc', return_value=self.proc), patch.object(m, 'menu', return_value=0) as menu:
      self.assertEqual(m.main(), 0)
      menu.assert_called_once_with(self.proc, shell_only=True)

  def test_shell_check_requires_selector_before_inventory(self):
    with patch.object(m.sys, 'argv', ['session-menu.py', 'shell', '--check']), \
      patch.object(m.sessions, 'inventory') as inventory, contextlib.redirect_stderr(io.StringIO()):
      with self.assertRaises(SystemExit) as error: m.main()
      self.assertEqual(error.exception.code, 2)
      inventory.assert_not_called()

  def test_shell_cli_refuses_invalid_or_ambiguous_selectors(self):
    for selector, rows in (('codex', [self.row]), ('11111111', [self.row, self.row]), ('99999999', [self.row])):
      with self.subTest(selector=selector), patch.object(m.sys, 'argv', ['session-menu.py', 'shell', selector, '--check']), \
        patch.object(m.sessions.status, 'Proc', return_value=self.proc), \
        patch.object(m.sessions, 'inventory', return_value=rows), patch.object(m.subprocess, 'run') as run:
        with self.assertRaises(m.Unavailable): m.main()
        run.assert_not_called()

  def test_sessions_shell_returns_to_selected_actions_without_close(self):
    with patch.object(m, 'choose', side_effect=[self.label(), 'Open shell', 'Back', 'Exit']) as choose, \
      patch.object(m, 'open_shell', return_value=0) as shell, patch.object(m, 'close_selected') as close:
      self.assertEqual(m.menu(self.proc), 0)
      shell.assert_called_once_with(self.row, self.proc)
      close.assert_not_called()
      self.assertEqual(choose.call_args_list[1].args[1][0], 'Back')
      self.assertIn('Attach existing harness', choose.call_args_list[1].args[1])

  def test_shell_picker_distinguishes_projects_and_retains_selected_identity(self):
    other = {**self.row, 'instance': '99999999-2222-4333-8444-555555555555',
      'container_id': 'b'*64, 'started_at': '2026-10-27',
      'project': {**self.row['project'], 'host_path': '/fixture/other-project'}}
    def pick(header, choices):
      if choices[0] == 'Exit':
        self.assertIn('/fixture/project', choices[-2])
        self.assertIn('2026-10-26', choices[-2])
        self.assertIn('/fixture/other-project', choices[-1])
        self.assertIn('2026-10-27', choices[-1])
        return choices[-1]
      self.assertEqual(choices, ['Back', 'Open shell'])
      return 'Open shell'
    with patch.object(m.sessions, 'inventory', return_value=[self.row, other]), \
      patch.object(m, 'choose') as choose, \
      patch.object(m, 'open_shell', return_value=0) as shell, patch.object(m, 'close_selected') as close:
      responses = iter([pick, pick, lambda *_: 'Back', lambda *_: 'Exit'])
      choose.side_effect = lambda header, choices: next(responses)(header, choices)
      self.assertEqual(m.menu(self.proc, shell_only=True), 0)
      shell.assert_called_once_with(other, self.proc)
      close.assert_not_called()

  def test_shell_picker_cancellation_never_executes(self):
    for response in (None, 'Exit'):
      with self.subTest(response=response), patch.object(m, 'choose', return_value=response), \
        patch.object(m, 'open_shell') as shell, patch.object(m, 'close_selected') as close:
        self.assertEqual(m.menu(self.proc, shell_only=True), 0)
        shell.assert_not_called(); close.assert_not_called()

  def test_menu_shell_failure_does_not_retry_or_close(self):
    with patch.object(m, 'choose', side_effect=[self.label(), 'Open shell', 'Back', 'Exit']), \
      patch.object(m, 'open_shell', return_value=127) as shell, patch.object(m, 'close_selected') as close, \
      patch('builtins.input', return_value=''):
      self.assertEqual(m.menu(self.proc, shell_only=True), 0)
      shell.assert_called_once_with(self.row, self.proc)
      close.assert_not_called()

  def test_shell_command_help_routes_without_execution(self):
    env = {**os.environ, 'OMARCHY_PATH': str(ROOT), 'OMARCHY_LANGUAGE_FILE': str(ROOT/'test/.no-language')}
    result = subprocess.run([str(ROOT/'bin/omarchy'), 'agent', 'shell', '--help'],
      env=env, capture_output=True, text=True, timeout=10)
    self.assertEqual(result.returncode, 0, result.stderr)
    self.assertIn('omarchy-agent-shell', result.stdout)
    self.assertIn('[instance-uuid-or-prefix] [--check]', result.stdout)

  def test_unknown_menu_result_is_rejected(self):
    with patch.object(m.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, stdout='untrusted\n')):
      with self.assertRaises(m.Unavailable): m.choose('fixture', ['Exit'])


if __name__ == '__main__':
  unittest.main()
