# Spec Delta

## Purpose

Provide explicit independent maintenance terminals in verified running agent containers. Bind user selection to the observed container identity without broadening container access or changing harness lifetime.

## ADDED Requirements

### Requirement: Shell selection identifies an existing agent instance

At the user-selection boundary, `omarchy agent shell` SHALL offer a picker of current-user running Omarchy agent containers. An explicit instance UUID or unique UUID prefix of at least eight characters SHALL select one instance. The picker SHALL distinguish instances by agent, project, instance and start time. Host agents, editor containers and arbitrary container names SHALL NOT be accepted as targets.

#### Scenario: Several containers use the same agent

- **WHEN** several running instances use the same agent
- **THEN** the picker presents their distinguishing metadata and preserves the selected instance identity independently of its display label
- **AND** the action uses no agent-name or first-match fallback

#### Scenario: Selector is missing or ambiguous

- **WHEN** an explicit selector matches no instance, matches several instances or uses an unsupported selector form
- **THEN** the command refuses without executing a shell or selecting another container

### Requirement: Shell execution revalidates the exact target

At the selection-to-execution boundary, the controller SHALL obtain fresh metadata and verify the original instance, full container ID, current-user process identity, boot identity, process start time and namespaces. It SHALL target only a 64-character lowercase hexadecimal container ID. Missing, malformed, stopped, changed or unverifiable targets SHALL cause refusal without fallback.

#### Scenario: A replacement takes the selected container name

- **GIVEN** the user selected container A
- **WHEN** A disappears and container B takes its name before execution
- **THEN** no shell is executed in B
- **AND** the controller reports refusal or failure for A without retrying by name

#### Scenario: Process identity changes

- **WHEN** the selected instance's process start time or namespaces change before the final check
- **THEN** no shell process is requested and the user must refresh selection

### Requirement: Unavailable inventory is not an empty inventory

At the observation-to-action boundary, readiness, inventory or required metadata failure SHALL be reported as unavailable and SHALL prevent shell execution. Successful observation of no eligible containers SHALL produce an empty picker state without launching anything. Unknown observation SHALL NOT be represented as absence or used to select a historical target.

#### Scenario: Engine observation fails

- **WHEN** the local engine query fails or returns an incomplete or malformed response
- **THEN** the command reports unavailability rather than claiming there are no running containers
- **AND** no shell, restart or alternative-runtime request occurs

#### Scenario: Successfully empty inventory

- **WHEN** a successful inventory contains no eligible running agent container
- **THEN** the picker reports the empty state and permits exit or an explicit refresh without creating a container

### Requirement: Shell access uses the existing local runtime boundary

At the host-to-engine boundary, shell metadata and execution requests SHALL use local rootless Podman with `--remote=false` and child-local removal of `CONTAINER_HOST` and `CONTAINER_CONNECTION`. Shell execution SHALL retain the configured container user, mounts, environment, working directory and resource restrictions, without host environment forwarding, user overrides, privileged execution or new mounts.

#### Scenario: Parent environment selects a remote engine

- **WHEN** the parent environment contains either remote selector
- **THEN** shell metadata and execution children omit both selectors and use explicit local routing
- **AND** the parent environment remains unchanged

#### Scenario: Maintenance shell has the existing container access

- **WHEN** the controller opens a shell successfully
- **THEN** it uses the container's configured user, working directory and environment under the existing container limits
- **AND** the controller does not import host credentials, sockets or additional filesystem access

### Requirement: Shell terminal access is explicit and independent

At the terminal boundary, **Open shell** SHALL be a separate action from **Attach existing harness**. Shell execution SHALL require a foreground controlling host terminal and run fixed `/bin/bash` interactively through Podman exec. The controller SHALL inherit terminal streams directly without capturing output, replaying logs or sending automatic input. Exit and Back SHALL remain menu defaults.

#### Scenario: User opens a maintenance terminal

- **WHEN** the user explicitly selects **Open shell** for a verified target
- **THEN** the controller opens a separate exec terminal, not the harness's attached terminal
- **AND** returning from the shell returns to the selected-instance menu without requesting a stop

#### Scenario: User cancels or lacks a terminal

- **WHEN** the user cancels selection or invokes an interactive shell without a foreground controlling terminal
- **THEN** no shell process is requested

#### Scenario: Container init has no allocated terminal

- **WHEN** a verified running target has no original attached terminal but the caller has a foreground controlling terminal
- **THEN** shell access can allocate its own exec terminal without requiring the init process to have terminal or open-stdin flags
- **AND** existing attachment eligibility remains unchanged

### Requirement: Target checks do not execute container commands

`omarchy agent shell <instance> --check` SHALL validate the selected target through metadata only, without requiring a host terminal, executing Bash or opening terminal streams. `--check` without an instance SHALL fail rather than open an interactive picker. A successful check SHALL NOT claim that Bash exists or that future execution is guaranteed.

#### Scenario: Noninteractive target check

- **WHEN** a caller checks an unambiguous verified running instance without a terminal
- **THEN** the command reports target verification without executing a container command or inspecting conversation content

### Requirement: Shell access preserves harness lifecycle and reports failures

At the shell-to-lifecycle boundary, shell exit SHALL NOT trigger container stop, removal or assignment finalization. Harness exit SHALL retain its existing container-stop behavior. Failed exec or missing Bash SHALL be reported without installation, automatic retry, host fallback or harness restart. The direct command SHALL propagate the shell or engine exit status.

#### Scenario: Harness exits during maintenance

- **WHEN** the harness exits while an exec shell is open
- **THEN** the existing container lifecycle can terminate that shell
- **AND** the controller does not keep the container alive or restart it

#### Scenario: Bash cannot be executed

- **WHEN** the engine cannot execute `/bin/bash` in the selected container
- **THEN** the command reports failure without installing software, trying another shell or starting a replacement container
