# Managed coding agents

Omarchy managed task assignments run through independent Git clones and a container runtime. The design goal is to keep assignment writes away from the source checkout until a human explicitly reviews and applies them. This is a workflow boundary, not host-wide confinement: ordinary ad-hoc Container launches bind their selected current directory read-write, and Host execution remains supported.

The [source boundary inventory](agent-safety-boundaries.md) records implemented checks, command/menu/widget contracts and known limits. The [first extraction design](../plans/agent-safety-first-extraction.md) now has an implemented source reader and scoped fixture results in the [implementation outcome](../openspec/changes/extract-agent-catalog-reader/outcome.md); it is not deployed or qualified as a new isolation boundary. The [Agent Control Plane](../plans/agent-control-plane.md) remains a stronger draft, not a description of current guarantees.

## Local status and managed inventory

`omarchy agent status` reports recognized current-user processes, including direct host agents and extension-associated processes in local rootless containers. It correlates local Herdr reports without counting the same process twice. It is distinct from `agent list` (configured definitions), `agent ps` (active managed harnesses), and `workspace list` (editor containers). Its structured output and coverage limitations are described in [`manual/56-agent-status.md`](../manual/56-agent-status.md). For matched agent harnesses, additive `container.project` metadata separates `host_path`, `container_path`, `project_id`, `access`, and mapping `state`. The existing bounded Podman inspect projects only the declared `/workspace` project bind, never arbitrary mount sources or environments. The observer checks mount/PID namespaces and revalidates the container init identity before attaching a mapping. Missing, stale, malformed, or ambiguous data does not become an inferred host path. The overview retains internal keys and shows observed project mount access; it does not claim safe isolation. Editor containers add `container.workspace_files` with observed bind fields and separate `registry_state`, `mode`, and `source_directory`. Only an exact canonical registry-directory/bind-source match attaches clone/live semantics and the registered source. A mismatch keeps the observed bind but suppresses source/mode. Registry enrichment reuses the existing read-only snapshot and does not query a remote engine or workspace credential stores. It is an observation tool, not an isolation audit or agent controller. Remote hosts are not queried.

## Existing harness terminal access

`omarchy agent sessions` provides an on-demand terminal picker for managed running harnesses. `omarchy agent attach <instance> [--check]` resolves a unique UUID/prefix, revalidates the selected process/container identity and interactive capabilities, and passes the user's terminal directly to local Podman attach with signal proxying disabled and explicit detach keys. `default/agents/session-menu.py` never captures harness output, sends automatic input, executes a shell/second agent, restarts stopped targets, or replays logs. Menu close actions use the existing `sessions.close_instance()` identity boundary after a default-No confirmation. Metadata menu labels are captured separately from the uncaptured harness stream. The overview's explicit Inspect sessions action opens this picker through the fixed host terminal launcher, without passing an instance or automatically attaching/closing anything. Text status/diagnosis reports hint at the picker only when managed harnesses were observed, reusing collected metadata; JSON output and collectors remain unchanged. Launch defaults are not changed. See [`manual/60-agent-session-menu.md`](../manual/60-agent-session-menu.md).

## Instance diagnostics and explicit closure

`omarchy agent diagnose` uses bounded local rootless engine metadata, user-owned process identities, a prefix-limited Codex subcommand recognizer, and PID-owned callback-listener metadata. It reports shared-project launches and possible login evidence without inferring abandonment or authentication state. `omarchy agent close <instance>` selects one unique UUID/prefix, confirms by default, revalidates after confirmation, and targets only the full immutable container ID. Normal close uses `stop --time=10`, which can escalate to KILL after ten seconds; `--force` requests KILL explicitly. The overview uses a different TERM-only controller with `--time=-1`; legacy task/workspace/audit stops have narrower identity checks. It never deletes shared homes or uses findings as an automatic close policy. `default/agents/sessions.py` owns this separate controller boundary; the status/widget observation code does not gain close actions. See [`manual/59-agent-session-diagnostics.md`](../manual/59-agent-session-diagnostics.md).

## Optional direct-command guards

`omarchy agent guards` manages opt-in PATH-based launch friction, not containment. Separate user-owned scripts block direct host agent invocations when the saved launch mode is Container, without replacing installed tools or changing running agents. The generator reuses the default-agent menu catalog and container definitions; optional definition `guardCommands` and manual registrations support additional names. Explicit sync discovers newly installed commands and future catalog/definition additions without a product allowlist. Known infrastructure/runner commands cannot be registered. See [`manual/57-agent-command-guards.md`](../manual/57-agent-command-guards.md).

`default/agents/command-guards.py` owns private metadata and unchanged managed scripts. Generation preflights conflicts; foreign or modified files are not overwritten. Runtime mode errors block rather than assume Host. Bash environment setup prefixes the opt-in directory, and a process-free Bash prompt hook restores it after mise. Status reports actual PATH precedence, not aliases/functions or universal coverage. Deliberate Host launches remove guard PATH entries in their child, including after a terminal service reconstructs PATH. Installed-only resolution looks past guards; explicit account sign-in retains its existing host flow. Absolute paths, IDE processes, other shells, and intentionally changed PATH remain bypasses. Enabling guards never means that every process is containerized.

### Bundled catalog reader

[`default/agents/catalog.js`](../default/agents/catalog.js) exports the pure CommonJS function `agentCatalog(raw)`. Guard discovery and the launch picker read the same bundled menu data through this agent-owned projection, not through the desktop menu model. The function preserves the limited comment/trailing-comma syntax, flat/wrapped rows, matching ID order and label fallback; it performs no I/O or execution. It does not read user overlays or maintain another product list.

The callers retain distinct validation, environments and limits. Malformed menu text still produces an empty catalog: guards can continue through definitions/registrations, while the picker refuses it. Missing files/module and Node errors/timeouts propagate; there is no fallback to the UI model or Host execution. Source extraction changes no mode/default, menu/widget action, workspace sharing, guard registration or runtime policy. The two focused fixture suites passed; authentication, actual container/GUI behavior and activation were not tested or performed.

## Reviewed first-run container preparation

`omarchy agent prepare --agent NAME` and the interactive image selector share `omarchy-harness-ensure`. Missing images require confirmation (or explicit `--yes`); existing images are reused without public release lookup. `omarchy-harness-build` consumes reviewed bundled `harness.json` metadata, builds a private candidate, and promotes only after network-free disposable version/filesystem checks. Pi, Codex, Claude Code (`claude`), and OpenCode (`opencode`) have bundled recipes. Preparation does not install host agents, import account homes, authenticate providers, or start an agent; an interactive **Prepare and run** explicitly continues to launch after preparation succeeds.

`default/agents/harness.py` validates bounded, regular bundled metadata in `containers/harnesses/<harness>/harness.json`. Its fields name the public mise tool, executable, version build argument, and exact version output template. The Containerfile and context allowlist must exist without leaf symlinks. Metadata drives builds and validation without an agent-product switch. Anonymous registry credentials, isolated public release lookup, private candidate tags, and disposable network-free runtime fixtures keep preparation separate from authentication. `--candidate-only` supports qualification without promoting production tags.

Claude Code uses the native executable selected by mise's `claude` registry entry. OpenCode uses the `opencode` registry entry; its npm backend needs Node/npm in the installer stage. The runtime image preserves the complete installed tool prefix because mise's launcher resolves the native executable through sibling package files. Node/npm is not separately installed in the runtime stage. Each recipe has a Containerfile-only context allowlist. Neither recipe copies a host installation, configuration, account store, or conversation history. They use the existing persistent container-home volumes, rootless launch policy, image selector, and independent execution/status path. Adding a recipe does not change the user's default or saved execution mode, enable usage collection, prepare an image, or authenticate a provider. Native image and interactive-login qualification are separate from metadata checks.

Automatic public release lookup requires Bubblewrap (`bubblewrap`) and mise. `harness.py` runs the selected mise executable in a filesystem namespace with read-only system executables, the resolved public CA bundle, DNS settings and synthetic account/configuration files. Only the new temporary work directory is host-backed and writable; `/tmp` and `/run` use private tmpfs mounts. The host home, project tree, `/etc/mise`, agent/engine sockets and credential environment are not exposed. The account-database HOME points into the temporary directory, not just the HOME environment variable. Network access remains available for anonymous public metadata; this is not a network allowlist or a compromised-host isolation claim. Missing Bubblewrap or a sandbox failure stops lookup without an unconfined fallback. An explicit version skips lookup, not build/runtime validation or first-run consent.

`omarchy-agent-prepare --check` is only a recipe/definition check, suitable for rejecting unsupported Container defaults before saving or invoking the old Host installer. It is not an engine/image/authentication readiness claim. Dependency installation and authenticated testing remain separate explicit actions. See [`manual/58-agent-container-preparation.md`](../manual/58-agent-container-preparation.md) for the interface, bounds, and limitations.

## Host filesystem journal preflight

`omarchy agent container doctor --quick` checks writable host directories, local rootless Podman and the current boot's last 15 minutes of system journal messages. Quick mode still creates temporary write probes and a disposable engine volume. It is not a read-only diagnostic command.

`default/agents/journal-filesystem-check.py` reads structured journal entries and retains the existing filesystem-warning patterns. Only informational Podman container events with matching structured labels can exempt the exact rendered `org.omarchy.filesystem.root=read-only` and `org.omarchy.harness.model-recovery=read-only` tokens. Those labels describe intentional container hardening. The check scans the rest of the message and all other entries, including real Podman storage errors. It does not exclude Podman, system messages or whole events.

The helper consumes the complete journal stream before returning: 0 means no matching warning, 1 means a matching warning, and 2 means the journal check is unverified. The checker supports the documented `journalctl(1)` JSON encodings: text, unsigned byte arrays and repeated field values. It scans every decoded MESSAGE value, including arbitrary non-UTF-8 bytes, rather than excluding those records. `--all` prevents the default null elision of fields larger than 4096 bytes; output projection excludes unrelated journal fields. Each JSON record is limited to 8 MiB. Oversized records are drained without unbounded allocation and make the check unverified. Journal command failures, malformed records and invalid field encodings block startup rather than pass as clean. The result describes only the accessible journal window, not disk health or recovery. Partial journal visibility and warnings outside the existing pattern/window are not a complete filesystem audit. No repair or guard bypass follows from this check.

## Launch, menu and widget contracts

`omarchy agent mode` reads the future launch default. An absent setting means Host; an invalid setting refuses rather than becoming Host. `omarchy agent mode host|container` saves directly and requests a best-effort label refresh. It does not migrate running agents, stop workspaces or enable PATH guards. The Default Execution menu adds a default-No terminal confirmation through `omarchy-menu-agent-mode`; the direct setter does not ask for that confirmation.

The standalone Agent execution default widget shares one event-driven mode reader across monitors. Left-clicking either its icon or label opens Default Execution; right-clicking either opens/toggles the local on-demand overview. Its initial mode read does not scan agents or contact providers. The separate usage widget has different actions: left-click opens its account/usage panel, right-click starts the terminal agent picker, and middle-click refreshes usage. Its optional execution label opens Default Execution on left-click but has no overview right-click action. These widgets are not interchangeable even when both show the same saved mode.

The terminal launch picker and Agents > Start Agent menu select an agent for one launch without saving defaults. Checks, managed/one-shot/session-recovery launches and explicit agent selections do not acquire the automatic terminal picker. Availability checks inspect installed Host commands or Container definitions, not login/image/model readiness. Cancellation never chooses an implicit fallback.

Agents > Start Agent selects a project, agent, execution target and file access, then shows a default-No terminal review before creating a clone or launching. Host means desktop-user permissions, not a project sandbox. Container can use a new committed-HEAD clone or an explicit live host directory. Workspace Files reuses the existing workspace's exact project files in either mode: it does not create a second copy, attach to its editor container or share its home volume. A new approved clone remains available if image selection or launch later fails. Recent-project storage is private/bounded; a failure to remember a project warns without undoing the launch. The final launcher uses an explicit mode/agent/directory and installed-only Host resolution.

Agents > Workspaces is the separate VS Code workflow. It requires an installed editor, supports create/reopen with clone/live warnings and default-No terminal review, and delegates to the workspace backend. Creation alone builds no image and starts no container. `workspace code` can start the container, install the local Remote SSH extension and download remote server/extensions; no workspace image is built/pulled automatically. Failed editor opening retains the newly created workspace. `workspace list --json` reads metadata and a bounded engine snapshot, reporting unknown runtime state on query failure. These are container project workspaces, not Hyprland display workspaces or managed task assignments. See [workspace internals](workspaces.md) and the [command/menu supplement](agent-safety-boundaries.md#implemented-entrypoint-contracts).

`omarchy default agent NAME` is not a per-launch chooser: it saves a supported default and launches it. In Container mode it checks the recipe before saving and does not invoke the Host installer; later preparation/launch can still fail after the save. Host selection can install a CLI. Prompt/resume/continue reuse the launcher; resume/continue currently support Pi only. Explicit local-model overlays require Host and do not silently broaden Container mounts or change the saved mode. Crash diagnosis intentionally calls the launcher with a Host override. These maintenance/explicit-Host paths must not be removed on the assumption that the saved Container preference is mandatory containment.

`omarchy agent container` is a routing prefix for `check`, `doctor` and the hidden overview `stop`, not another mode setter. `container check` can pull an image and runs an offline disposable probe with the current directory writable; it is not a read-only diagnostic or the ordinary harness policy. Doctor performs host write probes and engine operations even in quick mode. Audit observes selected active harnesses; `--fix` actively stops detected drift. None is permission to run the others automatically.

## Safety model

A managed task has three important locations:

- **Source checkout**: the Git repository where the task was created.
- **Task base commit**: the source commit recorded by `omarchy task create`.
- **Assignment workspace**: a private clone under
  `$XDG_DATA_HOME/omarchy/agent-workspaces/<project>/<task>/<assignment>/repo`.

The managed task start path selects the assignment workspace and verifies that it is inside Omarchy's managed assignment directory. Assignment creation removes its origin remote. This does not prevent other processes with the desktop user's authority from accessing canonical source. Ad-hoc Container launches and explicit live editor workspaces have different bind rules.

Moving changes back to the source checkout is explicit:

```bash
omarchy task diff <assignment>
omarchy task patch <assignment>
omarchy task apply <assignment>
```

If the source checkout moved after the task was created, use:

```bash
omarchy task apply <assignment> --3way
```

## Typical workflow

Create a task from a clean Git checkout:

```bash
omarchy task create "Implement the requested change"
```

Assign an agent:

```bash
omarchy task assign <task> pi coder
```

Start the assignment:

```bash
omarchy task start <assignment>
```

Review the result:

```bash
omarchy task status <assignment>
omarchy task diff <assignment>
omarchy task patch <assignment> review.patch
```

Patch export compares working state with the assignment workspace's current HEAD, not the recorded task base; already committed assignment changes are not necessarily included. Apply regenerates the patch. It checks source location, cleanliness and base compatibility, but does not verify a reviewer identity or approval tied to an immutable candidate digest.

Apply after review:

```bash
omarchy task apply <assignment>
```

Reconcile state if the source was updated manually or by a 3-way apply:

```bash
omarchy task reconcile <assignment>
```

Clean up completed workspace state:

```bash
omarchy task cleanup <assignment>
omarchy task archive <task>
```

## Start-time checks

`omarchy task start` fails closed when its safety checks fail. It runs:

1. `omarchy task preflight <assignment>`
2. `omarchy agent audit`
3. the configured agent launch

Preflight checks the assignment, workspace, source checkout, saved runtime mode, harness image, base ancestry, workspace remote state and observed active-instance state. Runtime audit rejects detected drift in its selected active harness snapshot. Preflight, audit and launch are separate operations: no atomic admission lease prevents concurrent starts or a later mode change. Audit visibility and label comparisons have the limitations below.

## Runtime policy

Show the effective policy with:

```bash
omarchy agent policy
omarchy agent policy --json
```

The default policy is:

```text
Filesystem:  workspace=read-write, source=unmounted, home=isolated persistent agent volume
Network:     delegated-to-openshell
Credentials: delegated-to-openshell
OpenShell:   optional (available or not-installed)
Resources:   memory=4g, pids=1024
```

Podman flags request resource constraints; labels describe policy for comparison and are not enforcement. The displayed network/credential delegation does not activate OpenShell or prove its availability. The `source=unmounted` declaration is not proof of canonical-source absence in an ad-hoc bind. Configure resource values in:

```text
~/.config/omarchy/agents/policy.json
```

Example:

```json
{
  "resources": {
    "memory": "6g",
    "pids": 512,
    "cpus": 2
  }
}
```

Environment variables override the config file:

```bash
OMARCHY_AGENT_MEMORY_LIMIT=8g
OMARCHY_AGENT_PIDS_LIMIT=2048
OMARCHY_AGENT_CPUS_LIMIT=2
```

## Runtime audit

Audit active managed agent containers:

```bash
omarchy agent audit
omarchy agent audit --json
```

The audit compares selected managed-label containers against expected policy labels and selected mount/security fields. It checks the source-unmounted/workspace declarations, host-root and `/home/agent` bind exclusions, a nonempty capability-drop list, `no-new-privileges` and resource labels. It does not measure all effective resource flags or require the exact all-capabilities drop set. The legacy runtime snapshot can return an empty successful result when Podman is unavailable; that is not independent evidence that no agent is active. The legacy snapshot, audit-fix and task-stop requests explicitly select the local engine, ignoring ambient remote-engine defaults without changing the user's configuration. Their output, target and failure policies remain distinct from newer controllers; local routing is not complete engine-access denial. Editor workspace operations, including bounded listing, also select the local engine; their loopback Remote SSH connection remains intentional. This is an intentional compatibility change for implicit remote defaults, not a change to direct user Podman commands. See [the local-engine change](../openspec/changes/pin-managed-workflows-local-engine/proposal.md). See O2/E1 in the [inventory](agent-safety-boundaries.md).

If audit detects drift, stop unsafe containers without deleting workspaces or
volumes:

```bash
omarchy agent audit --fix
```

This marks affected registry instances and managed assignments as failed when
labels are available.

## Inspecting and recovering tasks

Useful commands:

```bash
omarchy task inspect <task>
omarchy task list
omarchy task log <assignment>
omarchy task stop <assignment>
omarchy task reconcile <assignment>
```

`task status` separates assignment workspace cleanliness from source
reconciliation state. A dirty assignment workspace can still be safe if the
source state is `applied`.

`task cleanup` removes only Omarchy's managed assignment directory and refuses
unsafe states unless `--force` is used. `task archive` closes a task after its
assignments are applied, empty, or cleaned.

## OpenShell boundary

See [Agent OpenShell Architecture](agent-openshell-architecture.md) for the planned runtime, credential, workspace, and audit model.

Ordinary managed-task/Podman dispatch does not route through the OpenShell prototypes. Omarchy declares delegated network and credential policy but does not enforce those controls directly. OpenShell brokering, secret prompts and tool mediation are intended integration goals, not current guarantees. Explicit provider import and sandbox commands are separate credential-bearing operations. The Pi path imports an unexpired access-token/account snapshot without its rotating refresh token; the Codex import has a separate gateway refresh path. Best-effort Landlock/workdir/network behavior remains unqualified here.

Check OpenShell readiness with:

```bash
omarchy agent openshell doctor
omarchy agent openshell doctor --quick
omarchy agent openshell doctor --json
```

When the CLI is missing, the interactive doctor offers to install OpenShell for
the current user. To install explicitly, run:

```bash
omarchy agent openshell install
omarchy agent openshell doctor --install
```

Import a supported host account into OpenShell provider storage and run a
minimal provider-backed sandbox smoke test with:

```bash
omarchy agent openshell provider import codex
omarchy agent openshell prompt --provider codex "hello from OpenShell"
```

The smoke test verifies that OpenShell injects the expected credential
environment variables without printing their values. It is not yet a full agent
runtime.

On Omarchy, the installer uses a user-local layout instead of system deb/rpm
packages: binaries go in `~/.local/bin`, gateway TLS and state go under
`~/.local/state/openshell`, CLI mTLS credentials go under
`~/.config/openshell/gateways/openshell/mtls`, and the gateway runs as the
`openshell-gateway.service` systemd user service.

The quick check reports whether the `openshell` CLI is installed, Landlock is
enabled, a container engine is present, and a selected gateway is reachable. The
full check also runs a disposable `openshell sandbox create --no-keep` command.
`omarchy agent audit` includes the quick OpenShell status as advisory
information without failing the Podman runtime audit when OpenShell is not yet
installed.
