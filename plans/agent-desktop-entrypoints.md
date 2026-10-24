# Agent desktop entry points: staged implementation plan

Status: Phases 1 and 2 are active. Phase 3 is authorized and implemented in a separate feature worktree. Functional checks pass; actual visual verification and activation remain pending. The host has approximately 3 GiB available memory, below the disposable VM threshold. No Phase 3 user configuration or execution default has been changed.

## Goal

Expose existing container workspace and agent commands through the Omarchy menu. Make the execution boundary and writable files visible before launch. Implement, test, and review each phase before starting the next phase.

## Current foundations

- The default menu is `default/omarchy/omarchy-menu.jsonc`. Menu select/input helpers already provide shell-native picker interfaces.
- `omarchy workspace create`, `start`, `code`, `list`, and `doctor` manage independent container workspaces. `code` starts the workspace if needed and opens its isolated Remote SSH VS Code window.
- Workspace clone mode copies committed Git HEAD, excludes uncommitted and untracked files, and removes the source remote. Direct-mount mode explicitly grants immediate writes to the selected host directory.
- `omarchy agent` already resolves the default agent and execution mode, supports per-launch host/container overrides, and delegates container launches to the existing runtime and image selector.
- `omarchy agent mode host|container` already stores the launch default. With no stored setting, the current backend returns `host`. This plan does not silently change that behavior.
- The existing Agents shell plugin has agent-launch affordances. Preserve its usage panel and existing interactions unless a phase explicitly changes them.
- The editor workspace image and agent harness images are different backends. Do not present them as one shared runtime unless a shared-filesystem and lifecycle contract has been implemented and verified.

## Common design rules

- Use a shared Agents menu section for these entry points. Preserve existing default-agent settings and the normal VS Code application entry.
- Keep backend commands authoritative. UI code must not create its own container engine, configuration store, or credential handling.
- Use structured argument passing and stable workspace identifiers. Do not evaluate project names or paths as shell commands.
- Cancellation must not create a workspace, start an agent, build an image, or change defaults. For workspace creation, commit side effects only after the creation summary is accepted; opening VS Code is a subsequent action whose failure must leave the created workspace visible and reusable.
- Do not automatically install software, build or update images, copy credentials, or change mount permissions. Offer explicit actions for missing prerequisites.
- Use local project paths in this iteration. Do not change remote Herdr profiles or remote agent sessions.
- A container workspace is not a Herdr space. Keep these terms distinct in labels and documentation.

## Phase 1 — Open a container workspace from the menu

### User flow

1. Open Agents → Workspaces.
2. Select an existing workspace or Create from Project.
3. For an existing workspace, show its project, access type, and current state, then open it through `omarchy workspace code`.
4. For a new workspace, select a source directory and a unique workspace name.
5. Present an isolated clone of committed Git HEAD as the normal choice. Explain that uncommitted and untracked files will not be included.
6. Keep live host-directory mounts behind an explicit access choice and warning. Non-Git directories must not silently switch into mount mode.
7. Show the name, source, access type, and requested action before creation. Create through the existing backend, then open VS Code.

### Scope

- Add the menu entry and a thin interactive launcher.
- Reuse native menu pickers and the existing directory chooser where suitable. Do not add a new QML panel solely for this flow.
- Enumerate registered workspaces without starting them. Add a read-only structured backend listing only if the current listing cannot supply stable selection data.
- Leave the normal VS Code launcher unchanged.
- Do not start a separate agent harness automatically. The existing workspace editor integration remains available, with authentication owned by that workspace.
- Show first-launch network requirements for VS Code Server and extensions. Do not imply that starting the workspace is fully offline.

### Acceptance criteria

- Existing running and stopped workspaces open correctly; stopped workspaces start through the existing command.
- Two selected workspace names retain independent project, editor, home, key, and agent state.
- Clone mode does not mount the source checkout or include its uncommitted files.
- Direct-mount mode requires an explicit warning and retains all existing backend path restrictions.
- Cancelling before confirmation has no workspace/container side effects.
- Invalid names, missing paths, unavailable images, absent VS Code, and first-launch failures are actionable and do not trigger an automatic fallback or build.
- Paths with spaces and shell metacharacters are passed as data.

## Phase 2 — Start an agent with project selection

### User flow

1. Open Agents → Start Agent.
2. Select a project through a recent-project list or directory browser. Do not assume the menu's current working directory is the desired project.
3. Select the agent, with the current default preselected. A per-launch choice does not change the saved default agent.
4. Show the effective Host or Container execution choice, using the existing mode setting. A per-launch override does not change the saved execution default.
5. For a container launch, show the exact writable scope. Offer isolated-copy and live-directory access only where supported by the existing backends.
6. Confirm the project, agent, execution target, and writable scope.
7. Delegate launch to the existing agent command and retain its image/version selection and model-recovery flow.

### Design gate before implementation

Verified: the existing agent runtime mounts its working directory read-write. `workspace create` can prepare a private committed-HEAD clone without starting an editor container. `workspace list --json` provides the validated project path for that named clone. The agent can run through its existing harness with that clone as its explicit working directory; no engine socket or nested container is required.

Workspace Files is an explicit reuse action, not a combined editor/agent launch. Its review states that the project files are the same files the editor uses, while the agent harness, home, authentication, and lifecycle remain separate. Live-mount workspaces retain their host-write warning. A fully prepared, approved clone is retained if subsequent image selection is cancelled or launch fails, and can be selected through Workspace Files on the next launch. No second clone manager or private registry reader was added to QML.

### Scope

- Add a menu-specific interactive launcher rather than changing ordinary CLI invocations to prompt unexpectedly.
- Reuse the existing agent catalog and runtime capability checks. Host executable availability and container harness availability are different checks.
- Add a documented public per-launch agent selector if needed; do not make the menu depend on an undocumented internal flag as a permanent interface.
- Remember recent project choices, not credentials. Keep recent lists bounded and avoid recursive filesystem scans.
- Do not add another model picker or authentication workflow. Pi retains ownership of model and credential handling.

### Acceptance criteria

- The selected agent starts in the selected project with the selected execution target and displayed writable scope.
- Per-launch agent and execution choices leave saved defaults unchanged.
- Unsupported agent/runtime combinations fail before launch rather than falling back to Host.
- A Host launch is visibly different from a Container launch; selecting a directory never implies container isolation.
- Cancellation before final approval leaves no launched agent, project copy, or recent-project update. A complete clone created after approval is retained if later image selection is cancelled; no partial staging directory is published.
- Existing direct CLI, managed-task, one-shot, and noninteractive flows retain their behavior.
- Container image updates remain explicit, and no failed prompt is replayed.

## Phase 3 — Expose the execution default and show it in the bar

### User flow

1. Open Agents → Default Execution.
2. Select Host or Container using checked menu entries.
3. Explain that the setting affects future launches only. Show a clear warning when selecting Host.
4. Display an optional compact label in the existing Agents bar surface: Default: Host or Default: Container.
5. Link the mode display to the execution-default menu without removing the existing usage-panel interactions.

### Scope

- Read and write the existing `omarchy agent mode` setting. Do not add a second preference.
- Preserve the saved mode and the current unset-mode behavior. Changing the installation default to Container requires a separate, explicit compatibility decision.
- Refresh menu guards through the existing shared-reader mechanism.
- Use a shared file watch or command-driven refresh for the bar. Handle file creation and atomic replacement; do not poll or start one watcher process per monitor. The implementation uses one lazy QML singleton and a setter-driven IPC refresh after atomic publication. A save during an in-flight query queues a fresh read. Manual file edits require an explicit refresh or shell reload.
- Label the value as the launch default, not the execution mode of every running agent. Host and container agents can coexist.
- Invalid setting data must show an error/unknown state rather than silently displaying Host or Container.

### Acceptance criteria

- Menu and bar show the same saved default after a UI change, CLI change, shell reload, and fresh login in the disposable test environment.
- Switching defaults does not restart, migrate, stop, or otherwise modify existing agents or workspaces.
- Per-launch overrides remain available and do not alter the default indicator.
- Multi-monitor rendering is consistent, with no duplicated background polling and no idle process-spawn regression.
- Missing or invalid setting files follow the documented behavior and are covered by tests.

## Delivery and validation for every phase

1. Start from the current fork in a separate worktree and branch. Do not combine this work with the deferred upstream integration.
2. Implement only the current phase and its necessary backend interface.
3. Add focused tests for menu routing, stable identifiers, argument safety, cancellation, error handling, and relevant backend behavior.
4. Run focused tests, CLI/metadata checks where applicable, and existing menu performance guards. Keep complete output.
5. For menu-only entry points, use an approved, scoped host UI preview with backend mutations disabled. Use a disposable VM for the graphical acceptance suite and for runtime/isolation changes. Inspect reference and candidate captures for focus, clipping, stale state, and wrong-target behavior.
6. Use synthetic providers for agent tests. Do not issue live provider requests, copy personal credentials, or use existing independent workspaces as fixtures.
7. Document behavior and limitations. Present results for review before starting the next phase.
8. Activate approved changes through a history-preserving merge. Do not reboot the host or interrupt existing sessions. Obtain agreement before any required live shell restart.

## Rollback

Keep each phase independently reviewable and reversible. Reverting a UI integration must not delete workspace data, authentication state, editor state, or running agents. Preserve user menu and bar customizations. Remove or disable only the new entry points; use a normal revert commit if published history must be retained.

## Deferred work

- A combined editor-plus-agent launch that guarantees both operate on the same project files and has explicit credential and lifecycle ownership.
- Remote machine onboarding or remote Herdr management from the Omarchy menu.
- Automatic provider requests, account login, model changes, or image updates.
- A global change from Host to Container as the unset default.
- Host-action brokers or broader desktop automation permissions.

## Implementation order

1. Workspace menu launcher.
2. Agent project/agent selection launcher.
3. Execution-default menu and bar visibility.

Pause after each phase for review. Phases 1 and 2 are active. Phase 3 was authorized. Complete its visual verification and present the results before activation. Obtain approval before a required live shell restart or a host preview outside the previously approved menu-only scope.
