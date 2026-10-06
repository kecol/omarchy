#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

test_tmp=$(mktemp -d)
trap 'rm -rf "$test_tmp"' EXIT

mock_bin="$test_tmp/bin"
workspace="$test_tmp/workspace with spaces"
podman_log="$test_tmp/podman-log"
mkdir -p "$mock_bin" "$workspace"

cat >"$mock_bin/omarchy-cmd-missing" <<'SH'
#!/bin/bash
[[ ${OMARCHY_TEST_PODMAN_MISSING:-false} == "true" && $1 == "podman" ]]
SH

cat >"$mock_bin/podman" <<'SH'
#!/bin/bash
if [[ $1 == "info" ]]; then
  [[ ${OMARCHY_TEST_PODMAN_RESPONDS:-true} == "true" ]] || exit 1
  printf '%s\n' "${OMARCHY_TEST_PODMAN_ROOTLESS:-true}"
elif [[ $1 == "run" ]]; then
  printf '%s\0' "$@" >"$OMARCHY_TEST_PODMAN_LOG"
else
  exit 1
fi
SH

chmod +x "$mock_bin/omarchy-cmd-missing" "$mock_bin/podman"

run_check() {
  (
    cd "$workspace"
    PATH="$mock_bin:/usr/bin" \
      OMARCHY_TEST_PODMAN_LOG="$podman_log" \
      "$ROOT/bin/omarchy-agent-container-check" "$@"
  )
}

output=$(run_check)
[[ $output == *"Agent container check passed"* ]] || fail "container check reports success" "$output"
pass "container check reports success"

mapfile -d '' -t podman_args <"$podman_log"
joined=$(printf '%s\n' "${podman_args[@]}")

for expected in \
  "run" \
  "--rm" \
  "--pull=missing" \
  "--userns=keep-id" \
  "--cap-drop=all" \
  "--security-opt=no-new-privileges" \
  "--network=none" \
  "--workdir=/workspace" \
  "$workspace:/workspace" \
  "docker.io/library/archlinux:base"; do
  grep -Fxq -- "$expected" <<<"$joined" || fail "container check passes $expected to Podman" "$joined"
done
pass "container check applies the isolated workspace options"

custom_image="localhost/omarchy-agent:test"
output=$(OMARCHY_AGENT_CONTAINER_IMAGE="$custom_image" run_check)
mapfile -d '' -t podman_args <"$podman_log"
[[ ${podman_args[*]} == *"$custom_image"* ]] || fail "container check honors its image setting"
pass "container check honors its image setting"

if OMARCHY_TEST_PODMAN_ROOTLESS=false run_check >"$test_tmp/rootful-output" 2>&1; then
  fail "container check rejects rootful Podman"
fi
grep -Fq "require rootless Podman" "$test_tmp/rootful-output" || fail "rootful failure explains the requirement"
pass "container check rejects rootful Podman"

if OMARCHY_TEST_PODMAN_MISSING=true run_check >"$test_tmp/missing-output" 2>&1; then
  fail "container check rejects a missing Podman"
fi
grep -Fq "omarchy pkg add podman" "$test_tmp/missing-output" || fail "missing Podman failure offers the install command"
pass "container check explains how to install Podman"
