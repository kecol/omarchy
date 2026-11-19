# Proposal

## Delivery status

IMPLEMENTED SOURCE, qualified within the recorded limits, merged and source-active at `d3447839d7b53a2d04547e87b2eea74fa4b947a5`. The sections below preserve the original implementation plan and its pinned inputs. They do not describe an unimplemented current change. See the [delivery and current-status record](tasks.md#delivery-and-current-status) for publication, failed and passing CI, and separately approved source activation. Main-spec synchronization and archive are tracking operations, not additional runtime qualification or execution permission.

## Why

The selected bounded catalog adapter must recognize both the fork's legacy product rows and the inspected upstream namespace without weakening agent-safety callers. The completed [catalog-boundary proposal](../2026-11-19-define-agent-catalog-boundary/design.md) defines the contract, but its documentation-only tasks cannot track runtime implementation.

## What Changes

- Extend the existing pure `agentCatalog(raw)` reader to recognize exactly `setup.default.agent.<name>` and `agent.harness.<name>` product IDs.
- Retain source ordering, label fallback, malformed-input behavior and duplicate records. Keep both Python callers and their distinct validation/failure policies unchanged.
- Extend the existing guard/menu fixtures through actual reader transport with synthetic modern-format products, mixed namespaces and caller-specific refusal cases.
- Update only the bundled-catalog subsection of `docs/managed-agents.md` to describe supported forms and remaining schema coupling.

## Capabilities

### New Capabilities

- `bundled-agent-catalog`: Pure projection of the single bundled product catalog into ordered name/label records for caller-owned validation.

### Modified Capabilities

None. Runtime inventory availability, stop-target binding, launch policy, account/session handling and workspace behavior remain unchanged.

## Impact

Selected approach: option B from the prior comparison, chosen under the user's delegation and followed by the request to proceed. Stable shared metadata remains a possible later improvement, not a prerequisite or a second maintained list.

Expected implementation scope is one runtime file (`default/agents/catalog.js`), two existing Python fixtures and the catalog documentation subsection. There is no menu import, CLI/QML change, new dependency, package, migration or user-state conversion.

The implementation plan used fork `0a88b4f398e03bac581d652d579940f77e4fd7ed`; the known upstream form came from `c3c8acf1ef376d19c400464eab9bc382a8667c6f`. These were pinned planning inputs, not moving compatibility promises. Source and fixture inspection preceded the later focused and CI qualification recorded in the task file. This proposal records the selected behavior, not another architecture comparison.

The safety effect is preserved caller authority with additional product-metadata coverage, not stronger containment. The maintenance benefit is keeping known namespace adaptation inside the existing reader. Menu schema/location and future ID changes remain dependencies.

Planning creation does not execute this change. Implementation must use an inactive candidate after review of these artifacts. Focused tests, publication, merge, activation and archive retain their applicable approval gates. No live guard synchronization, agent/provider/engine/GUI/VM action or paused campaign is included.
