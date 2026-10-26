#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

run_node_test <<'JS'
const fs = require('fs')
const base = root + '/shell/plugins/agents/'
const manifest = JSON.parse(fs.readFileSync(base + 'ExecutionDefault.manifest.json','utf8'))
assert(manifest.id === 'omarchy.agent-execution', 'standalone mode widget has an independent identity')
assertDeepEqual(manifest.kinds,['bar-widget'], 'widget does not start a provider or account service')
assert(manifest.entryPoints.barWidget === 'ExecutionDefault.qml', 'widget does not load the usage panel')
assert(!manifest.capabilities && !manifest.clonedFrom && !manifest.omarchy, 'widget requests no authentication or usage capabilities')
assert(manifest.barWidget.defaultSection === 'right' && manifest.barWidget.allowMultiple === false, 'widget has one explicit optional bar placement')
const defaults = JSON.stringify(JSON.parse(fs.readFileSync(root + '/config/omarchy/shell.json','utf8')))
assert(!defaults.includes(manifest.id), 'existing and fresh-install bars are not silently changed')
const source = fs.readFileSync(base + 'ExecutionDefault.qml','utf8').replace(/\/\/[^\n]*/g,'')
assert(source.includes('import "execution" as Execution'), 'standalone and combined labels use the same module URL')
assert(source.includes('readonly property string mode: label.mode'), 'icon and label cannot disagree about the default')
assert(source.includes('Execution.Button {'), 'standalone reuses the existing label, click handler, and shared reader')
assert(!/\b(?:Main|Panel|Agent)\s*\{|Process\s*\{|Timer\s*\{|execDetached|omarchy-agent-usage|omarchy-agent-account/.test(source), 'bar entry embeds no usage, account, agent-launch, process, or polling component')
assert(source.includes('label.triggerPress(buttonCode)'), 'icon forwards to the same safe label action')
const label = fs.readFileSync(base + 'execution/Button.qml','utf8')
assert(label.includes('buttonCode === Qt.LeftButton'), 'left-click retains the execution-default menu action')
assert(label.includes('omarchy-menu summon agents.execution'), 'mode selection still uses the existing execution menu')
assert(source.includes('root.vertical ? 0 : icon.width') && source.includes('root.vertical ? icon.height : 0'), 'horizontal and vertical icon/label slots remain separate')
const iconLine = source.split('\n').find(line => line.trim().startsWith('text:'))
const iconExpression = iconLine.trim().slice('text:'.length)
const icon = mode => new Function('root','return ' + iconExpression)({mode})
assert(icon('host') === '\uf108', 'Host has a desktop icon')
assert(icon('container') === '\uf487', 'Container has a package icon')
assert(icon('unknown') === '\uf071', 'Unknown has a warning icon')
assert(source.includes('active: root.mode === "unknown"'), 'invalid settings use the urgent color instead of implying a safe mode')
const state = fs.readFileSync(base + 'execution/State.qml','utf8')
assert(state.includes('pragma Singleton') && !/Timer\s*\{/.test(state), 'both widgets and all monitors share the existing event-driven singleton')
assert((state.match(/Process\s*\{/g)||[]).length === 1, 'only the existing bounded local getter is used')
JS
