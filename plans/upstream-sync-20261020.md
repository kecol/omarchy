# Upstream quattro integration review: 2026-10-20

## Decision

The source merge is suitable for a review PR, subject to the known upstream translation-test failure. Do not activate this checkout on the current desktop yet. Matching system packages and a disposable VM acceptance run remain deployment gates. Passing source tests does not prove that a package update, migration run, or reboot will succeed.

## Pinned inputs and isolation

- Fork input: `822fc5ba7a76534c2a154f51d5c2c99a2a273d67`.
- Upstream input: `ce39c5e9e9e4f5db7e023a07d0eeda9351ef9c80`.
- Common ancestor: `902fd8aeb`.
- Initial divergence: 46 fork-only commits and 391 upstream-only commits.
- Integration branch: `sync/upstream-quattro-20261020`.
- Integration worktree: `/home/kecol/Projects/omarchy-upstream-sync`.
- Backup ref: `backup/quattro-before-upstream-20261020`.
- Unmodified upstream comparison worktree: `/home/kecol/Projects/omarchy-upstream-baseline`.

The active `quattro` checkout remains at the fork input. No dev-link switch, system package update, or intentional host migration execution formed part of this review. Migration tests use temporary fixtures and mocked system commands. The host pending-migration check used `omarchy-migrate --pending` only.

## Merge resolution

Only `bin/omarchy-agent` required a manual conflict resolution. The merged launcher retains the fork's host/container overrides, managed Pi prompt handling, session resume/continue, and one-shot controls. It also incorporates upstream's Kimi launcher, packaged OpenClaw bootstrap exception, and user-installed Cursor/Muse preference. The local Cursor/Muse preference applies only to host mode, so container commands do not inherit a host executable path.

The other paths changed on both sides (`AGENTS.md`, `bin/omarchy`, and `test/shell.d/default-agent-test.sh`) merged without textual conflicts. CLI and launcher tests passed after the merge.

Upstream's command-style test exposed raw command checks in eight fork commands. The integration changes replace them with command helpers, use `type -P` where the executable path is needed, and remove the optional presence check for the system-provided `journalctl`. Focused agent tests pass with these changes.

## Automated validation

The full non-graphical suite ran with the worktree's `OMARCHY_PATH` and `bin` directory. The run cleared compositor variables and inherited `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_DATA_HOME`, and `XDG_STATE_HOME`. Clearing these XDG overrides lets each test's temporary `HOME` control its state paths.

- CLI suite: passed.
- Shell suite: 1 of 477 test files failed.
- Checks were skipped in 47 of those files; these include compositor, hardware, performance-budget, and missing companion-package coverage. A file can run some checks and skip others.
- Sole failure: `test/shell.d/i18n-test.sh`, because `da/menu.json` still contains `system.reboot-boot-menu`, which is absent from the English catalog.
- The same failure was reproduced on unmodified upstream at the pinned commit with the XDG overrides cleared. No fork translation fix or test suppression is included.
- The staged whitespace check reports extra blank lines at EOF in ten upstream translation/test files. These warnings are inherited from the pinned upstream tree; no unrelated whitespace cleanup is included. Local unstaged compatibility changes pass `git diff --check`.

The first test run also failed `default-apps-test.sh`, `elsewhen-migration-test.sh`, and `provision-user-test.sh`. All three failures reproduced on unmodified upstream with the inherited XDG overrides and passed after those overrides were cleared. They are environment-sensitive fixture failures, not integration regressions.

Focused checks passed for command style, the default agent launcher, runtime execution, runtime overrides, OpenShell import/catalog/native tools, task workspaces, Kimi, mise installation, and lazy-shim migration. The native-tool regression uses a fake HTTP transport and verifies Pi's actual read/write/edit/bash lifecycle and blocking hooks without model usage.

A live OpenShell model doctor check from the integration worktree also passed for `pi-codex` and `gpt-6.1-sol`. Host Pi and the existing harness both reported 1.3.0. This proves one provider/model request, not all account/model combinations or the desktop upgrade.

Local evidence:

- `/tmp/omarchy-upstream-sync-tests-clean.log`.
- `/tmp/omarchy-sync-openshell-live.log`.
- `/tmp/omarchy-sync-migrations-review.diff`.
- `/tmp/omarchy-sync-update-review.diff`.
- `/tmp/omarchy-sync-host-pending.txt`.

These temporary files are not part of the PR and may be removed by the operating system.

## Migration and package review

The migration diff contains 58 additions, 5 modifications, and 1 deletion. All 63 added or modified migration scripts pass `bash -n`. Review covered the migration bodies and update/channel changes. No new migration directly references the fork's OpenShell credentials, task workspaces, container harness definitions, or agent execution-mode state.

Important deployment effects:

- `1791382872.sh` replaces exact shipped mise wrappers with system lazy shims and removes matching user `latest` requests without pruning installs. It deliberately fails pending if `/etc/mise/conf.d/omarchy-tools.toml` is missing. Explicit version pins are retained. Pi's launch path may change after this migration.
- `1792343099.sh` and `1792343225.sh` move Node defaults and the upgrade-pruning setting back to system mise declarations. Confirm that the settings package supplies those declarations before applying them.
- `1791403252.sh` reorders pacman repositories and invokes another system package update. This is not a config-only migration.
- `1791581004.sh`, `1791621765.sh`, and `1791898365.sh` affect boot images, console/keyboard handling, or the boot menu. Keep a usable recovery entry and validate the resulting boot before declaring deployment complete.
- `1791769486.sh` removes the briefly shipped USB/Thunderbolt approval system and can rebuild boot files or change device authorization. This is a security-policy change, not a mechanical source merge.
- Input-method, browser, bar-layout, background, and theme migrations change user-facing state. Back up the existing config before a real migration run. These UI effects were not checked on the live desktop.
- OpenClaw's earlier blocking migration becomes inert. The replacement migration guards for the new seed package and leaves user-managed installations for explicit launcher handling. The integration retains the corresponding launcher exception.
- ARM-specific firmware, kernel, audio, camera, and boot migrations are guarded by platform/model checks. This host is x86; those paths require platform-specific validation rather than inference from x86 tests.
- The update flow retains its fast-forward-only dev pull, adds blob-filtered fetching, and adds platform boot-verification dispatch after package/AUR work. The generic x86 boot-verification dispatch may be a no-op; it is not a guarantee that this machine's boot images are valid.
- Channel switching adds platform-template checks. Do not change channels merely to hide a missing package prerequisite.

## Current host deployment blockers

Read-only inspection found:

- Installed Omarchy and settings packages: 4.0.4-1.
- Installed mise package: 2026.10.3-1.
- `/etc/mise/conf.d/omarchy-tools.toml`: absent.
- Upstream documents mise 2026.10.11 or newer for safe lazy-default upgrade behavior.
- Installed `omarchy-nvim`: 2026.8.13-1; the transparency migration requires newer package content when applicable.
- No companion `omarchy-pkgs` or ISO checkout was available for package/image integration validation.
- 82 migrations are pending when the integration tree is compared with this user's current markers. Some predate this sync; this is not a count of migrations that will mutate this machine.

The cached pacman metadata was also old. It is not evidence that matching packages are unavailable in current repositories. Do not install new dependencies selectively from another channel. Establish a coherent package/settings/mise version set before deployment.

## Remaining gates

1. Commit the merge resolution and command-style compatibility changes on the integration branch.
2. Submit a review PR into the fork's `quattro` branch. Include the baseline translation failure rather than describing the suite as fully green.
3. Resolve or explicitly track the upstream translation-catalog mismatch before requiring a green aggregate check.
4. Verify matching package availability, including the settings tool declarations, the supported mise version, Neovim content, and any newly required desktop packages.
5. Test package update, migrations, desktop startup, and reboot in a disposable x86 VM with a rollback point. Run graphical acceptance there; do not use the active desktop as the acceptance VM.
6. Merge into `quattro` only after review. Back up system/user state before applying the actual update, and keep the source rollback ref. Reverting Git does not undo package changes or completed migrations.
