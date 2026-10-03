#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

test_tmp=$(mktemp -d)
trap 'rm -rf "$test_tmp"' EXIT

test_home="$test_tmp/home with spaces"
mode_file="$test_home/.config/omarchy/agents/mode"
mock_bin="$test_tmp/bin"
mv_log="$test_tmp/mv-log"
mkdir -p "$test_home" "$mock_bin"

run_mode() {
  HOME="$test_home" PATH="$mock_bin:/usr/bin" OMARCHY_TEST_MV_LOG="$mv_log" \
    "$ROOT/bin/omarchy-agent-mode" "$@"
}

[[ $(run_mode) == "host" ]] || fail "agent mode defaults to host"
[[ ! -e $mode_file ]] || fail "reading the default agent mode does not create configuration"
pass "agent mode defaults to host without writing configuration"

mkdir -p "$(dirname "$mode_file")"
printf 'host\n' >"$mode_file"

cat >"$mock_bin/mv" <<'SH'
#!/bin/bash
source_path=${3:?}
destination=${4:?}
printf 'before=%s\nstaged=%s\n' "$(<"$destination")" "$(<"$source_path")" >"$OMARCHY_TEST_MV_LOG"
exec /usr/bin/mv "$@"
SH
chmod +x "$mock_bin/mv"

[[ $(run_mode container) == "container" ]] || fail "agent mode reports the saved container mode"
[[ $(<"$mode_file") == "container" ]] || fail "agent mode saves the container mode"
grep -Fxq 'before=host' "$mv_log" || fail "agent mode preserves the old value until publication"
grep -Fxq 'staged=container' "$mv_log" || fail "agent mode stages the complete new value"
pass "agent mode atomically saves container mode"

[[ $(run_mode) == "container" ]] || fail "agent mode reads the saved container mode"
[[ $(run_mode host) == "host" ]] || fail "agent mode reports the saved host mode"
[[ $(run_mode) == "host" ]] || fail "agent mode reads the restored host mode"
pass "agent mode switches between valid modes"

before=$(<"$mode_file")
if run_mode sandbox >"$test_tmp/invalid-output" 2>&1; then
  fail "agent mode rejects unknown modes"
fi
[[ $(<"$mode_file") == "$before" ]] || fail "an unknown mode leaves the setting unchanged"
grep -Fq 'Unknown agent execution mode: sandbox' "$test_tmp/invalid-output" || fail "unknown mode failure names the bad value"
pass "agent mode rejects unknown modes without changing configuration"

printf 'broken\n' >"$mode_file"
if run_mode >"$test_tmp/broken-output" 2>&1; then
  fail "agent mode rejects invalid stored configuration"
fi
grep -Fq "Invalid agent execution mode in $mode_file: broken" "$test_tmp/broken-output" ||
  fail "invalid stored mode failure identifies its file and value"
pass "agent mode reports invalid stored configuration"

help=$(run_mode --help)
[[ $help == *"Usage: omarchy agent mode [host|container]"* ]] || fail "agent mode provides direct help"
pass "agent mode provides direct help"
