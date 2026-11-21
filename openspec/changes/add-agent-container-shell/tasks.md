# Tasks

## 1. Exact-instance shell execution

- [x] 1.1 Add shell-specific target verification and fixed interactive Bash exec in `default/agents/session-menu.py`, reusing the existing inventory, UUID selection and fingerprint boundary without requiring init TTY/open-stdin. Extend `test/shell.d/fixtures/agent-session-menu-test.py` to verify exact full-ID execution, replacement refusal, process/namespace changes, unavailable observations and no automatic fallback; retain existing attach/close regression behavior.
- [x] 1.2 Preserve the exec child's local-engine selection, configured container access and direct terminal streams. Extend the same fixture to verify removal of both remote selectors only from the child environment, absence of user/privilege/mount/environment-forwarding options, foreground-terminal refusal, inherited uncaptured streams and propagation of nonzero exec results. Document this execution boundary in `docs/managed-agents.md` without claiming universal containment or native qualification.

## 2. Command and picker integration

- [x] 2.1 Add metadata-bearing `bin/omarchy-agent-shell` and controller argument parsing for an optional instance plus metadata-only `--check`. Verify selector-based checks execute no container commands, work without a terminal and reject `--check` without a selector; verify help/routing through the repository's existing metadata checks. Document the direct interface and the limits of `--check` in `manual/60-agent-session-menu.md`.
- [x] 2.2 Add the shell picker and **Open shell** to the existing sessions actions, with distinguishing start time and existing sanitized project/instance metadata. Extend the existing fixture to verify cancellation, Exit/Back defaults, explicit selection, return to selected actions and no automatic stop or retry. Update `manual/60-agent-session-menu.md` and `docs/managed-agents.md` to distinguish attach from exec and warn about shared files/home, container startup files and unchanged harness-owned lifetime.

## 3. Focused integration and verification handoff

- [x] 3.1 Run the existing session-menu suite and applicable focused command-metadata checks against the inactive implementation candidate, retaining complete output in log files. Review the diff for unchanged attach/close, launcher, task, recipe, credential and desktop contracts; report any baseline failures separately rather than expanding this change.
- [x] 3.2 Deliver a bounded disposable native/terminal-visual verification plan and an implementation outcome record within this change. Identify the synthetic container/project/home inputs, exact-target replacement and unavailable-state cases, terminal exit behavior, current source binding and owned cleanup. Mark native/visual checks not run until separately approved and completed; verify the record does not present mocked controller results as native or visual success.

## Current status and permission boundaries

Source implementation is available in the inactive candidate `$HOME/Projects/omarchy-agent-container-shell`, branch `feature/agent-container-shell`, based on `1f879a93f309b8742d83145b9a0321cdd2d9c76a`. The focused session-menu suite passed 34 offline unittest methods; command metadata, bin style, syntax and whitespace checks passed. See [outcome.md](outcome.md) for source bindings and evidence limits.

The bounded native/terminal-visual scope is verified across separately approved attempts 03–05. Core native cases passed in 03; fault-injected metadata refusal and held-selection replacement refusal passed in 04; graphical captures were inspected and main-process exit passed in 05. See [outcome.md](outcome.md) and [verification-plan.md](verification-plan.md) for the unchanged earlier failures, startup capture artifact, source bindings and scope limits. All disposable fixtures, volumes and test windows were removed; the owned slices were stopped and their runtime properties reverted. Final source review and a local commit are approved. No active source integration, publication, merge, image build, agent/provider launch or archive occurred. The active checkout's pending `AGENTS.md` and `docs/project-goals.md` work remains untouched.

## Workflow follow-up

- Obtain separate approval before any live container or graphical verification. Use disposable credential-free containers, not existing working agent sessions. Keep native/visual delivery incomplete if those checks are blocked or not run.
- Local source review and commit are approved. Obtain separate approval before publication, merge or active-checkout integration. No image build, package operation, migration, refresh or agent restart is required by this design.
- Synchronize the new capability and archive only after the required review and separate approval. Planning completion does not establish implementation or runtime qualification.
- Explore optional plain-Pi versus Herdr-plus-Pi presentation after the shell picker is delivered. Conversation locations, credentials, concurrent writers and separate Herdr state remain undecided and outside this change.
