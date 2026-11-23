# Native and terminal-visual verification plan

Status: The planned bounded scope is verified across separately approved attempts 03–05. Core cases passed in 03; fault-injected metadata refusal and held-selection replacement refusal passed in 04; graphical captures were inspected and main-process exit passed in 05. The original failures in attempts 01–04 remain unchanged. See [outcome.md](outcome.md) for source bindings, the shell-startup capture artifact and qualification limits. This plan records the completed scope and does not authorize another execution.

## Scope and admission

Use the inactive source candidate at `$HOME/Projects/omarchy-agent-container-shell`, branch `feature/agent-container-shell`, based on `1f879a93f309b8742d83145b9a0321cdd2d9c76a`. Compare its five implementation-file SHA-256 digests with [outcome.md](outcome.md) before testing. Do not integrate or dev-link the candidate to perform these checks.

Use one explicitly selected, already available immutable image with a configured non-root agent user, `/bin/bash` and a finite wait command. Do not pull, build, install, authenticate or launch an agent/provider. If no suitable image is available, stop and report that prerequisite. Existing production image and home tags/volumes must remain unchanged.

Create at most two disposable rootless containers with fresh synthetic instance UUIDs, distinct names, a unique verification nonce label and the standard managed-agent identity/workspace labels used by the launcher. Bind only a newly created synthetic project directory. Give each fixture a fresh home volume, not an existing agent home. Use a finite wait process instead of an agent as the main process. At least one fixture must start without init TTY or open stdin so that exec's independent terminal behavior is exercised.

Use the normal keep-id namespace, capability-drop and no-new-privileges controls, a read-only root, network disabled and private `/tmp` and `/run` filesystems of at most 16 MiB each. Limit each container to 256 MiB memory, no swap, 0.5 CPU and 64 tasks. Keep the whole manual verification within ten minutes; use a finite fixture main-process deadline no longer than that. Do not raise limits or retry a failed attempt automatically. Record max-only memory events separately; high/OOM/kill/task-limit events stop the attempt. Store only bounded metadata and synthetic terminal captures, with at most 16 MiB total retained evidence.

Before mutation, record each new object's full engine ID, nonce and owned volume/project identity. Never infer ownership from a name alone. Metadata observation is not proof of storage health or general runtime safety.

## Cases

1. Run the candidate command's metadata-only `--check` against one synthetic instance from a noninteractive host terminal. Confirm that it verifies the target without exec, installation or a terminal stream. Confirm that `--check` without an instance refuses before inventory.
2. Open the candidate shell picker in an isolated test terminal. Inspect agent, project, instance and start-time fields with two fixtures present. Capture only synthetic content. Verify Exit/Back defaults, cancellation and deliberate selection without clipping or accidental action. Do not replace or restart the desktop shell.
3. Choose **Open shell** for the non-TTY fixture. Verify an independent terminal, the configured container user, working directory and synthetic home, and the inability to write the read-only root. Create only a small synthetic marker in the fixture project/home. Confirm that the other fixture receives no marker or exec process.
4. Exercise Ctrl+C inside the maintenance shell and confirm the controller remains attached to that shell until explicit exit. Use `exit` and Ctrl+D in separate explicitly selected entries; confirm return to selected-instance actions and no container stop. Use a direct selected-instance invocation with a nonzero shell exit to verify exit-status propagation. These are distinct cases, not automatic retries.
5. Hold a picker selection, then stop only its identity-verified disposable fixture. If testing name replacement, create the second fixture under the released name with a different full ID and instance identity. Attempt the held selection and confirm refusal or exact-ID engine failure, never exec in the replacement. Record both original client outcomes. Do not weaken the inventory's existing name/label checks to admit the replacement.
6. Use a controlled unavailable-metadata fixture to verify visible refusal and no empty-success claim, without disabling the user's real engine or changing its configuration. Keep this result explicitly fault-injected, not native engine-failure qualification. The existing offline fixtures cover malformed observations and changed process/namespace metadata; do not manipulate real host namespaces to manufacture those cases.
7. Open a shell in a disposable fixture, then let its finite main process exit. Confirm that the exec session ends under the unchanged container lifecycle and that the controller does not restart anything. Do not use a user's working harness to demonstrate this behavior.

## Results and cleanup

Retain full relevant command exit statuses, selected source digests and bounded per-container metadata. Do not capture prompts, credentials, real conversation contents, host process environments or unrelated terminal output. Distinguish native exec/PTY observations, injected failures and source/fixture checks in the result.

On success or failure, wait for the original exec clients. Stop/remove only containers whose full IDs and nonce still match the recorded owned objects. Remove only the newly created volumes and synthetic project directory after verifying that no owned process uses them. Never prune the engine or clean unrelated containers, images, caches or homes. If ownership or completion cannot be verified, stop and retain an explicit operator-follow-up record instead of broad cleanup.

Verify and record the final owned-object inventory. Review synthetic screenshots for clipping, correct selection and return-to-menu behavior under `agents/skills/visual-verification.md`. Mark native or visual delivery incomplete for every blocked or unexecuted case. Any source activation, publication or archive requires separate approval after review.
