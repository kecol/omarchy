#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"
require_command python3
require_command pacman-conf

# Exercise only the workflow's container payload. Never run Docker, a real
# package transaction, QEMU or its SSH/VM controller. The real config parser
# reads synthetic files, so Includes and the CI-only filesystem exception are
# tested while full/syscall opt-outs still fail closed.
python3 - <<'PY'
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile

root = Path(os.environ['ROOT'])
source = (root/'.github/workflows/test.yml').read_text()
step = source.split('      - name: Run the tests in the VM\n', 1)[1].splitlines()
assert step[0] == '        run: |'
lines = []
for line in step[1:]:
  if line and not line.startswith('          '):
    break
  lines.append(line[10:])
words = shlex.split('\n'.join(lines), comments=True)
index = words.index('bash')
assert words[index+1:index+4] == ['-euo', 'pipefail', '-c']
payload = words[index+4]
assert index+5 == len(words)
parser = str(Path(shutil.which('pacman-conf')).resolve())

with tempfile.TemporaryDirectory(prefix='CI package policy ') as directory:
  for name, directive, package_exit, expected_status, expected_events in (
    ('enabled', '', 0, 0, ['package', 'version', 'vm']),
    ('full-opt-out', 'DisableSandbox', 0, 1, []),
    ('filesystem-opt-out', 'DisableSandboxFilesystem', 0, 0, ['package', 'version', 'vm']),
    ('syscalls-opt-out', 'DisableSandboxSyscalls', 0, 1, []),
    ('filesystem-and-full-opt-out', 'DisableSandboxFilesystem\nDisableSandbox', 0, 1, []),
    ('filesystem-and-syscalls-opt-out', 'DisableSandboxFilesystem\nDisableSandboxSyscalls', 0, 1, []),
    ('missing-config', '', 0, None, []),
    ('package-fails', 'DisableSandboxFilesystem', 17, 17, ['package']),
  ):
    stage = Path(directory)/name
    binaries = stage/'bin';binaries.mkdir(parents=True)
    local = stage/'local/bin';local.mkdir(parents=True)
    etc = stage/'etc/pacman.d';etc.mkdir(parents=True)
    (etc/'mirrorlist').write_text('Server = https://example.invalid/$repo/os/$arch\n')
    (stage/'lsm').write_text('capability\n')
    config = stage/'etc/pacman.conf'
    included = stage/'etc/options.conf'
    included.write_text(directive + '\n')
    config.write_text('[options]\nInclude = ' + str(included) + '\n[core]\nServer = https://example.invalid/core\n')
    if name == 'missing-config':
      config.unlink()
    config_before = config.read_bytes() if config.exists() else None
    def program(path, body):
      path.parent.mkdir(parents=True, exist_ok=True)
      path.write_text('#!/bin/bash\n' + body)
      path.chmod(0o755)
    program(binaries/'pacman-conf', 'exec "$PARSER" --config "$CONFIG" "$@"\n')
    program(binaries/'native-pacman', 'printf "package\\n" >>"$CALLS"\nprintf "%s\\n" "$@" >>"$ARGS"\nexit "$PACKAGE_EXIT"\n')
    program(local/'pacman', 'printf "path-wrapper\\n" >>"$CALLS"\nexit 97\n')
    wrapper_before = (local/'pacman').read_bytes()
    program(binaries/'qemu-system-x86_64', 'printf "version\\n" >>"$CALLS"\nprintf "inert QEMU\\n"\n')
    program(stage/'src/omarchy/test/ci-vm', 'printf "vm\\n" >>"$CALLS"\n')
    program(binaries/'sleep', 'printf "retry-sleep\\n" >>"$CALLS"\n')
    # Remap filesystem/executable endpoints, not control flow. This also makes
    # the old payload safe as a negative control: its wrapper and retry loop
    # reach only these inert endpoints, never the real system.
    mapping = {
      '/usr/bin/pacman-conf': str(binaries/'pacman-conf'),
      '/usr/bin/pacman': str(binaries/'native-pacman'),
      '/usr/local/bin/pacman': str(local/'pacman'),
      '/etc/pacman.d/mirrorlist': str(etc/'mirrorlist'),
      '/sys/kernel/security/lsm': str(stage/'lsm'),
    }
    script = payload
    for old in sorted(mapping, key=len, reverse=True):
      script = script.replace(old, shlex.quote(mapping[old]))
    calls = stage/'calls';args = stage/'args'
    result = subprocess.run(['/bin/bash', '-euo', 'pipefail', '-c', script], cwd=stage, env={
      'HOME': str(stage), 'PATH': f'{local}:{binaries}:/usr/bin:/bin',
      'PARSER': parser, 'CONFIG': str(config), 'PACKAGE_EXIT': str(package_exit),
      'CALLS': str(calls), 'ARGS': str(args),
    }, capture_output=True, text=True, timeout=5)
    detail = json.dumps({'case': name, 'exit': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr})
    if expected_status is None:
      assert result.returncode != 0, detail
    else:
      assert result.returncode == expected_status, detail
    events = calls.read_text().splitlines() if calls.exists() else []
    assert events == expected_events, (detail, events)
    arguments = args.read_text().splitlines() if args.exists() else []
    assert not any(value.startswith('--disable-sandbox') for value in arguments), (detail, arguments)
    if directive == 'DisableSandboxFilesystem':
      assert '::warning::' in result.stdout, detail
    assert (local/'pacman').read_bytes() == wrapper_before, detail
    assert (config.read_bytes() if config.exists() else None) == config_before, detail
    assert included.read_text() == directive + '\n', detail
    print('ok - CI package policy: ' + name)
PY
