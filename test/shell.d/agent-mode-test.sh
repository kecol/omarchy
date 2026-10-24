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

cat >"$mock_bin/omarchy-shell" <<'SH'
#!/bin/bash
printf '%s\n' "$*" >>"$HOME/refresh-log"
exit 1
SH
chmod +x "$mock_bin/omarchy-shell"

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
grep -Fxq -- '-q omarchy.agent-execution-default refresh' "$test_home/refresh-log" ||
  fail "saving the mode nudges the shared indicator"
pass "agent mode atomically saves container mode and succeeds even without a running shell"

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
grep -Fq "Invalid agent execution mode in $mode_file" "$test_tmp/broken-output" ||
  fail "invalid stored mode failure identifies its file"
! grep -Fq 'broken' "$test_tmp/broken-output" || fail "invalid setting contents are not echoed"
pass "agent mode reports invalid stored configuration"

for value in $'host\nextra' $'container\n\n' ' host' ''; do
  printf '%s' "$value" >"$mode_file"
  if run_mode >"$test_tmp/broken-output" 2>&1; then
    fail "agent mode rejects extra lines, whitespace, and empty files"
  fi
done
printf 'host\0\n' >"$mode_file"
if run_mode >/dev/null 2>&1; then fail "agent mode rejects embedded NUL bytes"; fi
rm "$mode_file"
mkdir "$mode_file"
if run_mode >/dev/null 2>&1; then fail "a directory is not an unset mode"; fi
rmdir "$mode_file"
mkfifo "$mode_file"
if timeout 2 env HOME="$test_home" PATH="$mock_bin:/usr/bin" "$ROOT/bin/omarchy-agent-mode" >/dev/null 2>&1; then
  fail "agent mode rejects nonregular files"
else
  [[ $? != 124 ]] || fail "agent mode does not block on a FIFO"
fi
rm "$mode_file"
ln -s "$test_tmp/nonexistent" "$mode_file"
if run_mode >/dev/null 2>&1; then fail "a dangling symlink is not an unset mode"; fi
rm "$mode_file"
printf container >"$mode_file"
[[ $(run_mode) == "container" ]] || fail "a valid mode without a final newline remains supported"
pass "agent mode bounds reads and rejects malformed and nonregular settings"

if (( EUID != 0 )); then
  chmod 000 "$(dirname "$mode_file")"
  status=0
  run_mode >"$test_tmp/unreadable-output" 2>&1 || status=$?
  chmod 700 "$(dirname "$mode_file")"
  (( status != 0 )) || fail "an inaccessible mode directory does not silently become Host"
  pass "agent mode fails closed on unreadable parent directories"
fi
mkdir "$test_tmp/python-hooks"
printf "import os\nopen(os.environ['HOME'] + '/hook-ran', 'w').close()\n" >"$test_tmp/python-hooks/sitecustomize.py"
[[ $(PYTHONPATH="$test_tmp/python-hooks" run_mode) == "container" ]] || fail "isolated getter returns its setting"
[[ ! -e $test_home/hook-ran ]] || fail "mode queries do not execute project or user Python hooks"
pass "agent mode ignores Python startup hooks"

help=$(run_mode --help)
[[ $help == *"Usage: omarchy agent mode [host|container]"* ]] || fail "agent mode provides direct help"
pass "agent mode provides direct help"
