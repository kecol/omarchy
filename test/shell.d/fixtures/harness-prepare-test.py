import importlib.util
import json
import os
from pathlib import Path
import pty
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT=Path(os.environ['ROOT'])
OLD='sha256:'+'a'*64
NEW='sha256:'+'b'*64
MOCK='''#!/usr/bin/python3
import json,os,sys
from pathlib import Path
base=Path(sys.argv[0]).resolve().parent.parent
name=Path(sys.argv[0]).name
args=sys.argv[1:]
with (base/'calls').open('a') as f:f.write(json.dumps([name]+args)+'\\n')
p=base/'state.json';s=json.loads(p.read_text())
def save():p.write_text(json.dumps(s))
if name=='omarchy-cmd-missing':sys.exit(0 if args[0] in s.get('missing',[]) else 1)
if name=='mise':
 assert args[:1]==['latest'],args
 assert os.environ['HOME']!=str(base/'home')
 assert not any(k in os.environ for k in ('OPENAI_API_KEY','SSH_AUTH_SOCK','NODE_OPTIONS'))
 if s.get('resolve_fail'):sys.exit(1)
 print('1.4.0' if args[1]=='pi' else '0.164.0');sys.exit()
if name=='gum':
 if args[0]=='confirm':sys.exit(1 if s.get('decline') else 0)
 choice=s['choices'].pop(0) if s.get('choices') else 'Exit';save()
 print(choice);sys.exit()
if name=='systemd-run':
 index=args.index('nice');os.execvp('nice',args[index:])
if name=='omarchy-agent':sys.exit(0)
assert name=='podman'
assert args.pop(0)=='--remote=false',args
if args[0]=='info':print('false' if s.get('rootful') else 'true')
elif args[:2]==['image','exists']:
 if s.get('image_error'):sys.exit(125)
 sys.exit(0 if args[-1] in s.get('tags',{}) else 1)
elif args[:2]==['image','inspect']:
 if s.get('inspect_fail'):sys.exit(125)
 if s.get('inspect_empty'):sys.exit(0)
 cid=s.get('tags',{}).get(args[-1])
 if not cid:sys.exit(1)
 if args[3]=='{{.Id}}':print(cid)
 else:print(json.dumps({'Id':cid,'Labels':{'org.omarchy.harness':s.get('wrong_label',s.get('harness','pi')),'org.omarchy.harness.version':s.get('version','1.4.0')},'Created':'2026-01-01T00:00:00Z'}))
elif args[0]=='build':
 assert json.loads(Path(args[args.index('--authfile')+1]).read_text())=={'auths':{}}
 assert Path(args[args.index('--ignorefile')+1]).name=='.containerignore'
 if s.get('build_fail'):sys.exit(1)
 Path(args[args.index('--iidfile')+1]).write_text('sha256:'+'b'*64+'\\n')
 s['harness']=next(a.split('=',1)[1] for a in args if a.startswith('org.omarchy.harness='))
 s['version']=next(a.split('=',1)[1] for a in args if a.startswith('org.omarchy.harness.version='));save()
elif args[:2]==['volume','inspect']:sys.exit(1)
elif args[:2]==['volume','create']:print(args[-1])
elif args[:2]==['volume','rm']:pass
elif args[0]=='run':
 if '--entrypoint=/bin/bash' in args:
  if s.get('smoke_fail'):sys.exit(1)
  volume=next((a for a in args if a.startswith('--volume=') and ':/workspace:' in a),None)
  if volume:
   directory=volume[len('--volume='):].split(':/workspace:')[0]
   Path(directory,'fixture').write_text('fixture')
  elif s.get('home_fail'):sys.exit(1)
 else:
  value='0.0.0' if s.get('verify_fail') else s['version']
  print(('codex-cli ' if s['harness']=='codex' else '')+value)
elif args[0]=='tag':
 s.setdefault('tags',{})[args[-1]]=args[1];save()
elif args[0]=='untag':pass
else:raise AssertionError(args)
'''


class PrepareTests(unittest.TestCase):
  def setUp(self):
    temporary=tempfile.TemporaryDirectory(prefix='harness prepare ');self.addCleanup(temporary.cleanup)
    self.root=Path(temporary.name);self.bin=self.root/'bin';self.bin.mkdir()
    self.home=self.root/'home';self.home.mkdir()
    self.env={'HOME':str(self.home),'PATH':str(self.bin)+':'+str(ROOT/'bin')+':/usr/bin:/bin','OMARCHY_PATH':str(ROOT),'TERM':'dumb'}
    self.state={'tags':{},'choices':[]}
    self.save()
    for name in ('podman','mise','gum','omarchy-cmd-missing','systemd-run','omarchy-agent'):
      path=self.bin/name;path.write_text(MOCK);path.chmod(0o755)

  def save(self): (self.root/'state.json').write_text(json.dumps(self.state))
  def calls(self):
    path=self.root/'calls'
    return [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []
  def run_command(self,name,*args,code=0,terminal=False):
    self.save();command=[str(ROOT/'bin'/name),*args]
    if terminal:
      master,slave=pty.openpty();data=bytearray()
      def drain():
        try:
          while True:
            part=os.read(master,65536)
            if not part:break
            data.extend(part)
        except OSError:pass
      reader=threading.Thread(target=drain);reader.start()
      p=subprocess.Popen(command,env=self.env,stdin=slave,stdout=subprocess.PIPE,stderr=slave)
      os.close(slave)
      try:out,_=p.communicate(timeout=15)
      finally:
        if p.poll() is None:p.kill();p.wait()
      reader.join(timeout=3);os.close(master);self.assertFalse(reader.is_alive())
      result=subprocess.CompletedProcess(command,p.returncode,out,bytes(data))
    else:result=subprocess.run(command,env=self.env,input=b'',capture_output=True,timeout=15)
    self.state=json.loads((self.root/'state.json').read_text())
    self.assertEqual(result.returncode,code,result.stderr.decode(errors='replace'))
    return result

  def test_missing_pi_image_prepares_after_consent_with_no_host_agent(self):
    self.env.update(OPENAI_API_KEY='fixture-only',SSH_AUTH_SOCK=str(self.root/'not-forwarded.sock'),NODE_OPTIONS='--fixture-must-not-propagate')
    result=self.run_command('omarchy-harness-ensure','pi',terminal=True)
    self.assertEqual(result.stdout.decode().strip(),NEW)
    calls=self.calls();confirm=next(i for i,c in enumerate(calls) if c[:2]==['gum','confirm'])
    lookup=next(i for i,c in enumerate(calls) if c[:2]==['mise','latest'])
    self.assertLess(confirm,lookup)
    self.assertTrue(any('--default=false' in c for c in calls if c[0]=='gum'))
    self.assertEqual(self.state['tags']['localhost/omarchy-harness-pi:latest'],NEW)

  def test_codex_uses_same_pipeline_and_native_version_prefix(self):
    self.run_command('omarchy-harness-ensure','codex','--yes')
    self.assertEqual(self.state['tags']['localhost/omarchy-harness-codex:latest'],NEW)
    build=next(c for c in self.calls() if c[:3]==['podman','--remote=false','build'])
    self.assertIn('CODEX_VERSION=0.164.0',build)
    self.assertTrue(any('--entrypoint=codex' in c for c in self.calls()))

  def test_existing_image_reused_without_resolution_build_or_confirm(self):
    self.state.update(tags={'localhost/omarchy-harness-pi:latest':OLD},harness='pi',version='1.0.0')
    result=self.run_command('omarchy-harness-ensure','pi')
    self.assertEqual(result.stdout.decode().strip(),OLD)
    self.assertFalse(any(c[0] in ('gum','mise','systemd-run') for c in self.calls()))

  def test_wrong_existing_image_label_is_not_rebuilt_or_treated_as_missing(self):
    self.state.update(tags={'localhost/omarchy-harness-pi:latest':OLD},wrong_label='other',version='1.0.0')
    self.run_command('omarchy-harness-ensure','pi','--yes',code=1)
    self.assertFalse(any(c[0] in ('mise','systemd-run') for c in self.calls()))

  def test_inspect_errors_or_empty_output_fail_closed_without_rebuilding(self):
    for field in ('inspect_fail','inspect_empty'):
      with self.subTest(field=field):
        self.state={'tags':{'localhost/omarchy-harness-pi:latest':OLD},field:True}
        self.run_command('omarchy-harness-ensure','pi','--yes',code=1)
        self.assertFalse(any(c[0] in ('mise','systemd-run') for c in self.calls()))

  def test_cancel_does_not_resolve_build_or_create_home(self):
    self.state['decline']=True
    self.run_command('omarchy-harness-ensure','pi',terminal=True,code=130)
    self.assertFalse(any(c[0] in ('mise','systemd-run') or c[:4]==['podman','--remote=false','volume','create'] for c in self.calls()))

  def test_noninteractive_missing_image_needs_explicit_approval(self):
    self.run_command('omarchy-harness-ensure','pi',code=1)
    self.assertFalse(any(c[0] in ('mise','gum','systemd-run') for c in self.calls()))

  def test_first_launch_prepare_and_run_returns_image_without_second_menu(self):
    self.state['choices']=['Prepare and run']
    result=self.run_command('omarchy-harness-select-image','--interactive','pi','pi',terminal=True)
    self.assertEqual(result.stdout.decode().strip(),NEW)
    self.assertEqual(len([c for c in self.calls() if c[:2]==['gum','choose']]),1)

  def test_each_validation_failure_preserves_existing_tags(self):
    for field in ('resolve_fail','build_fail','verify_fail','smoke_fail','home_fail'):
      with self.subTest(field=field):
        self.state={'tags':{'localhost/omarchy-harness-pi:latest':OLD},'choices':[],field:True}
        before=len(self.calls())
        self.run_command('omarchy-harness-build','pi',code=1)
        self.assertEqual(self.state['tags']['localhost/omarchy-harness-pi:latest'],OLD)
        self.assertFalse(any(c[:3]==['podman','--remote=false','tag'] for c in self.calls()[before:]))

  def test_private_build_tags_promote_latest_last_and_keep_previous(self):
    self.state.update(tags={'localhost/omarchy-harness-pi:latest':OLD},harness='pi',version='1.0.0')
    self.run_command('omarchy-harness-build','pi','1.4.0')
    tags=[c for c in self.calls() if c[:3]==['podman','--remote=false','tag']]
    self.assertEqual(tags[-1][-1],'localhost/omarchy-harness-pi:latest')
    self.assertEqual(self.state['tags']['localhost/omarchy-harness-pi:previous'],OLD)
    untag=next(c for c in self.calls() if c[:3]==['podman','--remote=false','untag'])
    self.assertEqual(untag[-1],untag[-2]);self.assertIn(':build-',untag[-1])

  def test_candidate_only_qualification_never_changes_stable_tags(self):
    self.state.update(tags={'localhost/omarchy-harness-pi:latest':OLD},harness='pi',version='1.0.0')
    result=self.run_command('omarchy-harness-build','pi','1.4.0','--candidate-only')
    self.assertIn(NEW,result.stdout.decode())
    self.assertEqual(self.state['tags'],{'localhost/omarchy-harness-pi:latest':OLD})
    self.assertFalse(any(c[:3]==['podman','--remote=false','tag'] for c in self.calls()))

  def test_version_and_runtime_probes_are_offline_and_use_only_disposable_mounts(self):
    self.run_command('omarchy-harness-build','pi','1.4.0')
    runs=[c for c in self.calls() if c[:3]==['podman','--remote=false','run']]
    self.assertEqual(len(runs),3)
    for c in runs:
      for option in ('--network=none','--http-proxy=false','--read-only','--userns=keep-id','--cap-drop=all','--security-opt=no-new-privileges'):
        self.assertIn(option,c)
      mounts=[a for a in c if a.startswith('--volume=')]
      self.assertFalse(any(str(self.home) in a or 'SSH_AUTH_SOCK=' in a or 'podman.sock:' in a for a in mounts))
    self.assertTrue(any(c[:4]==['podman','--remote=false','volume','rm'] for c in self.calls()))
    scope=next(c for c in self.calls() if c[0]=='systemd-run')
    for option in ('--property=MemoryMax=2G','--property=CPUQuota=200%','--property=TasksMax=512'):self.assertIn(option,scope)

  def test_explicit_version_never_resolves_latest(self):
    self.run_command('omarchy-harness-build','codex','0.164.0')
    self.assertFalse(any(c[0]=='mise' for c in self.calls()))

  def test_invalid_version_and_unreviewed_harness_do_not_build(self):
    self.run_command('omarchy-harness-build','pi','latest',code=1)
    self.run_command('omarchy-harness-build','unknown-agent',code=1)
    self.assertFalse(any(c[0]=='systemd-run' for c in self.calls()))

  def test_unknown_engine_state_is_not_assumed_to_be_missing_image(self):
    self.state['image_error']=True
    self.run_command('omarchy-harness-ensure','pi','--yes',code=1)
    self.assertFalse(any(c[0] in ('mise','systemd-run') for c in self.calls()))

  def test_rootful_or_missing_engine_fails_before_setup(self):
    self.state['rootful']=True;self.run_command('omarchy-harness-ensure','pi','--yes',code=1)
    self.state={'tags':{},'missing':['podman']};self.run_command('omarchy-harness-build','pi','1.4.0',code=1)
    self.assertFalse(any(c[0]=='systemd-run' for c in self.calls()))

  def test_public_recipe_check_is_read_only_and_default_selection_skips_host_install(self):
    self.run_command('omarchy-agent-prepare','--agent=codex','--check')
    self.assertFalse(self.calls())
    mode=self.home/'.config/omarchy/agents/mode';mode.parent.mkdir(parents=True);mode.write_text('container\n')
    self.run_command('omarchy-default-agent','codex')
    self.assertEqual((self.home/'.config/omarchy/defaults/agent').read_text(),'codex\n')
    self.assertTrue(any(c[:2]==['omarchy-agent','--container'] for c in self.calls()))
    self.assertFalse(any(c[0] in ('podman','mise','gum') for c in self.calls()))

  def test_recipe_check_rejects_mismatched_agent_executable(self):
    directory=self.home/'.config/omarchy/agents';directory.mkdir(parents=True)
    (directory/'codex.json').write_text(json.dumps({'name':'codex','harness':'pi','runtime':'podman','command':['codex']}))
    self.run_command('omarchy-agent-prepare','--agent=codex','--check',code=1)
    self.assertFalse(self.calls())

  def test_unsupported_default_does_not_save_or_install_host_tool(self):
    mode=self.home/'.config/omarchy/agents/mode';mode.parent.mkdir(parents=True);mode.write_text('container\n')
    defaults=self.home/'.config/omarchy/defaults';defaults.mkdir();(defaults/'agent').write_text('pi\n')
    self.run_command('omarchy-default-agent','claude',code=1)
    self.assertEqual((defaults/'agent').read_text(),'pi\n')
    self.assertFalse(any(c[0]=='mise' for c in self.calls()))

  def test_bundled_recipe_contract_and_future_metadata_are_not_agent_switches(self):
    for name in ('pi','codex'):
      path=ROOT/'containers/harnesses'/name/'Containerfile'
      text=path.read_text();self.assertIn('USER agent',text);self.assertIn('ENTRYPOINT ["'+name+'"]',text)
    spec=importlib.util.spec_from_file_location('harness_meta',ROOT/'default/agents/harness.py')
    with patch.dict(os.environ,self.env):
      module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    source=self.root/'source';context=source/'containers/harnesses/future';context.mkdir(parents=True)
    (context/'Containerfile').write_text('FROM scratch\n')
    (context/'.containerignore').write_text('*\n!Containerfile\n')
    (context/'harness.json').write_text(json.dumps({'schema_version':1,'name':'future','display_name':'Future Agent','mise_tool':'future','executable':'future','version_build_arg':'FUTURE_VERSION','version_output':'future {version}'}))
    with patch.object(module,'ROOT',source):
      self.assertEqual(module.metadata('future')['executable'],'future')
      path=context/'harness.json';valid=json.loads(path.read_text())
      for key,value in (('mise_tool','--bad'),('version_build_arg','bad arg'),('version_output','no placeholder'),('display_name','bad\u001bname')):
        path.write_text(json.dumps({**valid,key:value}))
        with self.assertRaises(ValueError):module.metadata('future')
      with self.assertRaises(ValueError):module.metadata('../future')


if __name__=='__main__':unittest.main()
