#!/bin/bash

set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"
require_command python3
require_command git
require_command ssh-keygen
require_command jq

PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/test/shell.d/fixtures/agent-launch-options-test.py"
pass "per-launch agent/project selection, read-only checks, installed-only resolution, and no container host-account forwarding"
if (( EUID == 0 )); then
  skip "agent menu project/clone tests require an unprivileged user"
else
  PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/test/shell.d/fixtures/agent-menu-test.py"
  pass "agent menu choices, cancellation, recent-project state, permission warnings, and private clone preparation"
fi
"$ROOT/bin/omarchy" menu agent --help >/dev/null
pass "agent menu help routes without starting an agent"
