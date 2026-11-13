# Design

## Context

See [proposal.md](proposal.md) and the approved [first extraction proposal](../../../plans/agent-safety-first-extraction.md). The current consumers import `MenuModel.js` only for bundled agent projection. Guard and picker subprocess policies differ and must remain separate.

## Goals / Non-Goals

**Goals:** remove two runtime UI-model dependencies while preserving the single data catalog, projection order, names/label fallback, validation and failure behavior.

**Non-Goals:** change JSONC grammar, strengthen malformed-catalog handling, normalize subprocess policy, alter command/menu/widget behavior, move other backends or activate the checkout.

## Decisions

- Export only `agentCatalog(raw)` from `default/agents/catalog.js`. Keep the current whole-line-comment/trailing-comma transformations, flat/wrapped object handling, valid object-row filtering, exact ID regex, enumeration order and `label || id` fallback. The function performs no I/O, environment reads or execution.
- Keep file reads and JSON subprocess transport in the two callers. Guard discovery maps records to names; the picker receives records. Do not change timeouts, cwd/stdin/environment, byte/record limits, definition/registration merging, installed-command checks or picker validation.
- Return an empty list for the parser failures that currently produce empty rows. Guard discovery can continue through definitions/registrations; the picker still refuses empty input. No error-time fallback to the UI model or Host execution is added.
- Extend the existing two Python fixtures. Use real preinstalled Node, synthetic menu trees and actual reader/caller code. Compare synthetic projections with the original UI parser as a test oracle only. Include actual future-product discovery without a fabricated Node response. Keep existing mocked control-flow cases and their narrower interpretation.
- Demonstrate sensitivity with an omitted future-ID projection or changed label fallback in a disposable candidate copy. A missing new module on the base tree is not the meaningful negative control for this behavior-preserving refactor.

A new fixed product list would lose future entries. Importing the UI parser from the new module would preserve the unwanted dependency. Moving the full menu model or centralizing caller policy would exceed the reviewed scope.

## Risks / Trade-offs

- Limited parser duplication can diverge from UI parsing → synthetic parity cases preserve the current contract, including transformations inside strings. Future grammar changes require explicit compatibility review.
- Tests can accidentally run shims or reach live state → use an existing installed Node executable and scratch HOME/catalog trees; do not install prerequisites or invoke real agents/engines/providers.
- Passing fixtures can overstate safety → report metadata/dispatch compatibility only. No native UI, provider, container enforcement, full-suite/CI or release claim follows.
- Partial file delivery can leave consumers without their module → deliver the three runtime files coherently and preserve checked-subprocess failure; do not hide installation inconsistency with a fallback.

## Migration Plan

No user-state migration or runtime activation belongs to this change. Source rollback restores both consumers and their fixture edits from the same pre-extraction revision before removing the new module. Do not reset unrelated work, synchronize live guards, rebuild images, rewrite migrations or change mode/account/workspace state. Deployment, publication, merge and archival require separate approval.
