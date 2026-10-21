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
if [[ ${TEST_OCR_LAYOUT:-0} == 1 && ${@: -1} == 11 ]]; then
  printf 'Menu Bar\nPosition\nCED\n'
else
  printf 'Menu Bar\n\nPosition\n\n  Bar\nIndicators\n'
fi
exit "${TEST_OCR_FAIL:-0}"
SH
chmod +x "$test_tmp/bin/"*
export PATH="$test_tmp/bin:$PATH"
export OMARCHY_ACCEPTANCE_DIR="$test_tmp/artifacts"
source "$ROOT/test/acceptance.d/base-test.sh"
screen_contains 'Position Bar' || fail 'OCR matches a visible label split across lines'
screen_contains 'menu bar' || fail 'OCR matching remains case-insensitive'
if screen_contains 'Position Foo'; then fail 'OCR must not accept different words'; fi
[[ -f $ARTIFACTS/ocr-position-foo.last-miss.png ]] || fail 'a missed match retains the actual captured image'
grep -Fx 'Position Foo' "$ARTIFACTS/ocr-position-foo.expected.txt" >/dev/null || fail 'a missed match records the expected text'
grep -Fx '  Bar' "$ARTIFACTS/ocr-position-foo.last-miss.txt" >/dev/null || fail 'a missed match retains unnormalized OCR output'
if screen_contains 'PositionBar'; then fail 'OCR must not merge distinct words'; fi
if screen_contains 'Position Indicators'; then fail 'OCR must not skip intervening words'; fi
TEST_OCR_LAYOUT=1 screen_contains 'Position Bar' || fail 'block-layout retry recovers exact words missed by sparse OCR'
if TEST_OCR_LAYOUT=1 screen_contains 'Position Foo'; then fail 'block-layout retry must not invent absent words'; fi
if TEST_OCR_FAIL=1 screen_contains 'Position Bar'; then fail 'OCR errors must not become successes'; fi
if TEST_GRIM_FAIL=1 screen_contains 'Position Bar'; then fail 'capture errors must not become successes'; fi
grep -F 'capture-failed ' "$ARTIFACTS/ocr-position-bar.status.txt" >/dev/null || fail 'capture errors have distinct diagnostic status'
pass 'acceptance OCR normalizes line wrapping without accepting absent words or failed captures'
