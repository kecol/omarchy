#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

run_node_test <<'JS'
const handoff = requireFromRoot('shell/services/BackgroundHandoff.js');
function fixture(enabled, clone = false) {
  const id = clone ? 'fixture.background' : 'omarchy.background';
  const config = {version: 1, disabledPlugins: enabled ? [] : [id], plugins: [], bar: {layout: {right: [{id: 'omarchy.agent-execution'}]}}};
  const registry = {
    scanning: false, installedPlugins: {[id]: {id}},
    resolveEnabledId: () => id,
    isEnabled: () => !config.disabledPlugins.includes(id),
    setEnabled: () => { throw new Error('persistent mutation forbidden'); }
  };
  return {config, registry, state: handoff.create(), service: {suspended: false}};
}
function unchanged(f, action) {
  const before = JSON.stringify(f.config);
  const result = action();
  assertEqual(JSON.stringify(f.config), before, 'handoff must not change persistent config');
  return result;
}
for (const clone of [false, true]) {
  const f = fixture(false, clone);
  for (const value of ['true', 'false'])
    assertEqual(unchanged(f, () => handoff.request(f.state, f.registry, null, value, false)), 'disabled', 'disabled service absence is explicitly acknowledged');
  f.config.disabledPlugins = [];
  handoff.sync(f.state, f.registry, f.service, false);
  assertEqual(f.service.suspended, false, 'reenabling follows last acknowledged resume');
}
pass('disabled builtin and clone preferences survive suspend/resume without loading a service');

const f = fixture(true);
for (const value of ['true', 'false', 'true']) {
  assertEqual(unchanged(f, () => handoff.request(f.state, f.registry, f.service, value, false)), 'ok', 'live service acknowledges handoff');
  assertEqual(f.service.suspended, value === 'true', 'only runtime suspension changes');
}
const reloaded = {suspended: false};
handoff.sync(f.state, f.registry, null, false);
unchanged(f, () => handoff.sync(f.state, f.registry, reloaded, false));
assertEqual(reloaded.suspended, true, 'plugin reload retains accepted video-owner suspension');
reloaded.suspended = false;
handoff.sync(f.state, f.registry, reloaded, false);
assertEqual(reloaded.suspended, false, 'unrelated service updates do not overwrite live instance state');
pass('enabled handoff and replacement lifecycle preserve transient ownership without config writes');

const d = fixture(false);
assertEqual(handoff.request(d.state, d.registry, null, 'true', false), 'disabled', 'disabled suspend accepted');
d.config.disabledPlugins = [];
handoff.sync(d.state, d.registry, d.service, false);
assertEqual(d.service.suspended, true, 'reenable during video ownership stays suspended');
d.config.disabledPlugins = ['omarchy.background'];
unchanged(d, () => handoff.request(d.state, d.registry, d.service, 'false', false));
assertEqual(d.service.suspended, true, 'unloading disabled service stays hidden even for resume');
pass('disable and reenable races do not expose a user-disabled background');

for (const mode of ['scanning', 'unreadable', 'missing-manifest', 'missing-service', 'invalid-service']) {
  const g = fixture(true);
  if (mode === 'scanning') g.registry.scanning = true;
  if (mode === 'missing-manifest') g.registry.installedPlugins = {};
  const service = mode === 'missing-service' ? null : mode === 'invalid-service' ? {} : g.service;
  assertEqual(unchanged(g, () => handoff.request(g.state, g.registry, service, 'true', mode === 'unreadable')), 'not ready', 'unverified state refuses acknowledgement: ' + mode);
  assertEqual(g.state.suspended, false, 'failed request must not be remembered');
  assertEqual(g.service.suspended, false, 'failed request must not hide the current surface');
}
for (const value of ['', 'TRUE', '1', true, null]) {
  const g = fixture(true);
  assertEqual(handoff.request(g.state, g.registry, g.service, value, false), 'invalid', 'invalid values refused');
  assertEqual(g.state.suspended, false, 'invalid request has no effect');
}
pass('unready, unreadable, absent and malformed requests fail without changing runtime or preferences');
JS
