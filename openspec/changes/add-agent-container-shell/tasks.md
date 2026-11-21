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

Source implementation was prepared in the inactive candidate `$HOME/Projects/omarchy-agent-container-shell`, branch `feature/agent-container-shell`, based on `1f879a93f309b8742d83145b9a0321cdd2d9c76a`, then committed as `9eae668dd7aed58bc021370505ecd7b0f552a379`. [PR23](https://github.com/kecol/omarchy/pull/23) merged as `db9ba29a434bd21f0d183ed7b972a0d96aabd63c`, which is now source-active after separately approved integration and permission correction. The focused session-menu suite passed 34 offline unittest methods; command metadata, bin style, syntax and whitespace checks passed. See [outcome.md](outcome.md) for source bindings and evidence limits.

The bounded native/terminal-visual scope is verified across separately approved attempts 03–05. Core native cases passed in 03; fault-injected metadata refusal and held-selection replacement refusal passed in 04; graphical captures were inspected and main-process exit passed in 05. All disposable fixtures, volumes and test windows were removed; the owned slices were stopped and their runtime properties reverted. The original native failures and startup capture artifact remain explicit in [outcome.md](outcome.md) and [verification-plan.md](verification-plan.md).

Feature-head Tests `44917255058` and post-merge Tests `44918793323` each completed 454 test files without failures; eight files contained skipped checks. The focused CI session-menu log confirms 34 methods passed without skips; translation checks `44917255103` passed. CI regression coverage does not replace the bounded native/visual evidence or qualify skipped cases. The failed publication attempt, merge-preflight command-control error and failed activation permission postflight remain distinct from their subsequent verified outcomes in [outcome.md](outcome.md).

The active checkout's pending `AGENTS.md` and `docs/project-goals.md` work remains untouched. Seven original planning files remain in a private backup; active copies are now tracked. Activation ran only a help-routing check, not inventory or container entry. No image build, package operation, migration, agent/provider launch or agent restart occurred during source delivery. All six original tasks remain complete. This documentation reconciliation is local, uncommitted and unpublished; main-spec synchronization and archive have not occurred.

## Workflow follow-up

- The bounded native/visual scope is complete with its recorded limitations; it is not standing permission for another invocation. Obtain separate approval for any new live verification and use disposable credential-free containers, not working agent sessions.
- Source commit, publication, merge and activation are complete. Review this documentation reconciliation and obtain separate approval before committing or publishing it. No image build, package operation, migration, refresh or agent restart is required.
- Synchronize the new capability and archive only after the required review and separate approval. The unchanged delta contains seven requirements and fourteen scenarios. Tracking completion does not renew runtime qualification.
- Explore optional plain-Pi versus Herdr-plus-Pi presentation after the shell picker is delivered. Conversation locations, credentials, concurrent writers and separate Herdr state remain undecided and outside this change.
