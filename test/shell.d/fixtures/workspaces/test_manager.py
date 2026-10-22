import base64
import copy
import importlib.util
import io
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(os.environ['ROOT'])
spec = importlib.util.spec_from_file_location('workspace_manager', ROOT/'default/workspaces/manager.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def completed(stdout='', returncode=0):
  return subprocess.CompletedProcess([], returncode, stdout=stdout)


def fixture(directory, identity='a'*32):
  data = dict(id=identity, name='one', version=1, mode='clone', directory=str(directory/'repo'), source='/source', image_id='sha256:test')
  container, volume = m.identifiers(data)
  config = {
    'Image': data['image_id'], 'State': {'Running': True},
    'Config': {'User': f'{os.getuid()}:{os.getgid()}', 'Labels': {m.LABEL: identity},
         'Env': ['HOME=/home/workspace', 'CODEX_HOME=/home/workspace/.codex'],
         'CreateCommand': ['podman', 'run', '--cap-drop=ALL', '--userns=keep-id', '--network=pasta:--no-map-gw', '--cgroups=enabled', '--cgroupns=private', '--env-host=false', '--http-proxy=false']},
    'HostConfig': {'Privileged': False, 'ReadonlyRootfs': True, 'CapAdd': [], 'CapDrop': ['CAP_CHOWN', 'CAP_SETUID'],
           'SecurityOpt': ['no-new-privileges'], 'Devices': [], 'UsernsMode': 'private',
           'CgroupMode': 'private', 'Memory': m.MEMORY, 'MemorySwap': m.MEMORY, 'PidsLimit': m.PIDS,
           'NanoCpus': 2_000_000_000, 'NetworkMode': 'pasta',
           'Tmpfs': {'/tmp': 'rw,nosuid,nodev', '/run': 'rw,nosuid,nodev'},
           'PortBindings': {'2222/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '41000'}]}},
    'Mounts': [
      {'Type': 'bind', 'Source': data['directory'], 'Destination': '/workspace', 'RW': True},
      {'Type': 'volume', 'Name': volume, 'Destination': '/home/workspace', 'RW': True},
      {'Type': 'bind', 'Source': str(directory/'identity.pub'), 'Destination': '/etc/omarchy-workspace/authorized_keys', 'RW': False},
    ],
  }
  return data, config


class PolicyTests(unittest.TestCase):
  def setUp(self):
    for function in ['getuid', 'getgid']:
      mocked = patch.object(m.os, function, return_value=1000)
      mocked.start()
      self.addCleanup(mocked.stop)

  def test_normalized_podman_settings_pass(self):
    data, config = fixture(Path('/state/one'))
    m.audit(config, data, Path('/state/one'))

  def test_runtime_drift_fails_closed(self):
    data, good = fixture(Path('/state/one'))
    mutations = [
      lambda x: x['Config']['Labels'].clear(),
      lambda x: x.update(Image='different'),
      lambda x: x['Config'].update(User='0:0'),
      lambda x: x['HostConfig'].update(Privileged=True),
      lambda x: x['HostConfig'].update(ReadonlyRootfs=False),
      lambda x: x['HostConfig'].update(CapAdd=['CAP_SYS_ADMIN']),
      lambda x: x['Config']['CreateCommand'].remove('--cap-drop=ALL'),
      lambda x: x['HostConfig'].update(SecurityOpt=[]),
      lambda x: x['HostConfig'].update(UsernsMode='host'),
      lambda x: x['HostConfig'].update(CgroupMode='host'),
      lambda x: x['HostConfig'].update(PidMode='container:another-workspace'),
      lambda x: x['HostConfig'].update(IpcMode='container:another-workspace'),
      lambda x: x['HostConfig'].update(UTSMode='host'),
      lambda x: x['HostConfig'].update(Memory=0),
      lambda x: x['HostConfig'].update(MemorySwap=-1),
      lambda x: x['HostConfig'].update(NanoCpus=0),
      lambda x: x['HostConfig'].update(PidsLimit=0),
      lambda x: x['HostConfig'].update(NetworkMode='host'),
      lambda x: x['HostConfig']['PortBindings']['2222/tcp'][0].update(HostIp='0.0.0.0'),
      lambda x: x['HostConfig']['PortBindings'].update({'1455/tcp': []}),
      lambda x: x['Mounts'].append({'Type': 'bind', 'Source': '/run/podman/podman.sock', 'Destination': '/sock', 'RW': True}),
      lambda x: x['Mounts'][1].update(Name='another-workspace-home'),
      lambda x: x['Mounts'][2].update(RW=True),
      lambda x: x['Config']['Env'].append('SSH_AUTH_SOCK=/run/agent'),
      lambda x: x['Config']['Env'].append('OPENAI_API_KEY=not-a-real-key'),
    ]
    for mutate in mutations:
      with self.subTest(mutate=mutate):
        config = copy.deepcopy(good)
        mutate(config)
        with self.assertRaises(RuntimeError):
          m.audit(config, data, Path('/state/one'))

  def test_rootless_and_cgroups_required(self):
    for host in [{'security': {'rootless': False}, 'cgroupVersion': 'v2'},
          {'security': {'rootless': True}, 'cgroupVersion': 'v1'}]:
      with patch.object(m.os, 'getuid', return_value=1000), patch.object(m.os, 'getgid', return_value=1000), patch.object(m, 'output', return_value=json.dumps({'host': host})):
        with self.assertRaises(RuntimeError):
          m.rootless()

  def test_start_never_pulls_or_builds_and_uses_unique_home(self):
    with tempfile.TemporaryDirectory() as temporary:
      directory = Path(temporary)
      data, config = fixture(directory)
      calls = []
      def execute(args, **kwargs):
        calls.append([str(a) for a in args])
        return completed()
      image = {'Id': data['image_id'], 'Labels': {m.IMAGE_LABEL: '1', 'org.omarchy.workspace.uid': str(os.getuid()), 'org.omarchy.workspace.gid': str(os.getgid())}}
      with patch.object(m, 'rootless'), patch.object(m, 'exists', side_effect=lambda kind, _: kind == 'image'), patch.object(m, 'output', return_value=json.dumps([image])), patch.object(m, 'run', side_effect=execute), patch.object(m, 'inspect', return_value=config), patch.object(m, 'connect_files', return_value='alias'):
        m.start(directory, data)
      launch = next(args for args in calls if args[:2] == ['podman', 'run'])
      self.assertIn('--pull=never', launch)
      for flag in ['--userns=keep-id', '--cap-drop=ALL', '--read-only', '--security-opt=no-new-privileges', '--http-proxy=false', '--env-host=false', '--memory=4g', '--memory-swap=4g', '--pids-limit=512', '--cpus=2']:
        self.assertIn(flag, launch)
      mounts = [launch[i+1] for i, value in enumerate(launch[:-1]) if value == '--volume']
      self.assertEqual(len(mounts), 3)
      self.assertIn(m.identifiers(data)[1]+':/home/workspace:U,rw', mounts)
      self.assertEqual(launch[launch.index('--publish')+1], '127.0.0.1::2222')
      self.assertFalse(any('build' in args or '--pull=missing' in args for args in calls))

  def test_missing_image_cannot_trigger_a_build_or_pull(self):
    data, _ = fixture(Path('/state/one'))
    data.pop('image_id')
    with patch.object(m, 'rootless'), patch.object(m, 'exists', return_value=False), patch.object(m, 'run') as run:
      with self.assertRaisesRegex(RuntimeError, 'image is missing'):
        m.start(Path('/state/one'), data)
      run.assert_not_called()

  def test_new_container_is_stopped_on_failed_audit(self):
    with tempfile.TemporaryDirectory() as temporary:
      directory = Path(temporary)
      data, config = fixture(directory)
      config['HostConfig']['Privileged'] = True
      image = {'Id': data['image_id'], 'Labels': {m.IMAGE_LABEL: '1', 'org.omarchy.workspace.uid': str(os.getuid()), 'org.omarchy.workspace.gid': str(os.getgid())}}
      with patch.object(m, 'rootless'), patch.object(m, 'exists', side_effect=lambda kind, _: kind == 'image'), patch.object(m, 'output', return_value=json.dumps([image])), patch.object(m, 'run', return_value=completed()) as run, patch.object(m, 'inspect', return_value=config):
        with self.assertRaises(RuntimeError):
          m.start(directory, data)
        self.assertTrue(any(call.args[0][:2] == ['podman', 'stop'] for call in run.call_args_list))

  def test_host_key_pinning_and_ssh_authentication(self):
    with tempfile.TemporaryDirectory(prefix='workspace space-') as temporary:
      directory = Path(temporary)
      data, _ = fixture(directory)
      blob = base64.b64encode(b'\0\0\0\x0bssh-ed25519\0\0\0\x20'+b'A'*32).decode()
      with patch.object(m, 'output', return_value='127.0.0.1:41000'), patch.object(m, 'run', return_value=completed('ssh-ed25519 '+blob+'\n')) as run:
        alias = m.connect_files(directory, data, 'container')
        self.assertTrue(alias.endswith(data['id']))
        config = (directory/'ssh_config').read_text()
        for value in ['StrictHostKeyChecking yes', 'IdentityAgent none', 'ForwardAgent no', 'IdentitiesOnly yes', 'GlobalKnownHostsFile /dev/null']:
          self.assertIn(value, config)
        self.assertTrue(any(call.args[0][0] == 'ssh' for call in run.call_args_list))
        (directory/'known_hosts').write_text('changed\n')
        with self.assertRaisesRegex(RuntimeError, 'host key changed'):
          m.connect_files(directory, data, 'container')
        self.assertEqual((directory/'known_hosts').read_text(), 'changed\n')

  def test_non_loopback_endpoint_is_refused(self):
    with tempfile.TemporaryDirectory() as temporary, patch.object(m, 'output', return_value='0.0.0.0:41000'):
      with self.assertRaises(RuntimeError):
        m.connect_files(Path(temporary), {'id': 'a'*32}, 'container')


@unittest.skipIf(os.getuid() == 0 or os.getgid() == 0, 'workspace creation requires an unprivileged test user')
class StateTests(unittest.TestCase):
  def setUp(self):
    self.temporary = tempfile.TemporaryDirectory()
    self.addCleanup(self.temporary.cleanup)
    self.base = Path(self.temporary.name)
    self.home = self.base/'home'
    self.home.mkdir()
    environment = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    environment.update(HOME=str(self.home), XDG_DATA_HOME=str(self.base/'data'), OMARCHY_PATH=str(ROOT), GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1', GIT_TERMINAL_PROMPT='0', WAYLAND_DISPLAY='test-display')
    self.environment = patch.dict(os.environ, environment, clear=True)
    self.environment.start()
    self.addCleanup(self.environment.stop)
    self.root = m.state_root()
    self.source = self.home/'project'
    self.source.mkdir()
    for args in [['git', 'init', '-q', str(self.source)], ['git', '-C', str(self.source), 'config', 'user.name', 'Workspace Test'], ['git', '-C', str(self.source), 'config', 'user.email', 'workspace@example.invalid']]:
      subprocess.run(args, check=True)
    (self.source/'tracked.txt').write_text('committed\n')
    subprocess.run(['git', '-C', str(self.source), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(self.source), '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'fixture'], check=True)
    (self.source/'untracked.txt').write_text('not included\n')

  def command(self, *args):
    with patch.object(sys, 'argv', ['workspace']+list(args)), patch('sys.stdout', new_callable=io.StringIO):
      m.main()

  def test_two_clones_have_independent_keys_homes_and_no_source_remote(self):
    self.command('create', 'one', str(self.source))
    self.command('create', 'two', str(self.source))
    first, a = m.load(self.root, 'one')
    second, b = m.load(self.root, 'two')
    self.assertNotEqual(a['id'], b['id'])
    self.assertNotEqual(m.identifiers(a), m.identifiers(b))
    self.assertNotEqual((first/'identity.pub').read_text(), (second/'identity.pub').read_text())
    for directory, data in [(first, a), (second, b)]:
      repo = Path(data['directory'])
      self.assertFalse((repo/'untracked.txt').exists())
      self.assertFalse((repo/'.git/objects/info/alternates').exists())
      self.assertEqual(subprocess.check_output(['git', '-C', str(repo), 'remote'], text=True), '')
      self.assertEqual((directory/'identity').stat().st_mode & 0o777, 0o600)
      self.assertEqual((directory/'workspace.json').stat().st_mode & 0o777, 0o600)
    (Path(a['directory'])/'tracked.txt').write_text('one only\n')
    self.assertEqual((Path(b['directory'])/'tracked.txt').read_text(), 'committed\n')
    self.assertEqual((self.source/'tracked.txt').read_text(), 'committed\n')

  def test_mount_is_explicit_and_duplicate_names_fail(self):
    self.command('create', 'one', str(self.source), '--mount')
    _, data = m.load(self.root, 'one')
    self.assertEqual(data['directory'], str(self.source))
    self.assertEqual(data['mode'], 'mount')
    with self.assertRaises(RuntimeError):
      self.command('create', 'one', str(self.source))

  def test_sensitive_and_metadata_paths_are_refused(self):
    sensitive = self.home/'.ssh'
    sensitive.mkdir()
    alias = self.home/'alias'
    alias.symlink_to(sensitive, target_is_directory=True)
    for path in [self.home, Path('/'), sensitive, alias, self.root, self.root.parent]:
      with self.subTest(path=path), self.assertRaises(RuntimeError):
        self.command('create', 'bad', str(path), '--mount')

  def test_failed_clone_does_not_publish_workspace(self):
    ordinary = self.home/'not-git'
    ordinary.mkdir()
    with self.assertRaises(subprocess.CalledProcessError):
      self.command('create', 'failed', str(ordinary))
    self.assertFalse((self.root/'failed').exists())
    self.assertEqual(list(self.root.glob('.create-*')), [])

  def test_active_omarchy_tree_cannot_be_mounted_but_can_be_cloned(self):
    with patch.dict(os.environ, OMARCHY_PATH=str(self.source)):
      with self.assertRaises(RuntimeError):
        self.command('create', 'unsafe', str(self.source), '--mount')
      self.command('create', 'safe', str(self.source))
      self.assertEqual(m.load(self.root, 'safe')[1]['mode'], 'clone')

  def test_connection_key_symlinks_are_refused(self):
    self.command('create', 'one', str(self.source))
    identity = self.root/'one/identity.pub'
    identity.unlink()
    identity.symlink_to(self.source/'tracked.txt')
    with self.assertRaises(RuntimeError):
      m.load(self.root, 'one')

  def test_code_windows_use_distinct_client_and_remote_state(self):
    calls = []
    for name in ['one', 'two']:
      self.command('create', name, str(self.source))
      _, data = m.load(self.root, name)
      alias = 'omarchy-workspace-'+data['id']
      with patch.object(m, 'start', return_value=alias), patch.object(m, 'run', side_effect=lambda args, **kwargs: calls.append(args) or completed()):
        self.command('code', name)
      settings = json.loads((self.root/name/'vscode-data/User/settings.json').read_text())
      self.assertEqual(settings['remote.extensionKind'], {'openai.chatgpt': ['workspace']})
      self.assertEqual(settings['remote.SSH.defaultExtensions'], ['openai.chatgpt'])
    windows = [args for args in calls if '--new-window' in args]
    self.assertEqual(len(windows), 2)
    for flag in ['--user-data-dir', '--extensions-dir', '--shared-data-dir', '--agent-plugins-dir', '--agents-user-data-dir', '--agents-extensions-dir', '--folder-uri']:
      self.assertNotEqual(windows[0][windows[0].index(flag)+1], windows[1][windows[1].index(flag)+1])
    for args in calls:
      self.assertEqual(args[args.index('--sync')+1], 'off')
      for flag, folder in [('--shared-data-dir', 'vscode-shared'), ('--agent-plugins-dir', 'vscode-agent-plugins'), ('--agents-user-data-dir', 'vscode-agents-data'), ('--agents-extensions-dir', 'vscode-agents-extensions')]:
        path = Path(args[args.index(flag)+1])
        self.assertEqual(path.name, folder)
        self.assertEqual(path.parent, Path(args[args.index('--user-data-dir')+1]).parent)
      self.assertNotIn('openai.chatgpt', args)  # Never install Codex locally.

  def test_code_rejects_headless_shell_before_starting_container(self):
    self.command('create', 'one', str(self.source))
    with patch.dict(os.environ, DISPLAY='', WAYLAND_DISPLAY=''), patch.object(m, 'start') as start:
      with self.assertRaisesRegex(RuntimeError, 'No graphical display'):
        self.command('code', 'one')
      start.assert_not_called()

  def test_shared_and_agent_state_symlinks_are_refused(self):
    for folder in ['vscode-shared', 'vscode-agent-plugins', 'vscode-agents-data', 'vscode-agents-extensions']:
      with self.subTest(folder=folder):
        directory = self.root/folder
        directory.mkdir()
        (directory/folder).symlink_to(self.source, target_is_directory=True)
        with self.assertRaises(RuntimeError):
          m.editor_settings(directory, 'alias')

  def test_stop_still_works_when_project_or_ssh_files_are_missing(self):
    self.command('create', 'one', str(self.source))
    directory, data = m.load(self.root, 'one')
    shutil.rmtree(directory/'repo')
    (directory/'identity.pub').unlink()
    with patch.object(m, 'rootless'), patch.object(m, 'exists', return_value=True), patch.object(m, 'inspect', return_value={'Config': {'Labels': {m.LABEL: data['id']}}}), patch.object(m, 'run', return_value=completed()) as run:
      self.command('stop', 'one')
      self.assertEqual(run.call_args.args[0][:2], ['podman', 'stop'])

  def test_changed_remote_execution_settings_fail_closed(self):
    directory = self.root/'client'
    directory.mkdir()
    m.editor_settings(directory, 'alias')
    path = directory/'vscode-data/User/settings.json'
    settings = json.loads(path.read_text())
    settings['remote.extensionKind'] = {'openai.chatgpt': ['ui']}
    path.write_text(json.dumps(settings))
    with self.assertRaises(RuntimeError):
      m.editor_settings(directory, 'alias')


if __name__ == '__main__':
  unittest.main(verbosity=2)
