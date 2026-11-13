# Task 2.3 source and documentation review

## Outcome

**Documentation review complete; implementation approval pending.** The [boundary inventory](../../../docs/agent-safety-boundaries.md) and [first extraction proposal](../../../plans/agent-safety-first-extraction.md) were reconciled with [Managed coding agents](../../../docs/managed-agents.md), the draft [Agent Control Plane](../../../plans/agent-control-plane.md) and implemented command/menu/widget source on the same inspected checkout HEAD `68d22643e4bd4df623977d125da7ce3b06f3a30f`.

The preferred next implementation remains one pure bundled agent-catalog reader, with two consumer edits. It does not move the whole safety layer or alter runtime contracts. Completing this review does not approve that implementation, publication, merge, archival, package/migration execution or activation.

## Implemented entrypoints, not documentation alone

The user requested an explicit check for required behavior absent from the documents. The review indexed the current agent/workspace/harness command families and traced the named entrypoints and backend branches. It did not classify every command as fork-origin by name or perform a fresh upstream comparison.

| Source reviewed | Required behavior added or clarified in the inventory/reference/proposal |
| --- | --- |
| `bin/omarchy`, `omarchy-agent`, `omarchy-agent-mode`, `omarchy-menu-agent-mode`, `omarchy-default-agent` | Child-prefix routing versus prompts; absent/invalid mode; direct save versus menu confirmation; save-and-launch default selection versus per-launch choices; picker eligibility and installed-only/check semantics. |
| Prompt/resume/continue/local/crash routes and Herdr integration hook | Pi-only session recovery is not live attachment; explicit local overlays are Host-only; check does not generate overlays; crash intentionally requests Host; local setup and postinstall hooks can mutate package/configuration state. These paths are not covered by a universal Container-mode prohibition. |
| Definition/list/ps/inspect/state, container check/doctor/audit/stop, guard/harness and account/OpenShell families | Configured, observed and historical inventory differ; stale historical running state is unknown; check can pull/probe writable cwd; quick doctor writes; audit fix stops; controller identity/escalation differs; account mode concerns future subscription selection, not Host/Container mode. Existing detailed boundary rows remain authoritative for each traced backend. |
| `default/agents/launch-menu.py`, menu data and wrapper | Browse/recent/Workspace Files selection; catalog availability checks; per-launch mode; clone/live review; no implicit fallback; private recents; retained approved clone after later failure. Workspace Files means the same writable project files, not a new copy or an editor-container attachment. |
| `default/workspaces/manager.py`, `menu.py` and workspace wrappers | Explicit build; create without runtime start/build; clone versus live mount; bounded list/unknown engine state; checked image/SSH/editor setup; possible server/extension downloads; default-No menu review; retained workspace after editor failure; ten-second stop escalation with storage retained. |
| `ExecutionDefault.qml`, `execution/Button.qml`, `execution/State.qml`, manifests and account/usage `Panel.qml` handlers | Standalone icon/label left-click opens Default Execution and right-click toggles the lazy overview. Shared mode state is event-driven. Usage icon left-click opens panel, right-click starts terminal picker, middle-click refreshes. Optional usage mode label has no overview right-click. No automatic equivalence between these widget surfaces. |

The [implemented entrypoint supplement](../../../docs/agent-safety-boundaries.md#implemented-entrypoint-contracts) links the actual owners. It extends the original boundary rows rather than claiming new runtime enforcement. Provider-specific usage engines, local-model service internals, authentication, native clicks and installed binary behavior remain outside this source qualification.

## Contradictions reconciled

| Earlier wording or possible inference | Reconciled outcome |
| --- | --- |
| All managed/Container agent writes stay away from source | Scope private clones to managed assignments. Ordinary ad-hoc Container/live-workspace binds can expose canonical source. Reused workspace files can be shared with an editor/other harnesses. Same-UID authority remains. |
| Human review implies an enforced immutable approval | Patch export compares working state to workspace HEAD; apply regenerates it and checks source/base/cleanliness, not a reviewed digest or reviewer identity. Draft attestations/trusted promotion remain proposed. |
| Sequential preflight/audit/launch is an atomic admission boundary | Preserve the mode re-read/concurrent-start gap and audit visibility limits. No lease was implemented by this change. |
| Flags and labels both enforce resources; a clean audit proves isolation | Runtime flags request constraints. Audit uses labels and selected observed fields; its legacy snapshot can appear empty on engine failure. Locality and all-capabilities enforcement are not universally proved. |
| Normal close is graceful-only | Exact-ID normal close can escalate after ten seconds. Overview stop is TERM-only with independent checks. Legacy stop paths retain narrower checks. |
| Network/credential delegation means active OpenShell mediation | Ordinary Podman dispatch does not integrate the prototypes. Pi token snapshot versus Codex gateway refresh, best-effort policy and unqualified external behavior remain distinct. |
| The draft workspace/session/runtime interfaces describe today's commands | Added a current-implementation reconciliation near the draft's status. Its requirements, stages and proposed command examples remain target design, including stronger immutable-artifact/session-scope/controller requirements. |
| First extraction can normalize both callers' policy or replace menu/workspace behavior | Keep separate output validation, empty-catalog outcomes and subprocess environments. Preserve all per-launch/menu/widget/file-sharing contracts without changing the small extraction scope. |

## Evidence and checks

The review inspected the existing picker/workspace-menu fixture code and added Q18 to the inventory's mechanism map. Those fixtures substitute UI/engine/launcher answers; selected clone tests use real temporary Git operations. The widget checks use source/extracted-function assertions, not native Qt interaction. No tests were executed and no historical result was renewed.

Document verification checks relative file links, original boundary-row classification, Markdown table continuity, portable paths, whitespace and strict OpenSpec structure. Protected harness Containerfile hashes and unrelated working-tree edits must remain unchanged. These are documentation checks, not application, provider, container, CI, graphical, hardware or release qualification.

No mode/default/guard change, agent/task/workspace/engine/doctor/provider command, account inspection, VM/GUI action, package operation, migration or service activation was performed. No private state or credentials were imported into the documents. Existing source gaps were documented, not fixed or newly reproduced.

## Requested user review

Review the proposed catalog-reader boundary, its limited parser duplication cost, unchanged malformed/empty-catalog behavior and retained command/menu/widget contracts before approving a separate implementation change. No requirement was dropped to reduce upstream differences. The fork's existing safety behavior remains the preservation target; stronger draft controls remain future work. The inactive merge and VM/tracer work remain paused.
