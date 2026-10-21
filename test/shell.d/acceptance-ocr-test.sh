#!/bin/bash
set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"
test_tmp=$(mktemp -d)
trap 'rm -rf "$test_tmp"' EXIT
mkdir -p "$test_tmp/bin"
cat >"$test_tmp/bin/grim" <<'SH'
#!/bin/bash
[[ ${TEST_GRIM_FAIL:-0} == 0 ]] || exit 1
touch "${@: -1}"
SH
cat >"$test_tmp/bin/tesseract" <<'SH'
#!/bin/bash
printf 'Menu Bar\n\nPosition\n\n  Bar\nIndicators\n'
exit "${TEST_OCR_FAIL:-0}"
SH
chmod +x "$test_tmp/bin/"*
export PATH="$test_tmp/bin:$PATH"
export OMARCHY_ACCEPTANCE_DIR="$test_tmp/artifacts"
source "$ROOT/test/acceptance.d/base-test.sh"
screen_contains 'Position Bar' || fail 'OCR matches a visible label split across lines'
screen_contains 'menu bar' || fail 'OCR matching remains case-insensitive'
if screen_contains 'Position Foo'; then fail 'OCR must not accept different words'; fi
if screen_contains 'PositionBar'; then fail 'OCR must not merge distinct words'; fi
if screen_contains 'Position Indicators'; then fail 'OCR must not skip intervening words'; fi
if TEST_OCR_FAIL=1 screen_contains 'Position Bar'; then fail 'OCR errors must not become successes'; fi
if TEST_GRIM_FAIL=1 screen_contains 'Position Bar'; then fail 'capture errors must not become successes'; fi
pass 'acceptance OCR normalizes line wrapping without accepting absent words or failed captures'
