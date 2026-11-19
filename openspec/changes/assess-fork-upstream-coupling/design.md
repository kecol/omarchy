# Fork architecture and upstream-coupling assessment

## Context

**Assessment complete; the owner accepted the overall direction. Concrete interfaces remain undecided, and implementation is not authorized or performed.** See [proposal.md](proposal.md) for the authorized documentation-only scope. This document answers whether architectural boundaries should change before upstream intake. It does not rank individual commits for import.

### Pinned inputs and evidence limits

| Input | Revision or source | Interpretation |
| --- | --- | --- |
| Current fork | `0a88b4f398e03bac581d652d579940f77e4fd7ed` | PR18 and its documentation closeout are integrated. This is the source baseline, not a new native qualification. |
| Upstream `quattro` | `c3c8acf1ef376d19c400464eab9bc382a8667c6f` | The live upstream ref matched the available local object during the preceding read-only review. Future upstream revisions need a new comparison. |
| Common ancestor | `6194f4606c585da8b839b87df9120b7d796afedf` | Basis for distinguishing upstream changes from fork changes. |
| Existing architectural inventory | [Boundary inventory](../../../docs/agent-safety-boundaries.md), [managed-agent reference](../../../docs/managed-agents.md), [work ledger](../../history/work-ledger.md) | Reused historical mechanisms and evidence limits, reconciled with current source and later deliveries. |
| Earlier extraction | [Catalog-reader design](../../../plans/agent-safety-first-extraction.md) and [outcome](../extract-agent-catalog-reader/outcome.md) | The extraction exists in current source. Earlier preparation-time statements about unperformed activation do not mean it needs implementation again. |
| Durable behavior | [Runtime availability](../../specs/managed-runtime-availability/spec.md), [stop-target binding](../../specs/managed-stop-target-binding/spec.md) | Preserve these current contracts. This assessment changes neither specification. |

Evidence consists of source reads, Git trees/diffs/history, caller traces, existing test-source references and previously recorded results. No application test, agent, provider, engine, doctor, desktop, VM or package command ran for this assessment. Earlier non-mutating patch-applicability checks are not architectural or behavioral qualification. No modern merge simulation or complete conflict census was performed. No raw accounts, sessions, credentials or machine-specific reports were collected.

### What the Git comparison does and does not establish

At these inputs, the fork has 191 ancestry-only commits and upstream has 368. Of the upstream-only commits, 38 are merges and 330 are non-merges. `git cherry` identifies eleven patch-equivalent non-merge commits already represented in the fork. Patch equivalence is not a native test result, and absence of an equivalent patch does not mean every behavior is missing.

Using path comparison without rename detection, the fork differs from the common ancestor in 385 paths: 239 added, 143 modified and three deleted. Upstream differs in 1,784 paths. Both sides changed 117 paths; 25 of those have identical final tree entries and 92 differ. Twenty-seven shared-touch paths still differ outside `default/i18n/` and `test/`. These are scope measurements, not 92 conflicts, 27 unsafe files or a measured conflict rate. Nonoverlapping changes can still alter a dependency or an installed system.

Four disjoint current source families illustrate how much implementation is already additive:

| Selected family | Current files | Files absent at the same path upstream | Shared-touch paths since the common ancestor |
| --- | ---: | ---: | ---: |
| `bin/omarchy-task-*` | 15 | 15 | 0 |
| Workspace backend, image assets and `bin/omarchy-workspace-*` | 12 | 12 | 0 |
| `default/agents/` excluding bundled `skills/` | 18 | 18 | 0 |
| Harness recipes and `bin/omarchy-harness-*` | 18 | 18 | 0 |

These 63 files are a selected footprint, not an exhaustive safety inventory. Their absence upstream supports retaining coherent backend ownership. It does not prove semantic independence from terminal, engine, package, filesystem or desktop interfaces.

## Guiding references for later development

| Reference | Role and limits |
| --- | --- |
| [AGENTS.md](../../../AGENTS.md) and its linked task guides | Define the fork purpose and area-specific development procedures. Read the applicable guide before changing that area. |
| [OpenSpec reference](../../../docs/openspec.md) | Defines planning and approval boundaries. Accepted architecture direction and task completion do not authorize execution or publication. |
| [Safety-boundary inventory](../../../docs/agent-safety-boundaries.md) and [managed-agent reference](../../../docs/managed-agents.md) | Identify current enforcement owners, state/credential contracts, evidence and known limits. Do not convert scoped protections into universal containment claims. |
| [Runtime-availability specification](../../specs/managed-runtime-availability/spec.md) and [stop-target-binding specification](../../specs/managed-stop-target-binding/spec.md) | State the existing behavior that later integration changes must preserve. These specifications remain unchanged. |
| [Menu reference](../../../docs/menu.md), [shell architecture](../../../docs/omarchy-shell.md) and [lifecycle dispatcher](../../../docs/lifecycle-dispatch.md) | Describe existing integration contracts. A menu overlay, QML facade or platform dispatcher is not automatically an appropriate agent-safety boundary. |
| [Testing reference](../../../docs/testing.md) and the applicable guides linked from AGENTS.md | Define focused checks and native/graphical evidence requirements. Source inspection and historical results do not renew runtime qualification. |
| [Work ledger](../../history/work-ledger.md) and [catalog-extraction outcome](../extract-agent-catalog-reader/outcome.md) | Preserve prior deliveries and unresolved work. Reconcile historical preparation status with current source rather than repeating completed implementation. |
| [First-extraction design](../../../plans/agent-safety-first-extraction.md) and [control-plane draft](../../../plans/agent-control-plane.md) | Supply earlier reasoning and alternatives. They are historical design context, not approval of every proposed interface or a description of fully implemented architecture. |

Before a later proposal changes scope or design, identify any important new reference or conflict with these sources and explain its consequence to the owner. Do not silently resolve a conflict by weakening a safety contract. This index does not replace reading the relevant source and task guide.

## Goals / Non-Goals

**Goals:** identify avoidable change propagation; distinguish maintenance units from security boundaries; recommend where to keep, isolate, adapt or consolidate responsibilities; expose decisions and costs before code changes.

**Non-goals:** zero fork differences, an immediate separate repository/package, a whole-agent framework rewrite, mandatory Container mode, new authenticated-controller guarantees, a commit intake list, or closing known safety gaps by documentation. No feature or protection is designated removable without owner approval.

## Current ownership and dependency direction

```text
Upstream-facing entrypoints and presentation
  agent/default-agent/prompt, menu data, keybinding, usage panel
                    |
         fork launch selection and validation
                    |
       agent-exec --> runner / image / doctor / policy
                    |
          assignment or ad-hoc project + HOME scope

Task CLI --> state + clone/preflight/audit --> launch path
Task apply --> regenerated patch --> explicit source write

Standalone execution widget --> on-demand status presentation
  explicit action --> fixed terminal --> backend revalidation

container-stop --> sessions --> status identity/query primitives
status report --> workspace registry API + desktop association
```

Arrows denote source dependencies or dispatch, not a new authority boundary. The public launcher is an integration owner; the runner and controllers own actual argument construction, identity checks and lifecycle actions. Moving a label or file does not move those checks automatically.

### Boundary assessment

| Boundary | Current owner and interface | Architectural pressure | Recommended disposition and preservation condition |
| --- | --- | --- | --- |
| A. Harness command construction and launch policy | [`omarchy-agent`](../../../bin/omarchy-agent), [`agent-exec`](../../../bin/omarchy-agent-exec), [`default-agent`](../../../bin/omarchy-default-agent) | One shared launcher combines upstream product arguments/local-model support with fork mode, picker, installed-only, recovery, account, cwd and dispatch semantics. Upstream additions require understanding both responsibilities. | **Adapt the seam, retain policy authority.** Define the command-construction versus policy/dispatch boundary before moving code. Do not execute a whole upstream launcher as an assumed pure command builder. |
| B. Product discovery and menu placement | [`catalog.js`](../../../default/agents/catalog.js), guard `discover`, picker `agent_catalog`, bundled menu JSONC | Runtime UI-model imports were removed, but discovery still identifies products by menu-tree IDs. Presentation can change the discovered product set. | **Isolate semantic catalog identity from menu layout.** Retain one source of product metadata and existing caller validation. A bounded menu adapter is an interim option, not complete independence. |
| C. Fork menu contributions and guard reads | [`omarchy-menu.jsonc`](../../../default/omarchy/omarchy-menu.jsonc), [`MenuModel.js`](../../../shell/plugins/menu/MenuModel.js), [`menu-agent-mode`](../../../bin/omarchy-menu-agent-mode) | Start/workspace/mode entries share upstream data. A single `omarchy-agent-mode` guard-reader addition also connects the shared evaluator to fork state. | **Keep small explicit connections until an equivalent contribution interface exists.** Do not copy shipped policy into mutable user overlays solely to make the source diff smaller. |
| D. Safety presentation versus provider/account UI | [`ExecutionDefault.qml`](../../../shell/plugins/agents/ExecutionDefault.qml), `execution/`, `overview/`, shared [`Panel.qml`](../../../shell/plugins/agents/Panel.qml) | The standalone widget is already separate from usage collectors. Optional combined label and launch-button/keyboard edits still require adaptation when upstream changes its large account/local-model panel. | **Keep independent presentation; contain the combined integration.** Preserve both current surfaces unless the owner explicitly retires one. A plugin move must preserve host API, IPC identities, layout settings and action semantics. |
| E. Observation versus action primitives | [`status.py`](../../../default/agents/status.py), [`sessions.py`](../../../default/agents/sessions.py), [`container-stop.py`](../../../default/agents/container-stop.py), [`desktop.py`](../../../default/agents/desktop.py) | Controllers import process/query primitives from the same module that assembles the report. That module imports workspace registry and desktop adapters. A UI-oriented reorganization can therefore affect controllers. | **Consider an internal primitive/report split when this code next changes.** This is internal maintainability work, not the first upstream-friction intervention: these files are absent upstream. Do not consolidate distinct stop policies. |
| F. Task state, admission and promotion | [`task-start`](../../../bin/omarchy-task-start), [`agent-state`](../../../bin/omarchy-agent-state), task apply/cleanup/archive owners | These largely additive files depend on the shared launch seam and one registry/workspace lifecycle. Directory extraction alone supplies no atomic admission or immutable review approval. | **Keep a coherent fork-owned unit.** Preserve state paths/schema, clone boundaries, explicit apply, failure propagation and current specifications. Separate hardening proposals from maintenance extraction. |
| G. Workspace/editor bridge | [`manager.py`](../../../default/workspaces/manager.py), workspace wrappers/assets, launch-menu reuse of workspace APIs | Editor launch settings, SSH identity/host-key checks, registry paths and real bind mapping form a contract. The launch picker imports the manager and workspace menu helpers directly. | **Retain the backend; make its read-only reuse explicit.** A later module boundary must keep registry reads from creating state, starting containers or loading private keys. Renaming folders or relying on editor profile names is insufficient. |
| H. Startup, tool wrappers and Host maintenance | [`env-bootstrap`](../../../default/bash/env-bootstrap), [`init`](../../../default/bash/init), [`guard-path.sh`](../../../default/agents/guard-path.sh), account-add and mise hook configuration | Guard precedence depends on startup/mise ordering; new terminal services can rebuild PATH. Account sign-in intentionally removes guards for its Host child. Generic upstream startup changes can alter coverage without changing backend code. | **Retain narrow explicit hooks and document ordering.** Do not replace the helper connection with an optional load that silently disappears. Preserve explicit Host maintenance and opt-in guard coverage, not a stronger prohibition. |
| I. Credential/account/instruction sharing | Account home/exec/state/add/transfer, provider-specific shared-file lists, separate container HOME and OpenShell prototype | Upstream account/instruction features can deliberately write or share state. A generic catalog or UI adapter must not import those effects into discovery, status or Container preparation. | **Keep credential-bearing flows distinct.** Adapt their deliberate Host entrypoints individually. Do not merge Host account selection with isolated container HOME or treat shared instructions as containment. |
| J. Source/asset delivery and versions | `$OMARCHY_PATH`, sibling Python imports, `default/agents/definitions`, `containers/harnesses`, public Pi recovery asset, workspace image/editor files | Every helper assumes a coherent installed source/asset closure. Independent code releases would introduce versions, ordering and partial-install failure paths not currently designed. | **Keep one delivery unit initially.** Independent maintenance ownership does not require a package/repository split. Packaging follows a demonstrated contract and rollback need, not folder aesthetics. |
| K. Host reliability, CI and non-agent fork policy | [`omarchy-update`](../../../bin/omarchy-update), [CI workflow](../../../.github/workflows/test.yml), background handoff and existing shell access protections | Some differences protect lifecycle/evidence behavior rather than agent dispatch. Removing them does not become safe because the desktop is called the upstream base. | **Maintain an explicit preservation set.** Retire a patch only after an equivalent upstream behavior and its scope are reviewed. Do not classify all shared-file changes as cosmetic. |

## Concrete change-propagation evidence

### 1. The catalog extraction removed code coupling, not data ownership coupling

Current `catalog.js` is pure and both Python consumers import it instead of `MenuModel.js`. It accepts the existing JSONC subset and selects IDs matching `^setup\.default\.agent\.[a-z0-9-]+$`. The upstream menu now uses `agent.harness.*`. Therefore replacing only the bundled menu with that upstream form changes the catalog projection, despite neither Python consumer nor desktop parser code changing. The picker rejects an empty catalog; guards can continue through definitions/registrations and do not gain complete catalog coverage. This is a source-derived incompatibility, not a newly executed failure.

The architectural concern is that menu ancestry is acting as a product-discovery interface. Merely adding another regex can restore compatibility for one menu version but leaves that dependency implicit.

Separate four concepts before choosing a representation:

| Concept | Authority and meaning | Must not be inferred from it |
| --- | --- | --- |
| Product catalog | Logical harness names and display labels | Installation, authentication, image readiness or permission to launch |
| Container definition/recipe | Supported runtime/executable and reviewed build metadata | Every Host product having a Container implementation |
| Installed/readiness result | Caller-specific current availability | A persistent product catalog or permission to install/sign in |
| Process recognizer/action identity | Bounded known process forms and current identity evidence | Trusting a new product merely because it appears in the menu |

`status.py` has its own process-name/entry recognition set. Replacing that with all future catalog names would broaden an observation/controller input, not remove harmless duplication. The single-catalog objective must not erase distinct authority lists.

### 2. Launcher adaptation is a responsibility issue, not just a missing flag

Upstream account/desktop launch changes use `--app-id=...`; the current fork parser rejects that option and emits a fixed agent app ID at its terminal handoff. Upstream also adds Qwen local-overlay behavior. The fork launcher additionally owns explicit mode/directory selection, installed-only resolution, automatic picker exclusions, Pi recovery/one-shot/session handling, account pins, child guard removal and Container dispatch.

Replacing the fork launcher with upstream code loses behavior. Wrapping the complete upstream launcher is not automatically an alternative: that script can resolve another agent, construct Host-specific overlays, select account homes, install/launch through existing paths and exec a terminal before a fork backend sees a plan. The fork needs an identifiable pre-execution seam, not an assumption that an upstream entrypoint is a pure argv function.

Existing `agent-exec` already validates the selected definition, expected executable and supported runtime. Retain that boundary. A future command-construction interface should supply bounded data, not executable menu text or credential contents; the fork must still validate it and own final mode/runtime/cwd dispatch. Exact API and compatibility behavior are not selected here.

### 3. Desktop integration has an existing low-coupling path

The standalone `omarchy.agent-execution` widget loads mode state and the on-demand overview without instantiating account/usage collectors. The usage panel has separate login streams and launch/prompt/account actions. Its optional combined mode label and extra launch navigation remain edits inside upstream `Panel.qml`, which is undergoing substantial local-model and sign-in changes.

The maintenance improvement is to keep the independent component usable and bound combined integration to explicit small responsibilities. It is not permission to remove the optional combined label, change click mappings, start collectors implicitly or move authentication into the overview.

The [shell contract](../../../docs/omarchy-shell.md#plugin-manifest) distinguishes trusted built-ins and third-party facades. Plugins remain unsandboxed in one QML process. Moving a component to an external plugin is therefore neither a new security boundary nor a drop-in host-API equivalent. Preserve manifest/IPC identities, settings, terminal handoffs and bounded action-token validation before proposing such a move.

### 4. Stable-looking files can carry deliberate policy differences

Upstream's current update path tolerates shell-restart failure and does not retain the fork's explicit non-1 pending-migration failure handling. Its CI workflow differs from the fork's pinned bootstrap image/sandbox policy and successful-run artifact retention. Those are intentional behaviors to preserve or replace with reviewed equivalents, not accidental launcher coupling.

Likewise, upstream translation watching and plugin-rescan work may replace earlier fork repairs. The direct shell comparison already contains the common rescan logic; remaining background-handoff code serves another purpose. Retirement requires comparing responsibilities, not deleting every patch in a shared file or treating whole-file identity as the only acceptable result.

### 5. Internal maintenance boundaries do not imply interchangeable controllers

`container-stop.py` imports `sessions.py`, which imports `status.py`; `status.py` provides `Query`, `Proc`, container projection and report assembly. It dynamically imports desktop association and the workspace manager's read-only registry functions. The launcher menu separately imports workspace UI helpers and the workspace manager.

These are real maintenance dependencies. They justify considering narrower internal contracts if UI/report changes repeatedly affect controller work. They do not justify merging task-stop, audit repair, exact-session close, overview TERM-only stop and workspace stop into one generic controller. Their selectors, confirmation, escalation, state writes and partial-failure policies intentionally differ.

## Decisions and alternatives

### Assessment decisions already made

1. Judge architecture by responsibility and change propagation, not the behind count or directory names.
2. Reuse the existing boundary inventory; record only current-source reconciliation and new architectural consequences here.
3. Treat the two main specs and documented behavior/limits as preservation inputs. A new module/package does not strengthen their guarantees.
4. Keep this assessment documentation-only. The owner subsequently accepted the overall direction; concrete interface decisions and implementation approval remain separate.

### Accepted direction, not an implemented architecture

**Adapt selected integration boundaries; do not start with a wholesale backend rewrite or separate distribution.** Much of the backend is already independently owned in source. The highest-value change is making the shared launcher/catalog/UI/startup connections explicit and small enough that upstream presentation or product changes do not require policy owners to change in lockstep.

```text
Upstream desktop and product behavior
              |
   narrow, reviewed compatibility connections
              |
Fork-owned policy / workflow / identity / runtime units
              |
  explicit local engine, storage and terminal adapters

Independent safety presentation --> bounded reports / explicit actions
Upstream account UI            --> separate credential-bearing actions
```

This is a maintenance target. It introduces no broker, privilege boundary, network policy or new runtime API in this change.

| Option | Benefit | Cost or failure mode | Assessment |
| --- | --- | --- | --- |
| Keep current arrangement unchanged | Least immediate implementation risk; existing behavior/evidence remains applicable to its recorded scope. | Recurring semantic review in shared launcher/menu/panel and hidden catalog/state assumptions remain. | Valid baseline and rollback reference, not the preferred long-term integration boundary. |
| Maintain a small explicit patch set with named contracts | Keeps the existing delivery model and necessary mandatory connections. Easier to review which upstream changes cross policy boundaries. | Requires disciplined ownership and review; upstream can still change the seam. | Recommended immediate maintenance model. Do not build a patch-management framework for it. |
| Add a narrow compatibility adapter | Localizes menu/product normalization or argv translation when callers can consume a checked contract. | Adds a maintained contract and can merely hide coupling if it parses unstable presentation or executes whole upstream launchers. | Recommended selectively, with a change-propagation example and explicit failure behavior for each adapter. |
| Seek stable upstream metadata/launch contribution points | A shared semantic interface can avoid repeatedly adapting UI layout changes. Benefits are not tied to this fork alone. | Upstream may decline or choose another interface; compatibility and tests still cost maintenance. | Preferred direction for genuinely generic seams. No upstream acceptance is assumed; retain a small reviewed local adapter if necessary. |
| Move all fork features to an external plugin | Smaller apparent shared source footprint. | Current plugin trust/host APIs differ; user state and IPC can change; account and observation authority may become mixed. QML remains unsandboxed. | Do not use as the first architectural intervention. Independent presentation can be evaluated separately. |
| Split runtime code into another package/repository now | Separate release ownership and a clearer distributable identity. | Does not itself remove launcher/menu/startup connections. Adds asset-path, version, install-order, rollback and mandatory-availability problems. | Defer until interfaces and coherent delivery have demonstrated value. |
| Centralize every lifecycle path or introduce a daemon | Could reduce repeated transport code. | Risks changing confirmation/escalation/partial-state contracts and adds authority, protocol and service-lifetime complexity. | Not justified by this friction evidence. Do not make it a prerequisite. |
| Remove fork features or protections to match upstream | Reduces differences directly. | Changes the product purpose or user-visible behavior. | Not an architectural optimization without explicit feature/policy retirement decisions. |

### Catalog boundary choices

A bounded adapter accepting the known old/new menu namespaces is a possible low-disruption transition. It must define duplicate/ordering/label/error behavior, preserve future-product discovery and caller-specific validation, and not add a hidden product allowlist or Host fallback. It still needs maintenance when upstream changes the representation.

A stable product-metadata source used by both menu presentation and fork callers would address the underlying responsibility more directly. That could be an upstream data file or a strictly read-only structured interface; neither exists as an agreed contract in this assessment. Do not add a second manually synchronized fork catalog or replace discovery with a runtime/account query. Do not assume user menu overlays have the same trust or discovery scope as bundled data.

Recommendation: make the semantic contract explicit first; compare the cost of one bounded compatibility adapter with an upstream metadata contribution. Do not mandate the final representation before that decision.

### Launcher boundary choices

Prefer identifying a pure command-construction seam plus fork-owned policy/dispatch over copying whole upstream command tables or treating the upstream launcher as an opaque subprocess. Preserve public commands while evaluating that split. An upstream contribution is one route, not a dependency that blocks every maintenance fix. A small local semantic patch may be less costly than a new protocol if the seam stays small.

The interface needs to distinguish presentation fields such as app ID from logical agent identity, selected executable, runtime, cwd, preparation, account selection and Host-only overlay behavior. `--check` and installed-only operations must remain separate from installation, model-service probing and authentication. A new adapter must not turn an unsupported Container request into Host, pass Host overlay paths into a container, or alter saved defaults.

### Internal boundaries to retain or improve later

The fork's command router changes are chiefly group descriptions/registration; the existing longest-prefix routing already discovers command files. Keeping those small table entries can be cheaper and clearer than inventing a command-plugin registry. The menu evaluator's explicit mode-reader entry likewise has a performance role. A zero-diff shared file is not the acceptance criterion.

The launcher menu imports both workspace UI helpers and the workspace manager at module load. Independent packaging could therefore make a basic launch picker depend on a missing workspace package even before the user selects Workspace Files. A later split must either keep that dependency coherent or define a narrow, explicitly available workspace-selection interface; it must not guess registry contents or silently reinterpret a workspace as another directory.

The existing [lifecycle dispatcher](../../../docs/lifecycle-dispatch.md) is an example of fixed operation names and explicit required/optional failure contracts. It is not an agent integration API: it has different platform, root-ownership and privilege rules. Do not reuse its optional no-op semantics for a required launch-policy check or add an arbitrary hook bus merely to avoid a few source edits.

Keep task/state/apply, runtime/image/preparation and workspace/editor behavior coherent in the current delivery. Treat process/query identity primitives as potential internal shared code, separate from report/presentation assembly, without changing who revalidates before action. This could improve safety review when those modules evolve, but it has less direct upstream-overlap evidence than the launcher/catalog seams. Keep credentials, account sharing and OpenShell prototypes outside generic report/discovery interfaces.

## Preservation criteria for any later proposal

- Keep absent-mode Host semantics, invalid-mode refusal, explicit Host maintenance, per-launch overrides, installed-only resolution, cancellation and automatic-picker exclusions. Container mode remains a launch preference plus scoped workflow checks, not host-wide denial.
- Keep task clone versus ad-hoc/live workspace access, assignment/ad-hoc/editor HOME scopes, user-data paths, account pins/sharing and existing menu/widget actions. Do not trade compatibility for silent feature retirement or state reset.
- Preserve runtime-unavailable versus genuine-empty results and all dependent refusals; full-ID task/audit targeting, whole-plan validation, association refusal and partial-failure handling remain intact.
- Keep backend identity and confirmation checks. UI metadata, application IDs, labels, package names and API facades are not authorization.
- Preserve child-local engine selection/environment contracts per caller. Existing wrappers have different filtering/coverage; this analysis does not certify one universal sanitizer or justify erasing those differences through a shared helper.
- Keep preparation consent, reviewed metadata/assets, immutable image selection, validation before promotion and refusal without unconfined fallback. Existing-image reuse and tag rollback retain their recorded limits.
- Keep event-driven readers and existing startup/guard performance expectations. A compatibility layer must not add provider probes, state-changing discovery, idle processes or polling to repair missing interfaces.
- Preserve the current CI/update protections, published migration history, stricter active permissions and the existing source/asset closure until an equivalent delivery contract is approved.

Known gaps remain separate: same-user authority, PATH bypasses, non-atomic admission/mode reads, mutable reviewed-patch construction, incomplete observation and unqualified external credential/network mediation. Architectural separation does not close them.

## Risks / Trade-offs

- **Apparent modularity without reduced propagation**: a new folder or parser can retain the same unstable upstream semantics. Require a concrete before/after dependency example, not only fewer lines in shared files.
- **Hidden change in authority**: a pure catalog becomes a readiness probe, or a report helper becomes a controller. Keep data collection, validation and effects explicitly separate; preserve backend revalidation.
- **Optional safety implementation after packaging**: a missing addon can expose an upstream Host path. Any later package design must preserve the current required checks without inventing a permissive fallback; intentional Host operation must still work under its existing prerequisites.
- **Unbounded compatibility promise**: supporting every upstream version, API or plugin would create another framework. Pin the tested interface versions and refuse or clearly report unsupported contracts.
- **Duplicated metadata or product command tables**: maintaining parallel lists creates drift. Prefer one authoritative source and explicit adapters; accept bounded parser compatibility only with its documented cost.
- **Moving merge work into user configuration**: generated menu/plugin overlays can reduce the source diff while increasing upgrade and recovery risk. Do not overwrite user overlays, layouts or instructions to claim lower friction.
- **Removing useful upstream functionality**: rejecting local-model or account work solely because it touches a shared launcher hides rather than resolves the interface question. Preserve visible gaps and evaluate the integration contract; no feature is silently disabled here.
- **Confusing source evidence with qualification**: path counts, patch equivalence and source traces establish structure, not native runtime, graphical, provider, performance or release behavior. Later checks must match the changed boundary.

## Decision sequence and possible migration plan

This sequence is a proposal for later decisions, not approved implementation tasks:

1. Use the accepted overall direction: pursue selective integration-boundary adaptation while retaining the current single delivery unit. Review each later boundary proposal against this ownership model and its preservation criteria.
2. Choose the first bounded boundary proposal. Catalog identity is the smaller data-only option; launcher planning/dispatch is the more central but higher-risk option. Their priority is an owner decision, not a selected commit batch.
3. Specify the chosen boundary's inputs, outputs, supported versions, state/side effects, required availability and refusal behavior. Name every current caller, public route and affected fixture before code changes.
4. Compare one concrete upstream change before and after the proposed boundary. Require that unaffected policy owners no longer need coordinated edits, without losing their checks.
5. Implement only after a separate proposal/apply approval in an inactive candidate. Reuse existing focused checks; add only the regression that distinguishes the old coupling or lost guard. Native/graphical qualification depends on the actual behavior changed, with separate execution approval.
6. Review benefits and costs before expanding to the panel, internal primitive split or packaging. Do not make the complete target architecture a prerequisite for a useful bounded improvement.
7. Revisit upstream intake after the boundary strategy is chosen. Decide separately whether to use selective backports or a fresh full merge; neither is authorized here.

For rollback, preserve coherent caller/backend/assets versions and existing user state. A future metadata/launcher migration needs a reviewed inverse or compatibility period; removing the new backend before its callers are restored can create bypasses or broken launches. Restoring older safety code can reintroduce known weaknesses and cannot undo engine actions or state writes. Rollback remains separately approved, not automatic.

## Evidence needed to choose and evaluate an implementation

| Decision or claim | Available evidence | Specific missing evidence / later acceptance criterion |
| --- | --- | --- |
| Most backend code needs separate packaging to reduce conflicts | Selected additive families and their current path independence; existing coherent `$OMARCHY_PATH` resolution | No measured packaging benefit. Show reduced cross-owner adaptation plus a complete asset/version/update/rollback contract before selecting this option. |
| A catalog seam can isolate presentation changes | Pure reader and two real caller adapters; old/new menu-ID mismatch; existing catalog parity/dispatch fixture source | Choose one authoritative metadata contract. A future compatibility check must preserve discovery, ordering, caller refusals and no account/engine effects when layout changes. |
| A launcher seam preserves policy while taking upstream product changes | Current shared responsibilities and existing `agent-exec` boundary; app-ID/local-overlay examples | Define the pre-effect seam. Future checks must retain Host/Container/check/installed-only/recovery/cwd/account behavior and no fallback; inspect every known caller, not only a desktop tile. |
| Independent widget maintenance removes panel adaptation | Current standalone widget and lazy overview; optional combined-panel edits | Owner must decide whether combined placement remains required. Preserve API/settings/IPC/action contracts and obtain actual graphical checks if the UI changes. |
| Splitting status internals improves controller independence | Actual import chain and workspace/desktop adapters; existing identity/controller fixtures | No current conflict-rate benefit is measured. A future change must preserve the primitive semantics and keep different stop controllers distinct. |
| Upstream equivalents can retire reliability patches | Current direct source comparisons and earlier scoped evidence | Compare each behavior and dependency at the selected revisions, then qualify the affected boundary. Similar titles or patch equivalence alone do not renew runtime evidence. |
| The target architecture reduces maintenance effort | Concrete source-level change-propagation cases | Track future required shared-file edits, policy-owner co-edits, compatibility failures and review effort. Do not claim percentages or elapsed-time savings from this snapshot. |

Existing evidence groups Q1–Q18 in the [inventory](../../../docs/agent-safety-boundaries.md#boundary-to-test-map) identify relevant fixture mechanisms and exclusions. They are a source map, not a newly run suite. No new validation harness, tracer, VM bootstrap or broad test campaign is proposed by this assessment.

## Owner decision register

| Decision | Recommendation offered for review | Status |
| --- | --- | --- |
| Overall direction | Retain a coherent fork-owned backend and single delivery; adapt a few explicit upstream-facing seams. | Accepted by the owner; no concrete interface or implementation authorization. |
| First boundary | Compare a smaller catalog contract change with the broader launcher command-construction seam before selecting one. | Owner priority unresolved. |
| Metadata representation | Prefer a semantic shared source; a bounded old/new menu adapter is a possible transition. | Upstream feasibility and acceptable local maintenance cost unresolved. |
| Combined usage-panel integration | Preserve both existing surfaces unless the owner chooses a reviewed alternative. | No feature retirement authorized. |
| Packaging / separate repository | Defer until boundary contracts demonstrate a release/ownership benefit. | No package or repository split selected. |
| Eventual upstream synchronization | Decide after architectural priorities; do not treat the old paused merge or the behind count as the target architecture. | Selective versus full synchronization remains a later delivery decision. |

The owner accepted the overall direction, not a complete implementation design. The remaining choices do not block completion of the assessment, but they must be resolved before the affected implementation is proposed. The next decision is which boundary to address first. Acceptance does not start code changes, commit intake, publication or activation.
