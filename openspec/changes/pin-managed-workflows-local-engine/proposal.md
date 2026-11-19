# Proposal

Historical routing-only checkpoint: this document records the original options-only implementation and its planning or verification scope. Baseline behavior, preservation instructions, status and approval statements refer to that checkpoint, not current delivery. The [current contract reconciliation](design.md#current-contract-reconciliation) identifies the later safeguards that must remain in effect. The original [outcome](outcome.md) remains historical evidence, not renewed qualification.

## Why

The harness launcher already pins Podman to its local engine, but the legacy managed-runtime snapshot, audit-fix/task-stop actions and editor workspace backend invoke bare Podman. Ambient remote-engine defaults can therefore direct host-local workflow metadata and actions to a different engine; explicit locality removes this configuration-dependent mismatch without extracting a new framework or changing shared desktop code.

## What Changes

- Require explicit `podman --remote=false` selection for every Podman invocation in `bin/omarchy-agent-runtime-snapshot`, `bin/omarchy-agent-audit`, `bin/omarchy-task-stop` and `default/workspaces/manager.py`.
- Keep discovery and subsequent actions local across each scoped workflow, including workspace listing, checks, build/start, SSH endpoint/key discovery and both ordinary and failed-audit stop paths.
- **BREAKING for reliance on implicit remote defaults:** these Omarchy workflows will ignore remote-engine defaults instead of querying or acting on the selected remote engine. Their reviewed interfaces expose no remote-Podman option. Direct user Podman commands and the workspace's intentional Remote SSH editor connection are unchanged.
- Preserve caller-specific arguments, subprocess transport, output/state contracts, stop targets/grace periods, workspace storage and checks. Do not add an error-time remote fallback.
- Extend the existing inventory, task-workspace and workspace fixtures to detect missing locality selection with synthetic remote defaults and a fake executable; record focused outcomes only after separately approved implementation/execution.

This is a bounded engine-selection correctness/safety fix, not another module extraction or a claim of complete engine-access denial. In particular, the snapshot's empty-success behavior when Podman is unavailable, name-based legacy stop targeting, non-atomic admission and credential/network limits remain separate issues.

## Capabilities

### New Capabilities

- `managed-engine-selection`: Explicit local Podman routing for the named managed-runtime and editor-workspace workflows, with unchanged surrounding policies and no remote retry.

### Modified Capabilities

None. The repository currently has no main specs; this change introduces a narrow proposed behavior contract rather than certifying all existing runtime safety.

## Impact

Source review is against `0603b244ea2c67702d1cac1a0a5e6ce7e6f258c7`. The four runtime owners above, `test/shell.d/agent-inventory-test.sh`, `test/shell.d/task-workspace-test.sh`, `test/shell.d/fixtures/workspaces/test_manager.py`, and the directly relevant managed-agent/workspace/boundary documentation are the intended implementation scope. Existing harness/identity controllers already use explicit locality and need no refactor. No new public command, shared helper, package, image recipe, migration, state conversion, shell/QML change or new dependency is proposed.

The [boundary inventory](../../../docs/agent-safety-boundaries.md) identifies E1/O2/L5/C3 and the existing Q3/Q10 fixture limitations. Local host paths, procfs identities and loopback SSH supply the reason for locality; source review found no explicit remote-engine interface in these four owners. Fixtures do not establish actual Podman precedence, runtime confinement or remote-service denial. Native engine, GUI/VM, provider and release qualification remain unperformed.

The original approval covered creating these planning artifacts only. The user subsequently requested apply; the [outcome](outcome.md) records the implemented working-tree routing changes and three scoped fixture-suite results. Installation, activation, commits/pushes and archiving remain separately gated. The paused merge and VM/tracer work are not prerequisites and must not resume implicitly.
