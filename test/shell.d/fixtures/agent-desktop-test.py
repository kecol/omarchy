import importlib.util
import json
import os
from pathlib import Path
import unittest

ROOT=Path(os.environ['ROOT'])
spec=importlib.util.spec_from_file_location('status_fixtures',ROOT/'test/shell.d/fixtures/agent-status-test.py')
f=importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)
m=f.m
spec=importlib.util.spec_from_file_location('desktop',ROOT/'default/agents/desktop.py')
d=importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)


class DesktopTests(unittest.TestCase):
  setUpBase=f.StatusTests.setUp
  add_process=f.StatusTests.add_process
  row=f.StatusTests.row
  report=f.StatusTests.report

  def setUp(self):
    self.setUpBase()
    self.clients=[]
    self.monitors=[{'id':1,'name':'HDMI-A-1','activeWorkspace':{'id':11},'specialWorkspace':{'id':0}}]
    self.workspaces=[{'id':11,'name':'11','monitor':'HDMI-A-1'},{'id':12,'name':'12','monitor':'HDMI-A-1'}]
    self.sockets=''

  def query(self,args,json_output=True):
    if args[0]=='hyprctl':
      self.calls.append(args)
      return {'clients':self.clients,'monitors':self.monitors,'workspaces':self.workspaces}[args[-1]]
    if args[0]=='ss':
      self.calls.append(args)
      self.assertEqual(args,['ss','-xHapn'])
      return self.sockets
    return f.StatusTests.query(self,args,json_output)

  def window(self,pid=61,address='0xabc',workspace=11,**extra):
    self.clients.append({'pid':pid,'address':address,'mapped':True,'hidden':False,'class':'foot','title':f.SECRET,'initialTitle':f.SECRET,'workspace':{'id':workspace},'monitor':1,**extra})

  def socket_fd(self,pid,inode):
    directory=self.proc_root/str(pid)/'fd'
    directory.mkdir(exist_ok=True)
    path=directory/str(inode)
    if not path.is_symlink():path.symlink_to(f'socket:[{inode}]')

  def peer(self,client=50,endpoint=201):
    self.socket_fd(40,endpoint)
    self.socket_fd(client,endpoint+1)
    path=str(self.root/'herdr-client.sock')
    return f'u_str ESTAB 0 0 {path} {endpoint} * {endpoint+1} users:(("herdr",pid=40,fd=7))\n' + f'u_str ESTAB 0 0 * {endpoint+1} * {endpoint} users:(("herdr",pid={client},fd=8))\n'

  def attached_session(self):
    self.add_process(40,'herdr','/usr/bin/herdr')
    self.add_process(50,'herdr','/usr/bin/herdr',ppid=60)
    path=self.proc_root/'50/stat'
    prefix,fields=path.read_text().rsplit(')',1)
    fields=fields.split();fields[4]='123'
    path.write_text(prefix+') '+' '.join(fields)+'\n')
    self.add_process(60,'bash','/usr/bin/bash',ppid=61)
    self.add_process(61,'foot','/usr/bin/foot')
    self.add_process(10,'pi','/pi',ppid=40)
    self.row()
    self.window()
    self.socket_fd(40,100)
    self.sockets=f'u_str LISTEN 0 128 {self.root}/herdr.sock 100 * 0 users:(("herdr",pid=40,fd=6))\n'+self.peer()

  def test_direct_ancestor_maps_monitor_and_bar_workspace_without_titles(self):
    self.add_process(10,'pi','/pi',ppid=61)
    self.add_process(61,'foot','/usr/bin/foot')
    self.window()
    report=self.report(use_desktop=True)
    location=report['processes'][0]['desktop']
    self.assertEqual(location['state'],'matched')
    window=location['windows'][0]
    self.assertEqual(window['monitor']['name'],'HDMI-A-1')
    self.assertEqual(window['workspace'],{'id':11,'name':'11','slot':1,'label':'1'})
    self.assertEqual(window['association'],'process-ancestor')
    self.assertTrue(window['workspace_active'])
    self.assertNotIn(f.SECRET,json.dumps(report))

  def test_detached_herdr_server_uses_reciprocal_frontend_peer(self):
    self.attached_session()
    report=self.report(use_desktop=True)
    location=report['processes'][0]['desktop']
    self.assertEqual(location['state'],'matched')
    window=location['windows'][0]
    self.assertEqual(window['association'],'herdr-session-client')
    self.assertEqual(window['client_pid'],50)
    self.assertEqual(window['pid'],61)
    self.assertIn('visibility',location['detail'])
    session=report['herdr_sessions'][0]
    self.assertEqual(session['desktop']['windows'],location['windows'])
    self.assertFalse(any(key.startswith('_') for key in session))
    self.assertEqual(len(report['processes']),1)

  def test_control_api_connection_is_not_frontend_attachment(self):
    self.attached_session()
    self.sockets=self.sockets.replace('herdr-client.sock','herdr.sock')
    report=self.report(use_desktop=True)
    self.assertEqual(report['processes'][0]['desktop']['state'],'unknown')

  def test_wrong_server_owner_and_missing_reciprocal_peer_do_not_guess(self):
    self.attached_session()
    self.sockets=self.sockets.replace('pid=40,fd=7','pid=999,fd=7')
    self.assertEqual(self.report(use_desktop=True)['processes'][0]['desktop']['state'],'unknown')
    self.attached_session()
    self.sockets='\n'.join(line for line in self.sockets.splitlines() if 'pid=50' not in line)
    self.assertEqual(self.report(use_desktop=True)['processes'][0]['desktop']['state'],'unknown')

  def test_unix_owner_text_without_matching_kernel_fd_is_not_trusted(self):
    self.attached_session()
    (self.proc_root/'50/fd/202').unlink()
    location=self.report(use_desktop=True)['processes'][0]['desktop']
    self.assertEqual(location['state'],'unknown')

  def test_multiple_windows_are_retained_not_selected_by_focus(self):
    self.add_process(10,'pi','/pi',ppid=61)
    self.add_process(61,'code','/usr/bin/code')
    self.window()
    self.window(address='0xdef',workspace=12,focusHistoryID=0)
    location=self.report(use_desktop=True)['processes'][0]['desktop']
    self.assertEqual(location['state'],'multiple')
    self.assertEqual(len(location['windows']),2)
    self.assertIn('multiple',location['detail'])
    self.assertEqual([w['workspace_active'] for w in location['windows']],[True,False])

  def test_multiple_herdr_frontends_and_duplicate_fds(self):
    self.attached_session()
    self.add_process(51,'herdr','/usr/bin/herdr',ppid=62)
    path=self.proc_root/'51/stat';prefix,fields=path.read_text().rsplit(')',1)
    fields=fields.split();fields[4]='124';path.write_text(prefix+') '+' '.join(fields))
    self.add_process(62,'foot','/usr/bin/foot')
    self.window(pid=62,address='0xdef',workspace=12)
    self.sockets+=self.peer(51,301)+self.peer()
    location=self.report(use_desktop=True)['processes'][0]['desktop']
    self.assertEqual(location['state'],'multiple')
    self.assertEqual(len(location['windows']),2)

  def test_pid_reuse_and_reparenting_in_ancestry_reject_stale_window(self):
    self.add_process(10,'pi','/pi',ppid=61)
    self.add_process(61,'foot','/usr/bin/foot')
    processes,_=self.proc.scan()
    windows={61:[{'address':'0xabc'}]}
    self.add_process(61,'foot','/usr/bin/foot',start=101)
    self.assertEqual(d.ancestor_windows(10,processes,windows,self.proc),[])
    self.add_process(61,'foot','/usr/bin/foot',start=100)
    self.add_process(10,'pi','/pi',ppid=99)
    self.assertEqual(d.ancestor_windows(10,processes,windows,self.proc),[])

  def test_cross_namespace_pid_and_background_container_not_assigned(self):
    self.add_process(10,'codex','/codex',namespace=('pid:[2]','mnt:[2]'))
    self.window(pid=10)
    report=self.report(use_desktop=True,use_podman=False)
    self.assertEqual(report['processes'][0]['desktop']['state'],'unknown')

  def test_compositor_unavailable_and_disabled_are_not_no_window_success(self):
    self.add_process(10,'pi','/pi')
    self.clients=None
    report=self.report(use_desktop=True)
    self.assertEqual(report['coverage']['desktop']['state'],'unavailable')
    self.assertEqual(report['processes'][0]['desktop']['state'],'unavailable')
    self.calls.clear()
    report=self.report(use_desktop=False)
    self.assertEqual(report['coverage']['desktop']['state'],'disabled')
    self.assertFalse(any(c[0] in ('hyprctl','ss') for c in self.calls))

  def test_container_observer_never_matches_host_client_pid(self):
    self.add_process(10,'pi','/pi')
    self.proc.container_observer=True
    report=self.report(use_desktop=True)
    self.assertEqual(report['coverage']['desktop']['state'],'unavailable')
    self.assertFalse(any(c[0] in ('hyprctl','ss') for c in self.calls))

  def test_special_workspace_and_hidden_window_preserve_distinctions(self):
    self.add_process(10,'pi','/pi',ppid=61)
    self.add_process(61,'foot','/usr/bin/foot')
    self.workspaces=[{'id':-99,'name':'special:term','monitor':'HDMI-A-1'}]
    self.monitors[0]['specialWorkspace']={'id':-99}
    self.window(workspace=-99,hidden=True)
    window=self.report(use_desktop=True)['processes'][0]['desktop']['windows'][0]
    self.assertIsNone(window['workspace']['slot'])
    self.assertEqual(window['workspace']['label'],'special:term')
    self.assertTrue(window['hidden'])
    self.assertTrue(window['workspace_active'])

  def test_inconsistent_monitor_snapshot_does_not_choose_stale_location(self):
    self.add_process(10,'pi','/pi',ppid=61)
    self.add_process(61,'foot','/usr/bin/foot')
    self.window()
    self.workspaces[0]['monitor']='another-output'
    report=self.report(use_desktop=True)
    self.assertEqual(report['processes'][0]['desktop']['state'],'unknown')
    self.assertEqual(report['coverage']['desktop']['state'],'partial')

  def test_malformed_boolean_ids_and_unmapped_windows_do_not_match(self):
    self.add_process(10,'pi','/pi',ppid=61)
    self.add_process(61,'foot','/usr/bin/foot')
    self.window(monitor=True)
    self.assertEqual(self.report(use_desktop=True)['processes'][0]['desktop']['state'],'unknown')
    self.clients=[]
    self.window(mapped=False)
    self.assertEqual(self.report(use_desktop=True)['processes'][0]['desktop']['state'],'unknown')

  def test_duplicate_compositor_identifiers_make_coverage_unavailable(self):
    self.add_process(10,'pi','/pi',ppid=61)
    self.add_process(61,'foot','/usr/bin/foot')
    self.window()
    self.monitors.append(dict(self.monitors[0]))
    self.assertEqual(self.report(use_desktop=True)['coverage']['desktop']['state'],'unavailable')

  def test_slot_ten_uses_bar_zero_label(self):
    self.add_process(10,'pi','/pi',ppid=61)
    self.add_process(61,'foot','/usr/bin/foot')
    self.workspaces=[{'id':20,'name':'20','monitor':'HDMI-A-1'}]
    self.window(workspace=20)
    ws=self.report(use_desktop=True)['processes'][0]['desktop']['windows'][0]['workspace']
    self.assertEqual((ws['id'],ws['slot'],ws['label']),(20,10,'0'))


if __name__=='__main__':
  unittest.main()
