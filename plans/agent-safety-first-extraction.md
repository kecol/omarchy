# First agent-safety extraction proposal

## Status and decision

**IMPLEMENTED SOURCE — scoped fixture checks passed; not activated or deployed.** This document originally delivered task 2.2 of [separate-agent-safety-layer](../openspec/changes/separate-agent-safety-layer/proposal.md). After user approval, [extract-agent-catalog-reader](../openspec/changes/extract-agent-catalog-reader/proposal.md) implemented the reader and two consumer edits. The [implementation outcome](../openspec/changes/extract-agent-catalog-reader/outcome.md) records actual checks and limits. The approved design below remains the compatibility/rollback record, not independent runtime qualification.

Select one boundary: **the bundled agent-catalog projection used by command-guard discovery and the agent launch picker**. Move that responsibility behind an agent-owned pure JavaScript module. Keep one authoritative catalog in the bundled menu data. Keep the existing guard and launch validations in their current owners.

This is a maintenance boundary, not a new isolation boundary. It addresses the G1/T4 integration dependency described in the [boundary inventory](../docs/agent-safety-boundaries.md). It does not extract the entire safety layer or satisfy the stronger draft [Agent Control Plane](agent-control-plane.md).

## Why this boundary first

Before extraction, two Python consumers started Node scripts that imported [`shell/plugins/menu/MenuModel.js`](../shell/plugins/menu/MenuModel.js):

- [`command-guards.py`](../default/agents/command-guards.py), in `discover(root, extra)`, selects names from `setup.default.agent.*` entries before combining definitions, explicit registrations and installed-command checks.
- [`launch-menu.py`](../default/agents/launch-menu.py), in `agent_catalog()`, selects names and labels from the same entries before validating picker records and checking mode-specific availability.

Both need catalog data, not UI routing, search, translations, package guards or rendering. Changes to the general desktop menu module can therefore break guard synchronization and launch selection even when catalog semantics have not changed. A separate data reader removes that runtime code dependency without moving workspace/credential/lifecycle checks or changing the shared desktop parser.

Do not select a whole-widget or whole-`status.py` extraction first. Widget extraction needs a trusted-host API/capability review. `status.py` supplies identity/query primitives to action controllers as well as observations. Those larger boundaries would require more compatibility work than this metadata projection.

## Exact proposed source scope

This table records the approved source scope. The implementation outcome distinguishes delivered source and fixtures from unperformed rollout/native qualification.

| File | Proposed change | Interface retained |
| --- | --- | --- |
| `default/agents/catalog.js` — new | Export the pure CommonJS function `agentCatalog(raw)`. Own the limited bundled-menu syntax and agent name/label projection described below. No top-level or function-level filesystem, process, environment, network or state access. | Input is menu text; output is ordered catalog records. It does not select an execution mode or validate agent definitions. |
| [`default/agents/command-guards.py`](../default/agents/command-guards.py) | Replace only the embedded Node script's UI-model import and projection with `catalog.js` plus `agentCatalog(raw).map(record => record.name)`. Keep the current read of the bundled menu. | `discover(root, extra)`, the names-only JSON subprocess output, its validation/limit, definition/registration merge and installed-command resolution remain unchanged. |
| [`default/agents/launch-menu.py`](../default/agents/launch-menu.py) | Replace only the embedded Node script's UI-model import and projection with `catalog.js` plus `agentCatalog(raw)`. Keep the current read of the bundled menu. | `agent_catalog()`, its `{name, label}` JSON subprocess output, record/label validation, availability checks, saved-default behavior and cancellation remain unchanged. |
| [`test/shell.d/fixtures/agent-command-guards-test.py`](../test/shell.d/fixtures/agent-command-guards-test.py) | Extend the existing fixture with real installed-Node catalog checks and a synthetic future-catalog discovery case that does not mock the Node result. Retain the existing mocked control-flow cases with their narrower interpretation. | Use scratch HOME/state/catalog trees and the fixture's installed-Node selection. Do not run mise, agent binaries or engine commands to discover products. |
| [`test/shell.d/fixtures/agent-menu-test.py`](../test/shell.d/fixtures/agent-menu-test.py) | Extend the existing catalog checks to exercise the real reader with synthetic menu text, retaining caller validation and environment assertions. | Do not open gum/desktop panels, read live accounts or launch an agent. |
| [`docs/managed-agents.md`](../docs/managed-agents.md), [boundary inventory](../docs/agent-safety-boundaries.md), this proposal | After a separately approved implementation, record the actual reader interface and source/evidence outcome. Keep proposed versus implemented status explicit. | Existing claims and limitations must not become stronger merely because the reader moved. |

No changes are proposed to `MenuModel.js`, the bundled menu/catalog data, Bash startup, `bin/` entrypoints, QML, image recipes, mode/account/workspace state, packaging, installation scripts or migrations. The new module stays under `$OMARCHY_PATH/default/agents/`; independent packaging is not part of this first step. If implementation requires expanding that scope, stop for review rather than adding an installer, parser framework or compatibility fallback.

## Reader contract

### Inputs, projection and ordering

The caller continues reading only `$OMARCHY_PATH/default/omarchy/omarchy-menu.jsonc`. It does not read user menu overlays, project configuration, credentials, provider state or runtime discovery results for the catalog. Existing definition discovery in the guard caller remains separate.

`agentCatalog(raw)` must reproduce the current consumers' projection of `MenuModel.parseMenuJsonc(raw)`:

1. Preserve the current limited JSON-with-comments syntax: strip whole-line `//` comments and apply the current trailing-comma transformation before JSON parsing. This is not a full JSONC grammar; do not add inline/block comment support or silently replace the parser with a different grammar.
2. Accept the current flat object form or the existing object-valued `items` form. Preserve fallback to the outer object when `items` is not an accepted object. Ignore non-object/null/array row values as the current parser does.
3. Iterate accepted rows in the same JavaScript object enumeration order. Select IDs using the exact existing pattern `^setup\.default\.agent\.[a-z0-9-]+$` and obtain `name` from the last ID segment.
4. Return records containing only `name` and `label`, with the existing `label || id` fallback. Do not coerce a truthy non-string label to text: the launch caller must continue rejecting it; the guard caller currently needs only the name.
5. Do not interpret, return or execute `action`, `when`, `checked`, `disabled`, provider, alias or translation fields. Do not import the desktop UI model at runtime.

The implementation should copy only the required syntax/row-selection behavior, not the general menu model. Preserve its license/attribution obligations. The data-format contract is deliberately owned here after extraction; future desktop parser changes do not automatically redefine the agent reader.

### Caller-owned checks and failures

Do not centralize the two callers' policies while extracting the reader:

| Caller | Preserve unchanged |
| --- | --- |
| Guard discovery | Node timeout of five seconds, current stdin/cwd behavior, removal of `NODE_OPTIONS`/`NODE_PATH`, one-MiB result limit and at-most-256 list check. Retain `safe_name`, infrastructure exclusions, bounded/checked definition reads, conflict refusal, explicit registration merge and installed-only resolution outside the guard prefix. The guard caller's broader inherited environment remains unchanged; this module is not an environment sandbox. |
| Launch picker | Node timeout of five seconds, repository cwd, current environment allowlist, nonempty at-most-128 catalog check, name/duplicate/printable-label validation and label length of at most 80. Preserve mode-specific readiness, explicit unavailable saved defaults and cancellation without implicit launch/default saving. |
| Both | A missing/unreadable module or menu file, Node failure or timeout must still propagate through the existing checked-subprocess error path. Do not fall back to the UI parser, cached/stale data, a hard-coded product list or direct Host execution. Preserve each caller's JSON response type. |

**Existing limitation to retain:** malformed or non-object menu text currently becomes an empty row list through `parseMenuJsonc`. Guard discovery permits an empty catalog and can still use definitions/explicit registrations; the launch picker rejects an empty catalog. This proposal preserves that difference. It does not newly promise fail-closed catalog coverage or repair malformed-catalog handling. Any stricter rule needs a separately reviewed behavior change, not an undocumented refactor adjustment.

The existing textual transformations can also affect sequences inside strings. Compatibility must cover that behavior rather than claiming a standards-compliant parser. If exact parity cannot be preserved in this small reader, stop and revise the proposal; do not relax the contract to finish extraction.

## Safety and integration behavior that must not change

- Keep the menu data as the single product catalog. Newly added matching entries must remain discoverable without a new hard-coded product allowlist or definition.
- Keep G1 as opt-in PATH friction with its documented bypasses. No installed binary is replaced; generated guard ownership/conflict rules and explicit Host maintenance semantics remain in the existing backend.
- Keep G2's Bash/mise initialization and guard-PATH handling. A new metadata module does not replace those host connections.
- Keep T4/M1's launcher dispatch, mode validation, saved/override behavior and refusal paths. Catalog presence does not mean an agent is installed, prepared, authenticated or safe to launch.
- Keep task/workspace binds, policy/resource flags, image selection, credential/session sharing and identity-bound close/attach/stop operations untouched. Do not add a provider/engine probe to the reader.
- Keep all user data/configuration names, public commands and installed-path resolution unchanged. No data conversion, registry regeneration, account operation, image rebuild, guard enable/sync or migration is needed merely to replace the reader.

## Additional entrypoint compatibility from task 2.3

The [implemented entrypoint supplement](../docs/agent-safety-boundaries.md#implemented-entrypoint-contracts) was checked against command, menu and widget source, not only existing prose. The reader extraction must also preserve these caller-visible contracts:

- Keep terminal picker eligibility, default ordering, unavailable-default presentation and cancellation. Keep explicit-agent/check/managed/one-shot/recovery paths outside the automatic picker.
- Keep the full Start Agent flow: per-launch Host/Container selection, explicit clone/live access, default-No terminal review, private recent-project handling and retained clones after later failure. Workspace Files must still select the same existing files without starting/attaching to an editor container or changing either home/lifecycle.
- Keep Workspaces as a distinct create/reopen-and-open-VS-Code workflow with its existing review, warnings, explicit image-build requirement and retained state after editor failure. The reader does not supply new workspace policy.
- Keep `default agent NAME` save-and-launch behavior separate from per-launch selection. Container recipe refusal must precede saving or invoking a Host installer; later launch failure must not be presented as an automatic rollback of the saved default.
- Keep the standalone mode widget's left-click menu/right-click overview, the usage icon's right-click launch picker/middle-click refresh and its optional label's left-click-only mode action. The new reader must not start observation/usage/authentication services or reinterpret saved Container mode as mandatory Host denial.

These contracts require no expansion of the three-runtime-file extraction scope. Existing picker/menu fixtures cover part of the behavior through synthetic dispatch; real widget clicks, editor/container activity and provider behavior remain unqualified. Source review does not authorize running those paths.

## Focused compatibility plan

These are the approved compatibility checks; the implementation outcome records their actual execution. They were **not tests run during the original inventory/proposal**. Use synthetic inputs and existing fixtures. Do not start a broad suite, VM, native desktop, engine, provider or account campaign.

Before adding a test, name its breakage: a future catalog entry disappears from guard discovery; name/order/label projection changes; parser differences admit/reject different rows; or replacing the reader bypasses a caller's refusal/validation path. Avoid snapshots of the full product list, exact product counts and source-string greps as proof of behavior.

1. Compare the candidate reader against the current UI parser's agent projection on synthetic flat/wrapped catalogs: whole-line comments, trailing commas, missing/falsy/truthy-invalid labels, irrelevant IDs, invalid row types, enumeration order and malformed/empty/top-level-array inputs. Include syntax-like text inside labels. Use the old parser only as a compatibility oracle in tests, not a production dependency.
2. Exercise the real guard discovery function with the actual new reader and a scratch bundled catalog containing a future product, no product definition and an installed inert executable. Confirm discovery includes the product without executing it. The existing future-catalog case mocks the Node result, so it does not cover this parsing/transport behavior by itself.
3. Exercise the launch catalog function through its actual Node script/reader on synthetic catalog data. Retain tests for invalid/duplicate/control-character records and the restricted subprocess environment. Keep separate mocked picker cases to prove cancellation and unavailable-default behavior; do not call those real UI qualification.
4. Check missing module/file, nonzero Node exit, timeout and oversized/invalid responses through the existing caller seams. Preserve guard-only output-byte bounds and the launch caller's record/label limits; do not add a new shared byte cap as an undocumented behavior change. Preserve the deliberately different empty-catalog outcomes. Do not treat a new module import failure on the old tree as the meaningful negative control: show that a deliberately omitted future-ID projection or altered label/row rule makes the corresponding compatibility case fail.
5. Run only the two existing area entrypoints after the implementation and fixture edits: `bash test/shell.d/agent-command-guards-test.sh` and `bash test/shell.d/agent-menu-test.sh`. Capture each complete output in a separate log under `$HOME/Work/` and read that log. Use preinstalled Node and the existing bounded test environment/resource policy; do not resolve/install tools as a test precondition. Revisit scope if shared code actually changes.

The proposed fixture changes must use real reader code, not a stub that supplies its expected behavior. They must not inspect private files or mutate live guard/default state. Source inspection, negative controls and fixture passes would establish only the stated metadata/dispatch compatibility. They would not establish native containment, credentials/providers, graphical behavior, all-suite/CI, hardware or release qualification.

## Expected coupling reduction and remaining coupling

The before column is from the two inspected source consumers in this checkout, not a fresh upstream comparison or a conflict-history measurement. The after column records the approved acceptance target; the implementation outcome now confirms the scoped source dependency reduction and fixture results, not a conflict-rate measurement.

| Scoped measure | Before | Proposed after |
| --- | --- | --- |
| Runtime imports of the desktop `MenuModel.js` in these two Python consumers' Node scripts | Two call sites | Zero; both use the agent-owned reader. |
| Agent workflow exposure to UI-model routing/search/guard/translation/export changes when catalog syntax/projection is unchanged | Both discovery and picker load the general UI module | Neither loads that module. An unrelated UI-only model edit no longer changes their loaded code. |
| Owners of bundled agent projection logic | Two embedded projections dependent on UI normalization | One pure agent-owned projection; two narrow transport adapters retain distinct policies. |
| Authoritative product catalogs | One bundled menu catalog | Still one; no second maintained product list. |
| Runtime files changed in the first extraction | Not applicable | One new module and two targeted consumer edits; no shared desktop-file edit. |

Menu data location/schema/ID naming, Node availability and `$OMARCHY_PATH` remain dependencies. Changing the catalog format still requires explicit compatibility work between the desktop and reader. The parser behavior is intentionally small and separately maintained; that duplication is a cost, bounded by the parity checks. This step does not reduce unrelated QML, provider, workspace, lifecycle, package or upstream-merge differences. No numerical conflict-rate or elapsed-time improvement is claimed.

## Rollout and rollback design

No rollout is authorized here. A future implementation must be reviewed as a coherent source change before publication or activation.

- Deliver the new module with the two consumer edits as one versioned source unit. Do not switch consumers before the module exists. Existing source/package delivery must include the new file; if that requires packaging changes beyond this scope, stop for a separate review.
- Do not add an error-time fallback to the old UI parser. A partial installation must surface through the existing subprocess failure path rather than hide inconsistent code.
- Review the focused logs and source scope before any separately approved activation. This reader change alone requires no shell restart, provider login, engine action, guard synchronization or state migration.
- Roll back by restoring both Python consumers from the same pre-extraction revision; restore their focused fixture changes with the code. Restore the consumers before removing the new module if a delivery mechanism updates files sequentially. An unreferenced module may remain inert until the coherent rollback completes.
- Do not reset the repository, revert unrelated edits, remove workspaces/volumes, rewrite published migrations, replace guard registrations or alter account/default state to roll back this reader.

## Review gate

Task 2.2 is the delivery of this proposal, not implementation approval. Task 2.3 source/document reconciliation is recorded in the [review record](../openspec/changes/separate-agent-safety-layer/review.md), including implemented command/menu/widget contracts missing from earlier prose. The user subsequently approved source implementation and the two focused suites. That approval did not come from completing documentation tasks and did not authorize deployment, installation, commits/pushes or archiving. Publication, merge, package/migration execution, runtime testing and activation remain independent permission decisions.
