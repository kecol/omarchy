#!/bin/bash
# Offline integration test: real host Pi, fake curl, no credentials or model usage.
set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"
if ! command -v pi >/dev/null || ! command -v python3 >/dev/null; then
  skip 'native OpenShell provider test needs installed Pi and python3'
  exit 0
fi
# Resolve before replacing HOME/PATH. A lazy mise shim would otherwise try to
# install Pi through the fake model transport below. Tests must not log in or
# install tools implicitly; callers can provide a preinstalled binary explicitly.
pi_binary=${OMARCHY_TEST_PI_BINARY:-$(command -v pi)}
if [[ -z ${OMARCHY_TEST_PI_BINARY:-} ]] && command -v mise >/dev/null; then
  resolved_pi=$(mise which pi 2>/dev/null || true)
  if [[ -n $resolved_pi && -x $resolved_pi ]]; then
    pi_binary=$resolved_pi
  fi
fi
if [[ ! -x $pi_binary || $pi_binary == */shims/pi ]]; then
  skip 'install Pi before the offline native-tool test (or set OMARCHY_TEST_PI_BINARY)'
  exit 0
fi
pi_binary=$(realpath "$pi_binary")
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/bin" "$tmp/home" "$tmp/agent"
cat >"$tmp/bin/curl" <<'PY'
#!/usr/bin/env python3
import json, os, sys
p = json.load(sys.stdin)
results = [item for item in p['input'] if item.get('type') == 'function_call_output']
n = len(results)
path = os.environ['TEST_WORKFILE']
calls = [
    ('write', {'path': path, 'content': 'before\n'}),
    ('read', {'path': path, 'offset': 1, 'limit': 10}),
    ('edit', {'path': path, 'edits': [{'oldText': 'before', 'newText': 'after'}]}),
    ('bash', {'command': 'cat ' + path, 'timeout': 5}),
]
if os.environ.get('TEST_BLOCK') == '1':
    calls = [('bash', {'command': 'touch ' + path + '.forbidden', 'timeout': 5})]
def emit(event):
    print('data: ' + json.dumps(event) + '\n', flush=True)
if n:
    assert results[-1]['call_id'] == 'call_' + str(n-1), results
    if os.environ.get('TEST_BLOCK') == '1':
        assert 'blocked by regression test' in results[-1]['output'], results
    else:
        if n == 2: assert 'before' in results[-1]['output'], results
        if n == 4: assert 'after' in results[-1]['output'], results
if n < len(calls):
    name, args = calls[n]
    call = {'id': 'fc_' + str(n), 'call_id': 'call_' + str(n), 'type': 'function_call', 'name': name, 'arguments': json.dumps(args)}
    emit({'type': 'response.output_item.done', 'item': call})
else:
    emit({'type': 'response.output_text.delta', 'delta': 'OK'})
emit({'type': 'response.completed', 'response': {'usage': {'input_tokens': 1, 'output_tokens': 1, 'total_tokens': 2}}})
PY
cat >"$tmp/observer.ts" <<'TS'
import { appendFileSync } from 'node:fs';
export default function(pi: any) {
  for (const event of ['tool_call', 'tool_result']) {
    pi.on(event, (data: any) => {
      appendFileSync(process.env.TEST_EVENTS!, JSON.stringify({event, name: data.toolName, isError: data.isError}) + '\n');
      if (process.env.TEST_BLOCK === '1' && event === 'tool_call' && data.toolName === 'bash') {
        return {block: true, reason: 'blocked by regression test'};
      }
    });
  }
}
TS
chmod +x "$tmp/bin/curl"
export HOME="$tmp/home" PI_CODING_AGENT_DIR="$tmp/agent"
export PATH="$tmp/bin:$PATH"
export TEST_WORKFILE="$tmp/workfile" TEST_EVENTS="$tmp/events"
export OPENSHELL_CODEX_AUTH_ACCESS_TOKEN='openshell:resolve:env:offline-test'
export OMARCHY_OPEN_SHELL_MODELS_JSON
OMARCHY_OPEN_SHELL_MODELS_JSON=$(<"$ROOT/containers/harnesses/pi/extensions/openshell-codex-models.json")
cd "$tmp"
printf 'Test tools' | timeout 60s "$pi_binary" --print --no-session --offline --provider openshell-codex --model gpt-6.1-sol \
  --no-extensions --extension "$ROOT/containers/harnesses/pi/extensions/openshell-codex.ts" --extension "$tmp/observer.ts" \
  --tools read,bash,edit,write --no-mcp --no-context-files --no-skills --no-prompt-templates --no-themes >"$tmp/output" 2>&1 ||
  fail 'native Pi loop must complete with fake transport' "$(<"$tmp/output")"
grep -Fxq OK "$tmp/output" || fail 'native loop returns final answer' "$(<"$tmp/output")"
[[ $(<"$TEST_WORKFILE") == after ]] || fail 'native tools edited file' ''
python3 - "$TEST_EVENTS" <<'PY'
import json, sys
rows = [json.loads(line) for line in open(sys.argv[1])]
for name in ('read', 'bash', 'edit', 'write'):
    assert sum(r['event'] == 'tool_call' and r['name'] == name for r in rows) == 1, rows
    result = [r for r in rows if r['event'] == 'tool_result' and r['name'] == name]
    assert len(result) == 1 and not result[0].get('isError'), rows
PY
pass 'OpenShell provider delegates read/write/edit/bash to Pi and forwards native results and hooks'
export TEST_BLOCK=1
printf 'Test blocked tool' | timeout 60s "$pi_binary" --print --no-session --offline --provider openshell-codex --model gpt-6.1-sol \
  --no-extensions --extension "$ROOT/containers/harnesses/pi/extensions/openshell-codex.ts" --extension "$tmp/observer.ts" \
  --tools read,bash,edit,write --no-mcp --no-context-files --no-skills --no-prompt-templates --no-themes >"$tmp/blocked-output" 2>&1 ||
  fail 'blocked tool must be returned as a native tool error' "$(<"$tmp/blocked-output")"
grep -Fxq OK "$tmp/blocked-output" || fail 'native loop continues after blocked tool' "$(<"$tmp/blocked-output")"
[[ ! -e $TEST_WORKFILE.forbidden ]] || fail 'blocked command must not execute' ''
pass 'Pi tool_call blocking hook prevents execution and returns an error to the model'
