#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

test_tmp=$(mktemp -d)
trap 'rm -rf "$test_tmp"' EXIT

mock_bin="$test_tmp/bin"
test_home="$test_tmp/home"
workspace="$test_tmp/project with spaces"
exec_log="$test_tmp/exec-log"
podman_run_log="$test_tmp/podman-run-log"
podman_volume_log="$test_tmp/podman-volume-log"
launch_log="$test_tmp/launch-log"
state_log="$test_tmp/state-log"
mkdir -p "$mock_bin" "$test_home" "$workspace"

cat >"$mock_bin/omarchy-agent-mode" <<'SH'
#!/bin/bash
printf '%s\n' "${OMARCHY_TEST_AGENT_MODE:-host}"
SH

cat >"$mock_bin/host-command" <<'SH'
#!/bin/bash
printf '%s\0' host-command "$@" >"$OMARCHY_TEST_EXEC_LOG"
SH

cat >"$mock_bin/omarchy-agent-run-podman" <<'SH'
#!/bin/bash
printf '%s\0' "$@" >"$OMARCHY_TEST_EXEC_LOG"
SH

cat >"$mock_bin/omarchy-cmd-missing" <<'SH'
#!/bin/bash
[[ ${OMARCHY_TEST_COMMAND_MISSING:-false} == "true" ]]
SH

cat >"$mock_bin/podman" <<'SH'
#!/bin/bash
case "$1 ${2:-}" in
  "info --format")
    printf '%s\n' "${OMARCHY_TEST_PODMAN_ROOTLESS:-true}"
    ;;
  "image exists")
    [[ ${OMARCHY_TEST_IMAGE_EXISTS:-true} == "true" ]]
    ;;
  "image inspect")
    printf '%s\n' "${OMARCHY_TEST_IMAGE_HARNESS:-pi}"
    ;;
  "volume exists")
    [[ ${OMARCHY_TEST_VOLUME_EXISTS:-false} == "true" ]]
    ;;
  "volume create")
    printf '%s\0' "$@" >"$OMARCHY_TEST_PODMAN_VOLUME_LOG"
    ;;
  "volume rm")
    ;;
  "run --rm")
    printf '%s\0' "$@" >"$OMARCHY_TEST_PODMAN_RUN_LOG"
    ;;
  *)
    echo "unexpected podman call: $*" >&2
    exit 1
    ;;
esac
SH

cat >"$mock_bin/omarchy-launch-tui" <<'SH'
#!/bin/bash
printf '%s\0' "$@" >"$OMARCHY_TEST_LAUNCH_LOG"
SH

cat >"$mock_bin/omarchy-agent-state" <<'SH'
#!/bin/bash
printf '%s\t' "$@" >>"$OMARCHY_TEST_STATE_LOG"
printf '\n' >>"$OMARCHY_TEST_STATE_LOG"
SH

chmod +x "$mock_bin"/*

(
  cd "$workspace"
  env HOME="$test_home" OMARCHY_PATH="$ROOT" OMARCHY_TEST_PODMAN_VOLUME_LOG="$podman_volume_log" OMARCHY_AGENT_CONTAINER_DOCTOR_SKIP_JOURNAL=true PATH="$mock_bin:$ROOT/bin:/usr/bin" \
    "$ROOT/bin/omarchy-agent-container-doctor" --quick >"$test_tmp/doctor-output"
)
grep -Fq 'Agent container doctor passed.' "$test_tmp/doctor-output" || fail "container doctor reports success"
pass "container doctor validates writable storage and rootless Podman"

if (
  cd "$workspace"
  env HOME="$test_home" OMARCHY_PATH="$ROOT" OMARCHY_TEST_PODMAN_VOLUME_LOG="$podman_volume_log" OMARCHY_AGENT_CONTAINER_DOCTOR_SKIP_JOURNAL=true PATH="$mock_bin:$ROOT/bin:/usr/bin" \
    OMARCHY_TEST_PODMAN_ROOTLESS=false "$ROOT/bin/omarchy-agent-container-doctor" --quick
) >"$test_tmp/doctor-fail" 2>&1; then
  fail "container doctor rejects non-rootless Podman"
fi
grep -Fq 'Podman is not rootless' "$test_tmp/doctor-fail" || fail "container doctor explains non-rootless Podman"
pass "container doctor fails closed when Podman is unsafe"

common_env=(
  HOME="$test_home"
  OMARCHY_PATH="$ROOT"
  OMARCHY_AGENT_CONTAINER_DOCTOR_SKIP_JOURNAL=true
  OMARCHY_TEST_EXEC_LOG="$exec_log"
  OMARCHY_TEST_PODMAN_RUN_LOG="$podman_run_log"
  OMARCHY_TEST_PODMAN_VOLUME_LOG="$podman_volume_log"
  OMARCHY_TEST_LAUNCH_LOG="$launch_log"
  OMARCHY_TEST_STATE_LOG="$state_log"
)

(
  cd "$workspace"
  env "${common_env[@]}" PATH="$mock_bin:$ROOT/bin:/usr/bin" \
    "$ROOT/bin/omarchy-agent-exec" legacy -- host-command "argument with spaces"
)
mapfile -d '' -t exec_args <"$exec_log"
[[ ${#exec_args[@]} == 2 && ${exec_args[0]} == "host-command" && ${exec_args[1]} == "argument with spaces" ]] ||
  fail "host mode executes the original command unchanged"
pass "host mode executes agents without requiring a container definition"

(
  cd "$workspace"
  env "${common_env[@]}" PATH="$mock_bin:$ROOT/bin:/usr/bin" OMARCHY_TEST_AGENT_MODE=container \
    "$ROOT/bin/omarchy-agent-exec" pi -- pi "review this"
)
mapfile -d '' -t exec_args <"$exec_log"
[[ ${exec_args[*]} == "pi pi -- pi review this" ]] || fail "container mode dispatches the Pi agent to Podman" "${exec_args[*]}"
pass "container mode resolves the standard Pi agent and its harness"

if (
  cd "$workspace"
  env "${common_env[@]}" PATH="$mock_bin:$ROOT/bin:/usr/bin" OMARCHY_TEST_AGENT_MODE=container \
    "$ROOT/bin/omarchy-agent-exec" pi -- bash
) >"$test_tmp/wrong-command" 2>&1; then
  fail "agent execution rejects a command outside its harness definition"
fi
grep -Fq 'must run through pi, not bash' "$test_tmp/wrong-command" || fail "command mismatch identifies both executables"
pass "container agent definitions constrain the harness command"

(
  cd "$workspace"
  env "${common_env[@]}" PATH="$mock_bin:/usr/bin" \
    "$ROOT/bin/omarchy-agent-run-podman" pi pi -- pi --version
)

mapfile -d '' -t volume_args <"$podman_volume_log"
volume_joined=$(printf '%s\n' "${volume_args[@]}")
for expected in \
  "volume" \
  "create" \
  "org.omarchy.agent=pi" \
  "org.omarchy.harness=pi" \
  "omarchy-agent-pi-home"; do
  grep -Fxq -- "$expected" <<<"$volume_joined" || fail "Podman adapter creates labeled state with $expected" "$volume_joined"
done
pass "Podman adapter creates persistent agent-specific state"

mapfile -d '' -t run_args <"$podman_run_log"
run_joined=$(printf '%s\n' "${run_args[@]}")
workspace_hash=$(printf '%s' "$workspace" | sha256sum)
container_workspace="/workspace/${workspace_hash:0:16}"
for expected in \
  "run" \
  "--rm" \
  "--interactive" \
  "--userns=keep-id" \
  "--label=org.omarchy.managed=agent" \
  "--label=org.omarchy.agent=pi" \
  "--label=org.omarchy.harness=pi" \
  "--label=org.omarchy.runtime=podman" \
  "--label=org.omarchy.project=${workspace_hash:0:16}" \
  "--label=org.omarchy.workspace.target=$container_workspace" \
  "--label=org.omarchy.resources.memory=4g" \
  "--label=org.omarchy.resources.pids=1024" \
  "--memory=4g" \
  "--pids-limit=1024" \
  "--cap-drop=all" \
  "--security-opt=no-new-privileges" \
  "--workdir=$container_workspace" \
  "--hostname=agent-pi" \
  "--env=OMARCHY_AGENT_IN_CONTAINER=1" \
  "--volume=$workspace:$container_workspace" \
  "--volume=omarchy-agent-pi-home:/home/agent:U" \
  "--entrypoint=pi" \
  "localhost/omarchy-harness-pi:latest" \
  "--version"; do
  grep -Fxq -- "$expected" <<<"$run_joined" || fail "Podman adapter launches with $expected" "$run_joined"
done
grep -Eq '^--name=omarchy-agent-pi-[0-9a-f]{12}$' <<<"$run_joined" ||
  fail "Podman adapter assigns a unique managed container name" "$run_joined"
grep -Eq '^--label=org.omarchy.instance=[0-9a-f-]{36}$' <<<"$run_joined" ||
  fail "Podman adapter labels the instance identifier" "$run_joined"
pass "Podman adapter isolates Pi while preserving its workspace and arguments"

[[ $(wc -l <"$state_log") == 2 ]] || fail "Podman adapter records instance start and finish" "$(<"$state_log")"
grep -Fq $'start\t' "$state_log" || fail "Podman adapter records instance start"
grep -Fq $'finish\t' "$state_log" || fail "Podman adapter records instance finish"
pass "Podman adapter records the managed instance lifecycle"

managed_project="11111111-2222-3333-4444-555555555555"
managed_task="22222222-3333-4444-5555-666666666666"
managed_assignment="33333333-4444-5555-6666-777777777777"
(
  cd "$workspace"
  env "${common_env[@]}" PATH="$mock_bin:/usr/bin" \
    OMARCHY_AGENT_MANAGED=true \
    OMARCHY_AGENT_PROJECT_ID="$managed_project" \
    OMARCHY_AGENT_TASK_ID="$managed_task" \
    OMARCHY_AGENT_ASSIGNMENT_ID="$managed_assignment" \
    OMARCHY_AGENT_ROLE=coder \
    OMARCHY_AGENT_WORKSPACE="$workspace" \
    "$ROOT/bin/omarchy-agent-run-podman" pi pi -- pi --version
)
mapfile -d '' -t run_args <"$podman_run_log"
run_joined=$(printf '%s\n' "${run_args[@]}")
for expected in \
  "--label=org.omarchy.workspace.managed=true" \
  "--label=org.omarchy.task=$managed_task" \
  "--label=org.omarchy.assignment=$managed_assignment" \
  "--label=org.omarchy.role=coder" \
  "--workdir=/workspace/111111112222/333333334444" \
  "--volume=$workspace:/workspace/111111112222/333333334444" \
  "--volume=omarchy-agent-pi-333333334444-home:/home/agent:U"; do
  grep -Fxq -- "$expected" <<<"$run_joined" || fail "managed Podman launch includes $expected" "$run_joined"
done
pass "Podman adapter gives managed assignments task-scoped state and identity"

mkdir -p "$test_home/.config/omarchy/agents"
printf '%s\n' '{"resources":{"memory":"6g","pids":512,"cpus":2}}' >"$test_home/.config/omarchy/agents/policy.json"
(
  cd "$workspace"
  env "${common_env[@]}" PATH="$mock_bin:$ROOT/bin:/usr/bin" \
    "$ROOT/bin/omarchy-agent-run-podman" pi pi -- pi --version
)
mapfile -d '' -t run_args <"$podman_run_log"
run_joined=$(printf '%s\n' "${run_args[@]}")
for expected in \
  "--label=org.omarchy.resources.memory=6g" \
  "--label=org.omarchy.resources.pids=512" \
  "--label=org.omarchy.resources.cpus=2" \
  "--memory=6g" \
  "--pids-limit=512" \
  "--cpus=2"; do
  grep -Fxq -- "$expected" <<<"$run_joined" || fail "Podman adapter honors configured resource policy with $expected" "$run_joined"
done
policy_json=$(env HOME="$test_home" PATH="$mock_bin:$ROOT/bin:/usr/bin" "$ROOT/bin/omarchy-agent-policy" --json)
[[ $(jq -r '.resources.memory' <<<"$policy_json") == "6g" ]] || fail "agent policy reads configured memory limits" "$policy_json"
[[ $(env HOME="$test_home" OMARCHY_AGENT_MEMORY_LIMIT=8g PATH="$mock_bin:$ROOT/bin:/usr/bin" "$ROOT/bin/omarchy-agent-policy" --json | jq -r '.resources.memory') == "8g" ]] || fail "agent policy lets environment override config"
rm -f "$test_home/.config/omarchy/agents/policy.json"
pass "Podman adapter reads configurable resource policy"

if (
  cd "$workspace"
  env "${common_env[@]}" PATH="$mock_bin:/usr/bin" OMARCHY_TEST_IMAGE_EXISTS=false \
    "$ROOT/bin/omarchy-agent-run-podman" pi pi -- pi
) >"$test_tmp/missing-image" 2>&1; then
  fail "Podman adapter rejects a missing harness image"
fi
grep -Fq 'omarchy harness build pi' "$test_tmp/missing-image" || fail "missing image failure offers its build command"
pass "Podman adapter explains how to build a missing harness image"

mkdir -p "$test_home/.config/omarchy/defaults" "$test_home/.config/omarchy/agents"
printf 'pi\n' >"$test_home/.config/omarchy/defaults/agent"
printf 'container\n' >"$test_home/.config/omarchy/agents/mode"
(
  cd "$workspace"
  env "${common_env[@]}" PATH="$mock_bin:$ROOT/bin:/usr/bin" \
    OMARCHY_TEST_AGENT_MODE=container OMARCHY_TEST_COMMAND_MISSING=true \
    "$ROOT/bin/omarchy-agent"
)
mapfile -d '' -t launch_args <"$launch_log"
launch_joined=$(printf '%s\n' "${launch_args[@]}")
for expected in \
  "--app-id=org.omarchy.agent" \
  "omarchy-agent-exec" \
  "pi" \
  "--"; do
  grep -Fxq -- "$expected" <<<"$launch_joined" || fail "agent launcher routes container mode with $expected" "$launch_joined"
done
[[ $(grep -Fxc 'pi' <<<"$launch_joined") == 2 ]] || fail "agent launcher preserves both Pi identity and command" "$launch_joined"
pass "the desktop agent launcher routes Pi through container execution"

for action in resume continue; do
  : >"$launch_log"
  (
    cd "$workspace"
    env "${common_env[@]}" PATH="$mock_bin:$ROOT/bin:/usr/bin" \
      OMARCHY_TEST_AGENT_MODE=container OMARCHY_TEST_COMMAND_MISSING=true \
      "$ROOT/bin/omarchy-agent-$action"
  )
  mapfile -d '' -t launch_args <"$launch_log"
  launch_joined=$(printf '%s\n' "${launch_args[@]}")
  grep -Fxq -- "--$action" <<<"$launch_joined" ||
    fail "agent $action passes Pi's session flag through the container dispatcher" "$launch_joined"
done
pass "Pi sessions can be resumed or continued through the agent command group"

printf 'claude\n' >"$test_home/.config/omarchy/defaults/agent"
if env "${common_env[@]}" PATH="$mock_bin:$ROOT/bin:/usr/bin" \
  OMARCHY_TEST_AGENT_MODE=host OMARCHY_TEST_COMMAND_MISSING=false \
  "$ROOT/bin/omarchy-agent-resume" >"$test_tmp/unsupported-resume" 2>&1; then
  fail "session resume rejects harnesses without a defined resume interface"
fi
grep -Fq 'currently supported only for Pi' "$test_tmp/unsupported-resume" ||
  fail "unsupported session resume explains its Pi limitation"
pass "session routes fail explicitly for unsupported harnesses"
