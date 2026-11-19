# Tasks

These tasks deliver the authorized documentation proposal only. They do not implement either representation. Runtime specifications are skipped because this change adds no runtime behavior. Owner selection and any later implementation/test/publication permission remain separate.

## 1. Define the contract and representation choices

- [x] 1.1 Define input authority, normalized records, ordering, label/error behavior and enforcement ownership; verify `design.md` against the real reader, both callers, the original extraction contract and the accepted architecture direction.
- [x] 1.2 Compare one shared semantic metadata source with a bounded menu adapter; verify `design.md` explains producer/consumer and delivery costs, exact proposed legacy/current recognition, duplicate-name behavior, rollback limits and the unresolved owner representation decision without introducing another maintained product list.

## 2. Compatibility and document review

- [x] 2.1 Define future compatibility checks at the existing real guard/menu reader-transport seams; verify each proposed case identifies a behavioral regression and distinguishes source review from unperformed tests, with retained caller-specific limits and no native/GUI campaign inferred.
- [x] 2.2 Validate this change with strict OpenSpec validation and review local links/headings, whitespace, public-path hygiene and edit scope; verify only the four new catalog-proposal artifacts were added, the preexisting assessment and tracked runtime/test/config files remain untouched, and no reader/application/native test or activation ran. Present the representation recommendation and required review decision. Strict validation passed with the expected `skip_specs` informational notice; 20 local links/heading anchors and whitespace/public-path checks passed. HEAD and the tracked worktree/index remain unchanged. No reader/application/native tests or activation ran.

## Workflow follow-up

- Review the proposed contract and choose a representation. Option B is recommended as a bounded first implementation, not as complete menu-schema independence; option A remains the long-term semantic ownership alternative.
- Before implementation, record the selected behavior, appropriate runtime specification and bounded unchecked implementation tasks through a separately approved planning update or linked change. Do not silently convert completed documentation tasks into completed runtime work.
- Obtain a separate implementation request and appropriate focused/native execution approvals. This proposal contains acceptance cases, not execution permission or a qualification waiver.
- Keep commit, upstream publication, merge, activation and archive separately scoped. Do not resume the paused merge or consumed native/storage campaigns.
