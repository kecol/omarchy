"""Reviewed, bundled harness metadata and isolated public version resolution."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile

NAME = re.compile(r'[a-z0-9][a-z0-9._-]{0,95}\Z')
VERSION = re.compile(r'[0-9]+\.[0-9]+(?:\.[0-9]+)?(?:[+-][A-Za-z0-9.-]+)?\Z')
ROOT = Path(os.environ['OMARCHY_PATH'])
FIELDS = ('name', 'display_name', 'executable', 'mise_tool', 'version_build_arg', 'version_output')


def metadata(name):
  if not NAME.fullmatch(name):
    raise ValueError('Invalid harness name')
  context = ROOT / 'containers/harnesses' / name
  if context.is_symlink() or not context.is_dir():
    raise ValueError('No reviewed container recipe for this harness')

  fd = os.open(context / 'harness.json', os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
  try:
    if not stat.S_ISREG(os.fstat(fd).st_mode):
      raise ValueError('Harness metadata must be a regular file')
    raw = os.read(fd, 65537)
    if len(raw) > 65536:
      raise ValueError('Harness metadata exceeds its limit')
    data = json.loads(raw)
  finally:
    os.close(fd)

  if (not isinstance(data, dict) or type(data.get('schema_version')) is not int
      or data['schema_version'] != 1 or data.get('name') != name):
    raise ValueError('Invalid harness metadata')
  for key in ('executable', 'mise_tool'):
    if not isinstance(data.get(key), str) or not NAME.fullmatch(data[key]):
      raise ValueError('Invalid harness executable/tool')
  if (not isinstance(data.get('display_name'), str)
      or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 ._+-]{0,63}', data['display_name'])):
    raise ValueError('Invalid harness display name')
  if (not isinstance(data.get('version_build_arg'), str)
      or not re.fullmatch(r'[A-Z][A-Z0-9_]{0,63}', data['version_build_arg'])):
    raise ValueError('Invalid version build argument')
  output = data.get('version_output')
  if (not isinstance(output, str) or output.count('{version}') != 1
      or len(output) > 128 or not output.isprintable()):
    raise ValueError('Invalid version output template')

  recipe = context / 'Containerfile'
  ignore = context / '.containerignore'
  for path in (recipe, ignore):
    if path.is_symlink() or not path.is_file():
      raise ValueError('Reviewed recipe/context allowlist unavailable')
  return {**{key: data[key] for key in FIELDS}, 'context': str(context),
    'containerfile': str(recipe), 'ignorefile': str(ignore)}


def release_command(work, tool):
  # Environment overrides alone do not hide account-database HOME, config
  # includes, credential helpers or sockets. Expose no host home/project tree.
  sandbox = shutil.which('bwrap')
  mise = shutil.which('mise')
  if not sandbox or not mise:
    raise ValueError('Automatic release lookup requires bubblewrap and mise')
  home = work / 'home'
  (work / 'passwd').write_text(f'agent:x:{os.getuid()}:{os.getgid()}::{home}:/bin/sh\n')
  (work / 'group').write_text(f'agent:x:{os.getgid()}:\n')
  (work / 'hosts').write_text('127.0.0.1 localhost\n::1 localhost\n')
  (work / 'nsswitch.conf').write_text('passwd: files\ngroup: files\nhosts: files dns\n')
  command = [sandbox, '--unshare-all', '--share-net', '--die-with-parent', '--new-session',
    '--cap-drop', 'ALL', '--ro-bind', '/usr', '/usr']
  for name in ('bin', 'sbin', 'lib', 'lib64'):
    if Path('/' + name).exists():
      command += ['--symlink', 'usr/bin' if name in ('bin', 'sbin') else 'usr/lib', '/' + name]
  command += ['--dir', '/etc', '--proc', '/proc', '--dev', '/dev',
    '--tmpfs', '/tmp', '--tmpfs', '/run', '--bind', str(work), str(work)]
  for name in ('passwd', 'group', 'hosts', 'nsswitch.conf'):
    command += ['--ro-bind', str(work / name), '/etc/' + name]
  # Bind the resolved public bundle, not /etc/ssl (which can contain private keys).
  bundle = Path('/etc/ssl/certs/ca-certificates.crt').resolve(strict=True)
  command += ['--ro-bind', str(bundle), '/etc/ssl/certs/ca-certificates.crt',
    '--symlink', 'certs/ca-certificates.crt', '/etc/ssl/cert.pem',
    '--ro-bind', str(Path('/etc/resolv.conf').resolve(strict=True)), '/etc/resolv.conf',
    '--ro-bind', str(Path(mise).resolve(strict=True)), '/usr/bin/mise',
    '--chdir', str(work), '--', '/usr/bin/mise', 'latest', tool]
  return command


def latest(info):
  # Network resolution happens only after explicit setup. No provider account,
  # host installation/configuration or project hooks are needed for this query.
  with tempfile.TemporaryDirectory(prefix='omarchy-harness-release-') as directory:
    work = Path(directory)
    for name in ('home', 'config', 'data', 'cache', 'state', 'system'):
      (work / name).mkdir()
    (work / 'empty.toml').write_text('')
    env = {key: value for key, value in os.environ.items()
      if key in ('LANG', 'LC_ALL', 'TERM', 'NO_COLOR')}
    env.update(
      PATH='/usr/bin:/bin',
      HOME=str(work / 'home'),
      XDG_CONFIG_HOME=str(work / 'config'),
      XDG_DATA_HOME=str(work / 'data'),
      XDG_CACHE_HOME=str(work / 'cache'),
      XDG_STATE_HOME=str(work / 'state'),
      MISE_CONFIG_DIR=str(work / 'config' / 'mise'),
      MISE_DATA_DIR=str(work / 'data' / 'mise'),
      MISE_CACHE_DIR=str(work / 'cache' / 'mise'),
      MISE_STATE_DIR=str(work / 'state' / 'mise'),
      MISE_GLOBAL_CONFIG_ROOT=str(work / 'home'),
      MISE_SYSTEM_CONFIG_DIR=str(work / 'system'),
      MISE_SYSTEM_CONFIG_FILE=str(work / 'empty.toml'),
      MISE_GLOBAL_CONFIG_FILE=str(work / 'empty.toml'),
      MISE_CONFIG_FILE=str(work / 'empty.toml'),
      MISE_MINIMUM_RELEASE_AGE='0',
      SSL_CERT_FILE='/etc/ssl/certs/ca-certificates.crt',
      SSL_CERT_DIR='/etc/ssl/certs',
    )
    result = subprocess.run(release_command(work, info['mise_tool']), cwd=work, env=env,
      stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=30)
    if result.returncode or len(result.stdout) > 128:
      raise ValueError('Public release metadata unavailable; current image is unchanged')
    version = result.stdout.decode().strip()
    if not VERSION.fullmatch(version):
      raise ValueError('Invalid public release version')
    return version


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('name')
  parser.add_argument('--latest', action='store_true')
  args = parser.parse_args()
  info = metadata(args.name)
  print(latest(info) if args.latest else json.dumps(info))


if __name__ == '__main__':
  try:
    main()
  except (OSError, ValueError, subprocess.SubprocessError):
    sys.exit('Harness metadata or public release lookup unavailable; no image was replaced.')
