# OpenSpec development tracking

OpenSpec keeps reviewed intent, current work and outcomes in the repository instead of relying on a long agent conversation. It is a development tool, not a runtime safety boundary or permission system.

## Setup

The repository pins `@fission-ai/openspec` 2.0.0 in `mise.toml`. This is a project tool, not a new default installed on every Omarchy desktop. OpenSpec requires Node.js 22.12.0 or newer. Project configuration disables OpenSpec telemetry.

From a trusted checkout:

```bash
mise trust ./mise.toml
mise install npm:@fission-ai/openspec@2.0.0
mise exec -- openspec --version
```

Do not add a global npm installation or change the user's global mise configuration to use this project. Review the pinned version and generated skills before trusting a different checkout. The initial installation used disabled package lifecycle-script settings; dependency installation is still an explicit operation, not an agent safety guarantee.

## Tracked files

- `openspec/config.yaml`: fork purpose, evidence/approval boundaries and artifact guidance.
- `openspec/changes/<name>/`: an active proposal, design, tasks and any behavior deltas.
- `openspec/specs/`: durable reviewed behavior contracts. This setup does not invent a full runtime specification or certify existing behavior.
- `openspec/changes/archive/`: changes explicitly archived after review; not a place to fabricate pre-OpenSpec history.
- `openspec/history/work-ledger.md`: partial curated history, completed milestones, unresolved failures, blocked/deferred work and portable private-evidence locators.
- `.agents/skills/openspec-*/`: generated upstream workflows shared by Pi and Codex. Do not duplicate them into `.pi/skills` or `.codex/skills`.

The initial `separate-agent-safety-layer` change is documentation/inventory work only, with `skip_specs: true`. It records the maintenance direction without claiming a new runtime capability. See the change's task list for current progress. Installing OpenSpec did not complete the boundary inventory or extraction proposal.

## Daily use

```bash
mise exec -- openspec list
mise exec -- openspec list --specs
mise exec -- openspec status --change separate-agent-safety-layer
mise exec -- openspec validate --all --strict --no-interactive
```

Start Pi or Codex from this repository so project skills are discoverable. For Pi, use `/skill:openspec-explore` or `/skill:openspec-propose` to select the shared skills explicitly. For Codex, use `$openspec-explore` or `$openspec-propose`. A Pi session started outside the repository will not necessarily discover these project skills merely by reloading.

Use the proposal workflow to capture a new bounded change. Review its planning artifacts before explicitly starting apply. Keep changes small enough to deliver useful outcomes without repeatedly building unrelated validation infrastructure.

Update task checkboxes only after the stated deliverable and verification are complete. When blocked, record the reason and what was not run; do not check the task merely because a substitute passed. Use the work ledger for pre-OpenSpec milestones rather than retroactively pretending those tasks ran through this workflow.

## Testing and dev-linked activation

OpenSpec records the development process; it does not replace Omarchy's [test suites and CI](testing.md) or [disposable-VM acceptance process](../agents/skills/acceptance-tests.md). `openspec validate` checks planning artifacts, not application behavior. Select validation by the behavior and risk of the change, not by whether it uses OpenSpec.

| Change | Expected validation |
| --- | --- |
| Small declarative edit or documentation correction | Review and the relevant existing structural/focused checks. A dedicated PR or VM is not required solely because the edit has an OpenSpec artifact; state the reason for the reduced scope. |
| Parsing, routing or shared helper logic | Focused behavioral regressions and proportionate integration coverage. Use the normal PR/CI route when publishing. Select the broader runner according to `AGENTS.md`; do not repeatedly run the full suite during development. |
| Runtime discovery, admission, stop or destructive cleanup safety | Focused regressions and meaningful negative controls, targeted native checks in a disposable local VM, and a PR with the existing CI workflow before integration into the active checkout. Record and obtain review of any exception rather than silently omitting a gate. |

Use graphical acceptance when the behavior needs a real desktop. Package, installation, shipped-default and boot changes need the corresponding package/ISO/boot checks from the existing guides. A CLI-only change does not by itself require a fresh ISO build or a graphical campaign. Do not add a parallel testing framework or revive a paused validation campaign merely to satisfy a checklist.

### Keep implementation separate from the active checkout

Warning: a dev-linked checkout is a runtime source, not an inactive staging directory. Changes to resolved `bin/`, `default/` or `shell/` files can affect new commands or running readers immediately or on their next reload. A commit is not the activation boundary. Checking a task or omitting an explicit install/reload command does not make those edits inactive.

1. Verify the active `OMARCHY_PATH`, command resolution and relevant source paths before implementation.
2. For safety-sensitive changes, implement in a separate worktree/branch that is not dev-linked. Keep the host dev link unchanged.
3. Point isolated tests at the candidate through their existing ROOT/PATH/environment mechanisms. Check that child commands cannot silently resolve the active checkout instead; login shells can reset these paths.
4. Run the approved focused checks with scratch state, bounded resources and complete logs. Add native VM validation when required by the selected risk scope.
5. Publish the reviewed candidate through a PR after separate commit/publication approval. Review CI and native results separately against the exact tested revision/content.
6. Integrate into the active checkout only after the required results and integration/activation approval. Verify that the integrated content matches the reviewed candidate and command resolution selects it.

For CLI scripts already resolved from the active checkout, integration affects subsequent invocations without a reboot. Existing processes do not automatically restart. QML reloads, copied user configuration, fixed-path system files, packaged services and container images have different activation requirements. Changing the dev-link target also has its own session/reboot contract in `omarchy dev link`; do not confuse that with editing the already selected checkout.

### Preserve distinct validation results

The existing PR workflow runs `./test/all` inside a fresh installed Omarchy VM. Many tests still use fake executables or scratch data. A VM-backed CI pass is broader regression evidence, but it does not prove native Podman behavior unless a check actually exercised Podman. Targeted native checks should use disposable guest data and inert containers, not host projects, credentials or provider sessions. Identify mixed native/fault-injection cases explicitly.

A planned VM run requires a separately reviewed execution scope: image/source identity, available resources and limits, transport, guest actions, evidence collection and owned cleanup. Do not assume an existing harness meets the current machine's constraints. A blocked prerequisite remains blocked; do not bypass it or claim a fixture substitute closed the native gate.

Record the exact tested revision and runtime/test content, environment/version context, complete logs, failures/skips and cleanup outcome. Retain original failures and link scoped corrections rather than replaying until green. Recheck affected behavior after a covered source edit; do not rerun a successful suite only to redisplay its output. A first CI run is a distinct environment check. Required but unperformed or failed checks remain open integration gates unless the user explicitly reviews a documented exception. Use outcome and ledger records to distinguish implemented source, validated behavior and active deployment; do not rewrite historical evidence or infer activation status from Git status alone.

## Approval and evidence

Read `AGENTS.md` and the applicable repository guide first. OpenSpec task state, generated skill metadata, planning completion and archive status do not authorize commands or prove runtime enforcement. Publication, merge completion, provisioning, package/migration execution and activation stay separately approved. Preserve immutable migrations and unrelated edits.

Distinguish source review, simulated/offline checks, focused tests, native/graphical evidence, CI and hardware qualification. Keep initial failures alongside scoped corrections. Spec validation checks document structure; it is not application testing.

Keep raw evidence private and outside Git. Do not import credentials, account settings, session stores/transcripts, raw desktop media or personal home-directory paths. Use sanitized public references or portable local evidence locators.

## Updating

Change the version pin deliberately, install that version and review its release/compatibility changes. Refresh generated project skills with `mise exec -- openspec update`, then inspect the diff before use. Do not regenerate all integrations or modify global agent settings merely to refresh this repository.
