# Host RC transition plan

## Scope and approval

This document records the original transition plan. The packaged RC transition was subsequently completed with separate user approval, outside PR #7 validation. Fresh-boot checks and user-confirmed desktop operation passed; the host now runs packaged Omarchy/settings 4.5.0rc1-1 at `/usr/share/omarchy`. Root snapshot #14 and a root-private boot archive were prepared beforehand. Fork source activation has not occurred and still requires separate approval. Marking or merging the PR does not itself authorize deployment.

Use the supported Omarchy update and dev-link workflows during a separately approved maintenance window. Keep package signature and certificate verification enabled.

## Observed host baseline before transition

Read-only inspection during the final VM validation found:

- Active source: `/usr/share/omarchy`; the host remains unlinked.
- `omarchy` and `omarchy-settings`: `4.0.6-1`.
- `mise-bin`: `2026.10.15-1`.
- `omarchy-nvim`: `2026.9.21-5`.
- `linux-omarchy` package: `7.2.8-9`.
- `qt6-base`: `6.12.0-3`.
- `/etc/mise/conf.d/omarchy-tools.toml`: absent.
- Historical Btrfs corruption count: 10; other device error counters: zero.

Refresh this baseline before any real transition. Stable counters do not prove that the historical storage problem is repaired. Do not run filesystem repair as part of this upgrade plan.

## Gates before scheduling

1. Review and merge PR #7 separately. Preserve the published fork history and the backup ref. Record the selected deployment commit; do not deploy a moving branch without recording its identity.
2. Review the final VM evidence and its limitations in `plans/upstream-sync-20261020.md`: upstream i18n drift, earlier intermittent failures, the SSH final-newline edge case, and explicitly installed VM default packages.
3. Check current signed repository metadata for a coherent RC package set. The tested VM used Omarchy/settings `4.5.0rc1-1` and mise `2026.10.15-1`; those observations are not proof of current availability or a recommendation to pin only those packages.
4. Confirm that the chosen settings package supplies the system mise tool declarations before the dependent migration runs. Keep the matching Neovim content and kernel/header packages coherent. Do not install selected RC packages into the stable configuration as a workaround.
5. Decide explicitly whether this host should receive new default packages such as `fcitx5-table-extra` and `superwhisper-bin`. Their manual installation in the VM does not prove that the upgrade installs every new-install default.

## Recovery preparation

Before changing packages, verify available storage space and a supported rollback procedure. Create and verify an appropriate system snapshot and any needed user-configuration/data backup. Do not assume that a root snapshot includes `/home` or the EFI boot partition. Keep personal credentials private; do not include them in PR evidence or VM artifacts.

Record the current package/channel configuration, migration markers, source refs, and usable boot entries. Keep a known-good boot path and external recovery media available. Confirm how to restore the system and user state if the normal desktop cannot start.

Pause if new storage errors appear. Do not disable package verification, force an unsafe partial upgrade, or use filesystem repair to get past an upgrade failure.

## Proposed maintenance sequence

1. Recheck the baseline, package availability, recovery artifacts, and explicit user approval.
2. Perform the supported coherent RC channel/package transition. Follow its required migration and reboot sequence. Do not dev-link the old fork checkout to compensate for a package mismatch; it previously failed against Qt 6.12.
3. Verify the packaged RC desktop before activating fork source: booted kernel and matching headers, boot-entry usability, system/user unit health, theme rendering, terminal/browser launch, and the required mise declarations. Do not run the graphical acceptance suite on the live desktop.
4. If the packaged RC desktop is healthy, obtain separate approval to dev-link the recorded, reviewed fork commit through the supported workflow. Reboot when that workflow requires it, then inspect the actual desktop and service health again.
5. Check agent runtime selection and local doctor output. Any live provider request or harness rebuild needs its own approval. Keep Pi as the refresh-credential owner; do not mount host auth directories or copy personal credentials into test guests or containers.

## Rollback boundaries

Stopping a dev link only changes source selection; it does not undo packages or migrations. A Git revert alone is not a system rollback. Do not return to the old fork checkout against the newer Qt packages.

Use the prepared coherent system/boot recovery and needed user-state restoration if the package transition fails. Do not attempt an improvised per-package downgrade. Recheck service, desktop, and boot health after recovery. The working packaged desktop is the fallback source configuration, not an excuse to combine incompatible package versions.
