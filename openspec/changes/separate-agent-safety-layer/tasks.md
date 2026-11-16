# Tasks

Status: DOCUMENTATION COMPLETE; awaiting user review, not implementation approval. Tasks 1.1–1.3 and 2.1 have a source-reviewed inventory, test/history evidence map and conditional layer classification in `docs/agent-safety-boundaries.md`; relative file links, boundary-row mapping/classification and document whitespace checks passed. Existing test source was inspected, not executed. This is source/document verification only, not runtime qualification. Task 2.2 delivers `plans/agent-safety-first-extraction.md`, proposing one catalog-reader extraction with exact interfaces, unchanged behavior, focused future checks, rollback and coupling targets; it is not implemented. Task 2.3 source/document reconciliation is recorded in `review.md`, including implemented command/menu/widget behaviors absent from earlier prose and corrections to managed-agent/draft claims. No application tests ran and no extraction was implemented. Runtime behavior does not change in this documentation-only change.

## 1. Current safety boundaries

- [x] 1.1 Trace managed task start/apply, workspace assignment, launch mode/guards and harness preparation entrypoints; deliver source-linked rows in `docs/agent-safety-boundaries.md` that distinguish enforcement from launch friction and observation.
- [x] 1.2 Trace credential/session exposure, instance identity and closure, engine access and desktop action dispatch; add protected resources, explicit user actions, failure behavior and unresolved coverage to each relevant matrix row.
- [x] 1.3 Map existing focused tests and historical findings to those rows; verify that the document names unsupported paths and does not equate simulations, metadata or isolated passes with runtime containment.

## 2. First extraction recommendation

- [x] 2.1 Classify the source-linked rows as upstream base, safety enforcement, desktop integration or defaults/presentation; document which changes can move and which must remain patched without weakening the named contracts.
- [x] 2.2 Deliver `plans/agent-safety-first-extraction.md` for one small boundary, naming exact files/interfaces, unchanged safety behavior, focused compatibility checks, rollback and expected reduction in upstream coupling; do not implement it.
- [x] 2.3 Review both delivered documents against `docs/managed-agents.md` and the draft control-plane plan, reconcile contradictions and leave future-runtime claims explicitly proposed; record the review outcome in this change before marking it complete.

## Workflow follow-up

- Request review of the first extraction proposal before creating or applying an implementation change.
- Keep urgent upstream fixes scoped independently; do not silently resume the old merge or VM/bootstrap campaign.
- Archive this documentation change only after explicit approval. Publication, merge completion, provisioning, package/migration execution and activation remain separately gated.
