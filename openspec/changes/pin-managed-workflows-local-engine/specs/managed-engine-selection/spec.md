# Managed engine selection

## Purpose

Keep Omarchy's host-local managed-runtime and editor-workspace workflows on the local Podman engine even when the user's ambient configuration selects a remote engine. This contract concerns routing, not complete engine or container isolation.

## ADDED Requirements

### Requirement: Managed-runtime inventory and legacy stop actions select the local engine

Managed-runtime snapshot queries, `omarchy agent audit --fix` stop actions and `omarchy task stop` stop actions SHALL explicitly select the local Podman engine regardless of ambient remote-engine defaults. The engine-selection boundary covers both observation and the subsequent action, not just one side of that workflow.

#### Scenario: Managed inventory under a remote default

- **WHEN** a managed-runtime snapshot is requested while ambient configuration selects a remote Podman engine
- **THEN** engine availability, container enumeration and container inspection requests explicitly select the local engine
- **AND** the snapshot does not query the selected remote engine

#### Scenario: Audit requests a stop under a remote default

- **WHEN** audit fix requests a stop for a drifted instance while ambient configuration selects a remote Podman engine
- **THEN** its stop request explicitly selects the local engine
- **AND** the requested container name and existing audit registry-update behavior remain unchanged

#### Scenario: Assignment stop under a remote default

- **WHEN** task stop resolves an assignment with active supported instances while ambient configuration selects a remote Podman engine
- **THEN** its snapshot queries and every requested stop explicitly select the local engine
- **AND** assignment selection, existing container targets and stopping/stopped state transitions remain unchanged

### Requirement: Editor workspace engine operations select the local engine

Editor workspace engine operations SHALL explicitly select the local Podman engine regardless of ambient remote-engine defaults. This includes runtime listing, readiness and identity inspection, image/volume operations, explicit builds, container start/run, SSH endpoint/key discovery and ordinary or failed-audit stops. Host paths and loopback SSH remain host-local inputs.

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

The scoped workflows SHALL NOT retry a failed local Podman operation against a remote engine or change user engine connection configuration to achieve locality. This requirement does not replace each caller's existing error/output handling or govern direct user Podman commands and the workspace editor's intentional Remote SSH connection.

#### Scenario: Local engine failure with a reachable remote default

- **WHEN** a scoped local engine request fails while ambient configuration selects a remote engine
- **THEN** the workflow does not issue a remote-engine retry
- **AND** its existing failure/output policy remains in effect, including the legacy snapshot's documented empty-success limitation

#### Scenario: Omarchy operation leaves the user's engine preference intact

- **WHEN** a scoped Omarchy workflow explicitly selects the local engine
- **THEN** it does not rewrite the user's engine connection configuration or global environment defaults
- **AND** unrelated user Podman commands and workspace Remote SSH configuration remain outside this routing change
