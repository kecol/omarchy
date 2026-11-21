# Inspect an existing harness from its terminal

Run this command in a host terminal as your normal desktop user:

```bash
omarchy agent sessions
```

You can also right-click the execution-default widget and select **Inspect sessions…** in its overview. This opens the same menu in a host terminal. Opening the menu does not attach to or close any instance. The overview action remains available when a snapshot is empty or unavailable; the menu performs its own fresh checks.

When `omarchy agent status` or `omarchy agent diagnose` observes a managed harness, its text report includes the command as a hint. JSON reports do not include the hint or change their schema.

Choose a running harness by agent, instance prefix, host PID, project directory, and start time. The selected-instance view shows the full UUID, container name, start time, and project paths. Long project labels are shortened only in the list; the controller retains the original target identity.

The action menu offers:

- **Back**: return to the list. This is the default action.
- **Attach existing harness**: connect your terminal to the running container's main process.
- **Open shell**: open an independent Bash terminal inside that same container. This does not attach to harness input.
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

## Open an independent maintenance shell

**The shell shares project files and the container home with the harness. Concurrent writes can conflict, and Bash startup files in the container can execute. The shell is not read-only or isolated from the harness's credentials.**

Use **Open shell** in the selected-instance menu, or open the shell picker directly:

```bash
omarchy agent shell
```

The shell picker offers Exit and Refresh, then Back and Open shell for the selected instance. It does not select an instance automatically, even when only one is running. It lists Omarchy agent containers, not host agents, remote machines, or editor workspace containers.

To open a shell for a known instance, use its full UUID or a unique prefix of at least eight characters:

```bash
omarchy agent shell 11111111
```

Use `exit` or Ctrl+D to leave the shell. Menu entry returns to the selected-instance actions; the direct command returns the shell or engine exit status. Shell exit does not stop the harness or delete the container home.

**Exiting the harness still stops the container and its maintenance shells.** Opening a shell does not keep the container alive or preserve shell jobs after it stops. There is no automatic restart, conversation resume, or Herdr session.

The shell uses the container's configured user, working directory, environment, mounts, and resource limits. It adds no root-user override, host credentials, or socket mounts. Changes saved in the existing project or persistent home remain subject to their existing sharing rules; temporary files can disappear with the container. A read-only container root still prevents system package changes. Missing Bash or a failed exec produces an error without installing software, switching to a host shell, or retrying another container.

You can validate an explicit target without opening a terminal or executing a container command:

```bash
omarchy agent shell 11111111 --check
```

`--check` requires an instance. It validates current identity and running state, not Bash availability or permission to execute future commands. Actual entry repeats the checks and requires a foreground controlling host terminal. The shell gets its own terminal even if the container's main process has no allocated terminal. Unlike attach, it does not share the harness's terminal input or resizing. The controller does not record shell output or send automatic commands; your terminal scrollback still applies.

## Direct attachment command

You may attach to a unique instance UUID or prefix of at least eight hexadecimal UUID characters:

```bash
omarchy agent attach 11111111 --check
omarchy agent attach 11111111
```

Replace the example prefix with an instance from your list. `--check` validates current identity and interactive capabilities without opening the terminal stream. The interactive command requires a foreground controlling host terminal so detach keys can work. A background job or synthetic terminal without a controlling terminal is rejected. It verifies the full immutable container ID, current-user process identity and namespaces, running state, allocated terminal, and open standard input before attachment.

Stopped, missing, changed, ambiguous, and unsupported targets are rejected. Nothing is restarted. Harnesses launched with automatic removal normally disappear after their main process exits. Editor workspace containers are not targets of this menu.

**Closing can discard work or interrupt file writes.** Both menu close actions default to No and revalidate the exact original instance after confirmation. Shared homes and project volumes are not deleted. Use [agent diagnostics](59-agent-session-diagnostics.md) when you need read-only evidence rather than interactive access.
