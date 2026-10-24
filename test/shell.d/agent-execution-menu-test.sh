#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

python3 - <<'PY'
import json
import os
import subprocess
import tempfile
from pathlib import Path

root = Path(os.environ['ROOT'])
with tempfile.TemporaryDirectory(prefix='omarchy execution menu ') as directory:
  home = Path(directory)
  binaries = home / 'bin'
  binaries.mkdir()
  log = home / 'calls'
  def program(name, body):
    path = binaries / name
    path.write_text('#!/bin/bash\n' + body)
    path.chmod(0o755)
  program('gum', 'printf "gum %s\\n" "$*" >>"$CALLS"\nexit "$CONFIRM"\n')
  program('omarchy-shell', 'printf "ipc %s\\n" "$*" >>"$CALLS"\nexit 1\n')
  program('omarchy-launch-floating-terminal-with-presentation', 'printf "%s\\n" "$1" >"$HOME/launch"\n')
  source = home / 'source checkout'
  source.symlink_to(root, target_is_directory=True)
  env = {'HOME': directory, 'PATH': f'{binaries}:{root}/bin:/usr/bin:/bin', 'OMARCHY_PATH': str(source), 'CALLS': str(log), 'CONFIRM': '1'}
  mode_file = home / '.config/omarchy/agents/mode'
  def call(*args, confirm='1'):
    return subprocess.run([str(root/'bin/omarchy-menu-agent-mode'), *args], env={**env, 'CONFIRM': confirm}, capture_output=True, text=True, timeout=5)
  for mode in ('host', 'container'):
    result = call('--confirm', mode)
    assert result.returncode == 130, result.stderr
    assert not mode_file.exists()
    assert 'future' in result.stdout and 'Running agents and workspaces are unchanged' in result.stdout
    assert ('not a sandbox' if mode == 'host' else 'live-directory') in result.stdout
  assert '--default=false' in log.read_text()
  assert 'ipc ' not in log.read_text()
  print('ok - both reviews default to Cancel, show execution boundaries, and create no setting or runtime')
  result = call('--confirm', 'container', confirm='0')
  assert result.returncode == 130, result.stderr
  assert mode_file.read_text() == 'container\n'
  assert 'ipc -q omarchy.agent-execution-default refresh' in log.read_text()
  assert mode_file.stat().st_mode & 0o777 == 0o600
  original = mode_file.read_bytes()
  result = call('--confirm', 'host')
  assert result.returncode == 130
  assert mode_file.read_bytes() == original
  result = call('--confirm', 'host', confirm='0')
  assert result.returncode == 130
  assert mode_file.read_text() == 'host\n'
  print('ok - confirmation uses the authoritative atomic setter; later cancellation preserves the saved default')
  mode_file.write_text('invalid\n')
  result = call('--confirm', 'container', confirm='0')
  assert 'Current: unknown' in result.stdout
  assert mode_file.read_text() == 'container\n'
  assert call('host; touch marker').returncode == 1
  assert call('--confirm', 'container', 'extra').returncode == 1
  result = call('host')
  assert result.returncode == 0
  command = (home/'launch').read_text()
  # Execute the actual quoted terminal command with paths containing spaces.
  result = subprocess.run(['/bin/bash', '-c', command], env=env, capture_output=True, text=True, timeout=5)
  assert result.returncode == 130, result.stderr
  assert mode_file.read_text() == 'container\n'
  print('ok - explicit repair, input validation, and quoted terminal handoff work without changing running agents')
PY

run_node_test <<'JS'
const fs = require('fs')
const model = requireFromRoot('shell/plugins/menu/MenuModel.js')
const all = {}
for (const item of model.parseMenuJsonc(fs.readFileSync(root + '/default/omarchy/omarchy-menu.jsonc', 'utf8'))) all[item.id] = item
assert(model.guardReaders.includes('omarchy-agent-mode'), 'execution checks use the shared menu reader')
for (const mode of ['host', 'container']) {
  const row = all['agents.execution.' + mode]
  assert(row.action === 'omarchy-menu-agent-mode ' + mode, 'mode choice delegates to the confirmed backend: ' + mode)
  assert(row.checked.includes('$(omarchy-agent-mode)'), 'mode choice has the authoritative checkmark: ' + mode)
}
assert(all['agents.execution.unknown'].when.includes('$(omarchy-agent-mode)'), 'invalid mode has an explicit Unknown menu row')
const os = require('os')
const cp = require('child_process')
const fixture = fs.mkdtempSync(path.join(os.tmpdir(), 'agent-mode-guards-'))
try {
  const helper = path.join(fixture, 'omarchy-agent-mode')
  fs.writeFileSync(helper, '#!/bin/bash\necho read >>"$HOME/reads"\nif [[ $MODE == invalid ]]; then exit 1; fi\necho "$MODE"\n', {mode:0o755})
  fs.writeFileSync(path.join(fixture,'pacman'), '#!/bin/bash\nexit 0\n', {mode:0o755})
  fs.writeFileSync(path.join(fixture,'pacman-conf'), '#!/bin/bash\necho "$HOME/db"\n', {mode:0o755})
  const subset = {}
  for (const name of ['host','container','unknown']) subset['agents.execution.' + name] = all['agents.execution.' + name]
  for (const mode of ['host','container','invalid']) {
    fs.writeFileSync(path.join(fixture,'reads'),'')
    const result = cp.spawnSync('/bin/bash',['-c',model.guardScript(subset)], {encoding:'utf8',env:{...process.env,PATH:fixture+':/usr/bin:/bin',HOME:fixture,XDG_RUNTIME_DIR:fixture,MODE:mode}})
    assert(result.status === 0, 'real guard batch completes for ' + mode)
    assert(fs.readFileSync(path.join(fixture,'reads'),'utf8') === 'read\n', 'three mode rows share exactly one getter for ' + mode)
    assert(result.stdout.includes('agents.execution.host:c:' + (mode === 'host' ? '1' : '0')), 'Host checkmark matches ' + mode)
    assert(result.stdout.includes('agents.execution.container:c:' + (mode === 'container' ? '1' : '0')), 'Container checkmark matches ' + mode)
    assert(result.stdout.includes('agents.execution.unknown:w:' + (mode === 'invalid' ? '1' : '0')), 'Unknown warning matches ' + mode)
  }
} finally { fs.rmSync(fixture,{recursive:true,force:true}) }
const manifest = JSON.parse(fs.readFileSync(root + '/shell/plugins/agents/manifest.json', 'utf8'))
assert(manifest.barWidget.defaults.showExecutionDefault === false, 'bar label is opt-in and does not alter current layout')
assert(manifest.barWidget.schema.some(s => s.key === 'showExecutionDefault' && s.type === 'boolean'), 'bar editor exposes the label option')
const state = fs.readFileSync(root + '/shell/plugins/agents/execution/State.qml', 'utf8')
assert(state.includes('pragma Singleton'), 'all monitors share one reader')
assert(!/Timer\s*\{/.test(state), 'execution default has no polling or retry timer')
assert((state.match(/Process\s*\{/g) || []).length === 1, 'execution default has exactly one bounded event-driven reader')
assert(state.includes('["timeout", "5", "omarchy-agent-mode"]'), 'shared reader calls only the authoritative local getter')
function method(name) {
  const match = state.match(new RegExp('  function ' + name + '\\([^)]*\\) \\{([\\s\\S]*?)\\n  \\}'))
  assert(match, 'shared reader exposes ' + name)
  return match[1]
}
const queue = []
const reader = {running:false}
const shared = {mode:'unknown',refreshRequested:false}
const Qt = {callLater:f => {if (!queue.includes(f)) queue.push(f)}}
function bind(name, args) {
  return new Function('root','reader','Qt', 'return function(' + args + ') { with(root) {' + method(name) + '} }')(shared,reader,Qt)
}
shared.startRead = bind('startRead','')
shared.refresh = bind('refresh','')
shared.finishRead = bind('finishRead','exitCode,output')
for (let i=0;i<10;i++) shared.refresh()
assert(queue.length === 1, 'bursts of refresh requests coalesce')
queue.shift()()
assert(reader.running && !shared.refreshRequested, 'one getter starts for every monitor')
shared.refresh();queue.shift()()
assert(shared.refreshRequested, 'a save during an in-flight read is queued, not discarded')
reader.running = false;shared.finishRead(0,'host\n')
assert(shared.mode === 'host' && queue.length === 1, 'reader publishes Host and queues the latest save')
queue.shift()();reader.running = false;shared.finishRead(0,'container\n')
assert(shared.mode === 'container', 'latest read publishes Container')
for (const [code,text] of [[1,'host'],[124,'container'],[0,''],[0,'broken'],[0,'host\ncontainer']]) {
  shared.finishRead(code,text)
  assert(shared.mode === 'unknown', 'errors and malformed getter output show Unknown')
}
assert(queue.length === 0, 'an error does not schedule idle retries')
const panel = fs.readFileSync(root + '/shell/plugins/agents/Panel.qml','utf8')
assert(panel.includes('root.setting("showExecutionDefault", false) === true'), 'disabled labels do not instantiate the reader')
const button = fs.readFileSync(root + '/shell/plugins/agents/execution/Button.qml','utf8')
assert(button.includes('omarchy-menu summon agents.execution'), 'label opens the execution menu, not an agent')
assert(button.includes('textRotation: vertical ? -90 : 0'), 'vertical bars reserve a rotated label slot')
JS
