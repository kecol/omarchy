"""Read-only desktop associations. Never focus a window or infer pane visibility."""
from pathlib import Path
import hashlib
import os
import re
import stat

ADDRESS = re.compile(r'0x[0-9a-fA-F]{1,32}\Z')
# Only reciprocal Unix stream peers are used. Unsupported formats remain unknown.
SOCKET_ROW = re.compile(r'^u_str\s+(LISTEN|ESTAB)\s+\d+\s+\d+\s+(.+?)\s+(\d+)\s+\*\s+(\d+)(?:\s+(.*))?$')


def positive(value):
  return isinstance(value, int) and not isinstance(value, bool) and value > 0


def fresh(proc, process):
  try:
    current = proc.identity(process['pid'])
    return current['start_ticks'] == process['start_ticks'] and current['ppid'] == process['ppid']
  except (OSError, ValueError, IndexError):
    return False


def ancestor_windows(pid, processes, windows, proc):
  """Nearest live ancestor with window ownership; do not choose among its windows."""
  seen = set()
  for _ in range(64):
    process = processes.get(pid)
    if pid in seen or not process or process['namespaces'] != proc.namespaces or not fresh(proc, process):
      return []
    seen.add(pid)
    matches = windows.get(pid, [])
    if matches:
      return matches
    pid = process['ppid']
  return []


def socket_rows(text):
  rows = []
  if len(text.splitlines()) > 8192:
    raise ValueError('too many Unix sockets')
  for line in text.splitlines():
    match = SOCKET_ROW.fullmatch(line.strip())
    if match:
      state, path, local, peer, owners = match.groups()
      rows.append({'state': state, 'path': path, 'local': int(local), 'peer': int(peer), 'pids': {int(pid) for pid in re.findall(r'\bpid=(\d+)', owners or '')}})
  return rows


def socket_inodes(proc, pid):
  result = set()
  try:
    for index, fd in enumerate((proc.root/str(pid)/'fd').iterdir()):
      if index >= 1024:
        break
      try:
        target = os.readlink(fd)
        if re.fullmatch(r'socket:\[\d+\]', target):
          result.add(int(target[8:-1]))
      except OSError:
        continue
  except OSError:
    pass
  return result


def profile_pid(profile, uid):
  """VS Code's PID-only lockfile, never settings, logs, argv, or credentials."""
  directory = os.open(profile, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK)
  try:
    if os.fstat(directory).st_uid != uid:
      raise ValueError('editor profile not owned by observer')
    fd = os.open('code.lock', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    try:
      info = os.fstat(fd)
      if not stat.S_ISREG(info.st_mode) or info.st_uid != uid:
        raise ValueError('unsupported editor PID metadata')
      data = os.read(fd, 65)
      if not re.fullmatch(rb'[1-9][0-9]{0,9}', data):
        raise ValueError('invalid editor PID metadata')
      return int(data)
    finally:
      os.close(fd)
  finally:
    os.close(directory)


def editor_fresh(proc, process):
  return fresh(proc, process) and proc.namespace(process['pid']) == proc.namespaces and os.readlink(proc.root/str(process['pid'])/'exe').removesuffix(' (deleted)') == process['exe']


def editor_windows(rows, profiles, targets, processes, windows, proc):
  """Profile PID + profile-derived IPC listener + kernel fd + compositor owner.

  The short IPC hash alone is not identity. Require the full profile's PID file
  and the same live native Code process owning that listener. Never connect to it.
  """
  hashes = {}
  for wid, profile in profiles.items():
    digest = hashlib.sha256(os.fsencode(profile)).hexdigest()[:8]
    hashes.setdefault(digest, []).append(wid)
  result, failed = {}, 0
  runtime = os.environ.get('XDG_RUNTIME_DIR')
  runtime = Path(runtime) if runtime and Path(runtime).is_absolute() else None
  if runtime:
    try:
      info = runtime.lstat()
      if not stat.S_ISDIR(info.st_mode) or info.st_uid != proc.uid or info.st_mode & 0o077:
        runtime = None
    except OSError:
      runtime = None
  for wid in targets:
    profile = profiles[wid]
    try:
      pid = profile_pid(profile, proc.uid)
      process = processes.get(pid)
      if not process or Path(process['exe']).name not in ('code', 'code-insiders', 'codium') or process['namespaces'] != proc.namespaces or not editor_fresh(proc, process):
        raise ValueError('editor identity unavailable')
      digest = hashlib.sha256(os.fsencode(profile)).hexdigest()[:8]
      if len(hashes[digest]) != 1:
        raise ValueError('ambiguous editor profile hash')
      owned = socket_inodes(proc, pid)
      verified = False
      for row in rows:
        path = Path(row['path'])
        runtime_socket = runtime and path.parent == runtime and re.fullmatch(r'vscode-'+digest+r'-[0-9][0-9.]{0,3}-main\.sock', path.name)
        portable_socket = path.parent == profile and re.fullmatch(r'[0-9][0-9.]{0,3}-main\.sock', path.name)
        if row['state'] != 'LISTEN' or pid not in row['pids'] or row['local'] not in owned or not (runtime_socket or portable_socket):
          continue
        info = path.lstat()
        if stat.S_ISSOCK(info.st_mode) and info.st_uid == proc.uid:
          verified = True
      if not verified or profile_pid(profile, proc.uid) != pid or not editor_fresh(proc, process):
        raise ValueError('editor IPC ownership unavailable or changed')
      # Match the kernel-verified editor itself, not arbitrary descendant apps.
      # Electron may own multiple windows: never select one using focus/title.
      result[wid] = [{**window, 'association': 'workspace-editor-profile', 'editor_pid': pid, 'workspace_id': wid} for window in windows.get(pid, [])]
    except (OSError, ValueError, TypeError):
      failed += 1
  return result, {'state': 'partial' if failed else 'ok' if targets else 'not-needed', 'profiles_checked': len(targets), 'unavailable_profiles': failed}


def herdr_clients(rows, sessions, processes, windows, proc):
  """Identify session servers by API listeners, then their local frontend peers."""
  peers = {}
  for row in rows:
    if row['state'] == 'ESTAB':
      peers.setdefault((row['local'], row['peer']), []).append(row)
  result, owned = {}, {}
  def owns_socket(pid, inode):
    if pid not in owned:
      owned[pid] = socket_inodes(proc, pid)
    return inode in owned[pid]
  def herdr_process(pid):
    process = processes.get(pid)
    return process if process and Path(process['exe']).name == 'herdr' and process['namespaces'] == proc.namespaces and fresh(proc, process) else None
  for session in sessions:
    api = session.get('_socket_path')
    if not session.get('running') or not isinstance(api, str):
      continue
    servers = {pid for row in rows if row['state'] == 'LISTEN' and row['path'] == api for pid in row['pids'] if herdr_process(pid) and owns_socket(pid, row['local'])}
    # Herdr 0.9.x separates frontend presentation from its control API socket.
    # An API CLI connection is not evidence of an attached frontend window.
    client_socket = str(Path(api).with_name('herdr-client.sock'))
    matches = []
    for row in rows:
      if row['state'] != 'ESTAB' or row['path'] != client_socket or not any(owns_socket(pid, row['local']) for pid in row['pids'].intersection(servers)):
        continue
      for peer in peers.get((row['peer'], row['local']), []):
        for pid in peer['pids'] - servers:
          process = herdr_process(pid)
          if not process or not owns_socket(pid, peer['local']) or not (process.get('tty_nr') or windows.get(pid)):
            continue
          for window in ancestor_windows(pid, processes, windows, proc):
            matches.append({**window, 'association': 'herdr-session-client', 'session': session['name'], 'client_pid': pid})
    result[session['name']] = matches
  return result


def location(matches, reason='no verified window association'):
  # A client can have several descriptors for the same socket/window.
  unique = {}
  for row in matches:
    key = (row['address'], row['association'], row.get('session'))
    unique[key] = row
  windows = sorted(unique.values(), key=lambda r: (r['monitor']['name'], r['workspace']['id'], r['address'], r.get('session', '')))
  count = len({row['address'] for row in windows})
  if not windows:
    detail = reason
  elif any(row['association'] == 'herdr-session-client' for row in windows):
    detail = 'attached terminal location; agent pane visibility is not verified'
  elif any(row['association'] == 'workspace-editor-profile' for row in windows):
    detail = 'workspace editor profile location; remote connection and agent visibility are not verified'
  else:
    detail = 'process ancestry/window ownership; visibility is not verified'
  if count > 1:
    detail = 'multiple window candidates; not all necessarily host the agent; '+detail
  return {'state': 'matched' if count == 1 else 'multiple' if count else 'unknown', 'windows': windows, 'detail': detail}


def compositor_windows(clients, monitors, workspaces, processes, proc):
  if not all(isinstance(value, list) for value in (clients, monitors, workspaces)) or len(clients) > 1024 or len(monitors) > 32 or len(workspaces) > 512:
    raise ValueError('unsupported compositor metadata')
  by_monitor = {m['id']: m for m in monitors if isinstance(m, dict) and isinstance(m.get('id'), int) and not isinstance(m['id'], bool) and isinstance(m.get('name'), str)}
  by_workspace = {w['id']: w for w in workspaces if isinstance(w, dict) and isinstance(w.get('id'), int) and not isinstance(w['id'], bool) and isinstance(w.get('name'), str)}
  if len(by_monitor) != len(monitors) or len(by_workspace) != len(workspaces):
    raise ValueError('invalid or duplicate compositor identifiers')
  result, skipped = {}, 0
  for client in clients:
    if not isinstance(client, dict):
      skipped += 1
      continue
    if client.get('mapped') is not True:
      skipped += client.get('mapped') is not False
      continue
    pid, address = client.get('pid'), client.get('address')
    if not positive(pid) or not isinstance(address, str) or not ADDRESS.fullmatch(address):
      skipped += 1
      continue
    process = processes.get(pid)
    if not process or process['namespaces'] != proc.namespaces:
      continue
    if not fresh(proc, process):
      skipped += 1
      continue
    ws_ref = client.get('workspace')
    workspace = by_workspace.get(ws_ref.get('id')) if isinstance(ws_ref, dict) and isinstance(ws_ref.get('id'), int) and not isinstance(ws_ref['id'], bool) else None
    monitor = by_monitor.get(client.get('monitor')) if isinstance(client.get('monitor'), int) and not isinstance(client['monitor'], bool) else None
    if not workspace or not monitor or workspace.get('monitor') != monitor['name']:
      skipped += 1
      continue
    wid = workspace['id']
    slot = (wid - 1) % 10 + 1 if wid > 0 else None
    label = ('0' if slot == 10 else str(slot)) if slot else workspace['name']
    active = monitor.get('activeWorkspace' if wid > 0 else 'specialWorkspace', {})
    row = {'address': address, 'pid': pid, 'class': client.get('class')[:256] if isinstance(client.get('class'), str) else None, 'monitor': {'id': monitor['id'], 'name': monitor['name'][:256]}, 'workspace': {'id': wid, 'name': workspace['name'][:256], 'slot': slot, 'label': label[:256]}, 'workspace_active': isinstance(active, dict) and active.get('id') == wid, 'hidden': client.get('hidden') is True}
    # Ignore titles, initial titles, process arguments, and other client fields.
    result.setdefault(pid, []).append(row)
  return result, skipped


def discover(query, proc, processes, records, sessions, unavailable, profiles=None):
  if proc.container_observer or not proc.namespaces:
    for record in records:
      record['desktop'] = {'state': 'unavailable', 'windows': [], 'detail': 'desktop association requires a host observer'}
    for session in sessions:
      session['desktop'] = {'state': 'unavailable', 'windows': [], 'detail': 'desktop association requires a host observer'}
    return {'state': 'unavailable', 'detail': 'not a verified host observer context'}
  try:
    clients = query(['hyprctl', '-j', 'clients'])
    monitors = query(['hyprctl', '-j', 'monitors'])
    workspaces = query(['hyprctl', '-j', 'workspaces'])
    windows, skipped = compositor_windows(clients, monitors, workspaces, processes, proc)
  except (unavailable, OSError, ValueError, TypeError, KeyError):
    for value in records + sessions:
      value['desktop'] = {'state': 'unavailable', 'windows': [], 'detail': 'Hyprland metadata unavailable'}
    return {'state': 'unavailable', 'detail': 'Hyprland metadata unavailable'}
  profiles = profiles or {}
  targets = {r['container']['workspace_id'] for r in records if r['boundary'] == 'container' and r.get('container') and r['container']['workspace_id'] in profiles}
  herdr_needed = any(session.get('_socket_path') for session in sessions)
  session_windows, peer_state, socket_state, rows = {}, 'not-needed', 'not-needed', []
  if targets or herdr_needed:
    try:
      rows = socket_rows(query(['ss', '-xHapn'], json_output=False))
      socket_state = 'ok' if rows else 'unavailable'
      if herdr_needed:
        session_windows = herdr_clients(rows, sessions, processes, windows, proc)
        peer_state = socket_state
    except (unavailable, OSError, ValueError, TypeError, KeyError):
      socket_state = 'unavailable'
      if herdr_needed:
        peer_state = 'unavailable'
  editors, editor_coverage = editor_windows(rows, profiles, targets, processes, windows, proc)
  for session in sessions:
    reason = 'no attached local Herdr client window identified' if peer_state != 'unavailable' else 'local Herdr peer metadata unavailable'
    session['desktop'] = location(session_windows.get(session['name'], []), reason)
    if not session.get('running'):
      session['desktop'] = {'state': 'not-running', 'windows': [], 'detail': 'session not queried'}
  for record in records:
    pid = record['identity']['pid']
    process = processes.get(pid)
    if not process or not fresh(proc, process):
      record['desktop'] = location([], 'process disappeared or PID identity changed')
      continue
    direct = ancestor_windows(pid, processes, windows, proc) if record['boundary'] == 'host' else []
    matches = [{**row, 'association': 'process-ancestor'} for row in direct]
    if not matches:
      for evidence in record['herdr']:
        matches.extend(session_windows.get(evidence['session'], []))
    if not matches and record['boundary'] == 'container' and record.get('container'):
      if proc.namespace(pid) == process['namespaces']:
        matches.extend(editors.get(record['container']['workspace_id'], []))
    record['desktop'] = location(matches, 'no verified GUI association; background/container processes are not assigned by guesswork')
  return {'state': 'partial' if skipped or socket_state == 'unavailable' or editor_coverage['state'] == 'partial' else 'ok', 'herdr_peers': peer_state, 'unix_peers': socket_state, 'vscode_profiles': editor_coverage, 'skipped_windows': skipped}
