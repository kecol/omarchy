"""Opt-in launch-friction guards, not an isolation or executable-trust boundary."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile

NAME = re.compile(r'[a-z0-9][a-z0-9._-]{0,95}\Z')
# These are infrastructure/runner roles, not an allowlist of agent products.
RESERVED = frozenset(('sh bash zsh fish dash rbash env sudo su ssh scp sftp code mise node nodejs python python3 '
  'uv uvx pip pip3 npm npx pnpm yarn bun docker podman timeout jq git perl ruby php java go rustc cargo '
  'ls cat head tail grep sed awk find xargs printf echo true false test which dirname basename readlink realpath '
  'mkdir rmdir mktemp rm mv cp ln chmod chown touch sort uniq cut tr tee wc date sleep kill pkill systemctl '
  'loginctl curl wget tar gzip unzip make cc gcc clang').split())
ROOT = Path(os.environ['OMARCHY_PATH'])
LIMIT = 1024 * 1024


def safe_name(name):
  return isinstance(name, str) and NAME.fullmatch(name) and name not in RESERVED and not name.startswith(('omarchy', 'python'))


def private_read(path):
  fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
  try:
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
      raise ValueError('Guard metadata must be a private user-owned regular file')
    data = os.read(fd, LIMIT + 1)
    if len(data) > LIMIT:
      raise ValueError('Guard metadata exceeds its limit')
    return json.loads(data)
  finally:
    os.close(fd)


def state_root(create=False):
  root = Path(os.environ.get('XDG_DATA_HOME') or str(Path.home()/'.local/share'))/'omarchy/agents/command-guards'
  if not root.is_absolute() or any(c in str(root) for c in (':','\n','\r')):
    raise ValueError('Guard state path must be absolute without colons or line breaks')
  if create:
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
  if root.is_symlink() or (root.exists() and (not root.is_dir() or root.stat().st_uid != os.getuid() or root.stat().st_mode & 0o077)):
    raise ValueError('Guard state must be a private user-owned directory, not a symlink')
  return root


def empty():
  return {'version':1, 'enabled':False, 'commands':{}, 'extra':{}}


def load(root, missing=False):
  try:
    data = private_read(root/'state.json')
  except FileNotFoundError:
    if missing and not os.path.lexists(root/'state.json'):
      return empty()
    raise ValueError('Guard metadata unavailable; use guards host for deliberate maintenance') from None
  if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('enabled'), bool):
    raise ValueError('Invalid guard state')
  for field in ('commands','extra'):
    rows = data.get(field)
    if not isinstance(rows, dict) or len(rows) > 256 or any(not safe_name(k) or not isinstance(v,str) or not NAME.fullmatch(v) for k,v in rows.items()):
      raise ValueError('Invalid guard registrations')
  return data


def save(root, data):
  fd, name = tempfile.mkstemp(prefix='.state-', dir=root)
  try:
    with os.fdopen(fd,'w') as stream:
      json.dump(data, stream, indent=2)
      stream.write('\n')
    os.replace(name, root/'state.json')
  finally:
    if os.path.exists(name): os.unlink(name)


def clean_path(root):
  directory = os.path.realpath(root/'bin')
  return ':'.join(p for p in os.environ.get('PATH','').split(':') if os.path.realpath(p or '.') != directory)


def template(command, agent):
  return '#!/bin/bash\n# Managed by omarchy agent guards v1; no installed tool is replaced.\nexec "$OMARCHY_PATH/bin/omarchy-agent-guards" run '+shlex.quote(command)+' '+shlex.quote(agent)+' -- "$@"\n'


def owned(path, command, agent):
  try:
    info = path.lstat()
    return stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and path.read_bytes() == template(command,agent).encode()
  except OSError:
    return False


def discover(root, extra):
  script = '''const fs=require('fs'),path=require('path');
const root=process.env.OMARCHY_PATH,model=require(path.join(root,'shell/plugins/menu/MenuModel.js'));
const rows=model.parseMenuJsonc(fs.readFileSync(path.join(root,'default/omarchy/omarchy-menu.jsonc'),'utf8'));
console.log(JSON.stringify(rows.filter(e=>/^setup\\.default\\.agent\\.[a-z0-9-]+$/.test(e.id)).map(e=>e.id.split('.').pop())));'''
  env=dict(os.environ)
  for key in ('NODE_OPTIONS','NODE_PATH'):env.pop(key,None)
  result = subprocess.run(['node','-e',script], capture_output=True, stdin=subprocess.DEVNULL, cwd=Path.home(), env=env, timeout=5, check=True)
  if len(result.stdout) > LIMIT: raise ValueError('Agent catalog exceeds its limit')
  catalog = json.loads(result.stdout)
  if not isinstance(catalog,list) or len(catalog)>256: raise ValueError('Invalid agent catalog')
  entries = {name:name for name in catalog if safe_name(name)}
  definitions = {}
  for directory in (ROOT/'default/agents/definitions', Path.home()/'.config/omarchy/agents'):
    if directory.exists():
      for index,path in enumerate(sorted(directory.glob('*.json'))):
        if index >= 256: raise ValueError('Too many agent definitions')
        if not NAME.fullmatch(path.stem): continue
        # User policy/account files are not definitions. Never read identities,
        # credentials, histories, environments, or arbitrary home files.
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        try:
          info=os.fstat(fd)
          if not stat.S_ISREG(info.st_mode) or (directory != ROOT/'default/agents/definitions' and info.st_uid != os.getuid()):raise ValueError('Unsafe agent definition')
          raw=os.read(fd,LIMIT+1)
          if len(raw)>LIMIT:raise ValueError('Oversized agent definition')
          data=json.loads(raw)
        finally:os.close(fd)
        if not isinstance(data,dict) or not {'name','harness','runtime','command'} <= data.keys(): continue
        if data['name'] != path.stem or not isinstance(data['command'],list) or not data['command']:
          raise ValueError('Invalid agent definition')
        definitions[path.stem] = data
  for agent,data in definitions.items():
    commands = data.get('guardCommands', [agent, data['command'][0]])
    if not isinstance(commands,list) or len(commands)>32: raise ValueError('Invalid guardCommands')
    for command in commands:
      if safe_name(command):
        if command in entries and entries[command] != agent: raise ValueError('Ambiguous agent command mapping')
        entries[command]=agent
      elif 'guardCommands' in data: raise ValueError('guardCommands cannot shadow general-purpose tools')
  entries.update(extra)
  path = clean_path(root)
  # Never run tools to discover them, install missing ones, or claim a guard
  # executable itself proves that an underlying tool is installed.
  return {command:agent for command,agent in sorted(entries.items()) if shutil.which(command,path=path)}


def sync(root, data):
  desired = discover(root,data['extra'])
  directory = root/'bin'
  if directory.is_symlink() or (directory.exists() and (not directory.is_dir() or directory.stat().st_uid != os.getuid())):
    raise ValueError('Guard bin must be a user-owned real directory')
  if directory.exists() and any(p.name not in data['commands'] for p in directory.iterdir()):
    raise ValueError('Foreign files in guard bin; refusing to change PATH coverage')
  for command,agent in data['commands'].items():
    if not owned(directory/command,command,agent): raise ValueError('A managed guard was changed; refusing to overwrite or delete it')
  for command in desired:
    if os.path.lexists(directory/command) and command not in data['commands']:
      raise ValueError('A foreign file conflicts with a guard; nothing was replaced')
  directory.mkdir(mode=0o700,exist_ok=True)
  for command,agent in desired.items():
    fd,name=tempfile.mkstemp(prefix='.guard-',dir=directory)
    try:
      with os.fdopen(fd,'w') as stream: stream.write(template(command,agent))
      os.chmod(name,0o755)
      os.replace(name,directory/command)
    finally:
      if os.path.exists(name):os.unlink(name)
  for command in data['commands'].keys()-desired.keys(): (directory/command).unlink()
  data['commands']=desired
  save(root,data)


def execute(root, argv):
  if not argv: raise ValueError('Select a host command')
  env=dict(os.environ, PATH=clean_path(root))
  binary=shutil.which(argv[0],path=env['PATH'])
  if not binary: raise ValueError('Underlying host command is not installed')
  os.execvpe(binary,argv,env)


def run_guard(root, command, agent, args):
  data=load(root)
  if data['commands'].get(command) != agent: raise ValueError('Guard registration unavailable')
  if not data['enabled']:
    execute(root,[command,*args])
  result=subprocess.run([str(ROOT/'bin/omarchy-agent-mode')],capture_output=True,stdin=subprocess.DEVNULL,timeout=5)
  if result.returncode or result.stdout not in (b'host\n',b'container\n'):
    raise ValueError('Cannot read a valid execution mode; direct agent launch blocked')
  if result.stdout == b'host\n': execute(root,[command,*args])
  print(f'Agent launch mode is Container. Direct host launch of {command} was blocked.',file=sys.stderr)
  ready=subprocess.run([str(ROOT/'bin/omarchy-agent'),'--agent',agent,'--container','--check'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,stdin=subprocess.DEVNULL,timeout=5)
  if ready.returncode == 0:
    print('Run in this terminal:\n  '+shlex.join(['omarchy','agent','--inline','--container','--agent',agent]),file=sys.stderr)
    print('This mounts the selected project read-write; image, engine, and authentication readiness were not checked.',file=sys.stderr)
  else:
    print(f'No supported container launch is configured for {agent}. This guard does not install or build one.',file=sys.stderr)
  print('For a deliberate host/maintenance command, use: omarchy agent guards host -- <command> [args...]',file=sys.stderr)
  return 126


def main():
  parser=argparse.ArgumentParser(description=__doc__)
  parser.add_argument('action',choices=['enable','disable','sync','status','register','unregister','uninstall','host','run'])
  parser.add_argument('args',nargs=argparse.REMAINDER)
  options=parser.parse_args()
  if os.getuid()==0: raise ValueError('Run as the desktop user, not under sudo')
  action,args=options.action,options.args
  root=state_root(action not in ('run','status','host'))
  if action=='host':
    if args[:1]==['--']:args=args[1:]
    execute(root,args)
  elif action=='run':
    if len(args)<3 or args[2]!='--' or not safe_name(args[0]) or not NAME.fullmatch(args[1]):raise ValueError('Invalid guard invocation')
    return run_guard(root,args[0],args[1],args[3:])
  elif action=='status':
    if args:raise ValueError('status takes no arguments')
    if not os.path.lexists(root/'state.json') and (root/'bin').is_dir() and any((root/'bin').iterdir()):
      raise ValueError('Guard scripts exist but their status metadata is unavailable')
    data=load(root,missing=True)
    precedence={command:os.path.realpath(shutil.which(command) or '')==os.path.realpath(root/'bin'/command) for command in data['commands']}
    print(json.dumps({'enabled':data['enabled'],'directory':str(root/'bin'),'commands':data['commands'],'first_on_path':precedence,'limitations':'PATH-based launch friction only; aliases, absolute paths, IDEs and other shell environments can bypass it'},indent=2))
  else:
    fd=os.open(root/'operation.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK,0o600)
    try:
      if not stat.S_ISREG(os.fstat(fd).st_mode) or os.fstat(fd).st_uid!=os.getuid():raise ValueError('Unsafe guard lock')
      fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
      data=load(root,missing=True)
      if action in ('enable','disable','sync','uninstall') and args:raise ValueError('Unexpected arguments')
      if action=='disable':
        data['enabled']=False;save(root,data)
      elif action in ('register','unregister'):
        if not 1<=len(args)<=2 or not safe_name(args[0]) or (len(args)==2 and not NAME.fullmatch(args[1])):raise ValueError('Use register <command> [agent], or unregister <command>')
        if action=='unregister' and len(args)!=1:raise ValueError('Use unregister <command>')
        if action=='register':data['extra'][args[0]]=args[1] if len(args)==2 else args[0]
        else:data['extra'].pop(args[0],None)
        save(root,data)
        print('Registration saved. Run omarchy agent guards sync to reconcile installed commands.')
      elif action=='uninstall':
        directory=root/'bin'
        if directory.exists() and any(p.name not in data['commands'] for p in directory.iterdir()):raise ValueError('Foreign files in guard bin; refusing uninstall')
        for command,agent in data['commands'].items():
          if not owned(root/'bin'/command,command,agent):raise ValueError('A guard was changed; refusing uninstall')
        data['enabled']=False;save(root,data)
        for command in data['commands']:(root/'bin'/command).unlink()
        data['commands']={};save(root,data)
        if directory.exists():directory.rmdir()
      else:
        if action=='enable':data['enabled']=True
        sync(root,data)
        print(f"{'Enabled' if data['enabled'] else 'Disabled'}: {len(data['commands'])} installed command guards")
        print('Use a new Omarchy Bash terminal, or source "$OMARCHY_PATH/default/agents/guard-path.sh"; omarchy_agent_guard_init; hash -r')
    finally:os.close(fd)
  return 0


if __name__=='__main__':
  try:sys.exit(main())
  except (OSError,ValueError,subprocess.SubprocessError) as error:
    print('Agent command guards: '+str(error),file=sys.stderr)
    sys.exit(126)
