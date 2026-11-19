# Managed engine selection

## Purpose

Keep Omarchy's host-local managed-runtime and editor-workspace workflows on the local Podman engine even when the user's ambient configuration selects a remote engine. This contract concerns routing, not complete engine or container isolation.

## ADDED Requirements

### Requirement: Managed-runtime inventory and legacy stop actions select the local engine

Managed-runtime snapshot, audit-fix and task-stop Podman requests SHALL select the local engine with `--remote=false` and remove `CONTAINER_HOST` and `CONTAINER_CONNECTION` from each child environment. Observation and dependent stops SHALL retain the current availability, full-ID targeting, complete-plan validation, refusal and finalization contracts.

#### Scenario: Managed inventory under a remote default

- **WHEN** a managed-runtime snapshot is requested while ambient configuration selects a remote Podman engine
- **THEN** engine availability, container enumeration and container inspection requests explicitly select the local engine
- **AND** the snapshot does not query the selected remote engine

#### Scenario: Audit requests a stop under a remote default

- **WHEN** audit fix requests a stop for a drifted instance while ambient configuration selects a remote Podman engine
- **THEN** its stop request explicitly selects the local engine
- **AND** the target is the selected row’s full observed 64-character lowercase hexadecimal container ID, never a name or name fallback; repair validation and dependent finalization follow the current target-binding contract.

#### Scenario: Assignment stop under a remote default

- **WHEN** task stop resolves an assignment with active supported instances while ambient configuration selects a remote Podman engine
- **THEN** its snapshot queries and every requested stop explicitly select the local engine
- **AND** every selected target is validated before any stop or lifecycle-state write; requests use full observed IDs without name fallback, and final `stopped` status requires all selected stops to succeed.

### Requirement: Editor workspace engine operations select the local engine

Editor workspace Podman requests SHALL use `--remote=false` with `CONTAINER_HOST` and `CONTAINER_CONNECTION` absent from each child environment. This applies to listing, readiness/identity inspection, image/volume operations, explicit builds, start/run, SSH endpoint/key discovery and ordinary/failed-audit stops. Generic Git/SSH/editor subprocess environments, caller-specific failures, host-local paths and loopback SSH SHALL retain their existing policies.

#### Scenario: Workspace listing under a remote default

- **WHEN** workspace listing queries runtime state for registered workspaces while ambient configuration selects a remote Podman engine
- **THEN** the bounded runtime-state request explicitly selects the local engine
- **AND** the existing JSON fields, timeout and unknown-state behavior remain unchanged

#### Scenario: Workspace preparation and startup under a remote default

- **WHEN** an explicit workspace build or workspace start/code request needs engine operations while ambient configuration selects a remote Podman engine
- **THEN** all resulting Podman requests explicitly select the local engine
- **AND** existing explicit-build, image-pin, mount, resource, identity and SSH host-key checks remain in effect
- **AND** start/code does not gain an automatic image build or pull

#### Scenario: Workspace stop paths under a remote default

- **WHEN** workspace stop is requested or a newly created workspace container fails its runtime audit while ambient configuration selects a remote Podman engine
- **THEN** the requested stop explicitly selects the local engine
- **AND** existing target/ownership checks, ten-second grace argument and retained workspace storage remain unchanged

### Requirement: Local routing does not introduce remote fallback or global configuration changes

The scoped workflows SHALL NOT retry a failed local Podman operation against a remote engine or rewrite user engine connection settings or parent/global environment defaults. Local routing SHALL preserve each caller's current failure contract, including snapshot unavailability refusal. Direct user Podman commands and the workspace editor's intentional Remote SSH connection remain outside this contract.

#### Scenario: Local engine failure with a reachable remote default

- **WHEN** a scoped local engine request fails while ambient configuration selects a remote engine
- **THEN** the workflow does not issue a remote-engine retry
- **AND** unavailable managed-runtime observation returns nonzero with a diagnostic and no snapshot stdout, and dependent safety-sensitive actions refuse. Workspace runtime-listing failure retains its distinct unknown-state reporting.

#### Scenario: Omarchy operation leaves the user's engine preference intact

- **WHEN** a scoped Omarchy workflow explicitly selects the local engine
- **THEN** it does not rewrite the user's engine connection configuration or global environment defaults
- **AND** unrelated user Podman commands and workspace Remote SSH configuration remain outside this routing change
