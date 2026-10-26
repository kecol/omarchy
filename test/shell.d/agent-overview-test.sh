#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

run_node_test <<'JS'
const fs = require('fs')
const vm = require('vm')
const assertNode = require('assert/strict')
const base = root + '/shell/plugins/agents/'
const model = require(base + 'overview/Model.js')
function processRow(pid, options = {}) {
  return {identity:{pid,start_ticks:100,boot_id:'boot'},agent:'pi',boundary:'host',activity:{state:'idle',source:'herdr'},herdr:[],container:null,cwd:'/project',role:'agent process',desktop:{state:'unknown',windows:[]},...options}
}
function windowRow(id=11, options = {}) {
  return {address:'0xabc',pid:60,monitor:{name:'HDMI-A-1'},workspace:{id,label:String((id-1)%10+1)},association:'process-ancestor',...options}
}
function report(options = {}) {
  return {schema_version:1,observed_at:'2026-10-21T14:32:00Z',processes:[],candidates:[],unverified_observations:[],coverage:{processes:{state:'partial'},remote:{state:'not-queried'},podman:{state:'ok'},workspaces:{state:'ok'},herdr:{state:'ok'},default:{state:'ok'},desktop:{state:'ok'}},...options}
}
function parse(options) {return model.parse(JSON.stringify(report(options)))}
const host=processRow(10,{herdr:[{session:'default',pane:'w7:p1',workspace_id:'w7',tab_id:'w7:t1',workspace_label:'host - Work',tab_label:'pi host'}],desktop:{state:'matched',windows:[windowRow()]}})
const codex=processRow(20,{agent:'codex',boundary:'container',activity:{state:'process-observed',source:'procfs'},role:'extension-associated process',container:{name:'container',workspace_name:'pi-evolving',workspace_id:'workspace-id'},desktop:{state:'matched',windows:[windowRow(12,{association:'workspace-editor-profile'})]}})
const unknown=processRow(30,{boundary:'container'})
const multi=processRow(40,{desktop:{state:'multiple',windows:[windowRow(),windowRow(12,{address:'0xdef'})]}})
const possible=processRow(50)
let result=parse({processes:[host,codex,unknown,multi],candidates:[possible],unverified_observations:[{}]})
assertNode.deepEqual(result.groups.map(g=>g.type),['desktop','desktop','multiple','unknown','candidates'])
assertNode.equal(result.groups.reduce((n,g)=>n+g.rows.length,0),5)
assertNode.equal(result.total,4)
assertNode.equal(result.candidates,1)
assertNode.equal(result.unverified,1)
assertNode.deepEqual(result.counts,{host:2,container:2,unknown:0,observer:0})
assertNode.equal(result.groups[0].rows[0].herdr[0].tabLabel,'pi host')
assertNode.equal(result.groups[1].rows[0].activity,'observed')
assertNode.equal(result.partial,true)
pass('location groups retain one card per identity, separate candidates, and reported activity attribution')

result=parse({processes:[processRow(10,{desktop:{state:'multiple',windows:[windowRow(),windowRow(11,{address:'0xdef'})]}})]})
assertNode.equal(result.groups[0].type,'multiple')
assertNode.equal(result.total,1)
result=parse({processes:[processRow(10,{desktop:{state:'matched',windows:[windowRow(-99,{workspace:{id:-99,label:'special:term'}})]}})]})
assertNode.equal(result.groups[0].label,'special:term')
assertNode.equal(result.groups[0].workspace,-99)
pass('multiple windows are never selected by focus and special desktops retain raw identity')

const malformed=[null,{schema_version:2},{observed_at:'invalid'},{processes:null},{coverage:{}},{processes:[processRow(0)]},{processes:[processRow(10),processRow(10)]},{processes:[host],candidates:[host]},{processes:[processRow(10,{boundary:'safe'})]},{coverage:{desktop:{state:'invented'}}},{processes:[processRow(10,{desktop:{state:'matched',windows:[windowRow(true)]}})]}]
malformed.forEach(extra=>assertNode.throws(()=>model.parse(JSON.stringify(extra===null?null:report(extra)))))
assertNode.throws(()=>model.parse('x'.repeat(model.MAX_OUTPUT+1)))
assertNode.equal(parse({}).total,0)
pass('empty snapshots stay scoped; malformed/versioned/oversized or duplicate identities fail closed')

const privateMarker='SHOULD-NOT-REACH-VIEW'
const safe=parse({processes:[processRow(10,{agent:'pi\u001b\u202e',argv:[privateMarker],environ:privateMarker,desktop:{state:'matched',windows:[windowRow(11,{title:privateMarker,initialTitle:privateMarker,secret:privateMarker})]},herdr:[{session:'default',pane:'w7:p1',workspace_label:'<b>Work</b>',tab_label:'pi\nlabel',agent_session:privateMarker}]})],privateMarker})
assertNode.ok(!JSON.stringify(safe).includes(privateMarker))
assertNode.equal(safe.groups[0].rows[0].agent,'pi\\u001b\\u202e')
assertNode.equal(safe.groups[0].rows[0].herdr[0].tabLabel,'pi\\u000alabel')
assertNode.equal(safe.groups[0].rows[0].herdr[0].workspaceLabel,'<b>Work</b>')
pass('presentation projects only allowlisted metadata and escapes console/bidi controls without rich-text rendering')
result=parse({processes:Array.from({length:205},(_,i)=>processRow(i+1))})
assertNode.equal(result.total,205)
assertNode.equal(result.omitted,5)
assertNode.equal(result.groups[0].rows.length,200)
pass('large snapshots cap rendered cards without silently lowering identified totals')

const stateSource=fs.readFileSync(base+'overview/State.qml','utf8')
function extract(name) {
  const begin=stateSource.indexOf('function '+name+'(')
  assertNode.ok(begin>=0)
  let body=stateSource.indexOf('{',begin),end=body+1,depth=1
  while(depth && end<stateSource.length) {if(stateSource[end]==='{')depth++;else if(stateSource[end]==='}')depth--;end++}
  return stateSource.slice(begin,end)
}
const pending=[]
const state={snapshot:null,loading:false,scheduled:false,failed:false,buffer:'',overflow:false,reader:{running:false},Model:model,Qt:{callLater(fn){pending.push(fn)}}}
state.root=state
vm.createContext(state)
;['refresh','startRead','receive','finish'].forEach(name=>vm.runInContext(extract(name),state))
assertNode.equal(pending.length,0)
for(let i=0;i<20;i++)state.refresh()
assertNode.equal(pending.length,1)
pending.shift()()
assertNode.equal(state.loading,true)
assertNode.equal(state.reader.running,true)
state.refresh()
assertNode.equal(pending.length,0)
JSON.stringify(report({processes:[host,codex]}),null,2).split('\n').forEach(line=>state.receive(line))
state.finish(0);state.reader.running=false
assertNode.equal(state.loading,false)
assertNode.equal(state.snapshot.total,2)
const previous=state.snapshot
state.refresh();pending.shift()();state.receive('not JSON');state.finish(0);state.reader.running=false
assertNode.equal(state.failed,true)
assertNode.equal(state.snapshot,previous)
assertNode.equal(state.snapshot.timestamp,'2026-10-21T14:32:00Z')
assertNode.equal(pending.length,0)
state.refresh();pending.shift()();state.receive('x'.repeat(model.MAX_OUTPUT+1));state.receive('more');state.finish(0);state.reader.running=false
assertNode.equal(state.snapshot,previous)
assertNode.equal(state.buffer,'')
state.refresh();pending.shift()();state.receive(JSON.stringify(report()));state.finish(124)
assertNode.equal(state.failed,true)
assertNode.equal(state.snapshot,previous)
pass('shared reader is idle until requested, coalesces simultaneous opens, caps input, and retains dated snapshots on failures without retry')

const widget=fs.readFileSync(base+'ExecutionDefault.qml','utf8')
const button=fs.readFileSync(base+'execution/Button.qml','utf8')
const popup=fs.readFileSync(base+'overview/Popup.qml','utf8')
const card=fs.readFileSync(base+'overview/AgentCard.qml','utf8')
assertNode.ok(widget.includes('active: root.overviewCreated') && widget.includes('root.overviewOpened = !root.overviewOpened'))
assertNode.ok(widget.includes('onOpeningModeMenu: root.close()'))
assertNode.ok(button.includes('buttonCode === Qt.LeftButton && bar') && button.includes('Qt.RightButton && hasOverview'))
assertNode.ok(button.includes('omarchy-menu summon agents.execution'))
assertNode.ok(widget.includes('hasOverview: true'))
assertNode.ok(stateSource.includes('pragma Singleton'))
assertNode.ok(stateSource.includes('["timeout", "12", "omarchy-agent-status", "--json"]'))
assertNode.equal((stateSource.match(/Process\s*\{/g)||[]).length,1)
assertNode.ok(!/Timer\s*\{|Component\.onCompleted|execDetached|omarchy-agent-usage|omarchy-agent-account/.test(stateSource))
assertNode.ok(!/Process\s*\{|Timer\s*\{|omarchy-agent-usage|omarchy-agent-account|\bMain\s*\{|hyprctl|\bdispatch\b|focusWindow|ssh\b/.test(popup+card+widget))
assertNode.ok(popup.includes('content: Ui.PanelKeyCatcher') && popup.includes('focusTarget: loadedContent'))
assertNode.ok(popup.includes('fittedContentWidth(') && popup.includes('fittedContentHeight(') && popup.includes('clip: true'))
assertNode.ok(popup.includes('Keys.onEscapePressed') && popup.includes('Qt.Key_R'))
assertNode.ok(card.includes('focusable: true') && popup.includes('focusable: true'))
assertNode.ok(fs.readFileSync(base+'overview/Label.qml','utf8').includes('textFormat: Text.PlainText'))
assertNode.ok(!/Text\s*\{/.test(card+popup))
const manifest=JSON.parse(fs.readFileSync(base+'ExecutionDefault.manifest.json','utf8'))
assertNode.deepEqual(manifest.kinds,['bar-widget'])
assertNode.ok(!manifest.capabilities)
pass('overview preserves left-click, exposes right-click lazily, and has bounded/theme-aware keyboard UI without usage imports or navigation')
JS
