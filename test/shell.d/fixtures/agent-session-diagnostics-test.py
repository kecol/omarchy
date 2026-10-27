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


if __name__=='__main__':unittest.main()
