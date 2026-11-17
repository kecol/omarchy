# Bounded catalog namespace adapter

## Context

Option B is selected under the owner's delegated decision. This is the implementation plan for that option, not another architecture study. See [proposal.md](proposal.md), the [behavior delta](specs/bundled-agent-catalog/spec.md) and the prior [contract comparison](../define-agent-catalog-boundary/design.md).

Current `default/agents/catalog.js` recognizes only the legacy namespace. The existing two real-transport fixture seams and caller-specific checks were inspected in the preceding contract proposal. No new application tests have run. Earlier assessment records remain completed documentation snapshots; this change supersedes their representation-decision status without rewriting their history or claiming code exists.

Guiding references are [AGENTS.md](../../../AGENTS.md), [managed-agent catalog behavior](../../../docs/managed-agents.md#bundled-catalog-reader), [menu syntax](../../../docs/menu.md), [testing](../../../docs/testing.md), [OpenSpec execution/activation rules](../../../docs/openspec.md) and the [original extraction outcome](../extract-agent-catalog-reader/outcome.md). Important new reference conflicts must be reported before scope or behavior changes.

## Goals / Non-Goals

**Goals:** recognize the two known product namespaces in the existing pure reader; keep policy owners unchanged; prove both callers receive modern-format future products through their real reader transport.

**Non-goals:** change general JSONC parsing, malformed-catalog policy, label normalization, duplicate handling, launcher behavior, guard synchronization, menu placement, upstream intake, packaging or native confinement. The reader remains dependent on the bundled format and known ID forms.

## Decisions

### Minimal production scope

| File | Change and verification |
| --- | --- |
| `default/agents/catalog.js` | Extend only the existing anchored namespace selection to the two reviewed forms. Keep the exported function, parser, row enumeration, name projection, duplicate records, label fallback and attribution. |
| `test/shell.d/fixtures/agent-command-guards-test.py` | Extend the existing future-catalog real-discovery case with modern and mixed rows, identical-name collapse and name-only handling of an invalid label. Keep inert executable call accounting; the executable must not run during discovery. |
| `test/shell.d/fixtures/agent-menu-test.py` | Extend real reader transport with modern and mixed rows, ordered output, missing-label fallback, duplicate-name refusal, invalid-label refusal and exclusion of unrelated/nested IDs. Retain the legacy parser-parity cases and existing transport/refusal tests. |
| `docs/managed-agents.md` | Update only the bundled-catalog subsection with the supported namespaces, retained caller differences and remaining menu-schema dependency. Do not strengthen historical qualification claims. |

Do not edit either Python production caller. If the implementation needs another runtime file, a different validator/error policy or a menu/launcher/package change, pause for review. Do not create a parallel product list or a new test file.

### Preserve the ownership boundary

The reader returns ordered records, not verified launch requests. Guard discovery retains name/role filtering, definition/registration processing and installed-only lookup. The picker retains record/label/duplicate validation, mode-specific checks and explicit selection. Unknown namespaces remain excluded; parse failure still yields an empty list, which these callers handle differently. Missing file/module and Node failures remain errors, not an empty success or a Host fallback.

Mixed namespaces have no precedence. Return both rows when their logical names coincide; the picker refuses and guards retain identical-name mapping behavior. Preserve `label || id`, including truthy invalid label values for caller validation. Do not reinterpret labels as identifiers or infer support from menu actions.

Stable semantic metadata was considered and deferred because a shared producer contract does not yet exist in the reviewed menu. This adapter handles the concrete namespace move without introducing producer/menu changes; it does not remove every data-schema dependency.

### Proportionate verification

Use the existing real Node/reader transports and scratch fixtures. The key regression is a synthetic future product declared only under `agent.harness.*` disappearing from discovery or picker records. It needs no definition, registration or live product executable. Preserve old-form parity, and use explicit expected records for new/mixed forms rather than teaching the old menu-parser oracle to match the new reader.

After fixture edits, run each existing entrypoint once under the separately approved focused-test scope: `bash test/shell.d/agent-command-guards-test.sh` and `bash test/shell.d/agent-menu-test.sh`. Save complete separate logs; do not pipe away output or rerun successful suites to confirm a pass. Use preinstalled Node through the existing resolver, never a lazy shim/tool installation. Review existing clone/key/scratch-dispatch behavior in the menu suite before execution; do not mistake it for a live editor/container launch.

Use bounded test resources: at most 2 GiB memory, 512 MiB swap, 200% CPU, 512 tasks, nice 10 and a 150-second unit lifetime, with a 45-second per-suite deadline and two-second termination grace. Test execution still needs its applicable approval; these settings are a proposed upper bound, not permission or an assertion of kernel-enforced containment. Do not raise limits or use cache/reclaim tricks to qualify a result.

In a disposable copy, remove modern recognition while retaining the new fixture cases. Run only the affected real-discovery and real-picker methods; require failure for omitted modern records, not an import/setup error. Restore neither active files nor candidate source through a risky temporary mutation: mutate only the disposable copy. A duplicate-stripping control is useful only if needed to establish that the new duplicate case rejects a semantic regression.

This scope is metadata projection and synthetic caller transport, not engine/runtime-inventory discovery. No native or graphical behavior changes are planned, and no native/GUI run is proposed. Preserve the risk rules in `docs/openspec.md`: if source review finds effects beyond the stated pure-reader boundary, reassess qualification before proceeding. No existing consumed native approval applies.

## Risks / Trade-offs

- **Overbroad recognition** → Retain the existing suffix selection semantics and anchored namespace forms; test unrelated/nested/uppercase/underscore rows without broadening product authority.
- **Hidden duplicate or label repair** → Assert reader order and raw fallback behavior through real transport, then preserve the callers' different results.
- **False qualification from stubs** → Let real parsing/transport provide the tested behavior. Inert executables only expose accidental execution; they do not implement the catalog.
- **Shared-file edits expand without need** → Limit production changes to the reader and catalog documentation; retain existing callers and menu data.
- **Unpublished planning references** → Earlier assessment artifacts are currently local planning context. Do not publish them incidentally with a runtime fix; resolve their reference/publication disposition at a separate publication review.

## Migration Plan

1. Verify the active dev-link/source resolution without invoking a changed runtime command. Create a separate inactive worktree/branch from the pinned baseline; keep the active checkout and its stricter modes unchanged.
2. Carry this change's planning files into the candidate with verified bytes. Earlier local planning documents may be copied unchanged as reference context, not included in publication automatically. Preserve all original active planning files.
3. Implement the four-file scope and its regression cases together. Update the catalog documentation in the same work unit.
4. After applicable execution approval, run the bounded focused suites and affected semantic controls. Record exact source bindings, complete logs, failures/skips and cleanup status before marking validation complete.
5. Review the final diff and evidence. Stop before commit/publication, upstream intake, merge, activation or archive; those remain separate approvals.

No default change, live guard sync, account action, image build, menu refresh, shell restart, migration or package action is required for this source change. Later integration into a dev-linked checkout would affect subsequent caller invocations, so an inactive candidate is mandatory during development.

Rollback restores the reader, fixtures and catalog prose as a coherent source revision without touching user state. Legacy-only recognition is not compatible with a modern-only menu; review the reader/data pair if a later upstream integration has changed the bundled menu. Do not roll back unrelated safety deliveries or erase generated guard state.
