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

## Per-launch command-line options

The ordinary CLI remains noninteractive unless its existing flow needs interaction. Project and agent selection are explicit options:

```bash
omarchy agent --agent pi --directory ~/Projects/project --container
omarchy agent --agent codex --directory ~/Projects/project --host --installed-only
```

`--agent=NAME` and `--directory=PATH` are also accepted. These options do not save defaults. The project is entered again inside a newly launched terminal so the launch does not depend on a terminal service inheriting its caller's working directory.

`--check` checks the selected combination without starting an agent, creating a project, inspecting credentials, or pulling an image:

```bash
omarchy agent --agent pi --host --check
omarchy agent --agent pi --container --check
```

A successful host check prints its installed executable path. A successful container check validates the definition and command/runtime binding only. It does not prove that an image exists, the container engine is ready, or a model account has access. The normal launch still runs its runtime checks and image selector.
