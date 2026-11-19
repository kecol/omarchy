# Design

Historical routing-only checkpoint: this document records the original options-only implementation and its planning or verification scope. Baseline behavior, preservation instructions, status and approval statements refer to that checkpoint, not current delivery. The [current contract reconciliation](design.md#current-contract-reconciliation) identifies the later safeguards that must remain in effect. The original [outcome](outcome.md) remains historical evidence, not renewed qualification.

## Context

See [proposal.md](proposal.md) for motivation and [managed-engine-selection](specs/managed-engine-selection/spec.md) for the proposed routing contract. This security-relevant change spans four owners, so it needs an explicit design despite the small argument edits.

The inspected snapshot/audit/task-stop chain uses a local task registry but bare Podman for enumeration and stop. The workspace backend similarly combines local registry/project/key paths and a `127.0.0.1` SSH endpoint with bare Podman. Its `list_workspaces` request calls `subprocess.run` directly, bypassing the generic `run` helper used elsewhere. Rootless checks do not prove engine locality. Existing harness and identity-aware controllers already demonstrate explicit `--remote=false` selection.

## Goals / Non-Goals

**Goals:** close the routing inconsistency at every scoped subprocess boundary; keep queries and actions on the same local engine; retain each caller's transport and failure policy. Reduce dependence on ambient engine selection without adding another shared/upstream-facing abstraction.

**Non-Goals:** a global environment sanitizer, engine broker, hostile-code socket/network denial, snapshot error-policy repair, stronger target identity or atomic admission. Do not alter generic user Podman behavior, account transfer, OpenShell/local-model adapters, image recipes, UI or workspace Remote SSH behavior.

## Decisions

### Explicit option at existing call sites

Add `--remote=false` immediately after `podman` at every invocation in the four scoped runtime files. Use explicit argv in Python and explicit global options in Bash. Keep the generic Python `run` function unchanged. This makes the existing direct listing subprocess subject to the same rule without changing its timeout, capture or exception handling.

A shared wrapper/helper is unnecessary for this bounded patch. Changing the generic runner would add implicit behavior to Git/SSH/editor dispatch and could miss callers that bypass it. Editing global engine defaults would affect unrelated commands and violate the boundary. Removing a subset of environment variables alone would not cover configuration-selected remote defaults. Do not add broad environment removal as part of this fix; explicit routing is the selected mechanism, not a claim that all local engine configuration is sanitized.

### Scope and preserved policies

| Owner | Requests to pin | Preserve |
| --- | --- | --- |
| `bin/omarchy-agent-runtime-snapshot` | `info`, `ps`, `inspect` | Managed-label filtering and JSON projection; existing unavailable-engine empty-success behavior; existing process-substitution and error handling. |
| `bin/omarchy-agent-audit` | Stop requests made by `--fix`; queries remain owned by the snapshot producer | Label/selected-field comparisons, advisory OpenShell status, container-name targets, engine-default stop grace, registry updates and exit codes. Do not run the real advisory doctor in routing fixtures. |
| `bin/omarchy-task-stop` | Each stop after its snapshot lookup | Assignment/runtime selection, multiple-instance behavior, name-based targets, engine-default grace and stopping/stopped transitions. Do not replace this with the newer exact-ID controller. |
| `default/workspaces/manager.py` | All Podman requests: listing, `info`, inspection/existence, image/volume, explicit build, start/run, port/key discovery and ordinary/failed-audit stop | Current UID/GID/rootless/cgroup checks, five-second listing timeout and unknown-state reporting, image pinning, explicit build requirement, mount/resource audit, loopback SSH/key pins, ten-second stop grace and retained storage. |

No new CLI flag is introduced. A caller that previously depended on an ambient remote engine will now operate locally or receive the existing local failure/outcome. This is an intentional compatibility change, not a pure refactor. Document it in the managed-agent/workspace references and E1/O2/L5/C3 inventory follow-up without rewriting historical observations as newly qualified behavior. Direct user Podman commands and intentional editor Remote SSH remain outside scope.

### Focused verification by transport mechanism

Extend the existing `agent-inventory-test.sh`, `task-workspace-test.sh` and `fixtures/workspaces/test_manager.py`; run them through `agent-inventory-test.sh`, `task-workspace-test.sh` and `workspace-test.sh` only after execution approval. These suites use scratch state and fake engine/UI/launcher answers; selected Git/SQLite/key setup is real and temporary. No live Podman, agent, provider, editor or doctor operation belongs to these checks.

The regression to catch is a production request losing explicit locality when remote defaults are present. Put a fake Podman executable first in a scratch PATH, supply synthetic `CONTAINER_HOST` and `CONTAINER_CONNECTION` defaults/configuration, and observe the argv emitted by actual caller code. Keep remote endpoints inert and never contact them. The fake executable records requests and rejects requests without the explicit local option before returning minimal synthetic engine responses. That tests Omarchy's request construction, not Podman's real configuration-precedence implementation.

- The inventory fixture currently substitutes the snapshot producer. Add coverage that invokes the actual snapshot script against the fake engine, exercising nonempty `info`/`ps`/`inspect` transport. Require observed output and requests so a swallowed fake-engine refusal cannot appear as a pass. Cover audit-fix stop separately while replacing its advisory doctor and registry/action dependencies with inert fixtures.
- The task fixture already calls real task-stop against a synthetic snapshot. Keep its real scratch registry lifecycle assertions and require the stop argv to select local explicitly. Test the snapshot producer in the inventory fixture rather than duplicating it here.
- Existing workspace policy/start tests often mock `run` or `output`; those alone cannot demonstrate the changed subprocess boundary. Add coverage through actual production transport with the fake executable, including the direct listing path, representative readiness/inspection/start/build/key requests and both stop paths. Stub only surrounding engine data/SSH/editor/wait answers needed to avoid external activity. Keep existing policy and state tests; adapt their argv expectations without turning them into the sole regression.
- Assert existing failures/empty or unknown results and stop/state policies remain scoped as above. Do not mistake empty output, a missing fake command or an expected test skip for routing success.

Demonstrate sensitivity in disposable source copies: remove explicit locality from a covered snapshot query, a legacy stop and the direct workspace listing request, and show the corresponding assertions fail for missing local selection. Preserve failures and rerun only after a covered change. Do not use source greps, fixed invocation counts or a stub's own remote-routing implementation as proof of enforcement.

Keep complete separate logs under `$HOME/Work/` and use the existing bounded test resource policy with preinstalled dependencies. Do not install tools, increase failed timeouts or start a broad/native validation campaign to obtain a green result. Report absent prerequisites, skips and failures distinctly. Native Podman precedence and enforcement remain explicitly unqualified by the fake-executable tests.

## Risks / Trade-offs

- Previously remote-configured users observe different results → document the intended local-only behavior for these host-local workflows; add no hidden remote compatibility fallback.
- A query is pinned but an action or listing is missed → cover actual subprocess requests across all four owners, including direct listing and failed-audit cleanup, and use targeted omission controls.
- Snapshot failure still looks like no active agents → retain the documented limitation and avoid any new fail-closed/admission guarantee; repair it in a separate behavior change.
- Name-based stops and same-user engine authority remain → preserve their limitations rather than presenting local routing as immutable-target validation or socket denial.
- Synthetic tests overstate engine semantics → qualify request construction only; live engine/configuration, graphics, credentials, CI and release qualification require separate evidence and approval.

## Migration Plan

No state migration, user configuration edit, image rebuild, connection conversion, live stop or activation is required to implement the source change. Deliver the four runtime edits coherently so observation and action do not temporarily use different routing policies. Update only the three existing fixture areas and relevant references/tracking after approved implementation.

Rollback restores those four owners and their associated tests/documentation from the same pre-change revision, without resetting unrelated edits or changing workspace directories, volumes, keys, registry records, mode/defaults or user connection configuration. Rollback also restores the old ambient-routing weakness and must be reviewed as such. Do not move remotely created resources to the host or guess a recovery target. Publication, deployment and archival remain separately gated.

## Current contract reconciliation

Current scoped Podman requests retain `--remote=false` and exclude `CONTAINER_HOST` and `CONTAINER_CONNECTION` from their child environments. Parent/global defaults and generic Git/SSH/editor subprocess environments remain unchanged. This is not a complete engine-configuration sanitizer or engine-access denial.

The [runtime-availability contract](../../specs/managed-runtime-availability/spec.md) supersedes the historical snapshot empty-success limitation. Unavailable required observation produces nonzero failure, a diagnostic and no snapshot stdout; dependent safety-sensitive actions refuse.

The [stop-target-binding contract](../../specs/managed-stop-target-binding/spec.md) supersedes historical task/audit name targeting. Preserve full observed container IDs, complete-plan validation, ambiguity refusal, no name fallback and failure-aware finalization. This does not extend task/audit targeting requirements to workspace stops or change either controller’s existing stop grace/escalation policy.

These safeguards were delivered by later changes, not the original routing patch. Their evidence remains separate from the original fixture results. This reconciliation runs no application tests and renews no native or graphical qualification.

The historical rollback paragraph is not a current rollback recipe. Restoring pre-routing owners could also remove later safeguards. Any rollback requires separate review and approval. Specification synchronization, archive, publication and runtime actions remain separately gated.
