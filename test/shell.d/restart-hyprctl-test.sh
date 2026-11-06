#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

test_tmp=$(mktemp -d)
trap 'rm -rf "$test_tmp"' EXIT

log="$test_tmp/hyprctl.log"
mkdir -p "$test_tmp/bin"
cat >"$test_tmp/bin/hyprctl" <<'SH'
#!/bin/bash
printf '%s|%s\n' "${HYPRLAND_INSTANCE_SIGNATURE-unset}" "$*" >>"$HYPRCTL_LOG"
printf '%s\n' "${HYPRCTL_STDOUT-ok}"
[[ -z ${HYPRCTL_STDERR:-} ]] || printf '%s\n' "$HYPRCTL_STDERR" >&2
exit "${HYPRCTL_EXIT:-0}"
SH
chmod +x "$test_tmp/bin/hyprctl"

reload() {
  : >"$log"
  env PATH="$test_tmp/bin:$PATH" HYPRCTL_LOG="$log" "$@" "$ROOT/bin/omarchy-restart-hyprctl"
}

reload env HYPRLAND_INSTANCE_SIGNATURE=abc_1_1 >"$test_tmp/out" 2>"$test_tmp/err"
[[ $(<"$log") == "abc_1_1|reload" ]] || fail "reload targets only the explicit native session" "$(<"$log")"
[[ ! -s $test_tmp/out && ! -s $test_tmp/err ]] || fail "successful reload remains quiet"
pass "reload uses explicit native session routing without an instance selector"

if reload env -u HYPRLAND_INSTANCE_SIGNATURE >"$test_tmp/out" 2>"$test_tmp/err"; then
  fail "missing session context must not select instance zero or report success"
fi
[[ ! -s $log ]] || fail "missing session context contacted a compositor" "$(<"$log")"
grep -Fq 'HYPRLAND_INSTANCE_SIGNATURE must identify the intended session' "$test_tmp/err" || fail "missing session context has no guidance"
pass "missing session context refuses before any compositor request"

if reload env HYPRLAND_INSTANCE_SIGNATURE= >"$test_tmp/out" 2>"$test_tmp/err"; then
  fail "empty session context must not select a compositor"
fi
[[ ! -s $log ]] || fail "empty session context contacted a compositor"
pass "empty session context also refuses before any compositor request"

status=0
reload env HYPRLAND_INSTANCE_SIGNATURE=stale_1_1 HYPRCTL_EXIT=37 \
  HYPRCTL_STDOUT='native connection failed on stdout' HYPRCTL_STDERR='native failure on stderr' \
  >"$test_tmp/out" 2>"$test_tmp/err" || status=$?
(( status == 37 )) || fail "native reload failure status was lost" "$status"
[[ $(<"$log") == "stale_1_1|reload" ]] || fail "failed reload tried another target" "$(<"$log")"
grep -Fxq 'native connection failed on stdout' "$test_tmp/err" || fail "native stdout failure was hidden"
grep -Fxq 'native failure on stderr' "$test_tmp/err" || fail "native stderr failure was hidden"
pass "native failure status and both diagnostic streams survive without fallback"

status=0
reload env HYPRLAND_INSTANCE_SIGNATURE=stale_1_1 HYPRCTL_EXIT=1 HYPRCTL_STDOUT='No running Hyprland' \
  >"$test_tmp/out" 2>"$test_tmp/err" || status=$?
(( status == 1 )) || fail "unreachable explicit session was converted to a successful no-op"
[[ $(<"$log") == "stale_1_1|reload" ]] || fail "unreachable session tried another target"
pass "an unreachable explicit session remains a failure rather than a successful no-op"
