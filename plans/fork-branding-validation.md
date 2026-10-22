# Fork branding validation

## Scope

Validated feature commit `e7df718273333413b9896d794c7900f4988a9f15` in a disposable x86_64 VM running packaged Omarchy and omarchy-settings `4.5.0rc1-1`. The source tree came from a Git archive of that exact commit, not from host configuration directories. The following documentation-only commit does not change the validated command, asset, or test code.

The test used a new QCOW2 overlay of the retained RC-upgrade guest. It used only the disposable guest's SSH identity. It did not mount host directories, forward an SSH agent, copy personal credentials, call a model provider, or rebuild an agent harness.

## Automated checks

- The 14 focused branding checks pass on the host and in the guest. They cover command routing/help, confirmation/cancellation, backups, repeat application, screensaver-only operation, exact publisher arguments, restore selection, boot-helper failure status, staged-file cleanup, invalid destinations/assets, and direct lifecycle-call guards.
- `test/cli` passes on the host and in the guest.
- `test/shell.d/bin-style-test.sh` passes on the host and in the guest.
- Bash syntax checks and `git diff --check` pass.
- The stock `logo.txt`, Plymouth/SDDM defaults, and dev link/unlink commands remain unchanged.

This is not a new full shell-suite aggregate or a full graphical acceptance-suite run.

## Real guest workflow

1. Start packaged RC in a fresh overlay.
2. Transfer the exact source revision and run `omarchy dev link` against that source tree.
3. Reboot and confirm that the session uses the linked source.
4. Run the real `omarchy branding restore` command to establish a graphical stock control. Answer its actual Gum confirmation through a pseudoterminal. Allow the existing privileged publisher to rebuild the unified kernel image (UKI).
5. Reboot and inspect the stock Plymouth splash and SDDM login screen.
6. Run the real `omarchy branding apply` command, confirm it, and complete its UKI rebuild.
7. Compare the installed Plymouth and SDDM logos with the fork PNG, and compare the installed screensaver text with the fork text. All comparisons match.
8. Reboot and inspect the fork Plymouth splash and SDDM login screen. Both show the subtitle without clipping or overlap. Authenticate to the desktop with the disposable guest account.
9. Run a screensaver-only restore/apply round trip. The UKI, Plymouth logo, and SDDM logo hashes remain unchanged. Inspect the actual animated screensaver with its subtitle.
10. Run the real full restore command and complete its UKI rebuild. Installed boot/login logos and screensaver text match the stock source files.
11. Reboot and inspect the stock splash and login screen again. Authenticate and verify shell responsiveness, one shell instance, no Hyprland configuration errors, no failed system/user units, and no current-boot coredumps.
12. Run `omarchy dev unlink`, reboot, and verify a healthy packaged session at `/usr/share/omarchy`, with the stock branding still present. The packaged branding command group no longer lists the fork-only apply/restore commands.
13. Shut down the guest and verify that no VM process remains.

The fork logo hash was `ee6b5dcba5a56190d038a4d4f2b96509e899001db495b9f60af372daf9f78d0e`. The restored stock logo hash was `ba8f1547a02ab5db64fe3923d0b834a220e2c3798c1674374a0eb92a18dfddfb`. Both installed logo copies matched at each step.

## Guest fixture adjustments

The first reused-base boot displayed console output instead of a graphical splash. The accepted graphical runs used guest-only display configuration: an explicit Plymouth hook and virtio GPU module in the main mkinitcpio configuration, `plymouth.ignore-serial-consoles` for the QEMU serial console, and a 12-second delay before Plymouth quits so frames can be captured. SDDM autologin was disabled in the guest so its actual login screen could be inspected. The stock-control rebuild preceded the accepted fork/restore comparisons. These adjustments did not modify production source or host boot configuration.

UKI checksum reads used guest sudo because `/boot` is not readable by the guest user. Hyprland client checks used display variables from the guest's systemd user manager rather than assuming an SSH login inherited the graphical session. The existing screensaver launcher's event stream kept the initial SSH output open; QMP captures and dismissal worked. These observer corrections did not require a feature-code change.

## Resource and deployment limits

The single VM ran with `TasksMax=512`, `MemoryMax=6G`, `CPUQuota=400%`, and `Nice=5`. Its host cgroup peaked at about 5.75 GiB and 73 tasks. Memory-limit, OOM-kill, and task-limit event counters were zero. The VM session exited successfully. Host Btrfs device counters were unchanged across the validation interval; that does not prove the earlier filesystem or memory concern resolved.

The host boot image was not rebuilt and host boot/login branding was not installed. Host filesystem diagnosis and an offline memory test remain separate work. ARM boot chains, encrypted guest unlock, multi-monitor layouts, and physical hardware were not tested by this run.

## Evidence

Private logs and full QMP frame sequences are retained under `triage-evidence/fork-branding-validation/` in the local VM review workspace. They include stock controls, fork boot/login frames, screensaver frames, restored/unlinked boot frames, source/asset checks, CLI output, and resource counters. Selected full-frame VM boot and login captures are published in `manual/images/branding-fork-boot.webp` and `manual/images/branding-fork-login.webp`.
