#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

test_tmp=$(mktemp -d)
trap 'rm -rf "$test_tmp"' EXIT

mock_bin="$test_tmp/bin"
podman_log="$test_tmp/podman-log"
mise_log="$test_tmp/mise-log"
mkdir -p "$mock_bin"

cat >"$mock_bin/omarchy-cmd-missing" <<'SH'
#!/bin/bash
[[ $1 == ${OMARCHY_TEST_MISSING_COMMAND:-} ]]
SH

cat >"$mock_bin/podman" <<'SH'
#!/bin/bash
if [[ $1 == "info" ]]; then
  printf '%s\n' "${OMARCHY_TEST_PODMAN_ROOTLESS:-true}"
elif [[ $1 == "build" ]]; then
  printf '%s\0' "$@" >"$OMARCHY_TEST_PODMAN_LOG"
else
  exit 1
fi
SH

cat >"$mock_bin/mise" <<'SH'
#!/bin/bash
printf '%s\0' "$@" >"$OMARCHY_TEST_MISE_LOG"
[[ ${OMARCHY_TEST_MISE_FAIL:-false} != "true" ]] || exit 1
[[ $1 == "latest" && $2 == "pi" ]] || exit 1
printf '0.99.1\n'
SH

chmod +x "$mock_bin/omarchy-cmd-missing" "$mock_bin/podman" "$mock_bin/mise"

run_build() {
  PATH="$mock_bin:/usr/bin" \
    OMARCHY_PATH="$ROOT" \
    OMARCHY_TEST_PODMAN_LOG="$podman_log" \
    OMARCHY_TEST_MISE_LOG="$mise_log" \
    "$ROOT/bin/omarchy-harness-build" "$@"
}

output=$(run_build pi)
[[ $output == *"Built localhost/omarchy-harness-pi:0.99.1 and localhost/omarchy-harness-pi:latest"* ]] ||
  fail "harness build reports its image tags" "$output"
pass "harness build resolves and reports the Pi version"

mapfile -d '' -t mise_args <"$mise_log"
[[ ${mise_args[*]} == "latest pi" ]] || fail "harness build asks mise for the latest Pi version" "${mise_args[*]}"
pass "harness build resolves an omitted Pi version with mise"

mapfile -d '' -t podman_args <"$podman_log"
joined=$(printf '%s\n' "${podman_args[@]}")
for expected in \
  "build" \
  "--pull=newer" \
  "HARNESS_UID=$(id -u)" \
  "HARNESS_GID=$(id -g)" \
  "PI_VERSION=0.99.1" \
  "org.omarchy.harness=pi" \
  "org.omarchy.harness.version=0.99.1" \
  "localhost/omarchy-harness-pi:0.99.1" \
  "localhost/omarchy-harness-pi:latest" \
  "$ROOT/containers/harnesses/pi/Containerfile" \
  "$ROOT/containers/harnesses/pi"; do
  grep -Fxq -- "$expected" <<<"$joined" || fail "harness build passes $expected to Podman" "$joined"
done
pass "harness build supplies reproducible image metadata to Podman"

: >"$mise_log"
output=$(OMARCHY_TEST_MISE_FAIL=true run_build pi 1.2.3)
[[ ! -s $mise_log ]] || fail "an explicit Pi version does not invoke mise"
mapfile -d '' -t podman_args <"$podman_log"
[[ ${podman_args[*]} == *"PI_VERSION=1.2.3"* ]] || fail "harness build accepts an explicit Pi version"
pass "harness build accepts an explicit Pi version without resolving latest"

if run_build pi latest >"$test_tmp/invalid-output" 2>&1; then
  fail "harness build rejects an unpinned Pi version"
fi
grep -Fq 'Invalid Pi version: latest' "$test_tmp/invalid-output" || fail "invalid version failure names the value"
pass "harness build rejects an unpinned Pi version"

if OMARCHY_TEST_PODMAN_ROOTLESS=false run_build pi >"$test_tmp/rootful-output" 2>&1; then
  fail "harness build rejects rootful Podman"
fi
grep -Fq 'require rootless Podman' "$test_tmp/rootful-output" || fail "rootful failure explains the requirement"
pass "harness build rejects rootful Podman"

if OMARCHY_TEST_MISSING_COMMAND=podman run_build pi >"$test_tmp/missing-output" 2>&1; then
  fail "harness build rejects missing Podman"
fi
grep -Fq 'omarchy pkg add podman' "$test_tmp/missing-output" || fail "missing Podman failure offers installation"
pass "harness build explains how to install Podman"

containerfile="$ROOT/containers/harnesses/pi/Containerfile"
grep -Fq 'USER agent' "$containerfile" || fail "Pi harness runs as a non-root image user"
grep -Fq 'ENTRYPOINT ["pi"]' "$containerfile" || fail "Pi harness starts Pi"
grep -Fq 'mise install "pi@$PI_VERSION"' "$containerfile" || fail "Pi harness installs its selected Pi version"
pass "Pi harness image has a non-root Pi entrypoint"
