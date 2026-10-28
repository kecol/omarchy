# Agent container images

An interactive `omarchy agent` launch in container mode shows the local image before starting the agent. The menu displays the agent, harness version, image reference, immutable image ID, build time, and saved Pi default from the container's persistent home. The saved default is a metadata preview; project settings or a resumed session can override it, and Pi checks availability after launch.

- Select **Run** to start the displayed image. This does not check for a new release or build an image.
- Select **Update to latest release** to resolve the latest public release for the reviewed harness. Confirm the current and target versions before the build starts.
- Select **Exit**, or press Escape, to leave without starting an agent.

If no local image exists, the menu offers **Prepare and run** and **Exit**. Preparation asks for confirmation (default Cancel), builds and checks the image, and starts that image only after success. See [first-run preparation](58-agent-container-preparation.md) for CLI preparation, prerequisites, and authentication limits.

After a successful update, the menu shows the new version. Select **Run** to start it. Omarchy checks the executable/version and disposable runtime fixtures before changing the local `latest` tag. Pi and Codex use the same backend with reviewed per-harness metadata. If building or validation fails, the previous image remains selected.

The `latest` tag means the most recently built and verified local image. It does not check the release server during each launch. The host Pi version and container Pi version can differ.

Updates do not change running containers or delete agent home volumes. Start a new agent session to use an updated image. No desktop reboot is required.

Managed tasks, one-shot prompts, and launches without an interactive terminal do not display this menu and do not update images automatically.

## Container agents inside Herdr

Run the interactive agent in the existing Herdr pane with `--inline`:

```bash
omarchy agent --inline --container --agent=pi --directory="/path/to/project"
```

When `HERDR_ENV=1` and stdin/stdout are terminals, Omarchy sets a host-side `HERDR_AGENT` hint for supported agents. Herdr can then identify the container wrapper and use that agent's screen manifest. The hint uses the selected agent, not the harness image name. The Cursor executable name maps to Herdr's `cursor` label. A hint does not make an unconfigured container harness available.

An explicit `HERDR_AGENT` value is preserved, including an empty value to opt out:

```bash
HERDR_AGENT= omarchy agent --inline --container --agent=pi
```

Omarchy does not add the automatic hint for host execution, new terminal windows, non-terminal launches, one-shot prompts or `--check`. The hint is scoped to the launched host process, not exported into the calling shell or added to the container environment. It does not mount Herdr sockets or host account directories, install integrations, report lifecycle state, or change an existing agent. Pi lifecycle hooks/session restore are separate from screen-manifest detection. Use a new launch after this launcher change; do not interrupt working agents just to update a panel label.

## Build from a command

Build the latest release:

```bash
omarchy harness build pi
omarchy harness build codex
```

Build a specific version:

```bash
omarchy harness build pi 1.4.0
```

Both commands verify the image before selecting it for future launches. Versioned tags remain available. When a different image replaces `latest`, the old image also receives the `previous` tag.

## Restore the previous image

This changes the image for future launches only:

```bash
podman tag localhost/omarchy-harness-pi:previous localhost/omarchy-harness-pi:latest
```

The launch menu resolves the displayed reference to an immutable image ID. Retagging `latest` while the menu is open does not change what **Run** executes.
