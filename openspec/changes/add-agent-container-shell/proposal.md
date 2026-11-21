# Proposal

## Why

Users need an independent maintenance terminal in a running agent container without guessing which container belongs to their project or sharing the harness's input. An identity-aware shell action improves desktop usability while preserving exact-target control and existing container restrictions.

## What Changes

- Add `omarchy agent shell [<instance-uuid-or-prefix>] [--check]`. Without an instance, open an on-demand picker; an explicit selector identifies one existing instance. Require a selector with `--check`.
- Add **Open shell** to the selected-instance actions in `omarchy agent sessions`. Retain Exit and Back as the default choices.
- Display agent, project, instance and start time for selection. Revalidate the selected full container ID and process fingerprint before executing a fixed Bash command inside that container.
- Keep the shell separate from attachment. Inherit the user's terminal directly and do not capture shell output or send automatic input.
- Preserve local rootless routing, configured container user, mounts, read-only root and resource controls. Do not add a root-user override or privileged execution.
- Document that shell exit does not stop the harness, but harness exit still stops the container and its shell processes.

### Observed behavior and agreed direction

At proposal time, `default/agents/session-menu.py` supported attachment and explicit closure, not a second shell. `default/agents/sessions.py` already supplied current-user inventory, UUID-prefix selection and process/container fingerprints. `bin/omarchy-agent-run-podman` uses the harness as the entrypoint and enables automatic container removal. The delivered shell action extends terminal access only; it does not replace this lifecycle. See [outcome.md](outcome.md) for the implemented behavior, scoped verification and source activation.

### Non-goals and unverified assumptions

Herdr, SSH, persistent container owners, restart/resume, conversation sharing, extension installation, image builds, credential transfer, arbitrary command execution options and changes to task execution are excluded. Host agents, editor workspace containers and remote engines are not shell-picker targets. Bash exists in the bundled recipes. Real terminal execution was subsequently verified within the bounded local x86 scope recorded in [outcome.md](outcome.md); compatibility with arbitrary custom images, other platforms and untested terminal configurations remains unverified. Missing Bash must fail without installation or fallback.

## Capabilities

### New Capabilities

- `agent-container-shell`: Explicit independent terminal access to one verified running agent container, including picker behavior, identity checks, local routing and unchanged lifecycle.

### Modified Capabilities

None. Existing runtime-availability and stop-target-binding requirements remain unchanged; the new capability applies corresponding refusal and exact-target principles to shell execution.

## Impact

Expected implementation paths are a new `bin/omarchy-agent-shell`, `default/agents/session-menu.py`, the existing session-menu tests, `docs/managed-agents.md` and `manual/60-agent-session-menu.md`. The implementation should reuse `sessions.py` without changing its inventory or close contracts. The CLI router already discovers `agent-*` commands through metadata.

The agent-safety effect is reducing mistaken-target execution while preserving failure refusal. The upstream integration benefit is a narrow addition to fork-owned terminal control, without changing Quickshell, launch policy, container recipes or upstream desktop services. No new dependency, migration, saved default or host configuration change is planned. Planning does not authorize implementation, runtime access, activation or publication.
