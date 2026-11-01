# Paired OWE package

This package is the OWE component of the transient background handoff fix. Deploy it with `shell setBackgroundSuspended`. The old daemon can still change persistent preferences, even with the new shell.

## Inputs and behavior

- Upstream OWE0.2.13 is commit `56e7659fb46fbd48ec3e1c8b187d0186d97da866`. The source archive must match the SHA256 in `PKGBUILD`. No upstream source signature is declared by the pinned recipe.
- `0001-runtime-background-handoff.patch` removes the persistent enable fallback and requires an exact `ok` or `disabled` reply with process exit0.
- After the existing2-second handoff grace, the daemon stops and reaps its owned renderer. A parked renderer retains its last Wayland buffer and can expose stale video when the shell background is disabled. Normal still handoffs therefore no longer keep that renderer warm. Explicit intro preparation remains supported.
- Keep the upstream0.2.13 startup, held-frame, transition and pending-handoff guards. A pending video handoff must not be stopped by an earlier still timer.
- The native daemon tests require renderer exit after normal and intro handoffs. Run the full native x86_64 test suite. Do not skip failing tests or disable dependency, checksum, signature, sandbox or hook checks.

## Package boundary

The real package name is `owe-quattro`. It provides `owe=0.2.13` and conflicts with `owe`. This prevents normal repository updates from silently replacing the paired fix with an unpatched `owe` package. Do not fabricate package database records or versions. Review the native conflict transaction before installation.

The package retains the normal restart helper and Upgrade hook. The hook also targets `owe-quattro`. Native shared-library dependencies record the linked SONAME requirements. An incompatible library update must stop until this package is rebuilt and qualified.

Build with native `makepkg` in an isolated environment. Use one Ninja worker and one LTO worker; retain the other native security and build options. The recipe disables source fallback downloads, not the package manager sandbox. Do not build in the active desktop checkout or automatically install the result.

The qualified x86_64 package SHA256 is `a756f44d192d19c49c58162106c5ee9c4975e3be1bc5eba05f0046e99f4684f9`. The local build is unsigned. This checksum and the source review are not an upstream package signature. Host signature-policy and maintenance approval remain separate requirements.

Native validation used synthetic guest data. It covered exact preference preservation, enabled and disabled backgrounds, both real daemon handoff directions, visible video, renderer exit, correct still or blank output, and the original0.2.13 persistent-preference-loss negative control. It does not qualify physical GPU, audio, recording or all codecs. Keep the experimental capture work outside this release.

## Reinstall recovery

The qualified integration is published on branch `release/upstream-bc220e702-owe013`, not automatically activated by cloning the default branch. Check out that branch explicitly. A source clone and dev-link alone do not install the paired OWE fix: resolve the build dependencies through the normal coherent package workflow, build this checksum-pinned native package with all tests enabled, and review/install it before activating the shell. Do not disable guards or copy an evidence ELF into `/usr/bin`. Reinstall/Git does not recover unpushed work, personal files, workspace data, credentials or sessions.

## Installation order

Before an approved maintenance operation, verify recovery, package/service markers, the coherent transaction and the exact package/source manifest. Stop the old OWE service before changing the paired components. Keep native hooks enabled. Activate the paired shell and daemon only when the session is unlocked. Never bypass the locked-session restart refusal. Do not install this package, restart the desktop or reboot merely by following a source-review reference.
