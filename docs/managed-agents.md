# Managed coding agents

Omarchy managed agents run coding tasks through isolated Git workspaces and a
container runtime. The design goal is to keep agent writes away from the source
checkout until a human explicitly reviews and applies them.

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

Omarchy declares network and credential policy but does not enforce those
controls directly. OpenShell is expected to broker network access, credential
access, secret prompts, and tool mediation. Omarchy's responsibility is the
local Git/workspace lifecycle, container launch constraints, resource limits,
and active-runtime audit.
