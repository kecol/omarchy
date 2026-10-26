#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

python3 -I -B "$ROOT/test/shell.d/fixtures/agent-inline-test.py"
pass "inline container launches keep the current terminal with offline engine fixtures"
