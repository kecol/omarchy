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
audit_fail_file="$test_tmp/audit-fail"
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
count=0
if [[ -n ${OMARCHY_TEST_SNAPSHOT_COUNTER:-} ]]; then
  [[ ! -f $OMARCHY_TEST_SNAPSHOT_COUNTER ]] || read -r count <"$OMARCHY_TEST_SNAPSHOT_COUNTER"
  count=$((count + 1))
  printf '%s\n' "$count" >"$OMARCHY_TEST_SNAPSHOT_COUNTER"
fi
if [[ ${OMARCHY_TEST_SNAPSHOT_FAIL:-false} == "true" ]] || (( count > ${OMARCHY_TEST_SNAPSHOT_FAIL_AFTER:-999} )); then
  echo "Managed runtime observation unavailable: fixture" >&2
  exit 2
fi
if [[ -n ${OMARCHY_TEST_RUNTIME_SNAPSHOT:-} && -f $OMARCHY_TEST_RUNTIME_SNAPSHOT ]]; then
  cat "$OMARCHY_TEST_RUNTIME_SNAPSHOT"
else
  printf '[]\n'
fi
SH

cat >"$mock_bin/omarchy-task-cleanup" <<'SH'
#!/bin/bash
if [[ ${OMARCHY_TEST_CLEANUP_FAIL:-false} == "true" ]]; then
  echo "fixture cleanup failure" >&2
  exit 23
fi
exec "$OMARCHY_PATH/bin/omarchy-task-cleanup" "$@"
SH

cat >"$mock_bin/omarchy-agent-audit" <<'SH'
#!/bin/bash
if [[ -f ${OMARCHY_TEST_AUDIT_FAIL:-} ]]; then
  echo "fail: drift - simulated runtime drift"
  exit 1
fi
echo "No active managed agent instances."
SH

cat >"$mock_bin/podman" <<'SH'
#!/bin/bash
printf '%s\n' "$*" >>"$OMARCHY_TEST_PODMAN_LOG"
if [[ ${1:-} == "--remote=false" ]]; then
  shift
elif [[ ${1:-} == "stop" ]]; then
  echo "missing local engine selection" >&2
  exit 92
fi
if [[ ${1:-} == "image" && ${2:-} == "exists" ]]; then
  exit 0
fi
if [[ ${1:-} == "stop" ]]; then
  if [[ -v CONTAINER_HOST || -v CONTAINER_CONNECTION ]]; then
    echo "remote selector reached local stop child" >&2
    exit 125
  fi
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
export OMARCHY_TEST_AUDIT_FAIL="$audit_fail_file"
export OMARCHY_TEST_PODMAN_LOG="$podman_log"
export PATH="$mock_bin:$ROOT/bin:/usr/bin"
export CONTAINER_HOST=ssh://engine.example.invalid CONTAINER_CONNECTION=fixture-remote

create_json=$(cd "$source_repo" && "$ROOT/bin/omarchy-task-create" --json "Implement isolated workspaces")
task_id=$(jq -r '.task' <<<"$create_json")
project_id=$(jq -r '.project' <<<"$create_json")
[[ $(jq -r '.base_commit' <<<"$create_json") == "$base_commit" ]] || fail "task creation records the immutable base commit"
[[ $(jq -r '.goal' <<<"$create_json") == "Implement isolated workspaces" ]] || fail "task creation records its goal"
[[ $(jq -r '.selector' <<<"$create_json") == "${task_id:0:8}" ]] || fail "task creation reports a short selector"
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
[[ $(jq -r '.selector' <<<"$assignment_json") == "${assignment_id:0:8}" ]] || fail "task assignment reports a short selector"
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
git -C "$workspace" checkout --quiet -- file.txt
pass "assignment workspaces do not share checkout changes"

task_json=$("$ROOT/bin/omarchy-task-inspect" "$task_id" --json)
[[ $(jq '.assignments | length' <<<"$task_json") == "2" ]] || fail "task inspection includes its assignments"
[[ $(jq -r '.policy.network.mode' <<<"$task_json") == "delegated-to-openshell" ]] || fail "task inspection exposes delegated runtime policy"
[[ $(jq -r '.policy.resources.memory' <<<"$task_json") == "4g" ]] || fail "task inspection exposes Podman resource limits"
list_json=$("$ROOT/bin/omarchy-task-list" --json)
[[ $(jq -r '.[0].assignment_count' <<<"$list_json") == "2" ]] || fail "task list counts assignments"
[[ $(jq -r '.[0].project_path' <<<"$list_json") == "$source_repo" ]] || fail "task list includes project paths for contextual completion"
source "$ROOT/default/bash/completions"
PATH="$mock_bin:$ROOT/bin:/usr/bin"
COMP_WORDS=(omarchy task assign "")
COMP_CWORD=3
_omarchy_complete
[[ ${COMPREPLY[*]} == "$task_id" ]] || fail "task completion prefers tasks from the current project" "${COMPREPLY[*]}"
pass "task inventory reports private assignments"

expect_refusal() {
  local name=$1
  shift
  if "$@" >"$test_tmp/refusal.stdout" 2>"$test_tmp/refusal.stderr"; then
    fail "$name refuses unavailable runtime observation"
  fi
  grep -Fq 'Managed runtime observation unavailable' "$test_tmp/refusal.stderr" || fail "$name retains the availability diagnostic"
}

# Reconcile first: task status intentionally retains its existing earlier reconciliation write.
"$ROOT/bin/omarchy-task-reconcile" "$assignment_id" --json >/dev/null
before_status=$(omarchy-agent-state assignment-get "$assignment_id" | jq -r '.[0].status')
for command in preflight start stop cleanup status archive; do
  selector=$assignment_id
  [[ $command != "archive" ]] || selector=$task_id
  OMARCHY_TEST_SNAPSHOT_FAIL=true expect_refusal "$command" "$ROOT/bin/omarchy-task-$command" "$selector"
  [[ -d $workspace/.git && -d $second_workspace/.git ]] || fail "$command preserves assignment workspaces on unknown runtime"
  [[ $(omarchy-agent-state assignment-get "$assignment_id" | jq -r '.[0].status') == "$before_status" ]] || fail "$command does not finalize or launch an unobserved assignment"
  [[ $(omarchy-agent-state task-get "$task_id" | jq -r '.[0].status') != "archived" ]] || fail "$command does not archive an unobserved task"
done
for command in cleanup archive; do
  selector=$assignment_id
  [[ $command != "archive" ]] || selector=$task_id
  OMARCHY_TEST_SNAPSHOT_FAIL=true expect_refusal "$command --force" "$ROOT/bin/omarchy-task-$command" "$selector" --force
  [[ -d $workspace/.git ]] || fail "force cannot delete a workspace when observation is unavailable"
done
[[ ! -s $launch_log ]] || fail "unavailable start must not invoke the agent"
if [[ -f $podman_log ]] && grep -q 'stop ' "$podman_log"; then fail "unavailable stop must not call the engine stop action"; fi
pass "task gates and status refuse unknown runtime, including forced cleanup/archive"

# First observation passes preflight; the later start recheck must still refuse.
OMARCHY_TEST_SNAPSHOT_COUNTER="$test_tmp/start-counter" OMARCHY_TEST_SNAPSHOT_FAIL_AFTER=1 \
  expect_refusal "start recheck" "$ROOT/bin/omarchy-task-start" "$assignment_id" --inline
[[ ! -s $launch_log ]] || fail "failed late recheck must not launch an agent"
[[ $(omarchy-agent-state assignment-get "$assignment_id" | jq -r '.[0].status') == "$before_status" ]] || fail "failed late recheck must not mark launched"
pass "task start checks observation again after preflight and audit"

"$ROOT/bin/omarchy-task-start" "${assignment_id:0:12}" --inline --continue
[[ $(jq -r '.cwd' "$launch_log") == "$workspace" ]] || fail "task start enters the private workspace"
launch_args=$(jq -r '.args' "$launch_log")
[[ $launch_args == *"--agent-internal pi --inline --continue-session --prompt"* ]] || fail "task start selects the assigned agent and session action" "$launch_args"
[[ $launch_args == *"Goal:"* && $launch_args == *"Implement isolated workspaces"* ]] || fail "task start passes the task goal to the agent" "$launch_args"
[[ $launch_args == *"Do not edit the source checkout directly"* ]] || fail "task start passes workspace safety rules to the agent" "$launch_args"
[[ $(jq -r '.managed' "$launch_log") == "true" ]] || fail "task start marks the launch as managed"
[[ $(jq -r '.project' "$launch_log") == "$project_id" ]] || fail "task start passes the project identity"
[[ $(jq -r '.task' "$launch_log") == "$task_id" ]] || fail "task start passes the task identity"
[[ $(jq -r '.assignment' "$launch_log") == "$assignment_id" ]] || fail "task start passes the assignment identity"
[[ $(jq -r '.role' "$launch_log") == "coder" ]] || fail "task start passes the assignment role"
pass "task start launches the assigned agent with managed workspace context"

instance_id=11111111-1111-4111-8111-111111111111
omarchy-agent-state start "$instance_id" pi pi podman omarchy-agent-pi-test "$project_id" "$workspace" /workspace/test localhost/omarchy-harness-pi:latest running
omarchy-agent-state finish "$instance_id" stopped 0
log_json=$("$ROOT/bin/omarchy-task-log" "$assignment_id" --json)
[[ $(jq -r '.instances[0].id' <<<"$log_json") == "$instance_id" ]] || fail "task log includes assignment runtime instances" "$log_json"
[[ $(jq -r '.instances[0].events[-1].event' <<<"$log_json") == "stopped" ]] || fail "task log includes instance lifecycle events" "$log_json"
"$ROOT/bin/omarchy-task-log" "$assignment_id" >"$test_tmp/task-log-output"
grep -Fq "$instance_id" "$test_tmp/task-log-output" || fail "task log text includes instance identifiers"
pass "task log reports assignment runtime history"

preflight_json=$("$ROOT/bin/omarchy-task-preflight" "$assignment_id" --json)
[[ $(jq -r '.ok' <<<"$preflight_json") == "true" ]] || fail "task preflight passes a safe assignment" "$preflight_json"
[[ $(jq -r '.checks[] | select(.name == "workspace_remote") | .status' <<<"$preflight_json") == "pass" ]] || fail "task preflight checks workspace remotes"
[[ $(jq -r '.checks[] | select(.name == "workspace_base") | .status' <<<"$preflight_json") == "pass" ]] || fail "task preflight checks task base ancestry"
[[ $(jq -r '.checks[] | select(.name == "runtime_policy") | .status' <<<"$preflight_json") == "warn" ]] || fail "task preflight declares delegated runtime policy"
[[ $(jq -r '.policy.credentials.mode' <<<"$preflight_json") == "delegated-to-openshell" ]] || fail "task preflight exposes delegated credential policy"
[[ $(jq -r '.policy.resources.pids' <<<"$preflight_json") == "1024" ]] || fail "task preflight exposes Podman resource limits"
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
grep -Fq 'Workspace clean: false' "$test_tmp/status-output" || fail "text task status reports workspace cleanliness"
grep -Fq 'Source state:    ready-to-apply' "$test_tmp/status-output" || fail "text task status reports source reconciliation state"
grep -Fq 'Network:        delegated-to-openshell' "$test_tmp/status-output" || fail "text task status reports delegated network policy"
grep -Fq 'Resources:      memory=4g, pids=1024' "$test_tmp/status-output" || fail "text task status reports Podman resource limits"
pass "task status summarizes workspace changes"

"$ROOT/bin/omarchy-task-diff" "$assignment_id" --name-only >"$test_tmp/diff-names"
grep -Fxq 'file.txt' "$test_tmp/diff-names" || fail "task diff names modified files"
grep -Fxq 'new.txt' "$test_tmp/diff-names" || fail "task diff names untracked files"
"$ROOT/bin/omarchy-task-diff" "$assignment_id" --stat >"$test_tmp/diff-stat"
grep -Fq 'file.txt' "$test_tmp/diff-stat" || fail "task diff stat reports modified files"
pass "task diff reports assignment workspace changes"

if "$ROOT/bin/omarchy-task-cleanup" "$assignment_id" >"$test_tmp/cleanup-unapplied-output" 2>&1; then
  fail "task cleanup rejects unapplied assignment workspaces without force"
fi
grep -Fq 'Use --force' "$test_tmp/cleanup-unapplied-output" || fail "task cleanup explains force for unapplied changes"
pass "task cleanup protects unapplied assignment changes"

reconcile_json=$("$ROOT/bin/omarchy-task-reconcile" "$assignment_id" --json)
[[ $(jq -r '.status' <<<"$reconcile_json") == "ready-to-apply" ]] || fail "task reconcile detects cleanly applicable assignment changes" "$reconcile_json"
pass "task reconcile reports unapplied assignment changes"

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
reconcile_json=$("$ROOT/bin/omarchy-task-reconcile" "$assignment_id" --json)
[[ $(jq -r '.status' <<<"$reconcile_json") == "applied" ]] || fail "task reconcile detects assignment changes already in source" "$reconcile_json"
"$ROOT/bin/omarchy-task-status" "$assignment_id" >"$test_tmp/status-applied-output"
grep -Fq 'Source state:    applied' "$test_tmp/status-applied-output" || fail "task status reports applied source reconciliation state"
pass "task apply applies assignment changes to the clean source checkout"

if (cd "$source_repo" && "$ROOT/bin/omarchy-task-apply" "$assignment_id") >"$test_tmp/apply-dirty-output" 2>&1; then
  fail "task apply rejects dirty source checkouts"
fi
grep -Fq 'uncommitted changes' "$test_tmp/apply-dirty-output" || fail "task apply explains dirty source rejection"
pass "task apply fails clearly when the source checkout is dirty"

git -C "$source_repo" checkout --quiet -- file.txt
rm -f "$source_repo/new.txt"
printf 'unrelated\n' >"$source_repo/other.txt"
git -C "$source_repo" add other.txt
git -C "$source_repo" commit --quiet -m 'Unrelated source change'
if (cd "$source_repo" && "$ROOT/bin/omarchy-task-apply" "$assignment_id") >"$test_tmp/apply-old-base-output" 2>&1; then
  fail "task apply without --3way rejects advanced source checkouts"
fi
grep -Fq 'Use --3way' "$test_tmp/apply-old-base-output" || fail "task apply suggests --3way for advanced source checkouts"
(cd "$source_repo" && "$ROOT/bin/omarchy-task-apply" "$assignment_id" --3way) >"$test_tmp/apply-3way-output"
[[ $(<"$source_repo/file.txt") == $'coder change\nsecond line' ]] || fail "task apply --3way updates modified files"
[[ $(<"$source_repo/new.txt") == "new note" ]] || fail "task apply --3way creates new files"
[[ $(<"$source_repo/other.txt") == "unrelated" ]] || fail "task apply --3way preserves unrelated current changes"
pass "task apply can apply assignment changes onto a newer clean checkout"

"$ROOT/bin/omarchy-task-cleanup" "$assignment_id" >"$test_tmp/cleanup-output"
grep -Fq "Cleaned assignment workspace: $assignment_id" "$test_tmp/cleanup-output" || fail "task cleanup reports cleaned assignments"
[[ ! -e $workspace ]] || fail "task cleanup removes the assignment workspace"
[[ $(omarchy-agent-state assignment-get "$assignment_id" | jq -r '.[0].status') == "cleaned" ]] || fail "task cleanup records cleaned assignment status"
pass "task cleanup removes applied assignment workspaces"

git -C "$source_repo" reset --hard --quiet HEAD
git -C "$source_repo" clean -fd --quiet

workspace=$(jq -r '.workspace' <<<"$second_json")
assignment_id=$(jq -r '.assignment' <<<"$second_json")

jq -n --arg assignment "$assignment_id" '[{assignment_id: $assignment, runtime: "podman", container: "omarchy-agent-pi-test", status: "running"}]' >"$runtime_snapshot"
"$ROOT/bin/omarchy-task-stop" "$assignment_id" >"$test_tmp/stop-output"
grep -Fq 'Stopped omarchy-agent-pi-test' "$test_tmp/stop-output" || fail "task stop reports stopped containers"
grep -Fxq -- '--remote=false stop omarchy-agent-pi-test' "$podman_log" || fail "task stop asks Podman to stop the active container"
[[ $CONTAINER_HOST == "ssh://engine.example.invalid" && $CONTAINER_CONNECTION == "fixture-remote" ]] || fail "task stop preserves parent remote defaults"
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

touch "$audit_fail_file"
if "$ROOT/bin/omarchy-task-start" "$assignment_id" --inline >"$test_tmp/audit-output" 2>&1; then
  fail "task start rejects failed active runtime audit"
fi
grep -Fq 'runtime audit failed' "$test_tmp/audit-output" || fail "task start reports active runtime audit failure"
rm -f "$audit_fail_file"
pass "task start runs active runtime audit before launching agents"

"$ROOT/bin/omarchy-task-archive" "$task_id" >"$test_tmp/archive-output"
grep -Fq "Archived task: $task_id" "$test_tmp/archive-output" || fail "task archive reports archived tasks"
[[ $(omarchy-agent-state task-get "$task_id" | jq -r '.[0].status') == "archived" ]] || fail "task archive records archived task status"
[[ $(omarchy-agent-state assignment-get "$assignment_id" | jq -r '.[0].status') == "cleaned" ]] || fail "task archive cleans safe assignment workspaces"
[[ ! -e $workspace ]] || fail "task archive removes safe assignment workspaces"
pass "task archive closes tasks with safe assignments"

# The actual archive and nested cleanup run against disposable Git/SQLite state.
# Initial snapshot succeeds; one or more later cleanup snapshots fail.
for force in false true; do
  for completed in 0 1; do
    case_task=$(cd "$source_repo" && "$ROOT/bin/omarchy-task-create" --json "Archive availability fixture" | jq -r '.task')
    "$ROOT/bin/omarchy-task-assign" --json "$case_task" pi first >/dev/null
    if (( completed == 1 )); then
      "$ROOT/bin/omarchy-task-assign" --json "$case_task" pi second >/dev/null
    fi
    ordered=$(omarchy-agent-state task-assignments "$case_task")
    protected_id=$(jq -r --argjson index "$completed" '.[$index].id' <<<"$ordered")
    protected_workspace=$(jq -r --argjson index "$completed" '.[$index].workspace_path' <<<"$ordered")
    force_args=()
    [[ $force != "true" ]] || force_args+=(--force)
    counter="$test_tmp/archive-counter-$force-$completed"
    OMARCHY_TEST_SNAPSHOT_COUNTER="$counter" OMARCHY_TEST_SNAPSHOT_FAIL_AFTER=$((completed + 1)) \
      expect_refusal "archive nested cleanup" "$ROOT/bin/omarchy-task-archive" "$case_task" "${force_args[@]}"
    [[ -d $protected_workspace/.git ]] || fail "archive preserves the workspace whose cleanup lost observation"
    [[ $(omarchy-agent-state assignment-get "$protected_id" | jq -r '.[0].status') != "cleaned" ]] || fail "failed nested cleanup cannot finalize its assignment"
    [[ $(omarchy-agent-state task-get "$case_task" | jq -r '.[0].status') != "archived" ]] || fail "archive cannot finalize after nested observation failure"
    grep -Fq 'Task archive incomplete' "$test_tmp/refusal.stderr" || fail "archive reports incomplete cleanup"
    if (( completed == 1 )); then
      first_id=$(jq -r '.[0].id' <<<"$ordered")
      first_workspace=$(jq -r '.[0].workspace_path' <<<"$ordered")
      [[ ! -e $first_workspace ]] || fail "earlier completed cleanup is not rolled back"
      [[ $(omarchy-agent-state assignment-get "$first_id" | jq -r '.[0].status') == "cleaned" ]] || fail "partial cleanup keeps truthful earlier registry state"
    fi
    # Recovery with known-empty observation should still complete normally.
    "$ROOT/bin/omarchy-task-archive" "$case_task" "${force_args[@]}" >/dev/null
    [[ $(omarchy-agent-state task-get "$case_task" | jq -r '.[0].status') == "archived" ]] || fail "archive can finish after observation recovers"
  done
  case_task=$(cd "$source_repo" && "$ROOT/bin/omarchy-task-create" --json "Cleanup failure fixture" | jq -r '.task')
  case_assignment=$("$ROOT/bin/omarchy-task-assign" --json "$case_task" pi tester)
  if OMARCHY_TEST_CLEANUP_FAIL=true "$ROOT/bin/omarchy-task-archive" "$case_task" "${force_args[@]}" >"$test_tmp/cleanup-failure.stdout" 2>"$test_tmp/cleanup-failure.stderr"; then
    fail "archive refuses unrelated nested cleanup failure"
  else
    status=$?
    (( status == 23 )) || fail "archive retains the nested cleanup failure status"
  fi
  [[ -d $(jq -r '.workspace' <<<"$case_assignment")/.git ]] || fail "failed cleanup leaves its workspace intact"
  [[ $(omarchy-agent-state task-get "$case_task" | jq -r '.[0].status') != "archived" ]] || fail "force cannot bypass a nested cleanup failure"
  "$ROOT/bin/omarchy-task-archive" "$case_task" "${force_args[@]}" >/dev/null
  pass "archive propagates nested cleanup failure and partial progress (force=$force)"
done
