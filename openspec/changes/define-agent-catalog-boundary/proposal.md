# Proposal

## Why

The owner accepted selective integration-boundary adaptation and chose catalog definition as the next planning step. The existing agent-owned reader removes desktop-code imports but still derives product identity from menu placement; upstream's move from `setup.default.agent.*` to `agent.harness.*` exposes that remaining data dependency.

## What Changes

- Define the proposed catalog boundary: logical product identity and display metadata, separate from installation, Container support, account access, observation and launch permission.
- Specify inputs, normalized output, ownership, ordering, failures, side-effect exclusions and the two callers' distinct validation contracts.
- Compare a stable shared metadata source with a bounded menu-compatibility adapter. Give an implementation recommendation and its limits without treating it as approved.
- Define proportionate future compatibility checks in the existing guard/menu fixtures, including real reader transport for synthetic future products and retained failure behavior.
- Record the owner's remaining representation decision and the exact conditional scope for a later implementation proposal.

This is a documentation-only contract proposal, not implementation of a new catalog or behavior change. It sets `skip_specs: true`; no runtime delta specification is created. A later approved behavior change needs its own appropriate specification and unchecked implementation tasks.

## Capabilities

### New Capabilities

None in this documentation change. The proposed catalog contract is a design for review, not a delivered runtime capability.

### Modified Capabilities

None. The existing runtime-availability and stop-target-binding specifications remain unchanged. This proposal does not tighten malformed-catalog handling or change launch policy.

## Impact

### Authorized scope and status

Only this change's metadata, proposal, design and task record may change. The existing accepted [architectural assessment](../assess-fork-upstream-coupling/design.md) and earlier [catalog-extraction outcome](../extract-agent-catalog-reader/outcome.md) remain reference inputs, not files to rewrite. The earlier reader extraction already exists at current fork `0a88b4f398e03bac581d652d579940f77e4fd7ed`; it must not be repeated.

Source inspection uses upstream `c3c8acf1ef376d19c400464eab9bc382a8667c6f` as a pinned comparison, not a moving compatibility promise. Existing fixture source was inspected; no application tests, Node reader invocation, agent, engine, provider, GUI or VM ran for this proposal.

### Agent-safety effect and upstream benefit

The immediate effect is an explicit maintenance contract and decision aid, not stronger enforcement. A later implementation should confine known representation changes to a pure projection while preserving guard discovery, picker refusal, installed-only checks and explicit Host/Container dispatch. Catalog membership must not become permission to execute or read accounts.

Stable shared metadata could remove menu-tree identity coupling but requires coordinated producers and consumers. A bounded adapter could address the observed upstream rename with a smaller change, while deliberately retaining a documented representation dependency. `design.md` compares those costs rather than calling either option complete isolation.

### Non-goals and later gates

No runtime, test-source, bundled-menu, user-configuration, launcher, status/controller, packaging, installation or migration edits. Do not introduce another manually maintained product list, execute menu actions to discover products, reuse the installer/default setter as a catalog API, or broaden process recognition from catalog membership.

This authorization does not select a representation, permit implementation/test execution, import upstream commits, publish an upstream interface proposal, commit, merge, activate or archive. No feature retirement or paused native/storage/merge campaign is included.
