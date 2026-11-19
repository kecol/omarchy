# Agent catalog boundary

## Context

**Documentation proposal only.** The owner selected catalog-first planning under the accepted [architecture direction](../assess-fork-upstream-coupling/design.md). The owner has not selected a representation or authorized implementation. See [proposal.md](proposal.md) for motivation and scope.

The current source baseline is fork `0a88b4f398e03bac581d652d579940f77e4fd7ed`. The upstream menu comparison is pinned to `c3c8acf1ef376d19c400464eab9bc382a8667c6f`. No fetch, merge, reader invocation or application test is needed to establish the following source facts:

- [`catalog.js`](../../../default/agents/catalog.js) already exports `agentCatalog(raw)` as a pure CommonJS function. Do not repeat its earlier extraction.
- Two Node snippets read only the bundled `default/omarchy/omarchy-menu.jsonc`: [`command-guards.py`](../../../default/agents/command-guards.py) in `discover(root, extra)`, and [`launch-menu.py`](../../../default/agents/launch-menu.py) in `agent_catalog()`.
- The reader recognizes only `^setup\.default\.agent\.[a-z0-9-]+$`. The inspected upstream product rows use `agent.harness.*`. Taking that menu alone therefore changes discovery without changing either Python caller.
- Both callers already consume logical names, not menu actions or menu trees. Their policies and subprocess contracts differ.
- The inspected upstream `omarchy-default-agent` remains an installer/save/launch entrypoint, not a pure catalog API. Do not execute it or scrape its case statement as a replacement source of product metadata.

These are source observations, not newly reproduced runtime failures. Earlier [extraction results](../extract-agent-catalog-reader/outcome.md) remain historical scoped evidence; its preparation-time deployment statements do not describe the current checkout's later integration status.

### Important guiding references

| Reference | How it guides this boundary |
| --- | --- |
| [AGENTS.md](../../../AGENTS.md), [OpenSpec reference](../../../docs/openspec.md) | Keep scope small, distinguish planning from permission, and use an inactive candidate for any later safety-sensitive runtime edits. |
| [Managed-agent catalog contract](../../../docs/managed-agents.md#bundled-catalog-reader), [safety inventory](../../../docs/agent-safety-boundaries.md) | Preserve current caller ownership and limits. Catalog extraction is not containment or authenticated launch approval. |
| [Menu reference](../../../docs/menu.md), [original extraction design](../../../plans/agent-safety-first-extraction.md) | Preserve the limited parser contract and bundled-only data scope. User overlays and runtime providers have different semantics. |
| [Testing reference](../../../docs/testing.md), [guard fixture](../../../test/shell.d/fixtures/agent-command-guards-test.py), [menu fixture](../../../test/shell.d/fixtures/agent-menu-test.py) | Extend actual parsing/transport cases instead of adding snapshots, source greps or a new harness. No existing suite was rerun for this proposal. |
| [Runtime-availability spec](../../specs/managed-runtime-availability/spec.md), [stop-target-binding spec](../../specs/managed-stop-target-binding/spec.md), [work ledger](../../history/work-ledger.md) | Leave runtime inventory, lifecycle targeting and prior evidence unchanged. The catalog's historical empty-list behavior is not the engine-observation contract. |

Surface important new references or conflicts before they change the chosen scope or contract. Older plans inform the design; they do not authorize stronger mechanisms or execution.

## Goals / Non-Goals

**Goals:** define the smallest product-metadata interface that keeps presentation changes out of policy owners; compare representations against actual callers; give a bounded implementation recommendation and behavioral acceptance cases.

**Non-goals:** make all upstream menu changes compatible, impose one shared validator, centralize product/recipe/process allowlists, execute a readiness or installation service during discovery, or claim that the existing malformed-catalog limitation is fixed. Exact syntax and limits below are preservation conditions, not a parser redesign.

## Decisions

### 1. Separate four responsibilities

```text
Single bundled product metadata source
                  |
     pure representation adapter / projection
                  |
    ordered logical name + display-label records
           |                         |
  guard transport                picker transport
  name/role checks               record/label checks
  definitions + registrations    mode-specific availability
  installed-command lookup       explicit per-launch selection
```

The catalog owner handles representation-to-record projection only. Existing callers own file reads and subprocess transport. Existing guard, definition, picker and launcher backends retain all validation and effects.

A product record is not an executable path, installer recipe, account, authenticated session, Container capability, process-recognition rule or launch permission. Do not derive any of those authorities from catalog membership. Do not pass `action`, `checked`, `when`, `disabled`, aliases, translations or provider instructions to a consumer as executable data. Do not change `status.py` recognition when adding a catalog product.

### 2. Keep the normalized consumer boundary small

The proposed stable consumer boundary is the current `agentCatalog(raw)` projection and its ordered `{name, label}` records. If the metadata representation changes, adapt it on the reader side rather than changing both callers' policy code. Keep the two Python response shapes: names-only JSON for guards and record JSON for the picker.

| Contract element | Proposed preservation condition |
| --- | --- |
| Input authority | Callers read the bundled source under `$OMARCHY_PATH`. Do not merge user overlays, project files, account stores, process observations or runtime providers into this catalog. Guard definition discovery remains a separate existing operation. |
| Logical identity | Use a product name independent of execution mode and label. For the bounded menu option, derive it from the matched ID's final segment; accept future matching names without a hard-coded product list or a required definition. Existing caller name restrictions remain separate. |
| Output | Return only `name` and `label` records. Do not add readiness, command, credential, mode or action fields. |
| Ordering | Preserve source row enumeration order; do not sort or prioritize products in the reader. The picker retains its own saved-default ordering. |
| Labels | Preserve `entry.label || id` for menu-derived rows, including the source ID fallback. Do not stringify a truthy non-string label or sanitize it into an accepted picker label. Guards need only names; the picker owns label validation. |
| Purity | No filesystem, environment, process, network, state or clock access in the module or function. Only callers perform I/O. Do not import `MenuModel.js` at runtime. |
| Version/availability | Keep the existing source/asset delivery unit. Do not add an optional package, daemon, loader registry, user setting or permissive missing-module fallback. A future semantic metadata format needs an explicitly reviewed version/compatibility contract. |

The record shape is stable, but raw output is not a universal trusted schema: invalid truthy labels intentionally reach the picker validator. A shared normalizer must not silently discard a product that the picker should reject or broaden names that guards should refuse.

### 3. Preserve caller-owned validation and failure semantics

| Case | Guard discovery | Launch picker |
| --- | --- | --- |
| Valid metadata | Map catalog names, then retain definition/alias conflict checks, explicit registrations, infrastructure exclusions and installed-only lookup outside the guard prefix. Do not execute the discovered binary. | Validate records before readiness checks. Retain name checks, duplicate-name refusal, printable nonempty labels of at most 80 characters and existing menu-row ambiguity refusal. |
| Empty or malformed text / unsupported top-level value | Reader currently yields `[]`; discovery may continue with definitions and explicit registrations. This is incomplete catalog coverage, not a fail-closed coverage guarantee. | Reject an empty list before selecting or checking agents. Do not choose the saved default implicitly. |
| Duplicate logical names in projected records | Existing names-only mapping collapses identical names. Definition/command mapping conflicts retain their existing refusal. | Existing duplicate-name validator refuses the list. Do not silently select a preferred row. |
| Missing/unreadable module or data file; Node nonzero exit or timeout | Preserve checked-subprocess failure. Do not reinterpret it as an empty catalog or use stale metadata. | Preserve checked-subprocess failure before readiness or launch. Do not fall back to Host or the UI parser. |
| Transport limits | Five-second timeout, current stdin/cwd behavior, removal of `NODE_OPTIONS` and `NODE_PATH`, one-MiB output check and at-most-256 list check. Retain the broader inherited environment's existing limits. | Five-second timeout, repository cwd, existing environment allowlist and nonempty at-most-128 list check. Do not introduce a new shared byte cap as an incidental refactor. |
| Effects after discovery | Existing explicit enable/sync may write guard state/scripts. Catalog reading itself does not enable, sync or change PATH. | Existing selection/review flows own effects. Catalog reading does not save defaults, prepare images, sign in, create a project or launch an agent. |

**Do not silently tighten malformed-catalog handling in this change.** A future hardening proposal could distinguish parse failure from valid empty data, but that changes guard behavior and needs separate review. It is not required to handle the observed namespace move.

### 4. Compare representation choices

| Option | Change propagation and ownership | Cost / compatibility consequence | Recommendation |
| --- | --- | --- | --- |
| A. Stable shared product metadata | Both menu presentation and agent consumers derive products from one explicit semantic source. This could be a stable typed marker/logical-name field in the bundled data or a shared metadata file consumed by the menu producer. Menu ancestry would no longer define product identity. | Requires agreement on producer ownership, field/schema/version, ordering, labels, absent/invalid data and coherent source delivery. A separate file helps only if the menu also consumes it; a hand-maintained second list creates drift. The reviewed upstream rows do not currently expose such a contract. | Preferred long-term responsibility boundary. Do not assume upstream acceptance or invent a new producer in this documentation change. |
| B. Bounded menu-compatibility adapter | Keep the current bundled menu as the single product source. Normalize exactly the legacy and inspected upstream namespaces in the agent-owned reader. Both Python consumers continue to see the same record shape and policy checks. | Smaller change; no menu/launcher/startup/package edits are required by the proposed projection. Retains known schema/ID coupling and needs explicit revision when upstream changes it again. It is not complete separation from presentation. | Recommended first implementation for owner review, with the profile below. It handles the observed rename without making upstream interface adoption a prerequisite. |
| C. Keep legacy-only recognition | No source work or immediate regression risk. | The known upstream menu form still changes discovery. The larger integration must retain/adapt legacy rows. | Baseline and rollback limit, not a solution to the observed mismatch. |
| D. Infer products from actions, installer/help text or installed tools | Appears to avoid a schema change. | Couples discovery to executable syntax, product aliases, installation state or effectful commands; loses declared-but-uninstalled/future products. | Reject. These are different responsibilities and trust scopes. |

The owner must select A or B before an implementation task list is authorized. This is the requested representation comparison, not an unresolved assumption hidden inside code tasks. No upstream publication is needed to complete this document or choose a local bounded improvement.

### 5. Proposed profile for option B

If selected, preserve the current parser and change only representation recognition:

- Recognize exact full IDs matching `^setup\.default\.agent\.[a-z0-9-]+$` or `^agent\.harness\.[a-z0-9-]+$`. Do not match submenu roots, nested descendants, uppercase/underscore variants, aliases or arbitrary `agent.*` entries.
- Preserve the limited whole-line-comment/trailing-comma transformations, object-valued `items` selection with existing outer-object fallback, row-type filtering and malformed-input `[]` behavior. This is not standards-compliant JSONC; current transformations can affect syntax-like text inside strings.
- Enumerate matching rows together in source order. Do not prefer one namespace, deduplicate by product name or fall back from a new row to an old row. If both namespaces declare the same name, return both records: the picker refuses; guards retain their existing identical-name behavior.
- Retain each row's `label || id`. Do not rewrite a legacy fallback ID into a modern one or force missing labels to the product name. Label text may therefore still change when the source ID changes; logical name, not display text, is the consumer identity.
- Keep future matching names discoverable without a definition or a product-name allowlist. Do not map installer aliases such as alternate CLI names into this product namespace.
- Keep unsupported namespaces outside the projection. Do not claim to distinguish an entirely renamed schema from a legitimately empty catalog; that historical limitation remains explicit.

This profile is a proposed compatibility behavior change, not already implemented behavior. It would need a reviewed runtime delta contract and implementation task list after selection. It does not import the upstream menu or qualify any newly listed product's executable.

### 6. Conditional implementation scope and maintenance benefit

For B, the expected runtime edit is confined to `default/agents/catalog.js`. Extend the two existing Python fixture files and reconcile the catalog subsection of `docs/managed-agents.md`; retain attribution. The two Python callers should require no production edit. If implementation needs a changed validator, error policy, menu, launcher, new runtime file or package, stop for scope review.

The acceptance target is concrete: changing between synthetic legacy/current menu layouts produces the expected logical records in both real caller transports without coordinated edits to either policy owner. This moves known representation adaptation to one owner, but does not promise lower conflict percentages, faster merges or independence from every future schema.

For A, do not reuse B's scope estimate. A separate design decision must name the authoritative producer and every menu/agent consumer, define version/failure and label behavior, and avoid duplicate maintained lists. Its menu/producer changes could need broader shell or graphical checks. Do not declare A ready to implement before those choices exist.

## Focused compatibility checks for later implementation

These are planned acceptance cases, not checks run for this document. Reuse the existing installed-Node resolver and synthetic scratch HOME/catalog trees. Do not run mise/tool resolution, accounts, real guard sync, agents, providers, engines or a GUI to prove metadata behavior.

| Regression to catch | Existing fixture seam and expected result for B |
| --- | --- |
| A future upstream-format product disappears | Extend guard `test_future_catalog_entry_is_discovered_without_definition_or_registration` with a synthetic `agent.harness.future-catalog` row and an inert installed executable. Invoke real `discover`/Node/reader; it must discover the name without running the executable or needing a definition. |
| The new form never reaches the picker | Extend menu `test_real_catalog_transport_preserves_projection_validation_and_missing_file_errors` through actual `agent_catalog()` and Node. Expect the synthetic logical name, label and source order for both forms. Do not mock the response that provides the behavior under test. |
| Recognition broadens or hides ambiguity | Use compact mixed-namespace input with irrelevant/nested IDs and a duplicate logical name. Check ordered reader results, picker duplicate refusal and guard identical-name behavior separately. Include a truthy invalid label: picker rejects it while guard names remain discoverable. |
| Parser or old label behavior changes incidentally | Retain the existing legacy-only parser-parity cases and current menu model as a test-only oracle. Add explicit expected records for the new namespace; do not change that oracle to assert the new implementation against itself. Cover missing/falsy labels and syntax-like label text. |
| A new path bypasses a caller limit or refusal | Retain existing error/timeout/environment/size/list/label cases and cancellation/unavailable-default fixtures. Extend a boundary-size case to modern IDs only where it catches a new bypass. Do not rewrite the whole test suite or duplicate existing cases. |

The new real-discovery/transport cases should fail on the current reader because it omits modern-format products, not because a new module is missing. A disposable semantic omission of modern recognition should make those cases fail after implementation. Run only affected methods for that control; do not rerun successful complete suites to confirm them.

The expected focused entrypoints are `bash test/shell.d/agent-command-guards-test.sh` and `bash test/shell.d/agent-menu-test.sh`, with each complete output saved and read separately under the approved bounded test scope. They include existing behavior beyond the new cases; fixture-source review does not renew their results. These checks would qualify parsing, caller validation and fixture dispatch, not native guard coverage, runtime isolation, provider/credential behavior or a release.

This proposal does not waive the risk-based qualification rules in `docs/openspec.md`. If the later implementation expands into launch/runtime discovery policy, reassess the native/graphical gates before execution. Do not run a VM or revive a previous harness merely because a later task mentions validation.

## Risks / Trade-offs

- **An adapter is mistaken for complete decoupling** → Name the two supported forms and retain the schema dependency in documentation. Use semantic metadata as the long-term comparison, not a claim that B already supplies it.
- **One catalog becomes a universal authority list** → Keep Container definitions, process recognizers, installed-only checks and credential flows separate. A new declared product gains metadata coverage only.
- **Deduplication hides an invalid picker catalog** → Preserve both records and existing caller-specific behavior. No namespace precedence or automatic conflict repair.
- **Stricter parsing or failure handling changes guard coverage** → Keep the current parser and empty-list distinction. Review hardening separately rather than broadening this change.
- **A fallback label changes with menu ancestry** → Preserve exact legacy behavior and document the new ID fallback. A stable-label redesign belongs with a semantic metadata decision.
- **A shared metadata proposal creates a second maintained list** → Require a single producer/source consumed by presentation and agent readers before choosing A.
- **Tests assert a product snapshot or test their own stub** → Use synthetic future products and actual reader transport, with explicit semantic negative controls. Never assert the current total product count.

## Migration Plan

No runtime migration is authorized or needed for this document.

1. Review the contract and choose the representation. Keep this documentation-only task record separate from any future unchecked runtime tasks.
2. If B is selected, record the profile as an approved implementation proposal with the appropriate behavior delta and bounded source/test scope. If A is selected, specify its actual producer/version contract before implementation tasks are written.
3. Implement only after a separate request and in an inactive candidate. Keep the active dev link, user overlays, defaults, registrations and accounts unchanged.
4. Execute only separately approved checks. Review exact source, failures, skips and evidence limits before publication or integration gates.
5. Deliver any approved source and fixture changes coherently. Reader adaptation alone does not require a menu refresh, shell restart, guard enable/sync, registry conversion, provider login or image rebuild.

For B, source rollback restores the reader and corresponding fixture/docs changes from a coherent reviewed revision; leave callers and all user state unchanged. Restoring legacy-only recognition reintroduces incompatibility with a modern-only bundled menu. If a later upstream integration changes that menu, review the reader/data compatibility pair before rollback; never select Host or discard guard state to make rollback appear successful.

## Review decision

**Recommendation offered:** use B as a bounded first implementation; retain A as the preferred semantic ownership direction when a single shared producer contract is viable. This does not preselect any upstream commit or promise a future upstream contribution.

**Required owner decision:** select the representation and approve its exact proposed behavior before runtime specification/tasks or code work. The documentation comparison is complete without that decision; no runtime implementation task is marked ready or complete here.
