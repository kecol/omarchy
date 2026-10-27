# Managed coding agents

Omarchy managed agents run coding tasks through isolated Git workspaces and a
container runtime. The design goal is to keep agent writes away from the source
checkout until a human explicitly reviews and applies them.

## Local status and managed inventory

`omarchy agent status` reports recognized current-user processes, including direct host agents and extension-associated processes in local rootless containers. It correlates local Herdr reports without counting the same process twice. It is distinct from `agent list` (configured definitions), `agent ps` (active managed harnesses), and `workspace list` (editor containers). Its structured output and coverage limitations are described in [`manual/56-agent-status.md`](../manual/56-agent-status.md). For matched agent harnesses, additive `container.project` metadata separates `host_path`, `container_path`, `project_id`, `access`, and mapping `state`. The existing bounded Podman inspect projects only the declared `/workspace` project bind, never arbitrary mount sources or environments. The observer checks mount/PID namespaces and revalidates the container init identity before attaching a mapping. Missing, stale, malformed, or ambiguous data does not become an inferred host path. The overview retains internal keys and shows observed project mount access; it does not claim safe isolation. Editor containers add `container.workspace_files` with observed bind fields and separate `registry_state`, `mode`, and `source_directory`. Only an exact canonical registry-directory/bind-source match attaches clone/live semantics and the registered source. A mismatch keeps the observed bind but suppresses source/mode. Registry enrichment reuses the existing read-only snapshot and does not query a remote engine or workspace credential stores. It is an observation tool, not an isolation audit or agent controller. Remote hosts are not queried.

## Existing harness terminal access

`omarchy agent sessions` provides an on-demand terminal picker for managed running harnesses. `omarchy agent attach <instance> [--check]` resolves a unique UUID/prefix, revalidates the selected process/container identity and interactive capabilities, and passes the user's terminal directly to local Podman attach with signal proxying disabled and explicit detach keys. `default/agents/session-menu.py` never captures harness output, sends automatic input, executes a shell/second agent, restarts stopped targets, or replays logs. Menu close actions use the existing `sessions.close_instance()` identity boundary after a default-No confirmation. Metadata menu labels are captured separately from the uncaptured harness stream. This feature does not add widget actions or change launch defaults. See [`manual/60-agent-session-menu.md`](../manual/60-agent-session-menu.md).

## Instance diagnostics and explicit closure

`omarchy agent diagnose` uses bounded local rootless engine metadata, user-owned process identities, a prefix-limited Codex subcommand recognizer, and PID-owned callback-listener metadata. It reports shared-project launches and possible login evidence without inferring abandonment or authentication state. `omarchy agent close <instance>` selects one unique UUID/prefix, confirms by default, revalidates after confirmation, and sends graceful stop or explicit `--force` SIGKILL only to the full immutable container ID. It never deletes shared homes or uses findings as an automatic close policy. `default/agents/sessions.py` owns this separate controller boundary; the status/widget observation code does not gain close actions. See [`manual/59-agent-session-diagnostics.md`](../manual/59-agent-session-diagnostics.md).

## Optional direct-command guards

`omarchy agent guards` manages opt-in PATH-based launch friction, not containment. Separate user-owned scripts block direct host agent invocations when the saved launch mode is Container, without replacing installed tools or changing running agents. The generator reuses the default-agent menu catalog and container definitions; optional definition `guardCommands` and manual registrations support additional names. Explicit sync discovers newly installed commands and future catalog/definition additions without a product allowlist. Known infrastructure/runner commands cannot be registered. See [`manual/57-agent-command-guards.md`](../manual/57-agent-command-guards.md).

`default/agents/command-guards.py` owns private metadata and unchanged managed scripts. Generation preflights conflicts; foreign or modified files are not overwritten. Runtime mode errors block rather than assume Host. Bash environment setup prefixes the opt-in directory, and a process-free Bash prompt hook restores it after mise. Status reports actual PATH precedence, not aliases/functions or universal coverage. Deliberate Host launches remove guard PATH entries in their child, including after a terminal service reconstructs PATH. Installed-only resolution looks past guards; explicit account sign-in retains its existing host flow. Absolute paths, IDE processes, other shells, and intentionally changed PATH remain bypasses. Enabling guards never means that every process is containerized.

## Reviewed first-run container preparation

`omarchy agent prepare --agent NAME` and the interactive image selector share `omarchy-harness-ensure`. Missing images require confirmation (or explicit `--yes`); existing images are reused without public release lookup. `omarchy-harness-build` consumes reviewed bundled `harness.json` metadata, builds a private candidate, and promotes only after network-free disposable version/filesystem checks. Pi and Codex have bundled recipes. Preparation does not install host agents, import account homes, authenticate providers, or start an agent; an interactive **Prepare and run** explicitly continues to launch after preparation succeeds.

`default/agents/harness.py` validates bounded, regular bundled metadata in `containers/harnesses/<harness>/harness.json`. Its fields name the public mise tool, executable, version build argument, and exact version output template. The Containerfile and context allowlist must exist without leaf symlinks. Metadata drives builds and validation without an agent-product switch. Anonymous registry credentials, isolated public release lookup, private candidate tags, and disposable network-free runtime fixtures keep preparation separate from authentication. `--candidate-only` supports qualification without promoting production tags.

`omarchy-agent-prepare --check` is only a recipe/definition check, suitable for rejecting unsupported Container defaults before saving or invoking the old Host installer. It is not an engine/image/authentication readiness claim. Dependency installation and authenticated testing remain separate explicit actions. See [`manual/58-agent-container-preparation.md`](../manual/58-agent-container-preparation.md) for the interface, bounds, and limitations.

## Safety model

A managed task has three important locations:

- **Source checkout**: the Git repository where the task was created.
- **Task base commit**: the source commit recorded by `omarchy task create`.
- **Assignment workspace**: a private clone under
  `$XDG_DATA_HOME/omarchy/agent-workspaces/<project>/<task>/<assignment>/repo`.

Managed agents work in the assignment workspace only. They do not receive a Git
remote for the canonical source repository, and task start verifies that the
workspace is inside Omarchy's managed assignment directory.

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

Preflight verifies the assignment, workspace, source checkout, runtime mode,
harness image, base ancestry, workspace remote state, and active-instance
state. Runtime audit verifies already-running managed agent containers before a
new task agent starts.

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

Resource limits are enforced through Podman flags and labels. Configure them in:

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

The audit checks that active containers match the expected filesystem,
security, and resource policy. In particular, it checks that the source checkout
is labelled as unmounted, the workspace is read-write, host root is not mounted,
host home is not bind-mounted as `/home/agent`, capabilities are dropped,
`no-new-privileges` is set, and resource labels match `omarchy agent policy`.

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

Omarchy declares network and credential policy but does not enforce those
controls directly. OpenShell is expected to broker network access, credential
access, secret prompts, and tool mediation. Omarchy's responsibility is the
local Git/workspace lifecycle, container launch constraints, resource limits,
and active-runtime audit.

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
