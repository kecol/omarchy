import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(os.environ['ROOT'])
spec = importlib.util.spec_from_file_location('agent_status', ROOT/'default/agents/status.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
SECRET = 'PRIVATE-PROMPT-DO-NOT-REPORT'


class StatusTests(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory(prefix='agent status test ')
    self.addCleanup(self.temp.cleanup)
    self.root = Path(self.temp.name)
    self.proc_root = self.root/'proc'
    self.proc_root.mkdir()
    boot = self.proc_root/'sys/kernel/random'
    boot.mkdir(parents=True)
    (boot/'boot_id').write_text('fixture-boot\n')
    self.add_process(500, 'python3', '/usr/bin/python3', command=b'python3\0-I\0report.py\0')
    (self.proc_root/'self').symlink_to('500')
    self.proc = m.Proc(self.proc_root)
    self.proc.container_observer = False
    self.calls = []
    self.agent_rows = []
    self.info = {}
    self.ids = []
    self.details = ''
    self.default = 'container'
    self.sock = socket.socket(socket.AF_UNIX)
    self.sock.bind(str(self.root/'herdr.sock'))
    self.addCleanup(self.sock.close)
    self.sessions=[{'name':'default','running':True,'socket_path':str(self.root/'herdr.sock')}]
    self.session_agents={}

  def add_process(self, pid, comm, exe, namespace=('pid:[1]', 'mnt:[1]'), start=100, command=b'', cwd='/project', ppid=1):
    directory = self.proc_root/str(pid)
    directory.mkdir(exist_ok=True)
    fields = ['0']*20
    fields[0], fields[1], fields[19] = 'S', str(ppid), str(start)
    (directory/'stat').write_text(f'{pid} ({comm}) '+ ' '.join(fields)+'\n')
    (directory/'comm').write_text(comm+'\n')
    (directory/'cmdline').write_bytes(command)
    for name, target in [('exe',exe),('cwd',cwd),('ns/pid',namespace[0]),('ns/mnt',namespace[1])]:
      path=directory/name
      path.parent.mkdir(exist_ok=True)
      if path.is_symlink():path.unlink()
      path.symlink_to(target)
    return directory

  def query(self, args, json_output=True):
    self.calls.append(args)
    if args == ['podman','--remote=false','ps','--format=json']:
      return [{'Id':cid} for cid in self.ids]
    if args[:3] == ['podman','--remote=false','inspect']:
      self.assertIn('{{json .ID}}',args[4])
      self.assertNotIn('{{json .Id}}',args[4])
      self.assertNotIn('Env',args[4])
      self.assertNotIn('Auth',args[4])
      return self.details
    if args == ['herdr','session','list','--json']:
      return {'sessions':self.sessions}
    if args[:2] == ['herdr','--session'] and args[3:] == ['agent','list']:
      rows=self.agent_rows if args[2]=='default' else self.session_agents.get(args[2],[])
      if isinstance(rows,Exception):raise rows
      return {'result':{'agents':rows}}
    if args[:5] == ['herdr','--session','default','pane','process-info']:
      return {'result':{'process_info':self.info[args[-1]]}}
    if args == ['omarchy-agent-mode']:
      return self.default
    self.fail('Unexpected adapter invocation: '+str(args))

  def row(self, pane='w1:p1', pid=10, **extra):
    self.agent_rows.append({'agent':'pi','pane_id':pane,'agent_status':'working','terminal_title':SECRET,'agent_session':{'path':SECRET},**extra})
    self.info[pane]={'foreground_process_group_id':pid,'foreground_processes':[{'pid':pid,'argv':[SECRET],'cmdline':SECRET}],'shell_pid':900}

  def report(self, **options):
    return m.build_report(self.proc,self.query,workspace_reader=lambda:{'workspace-id':'test-project'},**options)

  def test_host_first_and_deduplicate_herdr_without_prompt_fields(self):
    self.add_process(10,'pi','/tools/pi',cwd='/home/user/work')
    self.row()
    self.row(pane='w2:p3')
    report=self.report()
    self.assertEqual(len(report['processes']),1)
    row=report['processes'][0]
    self.assertEqual(row['boundary'],'host')
    self.assertEqual(row['identity'],{'pid':10,'start_ticks':100,'boot_id':'fixture-boot'})
    self.assertEqual(row['sources'],['procfs','herdr'])
    self.assertEqual(row['activity'],{'state':'working','source':'herdr'})
    self.assertEqual(len(row['herdr']),2)
    self.assertNotIn(SECRET,json.dumps(report))

  def test_container_extension_process_is_not_working_agent_claim(self):
    ns=('pid:[2]','mnt:[2]')
    self.add_process(10,'pi','/tools/pi')
    self.add_process(20,'codex','/home/workspace/.vscode-server/extensions/openai.chatgpt-version/bin/codex',namespace=ns,cwd='/workspace')
    self.add_process(30,'sshd','/usr/bin/sshd',namespace=ns)
    cid='a'*64
    self.ids=[cid]
    self.details='\t'.join(json.dumps(x) for x in [cid,'workspace-container',30,'',None,'workspace-id'])+'\n'
    report=self.report()
    self.assertEqual([r['boundary'] for r in report['processes']],['host','container'])
    row=report['processes'][1]
    self.assertEqual(row['role'],'extension-associated process')
    self.assertEqual(row['activity']['state'],'process-observed')
    self.assertEqual(row['container']['workspace_name'],'test-project')
    self.assertFalse(any(c[0]=='omarchy-workspace-list' for c in self.calls))

  def test_namespace_gap_sorts_before_container_and_never_assumes_safe(self):
    self.add_process(10,'pi','/pi',namespace=('pid:[9]','mnt:[9]'))
    report=self.report(use_podman=False)
    self.assertEqual(report['processes'][0]['boundary'],'unknown')
    self.assertEqual(report['coverage']['podman']['state'],'disabled')

  def test_host_pid_container_requires_mount_namespace_match(self):
    ns=('pid:[1]','mnt:[2]')
    self.add_process(10,'pi','/pi')
    self.add_process(20,'codex','/codex',namespace=ns)
    self.add_process(30,'sshd','/sshd',namespace=ns)
    cid='b'*64;self.ids=[cid]
    self.details='\t'.join(json.dumps(x) for x in [cid,'host-pid-container',30,'agent','codex',None])
    self.assertEqual([r['boundary'] for r in self.report()['processes']],['host','container'])

  def test_observer_container_does_not_call_itself_host(self):
    self.proc.container_observer=True
    self.add_process(10,'pi','/pi')
    self.assertEqual(self.report()['processes'][0]['boundary'],'observer')

  def test_process_name_only_is_candidate_and_generic_node_not_agent(self):
    self.add_process(10,'pi','/some/native-program')
    self.add_process(20,'node','/usr/bin/node',command=b'node\0/project/cli.js\0'+SECRET.encode())
    report=self.report()
    self.assertEqual(report['processes'],[])
    self.assertEqual([r['agent'] for r in report['candidates']],['pi'])
    self.assertNotIn(SECRET,json.dumps(report))

  def test_interpreter_entrypoint_reads_only_first_two_tokens(self):
    prefix=b'node\0/tools/node_modules/@mariozechner/pi-coding-agent/dist/cli.js\0'
    self.add_process(10,'node','/usr/bin/node',command=prefix+SECRET.encode())
    reads=[]
    original=Path.open
    class Tracked(io.BytesIO):
      def close(inner):
        reads.append(inner.tell())
        super().close()
    def opened(path,*args,**kwargs):
      if path==self.proc_root/'10/cmdline':return Tracked(prefix+SECRET.encode())
      return original(path,*args,**kwargs)
    with patch.object(Path,'open',opened):report=self.report()
    self.assertEqual(report['processes'][0]['agent'],'pi')
    self.assertEqual(reads,[len(prefix)])
    self.assertNotIn(SECRET,json.dumps(report))

  def test_remote_pid_collision_is_unverified_and_never_queried(self):
    self.add_process(10,'pi','/pi')
    self.row(machine_id='remote-machine')
    report=self.report()
    self.assertEqual(report['processes'][0]['herdr'],[])
    self.assertEqual(report['unverified_observations'][0]['boundary'],'remote-unverified')
    self.assertFalse(any('process-info' in c for c in self.calls))
    self.assertFalse(any('--machine' in c or '--remote' in c for c in self.calls))

  def test_stale_hint_is_not_a_shell_agent(self):
    self.add_process(10,'bash','/usr/bin/bash')
    self.row()
    report=self.report()
    self.assertEqual(report['processes'],[])
    self.assertEqual(len(report['unverified_observations']),1)

  def test_pid_reuse_drops_stale_identification(self):
    self.add_process(10,'pi','/pi')
    processes,coverage=self.proc.scan()
    with patch.object(self.proc,'scan',return_value=(processes,coverage)), patch.object(self.proc,'identity',return_value={'pid':10,'ppid':1,'start_ticks':101}):
      report=self.report()
    self.assertEqual(report['processes'],[])
    self.assertEqual(report['vanished_identifications'],1)

  def test_pid_exit_after_herdr_match_keeps_unverified_observation(self):
    self.add_process(10,'pi','/pi')
    self.row()
    processes,coverage=self.proc.scan()
    old={'pid':10,'ppid':1,'start_ticks':100}
    new={**old,'start_ticks':101}
    with patch.object(self.proc,'scan',return_value=(processes,coverage)), patch.object(self.proc,'identity',side_effect=[old,new]):
      report=self.report()
    self.assertEqual(report['processes'],[])
    self.assertEqual(len(report['unverified_observations']),1)
    self.assertIn('reused',report['unverified_observations'][0]['reason'])
    pane=report['herdr_sessions'][0]['panes'][0]
    self.assertEqual(pane['match_state'],'unverified')
    self.assertEqual(pane['process_matches'],[])

  def test_unknown_sources_are_not_reported_as_empty_success(self):
    self.add_process(10,'pi','/pi')
    def missing(*args,**kwargs):raise m.Unavailable('probe unavailable')
    report=m.build_report(self.proc,missing)
    self.assertEqual(report['processes'][0]['agent'],'pi')
    self.assertEqual(report['coverage']['podman']['state'],'unavailable')
    self.assertEqual(report['coverage']['herdr']['state'],'unavailable')
    self.assertEqual(report['launch_default'],'unknown')

  def test_skips_optional_adapters_and_handles_invalid_default(self):
    self.default='BROKEN'
    report=self.report(use_herdr=False,use_podman=False)
    self.assertEqual(self.calls,[['omarchy-agent-mode']])
    self.assertEqual(report['launch_default'],'unknown')

  def test_failed_session_query_retains_other_evidence(self):
    self.row()
    self.info['w1:p1']=None
    report=self.report()
    self.assertEqual(report['coverage']['herdr']['state'],'partial')
    self.assertEqual(len(report['unverified_observations']),1)

  def test_stat_comm_parentheses_and_console_control_escaping(self):
    self.add_process(10,'pi) weird (name','/pi',cwd='/tmp/\x1b[31m\n\u202efile')
    report=self.report(use_herdr=False)
    output=io.StringIO()
    with contextlib.redirect_stdout(output):m.print_report(report)
    text=output.getvalue()
    self.assertNotIn('\x1b',text)
    self.assertNotIn('\u202e',text)
    self.assertIn('\\u001b',text)
    self.assertIn('\\u202e',text)

  def test_unrecognized_herdr_kind_is_retained_without_pid_promotion(self):
    self.add_process(10,'pi','/pi')
    self.row(agent='future-agent')
    report=self.report()
    self.assertEqual(len(report['processes']),1)
    self.assertFalse(report['processes'][0]['corroborated'])
    self.assertEqual(report['unverified_observations'][0]['agent'],'future-agent')

  def test_malformed_local_session_is_partial_not_empty_success(self):
    def bad(args,**kwargs):return {'sessions':[{'name':'broken'}]}
    rows,coverage=m.herdr_snapshot(bad)
    self.assertEqual(rows,[])
    self.assertEqual(coverage['state'],'partial')

  def test_registry_api_never_creates_state_or_queries_engine(self):
    data=self.root/'empty-data'
    with patch.dict(os.environ,{'OMARCHY_PATH':str(ROOT),'XDG_DATA_HOME':str(data)}), patch.object(subprocess,'run',side_effect=AssertionError('registry must not query engine')):
      self.assertEqual(m.workspace_names(),{})
    self.assertFalse(data.exists())

  def test_query_bounds_timeout_output_and_invalid_json(self):
    with self.assertRaisesRegex(m.Unavailable,'timed out'):
      m.Query(.05)(['/usr/bin/sleep','2'])
    with self.assertRaisesRegex(m.Unavailable,'exceeded limit'):
      m.Query()([sys.executable,'-I','-c',f'print("x"*{m.LIMIT+65536})'])
    with self.assertRaises(m.Unavailable) as error:
      m.Query()([sys.executable,'-I','-c',f'import sys;sys.stderr.write({SECRET!r});sys.exit(1)'])
    self.assertNotIn(SECRET,str(error.exception))
    with self.assertRaises(m.Unavailable):
      m.Query()([sys.executable,'-I','-c','print("not json")'])

  def test_root_invocation_fails_before_any_probe(self):
    with patch.object(sys,'argv',['agent-status']), patch.object(os,'getuid',return_value=0), patch.object(m,'build_report',side_effect=AssertionError('must not probe')), contextlib.redirect_stderr(io.StringIO()):
      with self.assertRaises(SystemExit) as error:m.main()
    self.assertEqual(error.exception.code,2)

  def test_grouped_panes_reference_existing_identities_without_extra_queries(self):
    self.add_process(10,'pi','/pi')
    self.add_process(20,'codex','/codex')
    self.row()
    report=self.report()
    self.assertEqual(len(report['processes']),2)
    self.assertEqual(len(report['herdr_sessions']),1)
    session=report['herdr_sessions'][0]
    self.assertEqual(session['state'],'ok')
    self.assertEqual(session['reported_agent_count'],1)
    pane=session['panes'][0]
    self.assertEqual(pane['match_state'],'matched')
    self.assertEqual(pane['reported_activity'],'working')
    pi=next(p for p in report['processes'] if p['agent']=='pi')
    self.assertEqual(pane['process_matches'],[{'identity':pi['identity'],'boundary':'host'}])
    self.assertEqual(len([c for c in self.calls if c[0]=='herdr']),3)
    self.assertNotIn(SECRET,json.dumps(report))

  def test_empty_stopped_and_unavailable_sessions_are_distinct(self):
    socket_path=str(self.root/'herdr.sock')
    self.sessions += [{'name':'empty','running':True,'socket_path':socket_path},{'name':'stopped','running':False},{'name':'offline','running':True,'socket_path':socket_path}]
    self.session_agents['offline']=m.Unavailable('unavailable')
    report=self.report()
    sessions={s['name']:s for s in report['herdr_sessions']}
    self.assertEqual(sessions['empty']['state'],'ok')
    self.assertEqual(sessions['empty']['reported_agent_count'],0)
    self.assertEqual(sessions['stopped']['state'],'not-running')
    self.assertIsNone(sessions['stopped']['reported_agent_count'])
    self.assertEqual(sessions['offline']['state'],'unavailable')
    self.assertIsNone(sessions['offline']['reported_agent_count'])
    self.assertFalse(any('stopped' in c for c in self.calls))
    self.assertEqual(report['coverage']['herdr']['state'],'partial')

  def test_failed_pid_query_keeps_session_pane_and_partial_coverage(self):
    self.row();self.info['w1:p1']=None
    session=self.report()['herdr_sessions'][0]
    self.assertEqual(session['state'],'partial')
    self.assertEqual(session['reported_agent_count'],1)
    self.assertEqual(session['panes'][0]['match_state'],'unverified')
    self.assertEqual(session['errors'],1)

  def test_group_remote_pid_collision_has_no_local_reference(self):
    self.add_process(10,'pi','/pi')
    self.row(machine_id='remote')
    pane=self.report()['herdr_sessions'][0]['panes'][0]
    self.assertEqual(pane['match_state'],'remote-unverified')
    self.assertEqual(pane['process_matches'],[])
    self.assertFalse(any('process-info' in c for c in self.calls))

  def test_duplicate_pane_reports_merge_and_expose_activity_conflict(self):
    self.add_process(10,'pi','/pi')
    self.row();self.row(agent_status='idle')
    report=self.report()
    self.assertEqual(len(report['processes']),1)
    session=report['herdr_sessions'][0]
    self.assertEqual(session['reported_agent_count'],2)
    self.assertEqual(len(session['panes']),1)
    self.assertEqual(len(session['panes'][0]['process_matches']),1)
    self.assertEqual(session['panes'][0]['reported_activity'],'conflicting-reports')

  def test_grouped_session_names_remain_case_sensitive(self):
    socket_path=str(self.root/'herdr.sock')
    self.sessions=[{'name':name,'running':True,'socket_path':socket_path} for name in ('R5L4','r5l4')]
    self.assertEqual([s['name'] for s in self.report()['herdr_sessions']],['R5L4','r5l4'])

  def test_empty_inventory_is_not_disabled_or_unavailable(self):
    self.sessions=[]
    report=self.report()
    output=io.StringIO()
    with contextlib.redirect_stdout(output):m.print_report(report)
    self.assertIn('No local sessions listed.',output.getvalue())
    report=self.report(use_herdr=False)
    self.assertEqual(report['herdr_sessions'],[])
    output=io.StringIO()
    with contextlib.redirect_stdout(output):m.print_report(report)
    self.assertIn('Local session inventory disabled.',output.getvalue())
    self.assertNotIn('No local sessions listed.',output.getvalue())

  def test_duplicate_session_name_is_partial_and_queried_once(self):
    self.sessions.append(dict(self.sessions[0]))
    report=self.report()
    self.assertEqual(len(report['herdr_sessions']),1)
    self.assertEqual(report['coverage']['herdr']['state'],'partial')
    self.assertEqual(len([c for c in self.calls if c[-2:]==['agent','list']]),1)

  def test_query_drops_remote_context_and_agent_socket(self):
    names=('CONTAINER_HOST','CONTAINER_CONNECTION','DOCKER_HOST','SSH_AUTH_SOCK','HERDR_MACHINE','HERDR_MACHINE_ID','HERDR_REMOTE','HERDR_SESSION')
    code='import os,json;print(json.dumps({k:os.environ.get(k) for k in '+repr(names)+'}))'
    with patch.dict(os.environ,{name:'must-not-forward' for name in names}):
      value=m.Query()([sys.executable,'-I','-c',code])
    self.assertTrue(all(value[name] is None for name in names))


if __name__=='__main__':
  unittest.main()
