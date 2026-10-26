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

## Local Herdr sessions

A grouped section lists each local session returned by Herdr and its reported agent panes:

```text
Local Herdr sessions (pane references, not additional agents)
  default [ok; reported entries: 1; labels: ok]
    PANE         AGENT          REPORTED ACTIVITY      PROCESS MATCH
    w7:p1        pi             working                host PID 1234
```

A matched pane references a process already listed above. It is not a second agent count. A reported pane without a matching live process says **unverified**. Cached remote observations say **remote-unverified** and never match local PIDs. Agent processes outside Herdr remain in the main process table without a pane reference.

Session coverage is explicit: **ok** means its agent listing was checked; **partial** means some metadata or PID checks failed; **unavailable** means its socket or agent listing could not be checked; **not-running** means it was listed as stopped and was not queried. A checked session with zero entries says **No agents reported**, not that no agents exist. An unavailable listing has an unknown count, never zero. Only reported agent panes are shown; ordinary terminal panes and terminal contents are not queried for this section.

When label metadata is available, both the process evidence and grouped pane show the readable Herdr path, for example `Local / host - Work / pi host / w7:p1`. This means local machine scope, Herdr workspace label, tab label, and pane ID. The session, workspace ID, and tab ID remain visible, and JSON retains them separately as `workspace_id`, `workspace_label`, `tab_id`, and `tab_label`. Names are display labels, not identifiers used for process matching or command arguments. They are distinct from desktop workspace numbers and container workspace names.

Labels come from one bounded local session metadata snapshot after the existing agent/PID queries. Pane, agent kind, workspace ID, tab ID, and tab parent must agree across the observations before labels are accepted. A moved pane, duplicate metadata identifier, missing label, or unsupported response falls back to IDs rather than borrowing another tab's name. `labels_state` reports label availability per session. A label-query failure does not remove an agent or invalidate its existing PID match. Labels are length-limited and console control characters are escaped. No window or terminal title is used as a fallback, and local names are not applied to remote observations.

Duplicate reports for the same agent pane produce one grouped row. Different reported activity values show **conflicting-reports**. Session names remain case-sensitive. The JSON `herdr_sessions` collection contains session coverage and pane references to the existing process identities; this is an additive field in schema version 1. Grouping reuses collected observations; display-label enrichment adds at most one local metadata snapshot per applicable session. No persistent state is created.

**Container does not mean safe.** A container can have writable host mounts. This report identifies execution boundaries; it does not audit filesystem permissions, credential exposure, or network isolation. Use `omarchy agent inspect`, `omarchy agent audit` without `--fix`, or `omarchy workspace doctor <name>` for their respective runtime details and checks.

## Automatic desktop location

When a local window association can be established, the report shows its monitor and Omarchy desktop workspace automatically. No manual mappings are required:

```text
Desktop: HDMI-A-1 / desktop 1 (Hyprland 11) [attached Herdr terminal; pane visibility unknown]
```

**Desktop workspace** is different from a Herdr workspace or container workspace. Omarchy numbers workspaces per monitor in blocks of ten. The report follows the bar's label, retains the global Hyprland ID, and preserves named or special workspace names in JSON. The tenth slot uses the bar's `0` label. Monitor IDs are not used to guess workspace numbering.

Ordinary host agents can be associated through their live process ancestry and compositor window ownership. Herdr's server is detached from its terminal, so the report also correlates its local API listener, reciprocal frontend socket connections, kernel socket-descriptor ownership, and client ancestry. It then reports the attached Herdr terminal's location. This does not prove that the agent's pane or tab is currently displayed; navigating within Herdr may still be necessary.

If a terminal server or application owns several windows, all matching locations remain **multiple candidates**. The report does not select a window based on focus or title. A background/container process without a verified GUI association stays **unknown**. An unavailable compositor or unreadable peer metadata is not treated as proof that an agent has no window. Window/workspace locations are snapshots and can change after the command runs.

Desktop fields are additive to JSON schema version 1 under process/candidate records and local Herdr sessions. They include window address/PID/class, monitor, raw workspace ID/name, bar slot/label, association source, hidden-window metadata, and whether that workspace was active. An active workspace does not prove that its window or Herdr pane was visible. Local Herdr client-socket conventions can vary with version; unsupported mappings remain unknown rather than being inferred from titles.

The command does not focus windows, switch workspaces, or create manual rules. It does not inspect window titles, screenshots, or pane contents. Compositor responses may contain titles; those fields are discarded and are not used or emitted. Socket descriptor links are read as metadata only, not opened for their contents. No remote desktop query is made.

## Structured output and optional sources

```bash
omarchy agent status --json
omarchy agent status --no-herdr
omarchy agent status --no-podman
omarchy agent status --no-desktop
```

`--json` returns a versioned object with separate process, candidate, unverified-observation, runtime, and coverage collections. Runtime entries are container observations, not extra agent counts. The other options skip the named adapter; `--no-desktop` skips compositor and Unix-peer queries. The command still reports host processes when an optional dependency is missing.

## Scope and privacy

The report covers the current user and processes visible through local procfs. It queries only running local Herdr sessions and forces Podman to use its local rootless engine. It does not connect to remote machines, use SSH-agent authentication, or inspect other users. Remote Herdr records, if present in local metadata, remain unverified and are not matched against local PIDs.

The process scanner reads names, executable paths, process identities, namespace links, and selected directories. For known interpreters, it reads only the executable token and first option/script token, never later prompt arguments. It does not read process environments, terminal contents, provider credentials, or agent histories. Herdr responses may include additional metadata; command lines, arguments, titles, and agent-session paths are discarded and never printed or used for identification. Errors do not echo adapter stderr. Console control characters are escaped.

External metadata queries share an eight-second budget, with a per-query timeout and response-size limit. The process scan also has time and count limits. The command produces no persistent cache. Visibility is not complete: hidden processes, other users, unsupported wrappers, remote hosts, and inaccessible namespace metadata can remain unknown. An empty identified-process list is not proof that no agents run on the system.
