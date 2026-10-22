#!/bin/bash

set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

require_command python3

test_tmp=$(mktemp -d)
trap 'rm -rf -- "$test_tmp"' EXIT
export HOME="$test_tmp/user home"
export OMARCHY_PATH="$test_tmp/source checkout"
export OMARCHY_TEST_BRANDING_CALLS="$test_tmp/calls"
export OMARCHY_TEST_BRANDING_ARGS="$test_tmp/args"
export OMARCHY_TEST_BRANDING_CONFIRM=0
export OMARCHY_TEST_BRANDING_BOOT_STATUS=0
mkdir -p "$HOME" "$OMARCHY_PATH/bin" "$OMARCHY_PATH/default/branding/fork" "$test_tmp/stubs"
export PATH="$test_tmp/stubs:/usr/bin:/bin"
cp "$ROOT/bin/omarchy" "$ROOT/bin/omarchy-branding-apply" "$ROOT/bin/omarchy-branding-restore" "$ROOT/bin/omarchy-branding-fork" "$OMARCHY_PATH/bin/"
cp "$ROOT/default/branding/fork/"{logo.png,screensaver.txt} "$OMARCHY_PATH/default/branding/fork/"
cp "$ROOT/logo.txt" "$OMARCHY_PATH/logo.txt"

cat >"$test_tmp/stubs/gum" <<'STUB'
#!/bin/bash
printf 'confirm\n' >>"$OMARCHY_TEST_BRANDING_CALLS"
exit "$OMARCHY_TEST_BRANDING_CONFIRM"
STUB
cat >"$test_tmp/stubs/sudo" <<'STUB'
#!/bin/bash
echo 'Unexpected real privilege request in a branding test' >&2
exit 99
STUB
cat >"$OMARCHY_PATH/bin/omarchy-plymouth-set" <<'STUB'
#!/bin/bash
# omarchy:summary=Test publisher
printf 'set\n' >>"$OMARCHY_TEST_BRANDING_CALLS"
printf '%s\0' "$@" >"$OMARCHY_TEST_BRANDING_ARGS"
exit "$OMARCHY_TEST_BRANDING_BOOT_STATUS"
STUB
cat >"$OMARCHY_PATH/bin/omarchy-plymouth-reset" <<'STUB'
#!/bin/bash
# omarchy:summary=Test reset
printf 'reset\n' >>"$OMARCHY_TEST_BRANDING_CALLS"
exit "$OMARCHY_TEST_BRANDING_BOOT_STATUS"
STUB
# Fail closed if a regression tries to reach the real desktop or boot tools.
for command in omarchy-launch-screensaver omarchy-system hyprctl systemctl reboot mkinitcpio limine-mkinitcpio plymouth-set-default-theme; do
  cp "$test_tmp/stubs/sudo" "$test_tmp/stubs/$command"
done
chmod +x "$test_tmp/stubs/"* "$OMARCHY_PATH/bin/"*

destination="$HOME/.config/omarchy/branding/screensaver.txt"
run_branding() {
  "$OMARCHY_PATH/bin/omarchy" branding "$@" >"$test_tmp/output" 2>&1
}
reset_home() {
  rm -rf -- "$HOME/.config"
  : >"$OMARCHY_TEST_BRANDING_CALLS"
  rm -f -- "$OMARCHY_TEST_BRANDING_ARGS"
}
seed_custom() {
  mkdir -p "${destination%/*}"
  printf 'my original art\n' >"$destination"
}
assert_no_boot() {
  ! grep -E '^(set|reset)$' "$OMARCHY_TEST_BRANDING_CALLS" >/dev/null || fail "$1"
}

python3 - "$ROOT" <<'PY'
from pathlib import Path
import struct, sys
root = Path(sys.argv[1])
asset = root / 'default/branding/fork'
image = (asset / 'logo.png').read_bytes()
assert image[:8] == b'\x89PNG\r\n\x1a\n'
assert struct.unpack('>II', image[16:24]) == (800, 260)
stock = (root / 'logo.txt').read_text().splitlines()
fork = (asset / 'screensaver.txt').read_text().splitlines()
assert fork[:-2] == stock
assert fork[-2] == '' and fork[-1].strip() == 'sandboxed agents'
width = max(map(len, stock))
left = len(fork[-1]) - len(fork[-1].lstrip())
right = width - len(fork[-1])
assert abs(left - right) <= 1
PY
pass "fork assets preserve the stock text art and add a centered subtitle"

reset_home
run_branding apply --help
run_branding restore --help
[[ ! -e $HOME/.config && ! -s $OMARCHY_TEST_BRANDING_CALLS ]] || fail "help has no side effects"
if run_branding apply --yes; then fail "unknown flags are rejected"; fi
if run_branding restore --screensaver-only unexpected; then fail "extra arguments are rejected"; fi
[[ ! -e $HOME/.config && ! -s $OMARCHY_TEST_BRANDING_CALLS ]] || fail "invalid arguments have no side effects"
pass "CLI help and invalid arguments never modify branding"

export OMARCHY_TEST_BRANDING_CONFIRM=1
for operation in apply restore; do
  : >"$OMARCHY_TEST_BRANDING_CALLS"
  run_branding "$operation"
  [[ ! -e $HOME/.config && ! -e $OMARCHY_TEST_BRANDING_ARGS ]] || fail "declining leaves files untouched"
  [[ $(<"$OMARCHY_TEST_BRANDING_CALLS") == "confirm" ]] || fail "declining never publishes boot branding"
done
pass "full branding requires confirmation before creating any user files"
export OMARCHY_TEST_BRANDING_CONFIRM=0

reset_home
seed_custom
run_branding apply --screensaver-only
cmp -s "$destination" "$OMARCHY_PATH/default/branding/fork/screensaver.txt" || fail "screensaver-only installs fork art"
shopt -s nullglob
backups=("$destination".bak.*)
(( ${#backups[@]} == 1 )) || fail "screensaver replacement creates a backup"
[[ $(<"${backups[0]}") == "my original art" ]] || fail "backup retains the original art"
[[ $(stat -c %a "${backups[0]}") == "600" ]] || fail "backup is private"
run_branding apply --screensaver-only
backups=("$destination".bak.*)
(( ${#backups[@]} == 1 )) || fail "reapplying unchanged art does not create redundant backups"
[[ ! -s $OMARCHY_TEST_BRANDING_CALLS ]] || fail "screensaver-only never confirms or calls boot helpers"
pass "screensaver-only is backed up, repeatable, and cannot rebuild boot images"

reset_home
seed_custom
run_branding apply
[[ $(<"$OMARCHY_TEST_BRANDING_CALLS") == $'confirm\nset' ]] || fail "full apply confirms then calls the existing boot publisher"
python3 - "$OMARCHY_TEST_BRANDING_ARGS" "$OMARCHY_PATH" <<'PY'
from pathlib import Path
import sys
args = Path(sys.argv[1]).read_bytes().split(b'\0')
assert args == [b'#1a1b26', b'#ffffff', str(Path(sys.argv[2])/'default/branding/fork/logo.png').encode(), b'']
PY
cmp -s "$destination" "$OMARCHY_PATH/default/branding/fork/screensaver.txt" || fail "full apply installs fork text after boot success"
pass "full apply uses the publisher with the exact logo path and colors, including checkout paths with spaces"

: >"$OMARCHY_TEST_BRANDING_CALLS"
run_branding restore
[[ $(<"$OMARCHY_TEST_BRANDING_CALLS") == $'confirm\nreset' ]] || fail "full restore confirms then calls stock boot reset"
cmp -s "$destination" "$OMARCHY_PATH/logo.txt" || fail "restore selects stock text, not fork art"
pass "full restore delegates stock boot/login reset and restores stock text"

reset_home
run_branding restore --screensaver-only
cmp -s "$destination" "$OMARCHY_PATH/logo.txt" || fail "restore can create missing branding directories"
[[ ! -s $OMARCHY_TEST_BRANDING_CALLS ]] || fail "screensaver-only restore never calls boot helpers"
pass "screensaver-only restore works without touching boot or login branding"

for operation in apply restore; do
  reset_home
  seed_custom
  export OMARCHY_TEST_BRANDING_BOOT_STATUS=42
  status=0
  run_branding "$operation" || status=$?
  (( status == 42 )) || fail "$operation preserves the boot helper's failure status"
  [[ $(<"$destination") == "my original art" ]] || fail "$operation preserves screensaver on boot failure"
  grep -F 'may already have changed' "$test_tmp/output" >/dev/null || fail "$operation warns about partial system changes"
  stages=("${destination%/*}/".screensaver.*)
  (( ${#stages[@]} == 0 )) || fail "$operation cleans its staged user file on failure"
done
export OMARCHY_TEST_BRANDING_BOOT_STATUS=0
pass "failed apply/restore never reports success or publishes staged screensaver art"

for operation in apply restore; do
  reset_home
  mkdir -p "${destination%/*}"
  printf 'do not change\n' >"$test_tmp/symlink-target"
  ln -s "$test_tmp/symlink-target" "$destination"
  if run_branding "$operation"; then fail "$operation rejects a symlink destination"; fi
  [[ $(<"$test_tmp/symlink-target") == "do not change" && ! -s $OMARCHY_TEST_BRANDING_CALLS ]] || fail "$operation refuses before boot publication or symlink traversal"
done
pass "symlink destinations are rejected before confirmation or system changes"

reset_home
mkdir -p "$destination"
if run_branding apply; then fail "directory destinations are rejected"; fi
[[ ! -s $OMARCHY_TEST_BRANDING_CALLS ]] || fail "invalid destinations never call boot helpers"
pass "non-regular destinations are rejected"

reset_home
mv "$OMARCHY_PATH/default/branding/fork/logo.png" "$test_tmp/saved-logo.png"
if run_branding apply; then fail "full apply requires the logo asset"; fi
[[ ! -s $OMARCHY_TEST_BRANDING_CALLS && ! -e $HOME/.config ]] || fail "missing logo fails before confirmation or writes"
run_branding apply --screensaver-only
assert_no_boot "screensaver-only does not require a boot logo or boot helper"
mv "$test_tmp/saved-logo.png" "$OMARCHY_PATH/default/branding/fork/logo.png"
pass "missing boot assets fail safely without blocking screensaver-only use"

reset_home
mv "$OMARCHY_PATH/default/branding/fork/screensaver.txt" "$test_tmp/saved-text.txt"
ln -s "$test_tmp/saved-text.txt" "$OMARCHY_PATH/default/branding/fork/screensaver.txt"
if run_branding apply; then fail "symlinked text assets are rejected"; fi
rm "$OMARCHY_PATH/default/branding/fork/screensaver.txt"
if run_branding apply --screensaver-only; then fail "missing text assets are rejected"; fi
[[ ! -e $HOME/.config && ! -s $OMARCHY_TEST_BRANDING_CALLS ]] || fail "invalid text assets fail before writes or confirmation"
mv "$test_tmp/saved-text.txt" "$OMARCHY_PATH/default/branding/fork/screensaver.txt"
pass "missing or symlinked text assets fail before any changes"

reset_home
seed_custom
cat >"$test_tmp/stubs/install" <<'STUB'
#!/bin/bash
exit 73
STUB
chmod +x "$test_tmp/stubs/install"
status=0
run_branding apply || status=$?
(( status == 73 )) || fail "staging errors are reported"
[[ $(<"$destination") == "my original art" ]] || fail "staging errors preserve the destination"
assert_no_boot "staging errors cannot begin a boot rebuild"
stages=("${destination%/*}/".screensaver.*)
(( ${#stages[@]} == 0 )) || fail "staging errors clean temporary user files"
rm "$test_tmp/stubs/install"
pass "user-file staging failures prevent boot publication and clean up safely"

# The lifecycle commands must remain opt-in; do not add a refresh/rebuild there.
lifecycle_call='^[[:space:]]*(exec[[:space:]]+)?(("?[^[:space:]]*/)?omarchy-(branding-(apply|restore)|plymouth-(set|reset)|refresh-plymouth)("|[[:space:]]|$)|omarchy[[:space:]]+(branding[[:space:]]+(apply|restore)|plymouth[[:space:]]+(set|reset)|refresh[[:space:]]+plymouth))'
for injected in 'omarchy branding apply' 'exec omarchy-branding-restore' '"$OMARCHY_PATH/bin/omarchy-plymouth-set"' 'omarchy refresh plymouth'; do
  printf '%s\n' "$injected" | grep -E "$lifecycle_call" >/dev/null || fail "lifecycle guard detects direct branding calls"
done
! grep -E "$lifecycle_call" "$ROOT/bin/omarchy-dev-link" "$ROOT/bin/omarchy-dev-unlink" >/dev/null || fail "dev link/unlink never install branding"
pass "dev link/unlink remain independent of branding publication"
