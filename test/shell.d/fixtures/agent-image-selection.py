import json
import os
from pathlib import Path
import pty
import subprocess
import sys
import tempfile
import threading

ROOT = Path(sys.argv[1])
OLD = 'sha256:' + 'a' * 64
NEW = 'sha256:' + 'b' * 64

MOCK = r'''#!/usr/bin/python3
import json,os,sys
from pathlib import Path
name=Path(sys.argv[0]).name
args=sys.argv[1:]
base=Path(os.environ['FIXTURE'])
with (base/'calls').open('a') as f:f.write(json.dumps([name]+args)+'\n')
def read(name,default=None):
 p=base/name
 return json.loads(p.read_text()) if p.exists() else default
def write(name,value):(base/name).write_text(json.dumps(value))
old='sha256:'+'a'*64;new='sha256:'+'b'*64
if name=='omarchy-cmd-missing':sys.exit(1)
if name=='mise':
 if os.environ.get('RESOLVE_FAIL'):sys.exit(1)
 print('1.4.0');sys.exit()
if name=='gum':
 if args[0]=='confirm':sys.exit(1 if os.environ.get('DECLINE') else 0)
 choices=read('choices',[])
 if not choices:sys.exit(130)
 pick=choices.pop(0);write('choices',choices)
 if pick=='CANCEL':sys.exit(130)
 print(pick);sys.exit()
if args[0]=='info':print('true')
elif args[:2]==['image','exists']:sys.exit(0 if read('current') else 1)
elif args[:2]==['image','inspect']:
 current=read('current')
 if not current:sys.exit(1)
 if args[3]=='{{.Id}}':print(current)
 else:
  print(json.dumps({'Id':current,'Labels':{'org.omarchy.harness':os.environ.get('HARNESS','pi'),'org.omarchy.harness.version':'1.4.0' if current==new else '1.0.0'},'Created':'2026-01-01T00:00:00Z'}))
  if os.environ.get('RETAG'):write('current',new)
elif args[0]=='build':
 if os.environ.get('BUILD_FAIL'):sys.exit(1)
 Path(args[args.index('--iidfile')+1]).write_text(new+'\n')
elif args[0]=='run':print('0.0.0' if os.environ.get('VERIFY_FAIL') else '1.4.0')
elif args[0]=='tag':
 if args[-1].endswith(':latest'):write('current',args[1])
elif args[0]!='untag':raise RuntimeError(args)
'''


def run(choices=(), current=OLD, terminal=True, interactive=True, extra=None, adapter=False):
  with tempfile.TemporaryDirectory(prefix='agent-image-') as temp:
    base = Path(temp)
    binaries = base / 'bin'
    binaries.mkdir()
    for name in ('podman', 'mise', 'gum', 'omarchy-cmd-missing'):
      path = binaries / name
      path.write_text(MOCK)
      path.chmod(0o755)
    (base / 'choices').write_text(json.dumps(choices))
    (base / 'current').write_text(json.dumps(current))
    env = dict(os.environ, HOME=temp, FIXTURE=temp, OMARCHY_PATH=str(ROOT),
               PATH=f'{binaries}:/usr/bin')
    for key in ('OMARCHY_AGENT_MANAGED', 'OMARCHY_AGENT_ONESHOT'):
      env.pop(key, None)
    env.update(extra or {})
    command = [str(ROOT / 'bin/omarchy-harness-select-image')]
    if interactive:
      command.append('--interactive')
    command += ['pi', 'pi']
    if adapter:
      scripts = base / 'scripts'
      scripts.mkdir()
      for name in ('omarchy-agent-run-podman', 'omarchy-harness-select-image'):
        target = scripts / name
        target.write_bytes((ROOT / 'bin' / name).read_bytes())
        target.chmod(0o755)
      doctor = scripts / 'omarchy-agent-container-doctor'
      doctor.write_text('#!/bin/bash\nexit 0\n')
      doctor.chmod(0o755)
      command = [str(scripts / 'omarchy-agent-run-podman'), '--select-image', 'pi', 'pi', '--', 'pi']
    if terminal:
      master, slave = pty.openpty()
      transcript = bytearray()

      def drain():
        try:
          while True:
            data = os.read(master, 65536)
            if not data:
              break
            transcript.extend(data)
        except OSError:
          pass
      process = subprocess.Popen(command, env=env, stdin=slave, stderr=slave,
                                 stdout=slave if adapter else subprocess.PIPE)
      os.close(slave)
      reader = threading.Thread(target=drain)
      reader.start()
      stdout, _ = process.communicate(timeout=20)
      reader.join(timeout=5)
      os.close(master)
      assert not reader.is_alive()
      stderr = transcript.decode()
    else:
      process = subprocess.run(command, env=env, input=b'', capture_output=True, timeout=20)
      stdout, stderr = process.stdout, process.stderr.decode()
    calls = [json.loads(s) for s in (base / 'calls').read_text().splitlines()]
    return process.returncode, (stdout or b'').decode().strip(), stderr, calls


def check(condition, message):
  assert condition, message
  print('ok - ' + message)


def called(calls, program, action):
  return any(c[:2] == [program, action] for c in calls)


code, image, text, calls = run(['Run'])
check(code == 0 and image == OLD and 'Version: 1.0.0' in text and OLD in text,
      'interactive Run shows metadata and returns the displayed immutable image')
check(not called(calls, 'mise', 'latest') and not called(calls, 'podman', 'build'),
      'Run does not check the network or build')
code, image, _, _ = run(['Run'], current=OLD.removeprefix('sha256:'))
check(code == 0 and image == OLD, 'bare Podman image IDs normalize to immutable sha256 references')
code, image, _, calls = run(['Run'], extra={'RETAG': '1'})
check(code == 0 and image == OLD, 'retagging latest after inspection cannot change the selected image')
code, image, text, calls = run(['Update to latest release', 'Run'])
check(code == 0 and image == NEW and 'Version: 1.4.0' in text,
      'update verifies and promotes the image then displays the new version')
check(called(calls, 'gum', 'confirm') and called(calls, 'podman', 'run'),
      'update requires confirmation and checks the actual Pi version')
for failure in ('BUILD_FAIL', 'VERIFY_FAIL', 'RESOLVE_FAIL'):
  code, image, _, calls = run(['Update to latest release', 'Run'], extra={failure: '1'})
  check(code == 0 and image == OLD and not called(calls, 'podman', 'tag'),
        failure + ' retains the previous image and permits Run')
code, image, _, calls = run(['Update to latest release', 'Run'], extra={'DECLINE': '1'})
check(code == 0 and image == OLD and not called(calls, 'podman', 'build'),
      'declining an update does not build')
code, image, _, calls = run(['Build latest', 'Run'], current=None)
check(code == 0 and image == NEW, 'a missing image can be built and selected')
for choice in ('Exit', 'CANCEL'):
  code, image, _, calls = run([choice])
  check(code == 130 and not image and not called(calls, 'podman', 'build'),
        choice + ' leaves without selecting or updating')
code, _, text, calls = run(['Exit'], adapter=True)
check(code == 0 and 'Version: 1.0.0' in text and
      not any(c[0] == 'podman' and c[1] in ('volume', 'run') for c in calls),
      'adapter Exit succeeds without creating volumes, starting an agent, or recording state')
for terminal, interactive, extra in (
    (False, True, {}), (True, False, {}),
    (True, True, {'OMARCHY_AGENT_MANAGED': 'true'}),
    (True, True, {'OMARCHY_AGENT_ONESHOT': '1'}),
    (True, True, {'OMARCHY_AGENT_ONESHOT': 'true'})):
  code, image, _, calls = run(terminal=terminal, interactive=interactive, extra=extra)
  check(code == 0 and image == OLD and not any(c[0] in ('gum', 'mise') for c in calls),
        f'noninteractive policy bypasses menus and updates: {terminal}, {interactive}, {extra}')
code, image, text, _ = run(current=None, terminal=False)
check(code == 1 and not image and 'omarchy harness build pi' in text,
      'noninteractive missing images fail with an explicit build instruction')
for extra, current in (({'HARNESS': 'wrong'}, OLD), ({}, 'malformed')):
  code, image, _, calls = run(['Run'], current=current, extra=extra)
  check(code == 1 and not image and not called(calls, 'gum', 'choose'),
        'invalid image identity fails closed before the menu')
