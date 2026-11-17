# Design

## Context

See [proposal.md](proposal.md) for motivation, reviewed baseline and exact source scope. The existing [availability contract](../../specs/managed-runtime-availability/spec.md) validates complete engine observations; it does not bind later actions to immutable targets. The proposed [target-binding contract](specs/managed-stop-target-binding/spec.md) owns that additional boundary.

The two Bash callers already receive `container_id`, container name and workflow labels. The producer checks engine IDs, but labels can be absent or repeated. The consumer must not substitute label identity or display names for the engine ID. Existing newer controllers use process/namespace fingerprints and separate confirmation policies; importing them would change behavior and expand this change beyond two CLI owners.

## Goals / Non-Goals

**Goals:** separate action identity from display metadata, validate complete target plans before lifecycle mutation, and preserve caller-specific behavior after execution starts.

**Non-goals:** authenticate labels against registry ownership, add process-incarnation checks or locks, perform another observation before every action, change audit policy tests or advisory doctor behavior, or consolidate the lifecycle controllers. Do not change the producer, registry schema or successful output field schemas.

## Decisions

### 1. Retain the observed full ID through execution

Each stop record retains the original row's full `container_id`; names remain display metadata. Validate the JSON type before extracting text and require exactly `[0-9a-f]{64}`. Reject nulls, numbers, short IDs, whitespace and option-shaped strings. Reject repeated IDs rather than silently deduplicating them.

Task stop validates all rows selected for the uniquely resolved assignment, including the existing Podman-runtime restriction. Audit `--fix` validates the captured snapshot's ID set before deriving a repair plan and checks that selected repair runtimes are Podman. Neither action path resolves a name after validation. The stop child retains `env -u CONTAINER_HOST -u CONTAINER_CONNECTION podman --remote=false stop` with only the validated ID as target.

Alternative rejected: looking up the name immediately before stopping. That introduces another mutable-name resolution and still leaves a lookup/action gap. Full IDs directly address this risk without another engine query or shared helper layer.

### 2. Bind audit failures to container IDs, not instance-label keys

Retain the existing policy checks and their displayed instance/name fields. Internally associate each failure with its observed container ID, then derive the repair plan only from those failed rows. Do not select repair rows by membership in an instance-label map.

For every failed row, require a nonempty string instance label that occurs on exactly one container in the full captured snapshot, including passing rows. If this association is absent or ambiguous, refuse the entire repair plan before any stop or dependent registry update. This prevents a failed row from selecting a healthy row and avoids finalizing a shared instance label while another associated container remains running. Multiple uniquely labelled failed instances can still share an assignment; that remains the existing assignment-level workflow, not a uniqueness error.

Alternative rejected: changing only the final stop argument to `container_id`. The instance-keyed selection bug would still select another row's ID. Alternative rejected: stopping the failed row but silently omitting its ambiguous registry update. That invents another partial-repair policy instead of visibly refusing ambiguous action/state association.

This is a consistency check within one snapshot, not proof that a label belongs to the caller or registry record. Do not infer a new trusted-controller boundary.

### 3. Validate first, retain partial-execution semantics

Construct and validate the complete applicable plan in checked control flow before task stop writes `stopping` or either caller submits a stop. Parsing or validation failures must reach the main command's nonzero exit path; do not hide them in an unchecked process substitution or skip invalid rows inside the action loop. For audit, refusal must not imply `ok: true` or successful repair. A fixed diagnostic on stderr and nonzero status is sufficient; no new error envelope is required. Display names must not affect target eligibility.

Once execution begins, preserve the differences between callers:

- Task stop retains the sequence `stopping`, selected ID stops, then `stopped` only after all requests succeed. Failure can leave earlier containers stopped and assignment status `stopping`.
- Audit retains per-target `stopped` or `stop-failed` reporting, nonzero exit when any stop fails, and existing continuation across independently validated targets. It issues dependent finalization only for a successful stop; existing best-effort registry writes remain best effort.
- Both retain engine-default stop behavior, including possible KILL escalation. Neither gains the overview's TERM-only policy, confirmation, retry, force, deletion or a fallback controller.

Alternative rejected: an all-or-nothing rollback promise. Stopping a container cannot be reversed by restoring a database value, and concurrent launches remain possible. Target disappearance after validation is an execution failure, not permission to retarget a replacement.

The pre-mutation guarantee concerns stop and dependent lifecycle writes, not all audit side effects. Audit still has an advisory quick doctor; tests must isolate it rather than treating audit execution as read-only.

### 4. Extend existing behavioral fixtures

Keep regressions in `test/shell.d/task-workspace-test.sh` and `test/shell.d/agent-inventory-test.sh`. Replace placeholder or absent IDs with synthetic full IDs. Retain unavailable-observation, local-child routing, output and successful lifecycle checks. Do not add a new test runner or generic engine simulator.

| Regression | Production breakage it must catch |
| --- | --- |
| Rename A and reassign its old name to B between snapshot and action | Actual caller stops B by name instead of the selected ID A. |
| Remove A and reuse its old name for B | Caller retargets B or reports/finalizes successful stop despite the selected ID's failure. |
| Invalid or repeated IDs, including an invalid later task row | Caller silently skips a target, starts an earlier action or writes lifecycle state before complete validation. |
| A passing row and a failed row share an instance label | Audit selects another row through its instance-label failure map or finalizes ambiguous state. |
| Distinct valid rows have different audit results | Repair scope broadens beyond the failed container. |
| A later ID stop fails after an earlier success | Caller falsely records final success or loses the existing partial-failure report. |

Use small stateful fake engine responses to model name-to-ID resolution and failure while executing the real production callers. Assert which synthetic object received the requested action and which registry writes occurred; do not only grep changed source or replace an expected argv literal. The fake supplies engine responses, not the target-selection guard under test. The inventory suite already copies audit beside an inert doctor; preserve that boundary.

After separately approved implementation and focused execution, use disposable copies for name-target and instance-key omission controls. Record semantic failures on the base or omission, exact tested content and complete logs. Do not rerun a successful suite merely to reproduce output.

### 5. Keep native and CI evidence separate

The required native scope is the same two callers operating on inert disposable guest containers: renamed-original/name-reuse selection, removed-original refusal, ordinary successful stops and failure reporting. Verify actual full IDs and the replacement container's state independently. For audit, declare any isolated advisory-doctor substitute explicitly; such a case qualifies real ID-bound stop behavior, not the real doctor. Label-collision and malformed-input fixtures remain synthetic unless a separately reviewed native procedure exercises them.

Before any native run, obtain separate approval for image/source identity, resource limits, transport, exact guest actions, evidence and owned cleanup under `docs/openspec.md`. No prior native allowance is reusable. Blocked native coverage stays open; fixtures or CI do not silently close it. Use the existing PR/CI route before active integration. This CLI-only change needs no graphical, provider, image-build or storage campaign.

## Risks / Trade-offs

- **Label authority and concurrent changes remain** → State that IDs prevent name retargeting, not hostile same-user actions, label forgery, restart-incarnation changes or concurrent assignment launches.
- **An invalid later target could follow an earlier side effect** → Validate the complete plan in checked main control flow before the first stop or dependent lifecycle write.
- **A repeated instance label could affect passing containers or registry state** → Check failed-row association against the full snapshot and refuse the entire ambiguous repair plan.
- **Strict validation breaks underspecified fixtures** → Use realistic synthetic full IDs; never restore name fallback to preserve an incomplete fixture.
- **Default stops can escalate and advisory audit can write** → Preserve and document those policies; do not describe these paths as TERM-only or read-only.
- **The active checkout is dev-linked** → Implement only after new approval in a non-dev-linked candidate; do not treat a missing restart or commit as an activation barrier.

## Migration Plan

No data migration, package change, user-config refresh or image rebuild is required. After separate implementation approval, keep the active dev link unchanged and prepare the candidate outside the active runtime source. Update only the two runtime owners, existing fixtures and current reference supplements. Preserve historical L5/Q3 descriptions and append current evidence rather than rewriting old qualification.

Before active integration, review focused and negative-control results, targeted native results and PR/CI for the exact candidate, or obtain review of a specific gate exception. Commit/publication, merge, activation and archive remain separate approvals. This plan authorizes none of those actions.

Rollback requires separately approved restoration of the reviewed parent versions of the two runtime owners and their compatible references/tests. It restores the known name-retargeting and label-association weaknesses; it does not undo stops, registry writes or other runtime effects. Do not broaden preexisting stricter file permissions during integration or rollback.
