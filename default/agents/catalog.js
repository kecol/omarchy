// Copyright (c) David Heinemeier Hansson
// SPDX-License-Identifier: MIT (see LICENSE)
// Parsing semantics derived from shell/plugins/menu/MenuModel.js.
// Keep the bundled catalog contract independent of desktop rendering/routing.
function agentCatalog(raw) {
  var stripped = String(raw || "")
    .replace(/^\s*\/\/[^\n]*(\n|$)/gm, "")
    .replace(/,(\s*[}\]])/g, "$1")
  if (!stripped.trim()) return []

  var parsed
  try {
    parsed = JSON.parse(stripped)
  } catch (e) {
    return []
  }
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) return []

  var source = (parsed.items && typeof parsed.items === "object" && !Array.isArray(parsed.items))
    ? parsed.items
    : parsed
  var out = []
  for (var id in source) {
    var entry = source[id]
    if (!entry || typeof entry !== "object" || Array.isArray(entry)) continue
    if (!/^setup\.default\.agent\.[a-z0-9-]+$/.test(id)) continue
    out.push({name: id.split(".").pop(), label: entry.label || id})
  }
  return out
}

module.exports = {agentCatalog: agentCatalog}
