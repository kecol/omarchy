# managed-runtime-availability Specification

## Purpose

Distinguish a successful observation of no managed containers from an unavailable runtime observation. Keep safety decisions from treating query failure as inactivity while preserving useful configured-agent information without false running counts.

## Requirements

### Requirement: Snapshot success requires successful observation

The managed-runtime snapshot SHALL return success with one JSON array only after readiness and enumeration succeed and any required inspection and projection succeed. A successfully observed empty enumeration SHALL return `[]`. Query or validation failure SHALL return nonzero, emit a stage-specific diagnostic on stderr and emit no snapshot on stdout.

#### Scenario: Successfully empty engine inventory

- **WHEN** local engine readiness and managed-container enumeration succeed and enumerate no containers
- **THEN** the snapshot returns success and exactly an empty JSON array
- **AND** no container inspection is required

#### Scenario: Missing or unavailable engine

- **WHEN** Podman is missing or its local readiness query fails
- **THEN** the snapshot returns nonzero with an availability diagnostic
- **AND** stdout contains neither an empty array nor a partial snapshot

#### Scenario: Enumeration fails after producing output

- **WHEN** managed-container enumeration returns a failure status, including after writing candidate IDs
- **THEN** the snapshot returns nonzero with an enumeration diagnostic
- **AND** the producer does not publish those IDs as a successful observation

### Requirement: Inspection responses cover the enumerated set

For a nonempty enumeration, the snapshot SHALL accept only a valid inspection collection covering each enumerated container once. Malformed enumeration, invalid JSON, wrong response shape, missing or duplicate inspection records, unexpected identities and projection failure SHALL make the observation unavailable instead of yielding empty or partial success.

#### Scenario: Valid nonempty observation

- **WHEN** all engine stages succeed and inspection supplies valid records for the enumerated containers
- **THEN** the snapshot returns the existing projected array fields without adding an availability envelope

#### Scenario: Incomplete or invalid inspection

- **WHEN** inspection fails, returns invalid or wrong-shaped data, or omits, duplicates or substitutes an enumerated container
- **THEN** the snapshot returns nonzero with an inspection/validation diagnostic
- **AND** no partial projected array is emitted

### Requirement: Safety-sensitive consumers refuse unavailable observation

Agent audit and task preflight/start/stop/cleanup/archive SHALL fail when required runtime observation is unavailable. The dependent launch, stop, deletion or final registry update SHALL NOT proceed on an assumed zero count. Force options SHALL NOT override this refusal. Existing policies for successfully observed inventories remain in effect.

#### Scenario: Unavailable observation before admission or stop

- **WHEN** audit, task preflight/start or task stop cannot obtain a successful snapshot at a required check
- **THEN** the command returns nonzero with an unavailability diagnostic
- **AND** it does not perform its dependent launch or stop, mark an assignment launched or stopped, or report audit success

#### Scenario: Unavailable observation before destructive cleanup

- **WHEN** task cleanup or the initial task archive check cannot obtain a successful snapshot
- **THEN** the command refuses the dependent deletion or archive finalization
- **AND** the same refusal applies with `--force`

### Requirement: Archive propagates nested cleanup failure

Task archive SHALL stop and return nonzero when a nested assignment cleanup fails, including observation unavailability after its initial snapshot succeeded. It SHALL NOT mark the task archived or claim success after that failure, with or without force. This requirement does not roll back earlier completed cleanups or establish an atomic transaction.

#### Scenario: Engine becomes unavailable during archive

- **WHEN** archive's initial snapshot succeeds but a subsequent assignment cleanup fails because runtime observation is unavailable
- **THEN** archive stops and does not issue the final archived-state update
- **AND** already completed earlier cleanup remains reported as partial progress, not rolled back or advertised as full success

#### Scenario: Another nested cleanup failure

- **WHEN** a nested cleanup fails for another reason during archive, including a forced archive
- **THEN** archive returns nonzero rather than ignoring the failure and marking the task archived

### Requirement: Configured-agent listing represents unknown counts explicitly

Agent list SHALL retain its configured-agent array and definitions/mode information when runtime observation is unavailable. Each record SHALL then contain `running_instances: null` and `runtime_available: false`; text counts SHALL display `unknown`. With successful observation, counts SHALL remain numeric and `runtime_available` SHALL be true. Unrelated definition or mode errors SHALL remain errors.

#### Scenario: Configured listing without runtime observation

- **WHEN** configured-agent listing encounters runtime snapshot unavailability while its definitions and mode are valid
- **THEN** it returns the configured records successfully with null running counts and false availability fields
- **AND** its text form displays unknown counts rather than zeros

#### Scenario: Successful observation supplies counts

- **WHEN** configured-agent listing obtains a successful empty or nonempty runtime snapshot
- **THEN** it reports numeric counts, including genuine zeros, with true availability fields

### Requirement: Runtime-dependent reports do not imply inactivity on failure

Agent ps, agent inspect and task status SHALL return nonzero with a diagnostic when required runtime observation is unavailable. They SHALL NOT emit a successful empty runtime report, a zero running count or a historical fallback that implies current inactivity. Their successful output contracts SHALL remain unchanged.

#### Scenario: Reporting with unavailable runtime

- **WHEN** a runtime-dependent report cannot obtain a successful snapshot
- **THEN** it fails visibly rather than claiming no active instances
- **AND** inspect does not substitute registry history for the unavailable observation

#### Scenario: Historical inspection after successful empty observation

- **WHEN** inspect obtains a successful snapshot with no matching active instance and a historical record matches
- **THEN** its existing historical fallback remains available with its existing historical/stale distinctions
