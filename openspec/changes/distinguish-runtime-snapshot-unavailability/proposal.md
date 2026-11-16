# Proposal

## Why

The legacy managed-runtime snapshot currently reports missing Podman or failed engine readiness as a successful empty inventory; failed enumeration can also be lost through process substitution. Callers can therefore mistake an unavailable observation for permission to launch or delete workspace state, while informational commands report false zero counts.

## What Changes

- Distinguish an observed empty inventory from an unavailable snapshot. Preserve the successful JSON array contract; report query, response-validation or projection failure with a nonzero status, a fixed stage-specific diagnostic and no snapshot on stdout.
- Check readiness, enumeration and inspection independently. Reject malformed or incomplete inspection responses for the enumerated containers instead of publishing partial success. Keep explicit local-engine routing and add no automatic retry, stale result or remote fallback.
- Include the separately approved locality correction discovered during native validation: keep `--remote=false` and remove only `CONTAINER_HOST` and `CONTAINER_CONNECTION` from local Podman child environments in snapshot, audit, task stop and the workspace manager. The option alone did not neutralize named-connection selection. Preserve the parent environment, global engine configuration and intentional workspace Remote SSH.
- Make safety-sensitive callers refuse unavailable observation before their dependent launch, stop, deletion or registry-finalization action. `--force` is not permission to assume inactivity. In task archive, stop on a failed nested cleanup instead of ignoring it and marking the task archived; already completed earlier cleanup is not rolled back.
- Keep configured `agent list` usable when runtime observation is unavailable: retain definitions/mode information, use JSON `running_instances: null` with `runtime_available: false`, and display `unknown` in text. Valid observed counts remain numeric with `runtime_available: true`.
- Runtime-dependent `agent ps`, `agent inspect` and `task status` report unavailability with a nonzero status and diagnostic, rather than a successful empty report, zero count or historical fallback presented as inactivity. Successful report shapes stay unchanged.
- **BREAKING:** unavailable engine observation no longer succeeds as `[]`/zero; configured-list running counts can be null and gain an availability field; archive no longer ignores nested cleanup failures, including with `--force`.

This is a bounded observation/failure-contract repair, not an atomic admission lease, hostile-code containment boundary or lifecycle-controller rewrite. It reduces implicit coupling between query failures and caller control flow without changing shared desktop code or adding a generic backend framework.

## Capabilities

### New Capabilities

- `managed-runtime-availability`: Explicit empty-versus-unavailable snapshot semantics, safe caller refusal and truthful configured-agent runtime reporting.

### Modified Capabilities

None in main specs: `openspec/specs/` currently has no capabilities. The earlier [local-engine change](../pin-managed-workflows-local-engine/proposal.md) intentionally preserved the empty-success behavior for its routing-only scope. This new change replaces that exception prospectively while preserving explicit locality; it does not rewrite or renew the historical routing evidence.

## Impact

The source base is `65c3a23eb0fb1cbd2d88d5a51470a8f23202bc4d`. The initial availability repair changed `bin/omarchy-agent-runtime-snapshot`, `bin/omarchy-agent-list` and `bin/omarchy-task-archive`; focused checks exercised the other eight direct callers without requiring failure-propagation edits. The subsequent approved routing correction also changes `bin/omarchy-agent-audit`, `bin/omarchy-task-stop` and `default/workspaces/manager.py`, with the producer shared by both scopes. Audit and task stop retain their existing failure/target policies; their additional edits only select the local child environment. Six runtime files therefore belong to the combined reviewed candidate, not three. New unrelated caller-policy or workspace-feature changes remain out of scope.

Implement in a separate, non-dev-linked worktree. The current development session resolves Omarchy commands from this fork checkout; editing its runtime files can affect the next invocation without a reboot. Integration into that checkout is activation and must wait for review and separate approval.

Extend `test/shell.d/agent-inventory-test.sh` and `test/shell.d/task-workspace-test.sh`, using the existing fake engine and scratch registry/workspace fixtures. The approved routing follow-up also extends `test/shell.d/fixtures/workspaces/test_manager.py` and uses the existing workspace suite. Its workspace evidence is focused fixture/subprocess coverage, not new native workspace qualification. Require focused regressions and negative controls, targeted integration checks with real rootless Podman in a disposable local VM, and a pull request (PR) with the existing continuous integration (CI) workflow running `./test/all` in a fresh Omarchy VM. Fake-engine tests inside CI are not native Podman qualification; record the targeted native checks separately. Retain original failures, skips, tested revisions and cleanup outcomes. These validation gates are required for this change but are not authorized by the plan.

Update managed-agent and boundary references, relevant end-user command documentation and the work ledger after approved implementation. Use the existing testing/VM/CI routes, subject to their resource and cleanup review; do not resume the paused VM/bootstrap campaign. No new command group, shipped image, package, migration, persistent state schema, UI feature, workspace feature, dependency or generic validation framework is proposed. The workspace-manager edit is limited to the approved local-child routing correction. No fresh ISO build or graphical acceptance campaign is required for this CLI-only change.

At proposal creation, approval covered planning/documentation only. Subsequent separate approvals covered inactive implementation, focused fixtures/negative controls, the routing correction and bounded guest-only native validation. Attempt 06 passed N1–N6 on the current staged runtime content under the explicitly reviewed reclaim-aware resource policy, with configuration restoration and owned cleanup confirmed. Earlier failed attempts remain preserved; see [outcome.md](outcome.md) for identities, mixed fault-injection scope and limits. Required PR/CI remains unperformed, so task 3.1 stays incomplete. Commit/publication, integration/activation, archive and any further runtime invocation require separate approval. Same-user authority, label trust, incomplete visibility, observation/action races and absence of producer deadlines remain limitations; no provider, graphical, hardware, native workspace-manager or release qualification follows.
