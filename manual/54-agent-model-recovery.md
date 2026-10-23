# Recover an unavailable Pi model

Pi versions, container images, and model availability have separate lifecycles. Updating an image does not necessarily replace a saved model default. A resumed session can also restore an older model selection.

Omarchy adds a model guard to Pi launched through `omarchy agent`. It checks saved defaults and resumed model selections against Pi's local catalog. If Pi reports a model-specific rejection, the guard offers recovery after the failed run stops. It does not assume that a model is retired globally: availability can depend on the provider, account, endpoint, or subscription.

## Choose a replacement

The recovery menu offers:

- **Choose a model for this session**
- **Choose and save a new default**
- **Refresh model catalog**
- **Exit Pi**

The session option prepares `/model` in an empty editor. Press Enter to open Pi's native picker, then Enter on a model to select it for this session.

The default option prepares `/model-recovery save`. Press Enter to open Pi's native picker in **Save default** mode. Press Enter on a model to save it for future launches; Ctrl+S also saves it. There is no additional save gesture. Omarchy uses Pi's settings API, waits for the write to finish, and reloads Pi's in-memory settings. It does not send or replay a prompt.

If the editor contains a draft, Omarchy leaves it unchanged and tells you which command to open. Pi owns model selection, provider authentication, and settings file handling. The guard does not implement its own model list or copy host credentials into a container.

You can open the recovery menu at any time:

```text
/model-recovery
```

You can also open Pi's picker directly with `/model`.

Project settings can override a saved global default. Review project model settings if the same warning returns after saving a default.

## Refresh the catalog

Select **Refresh model catalog** to ask the running Pi instance to refresh its model metadata. This does not rebuild an image or send a test prompt. The refresh has a 15-second cancellation deadline. If it fails, cached models remain available. Offline mode does not attempt a network refresh.

A catalog entry does not guarantee access for your account. If a replacement needs newer provider support, update the Pi image separately.

## Error behavior

The guard distinguishes explicit model rejection from invalid authentication, rate limits, temporary outages, and ambiguous HTTP 404 errors. Authentication problems need `/login` or a credential correction; they do not prove model retirement.

The guard never silently selects another model or provider, and it never resends the failed prompt. Choose a model and submit the next input yourself. Blocked text is restored to an empty editor where possible; reattach images before submitting again.

For managed tasks, one-shot prompts, and other noninteractive runs, an unavailable saved selection fails with an actionable error instead of opening a menu. Pin an available provider and model for automation. Explicit CLI model choices, including custom IDs outside the catalog, retain precedence. A later provider rejection still reports failure.

While a selection is blocked, the guard also prevents idle cache warming. This guard is not a security boundary against other trusted extensions that make their own model calls.

## Container behavior

Before **Run**, the image menu displays the saved default from the container's persistent Pi home. This is a bounded, read-only metadata check, not a check of account access. Project settings and resumed sessions can override this saved default; Pi validates the effective selection after launch.

The guard works with Pi 1.3 and newer, including existing images. Omarchy exposes one public extension file read-only inside the container. It does not expose the Omarchy source directory, host Pi home, host authentication, or engine sockets. Agent homes and authentication remain private to their existing environments.

The feature applies to new `omarchy agent` launches. Existing running sessions and independent VS Code workspaces are not changed. No desktop reboot or image rebuild is required. Direct Pi and the separate OpenShell launcher are not automatically modified.
