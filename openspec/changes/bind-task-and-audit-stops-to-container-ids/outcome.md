# Stop-target binding outcome

## Delivery status

IMPLEMENTED CANDIDATE; focused checks and named native qualification passed. Publication and continuous integration (CI) are approved but pending. Task 3.1 remains open until required CI and the final delivery review complete. Merge, active integration, main-spec synchronization and archive are not approved or performed.

The candidate branch is `fix/task-audit-stop-target-binding`, based on `19eea4aa53de29b8106bd0e58d5482778ccf5ae9`. The active dev-linked checkout remains at that base. Planning and earlier focused-check approval did not grant native execution; the user separately approved the new private packet and one native invocation. The user subsequently approved commit, PR publication and CI. No earlier consumed native approval was reused.

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

Commit and PR publication are approved for this candidate only. Required CI has not yet run for this change. Do not substitute the prior runtime-availability CI result or these focused/native results for the new PR's exact tested checkout. Record original CI failures and explicit skips without automatic retries or trust exemptions.

## Integration and rollback handoff

Before merge, review the published diff, commit identities, exact CI checkout/tree, native/focused source bindings and explicit coverage limits. Obtain separate merge approval. Preserve branch/history; do not squash, rebase, reset, force-push or rewrite published metadata automatically.

Before activation, obtain separate approval for the exact reviewed integration into the existing dev-linked checkout. Integration activates subsequent CLI invocations without a reboot. Preserve unrelated work, the existing dev link and preexisting stricter file modes. No package operation, configuration refresh, restart, migration or image rebuild is required by this source change.

Rollback needs separate approval to restore the reviewed parent versions of the two owners and compatible references/tests. It restores known name-retargeting and audit-association weaknesses and cannot undo completed stops or registry writes. IDs do not authenticate labels, bind process incarnations, prevent concurrent launches or make observation/action and registry updates transactional. Do not treat tracking completion as runtime or closeout permission.

## Private evidence locators

- `$HOME/Work/omarchy-stop-target-binding-apply-01/REVIEW.md`: focused suites, semantic controls, original failures and relevant source bindings.
- `$HOME/Work/omarchy-stop-target-binding-native-plan-01/REVIEW.md`: original planning scope and retained preparation failure.
- `$HOME/Work/omarchy-stop-target-binding-native-procedure-01/REVIEW.md`: frozen packet and offline checks; its original preparation status predates the later execution approval.
- `$HOME/Work/omarchy-stop-target-binding-native-01/`: complete runtime, provisioning, restoration, resource and cleanup evidence.
- `$HOME/Work/omarchy-stop-target-binding-native-review-01/REVIEW.md`: read-only review of named cases and retained source/cleanup evidence, without a rerun.
- `$HOME/Work/omarchy-stop-target-binding-publication-01/`: publication preparation and later exact CI evidence, when available.

These local paths are not public artifacts or independent verification. Raw transcripts, account/session identifiers, credentials and private home paths remain outside Git.
