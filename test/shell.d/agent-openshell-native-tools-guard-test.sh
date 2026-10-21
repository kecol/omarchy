#!/bin/bash

set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
mkdir -p "$work/bin" "$work/outside" "$work/shims"
# Provide the fixture's ordinary dependencies but deliberately no Pi or mise.
# Pi is a probe, not a model client: stop as soon as the guard invokes it.
for name in dirname realpath mktemp mkdir cat chmod rm timeout; do
  ln -s "$(type -P "$name")" "$work/bin/$name"
done
cat >"$work/bin/python3" <<'SH'
#!/bin/bash
exit 0
SH
cat >"$work/outside/pi" <<'SH'
#!/bin/bash
printf 'invoked\n' >"$OMARCHY_TEST_GUARD_MARKER"
printf 'guard probe reached\n' >&2
exit 19
SH
chmod +x "$work/bin/python3" "$work/outside/pi"
export OMARCHY_TEST_GUARD_MARKER="$work/invoked"
fixture="$ROOT/test/shell.d/agent-openshell-native-tools-test.sh"

run_probe() {
  local label=$1 binary=$2
  rm -f "$OMARCHY_TEST_GUARD_MARKER"
  probe_status=0
  env -u OMARCHY_TEST_PI_BINARY PATH="$work/bin" OMARCHY_TEST_PI_BINARY="$binary" \
    /bin/bash "$fixture" >"$work/$label.log" 2>&1 || probe_status=$?
}

assert_invoked() {
  local label=$1
  [[ -f $OMARCHY_TEST_GUARD_MARKER ]] || fail "$label invokes the selected binary" "$(<"$work/$label.log")"
  ((probe_status != 0)) || fail "$label propagates the probe's deliberate failure"
  grep -F 'guard probe reached' "$work/$label.log" >/dev/null || fail "$label reaches Pi execution"
  if grep -F '# SKIP' "$work/$label.log" >/dev/null; then
    fail "$label must not silently skip"
  fi
}

assert_skipped() {
  local label=$1
  ((probe_status == 0)) || fail "$label skips without a fixture error" "$(<"$work/$label.log")"
  [[ ! -e $OMARCHY_TEST_GUARD_MARKER ]] || fail "$label must not execute Pi"
  grep -F '# SKIP' "$work/$label.log" >/dev/null || fail "$label reports the missing prerequisite"
}

run_probe explicit "$work/outside/pi"
assert_invoked explicit
pass 'explicit preinstalled Pi outside PATH reaches the native-tool test'

run_probe absent ''
assert_skipped absent
pass 'missing Pi without an override skips cleanly'

mv "$work/bin/python3" "$work/python3-hidden"
run_probe no-python "$work/outside/pi"
assert_skipped no-python
mv "$work/python3-hidden" "$work/bin/python3"
pass 'an explicit Pi override still requires Python'

ln -s "$work/outside/pi" "$work/bin/pi"
run_probe path-default ''
assert_invoked path-default
run_probe invalid-override "$work/nonexistent-pi"
assert_skipped invalid-override
pass 'PATH fallback works and never replaces an invalid explicit override'

ln -s "$work/outside/pi" "$work/shims/pi"
run_probe lazy-shim "$work/shims/pi"
assert_skipped lazy-shim
pass 'lazy Pi shims remain excluded from the offline fixture'
