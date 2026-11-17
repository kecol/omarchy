# Stop-target binding outcome

## Delivery status

IMPLEMENTED, MERGED AND ACTIVE; focused checks, named native qualification and reviewed continuous integration (CI) passed. All three tasks are complete. Separate approvals merged [PR18](https://github.com/kecol/omarchy/pull/18) and activated its exact reviewed source. Later closeout approval synchronized the main specification and archived this change in an inactive closeout worktree. A further approval covers documentation-only publication, automatic CI review and subsequent integration of the tracking files. Archival does not renew runtime or release qualification.

The implementation candidate branch is `fix/task-audit-stop-target-binding`, based on `19eea4aa53de29b8106bd0e58d5482778ccf5ae9`. The active dev-linked checkout now reads merge `bdc914d401e03825637a112ff072ee0549b939da`, tree `41d75591ad12dfadbe78529919646bddc07e86d6`. Planning and earlier focused-check approval did not grant native execution; the user separately approved the new private packet and one native invocation. The user subsequently approved commit, PR publication and CI. No earlier consumed native approval was reused.

## Implemented contract

`omarchy-task-stop` validates the complete selected assignment plan before writing lifecycle state. It requires full, unique, lowercase hexadecimal container IDs and Podman runtimes, stops only those IDs and writes `stopped` only after every request succeeds. Names are display metadata. A failed later stop can leave earlier stops and intermediate `stopping` state.

`omarchy-agent-audit --fix` validates full, unique IDs across the captured snapshot, associates failed checks with container IDs and validates its whole repair plan. A failed row needs a nonempty string instance label that identifies exactly one row in the full snapshot, including passing rows. Missing or ambiguous association refuses the entire repair plan before stop or dependent finalization. Successful stops retain best-effort instance/assignment updates. Failed requests report `stop-failed`, return nonzero and receive no dependent finalization.

Both callers retain explicit local routing and child-local removal of `CONTAINER_HOST` and `CONTAINER_CONNECTION`. Unavailable observation still refuses dependent actions. Engine-default stop escalation can reach KILL. Audit still invokes its advisory quick doctor; this change does not make audit read-only.

Only the two runtime owners, their two existing fixture files and current reference supplements change. The producer, registry schema, shared helpers, workspace manager, desktop, translations, packages, migrations, images and user configuration remain unchanged. No new runtime framework or dependency is introduced.

## Content bindings

These content hashes bind the focused suites and native runtime owners. Native qualification staged seven runtime files totaling 28,132 bytes. Guest executable copies used 0700 modes rather than the candidate's 0755 modes; no whole-checkout or active-mode equivalence is claimed.

| File | SHA-256 |
| --- | --- |
| `bin/omarchy-task-stop` | `4443c0fe48ecda598a48342ccc66a873ec26042467cb868d70804703102f742c` |
| `bin/omarchy-agent-audit` | `2568c1456f6e7c510aed720d595227e6b50337e2f6c20c6772b3a0511995e563` |
| `test/shell.d/task-workspace-test.sh` | `f9c54df5a7c4fd1aa813295aaa39fc48218c4f50ed8e89bb2c18c794b70ac313` |
| `test/shell.d/agent-inventory-test.sh` | `02628668ad4282b8516d6651f761d1e62b000a2c4efc65c26073c6054bed26a4` |

The staged runtime source-manifest digest is `2e9cb601dc064de2cf2904dc6af33f93d6d0edb617c9342797ae67ab6bb7bd85`. The frozen native program-manifest digest is `8ed0583d7408be88d9026e3d6103b8e831f196a6fc26b088a9e1f9d7914b09db`; the contract digest is `c178a9c058d90b87626f921627d43d57d6666a327e3898cca395a6db864583d5`. These are evidence bindings, not authentication against a hostile same-user process.

## Focused checks and original failures

The final task/workspace suite passed 30 assertion groups and the final inventory/audit suite passed 17 groups, without skips. Stateful fake engine catalogs resolve names independently of the real caller's selection logic and record actual selected synthetic objects. Inventory copies audit beside an inert advisory doctor. These checks cover malformed/duplicate IDs, invalid later rows, unsupported runtimes, optional display names, ambiguous instance labels, selective repair, partial failures and existing availability/local-routing behavior.

Three disposable controls failed semantically: base task name targeting, audit name targeting, and a combined audit association-boundary omission restoring instance-key selection while removing the ambiguity guard. The combined control does not establish that changing only the map key defeats a retained ambiguity check.

Original failures remain retained: an initial task-fixture jq expression, an initially invalid association control and an overbroad source-binding assertion. Corrections were scoped. The final task suite covers its later strict empty-runtime correction; audit source and its fixture/helper bindings remained unchanged, so the successful inventory suite was not rerun. Source/document checks retained exact scope, syntax, whitespace, local links and strict OpenSpec validation. These are not additional application-suite runs.

## Named native qualification

One separately approved invocation used a fresh disposable guest, real rootless local Podman 6.2.0, scratch lifecycle records, the real policy helper and a pinned offline BusyBox image. An event barrier delayed complete successful output from the unchanged real snapshot producer; the driver verified mutation before releasing the exact original bytes. The adjacent advisory doctor was inert. There was no engine shim or execution tracer.

| Case | Observed result |
| --- | --- |
| N1: task ordinary stop | Selected ID stopped; assignment finalized as stopped. |
| N2: audit ordinary repair | Selected ID stopped; instance and assignment finalized as failed for controlled label drift. |
| N3: task rename/name reuse | Renamed original A stopped; replacement B at the old name remained running. |
| N4: audit rename/name reuse | A stopped, B remained running and only A's associated records finalized. |
| N5: task vanished ID/name reuse | Caller returned 125, B remained running and assignment stayed stopping. |
| N6: audit vanished ID/name reuse | Caller returned 1 with stop-failed, B remained running and failed-target records did not finalize. |

The direct-ID oracle used clean selectors and explicit local routing. Failed queries were not accepted as absence. Audit deliberately selected a `mounted` source-policy label while actual mounts remained empty; its successful repairs retained `ok: false` for that observed drift. This qualifies named ID-binding and failure behavior, not dangerous-bind detection, comprehensive policy enforcement or the real advisory doctor. Label-collision and malformed-input coverage remains synthetic. Providers, graphical behavior, workspace-manager stops, other platforms/engine versions and broad containment were not qualified.

The exact guest-only add-only prerequisite transaction verified archives, obtained manual guest sudo and exact INSTALL consent, and restored the original configuration. The recorded payload was 31,838,329 bytes; historical package-archive bytes total 31,835,867. Native input hashing occurred inside the bounded worker. Fixture containers, imported image and owned VM state were cleaned. The pidfd cleanup guard confirmed owned QEMU exit; the helper exited as expected, its reader ended, the service became inactive/dead and no other owned group members or VM state files remained. No host package operation occurred and no native retry ran.

The retained resource policy is `bounded-native-reclaim-aware-v1`, digest `0656efefc53c6a73e9a4b1cbd6704b1f8eaf682c88a517006409643d745a0897`. Host controls remained 5 GiB memory and 512 MiB swap around a 4 GiB/two-CPU guest. The run recorded 6,121 memory max-boundary events, 235 socket-throttled events, 5,370,462,208 peak memory bytes and 93,298,688 peak swap bytes. Memory high/OOM/OOM-kill/group-kill and task-limit counters were zero. Max-only events were not independently fatal under the already reviewed policy; the socket counter is retained and is not classified as fatal by that policy. This was not a pressure-free run or proof of an absolute physical-memory ceiling. Post-teardown statistics do not identify memory composition at the exact peak.

## Publication and CI

[PR18](https://github.com/kecol/omarchy/pull/18) publishes code/review commit `b196ad94fcffc487dc045091987c51eb1e80507d`. Both author and committer were explicitly pinned to `kecol <5040769+kecol@users.noreply.github.com>`. [Tests run 44077579604](https://github.com/kecol/omarchy/actions/runs/44077579604), attempt 1, passed the CLI suite and all 454 shell test files with zero failures and eight explicit skip-bearing files. Its actual checkout was `d805cbedce03a85e37e2ecab611023e87df81b3c`, with base/head parents `19eea4aa53de29b8106bd0e58d5482778ccf5ae9` and `b196ad94fcffc487dc045091987c51eb1e80507d`. Its tree matched the published code tree: `a3fa7856e26bae948accdfbf6d7c83eaa88cfa77`. The workflow reported zero changed source files and `rc=0`.

The eight skip-bearing files retain their exact limits: two require an installed Pi binary; one lacks hiddev hardware; two lack the Chinese or Turkish locale; one lacks Kitty; one covers a no-battery panel case; and structural i18n marks no pending translations. Structural i18n checks executed. [Translation run 44077579429](https://github.com/kecol/omarchy/actions/runs/44077579429) passed structural, sync-workflow and extraction checks. These are VM-backed regression results, many with fake executables or scratch data, not additional native engine, provider or hardware qualification.

Documentation-only commit `c8119afc4c8bb3d4097e04472160790c1d1402fa` recorded these code-head results and completed task 3.1 without changing runtime/test content. [Tests 44079423851](https://github.com/kecol/omarchy/actions/runs/44079423851), attempt 1, also passed 454 shell files with zero failures, the same eight skip-bearing files, zero source changes and `rc=0`. Its actual checkout `4d9c09923da3ca0a6f198b1e7ee343d2ee8127e1` had the same tree as that published head: `41d75591ad12dfadbe78529919646bddc07e86d6`. [Translation 44079424354](https://github.com/kecol/omarchy/actions/runs/44079424354) passed structural, sync-workflow and extraction checks. No manual CI retry or successful local-suite rerun was used to reproduce evidence. The prior runtime-availability CI result is not substituted for this change's qualification.

## Merge, activation and closeout

Separate merge approval published `bdc914d401e03825637a112ff072ee0549b939da` with exact parents `19eea4aa53de29b8106bd0e58d5482778ccf5ae9` and `c8119afc4c8bb3d4097e04472160790c1d1402fa`, preserving both feature commits and their branch. Its tree equals the reviewed final candidate tree. Both author and committer were explicitly pinned and verified as `kecol <5040769+kecol@users.noreply.github.com>` before publication and checked against the published Git object. No default GitHub merge-author metadata, squash, rebase, force-push or history rewrite was used.

Automatic [post-merge Tests 44082114258](https://github.com/kecol/omarchy/actions/runs/44082114258), attempt 1, passed at the merge itself: CLI and 454 shell files, zero failures, the same eight skip-bearing files, zero changed source files and `rc=0`. [Translation sync 44082114289](https://github.com/kecol/omarchy/actions/runs/44082114289) succeeded. These automatic new-head results remain distinct from the single named native invocation.

After separate source-only activation approval, the active local branch fast-forwarded from the base to that exact merge across twelve incoming paths. The five unchanged original planning files received an independent verified copy before their original directory was preserved intact; only the old task record differed from the incoming planning versions. All twelve incoming content hashes, native/focused content bindings and original file/directory modes matched postflight. A full-checkout census preserved 1,305 preexisting stricter tracked-file modes and 509 existing directory modes. That census is broader than the earlier availability delivery's 62 differences within its native-source subset; it does not establish newly changed permissions or whole-manifest mode equivalence. The active checkout/index became clean; command resolution, `OMARCHY_PATH` and the user's shell configuration remained unchanged. Subsequent CLI invocations now read this fix without a reboot. No changed runtime command, local application/native test, package operation, configuration refresh, migration, image build or restart ran during activation.

On 2026-11-17, separate closeout approval synchronized all five requirements and thirteen scenarios into `openspec/specs/managed-stop-target-binding/spec.md`, with the delta Purpose copied verbatim, then archived the complete change under `openspec/changes/archive/2026-11-17-bind-task-and-audit-stops-to-container-ids/`. The closeout reconciles current delivery records and links without changing runtime or test bytes, other main specifications or historical failures. The closeout was prepared in an inactive worktree. Separate approval then authorized its documentation-only publication and tracking integration after automatic CI review; neither operation changes the already qualified runtime source. This is tracking completion, not another application test, renewed native permission or release certification. Fork-friction analysis and the older upstream/storage campaigns were not started by closeout.

## Integration and rollback handoff

The original merge and exact-content source-activation gates were satisfied through the separate approvals recorded above. Future integration must still review the published diff, identities, exact CI checkout/tree, native/focused source bindings and coverage limits, preserve unrelated work and stricter permissions, and obtain its own approval. Source rollback, new runtime execution and closeout publication are not authorized by this completed delivery. Preserve branch/history; do not squash, rebase, reset, force-push or rewrite published metadata automatically.

Rollback needs separate approval to restore the reviewed parent versions of the two owners and compatible references/tests. It restores known name-retargeting and audit-association weaknesses and cannot undo completed stops or registry writes. IDs do not authenticate labels, bind process incarnations, prevent concurrent launches or make observation/action and registry updates transactional. Do not treat tracking completion as runtime or closeout permission.

## Private evidence locators

- `$HOME/Work/omarchy-stop-target-binding-apply-01/REVIEW.md`: focused suites, semantic controls, original failures and relevant source bindings.
- `$HOME/Work/omarchy-stop-target-binding-native-plan-01/REVIEW.md`: original planning scope and retained preparation failure.
- `$HOME/Work/omarchy-stop-target-binding-native-procedure-01/REVIEW.md`: frozen packet and offline checks; its original preparation status predates the later execution approval.
- `$HOME/Work/omarchy-stop-target-binding-native-01/`: complete runtime, provisioning, restoration, resource and cleanup evidence.
- `$HOME/Work/omarchy-stop-target-binding-native-review-01/REVIEW.md`: read-only review of named cases and retained source/cleanup evidence, without a rerun.
- `$HOME/Work/omarchy-stop-target-binding-publication-01/REVIEW.md`: both published heads, exact CI checkout/tree results and explicit skips.
- `$HOME/Work/omarchy-stop-target-binding-merge-01/REVIEW.md`: merge identities, preserved history and exact post-merge CI.
- `$HOME/Work/omarchy-stop-target-binding-activation-01/REVIEW.md`: source-only activation, permission census and original planning copies under `originals/` and `backup/`.
- `$HOME/Work/omarchy-stop-target-binding-closeout-01/`: local specification/archive checks and unchanged-runtime bindings; not publication evidence.

These local paths are not public artifacts or independent verification. Raw transcripts, account/session identifiers, credentials and private home paths remain outside Git.
