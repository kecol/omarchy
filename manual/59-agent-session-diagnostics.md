# Diagnose and close agent harness instances

List local Omarchy harness instances and limited diagnostic evidence:

```bash
omarchy agent diagnose
omarchy agent diagnose --json
```

The report shows each unique instance ID, container, host-visible PID, start time, selected project directory, internal path, and project key. It highlights multiple launches of the same agent sharing an observed host project bind. These are separate instances, not independent copies of the project.

## Interpret login evidence

For native Codex processes, the command can recognize a small set of command/subcommand tokens and check whether that exact process owns a TCP listener on the conventional callback port 1455. It does not connect to that listener or inspect remote connections.

- **Explicit login command** means the process was invoked with the `login` subcommand. It does not prove that login is stuck or abandoned.
- **Possible callback listener** can indicate browser sign-in. It does not establish authentication state or prove that closing is appropriate.
- **Interactive launch option** does not reveal whether the terminal currently shows a conversation, onboarding, a login screen, or an idle prompt.
- **Absent listener** does not prove successful authentication. Child-owned listeners, other ports, and unsupported flows can be missed.
- **Partial/unavailable** means evidence could not be checked completely, not that no listener exists.

Age and shared-directory launches do not establish abandoned work. The command does not inspect terminal buffers, prompts, later command arguments, process environments, credentials, provider accounts, or agent histories. Unknown command tokens are not consumed or printed in full. No automatic cleanup follows any finding.

## Select one instance

Use the full instance UUID from diagnosis, or a unique hexadecimal UUID prefix of at least eight characters. An agent name such as `codex`, a PID, or an ambiguous prefix is rejected.

Validate the selection without sending a signal:

```bash
omarchy agent close 568a857f --check
```

**Closing can discard work or interrupt file writes. Identify the unwanted terminal/session first.** Shared project files and the agent home are not deleted or rolled back by this command.

Stop one instance with a ten-second grace period, followed by forced termination if it does not exit:

```bash
omarchy agent close 568a857f
```

Immediately force-kill that exact instance:

```bash
omarchy agent close 568a857f --force
```

Both actions require terminal confirmation, defaulting to Cancel. Explicit unattended closure requires `--yes`; combining it with `--force` authorizes immediate termination. `--check` always remains read-only.

The command rechecks the instance UUID, full container ID, name, user-owned init process identity, and namespaces after confirmation and immediately before signalling. A changed, missing, ambiguous, or unsupported identity stops the operation. It uses the local rootless engine and signals only the resolved immutable container ID. It does not signal a host PID, close editor workspace containers, remove volumes/images/workspaces, switch execution mode, or retry with broader targets.

Closing a harness can remove its disposable container through the launcher's existing automatic-removal behavior. The shared persistent home remains, including an existing device-login result. Other instances using that home or project are not selected for closure.

These commands are not a security boundary against a compromised host or engine configuration. Missing/unavailable engine data is an error, not a complete zero-instance inventory. Run them on the host as your normal desktop user, not with sudo.
