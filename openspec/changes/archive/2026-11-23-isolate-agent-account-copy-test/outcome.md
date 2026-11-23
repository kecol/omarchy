# Outcome

## Status and recommendation

IMPLEMENTED, PUBLISHED, MERGED AND SOURCE-ACTIVE at `9aca54efe1c066fc00524de00d076861c44bf21a`. The owner separately approved implementation, bounded checks, retained-evidence review, formal deferral of unsafe historical-process reproduction, commit/publication, merge, source integration and this documentation-only archive. The three retained delivery tasks are complete. The hazardous comparison remains deferred and unperformed, not passed. This local tracking closeout is uncommitted and unpublished; it grants no further runtime permission.

The main goal remains making Omarchy safe in the presence of coding agents while preserving a usable desktop. This test-only change protects synthetic fixture inventory without weakening production refusal. Its fixture-local boundary avoids shared-runner or runtime-policy changes, which limits upstream coupling. It is not a new general execution framework.

## Implemented source and review

The candidate is `$HOME/Projects/omarchy-account-copy-test-isolation`, branch `fix/agent-account-copy-test-isolation`, based on `eca2500593229a428bf6928c5fed707c9229850e`. Only `test/shell.d/agent-account-copy-test.sh` changes implementation code. Its SHA-256 is `8405803dd5f887f72ae7095d3252dcf079e16e67f4f546b549da7a7f1a21c2de`.

The new entry re-enters the same fixture through Bubblewrap, with private PID/mount/network namespaces, a matching `/proc`, a cleared synthetic environment, private writable scratch filesystems and five read-only source bindings. The inner entry compares kernel namespace observations, source mount access and scratch paths before account operations. A marker alone cannot admit the fixture. Missing prerequisites and setup failures return nonzero without success skips or host fallback. Coreutils timeout bounds the entry at 45 seconds with up to three seconds of termination grace.

The complete preexisting test body remains byte-identical, including real process discovery, missing/empty/relative HOME refusal, replacement/recovery and mock-SSH cases. Production account copy/transfer/state code, `base-test.sh`, shared runners, CI workflow and package lists remain unchanged. The five source bindings name this test, `base-test.sh` and the existing account copy/transfer/state commands. No host account homes or session sockets are mounted by the entry. PID namespaces do not hide fixture processes from an ancestor host; this is not universal containment or protection from someone who can rewrite the fixture.

## Evidence and limits

| Check | Retained result | Limit |
| --- | --- | --- |
| Bash and embedded Python parsing, original-body/source preservation, whitespace and installed-manual option review | Accepted static checks. | No runtime qualification follows from parsing or documentation. |
| Complete candidate fixture | One invocation passed all six original shell checks without skips. | Existing synthetic fixture and mock-SSH coverage, not provider authentication or real SSH. |
| Marker-only inner entry | Exit 1 before the body, as expected. | Named missing-observation case, not every possible malformed entry. |
| Invalid PID namespace descriptor in a disposable source copy | Real Bubblewrap exited 1 with `Setting pidns failed: Invalid argument`; retained-evidence review accepted the intended pre-body setup failure. | The original automated matcher rejected `pidns`; original native attempt and service remain failed. This was not an actual kernel-policy denial or a successful rerun. |
| Owned cleanup and resources | Original namespace child and manager client reaped; no remaining test descendants in the owned cgroup; service collected. Peak memory 78,733,312 bytes, peak tasks 12, zero memory max/high/OOM/kill and task-limit events. | Completed local attempt only; timeout enforcement/cleanup and other platforms remain unqualified. |

The native attempt used a 512 MiB memory ceiling, zero swap, 64-task ceiling, 100% CPU quota and 45-second service deadline. It completed in about 2.4 seconds. No limits were increased, no failed native operation was retried, and no passing fixture invocation was repeated to obtain output.

The historical [Tests run 44922393670](https://github.com/kecol/omarchy/actions/runs/44922393670) remains failed. Its log shows unknown-home refusal before the interrupted-replacement exit-78 checkpoint, but identifies no candidate process or lifecycle state. The isolated fixture result does not prove historical parallel interference, a zombie mechanism or harmless flakiness. At the pre-commit checkpoint, new-head full CI had not run. The subsequent feature and merge CI results below establish admission and fixture completion in those actual CI snapshots, not all-platform compatibility. Missing prerequisites must still fail clearly, not trigger installation, skipping or fallback.

## Failures and evidence handling

The initial static option lookup failed because its manual parser did not decode escaped hyphens. A separately approved documentation-only correction passed without changing source or rerunning parsing checks.

Native attempt 01 failed in its verifier because it required the literal word `namespace`, while Bubblewrap emitted `pidns`. The original logs, missing final automated case verdict, driver failures and service exit remain unchanged. A separately approved retained-log review checked the exact intended diagnostic, exit status, no body pass markers, source mutation, resource receipts and owned cleanup. That review accepts the named operation separately; it does not reclassify the failed attempt.

The first retained-evidence preflight found one manifest mismatch: the manifest hashed `postflight.log` while that redirected log was empty, before its final write. All other original manifest bindings match. The flawed manifest and finalized log remain preserved. The final review adds a manifest of finalized original files and creates its own self-excluding manifest only after redirected writers have exited. Those additive observations do not retroactively repair historical provenance.

Private evidence remains under `$HOME/Work/omarchy-account-copy-isolation-implementation-01/`, `$HOME/Work/omarchy-account-copy-isolation-native-01/`, `$HOME/Work/omarchy-account-copy-isolation-retained-review-01/` and `$HOME/Work/omarchy-account-copy-isolation-retained-review-02/`. These workstation-local receipts are not published evidence or independent verification. No raw environment, credentials, real session identifiers or private execution scripts are included in this delivery.

## Publication, CI, merge and source activation

The separately approved atomic commit `08bfa35e5bd3a9ab5c6fca7d8093d14f8f8758a8`, “Isolate account-copy test process inventory”, contains exactly the existing test and five change artifacts. [PR24](https://github.com/kecol/omarchy/pull/24) published that unchanged source against `quattro`. [Feature-head Tests 45098956445](https://github.com/kecol/omarchy/actions/runs/45098956445) and [translation checks 45098956444](https://github.com/kecol/omarchy/actions/runs/45098956444) passed. The PR body identified the outcome as the pre-commit handoff checkpoint, not a claim that publication had not occurred.

Separate merge approval produced `9aca54efe1c066fc00524de00d076861c44bf21a`, with parents `eca2500593229a428bf6928c5fed707c9229850e` and the feature commit. Postflight confirmed the exact reviewed tree. Automatic [post-merge Tests 45171286751](https://github.com/kecol/omarchy/actions/runs/45171286751), attempt 1, passed at that merge. Both Tests runs completed 454 test files without failures, with skipped checks in eight files. Both retained account-copy logs show the private-inventory entry, exit 0 and all six original checks without skips. These were distinct automatic new-head runs, not manual retries. The skipped files were `agent-model-recovery-native-test.sh`, `agent-openshell-native-tools-test.sh`, `brightness-display-apple-cache-test.sh`, `fontconfig-cjk-test.sh`, `hw-match-device-tree-test.sh`, `i18n-test.sh`, `kitty-config-test.sh` and `panel-open-budgets-test.sh`, all under `test/shell.d/`.

After separate source-integration approval, active `quattro` fast-forwarded from the base to the merge. Five exact overlapping untracked planning files were retained intact outside the checkout before incoming tracked copies took their place. All six incoming hashes and modes matched. Pending goal content and metadata, other tracked source/modes and 23 unrelated indexes were preserved; the active index intentionally advanced to the merged tree. No test, namespace, account/provider action, restart, package operation, migration or archive ran during activation. This test-only source integration changed no production runtime policy. Earlier failed CI and native/verifier/manifest attempts remain unchanged.

## Deferred investigation

The HOME-less provider-like neighbor/unchanged-parent comparison is DEFERRED AND UNPERFORMED by the owner's explicit scope decision. It is not a delivery prerequisite and was not marked complete or replaced by the safe checks. A live ambiguous process could be visible to host account discovery even inside a child PID namespace. Any future reproduction needs separate scope, approval and an environment that prevents interference with working host account operations. Do not boot a VM, provision users, weaken the detector or resume historical infrastructure work automatically.

## Delivery boundary and rollback

The delivered atomic scope is six files: the existing account-copy test and `.openspec.yaml`, `proposal.md`, `design.md`, `tasks.md` and `outcome.md` within this change. `skip_specs: true` remains appropriate for fixture tooling with unchanged production behavior contracts. No new product spec, shared runner, package, workflow or runtime policy is added.

At the pre-commit handoff, the active checkout remained at the base and the candidate stayed inactive. Subsequent separately approved source integration is recorded above. Pending `AGENTS.md` and `docs/project-goals.md` edits remain protected. This tracking closeout changes documentation and archive placement only; it runs no application tests, namespaces, account operations, package operations, migrations, providers or services.

Commit, publication, merge and source integration completed through their separate approvals. The owner approved this documentation-only archive with `skip_specs: true`; no main specification is created for the fixture. Archive placement does not renew runtime qualification. Commit/publication of this tracking closeout still require separate approval. No account-data migration, package operation, provider launch or restart is required by this change. Rollback restores only the fixture entry and reintroduces shared process inventory; it does not change production account handling. Container-shell closeout, plain Pi/Herdr choices, upstream assessment and historical VM/storage/executor investigations remain outside this delivery.
