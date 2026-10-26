"""Reviewed, bundled harness metadata and isolated public version resolution."""
import argparse
import json
import os
from pathlib import Path
import re
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


def latest(info):
  # No host installation/config/credentials or project hooks are needed to ask
  # for a public version. Network resolution happens only after explicit setup.
  with tempfile.TemporaryDirectory(prefix='omarchy-harness-release-') as directory:
    work = Path(directory)
    for name in ('home', 'config', 'data', 'cache', 'system'):
      (work / name).mkdir()
    (work / 'empty.toml').write_text('')
    env = {key: value for key, value in os.environ.items()
      if key in ('PATH', 'LANG', 'LC_ALL', 'TERM', 'NO_COLOR')}
    env.update(
      HOME=str(work / 'home'),
      XDG_CONFIG_HOME=str(work / 'config'),
      XDG_DATA_HOME=str(work / 'data'),
      XDG_CACHE_HOME=str(work / 'cache'),
      MISE_SYSTEM_CONFIG_DIR=str(work / 'system'),
      MISE_GLOBAL_CONFIG_FILE=str(work / 'empty.toml'),
      MISE_CONFIG_FILE=str(work / 'empty.toml'),
      MISE_MINIMUM_RELEASE_AGE='0',
    )
    result = subprocess.run(['mise', 'latest', info['mise_tool']], cwd=work, env=env,
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
