#!/bin/bash

set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"
python3 -I -B "$ROOT/test/shell.d/fixtures/agent-session-menu-test.py"
pass "harness session menu and attachment use offline fixtures"
