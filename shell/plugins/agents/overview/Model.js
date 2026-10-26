// Presentation only. Never execute report fields, inspect providers, or navigate.
var MAX_OUTPUT = 2 * 1024 * 1024
var MAX_CARDS = 200

function object(value) { return value && typeof value === 'object' && !Array.isArray(value) }
function integer(value) { return typeof value === 'number' && isFinite(value) && Math.floor(value) === value }
function clean(value, limit) {
  if (typeof value !== 'string') return ''
  return value.slice(0, limit || 256).replace(/[\u0000-\u001f\u007f-\u009f\u202a-\u202e\u2066-\u2069]/g, function(c) {
    return '\\u'+('0000'+c.charCodeAt(0).toString(16)).slice(-4)
  })
}
function list(value, limit) {
  if (!Array.isArray(value) || value.length > limit) throw new Error('unsupported snapshot')
  return value
}
function identity(row) {
  var id = row.identity
  if (!object(id) || !integer(id.pid) || id.pid <= 0 || !integer(id.start_ticks) || id.start_ticks < 0) throw new Error('invalid identity')
  return {pid: id.pid, start: id.start_ticks, boot: clean(id.boot_id, 96)}
}
function windowRow(row) {
  if (!object(row) || !object(row.monitor) || !object(row.workspace) || !integer(row.workspace.id) || !integer(row.pid) || row.pid <= 0 || !/^0x[0-9a-fA-F]{1,32}$/.test(row.address)) throw new Error('invalid location')
  var source = ['process-ancestor', 'herdr-session-client', 'workspace-editor-profile'].indexOf(row.association) >= 0 ? row.association : 'unknown'
  return {address: row.address, pid: row.pid, monitor: clean(row.monitor.name), workspace: row.workspace.id,
    label: clean(row.workspace.label), source: source, hidden: row.hidden === true}
}
function projectRow(row) {
  if (!object(row)) return null
  var state = ['matched', 'unavailable', 'ambiguous'].indexOf(row.state) >= 0 ? row.state : 'unavailable'
  var host = clean(row.host_path, 4096), target = clean(row.container_path, 4096)
  var access = ['read-write', 'read-only'].indexOf(row.access) >= 0 ? row.access : 'unknown'
  if (target !== '/workspace' && target.indexOf('/workspace/') !== 0) target = ''
  if (state === 'matched' && (!host || host.charAt(0) !== '/' || !target || access === 'unknown')) state = 'unavailable'
  return {state: state, host: state === 'matched' ? host : '', target: target,
    id: clean(row.project_id, 96), access: state === 'matched' ? access : 'unknown'}
}
function card(row, candidate) {
  if (!object(row) || typeof row.agent !== 'string' || ['host','container','observer','unknown'].indexOf(row.boundary) < 0 || !object(row.desktop)) throw new Error('invalid process')
  var id = identity(row)
  if (['matched','multiple','unknown','unavailable','disabled'].indexOf(row.desktop.state) < 0) throw new Error('invalid desktop state')
  var windows = list(row.desktop.windows, 1024).map(windowRow)
  var herdr = list(row.herdr, 1024).map(function(e) {
    if (!object(e)) throw new Error('invalid Herdr evidence')
    return {session: clean(e.session, 96), pane: clean(e.pane, 96), workspace: clean(e.workspace_id, 96), tab: clean(e.tab_id, 96),
      workspaceLabel: clean(e.workspace_label) || clean(e.workspace_id, 96), tabLabel: clean(e.tab_label) || clean(e.tab_id, 96)}
  })
  var container = object(row.container) ? row.container : {}
  var activity = object(row.activity) ? row.activity : {}
  var reported = activity.source === 'herdr'
  var state = reported && ['working','idle','waiting','attention','needs_input','needs-input','unknown','exited','conflicting-reports'].indexOf(activity.state) >= 0 ? activity.state : 'observed'
  return {key: JSON.stringify([id.boot,id.pid,id.start]), identity: id, agent: clean(row.agent, 96), boundary: row.boundary,
    activity: state, reported: reported, candidate: candidate, windows: windows, herdr: herdr,
    single: row.desktop.state === 'matched' && windows.length === 1,
    multiple: row.desktop.state === 'multiple' || windows.length > 1,
    container: clean(container.name), workspace: clean(container.workspace_name), workspaceId: clean(container.workspace_id, 96),
    extension: row.role === 'extension-associated process', cwd: clean(row.cwd, 4096),
    project: container.kind === 'agent' ? projectRow(container.project) : null}
}
function parse(raw) {
  if (typeof raw !== 'string' || raw.length > MAX_OUTPUT) throw new Error('oversized snapshot')
  var report = JSON.parse(raw)
  if (!object(report) || report.schema_version !== 1 || !object(report.coverage) || typeof report.observed_at !== 'string' || !isFinite(Date.parse(report.observed_at))) throw new Error('unsupported snapshot')
  var identified = list(report.processes, 8192).map(function(r) { return card(r, false) })
  var candidates = list(report.candidates, 8192).map(function(r) { return card(r, true) })
  var unverified = list(report.unverified_observations, 1024).length
  var sources = Object.keys(report.coverage)
  if (sources.length > 32 || ['processes','remote','podman','workspaces','herdr','default','desktop'].some(function(name) { return !object(report.coverage[name]) })) throw new Error('missing coverage')
  var coverage = sources.sort().map(function(name) {
    var row = report.coverage[name]
    if (!object(row) || ['ok','partial','unavailable','disabled','not-needed','not-queried'].indexOf(row.state) < 0) throw new Error('invalid coverage')
    return {name: clean(name, 96), state: row.state}
  })
  if (!coverage.length) throw new Error('missing coverage')
  var counts = {host: 0, container: 0, unknown: 0, observer: 0}
  identified.forEach(function(row) { counts[row.boundary]++ })
  var groups = [], indexed = {}, seen = {}
  var rows = identified.concat(candidates)
  rows.forEach(function(row, index) {
    if (Object.prototype.hasOwnProperty.call(seen, row.key)) throw new Error('duplicate identity')
    seen[row.key] = true
    if (index >= MAX_CARDS) return
    var type = row.candidate ? 'candidates' : row.multiple ? 'multiple' : row.single ? 'desktop' : 'unknown'
    var window = row.single ? row.windows[0] : null
    var key = JSON.stringify([type, window ? window.monitor : '', window ? window.workspace : ''])
    if (!Object.prototype.hasOwnProperty.call(indexed, key)) {
      indexed[key] = {key: key, type: type, monitor: window ? window.monitor : '', workspace: window ? window.workspace : 0,
        label: window ? window.label : '', rows: []}
      groups.push(indexed[key])
    }
    indexed[key].rows.push(row)
  })
  var order = {desktop: 0, multiple: 1, unknown: 2, candidates: 3}
  groups.sort(function(a,b) { return order[a.type]-order[b.type] || a.monitor.localeCompare(b.monitor) || a.workspace-b.workspace })
  return {groups: groups, counts: counts, total: identified.length, candidates: candidates.length,
    unverified: unverified, omitted: Math.max(0, rows.length-MAX_CARDS), coverage: coverage,
    partial: coverage.some(function(row) { return row.state === 'partial' || row.state === 'unavailable' || row.state === 'disabled' }),
    timestamp: report.observed_at}
}

if (typeof module !== 'undefined') module.exports = {parse: parse, clean: clean, MAX_OUTPUT: MAX_OUTPUT, MAX_CARDS: MAX_CARDS}
