#!/bin/bash

# Real Pi, offline synthetic provider, isolated settings: never contacts OpenAI.
set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"
pi_binary=${OMARCHY_TEST_PI_BINARY:-}
if [[ -z $pi_binary ]] && command -v mise >/dev/null; then
  pi_binary=$(mise which pi 2>/dev/null || true)
fi
if [[ ! -x $pi_binary || $pi_binary == */shims/pi ]]; then
  skip "native model recovery test needs an installed Pi binary"
  exit 0
fi
pi_binary=$(realpath "$pi_binary")
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/home" "$tmp/agent"
printf '%s\n' '{"defaultProvider":"recovery-fixture","defaultModel":"retired-model","enableAnalytics":false,"enableInstallTelemetry":false,"cacheWarming":"off","retry":{"enabled":false}}' >"$tmp/agent/settings.json"
args=(--print --no-session --offline --no-extensions --no-tools --no-mcp --no-context-files --no-skills --no-prompt-templates --no-themes
  --extension "$ROOT/test/shell.d/fixtures/model-recovery-provider.ts"
  --extension "$ROOT/default/agents/pi/model-recovery.ts")
run_pi() {
  (cd "$tmp" && env -i HOME="$tmp/home" PATH=/usr/bin:/bin TERM=dumb PI_CODING_AGENT_DIR="$tmp/agent" MODEL_RECOVERY_CALLS="$tmp/calls" \
    timeout 30 "$pi_binary" "${args[@]}" "$@" "synthetic offline input")
}
if run_pi >"$tmp/preflight.log" 2>&1; then
  fail "stale default must fail with a nonzero status"
fi
[[ ! -e $tmp/calls ]] || fail "stale default must not invoke even the fake provider" "$(<"$tmp/preflight.log")"
grep -Fq 'Omarchy model guard:' "$tmp/preflight.log" || fail "preflight provides an actionable guard error" "$(<"$tmp/preflight.log")"
pass "real Pi rejects a missing saved default without a provider request"

if run_pi --provider recovery-fixture --model available-model >"$tmp/rejected.log" 2>&1; then
  fail "explicit provider rejection must fail"
fi
[[ -f $tmp/calls && $(wc -l <"$tmp/calls") == 1 ]] || fail "provider rejection must not replay input" "$(<"$tmp/rejected.log")"
grep -Fq 'Omarchy model guard:' "$tmp/rejected.log" || fail "provider rejection provides recovery instructions" "$(<"$tmp/rejected.log")"
pass "real Pi reports synthetic model rejection without retrying or switching models"

python3 "$ROOT/test/shell.d/fixtures/model-default-relaunch.py" "$ROOT" "$pi_binary"
pass "Save default Enter survives quit and a fresh Pi launch without invoking a provider"
