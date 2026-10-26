"""Read-only desktop associations. Never focus a window or infer pane visibility."""
from pathlib import Path
import os
import re

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


def herdr_clients(rows, sessions, processes, windows, proc):
  """Identify session servers by API listeners, then their local frontend peers."""
  peers = {}
  for row in rows:
    if row['state'] == 'ESTAB':
      peers.setdefault((row['local'], row['peer']), []).append(row)
  result, owned = {}, {}
  def owns_socket(pid, inode):
    if pid not in owned:
      owned[pid] = set()
      try:
        for index, fd in enumerate((proc.root/str(pid)/'fd').iterdir()):
          if index >= 1024:
            break
          try:
            target = os.readlink(fd)
            if re.fullmatch(r'socket:\[\d+\]', target):
              owned[pid].add(int(target[8:-1]))
          except OSError:
            continue
      except OSError:
        pass
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


def discover(query, proc, processes, records, sessions, unavailable):
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
  session_windows, peer_state = {}, 'not-needed'
  if any(session.get('_socket_path') for session in sessions):
    try:
      rows = socket_rows(query(['ss', '-xHapn'], json_output=False))
      session_windows = herdr_clients(rows, sessions, processes, windows, proc)
      peer_state = 'ok' if rows else 'unavailable'
    except (unavailable, OSError, ValueError, TypeError, KeyError):
      peer_state = 'unavailable'
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
    record['desktop'] = location(matches, 'no verified GUI association; background/container processes are not assigned by guesswork')
  return {'state': 'partial' if skipped or peer_state == 'unavailable' else 'ok', 'herdr_peers': peer_state, 'skipped_windows': skipped}
