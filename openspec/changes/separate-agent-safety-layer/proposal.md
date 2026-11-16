# Proposal

## Why

Upstream Omarchy is advancing faster than the current integration process, while repeated merge and validation work delays useful updates. The fork must reduce upstream coupling without weakening its purpose: making Omarchy safe in the presence of coding agents.

## What Changes

- Produce a source-grounded inventory of agent-safety guarantees, enforcement owners, upstream dependencies, current evidence and known gaps.
- Classify fork changes as upstream desktop base, safety enforcement, safety-related desktop integration, or fork defaults/presentation.
- Identify what can move into an independently maintained layer and what must remain a narrow upstream-facing patch. Packaging alone is not an enforcement boundary.
- Deliver one small extraction proposal with focused compatibility checks and rollback, rather than implementing the entire architecture at once.
- Keep urgent upstream fixes as a narrow parallel lane; do not promise that backport batches alone will catch up with upstream.

This first change is documentation and architecture inventory only. It is not implemented by installing OpenSpec. It does not approve code extraction, new packages, guest provisioning, a validation framework, merge completion or activation.

## Capabilities

### New Capabilities

None in this inventory-only change. `.openspec.yaml` declares `skip_specs: true`; no new runtime requirement is invented to satisfy tooling.

### Modified Capabilities

None. Runtime contracts remain unchanged. A later approved extraction must identify its affected capabilities and preserve their behavior explicitly.

## Impact

The inventory will reference the existing `bin/` commands, `default/agents/`, `containers/`, agent desktop plugin, managed-agent documentation, packaging/migrations and relevant tests. Existing source remains unchanged during this first deliverable.

Observed starting points include managed assignment workspaces and reviewed task apply, rootless harness preparation, identity-bound instance closure, metadata-only status observation, and opt-in PATH guards with documented bypasses. `plans/agent-control-plane.md` remains a draft, not proof of implemented enforcement.

The earlier inactive merge and VM/bootstrap prototypes remain historical or paused work. They are not dependencies that must be completed before this architecture inventory can start. See `../../history/work-ledger.md` for their scope and limitations.
