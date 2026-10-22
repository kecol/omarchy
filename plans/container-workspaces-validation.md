# Container workspace validation

## Result and scope

The unauthenticated two-workspace workflow passed in one disposable x86 VM. This run built the dedicated image, exercised real SSH connections, opened two actual VS Code windows, and verified that Codex ran remotely in each workspace. The VM is stopped. The session runner returned 0.

The run found and corrected a client-storage isolation gap. VS Code 1.142 uses `~/.vscode-shared/sharedStorage/state.vscdb` by default even when callers supply different `--user-data-dir` values. The launcher now supplies separate shared-storage and agent-data paths for each workspace. It does not copy a host profile or global shared store into those paths.

The run also found that the VS Code CLI could return 0 when its child GUI failed to initialize without a display. The launcher now rejects a headless `workspace code` invocation before starting a container or invoking VS Code. Headless callers can still use `workspace start` and SSH.

Authentication, live model responses, and account-scoped cloud history were not tested. These results do not establish that two logins to the same OpenAI account have separate server-side account state.

## Tested source and software

- Base implementation: `0356479b0b2384534e24b0a7b784dcd58a15a57e`.
- The image used the unchanged `containers/workspace/` build context from that commit.
- The final manager and regression fixture include the client-store overrides and headless preflight described above. Their host and guest SHA-256 values matched:
  - `default/workspaces/manager.py`: `766eac51efbff33b9a88885e0794dfdf66137d4fc59f0906c0254b3bfdf41af3`.
  - `test/shell.d/fixtures/workspaces/test_manager.py`: `816b57ca22fe4eeba186a819c21fb0b78c6d3aa36ee56fb7d2b135adc4c50e1f`.
- Podman: `6.1.4-1`, rootless, cgroup v2.
- Pasta package: `2026_10_02.cba3570-1`.
- VS Code: `1.142.0-1`.
- Remote SSH extension: `0.128.0`.
- Codex extension: `26.1007.21434`, Linux x64. Its audio dependency had the same version.
- Built image ID: `132240090422455ed6c2888c1d71b3d052216dc9469c52816ff2b7608e541563`.

The build kept registry TLS verification and package verification enabled. VS Code reported successful extension signature verification. The run did not rebuild or modify the Pi harness.

## Isolation and resource boundary

A new QCOW2 overlay used the retained packaged-RC test image. It had no host filesystem shares, home/auth mounts, SSH-agent forwarding, desktop socket forwarding, or host container-engine socket. Source arrived as a Git archive and two explicit source-file updates. Test repositories, SSH keys, and state markers were synthetic.

The VM had four virtual CPUs and 4 GiB guest RAM. Its host systemd unit enforced `TasksMax=512`, `MemoryMax=6G`, `CPUQuota=400%`, and `Nice=5`. There was one running VM.

The host unit recorded a memory peak of 6,443,655,168 bytes, approximately 6.00 GiB, and a task peak of 73. The memory controller recorded 1,429 `max` events and 53 socket-throttling events. These indicate that the limit was exercised; do not describe this run as free of memory-pressure events. It recorded no OOM or OOM-kill events. The process controller recorded no limit events.

The host Btrfs corruption counter remained 11. The other device-error counters remained zero. The pre-existing checksum concern is not repaired or explained by this validation.

## Completed checks

1. Install the required signed packages only inside the disposable guest.
2. Run the original 17 regressions and build the dedicated Node 24/Debian workspace image.
3. Create two separate Git projects and default-clone workspaces, initially named `project-a` and `project-b`.
4. Verify that ignored/untracked fixture files do not enter the clones, no source remote remains, and container edits do not change the canonical source repositories.
5. Start both containers through the public commands and pass `workspace doctor` for both.
6. Verify different workspace IDs, client keys, pinned host keys, home-volume names, and loopback SSH endpoints.
7. Verify separate `.codex` markers, container-local `HOME` and `CODEX_HOME`, and absence of guest-host home directories and engine sockets inside the containers.
8. Stop and restart each workspace. Verify that its repository changes, state marker, and host-key pin survive.
9. Replace a public host-key pin temporarily. Verify that startup refuses it instead of overwriting the pin. Restore the original public pin.
10. Increase a container's process limit temporarily. Verify that `doctor` rejects the drift. Restore the configured limit and pass `doctor` again.
11. Open two real VS Code windows. Verify Codex's remote location through **Developer: Show Running Extensions** and verify its native app-server process inside each container.
12. Identify the default global VS Code shared database and add explicit private shared/agent-directory overrides.
13. Create fresh post-fix workspaces, `project-c` and `project-d`, instead of treating the older client profiles as clean. Repeat the runtime checks.
14. Verify separate private client databases with different inodes. Verify the intended private paths in the client process titles and the actual private database paths in VS Code's startup logs. The fresh profiles initialized with three fallback items, not the older profiles' accumulated shared state.
15. Verify that the legacy global shared database's recorded inode, size, and modification time remain unchanged during the fresh-profile checks. This is a file-metadata check, not a complete filesystem-access trace.
16. Verify that Settings Sync reports disabled for each client and that no OpenAI extension is installed in either local extension directory.
17. Verify both post-fix Codex extension hosts visually, their separate remote app-server processes, their container-local home variables, and their separate remote workspace-storage URIs.
18. Verify remote terminals with `/workspace`, `/home/workspace`, and `/home/workspace/.codex`. The initial phase captured these values for both original workspaces.
19. Close both post-fix windows and confirm the containers remain running. Reopen the same workspaces. Verify that private client database inodes and remote state markers persist, and that both Codex app servers run remotely again.
20. Run the final 19 regressions in both the host source checkout and guest source copy. Pass CLI routing, style, and whitespace checks on the host checkout.
21. Reject a real headless `workspace code` call with status 1 and the display-preflight message. Repeat a successful two-window launch with the guest desktop environment.
22. Collect final runtime checks and source hashes, stop the VM, and verify runner exit 0 and unchanged host storage counters.

The last guest postflight reported no failed user units. Both final `doctor` checks and the final editor-isolation verifier passed.

## Fixture diagnostics and limits

- A pre-build probe used an incorrect Go-template field spelling. The fixture was changed to read Podman's JSON fields. This did not require a product change.
- An early transient service ended its whole test process group when the script exited. GUI fixture services were retained until cleanup. Separate normal SSH command invocations also verified that detached containers and desktop-environment GUI launches survived their launcher commands.
- Two early GUI launches from a shell without `DISPLAY` or `WAYLAND_DISPLAY` produced guest-only SIGTRAP dumps. A separate no-display control reproduced SIGTRAP and the explicit `Missing X server or $DISPLAY` / platform-initialization error. Its core size was limited to zero, although systemd retained the event record. The final headless preflight avoids invoking this failing GUI path. No cores were extracted or uploaded. Do not report a coredump-free guest boot or attribute these records to the host's older memory-corruption investigation.
- Native QMP keyboard input replaced unreliable virtual-keyboard command-palette entry. Palette selection was inspected before commands were accepted.
- A fuzzy terminal search initially selected VS Code's explicit **Local** terminal action. No project scripts or untrusted commands were run there. The observer then selected the remote terminal action and checked the remote prompt and environment. The manual now states which action to use.
- VS Code serializes the `+` in remote workspace-storage URIs as `%2B`. The verifier decodes the URI and compares its complete expected authority and folder.
- The virtual output was increased from 1280×800 to 1920×1080 so the two third-party application windows were readable. Maximized views were also inspected.
- No personal credentials were copied, no account login was completed, and no model prompt was submitted. This run does not cover authenticated Codex refresh behavior, browser callbacks, live tool calls from a model, cloud-history visibility, ARM, encrypted boot, or a host deployment.
- Real graphical acceptance used default clone mode. Direct-mount refusal and state separation have regression coverage, but a separate real direct-mount workflow was not part of this run.

## Evidence

Private local evidence lives under `/home/kecol/VMs/omarchy-sync-review/triage-evidence/container-workspaces-01/`. It includes the source archive, fixture scripts, whitelisted guest receipts, image/build records, runtime checks, editor and private-client receipts, final source hashes, resource-controller records, host storage comparisons, and session exit status.

Full-frame QMP captures live under `/home/kecol/VMs/omarchy-sync-review/triage/container-workspaces-01/`. Relevant post-fix views include `fixed-running-c.png`, `fixed-running-d.png`, `fixed-two-codex-loaded.png`, and `final-reopened.png`. These were inspected. The latter two show two independent remote windows with unauthenticated Codex panels.

The guest overlay retains systemd-managed fixture crash records privately. It is stopped and has no personal provider authentication. Do not publish disk images, home volumes, private SSH keys, or extracted process memory as test evidence.
