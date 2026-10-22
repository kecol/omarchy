# Container workspace layout and trust boundaries

User instructions live in [Container workspaces](../manual/52-container-workspaces.md). The implementation is `default/workspaces/manager.py`, dispatched by `bin/omarchy-workspace-*`.

## Storage

The registry root is `$XDG_DATA_HOME/omarchy/workspaces`, or `~/.local/share/omarchy/workspaces` when the XDG variable is unset. It is private to the desktop user. Each name selects one directory containing:

- `workspace.json`: private versioned metadata and a random workspace ID. The container name, home volume name, and SSH alias are derived from that ID, not from a shared agent name.
- `repo/`: an independent clone when clone mode is selected. Mount mode points only at the explicitly selected directory instead.
- `identity` and `identity.pub`: a new client key pair for this workspace. Only the public key is mounted into the container.
- `known_hosts` and `ssh_config`: the container's pinned Ed25519 host key and loopback connection settings. No host SSH config includes or agent forwarding are used.
- `vscode-data/` and `vscode-extensions/`: independent local VS Code client data and the Remote SSH client extension. The manager requests the Codex extension only on the remote side.
- `operation.lock`: serializes start/code/stop operations for that workspace. Workspace creation has a separate registry lock.

Codex state and remote VS Code state live in the uniquely named Podman home volume at `/home/workspace`. The image does not receive host account directories, an engine socket, a graphical socket, or an SSH agent. Container host keys are generated on first start in that volume, not baked into the image. Losing or changing a host key requires an explicit recovery decision; the manager does not erase pins automatically.

## Runtime

The explicit build context is `containers/workspace/`. It supplies Node 24, Python, Git, basic Unix tools, and a non-root OpenSSH server. TLS verification and package verification remain enabled. The build and runtime disable automatic proxy-environment forwarding. The Pi harness image and account volumes are not reused.

The container has a read-only root, private temporary filesystems, a unique persistent home volume, one project bind mount, and a read-only authorized-public-key bind mount. The runtime sets keep-id user namespaces, drops all capabilities, prohibits new privileges, and enables cgroup limits. SSH is the only published port and binds to host loopback. SSH allows key authentication and local forwarding for VS Code Server, but no root/password login, agent forwarding, remote forwarding, X11, or tunnels.

Runtime checks inspect actual Podman settings as well as creation arguments. Podman 6 expands `--cap-drop=ALL` into individual capabilities and reports keep-id namespaces as `private`; do not assume inspect preserves those command-line spellings. The checks require the corresponding explicit creation arguments and reject contradictory normalized settings. The pasta network is separate from the host network namespace, but it is not an outbound access policy or a complete host-service firewall.

A workspace pins its first image ID. Starting an existing workspace does not pull, rebuild, or upgrade the image. Do not replace its home volume or merge it with another workspace to upgrade software; that can mix authentication and session state. An explicit upgrade/migration workflow is not part of this initial implementation.

## Editor and account separation

The launcher does not copy host VS Code settings, extension state, or Codex/Pi credentials. It creates private client settings that point Remote SSH at one generated configuration, request the remote Codex extension, and force that extension's workspace execution kind. Reopening refuses changed isolation-critical settings rather than silently accepting a local execution kind. The generated settings file must remain valid JSON; changing ordinary settings is allowed, but comments/trailing commas are not parsed by the manager.

The running extension host still needs interactive verification through VS Code. A separate client directory and Settings Sync being off cannot prevent an extension from exposing account-scoped cloud state. Codex authentication belongs to each workspace's own fresh login, not the Pi refresh-token pipeline. Do not import Pi credentials or enable SSH-agent forwarding for convenience.

## Tests and deployment

`test/shell.d/workspace-test.sh` runs Python regressions under fake user data directories. Real local Git repositories and disposable SSH client keys exercise cloning and filesystem separation. Container startup, SSH server readiness, and VS Code launches are mocked. Policy tests cover security drift, port exposure, resource limits, volume substitution, host-key changes, and distinct editor state.

The implementation also checked the exact launch arguments and full inspection policy against a stopped container on Podman 6.1.4, using an existing image for that API contract check. Its program was never started, and the temporary container and volume were removed. This is not a real workspace-image, SSH/server, or Codex integration test. Building the new image, connecting two actual VS Code windows, completing independent authentication, and verifying the remote extension host remain deployment acceptance steps. Do them only with explicit approval; a passing mocked test is not evidence that the interactive workflow has passed.
