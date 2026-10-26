# Start an agent from the desktop menu

Open **Agents → Start Agent** to select a project, an agent, and an execution target for one launch. This does not change the saved default agent or the default Host/Container execution setting.

## Select the project

Select **Browse Project** to use the desktop directory chooser. Recent confirmed source projects are also listed. The menu remembers at most ten paths in private local state; it does not scan your home directory or store credentials.

Select **Workspace Files** to reuse a named container workspace's project files. This is an explicit choice to share those files with any editor session using that workspace. It does not open VS Code or start the workspace's editor container. The agent runs through its own harness and uses its own agent home, not the editor workspace's home or authentication.

## Select the agent and execution target

The agent picker uses the same catalog as **Setup → Defaults → Agent**. The current default is listed first. Rows distinguish an installed host command from a configured container definition; these are separate requirements.

Select **Host** or **Container** for this launch. The current execution default is listed first. An unsupported selection reports an error; it never falls back to another agent or to Host. The bundled container definition currently supports Pi. Other agents require their own valid container definitions and images.

Host checks resolve installed executables without running them. Menu launches bypass mise's lazy shims and do not ask Omarchy to install or update a missing host tool. Install missing tools explicitly. OpenClaw starts through its installed `tui` command; its gateway must already be configured, because this menu does not install/onboard a gateway service.

## Review file access

**Host is not a sandbox.** A host agent runs with your desktop user's permissions. The selected project is its working directory, not a restriction on other files. The existing agent launcher's permission/approval options still apply.

For a source project in Container mode, choose:

- **Isolated Git Clone**: create a new, uniquely named workspace using the existing workspace backend. It copies committed Git HEAD, excludes uncommitted/untracked files, and removes the source remote. The agent receives the new clone read-write; the source checkout is not mounted.
- **Live Host Directory**: mount the selected directory read-write. The agent can change host files immediately, including ignored files. Review it for secrets first. Known credential, system, state, and active Omarchy source paths remain restricted.

For **Workspace Files**, the recorded workspace access type applies. A clone remains a clone; a live mount still permits immediate host writes. A separate agent harness does not make another copy of the workspace files.

A review terminal shows the agent, execution target, project, and access warning. **Cancel is selected by default.** No agent, copy, or recent-project update is created before confirmation. Confirm to continue to the existing agent launcher and, in Container mode, its image/version selector. Image updates remain explicit. Model selection and authentication remain owned by the agent; Pi keeps its existing model-recovery flow.

## Homes and lifecycle

An interactive agent container has a persistent home shared by that agent's interactive projects. A new project clone does not create a new provider account or a new agent home. Host auth/home directories and engine sockets are not mounted by this flow.

A workspace's editor container and the agent harness have independent lifecycles. `omarchy workspace list` reports the editor workspace container status, not every agent using its files. Use `omarchy agent ps` to inspect container agent instances. Stopping an editor workspace does not stop a separate agent harness.

A confirmed clone is complete and retained if image selection is later cancelled or the agent fails. It remains available through **Workspace Files** on the next agent launch, or through **Agents → Workspaces** for an editor. The menu does not delete approved project copies automatically. Review and transfer changes back to the original checkout explicitly; no automatic copy-back occurs.

## Change the execution default

Open **Agents → Default Execution**. The checked row is the saved launch default. Select Host or Container, review its permissions, then confirm **Save default**. Cancel leaves the setting unchanged. The choice affects future launches only; running agents and workspaces keep their current execution environments. A per-launch Host/Container choice still takes precedence and does not save a new default. Without a saved setting, the default remains Host.

The same setting is available from the terminal:

```bash
omarchy agent mode
omarchy agent mode container
omarchy agent mode host
```

Use the independent **Agent execution default** widget to show a mode icon and status without enabling the Agents usage panel:

```bash
omarchy plugin enable omarchy.agent-execution
```

It shows a desktop icon for **Default: Host**, a package icon for **Default: Container**, or a warning icon for **Default: Unknown**. This is the launch default, not where every running agent executes. Left-click either the icon or text to open Default Execution. Right-click either part to open or close the local agent overview. Middle-click does nothing. The bar label reads only the local mode setting. The overview reads local inventory metadata only when requested. Neither uses background polling, starts usage collectors, contacts providers, inspects authentication, or launches an agent. Vertical bars stack the icon above a rotated label.

### Local agent overview

Right-click the independent execution-default widget for an on-demand local snapshot. The panel groups identified processes by monitor and desktop workspace. Possible window matches, unknown locations, and possible process-name candidates have separate sections. Each process appears once. Herdr reports say **Herdr**; **Observed · activity unknown** does not mean that an agent is working.

Expand **Details** to see process, container workspace, Herdr session/tab/pane, and desktop-window identities. A VS Code profile location does not verify a remote connection or visible agent panel. An attached Herdr terminal does not verify pane visibility. Multiple window matches are not resolved by guessing.

The panel scans when opened or when you select **Refresh**. The timestamp belongs to that snapshot, not a live feed. Failed refreshes retain the previous snapshot and its original timestamp with a warning. **Show coverage** explains which sources were available. Partial or unavailable coverage is not a claim of zero agents. Large snapshots show a limit notice; use `omarchy agent status` for all process rows.

Use **Tab** to select controls, **Enter** to activate them, **R** to refresh, **Page Up/Down** or arrow keys to scroll, and **Esc** to close. **Change default** opens the existing confirmation-based menu; it does not change running processes. The panel does not focus agent windows, switch desktops, start agents, or contact providers. It has no background polling or usage collectors. Opening it on several monitors shares one reader. See [Local agent status](56-agent-status.md) for the observation limits.

Hide it with `omarchy plugin disable omarchy.agent-execution`. The existing Agents usage widget can remain disabled. No widget or bar placement is enabled automatically.

The older combined label remains available on an already enabled Agents usage widget through `omarchy bar set omarchy.agents showExecutionDefault true --json`; use `false` to hide it. Both labels share one reader. Enabling the usage widget itself starts its normal collectors, which may contact providers. It is not required for the independent indicator.

An invalid or unreadable setting shows **Default: Unknown**, with neither execution row checked. Choose Host or Container and confirm to repair it. Use `omarchy agent mode` to display an error diagnostic. The label updates after changes made through the menu or CLI. After a manual file edit, use `omarchy-shell -q omarchy.agent-execution-default refresh` or reload the shell to refresh it.

## Per-launch command-line options

The ordinary CLI remains noninteractive unless its existing flow needs interaction. Project and agent selection are explicit options:

```bash
omarchy agent --agent pi --directory ~/Projects/project --container
omarchy agent --agent codex --directory ~/Projects/project --host --installed-only
```

`--agent=NAME` and `--directory=PATH` are also accepted. These options do not save defaults. The project is entered again inside a newly launched terminal so the launch does not depend on a terminal service inheriting its caller's working directory.

### Start in the current terminal

**The direct container CLI mounts the selected directory read-write.** It does not create an isolated clone. Select an existing workspace clone's project directory if you do not want to expose the original checkout.

Use `--inline` to run in the current terminal, including a Herdr pane, instead of opening a new terminal window:

```bash
omarchy agent --inline --container --agent pi --directory /path/to/project
```

The image selector and interactive agent use the current terminal. The command does not change the saved execution default. Omit `--container` to use that default. Without a terminal, the container does not allocate a pseudo-terminal or show the interactive image selector.

Running inside a Herdr pane does not guarantee that Herdr identifies the container agent. Its foreground host process can be Podman. Pane labels and a verified link between the pane and the container process are separate observations.

### Check without launching

`--check` checks the selected combination without starting an agent, creating a project, inspecting credentials, or pulling an image:

```bash
omarchy agent --agent pi --host --check
omarchy agent --agent pi --container --check
```

A successful host check prints its installed executable path. A successful container check validates the definition and command/runtime binding only. It does not prove that an image exists, the container engine is ready, or a model account has access. The normal launch still runs its runtime checks and image selector.
