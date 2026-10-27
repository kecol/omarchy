# Inspect an existing harness from its terminal

Run this command in a host terminal as your normal desktop user:

```bash
omarchy agent sessions
```

You can also right-click the execution-default widget and select **Inspect sessions…** in its overview. This opens the same menu in a host terminal. Opening the menu does not attach to or close any instance. The overview action remains available when a snapshot is empty or unavailable; the menu performs its own fresh checks.

When `omarchy agent status` or `omarchy agent diagnose` observes a managed harness, its text report includes the command as a hint. JSON reports do not include the hint or change their schema.

Choose a running harness by agent, instance prefix, host PID, and project directory. The selected-instance view shows the full UUID, container name, start time, and project paths. Long project labels are shortened only in the list; the controller retains the original target identity.

The action menu offers:

- **Back**: return to the list. This is the default action.
- **Attach existing harness**: connect your terminal to the running container's main process.
- **Close (10-second grace)**: ask for confirmation before stopping that instance.
- **Force close**: ask for confirmation before sending an immediate kill to that instance.

The selected snapshot is always shown above the action menu without reading harness output. Cancelling a close returns to that action menu. The menu clears only its visible terminal area between views; it does not clear scrollback.

Exit is the default list choice. Refresh fetches new metadata on demand. There is no background polling, automatic cleanup, or automatic closure after attachment.

## Attach and detach

**Attachment shares input and terminal resizing with any terminal already attached. Your keystrokes can change the agent's state. Ctrl+C may interrupt the agent even though the controller disables host-signal proxying.**

Select Attach existing harness only when you intend to inspect that session. Detach without stopping it with **Ctrl+P, then Ctrl+Q**. The menu then returns to the same selected instance. Choose Back to refresh the list or explicitly select a close action after inspection.

Attachment connects to the existing process. It does not start another Codex/Pi process, execute a new shell, restart a stopped container, replay stored logs, or scrape a screen. The screen might not redraw immediately; a blank or incomplete display is not proof of abandonment. Detaching is not a close action. A nonzero attach exit does not trigger a fallback or retry.

The harness stream goes directly to your terminal, without controller output capture or recording. Your terminal's own scrollback behavior still applies. Do not share screenshots or pasted output containing device codes, credentials, prompts, or other private content.

A running container with an allocated terminal is not proof that it already has an attached host terminal. Authentication state and work state are not inferred from attachment capabilities.

## Direct command

You may attach to a unique instance UUID or prefix of at least eight hexadecimal UUID characters:

```bash
omarchy agent attach 11111111 --check
omarchy agent attach 11111111
```

Replace the example prefix with an instance from your list. `--check` validates current identity and interactive capabilities without opening the terminal stream. The interactive command requires a foreground controlling host terminal so detach keys can work. A background job or synthetic terminal without a controlling terminal is rejected. It verifies the full immutable container ID, current-user process identity and namespaces, running state, allocated terminal, and open standard input before attachment.

Stopped, missing, changed, ambiguous, and unsupported targets are rejected. Nothing is restarted. Harnesses launched with automatic removal normally disappear after their main process exits. Editor workspace containers are not targets of this menu.

**Closing can discard work or interrupt file writes.** Both menu close actions default to No and revalidate the exact original instance after confirmation. Shared homes and project volumes are not deleted. Use [agent diagnostics](59-agent-session-diagnostics.md) when you need read-only evidence rather than interactive access.
