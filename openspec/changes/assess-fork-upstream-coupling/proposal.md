# Proposal

## Why

The fork needs an architectural decision before another upstream intake: which responsibilities should it own, and through which interfaces should those responsibilities connect to the upstream desktop? Selecting individually applicable commits does not answer whether the current ownership and dependency boundaries cause avoidable recurring adaptation.

## What Changes

- Produce a source-grounded upstream-coupling assessment, not an upstream commit-selection list or an implementation plan for a chosen extraction.
- Map current ownership, dependency direction, action authority, data/state contracts, installation assumptions and expected change propagation across the launcher, catalog/menu, desktop components, task/runtime backends, observation/controllers and delivery paths.
- Use concrete upstream changes as examples of architectural pressure. Separate Git path overlap, actual interface incompatibility, intentional fork policy and runtime qualification.
- Compare keeping current boundaries, retaining small explicit patches, introducing narrow adapters, separating components, separate packaging and seeking upstream interfaces. Include the costs and failure modes of each option.
- Record the target direction, protected behavior, staged decision points, evidence limits and unresolved owner choices in `design.md`. Distinguish owner acceptance of the overall direction from selection of a concrete interface or authorization to implement it.
- Preserve the completed catalog extraction and the current runtime-availability and stop-target contracts. Do not repeat earlier inventory work or reinterpret historical draft status as the current source state.

No externally observable behavior changes. This change sets `skip_specs: true`; it creates no runtime delta specification.

## Capabilities

### New Capabilities

None. The deliverable is an architectural assessment and decision aid, not a new runtime capability.

### Modified Capabilities

None. `managed-runtime-availability` and `managed-stop-target-binding` remain authoritative and unchanged. Additional existing behaviors and limits remain documented in the managed-agent reference and source inventory.

## Impact

### Planning scope

Only this change's CLI-generated metadata, proposal, design/assessment and task record may change. Source comparison covers current fork `0a88b4f398e03bac581d652d579940f77e4fd7ed`, upstream `c3c8acf1ef376d19c400464eab9bc382a8667c6f` and common ancestor `6194f4606c585da8b839b87df9120b7d796afedf`. These are pinned analysis inputs, not moving compatibility promises.

The starting evidence is the [boundary inventory](../../../docs/agent-safety-boundaries.md), [managed-agent reference](../../../docs/managed-agents.md), [work ledger](../../history/work-ledger.md), [first extraction design](../../../plans/agent-safety-first-extraction.md) and current source. Historical inventory/classification is reused and reconciled with later deliveries, not rewritten or treated as new test execution.

### Agent-safety effect and upstream benefit

The immediate effect is better architectural decisions, not stronger enforcement. The intended future benefit is reducing how often upstream presentation, launch or delivery changes require edits to unrelated safety owners. Fewer shared-file edits are useful only if the existing refusal paths, explicit Host semantics, project/home scopes, credential separation, target validation and evidence requirements remain connected to every relevant entrypoint.

### Non-goals

Do not import commits, resume the old merge, change runtime or user configuration, select a new broker/service, move code into packages/plugins, redesign credentials or lifecycle policy, close known admission/approval gaps, or introduce a generic compatibility/test framework. No provider, engine, doctor, GUI, VM, package, migration or storage/kernel/tracer action is included. Commit, publication, implementation, runtime qualification, activation and archive require their own later scopes.

### Decision status

The user accepted the overall direction: retain coherent fork-owned backends and one delivery unit, adapt selected upstream-facing integration boundaries, preserve independent safety presentation and defer separate packaging, repositories or a new daemon. The user also approved recording that acceptance and the guiding references in this change's existing artifacts.

The first boundary, concrete interfaces and compatibility details remain unresolved. No existing feature retirement, implementation, upstream intake, publication or activation is authorized. Accepting the direction does not establish that the target architecture is implemented or newly qualified.
