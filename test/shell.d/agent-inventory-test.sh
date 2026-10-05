#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

test_tmp=$(mktemp -d)
trap 'rm -rf "$test_tmp"' EXIT

mock_bin="$test_tmp/bin"
test_home="$test_tmp/home"
snapshot_file="$test_tmp/snapshot.json"
mkdir -p "$mock_bin" "$test_home"

cat >"$mock_bin/omarchy-agent-mode" <<'SH'
#!/bin/bash
printf '%s\n' "${OMARCHY_TEST_AGENT_MODE:-container}"
SH

cat >"$mock_bin/omarchy-agent-runtime-snapshot" <<'SH'
#!/bin/bash
cat "$OMARCHY_TEST_SNAPSHOT"
SH

cat >"$mock_bin/omarchy-agent-state" <<'SH'
#!/bin/bash
[[ $1 == "get" ]] || exit 1
cat "$OMARCHY_TEST_HISTORY"
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
export OMARCHY_TEST_HISTORY="$history_file"
export PATH="$mock_bin:$ROOT/bin:/usr/bin"

list_json=$("$ROOT/bin/omarchy-agent-list" --json)
[[ $(jq -r '.[0].agent' <<<"$list_json") == "pi" ]] || fail "agent list includes the built-in Pi agent"
[[ $(jq -r '.[0].runtime' <<<"$list_json") == "podman" ]] || fail "agent list reports the effective container runtime"
[[ $(jq -r '.[0].running_instances' <<<"$list_json") == "1" ]] || fail "agent list counts active instances"
[[ $(jq -r '.[0].source' <<<"$list_json") == "builtin" ]] || fail "agent list identifies the built-in definition source"
pass "agent list reports configured agents and active instance counts"

host_list=$(OMARCHY_TEST_AGENT_MODE=host "$ROOT/bin/omarchy-agent-list" --json)
[[ $(jq -r '.[0].runtime' <<<"$host_list") == "host" ]] || fail "agent list reports host as the effective runtime"
[[ $(jq -r '.[0].configured_runtime' <<<"$host_list") == "podman" ]] || fail "agent list preserves the configured container runtime"
pass "agent list distinguishes effective and configured runtimes"

ps_json=$("$ROOT/bin/omarchy-agent-ps" --json)
[[ $(jq -r '.[0].instance' <<<"$ps_json") == "019abcde-1111-2222-3333-444444444444" ]] || fail "agent ps reports the active instance"
[[ $(jq -r '.[0].workspace' <<<"$ps_json") == "/workspace/project123" ]] || fail "agent ps reports the runtime workspace"
pass "agent ps reports observed active instances"

inspect_json=$("$ROOT/bin/omarchy-agent-inspect" 019abcde --json)
[[ $(jq -r '.record_source' <<<"$inspect_json") == "observed" ]] || fail "agent inspect prefers observed runtime state"
[[ $(jq -r '.filesystem_policy.host_root_mounted' <<<"$inspect_json") == "false" ]] || fail "agent inspect detects that host root is not mounted"
[[ $(jq -r '.credential_policy.readable_by_agent' <<<"$inspect_json") == "true" ]] || fail "agent inspect reports credential exposure"
[[ $(jq -r '.network_policy.egress_verified' <<<"$inspect_json") == "false" ]] || fail "agent inspect does not claim unverified network enforcement"
pass "agent inspect reports filesystem, credential, and network security state"

printf '[]\n' >"$snapshot_file"
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
