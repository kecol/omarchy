# Design

## Context

See [proposal.md](proposal.md) for motivation and scope. This design is warranted because an additional container-execution action crosses identity, engine-selection and terminal boundaries. It records the reviewed implementation plan and its pre-implementation context; prospective wording below does not describe current delivery status. See [outcome.md](outcome.md) for publication, CI, merge, source activation, retained failures and qualification limits.

`default/agents/session-menu.py` owns the current terminal picker, attachment and close menus. It uses `sessions.inventory(..., diagnostics=False)`, `sessions.select()` and `sessions.fingerprint()` from `default/agents/sessions.py`. Inventory validates local rootless engine state, container labels/names, current-user init process ownership/start time and PID/mount namespaces. The fingerprint includes instance, agent, full container ID, name, init PID, boot ID, start ticks and namespaces.

`verify_attach()` additionally requires the container init to have a terminal and open standard input. Those flags are attachment requirements, not exec requirements. `status.Query` bounds metadata collection and removes ambient engine selectors in a child environment. Interactive attach currently uses a separate direct subprocess; its environment handling must not be copied unchanged into the new shell action.

`bin/omarchy-agent-run-podman` retains the harness as entrypoint, `--rm`, a read-only root, private temporary filesystems and existing workspace/home mounts. The [control-plane draft](../../../plans/agent-control-plane.md) proposes stronger durable-session behavior; this change does not implement that draft. The [work ledger](../../history/work-ledger.md) preserves earlier delivered identity and availability safeguards without qualifying this new action.

## Goals / Non-Goals

**Goals:**

- Reuse the existing instance-selection and identity owners instead of creating a second container inventory.
- Distinguish a separate maintenance exec terminal from attachment to harness input.
- Keep controller decisions metadata-only and fail closed when required observations fail.
- Add one command and one existing-menu action without changing desktop services or container startup.

**Non-Goals:**

- No universal containment, authenticated-label ownership, atomic admission or protection from a malicious process with the same host-user authority.
- No new execution permissions for coding agents, task-state transitions or automatic maintenance commands.
- No Herdr, shared-conversation design, image rebuild or container persistence mechanism.

## Decisions

### 1. Reuse the session-menu controller and instance selector

Add a thin metadata-bearing `bin/omarchy-agent-shell` wrapper that invokes the controller's new `shell` operation. The interface is `omarchy agent shell [<instance-uuid-or-prefix>] [--check]`. No selector opens a shell-specific picker. Require an explicit selector for `--check`, which remains metadata-only and works without a terminal.

Use the same inventory, UUID-prefix grammar and sanitized metadata rendering as the session menu. Add start time to the existing distinguishing list fields and retain full project information in the selected view. Do not parse display labels to reconstruct targets. The shell picker must allow Exit and explicit Refresh; the existing sessions menu retains Back as its default selected-instance action and gains **Open shell**. After shell exit, return to selected-instance actions rather than executing a second action automatically.

Alternative: list arbitrary Podman containers and exec by name. Rejected because it discards the existing eligibility and identity boundary and can select an editor or unrelated container.

### 2. Separate exec eligibility from attachment capabilities

Implement shell-specific verification in `session-menu.py`, reusing inventory and fingerprint comparison without calling `verify_attach()`. Immediately before exec, obtain a fresh inventory, resolve the original UUID, compare its fingerprint, validate the full ID, inspect the target's running state and init PID, and recheck process start identity and namespaces. Recheck boot identity against the original fingerprint. Reject changed, missing, malformed or ambiguous observations.

Do not require `.Config.Tty` or `.Config.OpenStdin` for exec. Podman allocates a new exec terminal independently. Leave `verify_attach()` and all close validation semantics unchanged; a small shared validation extraction is acceptable only if focused tests preserve those contracts.

Submit one exec request using the validated full container ID. An instance that exits between verification and exec may cause engine failure. Do not retry, target a name or claim an atomic validation-and-execution transaction. Full-ID targeting prevents replacement-by-name, but cannot eliminate every same-ID restart race with another actor.

### 3. Execute a fixed shell without widening access

The action is a direct subprocess equivalent to `podman --remote=false exec --interactive --tty <full-container-id> /bin/bash -i`. Use the container's configured user, working directory and environment. Do not add `--user`, `--privileged`, host environment forwarding, mounts, credentials or socket access. No arbitrary command or shell-path option is exposed.

Create a copied environment for the interactive Podman child, remove `CONTAINER_HOST` and `CONTAINER_CONNECTION`, and leave the parent untouched. Metadata continues through the existing bounded `status.Query` path. Interactive streams must not pass through the bounded query collector: inherit stdin, stdout and stderr and wait for the shell process normally. Metadata collection remains bounded; an explicitly opened user shell is not subject to the metadata deadline.

Use the existing foreground-controlling-terminal check for actual shell entry. Adapt wording where needed so shell errors do not falsely describe attachment. Show target metadata and explain that the shell shares project files and the container home with the harness. A separate terminal does not isolate file writes or secrets from the harness. Bash startup files inside the container may run; the controller must not read their contents or imply that entering a shell is read-only.

Alternative: attach and attempt to send shell commands through harness input. Rejected because that is neither a separate terminal nor a reliable maintenance interface.

### 4. Preserve lifecycle and distinguish exit results

The direct command returns the exec subprocess exit status. The menu reports a nonzero result and requires another explicit action; it never automatically retries or closes the container. Shell exit alone causes no registry or assignment write. Existing explicit close actions remain available and unchanged.

If the harness exits, Podman can terminate the exec shell and remove the container. The controller must report the ended or failed shell without recreating anything. Missing `/bin/bash` fails at exec, not through a preparatory container probe or automatic installation. `--check` verifies metadata, not executable availability.

### 5. Keep integration and validation narrow

Extend `test/shell.d/fixtures/agent-session-menu-test.py` through its existing `agent-session-menu-test.sh` entrypoint. Exercise the real controller's selection, validation and subprocess construction with controlled observations. Cover exact-ID execution, name replacement, process/namespace changes, unavailable inventory, cancellation, terminal refusal, `--check`, child-only remote-selector removal, return-to-menu behavior and exit-status propagation. Keep existing attachment/close cases as regressions. Verify that a running target without init TTY/open-stdin remains eligible for exec but not attach.

These fixtures validate controller logic, not native Podman PTY behavior. After separate runtime approval, use only disposable, credential-free containers and synthetic project/home data for native shell and terminal checks. Do not enter a working user container to validate the implementation. Verify the changed terminal menu visually under the repository's visual-verification procedure before claiming UI delivery. Record blocked or not-run native/visual checks rather than substituting mocked success.

Update `docs/managed-agents.md` so its current controller-wide statement that no shell is executed becomes an action-specific distinction. Update `manual/60-agent-session-menu.md` with picker/direct invocation, shell exit, shared-file risks and the unchanged harness-owned lifetime. Do not change QML, the desktop menu catalog, runtime collectors or the CLI router unless inspection reveals a concrete routing defect; stop before expanding that scope.

## Risks / Trade-offs

- [Harness exit terminates maintenance] Mitigation: explain this before entry and in the manual; retain lifetime changes as separate future work.
- [Concurrent shell and harness writes conflict] Mitigation: display the selected project/home context and warn that maintenance is not serialized or isolated from harness writes. Do not install an extension automatically.
- [Container images lack Bash or tools needed by an extension] Mitigation: fail without fallback or installation. The feature does not qualify extension support.
- [Container selection changes after observation] Mitigation: fresh fingerprint checks, full-ID execution and no fallback. Retain the remaining non-atomic race limitation explicitly.
- [Shared helper edits affect attach/close] Mitigation: prefer a shell-specific verifier and run existing session-menu regressions. Avoid a controller-wide rewrite.
- [Active checkout is dev-linked] Mitigation: implement later in an inactive candidate; keep integration into the active checkout separately approved. Preserve pending goal-document edits.

## Migration Plan

No data or configuration migration is needed. A later approved source integration exposes the command and menu action without rebuilding images, copying homes, changing defaults or restarting running agents. That integration is activation and remains a separate gate.

Rollback removes the new command and shell operation/menu action and restores action-specific documentation. No shell-owned persistent state exists to delete. Reverting source does not terminate an already opened shell; any runtime closure requires its own explicit target selection and approval. Commit, publication, merge and archive remain separate actions.
