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

## Approval and evidence

Read `AGENTS.md` and the applicable repository guide first. OpenSpec task state, generated skill metadata, planning completion and archive status do not authorize commands or prove runtime enforcement. Publication, merge completion, provisioning, package/migration execution and activation stay separately approved. Preserve immutable migrations and unrelated edits.

Distinguish source review, simulated/offline checks, focused tests, native/graphical evidence, CI and hardware qualification. Keep initial failures alongside scoped corrections. Spec validation checks document structure; it is not application testing.

Keep raw evidence private and outside Git. Do not import credentials, account settings, session stores/transcripts, raw desktop media or personal home-directory paths. Use sanitized public references or portable local evidence locators.

## Updating

Change the version pin deliberately, install that version and review its release/compatibility changes. Refresh generated project skills with `mise exec -- openspec update`, then inspect the diff before use. Do not regenerate all integrations or modify global agent settings merely to refresh this repository.
