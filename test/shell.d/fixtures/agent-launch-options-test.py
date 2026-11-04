import json
import os
import fcntl
from pathlib import Path
import pty
import select
import struct
import termios
import time
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(os.environ['ROOT'])


class LauncherTests(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    self.base = Path(self.temp.name)
    self.home, self.bin = self.base/'home', self.base/'bin'
    self.home.mkdir()
    self.bin.mkdir()
    self.project = self.home/'project $(touch INJECTED); "quoted"'
    self.project.mkdir()
    for name in ('omarchy-agent', 'omarchy-agent-exec', 'omarchy-agent-host-command', 'omarchy-cmd-present'):
      shutil.copy2(ROOT/'bin'/name, self.bin/name)
    self.log = self.base/'calls'
    self.env = dict(HOME=str(self.home), PATH=str(self.bin)+':/usr/bin:/bin', OMARCHY_PATH=str(ROOT), CALLS=str(self.log), MISE_LOG=str(self.base/'mise-log'))
    logger = '#!/usr/bin/python3\nimport json,os,sys\nwith open(os.environ["CALLS"],"a") as f: f.write(json.dumps({"args":sys.argv,"cwd":os.getcwd()})+"\\n")\n'
    for name in ('pi', 'codex', 'omarchy-agent-run-podman'):
      self.program(name, logger)
    self.program('omarchy-default-agent', '#!/bin/bash\necho "${DEFAULT_AGENT-codex}"\n')
    self.program('omarchy-agent-mode', '#!/bin/bash\necho "${MODE:-host}"\nexit "${MODE_STATUS:-0}"\n')
    self.program('omarchy-cmd-missing', '#!/bin/bash\n! command -v "$1" >/dev/null\n')
    self.program('omarchy-pkg-present', '#!/bin/bash\nexit 1\n')
    self.program('omarchy-agent-account-home', '#!/bin/bash\necho account-query >>"$CALLS"\n')
    self.program('omarchy-launch-tui', '#!/bin/bash\nshift\ncd "$HOME"\nexec "$@"\n')

  def program(self, name, text, directory=None):
    path = (directory or self.bin)/name
    path.write_text(text)
    path.chmod(0o755)
    return path

  def launch(self, *args, **env):
    return subprocess.run([str(self.bin/'omarchy-agent'), *args], env={**self.env, **env}, capture_output=True, text=True)

  def calls(self):
    return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

  def picker_tools(self):
    # Synthetic catalog/UI adapters for launcher control flow. Real gum has a
    # separate private-PTY qualification; these stubs are not visual evidence.
    self.picker_log = self.base/'picker-calls'
    self.program('node', '#!/usr/bin/python3\nimport os,json\nassert "NODE_OPTIONS" not in os.environ\nprint(json.dumps([{"name":"codex","label":"Codex"},{"name":"pi","label":"Pi"},{"name":"claude","label":"Claude Code"}]))\n')
    self.program('gum', '#!/usr/bin/python3\nimport json,os,sys\nwith open(os.environ["PICKER_CALLS"],"a") as f:f.write(json.dumps(sys.argv[1:])+"\\n")\nprint(os.environ.get("PICKER_CHOICE","Cancel"))\nsys.exit(int(os.environ.get("PICKER_STATUS","0")))\n')
    self.env['PICKER_CALLS'] = str(self.picker_log)

  def launch_tty(self, *args, **extra):
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, 100, 0, 0))
    process = subprocess.Popen([str(self.bin/'omarchy-agent'), *args], env={**self.env, 'TERM':'xterm-256color', **extra}, cwd=self.project, stdin=slave, stdout=slave, stderr=slave)
    os.close(slave)
    output = bytearray()
    try:
      deadline = time.monotonic()+15
      while time.monotonic() < deadline:
        if select.select([master], [], [], 0.1)[0]:
          try:
            data = os.read(master, 65536)
          except OSError:
            break
          if not data:
            break
          output.extend(data)
        elif process.poll() is not None:
          break
      code = process.wait(timeout=2)
    finally:
      os.close(master)
    return subprocess.CompletedProcess(args, code, output.decode(errors='replace'), '')

  def test_interactive_cancel_never_launches_or_changes_defaults(self):
    self.picker_tools()
    result = self.launch_tty('--inline', MODE='container', NODE_OPTIONS='--synthetic-must-not-run')
    self.assertEqual(result.returncode, 0, result.stdout)
    self.assertFalse(self.log.exists(), 'cancelled picker started an agent')
    self.assertFalse((self.home/'.config').exists())
    self.assertEqual(len(self.picker_log.read_text().splitlines()), 1)

  def test_interactive_choice_and_override_are_one_launch_only(self):
    self.picker_tools()
    result = self.launch_tty('--inline', '--container', MODE='host', PICKER_CHOICE='Pi')
    self.assertEqual(result.returncode, 0, result.stdout)
    self.assertIn('pi', self.calls()[0]['args'])
    self.assertFalse((self.home/'.config').exists())
    options = json.loads(self.picker_log.read_text().splitlines()[0])
    self.assertIn('--header=Mode: Container (override)\nDefault agent: Codex\nChoose for this launch only', options)
    self.assertIn('--selected=Codex (default)', options)

  def test_explicit_agent_and_programmatic_tty_calls_bypass_picker(self):
    self.picker_tools()
    for args in [('--inline','--agent','pi'), ('--inline','--agent-internal','pi'), ('--inline','--prompt','literal task'), ('--check',), ('--inline',)]:
      extra = {'MODE':'container'}
      if args == ('--inline',):
        extra['OMARCHY_AGENT_MANAGED'] = 'true'
      result = self.launch_tty(*args, **extra)
      self.assertEqual(result.returncode, 0, result.stdout)
    self.assertFalse(self.picker_log.exists())

  def test_host_picker_uses_installed_only_without_host_account_lookup(self):
    self.picker_tools()
    result = self.launch_tty('--inline', MODE='host', PICKER_CHOICE='Pi')
    self.assertEqual(result.returncode, 0, result.stdout)
    self.assertEqual(self.calls()[0]['args'][0], str(self.bin/'pi'))
    self.assertFalse((self.home/'.config').exists())
    self.assertNotIn('account-query', self.log.read_text())

  def test_oneshot_and_resume_tty_calls_bypass_picker(self):
    self.picker_tools()
    for args in [('--oneshot','--prompt','literal task'), ('--inline','--resume-session')]:
      result = self.launch_tty(*args, MODE='container', DEFAULT_AGENT='pi')
      self.assertEqual(result.returncode, 0, result.stdout)
    self.assertFalse(self.picker_log.exists())

  def test_noninteractive_pick_and_prompt_do_not_prompt(self):
    self.picker_tools()
    for args in [('--inline',), ('--inline','--pick'), ('--inline','--prompt','literal task')]:
      result = self.launch(*args, MODE='container')
      self.assertEqual(result.returncode, 0, result.stderr)
    result = self.launch('--pick', DEFAULT_AGENT='')
    self.assertNotEqual(result.returncode, 0)
    self.assertFalse(self.picker_log.exists())

  def test_picker_refusals_do_not_fall_back_or_read_accounts(self):
    self.picker_tools()
    for extra in [dict(MODE='invalid'), dict(MODE='host',MODE_STATUS='1'), dict(MODE='container',PICKER_STATUS='2'), dict(MODE='container',PICKER_CHOICE='invalid output')]:
      result = self.launch_tty('--inline', **extra)
      self.assertNotEqual(result.returncode, 0, result.stdout)
    self.assertFalse(self.log.exists())
    self.assertFalse((self.home/'.config').exists())

  def test_no_saved_default_cancel_and_explicit_pick_do_not_save(self):
    self.picker_tools()
    result = self.launch_tty('--inline','--pick', MODE='container', DEFAULT_AGENT='')
    self.assertEqual(result.returncode, 0, result.stdout)
    options = json.loads(self.picker_log.read_text().splitlines()[0])
    self.assertIn('--selected=Cancel', options)
    self.assertEqual(options[options.index('--')+1], 'Cancel')
    self.assertFalse(self.log.exists())
    self.assertFalse((self.home/'.config').exists())

  def test_host_check_resolves_without_running_agent_or_reading_account_state(self):
    result = self.launch('--check', '--agent', 'pi', '--host')
    self.assertEqual(result.returncode, 0, result.stderr)
    self.assertEqual(result.stdout.strip(), str(self.bin/'pi'))
    self.assertFalse(self.log.exists())
    self.assertFalse((self.home/'.config').exists())

  def test_container_check_does_not_start_runtime_or_resolve_host_install(self):
    (self.bin/'pi').unlink()
    result = self.launch('--check', '--agent', 'pi', '--container')
    self.assertEqual(result.returncode, 0, result.stderr)
    self.assertFalse(self.log.exists())
    result = self.launch('--check', '--agent', 'codex', '--container')
    self.assertEqual(result.returncode, 0, result.stderr)
    result = self.launch('--check', '--agent', 'hermes', '--container')
    self.assertNotEqual(result.returncode, 0)
    self.assertFalse(self.log.exists())

  def test_explicit_project_survives_terminal_cwd_reset_and_shell_characters(self):
    result = self.launch('--agent', 'pi', '--directory', str(self.project), '--host', '--installed-only')
    self.assertEqual(result.returncode, 0, result.stderr)
    calls = self.calls()
    self.assertEqual(calls[0]['cwd'], str(self.project))
    self.assertEqual(calls[0]['args'][0], str(self.bin/'pi'))
    self.assertFalse((self.project/'INJECTED').exists())
    self.assertFalse((self.home/'.config').exists())

  def test_public_agent_selector_preserves_legacy_internal_alias(self):
    for flag in ('--agent', '--agent-internal'):
      result = self.launch('--inline', flag, 'pi', '--directory', str(self.project), '--host')
      self.assertEqual(result.returncode, 0, result.stderr)
    self.assertEqual(len(self.calls()), 2)

  def test_equals_flag_forms_and_empty_values(self):
    result = self.launch('--inline', '--agent=pi', '--directory='+str(self.project), '--host', '--installed-only')
    self.assertEqual(result.returncode, 0, result.stderr)
    self.assertEqual(self.calls()[0]['cwd'], str(self.project))
    for flag in ('--agent=', '--directory='):
      result = self.launch('--inline', '--agent', 'pi', '--host', flag)
      self.assertNotEqual(result.returncode, 0)
    self.assertEqual(len(self.calls()), 1)

  def test_missing_directory_and_invalid_mode_fail_closed(self):
    for args, env in [(['--inline', '--agent', 'pi', '--directory', '/no-such-project', '--host'], {}), (['--inline', '--agent', 'pi'], {'MODE':'invalid'}), (['--inline', '--agent', 'pi'], {'MODE':'host', 'MODE_STATUS':'1'})]:
      result = self.launch(*args, **env)
      self.assertNotEqual(result.returncode, 0)
    self.assertFalse(self.log.exists())

  def test_container_launch_does_not_forward_host_account_pin(self):
    definitions = self.home/'.config/omarchy/agents'
    definitions.mkdir(parents=True)
    (definitions/'codex.json').write_text(json.dumps(dict(name='codex', harness='codex', runtime='podman', command=['codex'])))
    result = self.launch('--inline', '--agent', 'codex', '--directory', str(self.project), '--container')
    self.assertEqual(result.returncode, 0, result.stderr)
    args = self.calls()[0]['args']
    self.assertIn('codex', args)
    self.assertNotIn('env', args)
    self.assertNotIn('account-query', self.log.read_text())

  def test_installed_only_preserves_hermes_prompt_and_skips_openclaw_setup(self):
    for name in ('hermes', 'openclaw'):
      self.program(name, (self.bin/'pi').read_text())
    self.program('omarchy-launch-openclaw', '#!/bin/bash\necho unexpected-setup >>"$CALLS"\nexit 99\n')
    result = self.launch('--inline', '--agent', 'hermes', '--host', '--installed-only', '--prompt', 'test task')
    self.assertEqual(result.returncode, 0, result.stderr)
    self.assertIn('--query=test task', self.calls()[0]['args'])
    result = self.launch('--inline', '--agent', 'openclaw', '--host', '--installed-only')
    self.assertEqual(result.returncode, 0, result.stderr)
    self.assertEqual(self.calls()[1]['args'][1:], ['tui'])
    self.assertNotIn('unexpected-setup', self.log.read_text())

  def test_installed_only_preserves_new_bash_and_env_wrappers(self):
    self.program('amp', '#!/usr/bin/python3\nimport json,os,sys\nwith open(os.environ["CALLS"],"a") as f: f.write(json.dumps({"args":sys.argv,"stdin":sys.stdin.read()})+"\\n")\n')
    self.program('dsh', (self.bin/'pi').read_text())
    prompt = 'literal $(touch SHOULD_NOT_EXIST); --option'
    result = self.launch('--inline', '--agent', 'amp', '--host', '--installed-only', '--directory', str(self.project), '--prompt', prompt)
    self.assertEqual(result.returncode, 0, result.stderr)
    self.assertEqual(self.calls()[0]['args'], [str(self.bin/'amp'), '--dangerously-allow-all'])
    self.assertEqual(self.calls()[0]['stdin'], prompt+'\n')
    result = self.launch('--inline', '--agent', 'dsh', '--host', '--installed-only')
    self.assertEqual(result.returncode, 0, result.stderr)
    self.assertEqual(self.calls()[1]['args'], [str(self.bin/'dsh'), 'web'])
    self.assertFalse((self.project/'SHOULD_NOT_EXIST').exists())

  def test_unsupported_container_prompt_does_not_touch_host_clipboard(self):
    self.program('wl-copy', '#!/bin/bash\necho UNEXPECTED-CLIPBOARD >>"$CALLS"\n')
    self.program('omarchy-notification-send', '#!/bin/bash\necho UNEXPECTED-NOTIFICATION >>"$CALLS"\n')
    result = self.launch('--inline', '--agent', 'dsh', '--container', '--prompt', 'private fixture task')
    self.assertNotEqual(result.returncode, 0)
    self.assertFalse(self.log.exists())

  def test_modern_legacy_wrapper_is_resolved_offline_not_executed(self):
    local = self.home/'.local/bin'
    local.mkdir(parents=True)
    self.program('pi', '#!/bin/bash\necho LAZY-SHIM-WAS-EXECUTED >>"$CALLS"\nmise x pi -- pi "$@"\n', local)
    self.program('mise', '#!/bin/bash\nprintf "%s %s\\n" "$MISE_OFFLINE" "$*" >>"$MISE_LOG"\nprintf "%s\\n" "$RESOLVED_BINARY"\n')
    result = self.launch('--inline', '--agent', 'pi', '--host', '--installed-only', PATH=str(local)+':'+self.env['PATH'], RESOLVED_BINARY=str(self.bin/'pi'))
    self.assertEqual(result.returncode, 0, result.stderr)
    self.assertNotIn('LAZY', self.log.read_text())
    self.assertEqual(len(self.calls()), 1)
    self.assertIn('true -C '+str(self.home)+' which pi', (self.base/'mise-log').read_text())

  def test_lazy_shim_is_resolved_offline_and_never_executed_or_installed(self):
    shims = self.base/'mise/shims'
    shims.mkdir(parents=True)
    self.program('pi', '#!/bin/bash\necho LAZY-SHIM-WAS-EXECUTED >>"$CALLS"\nexit 99\n', shims)
    self.program('mise', '#!/bin/bash\nprintf "%s %s\\n" "$MISE_OFFLINE" "$*" >>"$MISE_LOG"\n[[ -n ${RESOLVED_BINARY:-} ]] || exit 1\nprintf "%s\\n" "$RESOLVED_BINARY"\n')
    path = str(shims)+':'+self.env['PATH']
    result = self.launch('--inline', '--agent', 'pi', '--host', '--installed-only', PATH=path, RESOLVED_BINARY=str(self.bin/'pi'))
    self.assertEqual(result.returncode, 0, result.stderr)
    self.assertEqual(len(self.calls()), 1)
    self.assertNotIn('LAZY', self.log.read_text())
    self.assertIn('true -C '+str(self.home)+' which pi', (self.base/'mise-log').read_text())
    result = self.launch('--inline', '--agent', 'pi', '--host', '--installed-only', PATH=path)
    self.assertNotEqual(result.returncode, 0)
    self.assertEqual(len(self.calls()), 1)


if __name__ == '__main__':
  unittest.main(verbosity=2)
