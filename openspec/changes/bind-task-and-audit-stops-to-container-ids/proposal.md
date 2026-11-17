# Proposal

## Why

Task stop and audit repair still pass mutable container names to Podman even though the checked runtime snapshot supplies full container IDs. Audit also associates policy failures by instance label, so a repeated label can select another container for stopping; fixing these two action-binding gaps advances the fork's agent-safety purpose without coupling the desktop to another controller framework.

## What Changes

- Bind `omarchy task stop` and `omarchy agent audit --fix` stop requests to full, validated container IDs from the successful snapshot. Keep container names for display only; never resolve a missing ID through a name.
- Validate the complete applicable stop plan before any stop or dependent lifecycle-state write. Reject missing, malformed or duplicate target IDs rather than skipping rows or reporting success.
- Associate audit failures with the specific observed container ID. Refuse the entire repair plan if a failed row lacks an instance label or its instance label identifies multiple containers in that snapshot. Do not let one row's failure select another row through a shared label.
- Preserve explicit local-engine routing, caller-visible command options, existing stop grace/escalation policy and partial-failure handling. Preserve unavailable-observation refusal.
- Extend the two existing fixture suites and update current reference documentation after implementation. Keep historical evidence unchanged.

**Compatibility change:** malformed or ambiguous repair targets will fail before mutation, where current code can stop by name, skip a row or associate another row's failure. No CLI route, registry schema or successful JSON field schema change is proposed.

## Capabilities

### New Capabilities

- `managed-stop-target-binding`: exact container-ID targeting and unambiguous audit finding-to-action association for task stop and audit repair.

### Modified Capabilities

None. The existing `managed-runtime-availability` specification continues to govern producer completeness and unavailable-observation refusal. This change adds a consumer action-binding contract rather than replacing that specification.

## Impact

### Source-reviewed baseline

Review baseline: `19eea4aa53de29b8106bd0e58d5482778ccf5ae9`. This is a source-confirmed risk, not evidence of an incident on the user's machine.

- `bin/omarchy-task-stop` resolves one assignment, selects snapshot rows by assignment label, writes `stopping`, stops nonempty container names and then writes `stopped`.
- `bin/omarchy-agent-audit` keys failed checks by instance label and later stops matching rows by name. Its registry updates are best effort after stop success. Its advisory quick doctor can perform engine/write operations; executing audit is not part of this planning review.
- `bin/omarchy-agent-runtime-snapshot` already projects the inspected engine ID as `container_id`. It need not change.
- `test/shell.d/task-workspace-test.sh` supplies a stop fixture without `container_id`; `test/shell.d/agent-inventory-test.sh` uses a placeholder ID and asserts name-based stopping. These fixtures need realistic synthetic IDs and behavioral regressions, not just new expected argv strings.

### Intended implementation scope

Runtime owners: only `bin/omarchy-task-stop` and `bin/omarchy-agent-audit`. Tests: only their existing two shell fixture files. Current references: `docs/managed-agents.md` and the prospective status supplement in `docs/agent-safety-boundaries.md`; later delivery tracking may update `openspec/history/work-ledger.md` under its own approved scope. No new dependency, generic controller, helper framework or desktop integration is required. Keeping enforcement in these existing CLI owners limits upstream integration work.

### Non-goals and limits

Do not change workspace-manager stop, session close, overview stop, launch/admission, image preparation, policy measurements, credentials, packages, migrations, translations or branding. Do not add confirmation, retries, force, deletion, query deadlines or TERM-only semantics. Existing default stop behavior can escalate to KILL.

Container IDs prevent mutable-name retargeting; they do not authenticate labels, constrain malicious same-user engine authority, bind a process incarnation, prevent concurrent launches or make observation/action and registry updates transactional. Native rename/name-reuse behavior and failure reporting remain unverified for this proposed change.

### Approval and validation boundary

This approval covers these planning artifacts and metadata only. No application test, doctor, engine operation, worktree creation, implementation, commit, publication or activation is authorized. Future implementation must use a separately approved non-dev-linked candidate. Focused behavioral checks, meaningful negative controls, targeted native checks in a disposable VM and PR/CI are required before active integration, unless a specific exception is reviewed under `docs/openspec.md`. The prior native invocation is consumed; this proposal does not renew it or resume paused infrastructure work.
