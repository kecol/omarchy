import importlib.util
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(os.environ['ROOT'])
SECRET='PRIVATE-ARGUMENT-NOT-FOR-GUARD-OUTPUT'


def installed_node(command=None):
  # Resolve public installed executables by metadata only. Running a mise shim
  # here could load caller config or lazily install after HOME becomes scratch.
  # CI prepares Node serially in its disposable guest and hands off its actual
  # executable. An invalid explicit value must never fall back to PATH/aliases.
  explicit = os.environ.get('OMARCHY_TEST_NODE_BINARY') if command is None else None
  if explicit is not None:
    if not explicit or not Path(explicit).is_absolute():
      raise RuntimeError('OMARCHY_TEST_NODE_BINARY must be an absolute installed Node ELF; no shim was executed or tool installed')
    command = explicit
  else:
    command = command or shutil.which('node')
  if not command:
    raise RuntimeError('Expose a preinstalled Node ELF on PATH; no tool was installed')
  selected = Path(command)
  candidates = [selected]
  if explicit is None and selected.parent.name == 'shims':
    # Omarchy declares node=latest. This existing alias needs no mise lookup.
    candidates.append(selected.parent.parent/'installs/node/latest/bin/node')
  for candidate in candidates:
    path = candidate.resolve()
    if path.name != 'node' or not os.access(path, os.X_OK):
      continue
    try:
      with path.open('rb') as stream:
        if stream.read(4) == b'\x7fELF':
          return path
    except OSError:
      continue
  raise RuntimeError(f'No preinstalled Node ELF found for {selected}; no shim was executed or tool installed')


@unittest.skipIf(os.getuid()==0,'guard management deliberately rejects root')
class GuardsTests(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.node = installed_node()
    print(f'Guard fixture uses installed Node: {cls.node}', file=sys.stderr)

  def setUp(self):
    temp=tempfile.TemporaryDirectory(prefix='agent guards ');self.addCleanup(temp.cleanup)
    self.root=Path(temp.name);self.home=self.root/'home';self.home.mkdir()
    self.bin=self.root/'tools';self.bin.mkdir();self.calls=self.root/'calls'
    # Keep the selected real Node available after HOME/PATH become scratch.
    (self.bin/'node').symlink_to(self.node)
    self.env={'HOME':str(self.home),'PATH':str(self.bin)+':'+str(ROOT/'bin')+':/usr/bin:/bin','OMARCHY_PATH':str(ROOT),'ROOT':str(ROOT),'CALLS':str(self.calls),'TERM':'dumb'}
    self.state=self.home/'.local/share/omarchy/agents/command-guards'
    self.mode=self.home/'.config/omarchy/agents/mode';self.mode.parent.mkdir(parents=True)
    self.mode.write_text('container\n')
    self.tool('pi')

  def tool(self,name):
    path=self.bin/name
    path.write_text('#!/bin/bash\nprintf "%s\\0" "$@" > "$CALLS"\nprintf "host tool\\n"\nexit "${TOOL_EXIT:-0}"\n')
    path.chmod(0o755)

  def command(self,args,code=0,**env):
    result=subprocess.run(args,env={**self.env,**env},capture_output=True,timeout=12)
    self.assertEqual(result.returncode,code,result.stderr.decode(errors='replace'))
    return result

  def ctl(self,*args,code=0,**env):
    return self.command([str(ROOT/'bin/omarchy-agent-guards'),*args],code,**env)

  def enable(self):
    self.ctl('enable')
    self.env['PATH']=str(self.state/'bin')+':'+self.env['PATH']

  def test_node_selection_uses_installed_alias_without_executing_mise(self):
    data = self.root/'mise-data';shims = data/'shims';shims.mkdir(parents=True)
    mise = self.root/'mise';mise.write_text('#!/bin/bash\nexit 99\n');mise.chmod(0o755)
    shim = shims/'node';shim.symlink_to(mise)
    binary = data/'installs/node/latest/bin/node';binary.parent.mkdir(parents=True)
    binary.symlink_to(self.node)
    with patch.object(subprocess, 'run') as run:
      self.assertEqual(installed_node(str(shim)), self.node)
      run.assert_not_called()

  def test_node_selection_refuses_shim_without_installed_node(self):
    shims = self.root/'uninstalled/shims';shims.mkdir(parents=True)
    mise = self.root/'mise';mise.write_text('#!/bin/bash\nexit 99\n');mise.chmod(0o755)
    shim = shims/'node';shim.symlink_to(mise)
    with patch.object(subprocess, 'run') as run:
      with self.assertRaisesRegex(RuntimeError, 'no shim was executed'):
        installed_node(str(shim))
      run.assert_not_called()

  def test_node_selection_uses_explicit_elf_without_resolving_cold_wrapper(self):
    wrapper = self.root/'mise-data/command-wrappers/bin/node';wrapper.parent.mkdir(parents=True)
    wrapper.write_text('#!/bin/bash\nexit 99\n');wrapper.chmod(0o755)
    with patch.dict(os.environ, {'OMARCHY_TEST_NODE_BINARY': str(self.node)}):
      with patch.object(shutil, 'which', return_value=str(wrapper)) as which, patch.object(subprocess, 'run') as run:
        self.assertEqual(installed_node(), self.node)
        which.assert_not_called();run.assert_not_called()

  def test_node_selection_rejects_invalid_explicit_binary_without_fallback(self):
    data = self.root/'mise-data';shims = data/'shims';shims.mkdir(parents=True)
    shim = shims/'node';shim.write_text('#!/bin/bash\nexit 99\n');shim.chmod(0o755)
    alias = data/'installs/node/latest/bin/node';alias.parent.mkdir(parents=True);alias.symlink_to(self.node)
    for value in ('', 'node', str(self.root/'absent/node'), str(shim)):
      with self.subTest(value=value), patch.dict(os.environ, {'OMARCHY_TEST_NODE_BINARY': value}):
        with patch.object(shutil, 'which', return_value=str(self.node)) as which, patch.object(subprocess, 'run') as run:
          with self.assertRaisesRegex(RuntimeError, 'no shim was executed'):
            installed_node()
          which.assert_not_called();run.assert_not_called()

  def test_ci_guest_prepares_node_before_tests_and_records_failures(self):
    # Execute the real guest payload, never its QEMU/SSH controller. The inert
    # Node and suite endpoints reveal ordering, handoff and failure propagation.
    source = (ROOT/'test/ci-vm').read_text()
    start = source.index('\ncommand=') + 1
    assignment = source[start:source.index('\nssh_vm "systemd-run', start)]
    for name, setup_exit, suite_exit, binary, expected in (
      ('ready', 0, 0, str(self.node), 0),
      ('setup-fails', 17, 0, str(self.node), 17),
      ('suite-fails', 0, 23, str(self.node), 23),
      ('empty-path', 0, 0, '', 1),
      ('relative-path', 0, 0, 'node', 1),
    ):
      with self.subTest(name=name):
        guest = self.root/('CI guest ' + name);checkout = guest/'src/omarchy'
        binaries = checkout/'bin';binaries.mkdir(parents=True)
        tests = checkout/'test';tests.mkdir()
        node = binaries/'node'
        node.write_text('#!/bin/bash\nprintf "node:%s:%s\\n" "$PWD" "$*" >>"$CALLS"\nif (( SETUP_EXIT != 0 )); then exit "$SETUP_EXIT"; fi\nprintf "%s\\n" "$NODE_BINARY"\n')
        node.chmod(0o755)
        suite = tests/'all'
        suite.write_text('#!/bin/bash\nprintf "suite:%s\\n" "${OMARCHY_TEST_NODE_BINARY-unset}" >>"$CALLS"\nexit "$SUITE_EXIT"\n')
        suite.chmod(0o755)
        calls = guest/'calls'
        result = subprocess.run(['/bin/bash', '-c', assignment + '\n/bin/bash -c "$command"'], env={
          'HOME': str(guest), 'PATH': '/usr/bin:/bin', 'CALLS': str(calls),
          'SETUP_EXIT': str(setup_exit), 'SUITE_EXIT': str(suite_exit), 'NODE_BINARY': binary,
        }, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((guest/'rc').read_text(), str(expected) + '\n')
        self.assertFalse((guest/'rc.next').exists())
        self.assertTrue((guest/'started').is_file())
        self.assertTrue((guest/'run.log').is_file())
        expected_calls = [f'node:{guest}:-p process.execPath']
        if not setup_exit and binary == str(self.node):
          expected_calls.append(f'suite:{self.node}')
        self.assertEqual(calls.read_text().splitlines(), expected_calls)

  def test_blocks_bare_pi_without_running_or_echoing_arguments(self):
    self.enable();before=self.mode.read_bytes()
    result=self.command([str(self.state/'bin/pi'),SECRET,'$(touch unwanted)'],126)
    self.assertIn(b'--inline --container --agent pi',result.stderr)
    self.assertNotIn(SECRET.encode(),result.stdout+result.stderr)
    self.assertFalse(self.calls.exists());self.assertEqual(self.mode.read_bytes(),before)
    self.assertTrue((self.bin/'pi').read_text().startswith('#!/bin/bash'))

  def test_host_mode_preserves_arguments_exit_and_current_directory(self):
    self.enable();self.mode.write_text('host\n')
    self.command([str(self.state/'bin/pi'),'two words',SECRET],17,TOOL_EXIT='17')
    self.assertEqual(self.calls.read_bytes(),b'two words\0'+SECRET.encode()+b'\0')

  def test_alias_paths_to_guard_directory_do_not_recurse_on_host_delegation(self):
    self.enable();self.mode.write_text('host\n')
    alias=self.root/'guard alias';alias.symlink_to(self.state/'bin')
    self.env['PATH']=str(alias)+':'+self.env['PATH']
    self.command([str(alias/'pi'),'safe argument'])
    self.assertEqual(self.calls.read_bytes(),b'safe argument\0')
    resolved=self.command([str(ROOT/'bin/omarchy-agent-host-command'),'pi'])
    self.assertEqual(resolved.stdout.decode().strip(),str(self.bin/'pi'))
    (self.bin/'pi').unlink()
    self.command([str(ROOT/'bin/omarchy-agent-host-command'),'pi'],1)

  def test_file_alias_back_to_guard_fails_without_recursion_or_false_installation(self):
    self.enable();self.mode.write_text('host\n')
    (self.bin/'pi').unlink();(self.bin/'pi').symlink_to(self.state/'bin/pi')
    result=self.command([str(self.state/'bin/pi')],126)
    self.assertIn(b'guard alias',result.stderr)
    self.command([str(ROOT/'bin/omarchy-agent-host-command'),'pi'],1)
    self.assertFalse(self.calls.exists())

  def test_disable_immediately_unblocks_existing_path_and_uninstall_removes_only_guards(self):
    self.enable();self.ctl('disable')
    self.command([str(self.state/'bin/pi'),'--version'])
    self.assertEqual(self.calls.read_bytes(),b'--version\0')
    self.ctl('uninstall');self.assertFalse((self.state/'bin').exists());self.assertTrue((self.bin/'pi').exists())

  def test_bad_mode_fifo_dangling_and_missing_state_fail_closed(self):
    self.enable()
    for text in ('invalid\n','container\0',''):
      self.mode.write_text(text)
      self.command([str(self.state/'bin/pi'),SECRET],126)
    self.mode.unlink();os.mkfifo(self.mode)
    self.command([str(self.state/'bin/pi')],126)
    self.mode.unlink();self.mode.symlink_to(self.root/'absent')
    self.command([str(self.state/'bin/pi')],126)
    (self.state/'state.json').unlink()
    self.command([str(self.state/'bin/pi')],126)
    self.ctl('status',code=126)
    self.assertFalse(self.calls.exists())

  def test_absent_mode_is_host_and_guard_disable_does_not_need_valid_mode(self):
    self.enable();self.mode.unlink()
    self.command([str(self.state/'bin/pi')])
    self.mode.write_text('broken')
    self.ctl('disable');self.command([str(self.state/'bin/pi')])

  def test_explicit_host_escape_does_not_change_mode(self):
    self.enable()
    self.ctl('host','--','pi',SECRET)
    self.assertEqual(self.calls.read_bytes(),SECRET.encode()+b'\0')
    self.assertEqual(self.mode.read_text(),'container\n')

  def test_public_inline_and_new_terminal_host_overrides_bypass_guards(self):
    self.enable()
    self.command([str(ROOT/'bin/omarchy-agent'),'--inline','--host','--agent=pi'])
    self.assertTrue(self.calls.exists());self.calls.unlink()
    # A fixture terminal reintroduces the guarded PATH like a terminal service.
    terminal=self.bin/'omarchy-launch-tui'
    terminal.write_text('#!/bin/bash\nexport PATH="$GUARDS_DIR:$PATH"\nshift\nexec "$@"\n');terminal.chmod(0o755)
    self.command([str(ROOT/'bin/omarchy-agent'),'--host','--agent=pi'],GUARDS_DIR=str(self.state/'bin'))
    self.assertTrue(self.calls.exists());self.assertEqual(self.mode.read_text(),'container\n')

  def test_account_login_keeps_explicit_host_maintenance_with_offline_stubs(self):
    cli=self.bin/'claude'
    cli.write_text('#!/bin/bash\nprintf "%s\\0" "$@" > "$CALLS"\ntouch "$SIGNED_IN"\n');cli.chmod(0o755)
    state=self.bin/'omarchy-agent-account-state'
    state.write_text('#!/bin/bash\nif [[ -e $SIGNED_IN ]]; then printf \'[{"accounts":[{"primary":true,"signedIn":true}]}]\\n\'; else printf \'[{"accounts":[]}]\\n\'; fi\n');state.chmod(0o755)
    usage=self.bin/'omarchy-agent-usage-update';usage.write_text('#!/bin/bash\nexit 0\n');usage.chmod(0o755)
    self.enable()
    self.command([str(ROOT/'bin/omarchy-agent-account-add'),'claude'],SIGNED_IN=str(self.root/'signed-in'))
    self.assertEqual(self.calls.read_bytes(),b'auth\0login\0')
    self.assertEqual(self.mode.read_text(),'container\n')

  def test_installed_only_resolution_does_not_report_guard_as_installation(self):
    self.enable()
    result=self.command([str(ROOT/'bin/omarchy-agent-host-command'),'pi'])
    self.assertEqual(result.stdout.decode().strip(),str(self.bin/'pi'))
    (self.bin/'pi').unlink()
    self.command([str(ROOT/'bin/omarchy-agent-host-command'),'pi'],1)

  def test_future_definitions_aliases_and_explicit_registrations_need_no_agent_allowlist(self):
    for name in ('future-agent','futurecli','later-agent'):self.tool(name)
    definitions=self.home/'.config/omarchy/agents';definitions.mkdir(exist_ok=True)
    (definitions/'future-agent.json').write_text(json.dumps({'name':'future-agent','harness':'future-harness','runtime':'podman','command':['future-agent'],'guardCommands':['future-agent','futurecli']}))
    self.enable()
    for name in ('future-agent','futurecli'):
      result=self.command([str(self.state/'bin'/name)],126)
      self.assertIn(b'No supported container launch',result.stderr)
      self.assertNotIn(b'--agent future-agent',result.stderr)
    self.ctl('register','later-agent');self.ctl('sync')
    self.assertTrue((self.state/'bin/later-agent').is_file())
    self.assertFalse(self.calls.exists())

  def test_future_catalog_entry_is_discovered_without_definition_or_registration(self):
    self.tool('future-catalog')
    with patch.dict(os.environ,self.env,clear=True):
      spec=importlib.util.spec_from_file_location('guards_fixture',ROOT/'default/agents/command-guards.py')
      module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
      result=subprocess.CompletedProcess(['node'],0,json.dumps(['pi','future-catalog']).encode(),b'')
      with patch.object(module.subprocess,'run',return_value=result):
        self.assertEqual(module.discover(self.state,{})['future-catalog'],'future-catalog')
    self.assertFalse(self.calls.exists())

  def test_definition_runner_is_not_guarded_and_explicit_generic_alias_is_rejected(self):
    self.tool('future-runner')
    directory=self.home/'.config/omarchy/agents'
    definition={'name':'future-runner','harness':'future','runtime':'podman','command':['python3','/app/main.py']}
    path=directory/'future-runner.json';path.write_text(json.dumps(definition))
    self.enable();self.assertFalse((self.state/'bin/python3').exists())
    definition['guardCommands']=['bash'];path.write_text(json.dumps(definition))
    self.ctl('sync',code=126)

  def test_posix_environment_bootstrap_prepends_opt_in_guards(self):
    self.enable()
    result=self.command(['/bin/sh','-c','. "$ROOT/default/bash/env-bootstrap"; printf "%s\\n" "${PATH%%:*}"'])
    self.assertEqual(result.stdout.decode().strip(),str(self.state/'bin'))

  def test_general_tools_and_management_commands_cannot_be_registered(self):
    for name in ('bash','env','node','python3','mise','omarchy-agent','git','bad/name','pi;touch'):
      self.ctl('register',name,code=126)

  def test_foreign_or_modified_guard_files_are_never_overwritten(self):
    self.enable();path=self.state/'bin/pi';path.write_text('user content')
    self.ctl('sync',code=126);self.ctl('uninstall',code=126)
    self.assertEqual(path.read_text(),'user content')
    self.ctl('disable')

  def test_foreign_bin_entries_block_sync_before_installing_anything(self):
    self.enable();path=self.state/'bin/foreign';path.write_text('foreign')
    self.tool('codex');self.ctl('sync',code=126)
    self.assertFalse((self.state/'bin/codex').exists())
    self.assertEqual(path.read_text(),'foreign')

  def test_status_reports_path_precedence_without_creating_state(self):
    result=self.ctl('status');self.assertFalse(self.state.exists())
    self.assertFalse(json.loads(result.stdout)['enabled'])
    self.enable();self.assertTrue(json.loads(self.ctl('status').stdout)['first_on_path']['pi'])
    self.env['PATH']=str(self.bin)+':'+self.env['PATH']
    self.assertFalse(json.loads(self.ctl('status').stdout)['first_on_path']['pi'])

  def test_guard_metadata_symlink_and_fifo_do_not_block_or_launch(self):
    self.enable();path=self.state/'state.json';path.unlink();os.mkfifo(path)
    self.command([str(self.state/'bin/pi')],126)
    path.unlink();path.symlink_to(self.root/'missing')
    self.command([str(self.state/'bin/pi')],126)
    self.assertFalse(self.calls.exists())

  def test_shell_hook_restores_precedence_after_mise_without_processes(self):
    self.enable()
    script='''source "$ROOT/default/agents/guard-path.sh"
PROMPT_COMMAND=(_mise_hook)
_mise_hook() { export PATH="$TOOLS:$PATH"; }
omarchy_agent_guard_init
for hook in "${PROMPT_COMMAND[@]}"; do eval "$hook"; done
printf '%s\\n' "${PATH%%:*}"
unset PROMPT_COMMAND
PROMPT_COMMAND=_mise_hook
omarchy_agent_guard_init
eval "$PROMPT_COMMAND"
printf '%s\\n' "${PATH%%:*}"
'''
    result=self.command(['/bin/bash','--noprofile','--norc','-ic',script],TOOLS=str(self.bin))
    self.assertEqual(result.stdout.decode().splitlines(),[str(self.state/'bin')]*2)


if __name__=='__main__':unittest.main()
