#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

test_tmp=$(mktemp -d)
trap 'rm -rf "$test_tmp"' EXIT

mock_bin="$test_tmp/bin"
test_home="$test_tmp/home"
snapshot_file="$test_tmp/snapshot.json"
inspection_file="$test_tmp/inspection.json"
engine_id=$(printf '%064d' 1)
podman_log="$test_tmp/podman-log"
state_log="$test_tmp/state-log"
mkdir -p "$mock_bin" "$test_home" "$test_tmp/commands"

# Keep the actual audit script, but never run its adjacent advisory doctor.
audit_command="$test_tmp/commands/omarchy-agent-audit"
cp "$ROOT/bin/omarchy-agent-audit" "$audit_command"
printf '#!/bin/bash\necho doctor >>"$OMARCHY_TEST_STATE_LOG"\nprintf '\''{"checks":[]}\\n'\''\n' >"$test_tmp/commands/omarchy-agent-openshell-doctor"
chmod +x "$test_tmp/commands/omarchy-agent-openshell-doctor"

cat >"$mock_bin/omarchy-agent-mode" <<'SH'
#!/bin/bash
if [[ ${OMARCHY_TEST_MODE_FAIL:-false} == "true" ]]; then exit 1; fi
printf '%s\n' "${OMARCHY_TEST_AGENT_MODE:-container}"
SH

cat >"$mock_bin/omarchy-agent-runtime-snapshot" <<'SH'
#!/bin/bash
if (( ${OMARCHY_TEST_SNAPSHOT_STATUS:-0} != 0 )); then
  echo "Managed runtime observation unavailable: fixture" >&2
  exit "$OMARCHY_TEST_SNAPSHOT_STATUS"
fi
cat "$OMARCHY_TEST_SNAPSHOT"
SH

cat >"$mock_bin/omarchy-agent-state" <<'SH'
#!/bin/bash
case "$1" in
  get)
    echo history >>"$OMARCHY_TEST_STATE_LOG"
    cat "$OMARCHY_TEST_HISTORY"
    ;;
  finish|assignment-status)
    printf '%s\t' "$@" >>"$OMARCHY_TEST_STATE_LOG"
    printf '\n' >>"$OMARCHY_TEST_STATE_LOG"
    ;;
  *)
    exit 1
    ;;
esac
SH

cat >"$mock_bin/podman" <<'SH'
#!/bin/bash
printf '%s\n' "$*" >>"$OMARCHY_TEST_PODMAN_LOG"
[[ ${1:-} == "--remote=false" ]] || { echo "missing local engine selection" >&2; exit 92; }
if [[ -v CONTAINER_HOST || -v CONTAINER_CONNECTION ]]; then
  echo "remote selector reached local engine child" >&2
  exit 125
fi
shift
case ${1:-} in
  info) [[ ${OMARCHY_TEST_ENGINE_FAIL:-false} != "true" ]] ;;
  ps)
    if [[ ${OMARCHY_TEST_ENUM_NUL:-false} == "true" ]]; then
      printf '%s\0\n' "$OMARCHY_TEST_ENGINE_IDS"
    else
      printf '%s\n' "$OMARCHY_TEST_ENGINE_IDS"
    fi
    echo "private-engine-detail" >&2
    exit "${OMARCHY_TEST_ENUM_STATUS:-0}"
    ;;
  inspect)
    cat "$OMARCHY_TEST_INSPECTION" || exit 1
    echo "private-engine-detail" >&2
    exit "${OMARCHY_TEST_INSPECT_STATUS:-0}"
    ;;
  stop) exit 0 ;;
  *) echo "unexpected podman call: $*" >&2; exit 1 ;;
esac
SH

chmod +x "$mock_bin"/*

cat >"$snapshot_file" <<'JSON'
[
  {
    "instance": "019abcde-1111-2222-3333-444444444444",
    "agent": "pi",
    "harness": "pi",
    "runtime": "podman",
    "project_id": "project123",
    "managed_workspace": true,
    "task_id": "task123",
    "assignment_id": "assignment123",
    "filesystem": {
      "workspace": "read-write",
      "source": "unmounted"
    },
    "resources": {
      "memory": "4g",
      "pids": "1024",
      "cpus": null
    },
    "container": "omarchy-agent-pi-019abcde1111",
    "container_id": "container123",
    "status": "running",
    "pid": 1234,
    "image": "localhost/omarchy-harness-pi:latest",
    "image_digest": "sha256:image",
    "started_at": "2026-10-05T10:00:00Z",
    "workspace": "/workspace/project123",
    "mounts": [
      {
        "type": "bind",
        "source": "/home/test/Project",
        "destination": "/workspace/project123",
        "read_write": true,
        "options": ["rw"]
      },
      {
        "type": "volume",
        "source": "omarchy-agent-pi-home",
        "destination": "/home/agent",
        "read_write": true,
        "options": ["rw"]
      }
    ],
    "network": {
      "mode": "private",
      "ports": {},
      "networks": ["podman"]
    },
    "security": {
      "user": "agent",
      "userns": "keep-id",
      "capabilities_add": [],
      "capabilities_drop": ["CAP_AUDIT_WRITE", "CAP_CHOWN"],
      "security_options": ["no-new-privileges"]
    }
  }
]
JSON

history_file="$test_tmp/history.json"
cat >"$history_file" <<'JSON'
[
  {
    "id": "019fffff-1111-2222-3333-444444444444",
    "agent": "pi",
    "harness": "pi",
    "runtime": "podman",
    "status": "stopped",
    "container_name": "omarchy-agent-pi-019fffff1111",
    "project_id": "project123",
    "workspace_host": "/home/test/Project",
    "workspace_container": "/workspace/project123",
    "image": "localhost/omarchy-harness-pi:latest",
    "created_at": "2026-10-05T09:00:00Z",
    "stopped_at": "2026-10-05T09:30:00Z",
    "exit_code": 0
  }
]
JSON

export HOME="$test_home"
export OMARCHY_PATH="$ROOT"
export OMARCHY_TEST_SNAPSHOT="$snapshot_file"
export OMARCHY_TEST_INSPECTION="$inspection_file"
export OMARCHY_TEST_ENGINE_IDS="$engine_id"
export OMARCHY_TEST_HISTORY="$history_file"
export OMARCHY_TEST_PODMAN_LOG="$podman_log"
export OMARCHY_TEST_STATE_LOG="$state_log"
export PATH="$mock_bin:$ROOT/bin:/usr/bin"
export CONTAINER_HOST=ssh://engine.example.invalid CONTAINER_CONNECTION=fixture-remote

jq -n --arg id "$engine_id" '[{
  Id: $id, Name: "fixture", ImageName: "fixture-image",
  Config: {User: "agent", Labels: {"org.omarchy.instance": "routing-fixture"}},
  State: {Status: "running", Pid: 123, StartedAt: "2026-01-01T00:00:00Z"},
  Mounts: [], HostConfig: {NetworkMode: "private", UsernsMode: "keep-id"}, NetworkSettings: {}
}]' >"$inspection_file"
cp "$inspection_file" "$test_tmp/valid-inspection.json"

expect_unavailable() {
  local stage=$1 status
  shift
  if "$@" >"$test_tmp/unavailable.stdout" 2>"$test_tmp/unavailable.stderr"; then
    fail "unavailable $stage must fail"
  else
    status=$?
  fi
  (( status == 2 )) || fail "unavailable $stage returns status 2" "$status"
  [[ ! -s $test_tmp/unavailable.stdout ]] || fail "unavailable $stage publishes no snapshot"
  grep -Fq "Managed runtime observation unavailable: $stage" "$test_tmp/unavailable.stderr" || fail "unavailable $stage has a stage diagnostic"
  if grep -Fq private-engine-detail "$test_tmp/unavailable.stderr"; then fail "engine diagnostics stay sanitized"; fi
}

# Exercise the real producer, not the synthetic snapshot used by list/audit below.
observed=$("$ROOT/bin/omarchy-agent-runtime-snapshot")
[[ $(jq -r '.[0].instance' <<<"$observed") == "routing-fixture" ]] || fail "snapshot queries local engine under remote defaults" "$observed"
[[ $CONTAINER_HOST == "ssh://engine.example.invalid" && $CONTAINER_CONNECTION == "fixture-remote" ]] || fail "snapshot preserves parent remote defaults"
for operation in info ps inspect; do
  grep -Eq "^--remote=false $operation( |$)" "$podman_log" || fail "snapshot explicitly selects local $operation"
done
jq -e --arg id "$engine_id" 'length == 1 and .[0].container_id == $id and .[0].pid == 123 and .[0].status == "running" and .[0].filesystem.source == "unknown"' <<<"$observed" >/dev/null || fail "valid observation preserves projected fields and optional label defaults"
jq --arg id "$(printf '%064d' 2)" '. + [.[0] | .Id = $id]' "$test_tmp/valid-inspection.json" >"$inspection_file"
observed=$(OMARCHY_TEST_ENGINE_IDS="$engine_id"$'\n'"$(printf '%064d' 2)" "$ROOT/bin/omarchy-agent-runtime-snapshot")
[[ $(jq 'length' <<<"$observed") == 2 ]] || fail "snapshot covers a valid multi-container enumeration"
cp "$test_tmp/valid-inspection.json" "$inspection_file"
OMARCHY_TEST_ENGINE_FAIL=true expect_unavailable readiness "$ROOT/bin/omarchy-agent-runtime-snapshot"
# Simulate a missing optional engine without consulting the host executable.
printf '#!/bin/bash\nexit 0\n' >"$mock_bin/omarchy-cmd-missing"
chmod +x "$mock_bin/omarchy-cmd-missing"
expect_unavailable "engine missing" "$ROOT/bin/omarchy-agent-runtime-snapshot"
rm "$mock_bin/omarchy-cmd-missing"
for ids in "" "$engine_id"; do
  OMARCHY_TEST_ENGINE_IDS="$ids" OMARCHY_TEST_ENUM_STATUS=23 expect_unavailable enumeration "$ROOT/bin/omarchy-agent-runtime-snapshot"
done
for ids in "short-id" "$engine_id"$'\n'"$engine_id"; do
  OMARCHY_TEST_ENGINE_IDS="$ids" expect_unavailable enumeration "$ROOT/bin/omarchy-agent-runtime-snapshot"
done
OMARCHY_TEST_ENUM_NUL=true expect_unavailable enumeration "$ROOT/bin/omarchy-agent-runtime-snapshot"
empty=$(OMARCHY_TEST_ENGINE_IDS= "$ROOT/bin/omarchy-agent-runtime-snapshot")
[[ $empty == "[]" ]] || fail "a successful empty enumeration remains empty"
OMARCHY_TEST_INSPECT_STATUS=23 expect_unavailable inspection "$ROOT/bin/omarchy-agent-runtime-snapshot"
pass "snapshot distinguishes missing/readiness/enumeration/inspection failure from genuine empty success"

for shape in empty garbage nul multiple object missing duplicate unexpected pid labels mounts networks; do
  stage="inspection validation"
  case "$shape" in
    empty) : >"$inspection_file" ;;
    garbage) printf 'not JSON\n' >"$inspection_file"; stage=inspection ;;
    nul)
      python -c 'import sys; data = open(sys.argv[1], "rb").read(); open(sys.argv[2], "wb").write(data.replace(b"routing-fixture", b"routing-\x00fixture"))' "$test_tmp/valid-inspection.json" "$inspection_file"
      stage=inspection
      ;;
    multiple) printf '[]\n[]\n' >"$inspection_file" ;;
    object) printf '{}\n' >"$inspection_file" ;;
    missing) printf '[]\n' >"$inspection_file" ;;
    duplicate) jq '. + .' "$test_tmp/valid-inspection.json" >"$inspection_file" ;;
    unexpected) jq '.[0].Id = ("f" * 64)' "$test_tmp/valid-inspection.json" >"$inspection_file" ;;
    pid) jq 'del(.[0].State.Pid)' "$test_tmp/valid-inspection.json" >"$inspection_file" ;;
    labels) jq '.[0].Config.Labels = []' "$test_tmp/valid-inspection.json" >"$inspection_file" ;;
    mounts) jq '.[0].Mounts = null' "$test_tmp/valid-inspection.json" >"$inspection_file" ;;
    networks) jq '.[0].NetworkSettings.Networks = []' "$test_tmp/valid-inspection.json" >"$inspection_file" ;;
  esac
  expect_unavailable "$stage" "$ROOT/bin/omarchy-agent-runtime-snapshot"
done
cp "$test_tmp/valid-inspection.json" "$inspection_file"
pass "snapshot rejects malformed, partial, duplicated and substituted inspection responses without publishing data"

# A failing projector must not leak even a syntactically valid partial result.
cat >"$mock_bin/jq" <<'SH'
#!/bin/bash
if [[ $1 == "-e" || $1 == "-Rsec" || $1 == "-r" || $1 == "-cs" ]]; then
  exec /usr/bin/jq "$@"
else
  printf '[]\n'
  exit 23
fi
SH
chmod +x "$mock_bin/jq"
expect_unavailable projection "$ROOT/bin/omarchy-agent-runtime-snapshot"
rm "$mock_bin/jq"
pass "snapshot buffers projected output until the projector succeeds"

list_json=$("$ROOT/bin/omarchy-agent-list" --json)
pi_json=$(jq -c '.[] | select(.agent == "pi")' <<<"$list_json")
[[ $(jq -r '.agent' <<<"$pi_json") == "pi" ]] || fail "agent list includes the built-in Pi agent"
[[ $(jq -r '.runtime' <<<"$pi_json") == "podman" ]] || fail "agent list reports the effective container runtime"
[[ $(jq -r '.running_instances' <<<"$pi_json") == "1" ]] || fail "agent list counts active instances"
[[ $(jq -r '.runtime_available' <<<"$pi_json") == "true" ]] || fail "agent list marks observed counts available"
[[ $(jq -r '.source' <<<"$pi_json") == "builtin" ]] || fail "agent list identifies the built-in definition source"
[[ $(jq -r '.[] | select(.agent == "codex") | .running_instances' <<<"$list_json") == "0" ]] || fail "agent list includes the configured Codex harness without borrowing Pi instances"
pass "agent list reports configured agents and active instance counts"

host_list=$(OMARCHY_TEST_AGENT_MODE=host "$ROOT/bin/omarchy-agent-list" --json)
[[ $(jq -r '.[0].runtime' <<<"$host_list") == "host" ]] || fail "agent list reports host as the effective runtime"
[[ $(jq -r '.[0].configured_runtime' <<<"$host_list") == "podman" ]] || fail "agent list preserves the configured container runtime"
pass "agent list distinguishes effective and configured runtimes"

unknown=$(OMARCHY_TEST_SNAPSHOT_STATUS=2 "$ROOT/bin/omarchy-agent-list" --json 2>"$test_tmp/list-warning")
jq -e 'length > 0 and all(.[]; .running_instances == null and .runtime_available == false)' <<<"$unknown" >/dev/null || fail "configured list reports unavailable counts as null"
[[ $(jq 'map(del(.running_instances, .runtime_available))' <<<"$unknown") == "$(jq 'map(del(.running_instances, .runtime_available))' <<<"$list_json")" ]] || fail "configured list retains its definitions during unavailability"
OMARCHY_TEST_SNAPSHOT_STATUS=2 "$ROOT/bin/omarchy-agent-list" >"$test_tmp/list-text" 2>/dev/null
grep -Eq 'pi +pi +podman +unknown +builtin' "$test_tmp/list-text" || fail "configured list displays unknown rather than zero"
if OMARCHY_TEST_SNAPSHOT_STATUS=23 "$ROOT/bin/omarchy-agent-list" --json >"$test_tmp/list-error" 2>/dev/null; then fail "configured list preserves unexpected producer failures"; fi
if OMARCHY_TEST_SNAPSHOT_STATUS=2 OMARCHY_TEST_MODE_FAIL=true "$ROOT/bin/omarchy-agent-list" --json >"$test_tmp/list-error" 2>/dev/null; then fail "configured list preserves mode errors"; fi
mkdir -p "$HOME/.config/omarchy/agents"
printf '{}\n' >"$HOME/.config/omarchy/agents/invalid.json"
if OMARCHY_TEST_SNAPSHOT_STATUS=2 "$ROOT/bin/omarchy-agent-list" --json >"$test_tmp/list-error" 2>/dev/null; then fail "configured list preserves definition errors"; fi
rm "$HOME/.config/omarchy/agents/invalid.json"
pass "configured listing degrades only runtime availability, not definition or mode failures"

: >"$state_log"
: >"$podman_log"
OMARCHY_TEST_SNAPSHOT_STATUS=2 expect_unavailable fixture "$ROOT/bin/omarchy-agent-ps" --json
OMARCHY_TEST_SNAPSHOT_STATUS=2 expect_unavailable fixture "$ROOT/bin/omarchy-agent-inspect" 019fffff --json
OMARCHY_TEST_SNAPSHOT_STATUS=2 expect_unavailable fixture "$audit_command" --json
OMARCHY_TEST_SNAPSHOT_STATUS=2 expect_unavailable fixture "$audit_command" --fix
[[ ! -s $state_log && ! -s $podman_log ]] || fail "unavailable reports/audit must not read history, call doctor, stop or finalize state"
pass "runtime reports and audit refuse unavailable observation before history or dependent actions"

ps_json=$("$ROOT/bin/omarchy-agent-ps" --json)
[[ $(jq -r '.[0].instance' <<<"$ps_json") == "019abcde-1111-2222-3333-444444444444" ]] || fail "agent ps reports the active instance"
[[ $(jq -r '.[0].workspace' <<<"$ps_json") == "/workspace/project123" ]] || fail "agent ps reports the runtime workspace"
pass "agent ps reports observed active instances"

audit_json=$("$audit_command" --json)
[[ $(jq -r '.ok' <<<"$audit_json") == "true" ]] || fail "agent audit passes safe active instances" "$audit_json"
[[ $(jq -r '.checks[] | select(.name == "source_unmounted") | .status' <<<"$audit_json") == "pass" ]] || fail "agent audit checks source mount policy" "$audit_json"
[[ $(jq -r '.checks[] | select(.name == "resources") | .status' <<<"$audit_json") == "pass" ]] || fail "agent audit checks resource policy" "$audit_json"
python - "$snapshot_file" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data[0]["filesystem"]["source"] = "mounted"
json.dump(data, open(path, "w"))
PY
if "$audit_command" >"$test_tmp/audit-fail" 2>&1; then
  fail "agent audit rejects runtime policy drift"
fi
grep -Fq 'source_unmounted' "$test_tmp/audit-fail" || fail "agent audit names source mount drift"
"$audit_command" --fix >"$test_tmp/audit-fix"
grep -Fxq -- '--remote=false stop omarchy-agent-pi-019abcde1111' "$podman_log" || fail "agent audit --fix stops drifted containers"
grep -Fq $'assignment-status\tassignment123\tfailed' "$state_log" || fail "agent audit --fix marks managed assignments failed"
grep -Fq 'fix: 019abcde-111 stopped omarchy-agent-pi-019abcde1111' "$test_tmp/audit-fix" || fail "agent audit --fix reports stopped containers"
python - "$snapshot_file" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path))
data[0]["filesystem"]["source"] = "unmounted"
json.dump(data, open(path, "w"))
PY
pass "agent audit detects active runtime drift"

inspect_json=$("$ROOT/bin/omarchy-agent-inspect" 019abcde --json)
[[ $(jq -r '.record_source' <<<"$inspect_json") == "observed" ]] || fail "agent inspect prefers observed runtime state"
[[ $(jq -r '.filesystem_policy.host_root_mounted' <<<"$inspect_json") == "false" ]] || fail "agent inspect detects that host root is not mounted"
[[ $(jq -r '.filesystem_policy.source_unmounted' <<<"$inspect_json") == "true" ]] || fail "agent inspect reports source checkout is unmounted"
[[ $(jq -r '.filesystem_policy.workspace_access' <<<"$inspect_json") == "read-write" ]] || fail "agent inspect reports workspace access policy"
[[ $(jq -r '.credential_policy.readable_by_agent' <<<"$inspect_json") == "true" ]] || fail "agent inspect reports credential exposure"
[[ $(jq -r '.network_policy.egress_verified' <<<"$inspect_json") == "false" ]] || fail "agent inspect does not claim unverified network enforcement"
pass "agent inspect reports filesystem, credential, and network security state"

printf '[]\n' >"$snapshot_file"
empty_list=$("$ROOT/bin/omarchy-agent-list" --json)
jq -e 'all(.[]; .running_instances == 0 and .runtime_available == true)' <<<"$empty_list" >/dev/null || fail "successful empty inventory gives known numeric zero counts"
history_json=$("$ROOT/bin/omarchy-agent-inspect" 019fffff --json)
[[ $(jq -r '.record_source' <<<"$history_json") == "registry" ]] || fail "agent inspect uses the registry for a stopped instance"
[[ $(jq -r '.status' <<<"$history_json") == "stopped" ]] || fail "historical inspection reports the final status"
pass "agent inspect reports historical registry records"

state_home="$test_tmp/state"
XDG_STATE_HOME="$state_home" "$ROOT/bin/omarchy-agent-state" start \
  "019state-1111-2222-3333-444444444444" \
  pi \
  pi \
  podman \
  omarchy-agent-pi-019state1111 \
  project123 \
  "/home/test/Project's files" \
  /workspace/project123 \
  localhost/omarchy-harness-pi:latest \
  running
XDG_STATE_HOME="$state_home" "$ROOT/bin/omarchy-agent-state" finish \
  "019state-1111-2222-3333-444444444444" stopped 0
state_record=$(XDG_STATE_HOME="$state_home" "$ROOT/bin/omarchy-agent-state" get 019state)
[[ $(jq -r '.[0].workspace_host' <<<"$state_record") == "/home/test/Project's files" ]] ||
  fail "agent state preserves paths with SQL punctuation"
[[ $(jq -r '.[0].status' <<<"$state_record") == "stopped" ]] || fail "agent state records lifecycle completion"
[[ $(stat -c '%a' "$state_home/omarchy/agents/control.db") == "600" ]] || fail "agent state protects its database permissions"
pass "agent state stores lifecycle records in a protected SQLite database"
