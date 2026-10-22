import assert from 'node:assert/strict';
import { pathToFileURL } from 'node:url';
const { default: install, classifyModelError, startupIssue } = await import(pathToFileURL(process.argv[2]));
const old = { provider: 'openai', id: 'retired-model' };
const good = { provider: 'openai', id: 'available-model' };
const key = (m) => `${m.provider}/${m.id}`;
function fixture({ mode = 'tui', choices = [], draft = '', settings = {}, branch = [], models = [good], auth = true, sdk = true } = {}) {
  const events = new Map(), commands = new Map();
  const notices = [], counts = { abort: 0, shutdown: 0, refresh: 0, select: 0 };
  const ctx = {
    mode, model: good, scopedModels: [], sessionManager: { getBranch: () => branch },
    abort: () => counts.abort++, shutdown: () => counts.shutdown++,
    modelRegistry: {
      find: (provider, id) => models.find((m) => m.provider === provider && m.id === id),
      hasConfiguredAuth: () => auth,
      refresh: async (options) => { counts.refresh++; assert.equal(options.force, true); return { aborted: false, errors: new Map() }; },
    },
    ui: {
      select: async () => { counts.select++; return choices.shift(); },
      getEditorText: () => draft, setEditorText: (text) => { draft = text; },
      notify: (...args) => notices.push(args), setStatus: () => {},
    },
  };
  install({
    on: (name, callback) => events.set(name, callback),
    registerCommand: (name, command) => commands.set(name, command),
    ...(sdk ? { getSettings: () => settings } : {}),
    // Deliberately no sendUserMessage, setModel, credential or settings writer API.
  });
  return { ctx, counts, notices, commands, draft: () => draft,
    emit: async (name, event = {}) => events.get(name)?.(event, ctx) };
}
function pass(text) { console.log('ok - ' + text); }

for (const code of ['model_not_found', 'model_decommissioned', 'model_not_available', 'model_not_supported', 'unsupported_model']) {
  assert.equal(classifyModelError(400, JSON.stringify({ error: { code } }), old.id), 'unavailable');
}
assert.equal(classifyModelError(404, 'The model retired-model does not exist or you do not have access', old.id), 'unavailable');
assert.equal(classifyModelError(undefined, 'The model retired-model is not supported for this account', old.id), 'unavailable');
for (const status of [401, 403, 429, 500, 503]) {
  assert.notEqual(classifyModelError(status, 'model_not_found', old.id), 'unavailable');
}
for (const error of ['Not found', 'Endpoint /models/retired-model not found', 'The model retired-model is temporarily not available', 'The file was not found while using retired-model', 'Connection timeout for retired-model']) {
  assert.notEqual(classifyModelError(404, error, old.id), 'unavailable');
}
pass('only explicit model rejection triggers recovery, not auth, quota, outage, or ambiguous 404');

const settings = { defaultProvider: old.provider, defaultModel: old.id };
let f = fixture({ settings });
assert.equal(startupIssue(f.ctx, settings, []).reason, 'catalog');
assert.equal(startupIssue(f.ctx, settings, ['--model', good.id]), undefined);
assert.equal(startupIssue(f.ctx, settings, ['--model=custom/private']), undefined);
assert.equal(startupIssue(f.ctx, settings, ['--provider', old.provider]).reason, 'catalog');
f.ctx.scopedModels = [{ model: good }];
assert.equal(startupIssue(f.ctx, settings, []), undefined);
pass('stale defaults block implicit fallback but explicit CLI and scoped choices retain precedence');

f = fixture({ branch: [{ type: 'message', message: { role: 'user' } }, { type: 'model_change', provider: old.provider, modelId: old.id }] });
assert.equal(startupIssue(f.ctx, {}, []).id, old.id);
f = fixture({ settings: { defaultProvider: good.provider, defaultModel: good.id }, auth: false });
assert.equal(startupIssue(f.ctx, { defaultProvider: good.provider, defaultModel: good.id }, []).reason, 'authentication');
pass('resumed model and absent authentication are diagnosed separately');

for (const choice of ['Choose a model for this session', 'Choose and save a new default']) {
  f = fixture({ settings, choices: [choice] });
  await f.emit('session_start');
  assert.equal(f.draft(), '/model');
  assert.ok(f.notices.some(([text]) => text.includes(choice.includes('default') ? 'Ctrl+S' : 'this session only')));
  assert.deepEqual(await f.emit('cache_warming_decision'), { action: 'stop' });
  assert.deepEqual(await f.emit('input', { text: 'do not send this', source: 'interactive' }), { action: 'handled' });
  await f.emit('model_select', { model: good, source: 'restore' });
  assert.deepEqual(await f.emit('input', { text: 'still blocked' }), { action: 'handled' });
  await f.emit('model_select', { model: good, source: 'set' });
  assert.deepEqual(await f.emit('input', { text: 'now authorized' }), { action: 'continue' });
  assert.equal(await f.emit('cache_warming_decision'), undefined);
}
pass('session/default repair prepares the native picker; only explicit selection clears the block');

f = fixture({ settings, draft: 'my existing draft', choices: ['Choose a model for this session'] });
await f.emit('session_start');
assert.equal(f.draft(), 'my existing draft');
f = fixture({ settings, choices: [undefined] });
await f.emit('session_start');
await f.emit('input', { text: 'recoverable unsent text' });
assert.equal(f.draft(), 'recoverable unsent text');
pass('recovery does not overwrite drafts or silently send blocked input');

f = fixture({ settings, choices: ['Refresh model catalog', 'Choose a model for this session'] });
await f.emit('session_start');
assert.equal(f.counts.refresh, 1);
assert.deepEqual(await f.emit('cache_warming_decision'), { action: 'stop' });
f = fixture({ settings, choices: ['Refresh model catalog', undefined] });
f.ctx.modelRegistry.refresh = async () => { throw new Error('PRIVATE ERROR MUST NOT LEAK'); };
await f.emit('session_start');
assert.ok(!JSON.stringify(f.notices).includes('PRIVATE ERROR'));
pass('bounded refresh uses Pi registry and does not auto-select or disclose raw errors');

f = fixture({ settings, choices: ['Refresh model catalog'] });
let finishRefresh, refreshSignal;
f.ctx.modelRegistry.refresh = ({ signal }) => {
  refreshSignal = signal;
  return new Promise((resolve) => { finishRefresh = resolve; });
};
const pending = f.emit('session_start');
await new Promise(setImmediate);
assert.ok(refreshSignal);
await f.emit('session_shutdown');
assert.equal(refreshSignal.aborted, true);
finishRefresh({ aborted: true, errors: new Map() });
await pending;
assert.equal(f.notices.length, 0);
assert.equal(f.counts.select, 1);
pass('session replacement aborts refresh and cannot publish UI updates through an old context');

f = fixture({ settings, choices: ['Exit Pi'] });
await f.emit('session_start');
assert.equal(f.counts.shutdown, 1);
pass('Exit requests native graceful shutdown');

const branch = [{ type: 'model_change', id: 'initial', provider: good.provider, modelId: good.id }];
f = fixture({ settings, branch });
await f.emit('session_start');
branch.push({ ...branch[0], id: 'restored' });
await f.emit('model_select', { source: 'restore', model: good });
assert.deepEqual(await f.emit('input', { text: 'not authorized by restore' }), { action: 'handled' });
branch.push({ ...branch[0], id: 'explicit-same-model' });
assert.deepEqual(await f.emit('input', { text: 'authorized by native re-selection' }), { action: 'continue' });
pass('explicit same-model selection is recognized even when Pi emits no model_select event');

f = fixture({ settings, choices: ['Refresh model catalog', undefined] });
process.argv.push('--offline');
try { await f.emit('session_start'); } finally { process.argv.pop(); }
assert.equal(f.counts.refresh, 0);
pass('offline refresh requests never access a remote catalog');

f = fixture({ mode: 'print', sdk: false });
await f.emit('session_start');
assert.deepEqual(await f.emit('input', { text: 'unsupported runtime' }), { action: 'handled' });
assert.equal(process.exitCode, 1);
process.exitCode = 0;
pass('unsupported Pi extension APIs fail closed with an upgrade instruction');
f = fixture({ settings, mode: 'print' });
f.ctx.modelRegistry.find = () => { throw new Error('private runtime detail'); };
await f.emit('session_start');
assert.deepEqual(await f.emit('input', { text: 'runtime validation failed' }), { action: 'handled' });
assert.equal(process.exitCode, 1);
process.exitCode = 0;
pass('a preflight API failure cannot fall through to an implicit model request');

for (const mode of ['print', 'json', 'rpc']) {
  f = fixture({ settings, mode });
  await f.emit('session_start');
  assert.deepEqual(await f.emit('input', { text: 'synthetic test input' }), { action: 'handled' });
  assert.equal(process.exitCode, 1);
  assert.equal(f.counts.refresh, 0);
  process.exitCode = 0;
}
pass('automation rejects stale defaults without a picker, refresh, or provider request');

for (const [name, value] of [['OMARCHY_AGENT_MANAGED', 'true'], ['OMARCHY_AGENT_ONESHOT', '1'], ['OMARCHY_AGENT_ONESHOT', 'true']]) {
  const previous = process.env[name];
  process.env[name] = value;
  try {
    f = fixture({ settings, mode: 'tui' });
    await f.emit('session_start');
    assert.deepEqual(await f.emit('input', { text: 'managed input' }), { action: 'handled' });
    assert.equal(f.counts.select, 0);
    assert.ok(f.counts.shutdown > 0);
    assert.equal(process.exitCode, 1);
    process.exitCode = 0;
  } finally {
    if (previous === undefined) delete process.env[name];
    else process.env[name] = previous;
  }
}
pass('managed and one-shot policies suppress recovery dialogs even with a terminal UI');

f = fixture({ choices: ['Choose a model for this session'] });
await f.emit('session_start');
await f.emit('before_provider_request');
await f.emit('after_provider_response', { status: 404 });
await f.emit('message_end', { message: { role: 'assistant', stopReason: 'error', provider: old.provider, model: old.id, errorMessage: 'model_not_found SECRET' } });
assert.equal(f.counts.abort, 1);
await f.emit('agent_settled');
assert.equal(f.draft(), '/model');
assert.ok(!JSON.stringify(f.notices).includes('SECRET'));
assert.deepEqual(await f.emit('input', { text: 'must not retry' }), { action: 'handled' });
pass('provider rejection stops work and offers repair after settlement without replaying input');

for (const status of [401, 403, 429, 503]) {
  f = fixture();
  await f.emit('session_start');
  await f.emit('before_provider_request');
  await f.emit('after_provider_response', { status });
  await f.emit('message_end', { message: { role: 'assistant', stopReason: 'error', ...old, model: old.id, errorMessage: 'model_not_found' } });
  assert.equal(f.counts.abort, 0);
  assert.deepEqual(await f.emit('input', { text: 'native handling' }), { action: 'continue' });
}
pass('auth and transient errors keep native error handling and do not change model policy');
