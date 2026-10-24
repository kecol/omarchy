# Local agent status

Run this command on the host as your desktop user, not with sudo, for a one-shot report of identified agent processes:

```bash
omarchy agent status
```

Host processes appear first, followed by processes with unknown execution boundaries and identified container processes. The command does not launch, stop, restart, or change an agent, container, workspace, or setting. It does not start a watcher or usage collector.

## Read the report

- **Boundary** describes the observed process location. Host means the command's own PID and mount namespaces. A recognized local rootless container is named when its namespaces match. Unknown means the boundary could not be established. If the command detects that it is itself inside a container, same-namespace processes are labeled Observer rather than Host.
- **Agent** identifies a known executable or supported interpreter entry point. A process-name-only match without Herdr corroboration appears under possible candidates, not identified processes. Identification does not attest that an executable is trusted.
- **Activity** distinguishes process presence from Herdr's reported state. `working [Herdr]` is Herdr's observation, not an independent activity check. `process-observed` does not mean the agent is executing a task.
- **PID** identifies a process in the command's visible process namespace. Process start time and boot identity are also included in JSON. A Herdr pane attached to that process adds evidence; it is not counted as a second agent process.
- **Location / evidence** shows the process directory, workspace/container name, and matching local Herdr session/pane. A Codex executable installed by the VS Code extension is labeled as an extension-associated process; its work state remains unverified.
- **Launch default** applies to future launches only. A Container default does not imply that no host agent is running.
- **Coverage** reports successful, partial, unavailable, disabled, and unqueried sources. Missing access or a failed adapter never means that no agents exist.

Unverified Herdr observations appear separately. An idle shell, SSH launcher, stale agent hint, or remote record is not promoted into a confirmed host process. A running editor workspace alone is not counted as an agent.

**Container does not mean safe.** A container can have writable host mounts. This report identifies execution boundaries; it does not audit filesystem permissions, credential exposure, or network isolation. Use `omarchy agent inspect`, `omarchy agent audit` without `--fix`, or `omarchy workspace doctor <name>` for their respective runtime details and checks.

## Structured output and optional sources

```bash
omarchy agent status --json
omarchy agent status --no-herdr
omarchy agent status --no-podman
```

`--json` returns a versioned object with separate process, candidate, unverified-observation, runtime, and coverage collections. Runtime entries are container observations, not extra agent counts. The other options skip the named adapter. The command still reports host processes when an optional dependency is missing.

## Scope and privacy

The report covers the current user and processes visible through local procfs. It queries only running local Herdr sessions and forces Podman to use its local rootless engine. It does not connect to remote machines, use SSH-agent authentication, or inspect other users. Remote Herdr records, if present in local metadata, remain unverified and are not matched against local PIDs.

The process scanner reads names, executable paths, process identities, namespace links, and selected directories. For known interpreters, it reads only the executable token and first option/script token, never later prompt arguments. It does not read process environments, terminal contents, provider credentials, or agent histories. Herdr responses may include additional metadata; command lines, arguments, titles, and agent-session paths are discarded and never printed or used for identification. Errors do not echo adapter stderr. Console control characters are escaped.

External metadata queries share an eight-second budget, with a per-query timeout and response-size limit. The process scan also has time and count limits. The command produces no persistent cache. Visibility is not complete: hidden processes, other users, unsupported wrappers, remote hosts, and inaccessible namespace metadata can remain unknown. An empty identified-process list is not proof that no agents run on the system.
