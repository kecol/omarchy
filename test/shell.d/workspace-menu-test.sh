#!/bin/bash

set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"
require_command python3
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/test/shell.d/fixtures/workspaces/test_menu.py"
pass "workspace menu cancellation, access warnings, stable selections, and safe argument dispatch"
"$ROOT/bin/omarchy" menu workspace --help >/dev/null
pass "container workspace menu help routes without opening the UI"
