# Fork work ledger

## Scope and interpretation

This is a partial curated starting record, assembled when OpenSpec was introduced on 2026-11-12. It is not a new validation run, a complete commit census, or a replacement for Git/PR history and the original evidence. Add missing milestones incrementally when their source and outcome have been reviewed.

The fork's central purpose is making Omarchy safe in the presence of coding agents. Branding and defaults are additional fork policy, not a substitute for that purpose.

Status meanings:

- **IMPLEMENTED SOURCE**: code/documentation exists or the stated source merge occurred; read its validation limits separately.
- **PARTIAL**: only the stated scope is established; unresolved failures remain.
- **PLANNED**: intended work, not implemented.
- **BLOCKED**: a prerequisite or approval is missing.
- **DEFERRED / NOT SELECTED**: not the current path; evidence remains preserved.

Do not turn these labels into automatic release, merge, provisioning, account, package/migration or activation approval. Do not fabricate archived OpenSpec changes or checked tasks for work done before this tracker existed.

## Existing agent-safety foundation

| Area | Status and scope | Source/reference |
| --- | --- | --- |
| Managed assignment workspaces and reviewed transfer back to canonical source | IMPLEMENTED SOURCE; protects the documented managed-task flow, not every possible host agent invocation. | `docs/managed-agents.md`; `bin/omarchy-task-*` and associated agent/workspace modules. |
| Rootless harness preparation and independent launch selection | IMPLEMENTED SOURCE; preparation, version/filesystem checks, authentication and runtime qualification are distinct. | `docs/managed-agents.md`; `default/agents/harness.py`; `containers/harnesses/`. |
| Instance observation, identity-bound diagnostics/closure and explicit terminal attachment | IMPLEMENTED SOURCE; status is observation, not an isolation audit, authentication decision or automatic termination policy. | `docs/managed-agents.md`; `default/agents/sessions.py`; `default/agents/status.py`. |
| Opt-in direct-command guards | IMPLEMENTED SOURCE; PATH-based friction with documented bypasses, not universal containment. | `default/agents/command-guards.py`; `manual/57-agent-command-guards.md`. |
| Agent Control Plane | PLANNED/DRAFT; its desired capabilities must not be treated as implemented merely because the design exists. | `plans/agent-control-plane.md`. |

## Recent integration and validation work

| Milestone | Recorded outcome | Still not established |
| --- | --- | --- |
| [PR11](https://github.com/kecol/omarchy/pull/11) integration/qualification work | Historical bounded package transaction, package census and cold-boot evidence retained for that tested snapshot. | Not qualification of later source/package/kernel snapshots. |
| [PR12](https://github.com/kecol/omarchy/pull/12) follow-up | PARTIAL; source work and scoped follow-up results retained. | The original CI failure cause remains unresolved; later scoped passes do not erase it. |
| [PR13](https://github.com/kecol/omarchy/pull/13) recorder stop status | Scoped stop-status correction retained. | The broader owned recorder-lifecycle rewrite remains DEFERRED and is not a completed fix. |
| [PR14](https://github.com/kecol/omarchy/pull/14), [PR16](https://github.com/kecol/omarchy/pull/16), [PR15](https://github.com/kecol/omarchy/pull/15) | Source merges and source-only activation reached `68d22643e4bd4df623977d125da7ce3b06f3a30f`. PR16 addressed FileView watcher/read ordering; PR15 was updated atop that fix. | This source-only activation was not a package upgrade, migration execution or reboot qualification. Historical visual evidence applies only to its recorded snapshots. |
| Larger upstream candidate | Inactive, uncommitted merge against pinned upstream `0e7530fb7c23fbf496d44f072ad64efaa7713d14`; recorded staged tree `9da22add71d26f659da692003374907effa300c7`. Policy preservation and scoped defect/forward-repair work were prepared. | No merge completion, publication, activation or full integrated release qualification. The forward repair was not executed live. New upstream commits are not included automatically. |
| Partition checks | Six bounded groups produced32 scoped checks after the original timeout was retained and investigated. | Not a full suite/CI pass; the original timeout and later whitespace failures remain historical evidence. |
| Pre-loader tracer design | NOT SELECTED for the revised route; selected source/design review and known gaps retained. | No tracer implementation, execution or runtime permission qualification is claimed. |
| Revised offline VM preparation | PARTIAL/OFFLINE ONLY:22 initial protocol/model test methods passed, then38 affected/new hardening methods passed. Staging's original21-method run had20 setup errors and one pass; after diagnosis/correction, only the20 errored methods were rerun and passed. | No VM, live transport, native consumer lifetime, GUI/backend, package coherence, power-loss durability or release qualification follows. These counts must not be summed into a new integrated suite result. |
| Guest bootstrap review | BLOCKED: existing helpers use incompatible networking/resources or startup/ownership/cleanup assumptions. No unchanged bootstrap was certified. | No guest mounting, provisioning, media/overlay creation, boot or application launch is approved by that review. |

## Evidence locator

Raw logs, media, failed runs, source snapshots and local receipts stay outside Git. On the originating workstation, portable locators include:

- `$HOME/Work/omarchy-upstream-candidate-20261111/REVIEW.md`: historical integration review and linked phase reports.
- `$HOME/Work/omarchy-upstream-candidate-20261111/vm-offline-design-01/QUALIFICATION.md`, `HARDENING.md` and `STAGING_QUALIFICATION.md`: exact offline test scopes, preserved failures and source receipts.
- `$HOME/Work/omarchy-upstream-candidate-20261111/vm-bootstrap-review-01/REVIEW.md`: latest bootstrap blockers.
- `$HOME/Work/omarchy-source-activation-20261111/REVIEW.md`: source-only activation scope.

These private local paths may not exist on another workstation. Their presence in this ledger is not public artifact publication or independent verification. Never copy private account/session settings, credentials, transcripts, identifying process/session data or raw desktop media into this tracker.

## Current direction

[`separate-agent-safety-layer`](../changes/separate-agent-safety-layer/proposal.md) records the preferred maintenance direction: reduce upstream coupling while preserving explicit agent-safety enforcement. Its first deliverable is an architecture inventory and one extraction proposal. Installing OpenSpec completed neither extraction nor the inventory. Tasks 1.1–1.3 now have a source-reviewed inventory and test/history evidence map in [`docs/agent-safety-boundaries.md`](../../docs/agent-safety-boundaries.md), including credential/session sharing, identity/closure, engine selection and desktop dispatch. Test source and the historical workspace report/ledger were reviewed without running tests or renewing qualification. Document links, boundary-row mapping and whitespace checks passed; no runtime execution or qualification occurred. Task 2.1 adds conditional layer classification and retained host connections for all boundary rows; no extraction was selected or implemented by that classification. Task 2.2 delivers [`plans/agent-safety-first-extraction.md`](../../plans/agent-safety-first-extraction.md): a proposed pure bundled-catalog reader that would remove two agent workflow imports of the desktop menu model while retaining the single catalog and caller-specific checks/failure behavior. Exact files/interfaces, focused future checks, rollback and coupling targets are documented; no extraction or application test ran. Task 2.3 source/document reconciliation is complete in the [review record](../changes/separate-agent-safety-layer/review.md). It checks implemented command families, mode/default/per-launch behavior, container diagnostics, workspace CLI/menu, Start Agent options/file reuse and distinct widget click actions; Q18 adds fixture-source coverage without test execution. Managed-agent claims about source isolation, review approval, audit/resource enforcement, close escalation and OpenShell were corrected; the control-plane document explicitly retains its stronger proposed status. All six documentation tasks are complete; user review was requested at that documentation checkpoint. No implementation, runtime qualification, archive or activation follows. See the [task list](../changes/separate-agent-safety-layer/tasks.md).

The user subsequently approved [extract-agent-catalog-reader](../changes/extract-agent-catalog-reader/proposal.md). Its [outcome](../changes/extract-agent-catalog-reader/outcome.md) records IMPLEMENTED SOURCE in the working tree: one pure catalog module, two targeted consumer edits and extensions to the existing two Python fixtures. Runtime UI-model imports in those consumers changed from two to zero; the single bundled catalog and caller-specific checks/failure behavior remain. Both approved focused suites passed once without skips (27 guard, 26 launcher and 19 menu methods); future-ID and label-fallback mutations failed semantically in disposable copies. This is parser/metadata/fixture-dispatch qualification, not live container, credential, graphical, full-suite/CI, hardware or release qualification. No activation, installation, commit/push or archive occurred. Existing safety gaps and the broader target architecture remain unresolved/proposed as documented.

After a separate source-review acceptance and explicit commit approval, `d2471ba1d` (`Extract bundled agent catalog reader`) committed only the three runtime files, two fixtures and the catalog-reader subsection of `docs/managed-agents.md`. Earlier OpenSpec setup/inventory/tracking and broader documentation edits remain uncommitted, as do the unrelated Containerfile edits. The commit uses the repository-local public `noreply` identity. Tested source hashes were rechecked without rerunning suites; no push, activation or archive occurred.

Do not resume the inactive merge or VM/bootstrap framework automatically. Keep those findings available without making that infrastructure a prerequisite for every useful fork change.
