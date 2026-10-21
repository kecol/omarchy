# Upstream quattro integration review: 2026-10-20

## Decision

The source merge is ready for review in PR #7, not for automatic merge or host deployment. The packaged stable-to-RC VM upgrade passed. The corrected full graphical suite passed all 10 files twice in separate fresh overlays, without temporary shell logging. After correcting two independently reproduced test-helper races, the final full non-graphical rerun has only the known upstream i18n completeness failure out of 478 shell files; CLI passes. Earlier intermittent GTK-startup, monitor-placement, and synthetic-typing failures remain recorded without claims that their causes are fixed. Review these limitations and the explicit VM prerequisites before merging. Do not activate this checkout on the current desktop yet. Matching host packages and completed acceptance validation remain deployment gates. Passing source tests does not prove that a package update, migration run, or reboot will succeed.

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

## Host deployment blockers at initial review

Read-only inspection found:

- Installed Omarchy and settings packages: 4.0.4-1.
- Installed mise package: 2026.10.3-1.
- `/etc/mise/conf.d/omarchy-tools.toml`: absent.
- Upstream documents mise 2026.10.11 or newer for safe lazy-default upgrade behavior.
- Installed `omarchy-nvim`: 2026.8.13-1; the transparency migration requires newer package content when applicable.
- No companion `omarchy-pkgs` or ISO checkout was available for package/image integration validation.
- 82 migrations are pending when the integration tree is compared with this user's current markers. Some predate this sync; this is not a count of migrations that will mutate this machine.

The cached pacman metadata was also old. It is not evidence that matching packages are unavailable in current repositories. Do not install new dependencies selectively from another channel. Establish a coherent package/settings/mise version set before deployment.

## VM follow-up and fixture corrections

Draft PR: <https://github.com/kecol/omarchy/pull/7>.

The official stable 4.0.6 VM image passed its SHA-256 check before boot. Tests used separate disk overlays without host-home mounts, account credentials, or SSH agent forwarding. A newly generated VM-only SSH identity controls the guest; its private key remains on the host with mode 0600.

The packaged stable 4.0.6 to RC 4.5.0rc1 upgrade passed all 13 checks. It ran 84 migrations, skipped none, rebooted without intervention, and reached a healthy desktop with no failed units or undefined shell theme bindings. Evidence is in `~/VMs/omarchy-sync-review/rc-upgrade-evidence/`.

The corrected full VM CLI/shell rerun has only the known upstream i18n completeness failure out of 477 files. The incoming workflow's structural i18n mode and extraction scan passed separately. Changes in `2bc25c8bd` resolve the installed Pi executable before installing fake transport fixtures and mock the Podman socket readiness check, including a negative unavailable-socket assertion. No provider credentials are needed for these tests. The security and T3 tests passed three repeated standalone runs against both upstream and fork source; their earlier aggregate failures were not reproduced, so no production security fix is claimed.

Initial graphical failures included VM display power-off during the long SSH-driven run. Later comparisons disabled guest idle and used an independent overlay per case. Two new default packages, `fcitx5-table-extra` and `superwhisper-bin`, were installed explicitly inside the test guest before the comparison. The original stable-to-RC upgrade did not install them; its success is not a claim that it supplies every new-install default.

The SSH acceptance test also exposed an existing setup edge case: the VM bootstrap's authorized_keys file had no final newline, so the setup command appended its test key onto the existing line. This reproduced on packaged RC. Normalizing the test prerequisite made the acceptance check pass, but no product fix for no-final-newline input is claimed.

Graphical coverage (see complete-suite evidence below):

| Check | Packaged RC | Fork |
| --- | --- | --- |
| SSH/security acceptance with normalized prerequisite | Pass | Pass |
| Core system and package checks with explicit prerequisites | Pass | Pass |
| Weather/panels | Pass | Pass |
| Overlay-monitor geometry | Pass | Pass in corrected complete suite; earlier intermittent placement failure retained for review |
| Menu and bar-position navigation | Pass | Pass |
| Shell surfaces and app launch through the dock grid | Pass | Pass |
| Full input-method sequence | Pass | Three later fresh-overlay passes; earlier GTK startup failure not reproduced |

The two shared menu/app-launch failures were stale test expectations. Changes in `2381f3dd6` derive the bar-position route from the product's own menu declarations instead of fixed keyboard row counts, and assert on `omarchy-dock-apps` after the Apps action hands off to the dock. Both corrected tests passed on packaged RC and fork VM overlays. Bar-position screenshots were inspected on both products.

A host process-exhaustion interruption invalidated part of the first comparison. Subsequent jobs ran with 512 host tasks maximum, 6 GiB host memory maximum, a 400% CPU quota, and one 4 GiB VM at a time. In that bounded rerun, fork input testing passed Japanese, Korean, and Pinyin terminal/GTK/Qt/browser composition and Chewing terminal composition, then failed to open the Chewing GTK fixture. This was a test/application-startup failure, not a credential failure. No relevant error was found in the retained previous-boot journal query; the fixture discarded application startup output, so that query did not establish a cause. The subsequent instrumented reruns below did not reproduce it.

The input-method follow-up adds per-engine/toolkit application startup logs and captures clients, failed user units, the user journal, process metadata, and memory state before failure cleanup. Composition, window-readiness, and notification assertions are unchanged. The instrumented full sequence passed three consecutive times in separate fresh fork overlays, including Chewing GTK and Cangjie terminal/GTK/Qt/browser checks. All three runs recorded zero host memory-cap, OOM, and task-limit events. Startup logs showed nonfatal Mesa EGL warnings. No fatal startup error or confirmed root cause for the earlier failure was established. Successful Chewing GTK and Cangjie browser screenshots were inspected. The source production code did not change during these reruns.

The diagnostic evidence is in `input-startup-diagnostics/`, `input-startup-diagnostics-02/`, and `input-startup-diagnostics-03/` beneath the comparison evidence directory. Three passing isolated reruns are not proof that the earlier intermittent startup failure is fixed. The complete graphical aggregate subsequently passed after the OCR/session-preflight corrections below; those corrections do not establish a cause for the earlier GTK startup failure.

Comparison evidence is under `~/VMs/omarchy-sync-review/triage-evidence/`. The `menu-route-compat/results.csv` and `updated-ui-tests/results.csv` record the successful corrected menu and app-grid comparisons. `final-ui-checks/input-methods.log` preserves the earlier GTK-window failure, which later runs did not reproduce. These directories contain individual reruns; the later complete-suite result and its distinct evidence directory are recorded below.

The host was returned to packaged Omarchy 4.0.6 after the old dev checkout showed Qt 6.12 palette errors. The packaged desktop renders normally. Keep it unlinked during remaining validation. Host Btrfs corruption counters stayed at the historical value 10 during the later VM runs; this does not establish that the original storage problem is repaired.

## Complete graphical aggregate and focus investigation

At `92abe8ba8`, the complete graphical suite ran in a fresh fork overlay with guest idle disabled and the documented package and SSH prerequisites checked. It exited 1 after 229 seconds. Only the menu bar-submenu visibility check and the second overlay-monitor placement check failed. The full input-method sequence passed. Evidence is in `triage-evidence/full-corrected-acceptance/`.

The failed menu screenshot visibly contains Position Bar. OCR of that saved image splits Position and Bar across lines, which the helper's line-oriented literal match rejects. Commit `19411dd65` normalizes OCR whitespace without fuzzy matching or skipping words. Its mocked regression rejects absent, merged, and nonadjacent words as well as capture/OCR errors. The corrected menu test also passed inside a fresh fork VM.

For monitor diagnosis, temporary focus/screen-selection logging was added only inside a disposable VM, not to production source in this PR. Four consecutive full overlay-monitor tests passed. Attempt five passed placement but failed later when `wtype "keybindings"` arrived as `keybiindngs`; the failure screenshot shows that exact misspelled query and no matches. This is a different failure from the original wrong-output placement. Focus logs show the intended output was selected throughout these five attempts. Neither an original-placement root cause nor a production fix is established. Evidence is in `triage-evidence/menu-monitor-diagnostics/`.

The isolated diagnostic run recorded zero memory-cap, OOM, and task-limit events, with host Btrfs counters unchanged. The later full-sequence run under `triage-evidence/full-focus-diagnostics/` exited 1 after 342 seconds, with menu and notification visibility failures. That diagnostic run is invalid for judging normal shell behavior: its screenshots show two bars, and its journal records simultaneous shell PIDs 854 and 942, socket replacement, and competing notification-server registrations. The local runner called restart before checking that initial session startup had settled. No production restart fix is claimed.

## Corrected single-shell aggregate

The local runner now avoids restarting during guest startup. It waits for exactly one Quickshell instance and a responsive notification service. Before testing, it checks that the notification D-Bus owner is that same shell PID. It records instance and ownership data again after the suite. No QML instrumentation is applied.

The first such fresh-overlay run passed 9 of 10 files in 280 seconds, including notifications, input methods, and monitor recovery. Only the menu OCR check failed. The helper now preserves its actual scaled capture, raw OCR output, errors, and match status. That evidence shows sparse-layout OCR reading the visible word Bar as CED. Normalizing whitespace alone cannot repair this segmentation error. Evidence is in `triage-evidence/single-shell-ocr-capture/`.

Commit `4b4d20fb9` retries sparse-layout misses using block-layout OCR on the same captured pixels. Both modes still require the literal expected phrase, with only whitespace and case normalization. No fuzzy match or weakened menu assertion is used. Mocked regression tests cover the fallback, absent/merged/nonadjacent words, capture/OCR errors, and retained diagnostics. Replaying the actual failed VM frame through the real OCR helper recovered Position Bar with mode 6 and still rejected Position Foo. That replay used a mock capture command, not the host desktop.

The complete graphical suite at `4b4d20fb9` then passed all 10 files in 262 seconds in another fresh fork overlay. The test runner and evidence collector both exited 0. All package, SSH, and stay-awake prerequisites remained explicit. Preflight and postflight each show one shell, PID 844, which also owns the notification service. The bar-position, notification, and shorter-screen recovery screenshots were inspected. The bar-position OCR status confirms successful mode-6 matching. No temporary QML focus logging or production source changes were used.

Final evidence is in `triage-evidence/single-shell-ocr-capture-02/`: `acceptance.log`, preflight/postflight records, raw OCR files and screenshots under `omarchy-single-shell-ocr/`, and host resource/storage snapshots. Memory-cap, OOM, and task-limit events were zero. Host storage counters remained corruption 10 and all other error counters zero. All VMs were stopped after collection.

This first clean complete graphical pass did not prove that all earlier intermittent failures were eliminated. The subsequent full non-graphical rerun and second graphical pass are documented below. The exhaustive upstream i18n failure, missing-default-package upgrade distinction, and SSH no-final-newline edge case remain documented separately.

## Final review validation and deterministic test observers

A fresh-overlay run pinned to `70f3da454` repeated both suites. CLI passed. The shell suite initially reported three failures out of 478 files: known i18n drift, a privileged-heredoc fixture assertion, and a Windows-VM FD-count assertion. The complete graphical suite then passed all 10 files in 255 seconds, including input methods, menu/bar navigation, monitor recovery, and notifications. Session preflight and postflight passed with a single shell owning notifications. Recovery and notification screenshots were inspected. This provides a second complete graphical pass, after the earlier 262-second pass.

Both newly failing security tests and the Windows command under test match pinned upstream. Their original standalone tests subsequently passed three times each. Independent no-application-work controls identified the observer races rather than assuming that rerun success proves correctness:

- The parent-process FD counter returned different totals twice in 500 unchanged-state comparisons. It observes the parent's transient command-substitution pipe ends. A builtin snapshot of the counting subshell's inherited FDs had zero mismatches and measured a deliberate descriptor open/close as 4, 5, 4. Commit `ca1ad61a3` uses that observer and adds an open/close calibration. Existing exact-count, ancestry, mount-safety, and race assertions remain intact.
- The actual heredoc finding text contains the expected substring, but `grep -q` can exit before its producer finishes. In 1,000 controls, the producer once exited 141 while grep exited 0; consuming grep had zero failures. Commit `efcfcf9ff` consumes the complete stream under pipefail and retains the literal finding assertion. The privileged-write scanner and production commands are unchanged.

Both corrected tests passed three consecutive VM runs each. The complete CLI/shell suite then ran again in a separate fresh overlay with those frozen candidate files. CLI passed. Only `test/shell.d/i18n-test.sh` failed among 478 shell files, with skipped checks in 43 files. The aggregate exit remains 1 and is not relabeled green. Its Danish catalog mismatch is the same failure already reproduced on unchanged upstream. Session postflight and the evidence collector exited 0.

The frozen files match the committed fixture fixes byte-for-byte. The second graphical run validated the same production and acceptance-test code: only these two non-graphical fixture files and the host planning document changed afterward. No production behavior or graphical assertions were changed to obtain the final results.

Evidence directories under `~/VMs/omarchy-sync-review/triage-evidence/`:

- `final-sync-validation/`: pinned source identity, initial complete CLI/shell output, second full graphical pass, screenshots, session health, and resource/storage snapshots.
- `final-fixture-controls/`: no-application-work controls and repeated original security-test results.
- `fixed-unit-final-validation/`: frozen candidate files and hashes, exact patch, six corrected focused-test passes, final full CLI/shell output, and postflight results.

All final validation jobs retained the existing task, memory, CPU, and one-VM limits. Memory-cap, OOM, and task-limit events stayed zero. Host storage counters remained corruption 10 and all other error counters zero. All VMs were stopped after collection. These are manual VM results, not a claim of green GitHub CI or complete hardware coverage.

## Final minor review finding

The final review found that the native-tool fixture checked for Pi on PATH before honoring `OMARCHY_TEST_PI_BINARY`. The guard now checks Python independently, resolves the explicit binary first, and handles a missing PATH fallback without exiting under errexit. Executable and lazy-shim checks remain intact.

A new dependency-guard regression covers an explicit binary outside PATH, absent Pi, absent Python, ordinary PATH fallback, an invalid explicit override, and rejected lazy shims. It fails against the previous guard and passes with the correction. The real offline native-tool fixture passes both normally and with a real explicit Pi binary while PATH contains no Pi or mise. Both runs exercise native read/write/edit/bash execution and the blocking hook using fake model transport, scratch state, and no personal credentials or model requests.

The earlier full non-graphical result covers 478 files. The newly added guard regression and changed native-tool fixture were tested directly; no new full 479-file aggregate is claimed. Production and graphical acceptance code did not change.

## Review closure and deployment gates

1. PR #7 may leave draft for human review. The remaining reproducible test failure is pinned-upstream i18n completeness drift; the earlier intermittent failures remain documented limitations rather than claimed fixes.
2. Review the fixture changes, repeated graphical evidence, skipped checks, explicit new-package prerequisites, and SSH final-newline edge case before merging. Do not merge automatically.
3. Following separate user approval, the host completed the packaged RC 4.5.0rc1 transition and a successful fresh boot. Root snapshot #14 and a root-private boot archive were prepared before the package transition. All 52 pending migration markers are complete. Fresh-boot checks show matching kernel/headers, one responsive packaged shell, no Hyprland configuration errors, no failed system/user units, and unchanged storage counters. The user confirms normal desktop operation. The host remains unlinked; any fork source activation still requires separate approval. See `plans/host-rc-transition.md`.

## Initial gates (superseded by the follow-up above)

1. Commit the merge resolution and command-style compatibility changes on the integration branch.
2. Submit a review PR into the fork's `quattro` branch. Include the baseline translation failure rather than describing the suite as fully green.
3. Resolve or explicitly track the upstream translation-catalog mismatch before requiring a green aggregate check.
4. Verify matching package availability, including the settings tool declarations, the supported mise version, Neovim content, and any newly required desktop packages.
5. Test package update, migrations, desktop startup, and reboot in a disposable x86 VM with a rollback point. Run graphical acceptance there; do not use the active desktop as the acceptance VM.
6. Merge into `quattro` only after review. Back up system/user state before applying the actual update, and keep the source rollback ref. Reverting Git does not undo package changes or completed migrations.
