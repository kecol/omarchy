#!/bin/bash

set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

require_command python3
require_command git
require_command ssh-keygen

if (( EUID == 0 )); then
  skip "real workspace creation tests require an unprivileged user; policy tests still run"
fi
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/test/shell.d/fixtures/workspaces/test_manager.py"
pass "workspace clone, state, editor separation, SSH trust, and runtime policy regressions"

for command in create start stop code list build doctor; do
  "$ROOT/bin/omarchy" workspace "$command" --help >/dev/null
  pass "workspace $command help routes without execution"
done

if grep -E 'docker.sock|podman.sock|ForwardAgent yes|StrictHostKeyChecking no' "$ROOT/default/workspaces/manager.py" "$ROOT/containers/workspace/sshd_config" >/dev/null; then
  fail "workspace runtime must not mount engine sockets or weaken SSH trust"
fi
pass "workspace configuration does not mount engine sockets or forward SSH agents"
