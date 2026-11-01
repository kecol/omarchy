// Runtime renderer ownership is not persistent plugin enablement.
function create() {
  return { suspended: false, instance: null };
}

function status(registry, unreadable) {
  if (unreadable || !registry || registry.scanning || !registry.installedPlugins)
    return "not ready";
  var id = registry.resolveEnabledId("omarchy.background");
  if (!registry.installedPlugins[id]) return "not ready";
  return registry.isEnabled(id) ? "ready" : "disabled";
}

function request(state, registry, service, value, unreadable) {
  if (value !== "true" && value !== "false") return "invalid";
  var current = status(registry, unreadable);
  if (current === "not ready") return current;
  if (current === "ready" && (!service || !("suspended" in service)))
    return "not ready";

  state.suspended = value === "true";
  state.instance = service;
  // A disabled plugin must stay hidden even if its service is still unloading.
  if (service && "suspended" in service)
    service.suspended = current === "disabled" || state.suspended;
  return current === "disabled" ? "disabled" : "ok";
}

function sync(state, registry, service, unreadable) {
  var current = status(registry, unreadable);
  if (current === "not ready") return;
  if (!service) {
    state.instance = null;
    return;
  }
  if (!("suspended" in service)) return;
  if (current === "disabled") service.suspended = true;
  else if (service !== state.instance) service.suspended = state.suspended;
  state.instance = service;
}

if (typeof module !== "undefined") module.exports = { create, request, sync };
