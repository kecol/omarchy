#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

test_tmp=$(mktemp -d)
trap 'rm -rf "$test_tmp"' EXIT

mock_bin="$test_tmp/bin"
test_home="$test_tmp/home"
launch_log="$test_tmp/launch-log"
mkdir -p "$mock_bin" "$test_home"

cat >"$mock_bin/omarchy-default-agent" <<'MOCK'
#!/bin/bash
printf '%s\n' "${OMARCHY_TEST_DEFAULT_AGENT:-opencode}"
MOCK

cat >"$mock_bin/omarchy-agent-mode" <<'MOCK'
#!/bin/bash
printf '%s\n' "${OMARCHY_TEST_AGENT_MODE:-host}"
MOCK

cat >"$mock_bin/omarchy-cmd-missing" <<'MOCK'
#!/bin/bash
exit 1
MOCK

cat >"$mock_bin/omarchy-launch-tui" <<'MOCK'
#!/bin/bash
printf '%s\0' "$@" >"$OMARCHY_TEST_LAUNCH_LOG"
MOCK

cat >"$mock_bin/pi" <<'MOCK'
#!/bin/bash
printf '%s\0' "$@" >"$OMARCHY_TEST_LAUNCH_LOG"
MOCK

chmod +x "$mock_bin"/*

export HOME="$test_home"
export OMARCHY_PATH="$ROOT"
export OMARCHY_TEST_LAUNCH_LOG="$launch_log"
export PATH="$mock_bin:$ROOT/bin:/usr/bin"

"$ROOT/bin/omarchy-agent"
mapfile -d '' -t launch_args <"$launch_log"
[[ ${launch_args[*]} == "--app-id=org.omarchy.agent opencode --auto" ]] ||
  fail "agent launcher uses the configured default host mode" "${launch_args[*]}"

"$ROOT/bin/omarchy-agent" --container
mapfile -d '' -t launch_args <"$launch_log"
[[ ${launch_args[*]} == "--app-id=org.omarchy.agent $ROOT/bin/omarchy-agent-exec --container opencode -- opencode --auto" ]] ||
  fail "agent launcher can force a container launch" "${launch_args[*]}"

OMARCHY_TEST_AGENT_MODE=container "$ROOT/bin/omarchy-agent" --host
mapfile -d '' -t launch_args <"$launch_log"
[[ ${launch_args[*]} == "--app-id=org.omarchy.agent opencode --auto" ]] ||
  fail "agent launcher can force a host launch" "${launch_args[*]}"

"$ROOT/bin/omarchy-agent-prompt" --container "review this"
mapfile -d '' -t launch_args <"$launch_log"
[[ ${launch_args[*]} == "--app-id=org.omarchy.agent $ROOT/bin/omarchy-agent-exec --container opencode -- opencode --auto --prompt review this" ]] ||
  fail "agent prompt can force a container launch" "${launch_args[*]}"

OMARCHY_TEST_AGENT_MODE=container "$ROOT/bin/omarchy-agent-prompt" --host "review this"
mapfile -d '' -t launch_args <"$launch_log"
[[ ${launch_args[*]} == "--app-id=org.omarchy.agent opencode --auto --prompt review this" ]] ||
  fail "agent prompt can force a host launch" "${launch_args[*]}"

OMARCHY_TEST_DEFAULT_AGENT=pi "$ROOT/bin/omarchy-agent-prompt" --oneshot "print pwd"
mapfile -d '' -t launch_args <"$launch_log"
[[ ${launch_args[*]} == "--print print pwd" ]] ||
  fail "agent prompt can run Pi one-shot without opening a TUI" "${launch_args[*]}"


if "$ROOT/bin/omarchy-agent-prompt" --oneshot "unsupported" >"$test_tmp/oneshot-unsupported" 2>&1; then
  fail "one-shot rejects unsupported agents"
fi
grep -Fq 'One-shot prompts are not supported for opencode yet.' "$test_tmp/oneshot-unsupported" ||
  fail "one-shot unsupported error names the agent" "$(<"$test_tmp/oneshot-unsupported")"

pass "agent launcher supports per-launch runtime overrides"
