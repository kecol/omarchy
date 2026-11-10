import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
import sys
import contextlib
import subprocess
from unittest.mock import patch

ROOT=Path(os.environ['ROOT'])
spec=importlib.util.spec_from_file_location('sessions',ROOT/'default/agents/sessions.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
SECRET=b'PRIVATE-PROMPT-OR-TOKEN-MUST-NOT-BE-READ'


class Proc:
  container_observer=False
  boot_id='fixture-boot'
  namespaces=('pid:host','mnt:host')
  def __init__(self,root):self.root=root;self.start=100;self.ns=('pid:container','mnt:container')
  def identity(self,pid):return {'start_ticks':self.start}
  def namespace(self,pid):return self.ns


class SessionsTests(unittest.TestCase):
  def setUp(self):
    temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
    self.root=Path(temp.name);self.proc=Proc(self.root)
    self.calls=[];self.actions=[]
    self.instance='568a857f-e55a-4420-9411-be8c1b183113'
    self.pid=20;self.cid='a'*64;self.agent='codex'
    self.running=True;self.name=None;self.rootless='true';self.fail=False
    uid=patch.object(m.os,'getuid',return_value=1000);uid.start();self.addCleanup(uid.stop)
    evidence=patch.object(m,'login_evidence',return_value={'entry':'interactive-launch-option','callback_listener':'absent'})
    evidence.start();self.addCleanup(evidence.stop)
  def query(self,args,json_output=True):
    self.calls.append(args)
    self.assertFalse(any(word in args for word in ('stop','kill','rm','exec')))
    if self.fail:raise m.status.Unavailable('fixture unavailable')
    if args[2]=='info':return self.rootless
    if args[2]=='ps':return [{'Id':self.cid}]
    if args[2]=='inspect':
      template=args[4]
      self.assertNotIn('Env',template);self.assertNotIn('Auth',template)
      if 'org.omarchy.instance' in template:
        return '\t'.join(json.dumps(v) for v in [self.cid,self.instance,'2026-10-26T18:44:15Z',self.running,self.agent])
      name=self.name or 'omarchy-agent-'+self.agent+'-'+self.instance.replace('-','')[:12]
      mount={'type':'bind','source':'/projects/numerai','destination':'/workspace/key','rw':True}
      return '\t'.join(json.dumps(v) for v in [self.cid,name,self.pid,'agent',self.agent,None,'/workspace/key','key',[mount]])
    raise AssertionError(args)
  def inventory(self):return m.inventory(self.query,self.proc)
  def test_human_diagnosis_hints_only_when_harnesses_are_observed(self):
    rows = self.inventory()
    for items, expected in ((rows, True), ([], False)):
      with contextlib.redirect_stdout(io.StringIO()) as output:
        m.render(items)
      self.assertEqual(m.status.SESSION_HINT in output.getvalue(), expected)
    self.assertFalse(self.actions)

  def test_read_only_inventory_keeps_unique_identity_and_no_auth_claim(self):
    rows=self.inventory();self.assertEqual(len(rows),1)
    self.assertEqual(rows[0]['pid'],20);self.assertEqual(rows[0]['instance'],self.instance)
    self.assertEqual(rows[0]['login_evidence']['entry'],'interactive-launch-option')
    self.assertEqual(rows[0]['findings'],[]);self.assertFalse(self.actions)
  def test_shared_project_and_login_findings_are_not_auto_cleanup(self):
    first=m.status.container_snapshot(self.query,self.proc)[0]
    instance='a5314f92-021e-49bb-82f7-5ec41ee05026'
    second={**first,'id':'b'*64,'init_pid':21,'name':'omarchy-agent-codex-a5314f92021e'}
    def query(args,json_output=True):
      if args[2]=='inspect' and 'org.omarchy.instance' in args[4]:
        return '\n'.join('\t'.join(json.dumps(v) for v in [c['id'],i,'2026-10-26',True,'codex']) for c,i in ((first,self.instance),(second,instance)))
      return self.query(args,json_output)
    with patch.object(m.status,'container_snapshot',return_value=[first,second]), \
      patch.object(m,'login_evidence',return_value={'entry':'explicit-login-command','callback_listener':'present'}):
      rows=m.inventory(query,self.proc)
    self.assertEqual(len(rows),2)
    for row in rows:
      self.assertEqual(len(row['shared_project_instances']),2)
      self.assertIn('shared-project-launches',row['findings'])
      self.assertIn('login-command-present-not-proof-of-stall',row['findings'])
      self.assertFalse(self.actions)

  def test_custom_metadata_agent_is_not_limited_to_product_allowlist(self):
    self.agent='future-agent';self.assertEqual(self.inventory()[0]['agent'],'future-agent')
  def test_unavailable_or_rootful_engine_is_not_a_zero_instance_claim(self):
    self.fail=True
    with self.assertRaises(m.status.Unavailable):self.inventory()
    self.fail=False;self.rootless='false'
    with self.assertRaises(m.status.Unavailable):self.inventory()
  def test_root_and_container_observer_are_rejected(self):
    with patch.object(m.os,'getuid',return_value=0):
      with self.assertRaises(m.status.Unavailable):self.inventory()
    self.proc.container_observer=True
    with self.assertRaises(m.status.Unavailable):self.inventory()
  def test_name_label_disagreement_and_nonrunning_instance_are_rejected(self):
    self.name='unrelated-container'
    with self.assertRaises(m.status.Unavailable):self.inventory()
    self.name=None;self.running=False
    with self.assertRaises(m.status.Unavailable):self.inventory()
  def test_host_namespace_is_not_accepted_as_verified_harness(self):
    self.proc.ns=self.proc.namespaces
    with self.assertRaises(m.status.Unavailable):self.inventory()
  def test_unverified_process_owner_is_rejected_before_any_argv_or_fd_read(self):
    with patch.object(self.proc,'identity',side_effect=PermissionError('fixture denied')), \
      patch.object(m,'login_evidence') as evidence:
      with self.assertRaises(m.status.Unavailable):self.inventory()
      evidence.assert_not_called()

  def test_identity_change_during_diagnostic_probe_is_rejected(self):
    def changed(proc,container):
      proc.start=200
      return {'entry':'unknown','callback_listener':'absent'}
    with patch.object(m,'login_evidence',side_effect=changed):
      with self.assertRaises(m.status.Unavailable):self.inventory()

  def test_selector_requires_unique_uuid_prefix_not_agent_name_or_pid(self):
    row=self.inventory()[0]
    self.assertEqual(m.select([row],self.instance[:8]),row)
    for selector in ('codex','20','568a','--all'):
      with self.assertRaises(m.status.Unavailable):m.select([row],selector)
    with self.assertRaises(m.status.Unavailable):m.select([row,row],self.instance[:8])
  def test_graceful_close_targets_full_container_id_never_pid_or_volume(self):
    row=self.inventory()[0]
    m.close_instance(row,lambda:self.query,self.proc,False,self.actions.append)
    self.assertEqual(self.actions,[['podman','--remote=false','stop','--time=10',self.cid]])
  def test_force_close_is_explicit_sigkill_to_one_immutable_id(self):
    row=self.inventory()[0]
    m.close_instance(row,lambda:self.query,self.proc,True,self.actions.append)
    self.assertEqual(self.actions,[['podman','--remote=false','kill','--signal=KILL',self.cid]])
  def test_reused_pid_or_changed_namespace_is_not_signalled(self):
    row=self.inventory()[0];self.proc.start=200
    with self.assertRaises(m.status.Unavailable):m.close_instance(row,lambda:self.query,self.proc,True,self.actions.append)
    self.proc.start=100;self.proc.ns=('pid:changed','mnt:changed')
    with self.assertRaises(m.status.Unavailable):m.close_instance(row,lambda:self.query,self.proc,True,self.actions.append)
    self.assertFalse(self.actions)
  def test_changed_container_or_instance_is_not_signalled(self):
    row=self.inventory()[0];self.cid='b'*64
    with self.assertRaises(m.status.Unavailable):m.close_instance(row,lambda:self.query,self.proc,True,self.actions.append)
    self.cid='a'*64;self.instance='168a857f-e55a-4420-9411-be8c1b183113'
    with self.assertRaises(m.status.Unavailable):m.close_instance(row,lambda:self.query,self.proc,True,self.actions.append)
    self.assertFalse(self.actions)
  def test_unknown_second_token_is_not_consumed_or_reported(self):
    class Tracked(io.BytesIO):
      def close(inner):self.reads=inner.tell();super().close()
    argv=b'codex\0'+SECRET+b'\0'
    with patch.object(Path,'open',return_value=Tracked(argv)):
      self.assertEqual(m.entry_kind(Path('/unused')),'unknown')
    self.assertEqual(self.reads,len(b'codex\0')+1)
  def test_known_login_token_does_not_read_later_secret_or_prompt(self):
    class Tracked(io.BytesIO):
      def close(inner):self.reads=inner.tell();super().close()
    prefix=b'codex\0login\0'
    with patch.object(Path,'open',return_value=Tracked(prefix+SECRET+b'\0')):
      self.assertEqual(m.entry_kind(Path('/unused')),'explicit-login-command')
    self.assertEqual(self.reads,len(prefix))
  def test_close_without_tty_or_yes_never_signals(self):
    row=self.inventory()[0]
    with patch.object(m,'inventory',return_value=[row]), patch.object(m.status,'Proc',return_value=self.proc), \
      patch.object(sys,'argv',['sessions','close',self.instance]), contextlib.redirect_stderr(io.StringIO()), \
      patch.object(m.subprocess,'run') as run:
      with self.assertRaises(m.status.Unavailable):m.main()
      run.assert_not_called()

  def test_check_mode_never_prompts_or_signals(self):
    row=self.inventory()[0]
    with patch.object(m,'inventory',return_value=[row]), patch.object(m.status,'Proc',return_value=self.proc), \
      patch.object(sys,'argv',['sessions','close',self.instance,'--check']), contextlib.redirect_stdout(io.StringIO()), \
      patch.object(m.subprocess,'run') as run:
      m.main();run.assert_not_called()

  def test_default_cancel_confirmation_never_reaches_close(self):
    class Tty(io.StringIO):
      def isatty(self):return True
    row=self.inventory()[0]
    with patch.object(m,'inventory',return_value=[row]), patch.object(m.status,'Proc',return_value=self.proc), \
      patch.object(sys,'argv',['sessions','close',self.instance,'--force']), patch.object(sys,'stdin',Tty()), \
      contextlib.redirect_stderr(Tty()), patch.object(m.subprocess,'run',return_value=subprocess.CompletedProcess([],1)) as run:
      with self.assertRaises(SystemExit) as error:m.main()
      self.assertEqual(error.exception.code,130)
      self.assertEqual(run.call_count,1)
      self.assertEqual(run.call_args.args[0][:3],['gum','confirm','--default=false'])

  def test_explicit_yes_force_revalidates_then_sends_only_exact_kill(self):
    row=self.inventory()[0]
    with patch.object(m,'inventory',return_value=[row]) as inventory, patch.object(m.status,'Proc',return_value=self.proc), \
      patch.object(sys,'argv',['sessions','close',self.instance,'--force','--yes']), contextlib.redirect_stderr(io.StringIO()), \
      contextlib.redirect_stdout(io.StringIO()), patch.object(m.subprocess,'run',return_value=subprocess.CompletedProcess([],0)) as run:
      m.main()
      self.assertEqual(inventory.call_count,2)
      self.assertEqual(run.call_count,1)
      self.assertEqual(run.call_args.args[0],['podman','--remote=false','kill','--signal=KILL',self.cid])

  def test_diagnosis_json_does_not_close_anything(self):
    rows=self.inventory()
    with patch.object(m,'inventory',return_value=rows), patch.object(m.status,'Proc',return_value=self.proc), \
      patch.object(sys,'argv',['sessions','diagnose','--json']), contextlib.redirect_stdout(io.StringIO()) as output, \
      patch.object(m.subprocess,'run') as run:
      m.main();run.assert_not_called()
      self.assertEqual(json.loads(output.getvalue())['instances'][0]['instance'],self.instance)

  def test_callback_listener_requires_pid_fd_ownership_not_just_open_port(self):
    root=self.root/'socket-proc';(root/'fd').mkdir(parents=True);(root/'net').mkdir()
    (root/'net/tcp').write_text('header\n0: 0100007F:05AF 00000000:0000 0A 0:0 00:0 0 1000 0 12345\n')
    (root/'net/tcp6').write_text('header\n')
    self.assertEqual(m.callback_listener(root),'absent')
    (root/'fd/3').symlink_to('socket:[12345]')
    self.assertEqual(m.callback_listener(root),'present')


spec=importlib.util.spec_from_file_location('widget_stop',ROOT/'default/agents/container-stop.py')
cs=importlib.util.module_from_spec(spec);spec.loader.exec_module(cs)
spec=importlib.util.spec_from_file_location('status_fixture',ROOT/'test/shell.d/fixtures/agent-status-test.py')
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)


class WidgetStopTests(unittest.TestCase):
  add_process=f.StatusTests.add_process

  def setUp(self):
    f.StatusTests.setUp(self)
    self.boot='12345678-1234-1234-1234-123456789abc'
    self.proc.boot_id=self.boot
    self.actions=[];self.notified=[]
    self.data=self.root/'data'
    env=patch.dict(os.environ,{'XDG_DATA_HOME':str(self.data)})
    env.start();self.addCleanup(env.stop)
    self.seed()

  def seed(self,kind='workspace'):
    self.cid='a'*64;self.wid='b'*32;self.instance='568a857f-e55a-4420-9411-be8c1b183113'
    self.kind=kind;self.running=True;self.signal='15';self.rootless='true';self.started='2026-11-08T00:00:00Z'
    self.add_process(10,'codex','/opt/codex/bin/codex',namespace=('pid:[2]','mnt:[2]'),ppid=20)
    self.add_process(20,'tini','/usr/bin/tini',namespace=('pid:[2]','mnt:[2]'))
    (self.data/'omarchy/workspaces').mkdir(parents=True,exist_ok=True,mode=0o700)
    self.registry=self.data/'omarchy/workspaces/project/workspace.json'
    self.registry.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    self.registry.write_text(json.dumps({'version':1,'name':'project','id':self.wid,'mode':'clone','source':'/original/source','directory':str(self.registry.parent/'repo')}));self.registry.chmod(0o600)
    (self.registry.parent/'identity').write_bytes(SECRET)
    self.target=(self.cid,self.boot,10,100)

  def query(self,args,json_output=True):
    self.calls.append(args)
    self.assertFalse(any(x in args for x in ('stop','kill','rm','exec','start')))
    if args[2]=='info':return self.rootless
    if args[2]=='ps':
      if '--filter' in args:return json.dumps(self.cid) if self.running else ''
      return [{'Id':self.cid}] if self.running else []
    if args[2]=='inspect':
      self.assertNotIn('Env',args[4]);self.assertNotIn('Auth',args[4])
      if '.Config.StopSignal' in args[4]:return '\t'.join(json.dumps(v) for v in (self.cid,self.running,self.started,self.signal,self.instance))
      name='omarchy-workspace-'+self.wid if self.kind=='workspace' else 'omarchy-agent-codex-'+self.instance.replace('-','')[:12]
      return '\t'.join(json.dumps(v) for v in (self.cid,name,20,self.kind,'codex',self.wid if self.kind=='workspace' else '',None,None,[]))
    raise AssertionError(args)

  def action(self,command):
    self.actions.append(command);self.running=False

  def request(self,confirm=lambda row:True,action=None,notify=None,clock=lambda:0):
    return cs.request_stop(self.target,self.proc,lambda:self.query,confirm,action or self.action,notify or (lambda:self.notified.append('refresh')),clock)

  def test_workspace_and_harness_stop_one_exact_id_without_force_or_deletion(self):
    original=Path.open
    def private(path,*args,**kwargs):
      if path.name in ('identity','identity.pub','ssh_config','known_hosts'):raise AssertionError('Credential content read')
      return original(path,*args,**kwargs)
    for kind in ('workspace','agent'):
      with self.subTest(kind=kind):
        self.seed(kind);self.actions.clear();self.notified.clear()
        with patch.object(Path,'open',private):
          self.assertEqual(self.request(),'stopped')
        self.assertEqual(self.actions,[['podman','--remote=false','stop','--time=-1',self.cid]])
        self.assertEqual(self.notified,['refresh'])
        self.assertTrue(self.registry.exists())

  def test_cancel_is_not_stop_and_sends_no_command(self):
    self.assertEqual(self.request(confirm=lambda row:False),'cancelled')
    self.assertEqual(self.actions,[]);self.assertEqual(self.notified,[])

  def test_invalid_or_injected_identity_never_queries_or_stops(self):
    for index,value in ((0,'--all'),(0,'a'*64+';echo BAD'),(1,'bad boot'),(2,True),(2,-1),(3,9007199254740992)):
      with self.subTest(index=index,value=value):
        target=list(self.target);target[index]=value
        self.calls.clear()
        with self.assertRaises(cs.Unavailable):cs.request_stop(tuple(target),self.proc,lambda:self.query,lambda row:True,self.action,lambda:None)
        self.assertFalse(self.calls);self.assertFalse(self.actions)

  def test_changed_identity_during_confirmation_requires_refresh(self):
    for case in ('cid','restart','process','namespace','registry','boot','started','instance'):
      with self.subTest(case=case):
        self.seed('agent' if case=='instance' else 'workspace');self.actions.clear()
        def changed(row):
          if case=='cid':self.cid='c'*64
          elif case=='restart':self.add_process(20,'tini','/usr/bin/tini',namespace=('pid:[2]','mnt:[2]'),start=200)
          elif case=='process':self.add_process(10,'codex','/different/codex',namespace=('pid:[2]','mnt:[2]'),ppid=20)
          elif case=='namespace':self.add_process(10,'codex','/opt/codex/bin/codex',namespace=('pid:[3]','mnt:[3]'),ppid=20)
          elif case=='registry':self.registry.unlink()
          elif case=='boot':self.proc.boot_id='87654321-1234-1234-1234-123456789abc'
          elif case=='instance':self.instance='168a857f-e55a-4420-9411-be8c1b183113'
          else:self.started='replacement-start'
          return True
        with self.assertRaises(cs.Unavailable):self.request(confirm=changed)
        self.assertFalse(self.actions)
        self.proc.boot_id=self.boot

  def test_unsafe_or_unmanaged_sources_never_reach_confirmation(self):
    for case in ('rootful','signal','unmanaged','no-registry','host-namespace','container-observer'):
      with self.subTest(case=case):
        self.seed();self.proc.container_observer=False
        if case=='rootful':self.rootless='false'
        elif case=='signal':self.signal='SIGKILL'
        elif case=='unmanaged':self.kind='other'
        elif case=='no-registry':self.registry.unlink()
        elif case=='host-namespace':self.add_process(20,'tini','/usr/bin/tini')
        else:self.proc.container_observer=True
        confirm=unittest.mock.Mock(return_value=True)
        with self.assertRaises(cs.Unavailable):self.request(confirm=confirm)
        confirm.assert_not_called();self.assertFalse(self.actions)

  def test_root_and_weak_name_only_processes_never_get_a_stop(self):
    with patch.object(cs.os,'getuid',return_value=0):
      with self.assertRaises(cs.Unavailable):self.request()
    self.add_process(10,'codex','/unrecognized/binary',namespace=('pid:[2]','mnt:[2]'),ppid=20)
    with self.assertRaises(cs.Unavailable):self.request()
    self.assertFalse(self.actions)

  def test_shared_namespace_cannot_select_a_container_by_guesswork(self):
    rows=cs.status.container_snapshot(self.query,self.proc)
    with patch.object(cs.status,'container_snapshot',return_value=rows+[{**rows[0],'id':'d'*64,'name':'another-container'}]):
      with self.assertRaises(cs.Unavailable):self.request()
    self.assertFalse(self.actions)

  def test_confirmation_expiry_before_and_after_recheck_does_not_stop(self):
    for times in ((0,121),(0,0,121)):
      with self.subTest(times=times):
        clock=unittest.mock.Mock(side_effect=times)
        with self.assertRaises(cs.Unavailable):self.request(clock=clock)
        self.assertFalse(self.actions)

  def test_engine_failure_and_unconfirmed_result_never_retry_or_force(self):
    def fails(command):self.actions.append(command);raise cs.Unavailable('not confirmed')
    with self.assertRaises(cs.Unavailable):self.request(action=fails)
    self.assertEqual(len(self.actions),1);self.assertEqual(self.notified,['refresh'])
    self.actions.clear();self.notified.clear()
    with self.assertRaises(cs.Unavailable):self.request(action=self.actions.append)
    self.assertEqual(len(self.actions),1);self.assertEqual(self.notified,['refresh'])

  def test_refresh_failure_does_not_rewrite_success(self):
    with contextlib.redirect_stderr(io.StringIO()) as errors:
      self.assertEqual(self.request(notify=lambda:(_ for _ in ()).throw(OSError('fixture'))),'stopped')
    self.assertIn('refresh unavailable',errors.getvalue())

  def test_foreground_default_no_terminal_confirmation_and_warning(self):
    class Terminal(io.StringIO):
      def isatty(self):return True
      def fileno(self):return 0
    streams=[Terminal(),Terminal(),Terminal()]
    with patch.object(sys,'argv',['container-stop',*map(str,self.target)]),patch.object(sys,'stdin',streams[0]),patch.object(sys,'stdout',streams[1]),patch.object(sys,'stderr',streams[2]),patch.object(cs.os,'tcgetpgrp',return_value=123),patch.object(cs.os,'getpgrp',return_value=123),patch.object(cs.status,'Proc',return_value=self.proc),patch.object(cs.status,'Query',return_value=self.query),patch.object(cs.subprocess,'run',return_value=subprocess.CompletedProcess([],1)) as run:
      self.assertEqual(cs.main(),0)
      self.assertEqual(run.call_args.args[0],['gum','confirm','--default=false','Stop this exact container?'])
      self.assertEqual(run.call_count,1)
    self.assertIn('Unsaved work may be lost',streams[1].getvalue())
    self.assertIn('Cancelled; no stop requested',streams[1].getvalue())
    self.assertFalse(self.actions)


if __name__=='__main__':unittest.main()
