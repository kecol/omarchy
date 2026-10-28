#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

python3 -I -B "$ROOT/test/shell.d/fixtures/agent-doctor-journal.py"
pass "container doctor distinguishes policy labels from filesystem errors and fails closed"
