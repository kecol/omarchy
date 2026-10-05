# Agent Control Plane

Status: Draft

## Purpose

This document defines a control plane for coding agents in Omarchy.

The control plane manages agent identity, work assignment, workspace isolation, runtime policy, and system observation. It supports host processes, rootless Podman containers, and OpenShell sandboxes.

This design uses controlled English inspired by ASD-STE100. It does not claim formal ASD-STE100 compliance.

## Requirements Language

The words `must`, `should`, and `may` have specific meanings in this document.

- `must` identifies a mandatory requirement.
- `should` identifies a recommended requirement. An implementation can omit it when it records a reason.
- `may` identifies an optional capability.

## Goals

The control plane must provide these capabilities:

- List each configured agent.
- List each active agent instance.
- Identify the harness and runtime of each agent.
- Identify the project, task, team, and workspace of each instance.
- Report the filesystem and network access of each instance.
- Report credential exposure and session persistence.
- Show communication and shared-resource paths between agents.
- Give each assignment a private workspace.
- Transfer work through immutable artifacts.
- Prevent unapproved agents from changing canonical branches.
- Support Podman as a safer alternative to host execution.
- Support OpenShell as a policy-controlled runtime.
- Support durable harnesses without requiring them for all agents.

## Non-goals

The first implementation will not provide these capabilities:

- Formal verification of sandbox security.
- Prompt-injection prevention.
- Automatic semantic detection of confidential source code.
- A common transcript format for all harnesses.
- Direct concurrent editing of one checkout by multiple agents.
- Automatic merge approval by a language model.

## Terms

### Harness

A harness manages a model conversation and its tools. Pi, Pi Durable, Claude Code, Codex, and OpenCode are harnesses.

### Agent

An agent is a configured identity. Its configuration selects a harness, a role, a model policy, and a runtime policy.

### Runtime

A runtime supplies the security boundary for an agent execution environment. The initial runtime types are `host`, `podman`, and `openshell`.

### Conversation

A conversation is a persistent interaction history. A conversation can continue after its process stops.

### Instance

An instance is one active or historical execution of a conversation. A restart creates a new instance for the same conversation.

### Project

A project identifies a canonical Git repository and its control policy.

### Task

A task defines a goal and an immutable base commit. A task can have multiple assignments.

### Assignment

An assignment connects one agent, one role, and one task. An assignment owns one private workspace.

### Workspace

A workspace is an independent Git clone for one assignment. It is not the canonical host checkout.

### Sandbox

A sandbox is a runtime environment that exposes one workspace to one assignment.

### Team

A team is an explicit set of agents and roles that work on one project or task.

### Artifact

An artifact is an immutable output. Candidate commits, patches, test reports, and review reports are artifacts.

### Attestation

An attestation records a decision about one exact artifact digest. An approval is one type of attestation.

## Safety Invariants

The implementation must enforce these invariants:

1. Two active assignments must not share a writable checkout.
2. An agent must not receive the canonical host checkout as its workspace.
3. An agent workspace must have independent Git metadata.
4. An agent must not receive credentials that can update a canonical branch.
5. A review must identify one exact candidate commit.
6. An approval must not apply to a later branch head.
7. Only the trusted controller may promote an approved candidate.
8. A runtime must not fall back to another runtime.
9. An unknown security state must not appear as a safe state.
10. Inventory records must not contain credentials or transcript content.
11. The control-plane database must not be mounted into an agent sandbox.
12. Agent-to-agent access must require an explicit policy edge.

## System Architecture

The system has three planes.

### Control Plane

The trusted control plane manages desired state and observed state. It runs outside agent sandboxes.

The control plane owns these resources:

- Project records
- Team records
- Task and assignment records
- Agent definitions
- Workspace creation
- Artifact collection
- Review attestations
- Promotion decisions
- Runtime inventory
- Security policy
- Audit events

### Conversation Plane

The conversation plane runs harnesses. A conversation can outlive a harness process.

A traditional command-line harness usually has one process for one conversation. Pi Durable can run many conversations in one harness process.

The data model must not assume a one-to-one relation between harness processes and conversations.

### Execution Plane

The execution plane runs tools against a workspace. A sandbox lease connects one conversation to one workspace and runtime policy.

A durable harness may run in the trusted conversation plane while its tools run in OpenShell. This design keeps provider credentials out of the tool sandbox.

## Entity Relationships

The primary relationships are:

```text
Project
  └── Task
        ├── Assignment
        │     ├── Agent
        │     ├── Workspace
        │     ├── Conversation
        │     │     └── Instance
        │     └── Sandbox
        └── Artifact
              └── Attestation
```

A team references agents and roles. A team does not imply shared filesystem or network access.

## Workspace Model

Each assignment must receive an independent clone.

The controller should store managed workspaces below this directory:

```text
~/.local/share/omarchy/agent-workspaces/<project-id>/<task-id>/<assignment-id>/repo
```

The controller should use a clone operation that does not share local Git object files:

```bash
git clone --no-local --no-checkout <source> <workspace>
```

A Git worktree shares repository metadata with its parent repository. Therefore, a Git worktree does not provide the required isolation boundary.

The sandbox must mount only the assignment workspace. It must not mount sibling workspaces.

A private workspace may be writable for all roles. Role policy controls artifact promotion instead of individual path permissions.

## Task and Review Workflow

The controller creates a task at an immutable base commit.

```text
base commit
    |
    v
coder assignment
    |
    v
candidate commit
    |
    v
reviewer assignment
    |
    v
review attestation
    |
    v
trusted promotion
```

The coder creates a candidate in a private workspace. The controller seals the candidate as an immutable artifact.

The reviewer receives a separate workspace at the exact candidate commit. The review result must identify that commit.

A revision creates a new candidate commit. The prior approval or rejection remains attached to the prior commit.

Before promotion, the controller must verify all of these conditions:

- The candidate digest matches the reviewed digest.
- The required attestations exist.
- The attestations are valid for the current policy.
- Required tests have valid results.
- The candidate still applies to the permitted base or integration state.

The controller must update the canonical branch. An agent must not perform this operation.

## Role Capabilities

Roles control workflow operations. Roles do not control individual source paths by default.

| Role | Typical capabilities |
|---|---|
| Coder | Read the task, modify its private workspace, and create a candidate |
| Reviewer | Inspect a candidate, run tests, and submit a review |
| Tester | Run tests and submit a test result |
| Integrator | Request promotion of an approved candidate |
| Coordinator | Create tasks, assign agents, and request revisions |

A reviewer may modify files in its private workspace for analysis. The reviewer cannot publish those changes as a candidate without the `create-candidate` capability.

## Session Policy

Each agent definition must select a session scope.

| Scope | Behavior |
|---|---|
| `none` | The runtime discards the session after the instance stops |
| `task` | The runtime persists the session for one assignment or task |
| `agent` | The runtime persists the session across tasks for one agent identity |

The default scope should be `task`. This scope reduces context transfer between unrelated tasks.

Credential state must be separate from transcript state when the harness supports that separation.

A resumed session remains untrusted input. Runtime isolation does not make stored instructions safe.

## Runtime Security Levels

### Host

Host execution provides no host filesystem boundary. The control plane must report host access as broad unless an operating-system policy proves a narrower state.

Host execution should not be permitted for managed team tasks.

### Podman

Podman provides a safer execution boundary than host execution.

The Podman runtime must use a rootless container. It must mount only the private workspace and declared state volumes. It must not mount the host home, host root, SSH agent, or container socket by default.

Podman does not hide a credential from the process that uses that credential. An agent with unrestricted network access can disclose readable data.

The user must acknowledge this risk before the agent uses persistent credentials in Podman.

### OpenShell

OpenShell should provide the policy-controlled runtime.

An OpenShell policy should control these resources:

- Filesystem mounts
- Credential mediation
- Network destinations
- Host reachability
- Agent-to-agent reachability
- Runtime audit events

The dispatcher must fail when a required OpenShell control is unavailable. It must not use Podman or host execution as a fallback.

OpenShell does not prevent prompt injection. It limits the resources and destinations that a compromised agent can use.

## Desired and Observed State

The control plane must keep desired state separate from observed state.

A status field should include its source and verification time.

```text
Network policy
  Desired:   provider-allowlist
  Observed:  openshell-policy-8c21
  Verified:  2026-10-05T04:30:00Z
```

The runtime adapter must inspect the active runtime when possible. It must not report saved labels as proof of active enforcement.

Each uncertain value must use an explicit state such as `unknown` or `unverified`.

## Instance Identity

Each launch must receive a unique instance identifier.

A Podman container should use a name such as:

```text
omarchy-agent-<agent-id>-<instance-id>
```

The container should include labels for non-secret identifiers:

- Managed-by identifier
- Instance identifier
- Agent identifier
- Harness identifier
- Runtime identifier
- Project identifier
- Task identifier
- Assignment identifier
- Team identifier

The labels must not include prompts, credentials, transcript content, or private host paths.

## Runtime Adapter Interface

Each runtime adapter must provide these operations:

```text
capabilities
create
start
inspect
stop
destroy
events
```

The `capabilities` operation reports what the adapter can enforce and observe.

The `inspect` operation reports actual mounts, runtime state, network state, and policy identity.

The `events` operation may provide runtime lifecycle and policy events.

Podman can provide coarse process and container information. OpenShell should provide more detailed policy evidence.

## Harness Adapter Interface

Each harness adapter should provide these operations when the harness supports them:

```text
create-conversation
start-conversation
resume-conversation
stop-conversation
inspect-conversation
submit
watch
usage
```

An opaque command-line harness may support only part of this interface. The control plane must report unsupported capabilities.

## Reachability Model

The control plane must report separate reachability types.

### Filesystem Reachability

Examples include:

- Shared writable workspace
- Shared read-only workspace
- Shared state volume
- Host home mount
- Host root mount
- Runtime socket mount

### Network Reachability

Examples include:

- Internet egress
- Provider-only egress
- Host gateway access
- Peer sandbox access
- Published inbound port
- Message broker access

### Workflow Reachability

Examples include:

- Candidate delivery
- Review delivery
- Test result delivery
- Coordinator message

The control plane must not infer a team only from shared resources. Team membership must be explicit.

A graph can show safe and unsafe edges:

```text
coder-a   --candidate:abc123--> reviewer-a
reviewer  --review:abc123-----> controller
coder-a   --internet----------> unrestricted
agent-x   --host-home:rw------> host
```

## Pi Durable Integration

[Pi Durable](https://earendil.com/posts/pi-durable/) is an experimental durable harness. Its design matches several control-plane requirements.

Useful Pi Durable capabilities include:

- Durable conversations
- Durable tasks with checkpoints
- Explicit task ownership
- Idempotent submissions with request identifiers
- Replay policy for interrupted tools
- Per-conversation agent configuration
- Per-conversation execution environments
- Conversation forks
- Task graphs
- Atomic transcript and document updates
- Live watchers
- Usage records

The Pi Durable reviewer example gives a reviewer a separate checkout and a restricted tool set. Its sandbox example assigns one execution environment to each conversation.

Pi Durable should be a harness adapter. It should not be the only global inventory source.

This boundary is necessary for these reasons:

- Other harnesses do not use Pi Durable storage.
- Pi Durable is experimental.
- One process owns one Pi Durable storage at a time.
- Omarchy must track Git artifacts, runtime policy, and cross-harness teams.

A Pi Durable harness may keep provider credentials in the trusted conversation plane. Its execution environment may send tool operations to an OpenShell sandbox. This arrangement reduces credential exposure in the sandbox.

The control plane should apply Pi Durable design principles to all adapters where practical. These principles include atomic state changes, request identifiers, ownership trees, and explicit replay policy.

## Control-plane Storage

The first control-plane store should use SQLite. The store should use transactions for state changes and an append-only event table for audit history.

The store should contain identifiers, state transitions, policy references, artifact digests, and timestamps.

The store must not contain provider credentials. Transcript content should remain in harness-specific storage.

The store should use owner-only filesystem permissions.

## Proposed Commands

The command interface should include these command groups:

```text
omarchy project list
omarchy project inspect <project>

omarchy team list
omarchy team inspect <team>

omarchy task list
omarchy task inspect <task>
omarchy task create <project> <goal>
omarchy task assign <task> <agent> <role>

omarchy agent list
omarchy agent ps
omarchy agent inspect <agent-or-instance>
omarchy agent security <agent-or-instance>
omarchy agent graph [project-or-team]
```

Each inspection command should support machine-readable JSON output.

## Implementation Stages

### Stage 1: Inventory

- Define stable identifiers and the SQLite schema.
- Add instance names and labels to Podman launches.
- Add agent list, process list, and inspection commands.
- Record desired and observed security state.

### Stage 2: Private Workspaces

- Add project registration.
- Add task and assignment records.
- Create independent assignment clones.
- Prevent canonical checkout mounts for managed tasks.

### Stage 3: Artifact Workflow

- Seal candidate commits.
- Create reviewer workspaces from exact candidates.
- Record reviews and test results as attestations.
- Add trusted promotion with commit verification.

### Stage 4: OpenShell

- Add the OpenShell runtime adapter.
- Add credential mediation.
- Add network policies.
- Add policy inspection and fail-closed checks.

### Stage 5: Durable Harnesses

- Add a Pi Durable harness adapter.
- Connect each conversation to one sandbox lease.
- Import task graph and usage observations.
- Support durable submission and recovery.

### Stage 6: Additional Harnesses

- Add Claude Code and Codex images.
- Add their session adapters.
- Report unsupported durable capabilities explicitly.

## Open Design Questions

The implementation must resolve these questions before Stage 3:

1. What artifact format transfers a candidate into the trusted controller?
2. What validation must run before the controller imports an untrusted Git object?
3. Does each task have one conversation per assignment or multiple conversations?
4. When does the controller destroy or archive a private workspace?
5. Which attestations are mandatory for each project?
6. How does the controller handle a candidate whose base is stale?
7. Which process owns the SQLite writer lock?
8. Which OpenShell release and policy interface meet the required controls?
