# Container workspaces for VS Code and Codex

Use one workspace name for each independent project or agent context. Each workspace has its own rootless container, home volume, SSH keys, Codex state, VS Code Server, and local VS Code application data. Two windows opened for different workspace names do not use the same local session files.

These workspaces use Remote SSH, not Dev Containers. Do not mount a Docker or Podman socket to make an editor connect.

## Requirements

Use VS Code, Python 3, Git, OpenSSH client tools, and rootless Podman with cgroup v2 and the pasta network backend. Run the commands as your desktop user, not under sudo. Run `workspace code` from a desktop terminal with a graphical display. Headless shells can use `workspace start` and its SSH command, but cannot open the desktop window. The dedicated workspace image is separate from the Pi agent harness.

Building the image downloads its base image and packages. Creating a workspace does not build an image or start a container. Starting and opening a workspace never pull or build images automatically.

```bash
omarchy workspace build
```

The build uses the current user's UID/GID. Each workspace pins the image ID on its first start. Rebuilding the image updates the tag for new workspaces; it does not silently replace existing workspace images.

## Open from the desktop menu

Open **Agents → Workspaces**. Select an existing workspace, or select **Create from Project**, choose a project directory, enter a unique workspace name, and select file access.

**Isolated Git Clone** copies committed Git HEAD only. It does not include uncommitted or untracked files, and it removes the source remote. **Live Host Directory** permits immediate changes to the selected host files, including ignored files. Review that directory for secrets before granting access. Non-Git directories require an explicit live-directory choice; the menu does not make that choice automatically.

A review terminal shows the full paths and access warning before creation or opening. **Cancel is selected by default.** Confirm to create the workspace if needed and open its isolated VS Code window. The first editor setup downloads its server and extensions. The menu does not build or pull container images, install VS Code, start a separate agent harness, or change the default agent execution mode.

If creation succeeds but the editor cannot open, the workspace remains listed. Fix the reported prerequisite, then select that existing workspace to retry. Do not create another workspace with the same name.

The workspace list is read-only. `omarchy workspace list --json` returns names, source and workspace paths, access modes, and a bounded runtime-state snapshot. If the engine cannot answer, the state is `unknown`; this does not mean the container stopped. Listing does not start containers or audit their isolation. Opening still runs the existing backend checks.

## Two independent projects

By default, create makes an independent clone of committed Git HEAD. It does not include uncommitted or untracked files. It does not use hard links or a shared Git object store, and it removes the clone's source remote. The source checkout is not mounted in the container.

```bash
omarchy workspace create pi-evolving ~/Projects/gits/pi-evolving
omarchy workspace create other-project ~/Projects/other-project

omarchy workspace code pi-evolving
omarchy workspace code other-project
```

Each `code` command starts its workspace if needed and opens a new remote VS Code window. It uses private local user-data, extension, shared-storage, and agent-data directories, turns VS Code Settings Sync off, installs the Remote SSH client extension there, and requests installation of `openai.chatgpt` on the remote host. It does not install Codex in the local extension directory. The initial extension installation and server bootstrap need network access.

The first launch can show VS Code onboarding. You may select **Continue without Signing In**; a GitHub login is not required for Remote SSH or Codex. Accept Workspace Trust only for code you intend to work on. The launcher does not disable VS Code's trust checks.

Use **Developer: Show Running Extensions** to verify that Codex runs on the remote workspace. Use **Codex: Open Codex Sidebar** if its panel is not visible. For the checks below, select **Terminal: Create New Terminal (In Active Workspace)**. Do not select **Create New Integrated Terminal (Local)**: that terminal runs on the desktop host, outside the container.

Check the remote terminal:

```bash
printf 'HOME=%s\nCODEX_HOME=%s\n' "$HOME" "$CODEX_HOME"
pwd
```

Expected values are `/home/workspace`, `/home/workspace/.codex`, and `/workspace`. The same paths refer to different filesystems in different workspace containers.

Authenticate Codex separately inside each remote workspace. Do not copy or mount host `~/.codex`, `~/.pi`, or `~/.ssh` directories. This does not use the Pi/OpenShell credential broker. Remote/browser callback behavior depends on the installed Codex extension; use its supported device-code flow when available if browser callbacks reach the wrong local window. Do not share host auth files to work around login problems.

Separate local state does not create separate OpenAI accounts. Account limits and any account-scoped cloud tasks or history can remain shared. Use different accounts if server-side account separation is required.

Opening the same workspace name twice intentionally uses that workspace's existing state. To get two independent Codex contexts for the same source repository, create two different names using the same source path.

## Direct directory access

A direct mount lets the container change the supplied host files immediately. It includes untracked and ignored files, which can contain secrets. Review the directory before granting this access. The command refuses known credential, system, and workspace-state directories, but it is not a general secret scanner.

```bash
omarchy workspace create direct-project ~/Projects/project --mount
omarchy workspace code direct-project
```

Direct mounts also support non-Git directories. The active Omarchy source tree cannot be mounted read-write because its commands can run on the host with elevated privileges; use a clone. Linked Git worktrees are not supported in direct-mount mode; use a clone. Two workspaces that mount overlapping host directories share those files even though their Codex and editor state remain separate.

## Lifecycle and SSH access

```bash
omarchy workspace list
omarchy workspace start pi-evolving
omarchy workspace doctor pi-evolving
omarchy workspace stop pi-evolving
```

`start` prints a workspace-specific SSH command. Its private SSH configuration does not use your personal SSH identities or agent. The endpoint binds only to host `127.0.0.1`; its port is assigned by Podman. Host keys are obtained through the local container engine and pinned. A changed host key fails instead of silently replacing the pin.

`doctor` checks an existing container's identity, mounts, security settings, image, published port, and resource limits. It does not prove that a particular extension runs remotely or that an account's cloud history is isolated.

Stopping retains the project, home volume, authentication, and editor history. Closing a VS Code window does not stop the container. There is no automatic destructive removal command. Each container has a 4 GiB memory limit with swap disabled, a 512-process limit, and a two-CPU quota. Two workspaces can use 8 GiB in total; budget for the host and other programs.

## Review and testing boundaries

For clone mode, review and export changes from inside the remote workspace, then apply a reviewed patch to the original checkout explicitly. The launcher does not copy changes back. Treat an agent-modified clone's Git configuration and hooks as untrusted; do not run its build scripts or Git hooks on the host merely to review it.

The `pi-evolving` repository itself manages Docker/Compose containers. Editing it in a workspace does not grant permission to control the host engine. Test that container-management workflow in a separate VM or an explicitly controlled runner. Do not add an engine socket, privileged mode, host networking, or host credential mounts to make those tests run.

Codex's own approval and sandbox settings remain at their defaults. If its nested sandbox fails inside the container, investigate it rather than adding privileged mode or weakening the container policy automatically.

Containers share the host kernel. Outbound network access is not brokered or restricted to model-provider endpoints. Disabling pasta gateway mapping is not a complete host-service firewall; Podman host aliases and reachable services require a separate network policy. Use a VM or a policy-controlled runtime when the threat model requires a stronger boundary.
