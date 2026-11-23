# Proposal

## Why

The account-copy fixture scans shared process inventory while unrelated tests run in parallel. Give that fixture private process inventory so that test interference does not create pressure to weaken production refusal when an account home cannot be determined.

## What Changes

- Add a fixture-local Bubblewrap entry boundary to the existing `test/shell.d/agent-account-copy-test.sh`; run its complete existing body with private PID and network namespaces and a matching private `/proc`.
- Use synthetic HOME/state, a cleared environment, private temporary filesystems and read-only mounts of only the source/system files the fixture needs. Do not mount working account homes or session sockets.
- Verify namespace separation before account imports, process discovery or synthetic credential writes. An environment marker may select the inner entry, but must not count as proof of isolation.
- Make missing Bubblewrap, denied namespace setup, failed verification, timeout and nonzero test results fail the file. Do not skip, retry or fall back to host process inventory.
- Preserve the complete credential-transfer, replacement/recovery, source-name, mock-SSH and process-refusal checks. Keep the production detector and its unknown-home refusal unchanged.

### Observed behavior and agreed direction

[Tests 44922393670](https://github.com/kecol/omarchy/actions/runs/44922393670) failed at documentation head `eca2500593229a428bf6928c5fed707c9229850e`. The interrupted-replacement case expected intentional exit 78, but the detector refused an unknown default HOME before reaching that checkpoint. The detector, fixture, runner and workflow are unchanged from green parent `db9ba29a434bd21f0d183ed7b972a0d96aabd63c`. The retained log identifies no candidate PID or lifecycle state; parallel interference is plausible, not proven.

One separately approved run of the unchanged fixture passed all six existing shell checks in a verified private PID/process-filesystem/network environment. It used synthetic accounts and read-only source files from the green parent, completed in about 2.2 seconds and left no owned processes. This supports the isolation approach, but does not qualify an implemented wrapper or identify the historical CI cause. Private review and baseline receipts remain under `$HOME/Work/omarchy-account-copy-ci-review-44922393670-01/` and `$HOME/Work/omarchy-account-copy-isolated-baseline-01/`.

The approved native verification scope is now one complete isolated fixture invocation plus marker-only and namespace-setup failure controls. The originally proposed HOME-less provider-like neighbor and unchanged-parent comparison are explicitly deferred and remain unperformed, not delivery prerequisites: a child PID namespace does not hide its processes from the host, so that control could interfere with host account operations. The safe checks must not be reported as reproduction of the CI interference mechanism or historical root-cause evidence. See [design.md](design.md) for the revised boundary and [outcome.md](outcome.md) for implemented source, retained failures and delivery limits.

### Non-goals and unverified assumptions

Do not change `bin/omarchy-agent-account-transfer`, `bin/omarchy-agent-account-state`, the shared runners, CI workflow, package lists or unrelated fixtures. Do not add a generic execution framework, mark this test exclusive as a substitute for isolation, install prerequisites during tests, launch providers or use real SSH/accounts. The actual CI image's namespace admission remains to be checked by a separately approved new-head CI run. The failed run remains failed. Shell-feature spec synchronization/archive, Herdr, upstream catch-up and historical VM/storage/executor investigations are outside this change.

## Capabilities

### New Capabilities

None. This is fixture tooling, not a new runtime capability; `.openspec.yaml` declares `skip_specs: true`.

### Modified Capabilities

None. Existing production behavior contracts and the account-copy safeguard remain unchanged. Acceptance criteria are in [design.md](design.md) and [tasks.md](tasks.md), not a new product specification.

## Impact

The intended implementation scope is one existing file: `test/shell.d/agent-account-copy-test.sh`. Bubblewrap is already listed in `install/omarchy-base.packages`; no package or image change is planned. A missing prerequisite must fail clearly, not trigger installation or a silent skip.

Agent safety improves through separation of synthetic test processes and credentials from the surrounding session while retaining conservative production refusal. Sustainable upstream integration benefits from a fixture-local change rather than a shared-runner rewrite or runtime-policy workaround. No desktop UI, saved default, managed-container lifecycle or user-facing command changes. This proposal authorizes planning only, not implementation, native execution, publication, activation or archive.
