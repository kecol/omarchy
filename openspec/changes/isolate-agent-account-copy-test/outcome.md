# Outcome

## Status and recommendation

IMPLEMENTED SOURCE, inactive, uncommitted and unpublished. The owner approved a documentation-only delivery handoff and formal deferral of unsafe historical-process reproduction. Recommend one atomic commit containing the existing test change and these change artifacts, followed by separately approved publication and automatic new-head CI. This recommendation is not commit, publication, merge, activation or archive permission.

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

The historical [Tests run 44922393670](https://github.com/kecol/omarchy/actions/runs/44922393670) remains failed. Its log shows unknown-home refusal before the interrupted-replacement exit-78 checkpoint, but identifies no candidate process or lifecycle state. The isolated fixture result does not prove historical parallel interference, a zombie mechanism or harmless flakiness. New-head full CI has not run for this candidate. Namespace admission in the actual CI image remains a publication-time compatibility check; missing prerequisites must fail clearly, not trigger installation, skipping or fallback.

## Failures and evidence handling

The initial static option lookup failed because its manual parser did not decode escaped hyphens. A separately approved documentation-only correction passed without changing source or rerunning parsing checks.

Native attempt 01 failed in its verifier because it required the literal word `namespace`, while Bubblewrap emitted `pidns`. The original logs, missing final automated case verdict, driver failures and service exit remain unchanged. A separately approved retained-log review checked the exact intended diagnostic, exit status, no body pass markers, source mutation, resource receipts and owned cleanup. That review accepts the named operation separately; it does not reclassify the failed attempt.

The first retained-evidence preflight found one manifest mismatch: the manifest hashed `postflight.log` while that redirected log was empty, before its final write. All other original manifest bindings match. The flawed manifest and finalized log remain preserved. The final review adds a manifest of finalized original files and creates its own self-excluding manifest only after redirected writers have exited. Those additive observations do not retroactively repair historical provenance.

Private evidence remains under `$HOME/Work/omarchy-account-copy-isolation-implementation-01/`, `$HOME/Work/omarchy-account-copy-isolation-native-01/`, `$HOME/Work/omarchy-account-copy-isolation-retained-review-01/` and `$HOME/Work/omarchy-account-copy-isolation-retained-review-02/`. These workstation-local receipts are not published evidence or independent verification. No raw environment, credentials, real session identifiers or private execution scripts are included in this delivery.

## Deferred investigation

The HOME-less provider-like neighbor/unchanged-parent comparison is DEFERRED AND UNPERFORMED by the owner's explicit scope decision. It is not a delivery prerequisite and was not marked complete or replaced by the safe checks. A live ambiguous process could be visible to host account discovery even inside a child PID namespace. Any future reproduction needs separate scope, approval and an environment that prevents interference with working host account operations. Do not boot a VM, provision users, weaken the detector or resume historical infrastructure work automatically.

## Delivery boundary and rollback

The proposed atomic scope is six files: the existing account-copy test and `.openspec.yaml`, `proposal.md`, `design.md`, `tasks.md` and `outcome.md` within this change. `skip_specs: true` remains appropriate for fixture tooling with unchanged production behavior contracts. No new product spec, shared runner, package, workflow or runtime policy is added.

The active dev-linked checkout remains at the base, with its runtime/test files unchanged. Pending `AGENTS.md` and `docs/project-goals.md` edits, existing indexes and file modes remain protected. Only planning copies are reconciled in the active checkout; the test implementation stays inactive. This handoff runs no application tests, namespaces, account operations, package operations, migrations, providers or services.

Commit and publication require separate approval. Review automatic new-head CI without retrying the original failed run. Merge, active-checkout integration and archive remain separate gates. No account-data migration, package operation, provider launch or restart is required by this change. Rollback restores only the fixture entry and reintroduces shared process inventory; it does not change production account handling. Container-shell closeout, plain Pi/Herdr choices, upstream assessment and historical VM/storage/executor investigations remain outside this delivery.
