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
    environment=patch.dict(os.environ,{'OMARCHY_PATH':str(ROOT)})
    environment.start()
    self.addCleanup(environment.stop)
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
    self.session_snapshots={}
    self.workspace_metadata={'workspace-id':{'name':'test-project','editor_profile':None}}

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
    if args[0] in ('hyprctl','ss'):
      raise m.Unavailable('desktop fixture unavailable')
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
    if args[:2] == ['herdr','--session'] and args[3:] == ['api','snapshot']:
      snapshot=self.session_snapshots.get(args[2])
      if snapshot is None:raise m.Unavailable('labels unavailable')
      return {'result':{'snapshot':snapshot}}
    if args[:5] == ['herdr','--session','default','pane','process-info']:
      return {'result':{'process_info':self.info[args[-1]]}}
    if args == ['omarchy-agent-mode']:
      return self.default
    self.fail('Unexpected adapter invocation: '+str(args))

  def row(self, pane='w1:p1', pid=10, **extra):
    self.agent_rows.append({'agent':'pi','pane_id':pane,'agent_status':'working','terminal_title':SECRET,'agent_session':{'path':SECRET},**extra})
    self.info[pane]={'foreground_process_group_id':pid,'foreground_processes':[{'pid':pid,'argv':[SECRET],'cmdline':SECRET}],'shell_pid':900}

  def report(self, **options):
    options.setdefault('use_desktop',False)
    return m.build_report(self.proc,self.query,workspace_reader=lambda:self.workspace_metadata,**options)

  def test_read_only_registry_profiles_need_no_credentials_and_reject_duplicate_ids(self):
    data=self.root/'data'
    root=data/'omarchy/workspaces';root.mkdir(parents=True,mode=0o700)
    identity='a'*32
    def registered(name):
      directory=root/name;directory.mkdir(mode=0o700)
      metadata={'version':1,'name':name,'id':identity,'mode':'clone','source':'/source','directory':str(directory/'repo')}
      path=directory/'workspace.json';path.write_text(json.dumps(metadata));path.chmod(0o600)
      (directory/'identity').write_text(SECRET)
      return directory
    directory=registered('project')
    original=Path.open
    def safe(path,*args,**kwargs):
      if path.name in ('identity','identity.pub','ssh_config','known_hosts'):raise AssertionError('credential/connection content read')
      return original(path,*args,**kwargs)
    with patch.dict(os.environ,{'XDG_DATA_HOME':str(data)}):
      with patch.object(Path,'open',safe):
        self.assertEqual(m.workspace_snapshot(),{identity:{'name':'project','editor_profile':directory/'vscode-data','mode':'clone','source':'/source','directory':str(directory/'repo')}})
      registered('another')
      with self.assertRaises(m.Unavailable):m.workspace_snapshot()

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
    self.details='\t'.join(json.dumps(x) for x in [cid,'workspace-container',30,'',None,'workspace-id',None,None,[]])+'\n'
    report=self.report()
    self.assertEqual([r['boundary'] for r in report['processes']],['host','container'])
    row=report['processes'][1]
    self.assertEqual(row['role'],'extension-associated process')
    self.assertEqual(row['activity']['state'],'process-observed')
    self.assertEqual(row['container']['workspace_name'],'test-project')
    self.assertFalse(any(c[0]=='omarchy-workspace-list' for c in self.calls))

  def project_report(self, mounts=None, target='/workspace/abc123', managed='agent', key='abc123'):
    ns=('pid:[2]','mnt:[2]')
    self.add_process(20,'codex','/opt/codex/bin/codex',namespace=ns,cwd='/workspace/abc123/subdir')
    self.add_process(30,'bash','/usr/bin/bash',namespace=ns)
    cid='c'*64;self.ids=[cid]
    if mounts is None:mounts=[{'type':'bind','source':'/projects/numerai','destination':target,'rw':True}]
    self.details='\t'.join(json.dumps(x) for x in [cid,'agent-container',30,managed,'codex',None,target,key,mounts])
    return self.report()

  def test_project_paths_keep_host_container_key_and_cwd_distinct(self):
    row=self.project_report()['processes'][0]
    self.assertEqual(row['container']['project'],{'state':'matched','host_path':'/projects/numerai',
      'container_path':'/workspace/abc123','project_id':'abc123','access':'read-write'})
    self.assertEqual(row['cwd'],'/workspace/abc123/subdir')
    self.assertNotIn(SECRET,json.dumps(row))
    text=io.StringIO()
    with contextlib.redirect_stdout(text):m.print_report(self.project_report())
    for value in ('/projects/numerai','/workspace/abc123','Project key: abc123','read-write'):
      self.assertIn(value,text.getvalue())

  def test_project_read_only_mount_is_not_reported_read_write(self):
    row=self.project_report([{'type':'bind','source':'/projects/readonly','destination':'/workspace/abc123','rw':False}])['processes'][0]
    self.assertEqual(row['container']['project']['access'],'read-only')

  def test_ambiguous_project_mounts_do_not_choose_a_host_directory(self):
    mounts=[{'type':'bind','source':path,'destination':'/workspace/abc123','rw':True} for path in ('/first','/second')]
    project=self.project_report(mounts)['processes'][0]['container']['project']
    self.assertEqual(project['state'],'ambiguous');self.assertIsNone(project['host_path'])
    self.assertEqual(project['access'],'unknown')
    self.assertEqual(project['container_path'],'/workspace/abc123')

  def test_invalid_project_metadata_fails_closed_without_path_reads(self):
    bad=[[],[{'type':'volume','source':'/private','destination':'/workspace/abc123','rw':True}],
      [{'type':'bind','source':'relative','destination':'/workspace/abc123','rw':True}],
      [{'type':'bind','source':'/a/../b','destination':'/workspace/abc123','rw':True}],
      [{'type':'bind','source':'/private','destination':'/other','rw':True}],
      [{'type':'bind','source':'/private','destination':'/workspace/abc123','rw':'true'}]]
    for mounts in bad:
      with self.subTest(mounts=mounts):
        row=self.project_report(mounts)['processes'][0]['container']['project']
        self.assertEqual(row['state'],'unavailable');self.assertIsNone(row['host_path'])
    for target in ('/home/agent','/workspace/../private','relative','/workspace/abc\u0000def'):
      row=self.project_report(target=target)['processes'][0]['container']['project']
      self.assertEqual(row['state'],'unavailable');self.assertIsNone(row['host_path'])
    row=self.project_report(managed='other')['processes'][0]['container']['project']
    self.assertIsNone(row['host_path']);self.assertIsNone(row['container_path'])

  def test_reused_container_init_pid_discards_project_mapping(self):
    original=m.container_snapshot
    def stale(query,proc):
      rows=original(query,proc)
      self.add_process(30,'bash','/usr/bin/bash',namespace=('pid:[2]','mnt:[2]'),start=200)
      return rows
    with patch.object(m,'container_snapshot',stale):
      row=self.project_report()['processes'][0]['container']['project']
    self.assertEqual(row['state'],'unavailable');self.assertIsNone(row['host_path'])
    self.assertEqual(row['access'],'unknown')

  def workspace_report(self, mounts=None, registry=None):
    ns=('pid:[2]','mnt:[2]')
    self.add_process(20,'codex','/home/workspace/.vscode-server/extensions/openai.chatgpt-version/bin/codex',namespace=ns,cwd='/home/workspace')
    self.add_process(30,'sshd','/usr/bin/sshd',namespace=ns)
    cid='d'*64;self.ids=[cid]
    if mounts is None:mounts=[{'type':'bind','source':'/clones/editor/repo','destination':'/workspace','rw':True}]
    if registry is None:registry={'name':'editor','editor_profile':None,'mode':'clone','source':'/original/source','directory':'/clones/editor/repo'}
    self.workspace_metadata={'workspace-id':registry} if registry else {}
    self.details='\t'.join(json.dumps(x) for x in [cid,'editor-container',30,'',None,'workspace-id',None,None,mounts])
    return self.report()

  def test_editor_clone_files_source_and_internal_path_are_distinct(self):
    report=self.workspace_report();row=report['processes'][0];files=row['container']['workspace_files']
    self.assertEqual(files,{'state':'matched','host_path':'/clones/editor/repo','container_path':'/workspace',
      'access':'read-write','registry_state':'matched','mode':'clone','source_directory':'/original/source'})
    self.assertEqual(row['cwd'],'/home/workspace')
    self.assertEqual(row['container']['workspace_id'],'workspace-id')
    self.assertEqual(row['container']['workspace_name'],'editor')
    self.assertEqual(len([c for c in self.calls if c[:3]==['podman','--remote=false','inspect']]),1)
    out=io.StringIO()
    with contextlib.redirect_stdout(out):m.print_report(report)
    for value in ('/clones/editor/repo','/original/source','/workspace','workspace-id','not working files'):
      self.assertIn(value,out.getvalue())

  def test_editor_live_mode_and_read_only_mount_are_observed_separately(self):
    files=self.workspace_report([{'type':'bind','source':'/live','destination':'/workspace','rw':False}],
      {'mode':'mount','source':'/live','directory':'/live'})['processes'][0]['container']['workspace_files']
    self.assertEqual(files['mode'],'mount');self.assertEqual(files['access'],'read-only')
    self.assertEqual(files['source_directory'],'/live')

  def test_editor_registry_mismatch_does_not_override_actual_bind(self):
    files=self.workspace_report(registry={'mode':'clone','source':'/original','directory':'/different'})['processes'][0]['container']['workspace_files']
    self.assertEqual(files['state'],'matched');self.assertEqual(files['host_path'],'/clones/editor/repo')
    self.assertEqual(files['registry_state'],'mismatch')
    self.assertIsNone(files['mode']);self.assertIsNone(files['source_directory'])

  def test_editor_invalid_or_missing_registry_never_invents_source_mode(self):
    for registry in ({},{'mode':'clone','source':'relative','directory':'/clones/editor/repo'},
      {'mode':'mount','source':'/elsewhere','directory':'/clones/editor/repo'},
      {'mode':'unknown','source':'/original','directory':'/clones/editor/repo'}):
      files=self.workspace_report(registry=registry)['processes'][0]['container']['workspace_files']
      self.assertEqual(files['state'],'matched');self.assertEqual(files['registry_state'],'unavailable')
      self.assertIsNone(files['mode']);self.assertIsNone(files['source_directory'])

  def test_editor_missing_ambiguous_or_volume_mount_stays_unverified(self):
    good={'type':'bind','source':'/clones/editor/repo','destination':'/workspace','rw':True}
    for mounts,state in (([],'unavailable'),([good,good],'ambiguous'),([{**good,'type':'volume'}],'unavailable')):
      files=self.workspace_report(mounts)['processes'][0]['container']['workspace_files']
      self.assertEqual(files['state'],state);self.assertIsNone(files['host_path'])
      self.assertEqual(files['container_path'],'/workspace');self.assertEqual(files['access'],'unknown')
      self.assertIsNone(files['mode']);self.assertIsNone(files['source_directory'])

  def test_editor_reused_init_identity_discards_files_and_registry_semantics(self):
    original=m.container_snapshot
    def stale(query,proc):
      rows=original(query,proc)
      self.add_process(30,'sshd','/usr/bin/sshd',namespace=('pid:[2]','mnt:[2]'),start=200)
      return rows
    with patch.object(m,'container_snapshot',stale):files=self.workspace_report()['processes'][0]['container']['workspace_files']
    self.assertEqual(files['state'],'unavailable');self.assertIsNone(files['host_path'])
    self.assertIsNone(files['mode']);self.assertIsNone(files['source_directory'])

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
    self.details='\t'.join(json.dumps(x) for x in [cid,'host-pid-container',30,'agent','codex',None,None,None,[]])
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
      self.assertEqual(m.workspace_snapshot(),{})
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

  def label_fixture(self):
    self.add_process(10,'pi','/pi')
    self.row(workspace_id='w1',tab_id='w1:t1')
    snapshot={'workspaces':[{'workspace_id':'w1','label':'host - Work'}], 'tabs':[{'workspace_id':'w1','tab_id':'w1:t1','label':'pi host'}], 'agents':[{'agent':'pi','pane_id':'w1:p1','workspace_id':'w1','tab_id':'w1:t1','terminal_title':SECRET}]}
    self.session_snapshots['default']=snapshot
    return snapshot

  def test_readable_herdr_path_and_stable_ids_are_both_reported(self):
    self.label_fixture()
    report=self.report()
    evidence=report['processes'][0]['herdr'][0]
    self.assertEqual((evidence['workspace_id'],evidence['tab_id']),('w1','w1:t1'))
    self.assertEqual((evidence['workspace_label'],evidence['tab_label']),('host - Work','pi host'))
    self.assertEqual(report['herdr_sessions'][0]['labels_state'],'ok')
    pane=report['herdr_sessions'][0]['panes'][0]
    self.assertEqual(pane['tab_label'],'pi host')
    output=io.StringIO()
    with contextlib.redirect_stdout(output):m.print_report(report)
    self.assertIn('Local / host - Work / pi host / w1:p1',output.getvalue())
    self.assertIn('tab w1:t1',output.getvalue())
    self.assertNotIn(SECRET,json.dumps(report))
    self.assertEqual(len([c for c in self.calls if c[-2:]==['api','snapshot']]),1)

  def test_missing_labels_do_not_remove_pid_matches_or_invent_names(self):
    self.label_fixture();self.session_snapshots.clear()
    report=self.report()
    self.assertEqual(len(report['processes']),1)
    self.assertTrue(report['processes'][0]['corroborated'])
    evidence=report['processes'][0]['herdr'][0]
    self.assertIsNone(evidence['tab_label'])
    self.assertEqual(evidence['tab_id'],'w1:t1')
    self.assertEqual(report['herdr_sessions'][0]['labels_state'],'unavailable')
    self.assertEqual(report['herdr_sessions'][0]['state'],'partial')
    self.assertIn('Local / w1 / w1:t1 / w1:p1',m.herdr_display_path(evidence))

  def test_renames_change_labels_not_process_or_pane_identity(self):
    snapshot=self.label_fixture()
    first=self.report()
    snapshot['tabs'][0]['label']='new tab'
    snapshot['workspaces'][0]['label']='new workspace'
    second=self.report()
    self.assertEqual(first['processes'][0]['identity'],second['processes'][0]['identity'])
    self.assertEqual(second['processes'][0]['herdr'][0]['tab_label'],'new tab')
    self.assertEqual(second['herdr_sessions'][0]['panes'][0]['pane'],'w1:p1')
    self.assertEqual(len(second['processes']),1)

  def test_moved_pane_or_wrong_parent_cannot_borrow_another_tab_label(self):
    snapshot=self.label_fixture()
    snapshot['agents'][0]['tab_id']='w1:t2'
    report=self.report()
    self.assertIsNone(report['processes'][0]['herdr'][0]['tab_label'])
    self.assertEqual(report['herdr_sessions'][0]['labels_state'],'partial')
    snapshot['agents'][0]['tab_id']='w1:t1'
    snapshot['tabs'][0]['workspace_id']='w2'
    self.assertIsNone(self.report()['processes'][0]['herdr'][0]['tab_label'])

  def test_labels_are_bounded_and_console_control_characters_are_escaped(self):
    snapshot=self.label_fixture()
    snapshot['tabs'][0]['label']='\x1b[31m\n\u202epi host'
    report=self.report()
    output=io.StringIO()
    with contextlib.redirect_stdout(output):m.print_report(report)
    self.assertNotIn('\x1b',output.getvalue())
    self.assertNotIn('\u202e',output.getvalue())
    self.assertIn('\\u001b',output.getvalue())
    snapshot['tabs'][0]['label']='x'*257
    self.assertIsNone(self.report()['processes'][0]['herdr'][0]['tab_label'])

  def test_duplicate_snapshot_ids_and_bad_shape_do_not_supply_labels(self):
    snapshot=self.label_fixture()
    snapshot['tabs'].append(dict(snapshot['tabs'][0]))
    self.assertIsNone(self.report()['processes'][0]['herdr'][0]['tab_label'])
    snapshot['tabs']={}
    report=self.report()
    self.assertEqual(report['herdr_sessions'][0]['labels_state'],'unavailable')
    self.assertEqual(len(report['processes']),1)

  def test_remote_records_are_never_given_local_display_names(self):
    self.label_fixture()
    self.agent_rows[0]['machine_id']='remote'
    report=self.report()
    pane=report['herdr_sessions'][0]['panes'][0]
    self.assertIsNone(pane['workspace_label'])
    self.assertEqual(pane['match_state'],'remote-unverified')
    self.assertTrue(m.herdr_display_path(pane).startswith('Remote (unverified)'))
    self.assertFalse(any(c[-2:]==['api','snapshot'] for c in self.calls))

  def test_ids_absent_skip_label_query_and_conflicting_pane_ids_drop_names(self):
    self.row()
    self.assertEqual(self.report()['herdr_sessions'][0]['labels_state'],'not-reported')
    self.assertFalse(any(c[-2:]==['api','snapshot'] for c in self.calls))
    self.agent_rows.clear()
    self.label_fixture()
    self.row(workspace_id='w1',tab_id='w1:t2')
    pane=self.report()['herdr_sessions'][0]['panes'][0]
    self.assertIsNone(pane['tab_id'])
    self.assertIsNone(pane['tab_label'])

  def test_query_drops_remote_context_and_agent_socket(self):
    names=('CONTAINER_HOST','CONTAINER_CONNECTION','DOCKER_HOST','SSH_AUTH_SOCK','HERDR_MACHINE','HERDR_MACHINE_ID','HERDR_REMOTE','HERDR_SESSION')
    code='import os,json;print(json.dumps({k:os.environ.get(k) for k in '+repr(names)+'}))'
    with patch.dict(os.environ,{name:'must-not-forward' for name in names}):
      value=m.Query()([sys.executable,'-I','-c',code])
    self.assertTrue(all(value[name] is None for name in names))


if __name__=='__main__':
  unittest.main()
