# Runtime availability implementation outcome

## Status and scope

MERGED AND ACTIVE FOR SUBSEQUENT INVOCATIONS. [PR17](https://github.com/kecol/omarchy/pull/17) merged as `1f869f00bc789aac46e9363eeb14fdfcc0155ab8` on 2026-11-16. Separate approval then integrated that exact reviewed source into the active `quattro` checkout. Focused checks, named native N1–N6 and required PR/CI passed with the limits below. Earlier failures remain failed under their original contents and contracts. Native attempt 06 retains its reviewed reclaim-aware resource result, confirmed guest restoration and owned cleanup. No host installation, image build, reboot or additional runtime qualification followed from source integration.

Implementation used `$HOME/Projects/omarchy-runtime-availability`, branch `fix/runtime-snapshot-unavailability`, based on `65c3a23eb0fb1cbd2d88d5a51470a8f23202bc4d`. The final delivery tree is `e0151b04067728ba11b6277faec374d4d18ac86c`. The separately approved source integration moved the already selected `$HOME/Projects/omarchy` checkout to that merge without changing the dev link or restarting existing processes. Earlier proposal/design and private receipt statements about unperformed publication, CI or activation describe their historical checkpoints, not current delivery status. This documentation closeout is an unpublished review draft; a later documentation tree is not the recorded CI-tested tree and adds no new application/native qualification.

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

The native component supplies passing evidence only for the named staged integrations. Workspace manager remains focused-tested, not newly native-qualified; all ten callers' broad unavailable-control-flow coverage remains in fixtures. The subsequent PR/CI review below supplies the separate broader regression result. This reconciliation neither reruns nor expands native qualification.

## Publication and CI review

Publication approvals first covered five retained prerequisites plus two new commits. Two separately approved CI corrections then extended PR17 to nine commits and 60 paths against public `quattro` at `68d22643e4bd4df623977d125da7ce3b06f3a30f`. The prerequisites are catalog extraction (`d2471ba1d`), OpenSpec workflows (`749b87c50`), safety documentation (`c3d459ae7`), harness installer-stage full upgrades (`0603b244e`) and initial local-engine routing (`65c3a23eb`). The four later commits are validation guidance (`756828764`), runtime availability and routing follow-up (`8cf8d07d7`), initial CI/fixture repair (`88462ef51`) and unit-manager expansion correction (`4f3913c31`). No existing commit was rewritten. The two Containerfile edits were source-reviewed and exercised by build fixtures, not qualified by actual image builds.

| Tests run, attempt 1 | PR head and actual merge checkout | Recorded outcome |
| --- | --- | --- |
| [43783778084](https://github.com/kecol/omarchy/actions/runs/43783778084) | `8cf8d07d7755ef57b7464d446fd3352f22f4e359`; `cec130f507939a54d3933df7274acbc164368ffe` | Failed: 68 of 454 shell files. 67 reported untrusted project mise configuration; the menu clone fixture also expected the old Podman argv. CLI and translation checks passed; seven files contained skip markers. |
| [43802742180](https://github.com/kecol/omarchy/actions/runs/43802742180) | `88462ef51d2bbaa9fc1c07fda9b7f0419bb3de01`; `fc27c15c8a68bd8a0cad95a44fdb20e5d715e580` | Failed: 67 of 454 shell files still reported the trust diagnostic. The menu fixture passed. CLI and translation checks passed; seven files contained skip markers. The direct-Bash PATH control missed the unit-manager boundary. |
| [43874285028](https://github.com/kecol/omarchy/actions/runs/43874285028) | `4f3913c31d051df036b72e2b847b8613a632ce62`; `69d9b66992b94171b9ca8dcc13705935c520ea40` | Passed: CLI and all 454 shell files completed without failures; eight files contained skip markers. No untrusted-checkout mise diagnostic remained. |

Each actual checkout had the same tree as its corresponding PR head. The passing checkout tree is `21987d1323db63bd9757eb7e9dd64541045acf59`; CI reported zero changed source files after execution and `rc=0`. The Tests VM stage finished after 375 seconds. [Translation workflow 43874285022](https://github.com/kecol/omarchy/actions/runs/43874285022) passed with structural i18n, sync-workflow and extraction checks executed. The main shell census excludes nested runner self-test directories. The initial passing-run reader assumed the previous seven skip-bearing files; its corrected census records the eighth marker without rerunning CI or downloading the artifact again.

The first repair exposed the already resolved installed Node directory in the guest test PATH and updated the existing menu fixture to assert `podman --remote=false ps`. It did not resolve the trust failures. The second repair delegates inline payload expansion to Bash with `systemd-run --expand-environment=no`; default manager expansion had consumed `${OMARCHY_TEST_NODE_BINARY%/*}` before Bash ran. A bounded source-bound real-manager check failed installed Node selection with previous source and passed with corrected source before publication. No unexpected shim, trust bypass or project-tool installation was used in that check. The first catalog-only evidence binding had missed the changed transitive workspace dependency; the failed menu fixture remains evidence of that coverage gap.

| File containing skipped checks | Reviewed limit |
| --- | --- |
| `agent-model-recovery-native-test.sh` | Installed Pi absent. |
| `agent-openshell-native-tools-test.sh` | Installed Pi absent. |
| `brightness-display-apple-cache-test.sh` | No hiddev character device for the valid-cache case. |
| `fontconfig-cjk-test.sh` | Chinese locale absent. |
| `hw-match-device-tree-test.sh` | Turkish locale absent. |
| `i18n-test.sh` | No pending translations in structural mode. Structural, plural, locale, keybinding and extraction checks executed and passed; this marker was previously hidden by the Node failure. |
| `kitty-config-test.sh` | Kitty absent. |
| `panel-open-budgets-test.sh` | No-battery power-panel case. |

These limits are not passes for omitted native/tool/hardware cases. No required availability case was waived. VM-backed CI still includes fake engine, provider and action endpoints; it does not turn those tests into native Podman, workspace-manager, provider, hardware, containment or release qualification. Both earlier failed Tests runs remain failed, not retrospective passes or unchanged-content retries.

Raw publication and first-failure evidence remains under `$HOME/Work/omarchy-runtime-availability-publication-01/` and `$HOME/Work/omarchy-runtime-availability-ci-review-01/`. The first CI repair and its failed result remain under `$HOME/Work/omarchy-runtime-availability-ci-fix-01/`. The passing result, source-bound boundary control, actual checkout/tree receipts, original ZIP and all per-file logs remain under `$HOME/Work/omarchy-runtime-availability-ci-fix-02/`. Its retained manifest is `84eeb4709923d6f08fe3d5146a73c5b21f51bce35d113e046d12cda001d9a8b9`; artifact ZIP SHA-256 is `d03a2c9ed395676e79703bb3b55c75ab372a4b52c1a9c2b450a82de0590f565d`. These are portable private evidence locators and content bindings, not public copies of raw evidence.

## Final publication, merge and activation

Documentation commit `2f77fe93e6c713ba22f1a22de270ed3e297f9d5e` published the three reviewed reconciliation files without changing their bytes. PR17 then contained ten commits and 60 paths. Its descriptions identified uncommitted/unpublished wording as the preserved earlier review checkpoint. [Tests run 43883520871](https://github.com/kecol/omarchy/actions/runs/43883520871), attempt 1, passed CLI and all 454 shell files, with zero failures and the same eight skip-bearing files. Actual checkout `f4e83ddb7410f14ca549ada30e789de9919e5c2b` had the delivery tree `e0151b04067728ba11b6277faec374d4d18ac86c`. [Translation workflow 43883520869](https://github.com/kecol/omarchy/actions/runs/43883520869) passed with structure, sync-workflow and extraction checks executed.

After separate merge approval, merge `1f869f00bc789aac46e9363eeb14fdfcc0155ab8` retained public base `68d22643e4bd4df623977d125da7ce3b06f3a30f` and documentation head `2f77fe93e6c713ba22f1a22de270ed3e297f9d5e` as its exact parents, preserving all ten commits and the feature branch. Its tree matched the delivery tree above. Automatically triggered [post-merge Tests run 43886918266](https://github.com/kecol/omarchy/actions/runs/43886918266), attempt 1, passed CLI and all 454 shell files with zero failures and the same eight skip-bearing files. Actual checkout was the merge itself. CI reported zero changed source files and `rc=0`; the VM stage took 391 seconds. Translation is pull-request-only; no extra translation run was dispatched after merge. The push-checkout evidence reader initially assumed the detached PR checkout log format; its retained assertion was corrected using the actual checkout git-log output without rerunning CI or redownloading the artifact.

The merge-author policy check failed after publication because the assistant did not explicitly pin the required public `noreply` email and GitHub selected a non-noreply account email. The user accepted leaving that metadata and published history unchanged. The failure remains recorded; acceptance is not a retrospective policy pass. No account setting, author metadata or history was rewritten. Do not copy the address or private account data into this record.

The six active planning overlap files first received independent content/mode-verified private backup copies. Following explicit resolution and activation approval, the original untracked change directory was moved intact to private preservation, and the modified tracked document was independently copied before restoring only that document to its indexed baseline. Active `quattro` then fast-forwarded from `65c3a23eb0fb1cbd2d88d5a51470a8f23202bc4d` to the merge. This added six commits including the merge across 23 paths: six runtime owners, five reference/manual documents, seven change/history files and five CI/test files. The index and working tree were clean after integration. All 23 updated file hashes/modes matched the reviewed source. `OMARCHY_PATH` and metadata-only command resolution remained on the same checkout, so subsequent invocations use the repaired source without a reboot. Existing processes and images were not restarted or rebuilt. User shell configuration, including the restored workspace widget, remained unchanged by integration.

All 648 frozen native source hashes and 15 tested-source hashes match the integrated source. An exact-mode postflight assertion failed on an untouched file and remains retained. Read-only review identified 62 preexisting stricter-mode differences outside the 23-path integration scope: active 0700 versus staged 0755, or active 0600 versus staged 0644. Their change timestamps predated activation, owner permission bits matched, and they added no permissions. These modes were preserved, not repaired. Do not claim that every active mode matches the native staged manifest or that CI retrospectively qualifies those differences. No changed runtime command, application suite, native run, package operation, migration, refresh or restart was executed during integration.

Private delivery receipts remain under `$HOME/Work/omarchy-runtime-availability-doc-publication-01/`, `$HOME/Work/omarchy-runtime-availability-merge-01/` and `$HOME/Work/omarchy-runtime-availability-source-integration-01/`. The original backup remains under `$HOME/Work/omarchy-runtime-availability-active-planning-backup-01/`; the original planning directory and tracked-document copy remain under `$HOME/Work/omarchy-runtime-availability-source-integration-01/originals/`. These locators are not public evidence publication or hostile same-user containment. Original native/CI failures, mixed fault-injection limits, eight skip reasons and the consumed native invocation remain unchanged.

## Final contract review

Static review of the six-owner combined diff and retained focused/native/CI evidence found no blocking runtime-code issue. At the inactive-candidate final review, all 648 staged source hashes/modes and 15 tested-source bindings matched. Integrated source hashes still match; the preexisting active-mode differences are recorded above. Successful application/native suites were not rerun to record this result. The ten direct callers retain these contracts:

| Caller | Reviewed failure handling |
| --- | --- |
| `omarchy-agent-list` | Only producer status 2 yields a successful partial configured view, with null/unknown counts and false availability; other errors propagate. |
| `omarchy-agent-audit` | Checked snapshot capture fails before audit success, advisory doctor or fix actions. Its extra source edit filters only Podman child selectors. |
| `omarchy-agent-ps` | Checked capture refuses unavailable observation rather than a successful empty report. |
| `omarchy-agent-inspect` | Checked capture precedes active matching and historical fallback; failure does not authorize history as evidence of inactivity. |
| `omarchy-task-preflight` | Checked snapshot pipeline refuses admission when observation is unavailable. |
| `omarchy-task-start` | Its later checked snapshot recheck refuses launch/finalization after earlier preflight/audit success. |
| `omarchy-task-stop` | Checked discovery fails before dependent stop/state changes. Its extra edit filters only Podman child selectors. |
| `omarchy-task-cleanup` | Checked observation precedes assignment deletion/finalization, including force. |
| `omarchy-task-archive` | Checked initial observation and nested cleanup results precede final archive status, including force. Earlier successful cleanup is not rolled back. |
| `omarchy-task-status` | Checked runtime observation refuses an unavailable report. Earlier reconciliation writes remain possible. |

The six unchanged caller files are ps, inspect, preflight, start, cleanup and status. Snapshot validation remains the shared producer boundary. All 14 workspace-manager Podman calls retain explicit local selection and fresh child-only selector removal; generic subprocesses and intentional Remote SSH remain unchanged. Same-user authority, labels/visibility, name-based legacy stops, observation/action races and missing producer deadlines remain documented limitations.

## Reviewed integration and rollback handoff

This section retains the pre-integration handoff reviewed at code head `4f3913c31d051df036b72e2b847b8613a632ce62`. At that checkpoint PR17 was open and the final reconciliation was unpublished. Subsequent separate approvals completed documentation publication, merge, overlap preservation/resolution and activation as recorded above. The sequence below remains the reviewed historical plan; it does not authorize another update or rollback. A later documentation tree must not be relabeled as a previously tested full tree.

At the handoff checkpoint, active `quattro` was at `65c3a23eb0fb1cbd2d88d5a51470a8f23202bc4d`, already containing five prerequisites. The then-published candidate added four local commits and 23 paths, while PR17 had nine commits and 60 paths against the earlier public base. The later documentation commit and merge account for the final six incoming local commits without adding paths. No ancestry was hidden by rebasing, squashing or force-pushing.

At the handoff checkpoint, modified `docs/openspec.md` matched the published candidate. The untracked change metadata/spec matched; proposal/design/tasks differed, and outcome was absent. Initial fingerprints were not backups and authorized no overwrite or deletion. Later explicit backup and content-resolution approvals preserved all six originals before the reviewed incoming versions became tracked. Existing independent copies and the moved original directory remain at the private locators above.

The reviewed sequence required separate approval for each applicable operation:

1. Confirm the exact delivery head, public base, PR checks, runtime/test bindings and remaining documentation-only delta.
2. Preserve the active tracked/untracked overlaps and obtain an explicit resolution decision for differing planning content.
3. Review and authorize publication of the final documentation if it is part of delivery.
4. Obtain separate approval for a normal history-preserving PR merge; stop if the public base or merge tree introduces unreviewed source.
5. Obtain separate approval to update the active checkout to the reviewed result; recheck the active baseline and overlap preservation first.
6. Verify resulting file hashes/modes and command resolution by metadata, without starting managed agents or changing task/workspace state.

Changing the already selected runtime source affects subsequent CLI/workspace invocations without a reboot. Existing agent/container processes are not restarted. No dev-link switch, user-config refresh, service restart, package transaction, migration or image build belongs to this handoff. In particular, the existing harness installer-stage changes do not authorize rebuilding or replacing running images.

Warning: rollback to the active baseline restores successful false-empty readiness reports, ignored nested cleanup failure and ambient named-connection selection. Prefer a reviewed forward correction when feasible; do not assume the older source is safer. A rollback needs its own approval, exact affected-path review and preservation receipts. Use a new coherent change for affected runtime/tests/references while retaining historical outcomes and publication evidence; do not reset published history or unrelated active work. Keep the baseline's explicit `--remote=false` option, while acknowledging its selector gap. CI-only corrections may be assessed separately without unnecessarily removing the availability repair. Source rollback does not recreate deleted assignment directories, reverse earlier cleanup or restore registry/container state; never claim transactional rollback or automatically mutate user data.

## Delivery status

The required focused, named native and PR/CI evidence is reviewed with its limits. All three tasks are complete. The reviewed merge is active for subsequent command invocations after explicit overlap-resolution and activation approval. This closeout changes documentation only; archive placement and main-spec synchronization are tracking operations, not new qualification or runtime permission. The native invocation remains consumed. Earlier failures, skipped checks, the accepted merge-author metadata exception and the preexisting active-mode differences remain explicit. No provider, graphical, hardware, full containment or release qualification is claimed. Any commit/publication of this closeout or further runtime work requires separate approval.
