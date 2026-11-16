# Runtime availability implementation outcome

## Status and scope

IMPLEMENTED SOURCE IN AN INACTIVE CANDIDATE; FOCUSED CHECKS AND NAMED NATIVE N1–N6 PASSED. Native attempt 06 passed under the separately reviewed reclaim-aware resource policy, with guest provisioning/configuration restoration and owned cleanup confirmed. Required PR/CI remains NOT RUN, so task 3.1 stays incomplete. No commit, push, PR publication, integration, host installation, activation, new ISO/image build, reboot or archive occurred. The approved add-only prerequisite installation was confined to the disposable guest.

The candidate is `$HOME/Projects/omarchy-runtime-availability`, branch `fix/runtime-snapshot-unavailability`, based on `65c3a23eb0fb1cbd2d88d5a51470a8f23202bc4d`. It includes copies of the previously approved planning artifacts and OpenSpec process documentation; implementation exists only in this separate worktree. The original dev-linked checkout, its planning files and its command resolution remain unchanged. Updating that checkout later would be activation for subsequent invocations without a reboot.

The initial availability repair changed these three runtime owners:

- `bin/omarchy-agent-runtime-snapshot`: explicit status-2 unavailability, fixed stage diagnostics, no stdout on failure, checked enumeration/inspection membership and structure, and buffered projection. Raw engine streams pass through jq before Bash capture so NUL bytes cannot be silently removed first. Pipeline failure propagation retains an engine failure even when a parser produces output; detected unavailability is reported as status 2. Successful projection fields remain byte-for-byte the original jq filter after internal document selection; explicit local routing remains, with both ambient remote selectors removed only from Podman child environments by the approved follow-up.
- `bin/omarchy-agent-list`: catch only the explicit unavailability status, retain configured definitions/mode, report null/unknown running counts with false availability, and retain numeric counts with true availability after success. Other failures remain errors.
- `bin/omarchy-task-archive`: check every nested cleanup, preserve its nonzero status and force argument, and report incomplete archive without final archived-state update. Earlier completed cleanup is not rolled back.

The initial availability repair exercised the eight other direct callers through actual command entrypoints and required no failure-propagation edits. The later approved routing correction additionally changes `bin/omarchy-agent-audit`, `bin/omarchy-task-stop` and `default/workspaces/manager.py`, with the producer shared by both scopes. The combined candidate therefore has six runtime owners; six direct callers remain unchanged. Audit/task-stop target and failure policies are not redesigned. Task status retains its existing earlier reconciliation writes; runtime-report refusal does not establish that no earlier registry write occurred. Name-based legacy stops, label trust, query deadlines, same-user authority, incomplete visibility and observation/action races remain limitations.

## Executed checks

Evidence stays outside Git under `$HOME/Work/omarchy-runtime-availability-apply-01/`. The logs contain synthetic fixtures and private local paths; they are not public artifacts or native-runtime evidence.

| Check | Recorded result | Limits |
| --- | --- | --- |
| Inventory suite, first run | Passed, no skips. | Actual producer/list/ps/inspect/audit scripts, inert engine and adjacent advisory doctor, synthetic metadata and scratch state. |
| Task-workspace suite | Passed initially and after a covered exit-status assertion cleanup: 27 assertion groups, no skips. | Real temporary Git/SQLite/task commands; snapshot/audit/doctor/launcher/Podman substitutions. Includes all task caller refusals, later start recheck, ordinary/force nested failures, earlier partial cleanup and successful recovery. |
| Inventory suite after covered byte-transport correction | Passed: 12 assertion groups, no skips. | Adds NUL-byte cases for enumeration and inspection; malformed/partial/duplicate/substituted records, buffered projector failure and list/report/audit failure behavior remain covered. |
| False-empty negative control | Detected the semantic omission with test status 1; repeated on final producer content after the byte-transport correction. | Disposable copy restored readiness failure as successful `[]`; the availability assertion failed, not a prerequisite. |
| Ignored-enumeration negative control | Detected the semantic omission with test status 1; repeated on final producer content after the byte-transport correction. | Disposable copy ignored a failed enumeration and returned empty success. |
| Ignored-cleanup negative control | Detected the semantic omission with test status 1. | Disposable archive ignored nested failure and falsely finalized; actual nested-cleanup refusal assertion failed. Archive runtime content remained unchanged. A later task-fixture exit-status assertion cleanup was beyond the assertion where this control failed; that changed fixture was positively rerun. |
| Source review | Successful projection preserved; eight unchanged callers, protected Containerfiles and `migrations/1793512402.sh` unchanged. | Source/fixture evidence, not native engine compatibility or containment. |

The first positive run passed. A later source review identified Bash's raw NUL-byte capture behavior; the producer and inventory fixture were corrected, then only the affected inventory suite and producer omission controls were rerun. Original successful logs and initial source hashes remain beside final logs/hashes. The task suite was rerun after its nested exit-status assertion was changed to the repository's arithmetic conditional style. Archive runtime content stayed unchanged; its omission control was not replayed. The omission failed earlier in the fixture than the changed status assertion.

Each test worker ran as UID/GID 1000 with nice 10, memory maximum 2 GiB, swap maximum 512 MiB, CPU quota 200%, task maximum 512, worker runtime maximum 150 seconds and two-second stop grace. Each suite had a 45-second timeout and two-second termination grace. Available-memory admission required at least 4 GiB. Recorded worker peaks were at most 10.9M as reported by systemd, with no swap used. These are test execution bounds, not production sandbox guarantees or producer query deadlines.

Named receipts include `test-status.txt`, `agent-inventory.log`, `agent-inventory-final.log`, `task-workspace.log`, `task-workspace-final.log`, `negative-status.txt`, the three original omission logs and two final producer-control logs, worker logs/statuses, `tested-source.sha256`, final source hashes, `source-review.log` and active-checkout before/after receipts. Syntax, whitespace, document links, strict OpenSpec validation and final content checks are structural checks, not additional application-suite runs.

## Approved child-local routing follow-up

Native attempt 05 exposed a named-connection selector problem: direct `podman --remote=false` enumeration still selected a synthetic nonexistent `CONTAINER_CONNECTION` and exited 125 before the candidate's poisoned-default query. That query was not a candidate observation, and the independent memory-max events were not established as its cause.

After separate approval, local Podman children in snapshot/audit/task-stop remove only `CONTAINER_HOST` and `CONTAINER_CONNECTION`. The workspace manager passes a fresh filtered environment to all 14 Podman call sites, including direct listing. Parent environment, generic Git/SSH/editor execution, global engine configuration, explicit `--remote=false`, targets and existing error handling remain unchanged. No new workspace feature or native workspace workflow was added.

The affected existing fixtures reject either selector reaching the inert engine. One pre-correction negative pass failed semantically in inventory, task-workspace and workspace areas, with statuses 2/125/1. One corrected focused pass succeeded: inventory 12 assertion groups, task-workspace 27 groups and workspace 23 Python methods plus its existing CLI/configuration checks, without skips. These later receipts identify the corrected bytes; the initial availability receipts above remain historical. The follow-up used bounded offline units with 2 GiB memory, zero swap, 45 seconds per suite and a 150-second unit fallback. See `$HOME/Work/omarchy-local-routing-followup-01/REVIEW.md` and its manifests/logs. Workspace-manager coverage remains fixture/subprocess evidence, and actual audit-fix behavior is not newly native-qualified by N1–N6.

## Source review and native evidence

A subsequent read-only review found no blocking runtime-code issue in the three-owner diff and its focused evidence. Candidate content hashes still matched the implementation receipts at that review. This is not an independent audit or a new test pass. The evidence table above corrects an overstatement that the task fixture was unchanged after the archive omission control; its later assertion-style edit and positive rerun were already recorded in the original outcome narrative.

The earlier plan-only checkpoint proposed a 420-second unprovisioned run and retained missing-input/resource blockers. Subsequent separately scoped approvals covered bounded input acquisition/inspection, an exact guest-only prerequisite transaction, timing/cleanup reserves, manual host readiness, the routing correction and the resource-policy revision. The [executed native contract](design.md#executed-native-run-contract) records the approved procedure-08 invocation, not permission to reuse an earlier consumed approval or start another VM. It used the existing sibling sealed-image helper, a 4 GiB/two-vCPU guest and unchanged configured 5 GiB memory / 512 MiB swap / CPU 200% / 512-task / nice-10 controls. Active timing was limited to 600 seconds, including bounded cleanup, with provisioning/native phase limits and reserved evidence export. The passive manual READY wait started no guest and held no validation lock.

Published edge `2026.11.13.489` supplied the pinned matching disk/kernel/initrd/cmdline. The reviewed BusyBox archive supplied an inert local test image; starts used `--pull=never`. Input-only qualification relied on recorded publication bytes plus direct guest inspection and fresh exact replay, not independently signed publisher-build provenance. The final guest transaction installed seven absent packages, including Podman 6.2.0-1, with verified archives/signatures, unchanged indexes, trusted keyring policy and manual sudo/INSTALL consent. Final payload accounting was 31,838,329 bytes. Temporary transaction configuration was restored before native assertions. No host installation, refresh/full upgrade, fallback mirror, passwordless privilege or private host project was used.

### Retained earlier failures

| Attempt | Original outcome | Limit on interpretation |
| --- | --- | --- |
| Native 01 | Guest prerequisite Podman was missing. | No native cases passed. |
| Native 02 | The print-only resolver could not find Podman in the selected guest indexes. | Stopped before authentication/download/install; no database refresh was substituted. |
| Native 03 | Provisioning transport timed out, followed by an export attempt after its deadline; 65 memory-max events were independently recorded. | No exported guest/restoration summary exists; the destroyed overlay was not reconstructed. |
| Native 04 | Guest sudo validation timed out before installation. | Finalized failure/export retained; installer and N1–N6 were not invoked. |
| Native 05 | N1 passed; direct N2 reference enumeration failed with status 125 under synthetic named-connection defaults. Independently recorded 4,415 memory-max events failed its original resource contract. | Candidate poisoned-default query was not reached; N2 was incomplete and N3–N6 were not performed. No retrospective pass under the later policy. |

Original failures, consumed approvals, source bindings and cleanup receipts stay preserved in their corresponding `$HOME/Work/omarchy-runtime-availability-native-0*/` directories. Corrected offline preparation fixtures also retain their initial failures; their later passes are not guest execution or native qualification.

### Passing native attempt 06

A fresh single invocation of frozen procedure 08 passed N1–N6 on 2026-11-15:

- N1: real rootless empty inventory returns successful empty arrays and numeric configured zero counts.
- N2: real one/two-container enumeration/inspection agrees with snapshot, configured list and ps/inspect projections. Direct reference children are neutralized separately; candidate calls succeed while retaining both synthetic invalid remote defaults.
- N3: active assignment cleanup/archive refuse, including force, while preserving the specified workspace/container/finalization state.
- N4: owned task stop works under poisoned defaults; healthy inactive cleanup/archive completes and retains the required workspace/registry semantics.
- N5: controlled nested snapshot faults propagate archive failure, including force and earlier completed cleanup. Deliberate specified recovery succeeds after removing the fault. This is mixed native/fault-injection evidence, not a naturally occurring engine outage.
- N6: controlled guest readiness failure produces status 2, no stdout and the exact stage diagnostic. Configured counts become unknown; dependent reports/cleanup/archive refuse, including force. Specified recovery succeeds after removing injection.

The exported guest summary, source manifest and all numbered command outcomes agree with these results and record no timeout, output overflow or incomplete exit observation. Guest-owned container cleanup and restoration were confirmed. The helper was alive before owned teardown and exited with the expected status 130, with no reader errors or surviving reader. Post-stop observations confirm no other cgroup members, no VM state files and an empty overlay/state directory; the systemd unit was inactive with MainPID zero and no ControlGroup. Controller and visible-terminal exit statuses were zero.

### Reviewed resource semantics and identities

Policy `bounded-native-reclaim-aware-v1` retains raw counters, requires actual `memory.max = 5368709120` and `memory.swap.max = 536870912`, and separates observed boundary events from disqualifying events. The user explicitly selected this policy without raising those controls. Max-only events do not independently fail; memory high/OOM/OOM-kill/group-kill, task-limit events, invalid controls/counters, failed assertions, deadlines, evidence loss or unconfirmed cleanup still fail. This revises the earlier zero-max-event acceptance rule; it is not an unreported waiver.

Attempt 06 retained 5,070 max-boundary events and `limit_events: true`, with zero disqualifying events. Recorded peak was 5,369,364,480 bytes, 640 KiB above the configured setting; Linux permits temporary overshoot. Swap peak was 4,845,568 bytes. The verdict explicitly says the result is not pressure-free. No baseline/counter/peak was reset or subtracted; full buffered input hashing remained inside the owned unit. No cache manipulation, off-unit hashing, smaller guest, alternative driver/filesystem/kernel or automatic retry was used. Zero OOM events are not proof that every allocation succeeded; named command/assertion results were reviewed separately.

| Binding | Recorded identity |
| --- | --- |
| Base revision | `65c3a23eb0fb1cbd2d88d5a51470a8f23202bc4d` |
| Staged runtime manifest, 648 files and recorded modes | `ccecefe4d12745e21008b1fa7858d7d728b7935fd10c3f2ab2f27becf0832e11` |
| Procedure-08 program manifest | `58d3205509ffa0b3b2619a4797cce9f44ff6742019c369832eea537792258a15` |
| Procedure-08 contract | `3ac3559c904c218bf368fe03d5825758673b75e69bfcae7226f99b74f45ac758` |
| Native-06 retained evidence manifest | `623ead9839a7a33990ee6a3cbde6b07d8daa7be2935120c03b29bec647c0d525` |

Private evidence is under `$HOME/Work/omarchy-runtime-availability-native-06/REVIEW.md`, `RESULT.json`, original guest/provisioning archives and summaries, resource/control observations, approval/readiness/consumption copies and postflight receipts. Policy rationale is under `$HOME/Work/omarchy-runtime-availability-resource-policy-review-01/REVIEW.md`; frozen programs remain under `$HOME/Work/omarchy-runtime-availability-vm-procedure-08/`. These are portable local locators, not public artifact publication or independent third-party verification.

The native component now has passing evidence for the named staged integrations. Workspace manager remains focused-tested, not newly native-qualified; all ten callers' broad unavailable-control-flow coverage remains in fixtures. PR/CI evidence is still absent. Task 3.1 stays incomplete. Documentation reconciliation changes no runtime/test content and does not renew or expand the recorded qualification.

## Open integration gates

- Candidate source/evidence review found no blocking runtime issue; user acceptance and runtime integration permission remain separate.
- Review the combined availability/routing diff and the passing named native evidence under its exact source and policy bindings. The approved invocation is consumed; do not automatically repeat it. Native success does not replace required PR/CI or qualify unrelated workspace/provider/UI behavior.
- Obtain separate commit/publication approval, publish a candidate PR and review the existing CI workflow's `./test/all` result, failures/skips and exact tested revision/content. No PR or CI run exists for this candidate yet.
- Integrate only the reviewed/tested content into the active checkout after separate activation approval. Retain the known pre-change weaknesses in any rollback assessment. Do not resume the paused merge/VM/tracer campaign.

The source is ready for review, not yet qualified for active integration. No provider, graphical, hardware, full containment or release qualification is claimed.
