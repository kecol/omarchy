# Implementation outcome

## Status

IMPLEMENTED, PUBLISHED, MERGED AND SOURCE-ACTIVE at `db9ba29a434bd21f0d183ed7b972a0d96aabd63c`. Focused offline checks passed. The planned native and terminal-visual scope is verified across attempts 03, 04 and 05, with the limits below. Attempts 01–04 remain failed at their original verifier/setup errors; attempt 05 completed its remaining scope and its captures were inspected. Publication, CI, merge and activation results are recorded separately below, including the failed publication attempt, merge-preflight control error and failed activation permission postflight. The owner separately approved this documentation-only synchronization and archive. The [main shell specification](../../../specs/agent-container-shell/spec.md) preserves the delta's seven requirements and fourteen scenarios without changing runtime behavior. This local tracking closeout remains uncommitted and unpublished.

Implementation was prepared in the inactive candidate `$HOME/Projects/omarchy-agent-container-shell`, branch `feature/agent-container-shell`, based on `1f879a93f309b8742d83145b9a0321cdd2d9c76a`, then committed as `9eae668dd7aed58bc021370505ecd7b0f552a379`. The active checkout now tracks the reviewed change artifacts. Their seven original planning files remain preserved in a private backup. Pending `AGENTS.md` and `docs/project-goals.md` edits remain local and outside this delivery.

## Implemented behavior

- `bin/omarchy-agent-shell` exposes the optional-selector command and metadata-only `--check` through the existing CLI router.
- `default/agents/session-menu.py` adds shell-specific fresh target verification and fixed `/bin/bash -i` exec by full immutable container ID. It strips both Podman remote selectors from the exec child only, inherits terminal streams and restores its temporary SIGINT handler after the shell returns or execution raises an error.
- The existing sessions menu offers **Open shell** separately from attachment. The shell-only picker retains explicit selection, Exit/Refresh and Back defaults, with start time added to distinguishing metadata. Shell return causes no automatic close or retry.
- Documentation separates attach from exec and warns about shared files/home, container startup files, configured access and harness-owned lifetime. No image change or extension installation is included.

## Focused evidence

Logs are local under `/tmp/omarchy-agent-container-shell-checks/`; they are not durable CI artifacts or native runtime receipts.

- `core.log`: the initial core implementation passed all 25 session-menu unittest methods, including the original attachment/close tests.
- `integration.log`: after CLI/menu integration, all 34 session-menu unittest methods passed without skips. Controller execution uses mocked engine observations and subprocess boundaries. The command-help case runs the actual router in help-only mode.
- `bin-style.log`: both existing bin-style checks passed.
- `commands.json`: the actual CLI metadata listing contains one visible, non-sudo `omarchy agent shell` route with the expected arguments and binary.
- `syntax.log` and `whitespace.log`: Bash syntax and tracked-diff whitespace checks passed. Separate source review checked whitespace in all five implementation files, including the new untracked command.
- `base-negative.log`: the new help-route test was run once against the unchanged active base and failed because it resolved to parent agent help rather than `omarchy-agent-shell`. This is an expected negative control, not an unexplained application failure or a full base-suite run.
- `source-review.log`: abstract syntax comparison confirmed that `attach`, `verify_attach`, `close_selected` and `choose` are unchanged. Shared terminal-guard/error wording changes only make diagnostics action-neutral. `sessions.py`, `status.py` and `omarchy-agent-run-podman` match the base bytes.

During the implementation and offline-check stage, no native shell, provider, account, live inventory or graphical action occurred. Subsequent native attempts are recorded separately below. No full CLI/theme suite or aggregate shell suite was run locally. Later CI results are recorded in the delivery section below. The scope does not change shared desktop components or the test runners.

## Source binding

The following SHA-256 digests identify the checked implementation bytes. They do not identify an image or certify runtime compatibility.

| Path | SHA-256 |
| --- | --- |
| `bin/omarchy-agent-shell` | `a4b2bf50f40af62e787b2c8428e964b6449acfca5cbbb4088a2e1555d7fc40c9` |
| `default/agents/session-menu.py` | `1eb72009db7e19d9308f49951191ecfa6f3507a97bce1cebb5b75c4f98ee0d7a` |
| `docs/managed-agents.md` | `cfb4ee29a8b7daf81bd19769208fcd1f60582efa0255be38ee3b24dc8a7d53b3` |
| `manual/60-agent-session-menu.md` | `2b31509fd5e37cb411ca90eb4bc4303ab1581d4a7ec00e603c4084ad41175cfa` |
| `test/shell.d/fixtures/agent-session-menu-test.py` | `8bdf8e8b5361366cfc642b4455aa4aff4ee2e1fb99fe6e6766fc06131f0c8061` |

## Native verification attempt 01

After separate runtime approval, attempt 01 stopped during verification setup because `systemd-run` rejects the combination of `--wait` and `--remain-after-exit`. No fixture container or volume was created, no candidate shell or picker ran, and no native or visual case passed. The original attempt remains failed. The exact service is not found; its slice is inactive/dead. The owned-container and owned-volume inventories are empty.

Private evidence remains at `$HOME/Work/omarchy-agent-container-shell-native-01/`, including `RESULT.json`, `controller.log` and `units-after.log`. This was a verification-driver error, not a reproduced defect in the candidate. The attempt 02 setup was then prepared offline with `Type=oneshot` plus `--remain-after-exit`. It ran only after renewed approval, as recorded below. No automatic retry occurred.

## Native verification attempt 02

After renewed approval, corrected attempt 02 created two disposable rootless fixtures under the existing limits. Native metadata-only checks passed. Retained output from one real exec shell contains the complete success marker after a chained check of non-root UID, the synthetic home, the configured working directory and a project marker write. The adapter recorded exec against only the selected full container ID. This is partial native evidence, not completion of the shell scenarios.

The driver expected CRLF around the marker; actual terminal output used a different CR/LF sequence with Bash terminal-control escapes. The marker exists in the retained output, but the exact byte matcher timed out. The original attempt remains failed. Ctrl+C, Ctrl+D, nonzero exit, stale selection, unavailable-state injection, main-process exit and graphical cases did not run.

The controller reaped its owned client and removed both identity-matched fixture containers, both fresh home volumes and both synthetic project directories. Its original receipt retained no cleanup errors and an anchor manager result of success with exit status 0. Retained aggregate counters show a 13,312,000-byte memory peak, seven tasks at peak and zero memory-high, max, OOM, kill and task-limit events under 640 MiB aggregate memory and zero swap. The original receipt did not separately retain the terminated exec client's numeric exit code.

A follow-up found the exact verification slice still active but empty after the anchor stopped. After confirming `populated=0` and no member processes, identity-scoped cleanup stopped that slice and reverted only its unique runtime properties. The follow-up verified inactive state and an empty control-group path. Private evidence remains at `$HOME/Work/omarchy-agent-container-shell-native-02/`, including `RESULT.json`, `direct-shell.pty`, `PARSER-REVIEW.json`, retained counters and `SLICE-CLEANUP.json`.

The attempt 03 setup was then prepared offline with a CR/LF-tolerant complete-line matcher and explicit empty-slice cleanup. Offline replay verified the matcher correction. The later attempt ran only after renewed approval, without changing the five candidate implementation files.

## Native verification attempt 03

After renewed approval, attempt 03 passed native metadata checks and independent shell entry for a container whose init had no terminal or open stdin. Chained non-root UID, synthetic home, working-directory and selected-project marker checks passed. The other fixture did not receive the marker. Ctrl+C left the maintenance shell usable, a root write was refused, normal exit and Ctrl+D returned 0, and explicit `exit 17` propagated 17. The fixture main process remained running after shell exit.

The next fault-injection probe reported `metadata query failed`. The verifier required the exact word `unavailable`, which is not part of the specified error contract, and stopped with an assertion failure. The original attempt remains failed. Its original receipt did not separately retain that probe's return code and streams; only their combined diagnostic log survives. Do not mark the complete injected-failure case passed from that message alone. Stale-selection, main-process-exit and graphical cases did not run.

Both disposable containers, fresh home volumes and synthetic project directories were removed. The anchor reported success and exit status 0. The controller verified the exact slice empty, stopped it and reverted its unique runtime properties; the final slice state was inactive with no control-group path. Retained aggregate counters show an 11,608,064-byte memory peak, seven tasks at peak and zero high, max, OOM, kill or task-limit events. Private evidence is at `$HOME/Work/omarchy-agent-container-shell-native-03/`, including `RESULT.json`, the three synthetic PTY records, `unavailable.log` and retained counters.

The attempt 04 setup was then prepared offline for remaining cases only: fault-injected metadata refusal with explicit return-code/stream receipts, held-selection replacement refusal, graphical picker/shell/return behavior and main-process exit. It ran only after renewed approval and did not repeat completed core native cases. The candidate implementation remained unchanged.

## Native verification attempt 04

After renewed approval, the remaining-only run passed controlled metadata-query failure: exit status 1, empty stdout and diagnostic `metadata query failed`. This is native subprocess transport with an explicitly fault-injected metadata failure, not a real engine outage. A held picker selection then refused after two owned containers were renamed so that a different full ID held the selected name. The controller returned to the list without executing a shell in the replacement. The corresponding PTY client exited 0.

The temporary Foot window opened, but the verifier's `hyprctl dispatch setfloating` request failed before screenshots or graphical shell interaction. This is a verification-driver window-placement failure, not a confirmed candidate defect. The original attempt remains failed. Main-process-exit verification did not run.

The original controller waited for its owned terminal processes, removed both containers and both fresh volumes/project directories, and stopped/reverted its empty verification slice. The anchor result was success with exit status 0; final slice state was inactive with no control-group path. Retained aggregate counters show a 9,375,744-byte memory peak, seven tasks at peak and zero high, max, OOM, kill or task-limit events. Private evidence is under `$HOME/Work/omarchy-agent-container-shell-native-04/`, including `RESULT.json`, `stale-picker.pty`, `foot.log` and retained counters.

The attempt 05 setup was then prepared offline for graphical terminal inspection and main-process exit only. It used Foot's own fullscreen request instead of compositor dispatch operations, retained PID/class checks before synthetic keyboard input and window-only captures, and did not repeat passed core, unavailable-state or replacement cases. It ran only after renewed approval; the candidate source remained unchanged.

## Native and terminal-visual verification attempt 05

After renewed approval, the last-two-case run completed without a controller error. Foot used its own fullscreen request, with no compositor dispatch operations. The reviewer inspected all four synthetic captures: the two-instance picker with Exit selected, the selected-instance details with Back selected, the independent container shell and marker output, and return to that same selected-instance menu after shell exit. At the tested fullscreen size, picker/action/return content was readable without clipping or overlap. The shell capture includes an early automated-input echo/redraw artifact during startup; it is retained explicitly, not presented as a clean startup-paint proof or a confirmed candidate defect. No rerun was performed to obtain a cleaner capture.

The finite fixture main process then exited while an independent exec shell was open. The original exec client returned 137 and the container was observed stopped. The controller did not restart it. This checks container main-process lifetime, not provider behavior or conversation resume.

Both fixture containers, both fresh home volumes and both synthetic project directories were removed. The original Foot and exec clients were waited. The anchor reported success with exit status 0, and its exact empty slice was stopped and reverted. Postflight independently confirmed no nonce-owned container, volume or test window, and an inactive slice with an empty control-group path. Retained fixture-slice counters show an 11,845,632-byte memory peak, seven tasks at peak and zero high, max, OOM, kill or task-limit events. These counters cover the fixture slice, not the entire desktop, Foot or controller process.

Private evidence is at `$HOME/Work/omarchy-agent-container-shell-native-05/`. `RESULT.json` retains the original successful controller outcome with visual review pending at capture time. `VERIFIED.json` records the subsequent inspected captures, combined coverage and unchanged five-file source binding. `SHA256SUMS.json` is a self-excluding evidence manifest. Original attempt receipts were not rewritten to claim later success.

## Publication and CI review

Local commit `9eae668dd7aed58bc021370505ecd7b0f552a379` contains the five implementation files and seven change artifacts. The final source review found no blocking issue in that scope. Tested implementation hashes matched, strict OpenSpec validation passed, and private runtime evidence and pending goal-document edits were excluded. No application or native test was repeated during commit preparation.

Publication attempt 01 failed with Git exit status 128 because the isolated invocation could not obtain an HTTPS username. No feature branch or PR was created, and no CI run started. The original attempt remains failed. After renewed approval, attempt 02 supplied GitHub CLI's credential helper for that push only, without changing persistent Git configuration, and opened [PR23](https://github.com/kecol/omarchy/pull/23) against `quattro` at the exact reviewed commit.

[Tests 44917255058](https://github.com/kecol/omarchy/actions/runs/44917255058) passed for that feature head: CLI/theme and aggregate shell checks completed 454 test files without failures; eight files contained skipped checks. The downloaded session-menu log confirms all 34 methods passed without skips. [Translation checks 44917255103](https://github.com/kecol/omarchy/actions/runs/44917255103) also passed for the same head. These CI results are regression evidence, not additional native Podman or graphical acceptance qualification.

The skip-bearing files were `agent-model-recovery-native-test.sh`, `agent-openshell-native-tools-test.sh`, `brightness-display-apple-cache-test.sh`, `fontconfig-cjk-test.sh`, `hw-match-device-tree-test.sh`, `i18n-test.sh`, `kitty-config-test.sh` and `panel-open-budgets-test.sh`, all under `test/shell.d/`. A passing file with skipped checks does not qualify those skipped cases. No manual CI retry or dispatch occurred.

Private receipts remain under `$HOME/Work/omarchy-agent-container-shell-commit-01/`, `$HOME/Work/omarchy-agent-container-shell-publication-01/` and `$HOME/Work/omarchy-agent-container-shell-publication-02/`. Raw native records and screenshots were not uploaded.

## Merge and retained preflight control error

After separate merge approval, GitHub merged PR23 as `db9ba29a434bd21f0d183ed7b972a0d96aabd63c`, with parents `1f879a93f309b8742d83145b9a0321cdd2d9c76a` and `9eae668dd7aed58bc021370505ecd7b0f552a379`. The initial textual diff-comparison assertion failed because GitHub and local Git supplied different informational hunk-header function labels. The command sequence lacked failure stopping after that assertion and incorrectly continued to the authorized merge. This is a failed preflight and an assistant command-control error, not a successful admission check or a product defect.

Mutation stopped after detection. Independent read-only checks confirmed the expected parents and exact identity between the merged tree and the reviewed feature tree. These checks do not reclassify the original preflight as passed. No rollback, merge retry, source change or activation occurred during that follow-up. The existing active source, goal-document metadata, planning copies, modes and unrelated worktree indexes remained preserved.

The automatic [post-merge Tests 44918793323](https://github.com/kecol/omarchy/actions/runs/44918793323) passed at the exact merge: 454 test files completed without failures; eight files contained skipped checks. No CI retry occurred. Private merge, incident, tree-verification and CI receipts remain under `$HOME/Work/omarchy-agent-container-shell-merge-01/`.

## Source activation and permission correction

After separate source-activation approval, the existing dev-linked `quattro` checkout fast-forwarded from the base to the reviewed merge. Before checkout, the seven byte-identical untracked planning files were moved to a private backup so that incoming tracked files could take their place. Goal-document edits were not moved or stashed. No merge commit, image build, package operation, migration, refresh or restart was needed.

Activation attempt 01 completed the fast-forward but failed its permission postflight. The private-evidence umask `077` was inherited by Git checkout: four replaced tracked files and seven incoming planning files became `0600`, the new command became `0700`, and three incoming planning directories became `0700`. Source bytes still matched the reviewed commit. The original attempt remains failed; correction did not proceed automatically.

After renewed approval, attempt 02 restored permissions only on those twelve files and three directories: regular documents and Python files to `0644`, the command to `0755`, and the three planning directories to their original `0755`. Postflight verified all 5,559 preexisting tracked-file modes, 22 other worktree indexes, unrelated active-index entries, pending goal-document metadata, planning contents/modes/owners, and the unchanged tested implementation bytes. The original planning files remain intact under `$HOME/Work/omarchy-agent-container-shell-activation-01/planning-backup/`.

The active `omarchy agent shell --help` route passed without inventory or container execution. Activation did not enter a container, launch a provider, restart an agent or repeat application/native tests. Subsequent invocations use the activated source; this is not a new native or graphical qualification. Private failure and correction receipts remain under `$HOME/Work/omarchy-agent-container-shell-activation-01/` and `$HOME/Work/omarchy-agent-container-shell-activation-02/`.

## Remaining gates and limitations

[verification-plan.md](verification-plan.md) now records completed bounded checks, not standing permission to execute again. Core native cases came from attempt 03, the replacement and fault-injection cases from attempt 04, and graphical/main-process-exit cases from attempt 05. Inventory was scoped by a private adapter to nonce-labeled synthetic fixtures; the metadata failure was injected, not a real engine outage. The containers used a finite Bash wait process rather than an agent/provider. This is local x86 image and fullscreen-terminal evidence, not qualification of every image, platform, custom shell configuration or narrow terminal. No additional application test or runtime retry follows from this closeout.

Fresh validation plus full-ID execution prevents name-based replacement targeting but is not atomic against every same-ID restart race. Labels and current-user identity are not authenticated ownership against another process with the same host-user authority. The shell shares the harness's existing files, home, credentials and limits. Bash startup code may execute. Harness exit still stops the container and its shells.

Herdr, persistent container owners, conversation sharing and concurrent conversation-writer policy remain deferred to later exploration. Source delivery and activation are complete within the recorded scope. The owner subsequently approved main-spec synchronization and archive as documentation-only tracking work. Commit/publication of this new closeout still require separate approval. Reconciliation does not renew native verification, erase failed attempts or authorize further runtime actions.

## Tracking publication and archive closeout

Delivery reconciliation was separately committed and published as `eca2500593229a428bf6928c5fed707c9229850e`, “Record agent container shell delivery”. Its automatic [Tests 44922393670](https://github.com/kecol/omarchy/actions/runs/44922393670) failed in the unchanged account-copy fixture before the intended exit-78 checkpoint. All 34 session-menu methods passed. That run remains failed, and its triggering process identity remains unknown; the feature and merge passes above do not erase it.

The separately approved account-copy fixture isolation arrived through [PR24](https://github.com/kecol/omarchy/pull/24), merge `9aca54efe1c066fc00524de00d076861c44bf21a`, and source integration. Feature Tests `45098956445` and merge Tests `45171286751` passed 454 test files with zero failures and eight skip-bearing files. Both account-copy fixture logs passed all six original checks without skips. Those later checks qualify their snapshots, not the historical interference mechanism. The HOME-less-neighbor comparison remains explicitly deferred and unperformed in the [account-copy outcome](../2026-11-23-isolate-agent-account-copy-test/outcome.md).

This approved tracking closeout synchronizes the unchanged shell delta into its new main spec and retains the complete change in the dated archive. The delta Purpose and all seven requirements/fourteen scenarios are preserved exactly. Native failure receipts, the startup redraw limitation, publication/merge/activation failures, credentials-sharing warning and non-atomic targeting limits remain unchanged. No runtime/test source, package, image, default or user configuration changes. Pending goal edits and unrelated worktree indexes remain protected. Archive placement is not new runtime qualification, renewed execution permission or release certification.
