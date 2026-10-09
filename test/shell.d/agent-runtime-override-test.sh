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
printf '%s\n' opencode
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
[[ ${launch_args[*]} == "--app-id=org.omarchy.agent omarchy-agent-exec opencode -- opencode --auto" ]] ||
  fail "agent launcher can force a container launch" "${launch_args[*]}"

OMARCHY_TEST_AGENT_MODE=container "$ROOT/bin/omarchy-agent" --host
mapfile -d '' -t launch_args <"$launch_log"
[[ ${launch_args[*]} == "--app-id=org.omarchy.agent opencode --auto" ]] ||
  fail "agent launcher can force a host launch" "${launch_args[*]}"

pass "agent launcher supports per-launch runtime overrides"
