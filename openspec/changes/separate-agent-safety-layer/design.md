# Design

## Context

See `proposal.md` for motivation and scope. Current agent logic spans command dispatch, Python policy/metadata modules, rootless container recipes, QML integration and installation/default policy. `docs/managed-agents.md` already distinguishes runtime controls, observations and bypassable PATH friction. The existing control-plane plan is a draft and must not be treated as the current architecture.

The first deliverable is an inventory plus a proposed extraction, not a runtime refactor. This separation allows upstream work to resume without first completing a new VM or generic validation system.

## Goals / Non-Goals

**Goals:**

- Make each claimed safety guarantee traceable to an enforcement owner, public source path, threat boundary, upstream dependency, evidence and limitation.
- Separate observed current behavior from intended future behavior.
- Propose one small change that measurably reduces merge conflicts or repeated qualification work without weakening a safety contract.

**Non-Goals:**

- No automatic extraction, packaging change, permission expansion, feature retirement, guest boot or desktop takeover.
- No claim that a status label, PATH wrapper, container default or planning document establishes complete containment.
- No retroactive promotion of source-only, simulated or partial historical results into full qualification.

## Decisions

### Inventory before extraction

Create `docs/agent-safety-boundaries.md` as a reviewed matrix. Start from the actual commands/modules and their documented limits, rather than converting the control-plane draft into assumed implementation. Each row identifies the actor, protected resource, enforcement owner, integration surface, failure behavior, focused verification and unresolved gaps.

### Separate responsibilities without assuming packaging solves safety

Classify each fork-specific boundary into enforcement, desktop integration, default/presentation or upstream base. An independently packaged module is only a maintenance unit unless it also owns an actual runtime boundary. Keep necessary enforcement patches in the fork where upstream extension points cannot preserve the contract.

Alternatives rejected as the default strategy: an indefinitely growing backport queue; dropping agent safety to follow upstream; another generic validator before defining the first extraction.

### Deliver one proposal, then stop for review

Write `plans/agent-safety-first-extraction.md` with one preferred boundary, exact files/interfaces, unchanged failure behavior, compatibility checks, rollback and a rough before/after coupling estimate. Do not move code in this inventory change. A new implementation change requires approval after that proposal is reviewed.

### Evidence remains scoped

Reuse existing focused checks and public source/history where applicable. Record missing coverage instead of starting broad suites, VM campaigns or backend/account activity. Keep private raw artifacts outside Git and link only sanitized evidence identifiers or portable local references.

## Risks / Trade-offs

- A module boundary could preserve labels but lose enforcement. Mitigation: map actual entrypoints and failure behavior, not just filenames or UI controls.
- The inventory could become another large planning effort. Mitigation: cover the existing safety entrypoints, select one extraction and stop; defer unrelated desktop cleanup.
- Upstream extension points may be insufficient. Mitigation: retain a documented small patch or propose an upstream interface; do not weaken the contract to remove a diff.
- Existing tests may overstate a boundary. Mitigation: include their scope, sensitivity and unresolved historical failures in the matrix.

## Migration Plan

This change adds documentation only. There is no runtime deployment, data migration or marker update. Rollback removes or reverts only this change's documents; existing agent commands, settings, sessions and packages remain untouched.

Any future extraction must provide its own compatibility and rollback plan and receive separate implementation approval. Publication, merge completion and activation remain independent gates.
