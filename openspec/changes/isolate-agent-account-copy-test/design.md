# Design

## Context

See [proposal.md](proposal.md) for the failure, baseline evidence and limits. This design is needed because the fixture crosses process-namespace and credential-state boundaries even though production code will not change.

`test/shell` places `agent-account-copy-test.sh` in its parallel pool. `base-test.sh` supplies root discovery, failure helpers and environment cleanup, but does not isolate `/proc`. The account-copy test exercises real `home_in_use()` logic, including named synthetic processes, unknown-home refusal, interrupted replacements and mock SSH receivers. Production transfer reads process environments, command names and arguments separately; this design does not change that scanner or establish the historical CI candidate.

Bubblewrap is already in `install/omarchy-base.packages`. The existing `chromium-claude-test.sh` uses Bubblewrap, but its whole-root mount and success skip when unavailable do not satisfy this fixture's proposed boundary. The successful private baseline used a smaller read-only system/source view and a cleared environment. Reuse that approach, not the baseline's private execution scripts as a new repository framework.

## Goals / Non-Goals

**Goals:**

- Give every existing account-copy assertion the same controlled process inventory under direct execution and the unchanged aggregate runner.
- Keep isolation enforcement in the existing fixture, with no shared-runner exception, new runtime command or generic test service.
- Fail before account operations when the boundary is unavailable; preserve original test exit status and owned cleanup.

**Non-Goals:**

- No change to account-home attribution, process-lifecycle policy, credential copying, rollback logic or production diagnostics.
- No historical CI root-cause claim, universal containment claim or protection against someone who can rewrite the fixture itself.
- No image provisioning, dependency installation, whole-suite retry, provider launch or new persistent state.

## Decisions

### 1. Re-enter the same existing test inside Bubblewrap

Add a bounded outer entry before `test_tmp` creation or any account operation. Continue sourcing `base-test.sh` for canonical root discovery and existing helpers. The outer entry invokes Bubblewrap once and replaces itself with that invocation; the inner entry runs the complete existing test body. Keep the Python tests and mock-SSH cases unchanged except for the entry boundary. Do not create another `*-test.sh` or duplicate the test body.

Use a fixed allowlist of five read-only source files under `/src`: `test/shell.d/agent-account-copy-test.sh`, `test/shell.d/base-test.sh`, `bin/omarchy-agent-account-copy`, `bin/omarchy-agent-account-transfer` and `bin/omarchy-agent-account-state`. These are the files used by the successful baseline. Mount the system executables/libraries read-only and only the required loader cache from `/etc`; do not bind the entire host root or project. Use private `/tmp` and scratch HOME, no host-backed writable account paths, and no host session sockets. Clear the environment and set only the fixture's synthetic HOME, fixed PATH, temporary directory, English locale and bytecode suppression, plus narrowly scoped bootstrap observations.

The inner `base-test.sh` must discover `/src` and point `OMARCHY_PATH` there, so child commands use the selected checkout's allowlisted source rather than the active host installation. Preserve the fixture's own synthetic HOME/state transitions and command stubs. The real production scanner must see synthetic processes created inside this namespace.

Alternative: add `# omarchy:exclusive`. Rejected as the selected correction because serialization is not process isolation and cannot exclude surviving or unrelated session processes. Mocking the scanner globally is also rejected because it would remove behavior the existing fixture tests.

### 2. Verify the kernel boundary before running the body

Use private PID, mount and network namespaces with a new `/proc`, dropped capabilities and parent-death cleanup. Capture outer namespace observations before launch and compare them with the inner kernel namespace identities. Verify that `/proc/1` belongs to the inner PID namespace and that required source bindings are read-only. Perform these checks before loading the account backend, scanning processes or writing synthetic credentials.

A re-entry marker only selects the inner verification path. A marker without valid boundary observations, or observations equal to the current namespace, must fail before the body. Do not accept the marker alone, silently recurse again or treat a preexisting surrounding sandbox as proof that this invocation created its required separation. These checks guard fixture setup and accidental unwrapped entry; they are not a new production authorization boundary.

Alternative: clear HOME without replacing process inventory. Rejected because the detector still reads surrounding processes and the synthetic provider-like processes can affect other fixtures.

### 3. Treat isolation as a required fixture prerequisite

Use `require_command` for the test prerequisites. Missing Bubblewrap, namespace denial or failed inner verification must return nonzero with a specific diagnostic. No success skip, provider-policy weakening, sudo, installation or unisolated fallback is permitted. Leave `test/shell`, `test/all`, `test/ci-vm` and `.github/workflows/test.yml` unchanged; their existing nonzero-status handling reports the failure in both direct and CI runs.

Bound the invocation with the installed Coreutils timeout mechanism: 45 seconds plus at most three seconds of termination grace. Preserve timeout and child failure statuses; do not retry or transform them into success. Use Bubblewrap parent-death behavior and private PID-namespace teardown to contain owned test children when the deadline fires. Preserve the existing test's terminate/wait and scratch cleanup. Do not kill processes by provider name or alter another test's processes.

A missing package in the actual CI image is a failed prerequisite to report, not authority to edit package lists or provision the image. Local baseline success establishes neither CI admission nor all-platform compatibility.

### 4. Verify isolated entry and fail-closed paths without an ambiguous host-visible process

The approved execution scope contains three checks inside a disposable outer private PID/network environment: one complete invocation of the unchanged candidate fixture body, marker-only inner entry without valid separation evidence, and an actual Bubblewrap namespace-setup failure using a disposable source copy. The two failure controls must stop before the account-test body. For the setup-failure copy, add `--pidns 0` while standard input is `/dev/null`, so the real namespace setup receives an invalid namespace descriptor; do not replace Bubblewrap or the account scanner with a stub. Stop the sequence at the first unexpected result. Do not retry or run the complete fixture again to obtain output.

Warning: a private PID namespace excludes ancestor processes from its own `/proc`, but does not hide its children from the ancestor host's `/proc`. Do not create a live provider-like process with missing, empty or relative HOME on the working desktop. The originally planned HOME-less neighbor and unchanged-parent comparison are explicitly DEFERRED and unperformed, not passed, skipped as success or replaced by these three checks. This historical-process investigation is not a delivery prerequisite for the narrow fixture change. Keep it outside tracked delivery progress; any future execution requires a separately reviewed environment that prevents interference with host account operations. Do not start a VM, provision another user or weaken the production guard to resolve this gap automatically.

The revised checks qualify only candidate entry, the existing fixture behavior and the two named failure paths. They do not reproduce the historical CI interference mechanism, prove timeout cleanup or identify the historical candidate process. Use disposable copies only for omission/failure controls. Retain complete output, original exit statuses, source bindings, namespace observations and owned-child cleanup; never capture raw environments, credentials or unrelated process inventory.

Keep the verification envelope at no more than the baseline's 512 MiB memory, zero swap, 64 tasks and 100% CPU. Each admitted invocation has the same 45-second ceiling, including any outer validation controller, so setup and cleanup must leave sufficient time inside that ceiling. High/OOM/kill/task-limit events fail the attempt; retain max-only counters separately. If prerequisites or time limits prevent completion, stop and retain the failure without increasing limits or retrying automatically. This is a named focused check, not a new reusable execution system.

## Risks / Trade-offs

- [User namespaces denied or Bubblewrap absent] Fail the test clearly. CI cannot claim coverage through a success skip; dependency or policy changes require a separate decision.
- [Isolation hides the processes the test needs] Keep the complete test body and its real named-process/refusal cases inside the new namespace; do not stub the scanner.
- [Source allowlist becomes incomplete after a future test edit] Missing source must fail rather than resolve a host checkout or installed backend. Maintain the allowlist beside this single fixture.
- [Deadline expires on a slower platform] Report the original timeout. Do not silently increase ceilings or claim that the existing x86 baseline qualified another platform.
- [An isolated pass is mistaken for historical diagnosis] Keep CI run `44922393670` failed and the candidate identity unknown. Keep the ambiguous-neighbor/unchanged-parent comparison explicitly deferred and unperformed; isolated-entry and fail-closed checks are not mechanism evidence.

## Migration Plan

No user-data migration or runtime activation is required by the implementation. The one-file change is implemented in an inactive candidate; [outcome.md](outcome.md) records source review, unchanged production detector bindings and bounded evidence. Local native validation, commit, publication/new-head CI and any active-checkout integration require their separately scoped approvals.

Rollback restores only the fixture entry logic. It restores exposure to shared process inventory and does not repair or weaken production account handling. No account homes, sessions, images or settings are created for delivery or removed by rollback. Shell-feature synchronization/archive remains a separate change and approval.
