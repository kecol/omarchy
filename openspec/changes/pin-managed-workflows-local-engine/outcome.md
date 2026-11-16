# Local-engine routing outcome

## Implemented source

After reviewing the planning artifacts, the user requested apply, covering the four runtime owners and the three scoped fixture suites. The implementation adds explicit local Podman selection to the existing calls in `omarchy-agent-runtime-snapshot`, `omarchy-agent-audit`, `omarchy-task-stop` and `default/workspaces/manager.py`. The inspected base is `0603b244ea2c67702d1cac1a0a5e6ce7e6f258c7`; the user subsequently accepted source review and separately authorized an atomic source commit. No activation is authorized.

The production diff adds only `--remote=false` immediately after Podman. It includes direct workspace listing, ordinary stop and failed-audit stop. The generic Python runner, subprocess transport, timeouts, command metadata, target arguments, stop grace, state transitions, image/mount/resource checks, SSH settings and storage behavior remain unchanged. No shared helper, package, image recipe, migration or new public interface was added.

This intentionally changes behavior for callers relying on ambient remote-engine defaults. These host-local Omarchy workflows select local instead; they do not rewrite the user's engine configuration or add a remote retry. Direct user Podman commands and the workspace editor's intentional loopback Remote SSH connection remain outside this change. The [spec](specs/managed-engine-selection/spec.md) records the narrow routing contract; it is not a whole-runtime safety specification.

## Focused evidence

| Check | Result and scope |
| --- | --- |
| `bash test/shell.d/agent-inventory-test.sh` | Passed once, exit 0, no skips. Actual snapshot producer performs info/enumeration/inspection against an inert executable under synthetic remote defaults and produces a nonempty projected record. Existing unavailable-engine empty-success behavior remains. Audit uses an unchanged source copy with an adjacent inert advisory doctor; its actual stop argv and existing state/report handling are checked without running the real doctor. |
| `bash test/shell.d/task-workspace-test.sh` | Passed once, exit 0, no skips. Actual task commands use temporary Git/SQLite/workspace state with fake agent/mode/doctor/audit/engine dependencies. The stop request explicitly selects local while retaining its target and state transition assertions. Its existing isolation-oriented success labels do not prove host-wide confinement. |
| `bash test/shell.d/workspace-test.sh` | Passed once: 23 Python methods, no skips, plus runner/help checks. The new transport case uses the actual workspace manager and subprocess transport with fake Podman/SSH under synthetic remote defaults. It covers listing, readiness, explicit build, new/existing container start, image/volume operations, key discovery, ordinary stop and failed-audit stop, as well as local query failures. Existing policy/editor/clone cases remain separately mocked or scratch-filesystem checks as documented. |
| Snapshot-query omission | In a disposable source copy, removing local selection from the info request caused the real snapshot to return empty and its nonempty-result assertion to fail. Exit 1 was expected; an empty result cannot hide the missing routing option. |
| Audit-stop omission | In a disposable source copy, removing local selection from the audit stop caused the fake executable to reject the actual request. Exit 1 and the missing-local-selection diagnostic were expected. |
| Workspace-list omission | Only the new transport method ran against a disposable source copy with local selection removed from the direct listing request. The runtime-availability assertion failed with exit 1 as expected. |

Each positive suite ran once. No failure required a corrective rerun, and no positive suite was repeated to redisplay output. The workspace suite's Git error in its deliberately failed-clone case is expected and its test passed; it is not an unexplained suite failure. All three omission failures are intentional negative controls, not delivered-source defects.

Runs used preinstalled dependencies as UID/GID 1000 with scratch homes/state, disabled global Git configuration, and transient user units configured with nice 10, memory 2 GiB, swap 512 MiB, CPU 200%, tasks 512 and runtime 150 seconds. Each suite/negative child had a 45-second limit with a two-second termination grace. Non-graphical admission checked at least 4 GiB available memory. Measured positive unit peaks were 13.6 MiB for the two legacy suites together and 24.3 MiB for the workspace suite; no swap was reported. These are test-run bounds, not new production enforcement.

The fake engine checks the actual argv before supplying synthetic replies; it does not implement Podman's real remote-configuration precedence. Fake SSH only supplies readiness, not a server or authentication transaction. Synthetic remote endpoints were never contacted. Temporary Git clones, SQLite records and generated test keys are not private user accounts or real session evidence.

Portable receipts are under `$HOME/Work/omarchy-local-engine-apply-01/`: positive suite logs, worker logs, `test-status.txt`, omission logs/scripts, source diff, tested-source hashes and final structural/protected-file checks. Raw temporary paths and test state stay outside Git.

## Final source and document checks

Removing only the added local-routing options reproduces the pre-change bytes of all four runtime owners. Static review confirms the direct workspace listing path is included and the generic runner is unchanged. The tracked-file scope is limited to those owners, the three existing fixture areas, relevant references and the work ledger. Protected harness Containerfiles and the published migration checked for preservation retain their hashes. Relative document links, portable paths and whitespace checks passed; strict OpenSpec validation reported three changes passed and none failed. These are structural/source checks, not another application test run.

## Remaining limits and exclusions

The legacy snapshot still returns successful empty JSON when Podman is unavailable, and its existing process-substitution failure handling is unchanged. Locality does not supply fail-closed admission. Audit still compares selected labels/fields rather than all effective enforcement settings. Legacy stops still use names with their existing grace behavior, not newer immutable-ID/identity/confirmation controllers. Same-user host authority, local engine configuration, socket/network reachability, credentials and provider-side session sharing remain separate trust dependencies.

No live Podman, agent, doctor, OpenShell/provider, SSH server, editor, GUI or VM operation ran. During implementation and fixture verification, no image build, installation, migration, global engine/configuration edit, activation, commit, push or archive occurred. Subsequent commit approval covers the reviewed source, fixtures and related documentation/tracking only; it does not authorize a push, image rebuild, activation or archive. Full-suite/CI, actual Podman precedence, native container enforcement, graphical interaction, hardware and release qualification remain unperformed. Older integration/VM/tracer work stays paused.

## Rollback

Restore the four runtime owners and their associated fixture/documentation changes from the same pre-change revision. Preserve unrelated edits and all user workspace directories, volumes, keys, settings and registry state. Restoring only a query or only an action can reintroduce mixed routing; deliver and roll back the scoped owners coherently. Rollback restores the old ambient-routing weakness and needs review. No automatic remote-resource discovery, migration or deletion is part of recovery.
