# Proposal

## Why

Guard discovery and the launch picker load the general desktop menu model to read agent names/labels. Implement the already reviewed [catalog-reader proposal](../../../plans/agent-safety-first-extraction.md) to remove those two code dependencies without weakening the fork's existing safety or changing command/menu/widget behavior.

## What Changes

- Add one pure agent-owned CommonJS catalog projection; keep the bundled menu as the single catalog.
- Replace only the two Python consumers' embedded Node imports/projections.
- Extend their existing fixtures for parser parity, actual reader transport, future products and unchanged refusal/limit behavior.
- Run the two approved focused suites and record scoped results/negative controls.
- Update references to distinguish implemented source from the earlier proposed architecture.

The user approved source implementation and the two focused suites after the documentation review. Activation, installation, commits/pushes and archiving remain excluded. This tracking change does not expand that approval.

## Capabilities

### New Capabilities

None. The new internal module preserves existing behavior; `skip_specs: true` declares a pure refactor rather than inventing runtime requirements.

### Modified Capabilities

None. Preserve current limited JSONC parsing, per-caller validation/environment/limits, differing empty-catalog behavior and all retained integration contracts.

## Impact

One new runtime file (`default/agents/catalog.js`), targeted edits to `command-guards.py` and `launch-menu.py`, their two existing Python fixtures and the relevant documentation. No menu/QML, public command, startup, package, image, migration or user-state changes. Fixture passes do not qualify runtime containment, authentication, native UI, full CI or release behavior.
