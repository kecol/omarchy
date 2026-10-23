import type { ExtensionAPI, ExtensionContext, ExtensionCommandContext } from "@earendil-works/pi-coding-agent";

type Reference = { provider: string; id: string };
type Issue = Reference & { reason: "catalog" | "authentication" | "rejected" };

const reference = (value: any): Reference | undefined =>
  typeof value?.provider === "string" && typeof value?.id === "string"
    ? { provider: value.provider, id: value.id } : undefined;
const label = (model: Reference) => JSON.stringify(`${model.provider}/${model.id}`);

// A missing/retired model is not the same as a generic HTTP 404, invalid key,
// quota limit, or service outage. Never render the raw provider error here.
export function classifyModelError(status: number | undefined, error: string, modelId: string) {
  if (status === 401 || status === 403) return "authentication";
  if (status === 429) return "rate_limit";
  if (status === 408 || (status !== undefined && status >= 500)) return "transient";
  if (/\b(?:invalid_api_key|authentication_error|insufficient_quota|rate_limit_exceeded)\b/i.test(error)) return "other";
  if (/\b(?:model_not_found|model_decommissioned|model_not_available|model_not_supported|unsupported_model)\b/i.test(error)) return "unavailable";
  const namesModel = modelId.length > 0 && error.toLowerCase().includes(modelId.toLowerCase());
  if (/temporar|overload|timeout|connection|try again/i.test(error)) return "other";
  const explicit = /(?:^|[\s"'])model\b.{0,160}(?:does not exist|not found|no longer available|has been (?:removed|retired)|decommissioned|not available|not supported)/i.test(error);
  return namesModel && explicit && (status === undefined || [400, 404, 410, 422].includes(status))
    ? "unavailable" : "other";
}

export function startupIssue(ctx: ExtensionContext, settings: any, argv: string[]): Issue | undefined {
  // Explicit CLI model/scope choices take precedence, including custom model IDs
  // absent from catalogs. A real rejection can still trigger recovery later.
  if (argv.some((arg) => /^(?:--model|--models)(?:=|$)/.test(arg))) return;
  const providerArg = argv.findIndex((arg) => /^--provider(?:=|$)/.test(arg));
  const provider = providerArg < 0 ? undefined : argv[providerArg].includes("=")
    ? argv[providerArg].slice("--provider=".length) : argv[providerArg + 1];
  const branch: any[] = ctx.sessionManager.getBranch();
  const changes = branch.filter((entry) => entry.type === "model_change");
  const hasConversation = branch.some((entry) => entry.type === "message" &&
    ["user", "assistant"].includes(entry.message?.role));
  let requested: Reference | undefined;
  if (provider && provider !== settings.defaultProvider) {
    requested = reference(ctx.model);
  } else if (hasConversation || changes.length > 1) {
    const last = changes.at(-1);
    requested = reference(last && { provider: last.provider, id: last.modelId });
  } else if (!ctx.scopedModels?.length) {
    requested = reference({ provider: settings.defaultProvider, id: settings.defaultModel });
  }
  requested ??= reference(ctx.model);
  if (!requested) return;
  const found = ctx.modelRegistry.find(requested.provider, requested.id);
  if (!found) return { ...requested, reason: "catalog" };
  if (!ctx.modelRegistry.hasConfiguredAuth(found)) return { ...requested, reason: "authentication" };
}

// Run from a command context: after saving through Pi's locking settings API,
// reload Pi's in-memory settings too. Do not reuse this context after reload.
export async function saveDefaultModel(pi: ExtensionAPI, ctx: ExtensionCommandContext, dependencies?: any) {
  const sdk = dependencies ?? await import("@earendil-works/pi-coding-agent");
  const runtime = {
    getAvailableSnapshot: () => ctx.modelRegistry.getAvailable(),
    getModel: (provider: string, id: string) => ctx.modelRegistry.find(provider, id),
    getError: () => ctx.modelRegistry.getError(),
    refresh: (options: any) => ctx.modelRegistry.refresh({ ...options, allowNetwork: !process.argv.includes("--offline") }),
  };
  const settings = pi.getSettings();
  const selected: any = await ctx.ui.custom((tui, theme, _keys, done) => {
    const picker = new sdk.ModelSelectorComponent(tui, ctx.model, runtime, ctx.scopedModels,
      (model: any) => done(model), () => done(undefined), undefined, (model: any) => done(model),
      settings.defaultProvider && settings.defaultModel ? { provider: settings.defaultProvider, id: settings.defaultModel } : undefined);
    const render = picker.render.bind(picker);
    picker.render = (width: number) => [theme.fg("accent", "Save default model: Enter saves; Escape cancels".slice(0, width)), ...render(width)];
    return picker;
  });
  if (!selected) return;
  if (!await pi.setModel(selected)) {
    ctx.ui.notify("The selected provider has no configured authentication. Default was not changed.", "error");
    return;
  }
  const preferences = sdk.SettingsManager.create(ctx.cwd, sdk.getAgentDir(), { projectTrusted: false });
  if (preferences.drainErrors().length) {
    ctx.ui.notify("Selected for this session, but Pi could not read its settings. Default was not saved.", "error");
    return;
  }
  preferences.setDefaultModelAndProvider(selected.provider, selected.id);
  await preferences.flush();
  if (preferences.drainErrors().length) {
    ctx.ui.notify("Selected for this session, but Pi could not save its settings. Default was not saved.", "error");
    return;
  }
  ctx.ui.notify(`Saved default ${label(selected)}. Reloading Pi settings; no prompt will be sent.`, "info");
  await ctx.reload();
}

export default function modelRecovery(pi: ExtensionAPI) {
  let issue: Issue | undefined;
  let status: number | undefined;
  let recovering = false;
  let offerRecovery = false;
  let selectionMark: string | undefined;
  let supported = true;
  let generation = 0;
  let refreshAbort: AbortController | undefined;
  const upgradeHint = "Omarchy model guard requires Pi 1.3 or newer. Update the Pi harness image or host Pi before submitting input.";
  const lastSelection = (ctx: ExtensionContext): any =>
    ctx.sessionManager.getBranch().filter((entry) => entry.type === "model_change").at(-1);
  const clearIssue = (ctx: ExtensionContext) => {
    issue = undefined;
    offerRecovery = false;
    ctx.ui.setStatus("omarchy-model-recovery", undefined);
  };
  const interactive = (ctx: ExtensionContext) => ctx.mode === "tui" &&
    process.env.OMARCHY_AGENT_MANAGED !== "true" &&
    !["1", "true"].includes(process.env.OMARCHY_AGENT_ONESHOT ?? "");

  const explain = () => issue?.reason === "authentication"
    ? `Authentication is not configured for ${label(issue)}. Use /login. No fallback model was approved.`
    : issue?.reason === "catalog"
      ? `${label(issue)} is absent from the current catalog. This does not prove retirement. Refresh or choose a model.`
      : issue ? `${label(issue)} was rejected as unavailable for this connection. Choose a model; no prompt will be resent.` : "No unavailable model is recorded.";

  const preparePicker = (ctx: ExtensionContext, save: boolean) => {
    const hint = save ? "press Enter in the picker to save the default" : "press Enter in the picker for this session only";
    if (!ctx.ui.getEditorText()) {
      ctx.ui.setEditorText(save ? "/model-recovery save" : "/model");
      ctx.ui.notify(`Press Enter to open Pi's model picker, then ${hint}. No prompt is submitted.`, "info");
    } else {
      ctx.ui.notify(`Your draft was not changed. Open ${save ? "/model-recovery save" : "/model"}, then ${hint}.`, "info");
    }
  };

  const recover = async (ctx: ExtensionContext) => {
    if (!interactive(ctx) || recovering) return;
    recovering = true;
    const activeGeneration = generation;
    try {
      while (true) {
        const choice = await ctx.ui.select(explain(), [
          "Choose a model for this session", "Choose and save a new default", "Refresh model catalog", "Exit Pi",
        ]);
        if (generation !== activeGeneration) return;
        if (choice === "Choose a model for this session" || choice === "Choose and save a new default") {
          preparePicker(ctx, choice === "Choose and save a new default");
          return;
        }
        if (choice === "Refresh model catalog") {
          if (process.argv.includes("--offline")) {
            ctx.ui.notify("Pi is offline. Cached models remain available; no network refresh was attempted.", "warning");
            continue;
          }
          const controller = new AbortController();
          refreshAbort = controller;
          const timer = setTimeout(() => controller.abort(), 15_000);
          try {
            const result = await ctx.modelRegistry.refresh({ allowNetwork: true, force: true, signal: controller.signal });
            if (generation !== activeGeneration) return;
            ctx.ui.notify(result.aborted || result.errors.size
              ? "Catalog refresh was incomplete. Cached models remain available."
              : "Catalog refreshed. Select a model explicitly; account access is not guaranteed by catalog presence.",
            result.aborted || result.errors.size ? "warning" : "info");
          } catch {
            if (generation !== activeGeneration) return;
            ctx.ui.notify("Catalog refresh failed. Cached models remain available; no model was changed.", "warning");
          } finally {
            clearTimeout(timer);
            if (refreshAbort === controller) refreshAbort = undefined;
          }
          continue;
        }
        if (choice === "Exit Pi") ctx.shutdown();
        return;
      }
    } finally {
      recovering = false;
    }
  };

  pi.registerCommand("model-recovery", {
    description: "Choose an available model or refresh Pi's catalog without resending a prompt",
    handler: async (args, ctx) => {
      if (!supported) ctx.ui.notify(upgradeHint, "error");
      else if (interactive(ctx) && args.trim() === "save") await saveDefaultModel(pi, ctx);
      else if (interactive(ctx)) await recover(ctx);
      else ctx.ui.notify("Model recovery needs interactive Pi. Set an explicit --provider and --model for automation.", "error");
    },
  });

  pi.on("session_shutdown", () => {
    generation++;
    refreshAbort?.abort();
  });
  pi.on("session_start", async (_event, ctx) => {
    status = undefined;
    offerRecovery = false;
    supported = typeof pi.getSettings === "function" && typeof ctx.mode === "string" &&
      typeof ctx.modelRegistry.find === "function" && typeof ctx.modelRegistry.hasConfiguredAuth === "function";
    if (supported) {
      try {
        issue = startupIssue(ctx, pi.getSettings(), process.argv);
        selectionMark = lastSelection(ctx)?.id;
      } catch {
        supported = false;
      }
    }
    if (!supported) {
      if (interactive(ctx)) ctx.ui.notify(upgradeHint, "error");
      else { console.error(upgradeHint); process.exitCode = 1; ctx.shutdown(); }
      return;
    }
    if (issue) {
      if (interactive(ctx)) await recover(ctx);
      else {
        console.error(`Omarchy model guard: ${explain()} Choose an explicit --provider and --model, or repair the default in interactive Pi.`);
        process.exitCode = 1;
        ctx.shutdown();
      }
    }
  });
  pi.on("model_select", (event, ctx) => {
    // Pi owns the actual selection and default persistence. Only an explicit
    // selection/cycle clears a blocked fallback; catalog refresh alone does not.
    if (event.source !== "restore") clearIssue(ctx);
    else selectionMark = lastSelection(ctx)?.id;
  });
  pi.on("input", (event, ctx) => {
    if (!supported) {
      if (interactive(ctx)) ctx.ui.notify(upgradeHint, "error");
      else { console.error(upgradeHint); process.exitCode = 1; ctx.shutdown(); }
      return { action: "handled" };
    }
    // Pi appends a model_change for an explicit re-selection of the same model,
    // but does not emit model_select in that case. Observe that native record.
    const selected = lastSelection(ctx);
    if (issue && selected?.id && selected.id !== selectionMark &&
        selected.provider === ctx.model?.provider && selected.modelId === ctx.model?.id) clearIssue(ctx);
    if (!issue) return { action: "continue" };
    if (interactive(ctx)) {
      if (!ctx.ui.getEditorText()) ctx.ui.setEditorText(event.text);
      ctx.ui.notify(`${explain()} Input was not sent. Use /model-recovery or /model; reattach images if needed.`, "error");
    } else {
      console.error(`Omarchy model guard: ${explain()} Input was not sent. Set an available --provider and --model.`);
      process.exitCode = 1;
      ctx.shutdown();
    }
    return { action: "handled" };
  });
  pi.on("cache_warming_decision", () => issue || !supported ? { action: "stop" } : undefined);
  pi.on("turn_start", () => { status = undefined; });
  pi.on("before_provider_request", () => { status = undefined; });
  pi.on("after_provider_response", (event) => { status = event.status; });
  pi.on("message_end", (event, ctx) => {
    const message = event.message;
    if (message.role !== "assistant" || message.stopReason !== "error") return;
    if (classifyModelError(status, message.errorMessage ?? "", message.model) !== "unavailable") return;
    issue = { provider: message.provider, id: message.model, reason: "rejected" };
    selectionMark = lastSelection(ctx)?.id;
    offerRecovery = true;
    // Stop further work in this run. Never queue or replay a failed prompt.
    ctx.abort();
    if (interactive(ctx)) ctx.ui.setStatus("omarchy-model-recovery", "Model unavailable · /model-recovery");
    else {
      console.error(`Omarchy model guard: ${explain()} Set an available --provider and --model.`);
      process.exitCode = 1;
    }
  });
  pi.on("agent_settled", async (_event, ctx) => {
    if (offerRecovery) {
      offerRecovery = false;
      if (interactive(ctx)) await recover(ctx);
      else ctx.shutdown();
    }
  });
}
