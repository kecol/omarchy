#!/bin/bash

set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"
node --experimental-strip-types "$ROOT/test/shell.d/fixtures/model-recovery-test.mjs" "$ROOT/default/agents/pi/model-recovery.ts"
