# managed-stop-target-binding Specification

## Purpose

Bind task stop and audit repair to the exact containers selected from a successful runtime observation. Prevent mutable names or repeated instance labels from redirecting those actions without claiming authenticated ownership or transactional lifecycle control.

## Requirements

### Requirement: Stop actions use full observed container IDs

At the snapshot-to-engine action boundary, task stop and audit repair SHALL pass only the selected row's full container ID to the local engine stop operation. A full ID SHALL be a string of exactly 64 lowercase hexadecimal characters. Names SHALL be display metadata only, never action targets or fallback selectors.

#### Scenario: A name changes owners after observation

- **GIVEN** the snapshot identifies container A by full ID and name N
- **WHEN** A is renamed and another container B takes name N before the stop request
- **THEN** the request targets A's full ID, not name N or B

#### Scenario: The selected container disappears

- **GIVEN** A was selected and another container now holds its former name
- **WHEN** stopping A by full ID fails because A no longer exists
- **THEN** the caller reports failure without retrying by name or stopping the replacement

### Requirement: Target validation precedes lifecycle mutation

Task stop SHALL validate every selected assignment row before any stop or assignment-status write. Audit repair SHALL validate full, unique container IDs across its captured snapshot and validate its complete repair plan before any stop or dependent registry write. Missing, malformed or duplicate IDs and unsupported target runtimes SHALL produce nonzero refusal with a diagnostic, not omission or successful repair.

#### Scenario: One task target is invalid

- **WHEN** a selected assignment has several observed rows and one lacks a full valid ID or has an unsupported runtime
- **THEN** task stop returns nonzero before stopping any row or writing `stopping` or `stopped`

#### Scenario: A duplicate target ID appears

- **WHEN** task stop's selected rows or audit repair's captured snapshot repeat a container ID
- **THEN** the command refuses before any stop or dependent lifecycle-state write
- **AND** it does not silently deduplicate the observation

#### Scenario: An audit snapshot contains a malformed ID

- **WHEN** audit repair receives a captured snapshot containing a missing, non-string, abbreviated, whitespace-bearing or non-hexadecimal container ID
- **THEN** it returns nonzero with a diagnostic before any stop or dependent registry write

### Requirement: Audit findings identify an unambiguous repair target

At the finding-to-action and action-to-registry boundaries, audit repair SHALL associate each failed policy check with its observed container ID. It SHALL refuse the entire repair plan if a failed row has no nonempty string instance label or that label maps to multiple containers in the captured snapshot. A passing row SHALL NOT become a stop target merely because it shares an instance label with a failed row.

#### Scenario: Passing and failing rows share an instance label

- **WHEN** two distinct containers share an instance label and only one fails a policy check
- **THEN** audit repair returns nonzero with an ambiguity diagnostic before stopping either container or updating dependent registry state

#### Scenario: A failed row lacks an instance association

- **WHEN** a row fails a policy check but lacks a nonempty string instance label
- **THEN** audit repair refuses the entire repair plan rather than silently skipping the failed row or reporting successful repair

#### Scenario: Distinct instances have distinct policy results

- **WHEN** observed containers have valid unique IDs and unambiguous instance labels and only one fails policy
- **THEN** audit repair selects only the failing container's ID for stopping
- **AND** the passing container receives no stop or instance-finalization request

### Requirement: Stop failure does not become successful finalization

Task stop SHALL write final assignment status `stopped` only after all selected ID-bound stop requests succeed. Audit repair SHALL report a failed ID-bound stop as `stop-failed`, return nonzero and issue no dependent instance or assignment finalization for that failed request. Earlier successful actions need not be rolled back; engine success is not independent proof of process or registry consistency.

#### Scenario: Task stop fails after an earlier successful stop

- **WHEN** one selected ID stops successfully and stopping a later ID fails
- **THEN** task stop returns nonzero and does not write final assignment status `stopped`
- **AND** the earlier stop and intermediate `stopping` state can remain

#### Scenario: Audit cannot stop a selected ID

- **WHEN** the stop operation fails for a validated audit target
- **THEN** audit repair records `stop-failed`, returns nonzero and does not finalize that target's instance or assignment
- **AND** earlier successful repair actions remain distinct from that failure

### Requirement: Existing local routing and stop policy remain distinct

Task stop and audit repair SHALL retain `--remote=false` and child-local removal of `CONTAINER_HOST` and `CONTAINER_CONNECTION`. They SHALL retain existing stop grace/escalation behavior and SHALL NOT add force, retry, deletion or automatic fallback to another controller. Unavailable required observation SHALL continue to refuse dependent actions under the existing availability contract.

#### Scenario: Parent environment selects a remote engine

- **WHEN** an otherwise valid stop request runs with remote selectors in its parent environment
- **THEN** its stop child uses explicit local routing with both selectors absent
- **AND** the parent environment remains unchanged

#### Scenario: Snapshot observation is unavailable

- **WHEN** either command cannot obtain its required successful runtime snapshot
- **THEN** it returns nonzero before its dependent stop or lifecycle-state writes

#### Scenario: An ID-bound request uses the existing stop policy

- **WHEN** either command submits a validated target
- **THEN** it retains its existing engine-default stop policy, which can escalate to KILL
- **AND** it does not claim the overview controller's TERM-only or process-fingerprint contract
