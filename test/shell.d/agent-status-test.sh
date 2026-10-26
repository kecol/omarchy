#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

python3 -I -B "$ROOT/test/shell.d/fixtures/agent-status-test.py"
python3 -I -B "$ROOT/test/shell.d/fixtures/agent-desktop-test.py"
pass "agent status privacy, identity, boundary, adapter, and failure regressions"
