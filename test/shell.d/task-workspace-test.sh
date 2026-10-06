#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

test_tmp=$(mktemp -d)
trap 'rm -rf "$test_tmp"' EXIT

mock_bin="$test_tmp/bin"
test_home="$test_tmp/home"
source_repo="$test_tmp/source project"
launch_log="$test_tmp/launch-log"
runtime_snapshot="$test_tmp/runtime-snapshot.json"
podman_log="$test_tmp/podman-log"
mkdir -p "$mock_bin" "$test_home" "$source_repo"

git -C "$source_repo" init --quiet
git -C "$source_repo" config user.name Tester
git -C "$source_repo" config user.email tester@example.test
printf 'original\n' >"$source_repo/file.txt"
git -C "$source_repo" add file.txt
git -C "$source_repo" commit --quiet -m Initial
base_commit=$(git -C "$source_repo" rev-parse HEAD)

cat >"$mock_bin/omarchy-agent-mode" <<'SH'
#!/bin/bash
printf '%s\n' "${OMARCHY_TEST_AGENT_MODE:-container}"
SH

cat >"$mock_bin/omarchy-agent-runtime-snapshot" <<'SH'
#!/bin/bash
if [[ -n ${OMARCHY_TEST_RUNTIME_SNAPSHOT:-} && -f $OMARCHY_TEST_RUNTIME_SNAPSHOT ]]; then
  cat "$OMARCHY_TEST_RUNTIME_SNAPSHOT"
else
  printf '[]\n'
fi
SH

cat >"$mock_bin/podman" <<'SH'
#!/bin/bash
printf '%s\n' "$*" >>"$OMARCHY_TEST_PODMAN_LOG"
if [[ ${1:-} == "image" && ${2:-} == "exists" ]]; then
  exit 0
fi
if [[ ${1:-} == "stop" ]]; then
  printf '%s\n' "${2:-}"
fi
SH

cat >"$mock_bin/omarchy-agent-container-doctor" <<'SH'
#!/bin/bash
if [[ ${OMARCHY_TEST_CONTAINER_DOCTOR_FAIL:-false} == "true" ]]; then
  exit 1
fi
exit 0
SH

cat >"$mock_bin/omarchy-agent" <<'SH'
#!/bin/bash
jq -n \
  --arg cwd "$PWD" \
  --arg args "$*" \
  --arg managed "$OMARCHY_AGENT_MANAGED" \
  --arg project "$OMARCHY_AGENT_PROJECT_ID" \
  --arg task "$OMARCHY_AGENT_TASK_ID" \
  --arg assignment "$OMARCHY_AGENT_ASSIGNMENT_ID" \
  --arg role "$OMARCHY_AGENT_ROLE" \
  --arg workspace "$OMARCHY_AGENT_WORKSPACE" \
  '{cwd: $cwd, args: $args, managed: $managed, project: $project, task: $task, assignment: $assignment, role: $role, workspace: $workspace}' \
  >"$OMARCHY_TEST_LAUNCH_LOG"
SH

chmod +x "$mock_bin"/*

export HOME="$test_home"
export XDG_STATE_HOME="$test_tmp/state"
export XDG_DATA_HOME="$test_tmp/data"
export OMARCHY_PATH="$ROOT"
export OMARCHY_TEST_LAUNCH_LOG="$launch_log"
export OMARCHY_TEST_RUNTIME_SNAPSHOT="$runtime_snapshot"
export OMARCHY_TEST_PODMAN_LOG="$podman_log"
export PATH="$mock_bin:$ROOT/bin:/usr/bin"

create_json=$(cd "$source_repo" && "$ROOT/bin/omarchy-task-create" --json "Implement isolated workspaces")
task_id=$(jq -r '.task' <<<"$create_json")
project_id=$(jq -r '.project' <<<"$create_json")
[[ $(jq -r '.base_commit' <<<"$create_json") == "$base_commit" ]] || fail "task creation records the immutable base commit"
[[ $(jq -r '.goal' <<<"$create_json") == "Implement isolated workspaces" ]] || fail "task creation records its goal"
pass "task creation records a clean project and immutable base"

printf 'dirty\n' >>"$source_repo/file.txt"
if (cd "$source_repo" && "$ROOT/bin/omarchy-task-create" "Unsafe task") >"$test_tmp/dirty-output" 2>&1; then
  fail "task creation rejects uncommitted source changes"
fi
grep -Fq 'uncommitted changes' "$test_tmp/dirty-output" || fail "dirty project failure explains the required action"
git -C "$source_repo" checkout --quiet -- file.txt
pass "task creation rejects an ambiguous dirty source"

assignment_json=$("$ROOT/bin/omarchy-task-assign" --json "${task_id:0:12}" pi coder)
assignment_id=$(jq -r '.assignment' <<<"$assignment_json")
workspace=$(jq -r '.workspace' <<<"$assignment_json")
branch=$(jq -r '.branch' <<<"$assignment_json")
[[ -d $workspace/.git ]] || fail "assignment workspace has independent Git metadata"
[[ $(git -C "$workspace" rev-parse HEAD) == "$base_commit" ]] || fail "assignment workspace starts at the task base"
[[ $(git -C "$workspace" branch --show-current) == "$branch" ]] || fail "assignment workspace uses its private branch"
[[ -z $(git -C "$workspace" remote) ]] || fail "assignment workspace cannot push to the canonical repository"
[[ $workspace != "$source_repo" ]] || fail "assignment workspace is separate from the canonical checkout"
pass "task assignment creates an independent clone without a canonical remote"

second_json=$("$ROOT/bin/omarchy-task-assign" --json "$task_id" pi reviewer)
second_workspace=$(jq -r '.workspace' <<<"$second_json")
[[ $second_workspace != "$workspace" ]] || fail "two assignments receive different workspaces"
printf 'coder change\n' >"$workspace/file.txt"
[[ $(<"$second_workspace/file.txt") == "original" ]] || fail "one assignment cannot modify another assignment workspace"
[[ $(<"$source_repo/file.txt") == "original" ]] || fail "an assignment cannot modify the canonical checkout through its workspace"
pass "assignment workspaces do not share checkout changes"

task_json=$("$ROOT/bin/omarchy-task-inspect" "$task_id" --json)
[[ $(jq '.assignments | length' <<<"$task_json") == "2" ]] || fail "task inspection includes its assignments"
list_json=$("$ROOT/bin/omarchy-task-list" --json)
[[ $(jq -r '.[0].assignment_count' <<<"$list_json") == "2" ]] || fail "task list counts assignments"
pass "task inventory reports private assignments"

"$ROOT/bin/omarchy-task-start" "${assignment_id:0:12}" --inline --continue
[[ $(jq -r '.cwd' "$launch_log") == "$workspace" ]] || fail "task start enters the private workspace"
[[ $(jq -r '.args' "$launch_log") == "--agent-internal pi --inline --continue-session" ]] || fail "task start selects the assigned agent and session action"
[[ $(jq -r '.managed' "$launch_log") == "true" ]] || fail "task start marks the launch as managed"
[[ $(jq -r '.project' "$launch_log") == "$project_id" ]] || fail "task start passes the project identity"
[[ $(jq -r '.task' "$launch_log") == "$task_id" ]] || fail "task start passes the task identity"
[[ $(jq -r '.assignment' "$launch_log") == "$assignment_id" ]] || fail "task start passes the assignment identity"
[[ $(jq -r '.role' "$launch_log") == "coder" ]] || fail "task start passes the assignment role"
pass "task start launches the assigned agent with managed workspace context"

preflight_json=$("$ROOT/bin/omarchy-task-preflight" "$assignment_id" --json)
[[ $(jq -r '.ok' <<<"$preflight_json") == "true" ]] || fail "task preflight passes a safe assignment" "$preflight_json"
[[ $(jq -r '.checks[] | select(.name == "workspace_remote") | .status' <<<"$preflight_json") == "pass" ]] || fail "task preflight checks workspace remotes"
if OMARCHY_TEST_AGENT_MODE=host "$ROOT/bin/omarchy-task-preflight" "$assignment_id" >"$test_tmp/preflight-host-output" 2>&1; then
  fail "task preflight rejects host mode"
fi
grep -Fq 'fail: mode' "$test_tmp/preflight-host-output" || fail "task preflight explains host mode rejection"
pass "task preflight validates assignment launch requirements"

printf 'coder change\nsecond line\n' >"$workspace/file.txt"
printf 'new note\n' >"$workspace/new.txt"
status_json=$("$ROOT/bin/omarchy-task-status" "$assignment_id" --json)
[[ $(jq -r '.git.clean' <<<"$status_json") == "false" ]] || fail "task status reports dirty workspaces"
[[ $(jq -r '.git.status[]' <<<"$status_json" | grep -Fxc ' M file.txt') == "1" ]] || fail "task status includes modified files"
[[ $(jq -r '.git.status[]' <<<"$status_json" | grep -Fxc '?? new.txt') == "1" ]] || fail "task status includes untracked files"
"$ROOT/bin/omarchy-task-status" "$assignment_id" >"$test_tmp/status-output"
grep -Fq 'Clean:     false' "$test_tmp/status-output" || fail "text task status reports cleanliness"
pass "task status summarizes workspace changes"

"$ROOT/bin/omarchy-task-diff" "$assignment_id" --name-only >"$test_tmp/diff-names"
grep -Fxq 'file.txt' "$test_tmp/diff-names" || fail "task diff names modified files"
grep -Fxq 'new.txt' "$test_tmp/diff-names" || fail "task diff names untracked files"
"$ROOT/bin/omarchy-task-diff" "$assignment_id" --stat >"$test_tmp/diff-stat"
grep -Fq 'file.txt' "$test_tmp/diff-stat" || fail "task diff stat reports modified files"
pass "task diff reports assignment workspace changes"

"$ROOT/bin/omarchy-task-patch" "$assignment_id" "$test_tmp/assignment.patch" >"$test_tmp/patch-output"
grep -Fq "Wrote patch: $test_tmp/assignment.patch" "$test_tmp/patch-output" || fail "task patch reports its output path"
grep -Eq '^diff --git .*file\.txt' "$test_tmp/assignment.patch" || fail "task patch includes modified files"
grep -Eq '^diff --git .*new\.txt' "$test_tmp/assignment.patch" || fail "task patch includes untracked files"
git -C "$source_repo" apply --check "$test_tmp/assignment.patch" || fail "task patch can apply to the canonical base"
pass "task patch exports reviewable assignment changes"

(cd "$source_repo" && "$ROOT/bin/omarchy-task-apply" "$assignment_id") >"$test_tmp/apply-output"
grep -Fq "Applied assignment $assignment_id" "$test_tmp/apply-output" || fail "task apply reports the assignment it applied"
[[ $(<"$source_repo/file.txt") == $'coder change\nsecond line' ]] || fail "task apply updates modified files in the canonical checkout"
[[ $(<"$source_repo/new.txt") == "new note" ]] || fail "task apply creates untracked assignment files in the canonical checkout"
[[ $(omarchy-agent-state assignment-get "$assignment_id" | jq -r '.[0].status') == "applied" ]] || fail "task apply records applied assignment status"
pass "task apply applies assignment changes to the clean source checkout"

if (cd "$source_repo" && "$ROOT/bin/omarchy-task-apply" "$assignment_id") >"$test_tmp/apply-dirty-output" 2>&1; then
  fail "task apply rejects dirty source checkouts"
fi
grep -Fq 'uncommitted changes' "$test_tmp/apply-dirty-output" || fail "task apply explains dirty source rejection"
pass "task apply fails clearly when the source checkout is dirty"

git -C "$source_repo" checkout --quiet -- file.txt
rm -f "$source_repo/new.txt"

jq -n --arg assignment "$assignment_id" '[{assignment_id: $assignment, runtime: "podman", container: "omarchy-agent-pi-test", status: "running"}]' >"$runtime_snapshot"
"$ROOT/bin/omarchy-task-stop" "$assignment_id" >"$test_tmp/stop-output"
grep -Fq 'Stopped omarchy-agent-pi-test' "$test_tmp/stop-output" || fail "task stop reports stopped containers"
grep -Fxq 'stop omarchy-agent-pi-test' "$podman_log" || fail "task stop asks Podman to stop the active container"
[[ $(omarchy-agent-state assignment-get "$assignment_id" | jq -r '.[0].status') == "stopped" ]] || fail "task stop records stopped assignment status"
printf '[]\n' >"$runtime_snapshot"
pass "task stop stops active assignment containers"

if "$ROOT/bin/omarchy-task-stop" "$assignment_id" >"$test_tmp/no-active-output" 2>&1; then
  fail "task stop rejects assignments without active instances"
fi
grep -Fq 'No active instance' "$test_tmp/no-active-output" || fail "task stop explains when nothing is running"
pass "task stop fails clearly when the assignment is idle"

if OMARCHY_TEST_AGENT_MODE=host "$ROOT/bin/omarchy-task-start" "$assignment_id" --inline >"$test_tmp/host-output" 2>&1; then
  fail "managed task start rejects host execution"
fi
grep -Fq 'fail: mode' "$test_tmp/host-output" || fail "host rejection explains the runtime requirement"
pass "managed assignments cannot run directly on the host"

if OMARCHY_TEST_CONTAINER_DOCTOR_FAIL=true "$ROOT/bin/omarchy-task-start" "$assignment_id" --inline >"$test_tmp/doctor-output" 2>&1; then
  fail "task start rejects failed container doctor preflight"
fi
grep -Fq 'fail: container_doctor' "$test_tmp/doctor-output" || fail "task start reports container doctor preflight failure"
pass "task start runs preflight before launching agents"
