#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

python3 -I -B "$ROOT/test/shell.d/fixtures/agent-command-guards-test.py"
pass "opt-in direct command guards preserve executables and explicit Host launches"
