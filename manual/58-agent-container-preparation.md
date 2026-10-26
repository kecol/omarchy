# First-run agent container preparation

A fresh install needs no pre-existing agent image or running container. In Container mode, an interactive agent launch offers **Prepare and run** when its image is missing. Preparation uses a reviewed bundled recipe; it does not install the agent on the host.

Pi and Codex have bundled definitions and recipes. Other agents are not automatically given generated recipes. Unsupported Container defaults are rejected before saving or installing anything on the host. Selecting a supported default validates its recipe, not engine readiness or authentication.

## Prepare without starting an agent

```bash
omarchy agent prepare --agent codex
omarchy agent prepare --agent pi
```

An existing matching local image is reused without release lookup or rebuilding. Otherwise a confirmation, defaulting to Cancel, explains the download/build and disposable checks. No saved execution mode is changed.

Check only that a reviewed recipe and launch definition exist:

```bash
omarchy agent prepare --agent codex --check
```

This does not query Podman, release servers, images, or provider accounts. Explicit unattended preparation is available:

```bash
omarchy agent prepare --agent codex --yes
omarchy agent prepare --agent pi --yes --version=1.4.0
```

`--yes` authorizes image preparation, not package installation, privileged setup, authentication, or an agent launch. Missing Podman/rootless prerequisites stop with instructions; they are never silently installed or repaired. Managed tasks and noninteractive agent launches still do not build automatically.

## What preparation checks

Omarchy uses reviewed bundled recipes and an explicit build-context allowlist. It does not generate recipes or accept arbitrary build commands from user definitions.

Public version lookup runs with an empty temporary home/config/data/cache, without host project hooks, installed-agent dependencies, account configuration, or credential environment variables. Image preparation and execution use the local rootless engine, ignoring remote engine defaults.

A private candidate image is built before changing stable tags. Builds use a user scope configured for 2 GiB memory, two CPUs, and 512 tasks, plus container memory/CPU flags and a 30-minute timeout. No unrelated service is restarted. Validation has no network and uses only an empty disposable home volume and temporary project fixture. It checks:

- the exact executable/version output;
- non-root execution, read-only root mount, dropped effective capabilities, and no-new-privileges;
- project writes, writable tmpfs, and home persistence across disposable containers;
- absence of the usual engine sockets and SSH-agent variable.

Checks do not copy personal credentials or mount the host home, SSH agent, or engine sockets. Disposable test state and the candidate tag are cleaned up. Failures do not promote the candidate to `latest`; an existing working image remains available. Existing running agents and their homes are not changed.

For development qualification without changing production agent tags:

```bash
omarchy harness build pi 1.4.0 --candidate-only
```

This still downloads/builds and validates. It reports the verified image ID, removes only its private candidate tag, and leaves `latest`, version, and `previous` tags unchanged. The untagged image remains available by ID for inspection; promotion is a separate explicit operation.

This is environment readiness, **not** proof of complete isolation, model access, successful agent tool use, or provider authentication. Trust in the bundled recipe, public package sources, base image, and local engine configuration remains necessary. These checks do not attest engine hooks or prove protection against a compromised host.

## Launch and authenticate separately

```bash
omarchy agent --inline --container --agent codex --directory /path/to/project
```

An inline project directory is a **read-write bind mount**, not a private clone. Use the Workspaces workflow for an independent editor workspace. Editor containers and their account stores are not reused for this harness.

Authentication belongs to the agent's explicit in-container sign-in flow and persistent container home. Host sign-in state is not copied during preparation. No provider request is used as a readiness test, and failure never silently falls back to Host.

See [image selection and rollback](53-agent-container-images.md) for updates and previous-image recovery.
