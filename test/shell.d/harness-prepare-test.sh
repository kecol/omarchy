#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

python3 -I -B "$ROOT/test/shell.d/fixtures/harness-prepare-test.py"
pass "reviewed generic harness preparation and first-run consent use offline fixtures"
