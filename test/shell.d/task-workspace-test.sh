#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

test_tmp=$(mktemp -d)
trap 'rm -rf "$test_tmp"' EXIT

mock_bin="$test_tmp/bin"
test_home="$test_tmp/home"
source_repo="$test_tmp/source project"
launch_log="$test_tmp/launch-log"
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
printf '[]\n'
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

if OMARCHY_TEST_AGENT_MODE=host "$ROOT/bin/omarchy-task-start" "$assignment_id" --inline >"$test_tmp/host-output" 2>&1; then
  fail "managed task start rejects host execution"
fi
grep -Fq 'require container mode' "$test_tmp/host-output" || fail "host rejection explains the runtime requirement"
pass "managed assignments cannot run directly on the host"
