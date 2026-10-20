#!/bin/bash
set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/bin" "$tmp/home"
cat >"$tmp/bin/pi" <<'SH'
#!/bin/bash
if [[ ${1:-} == --version ]]; then echo 1.3.0; exit; fi
cp "$TEST_PI_MODELS" "$OMARCHY_OPEN_SHELL_MODEL_EXPORT"
SH
cat >"$tmp/bin/podman" <<'SH'
#!/bin/bash
echo 1.3.0
SH
cat >"$tmp/bin/openshell" <<'SH'
#!/bin/bash
if [[ "$1 ${2:-} ${3:-}" == 'provider refresh status' ]]; then echo 'snapshot: no gateway refresh'; exit; fi
echo 'unexpected network/sandbox call' >&2
exit 99
SH
chmod +x "$tmp/bin/"*
export PATH="$tmp/bin:$ROOT/bin:/usr/bin"
export HOME="$tmp/home" XDG_CONFIG_HOME="$tmp/home/.config"
export TEST_PI_MODELS="$tmp/upstream.json"
source_catalog="$ROOT/containers/harnesses/pi/extensions/openshell-codex-models.json"
jq '.[0:1] | .[0].provider = "openai-codex"' "$source_catalog" >"$TEST_PI_MODELS"
command="$ROOT/bin/omarchy-agent-openshell-models"
"$command" sync >"$tmp/preview"
target="$XDG_CONFIG_HOME/omarchy/openshell/pi-models.json"
[[ ! -e $target ]] || fail 'sync preview must not write' ''
"$command" sync --apply >"$tmp/apply"
[[ -f $target ]] || fail 'sync apply writes user catalog' ''
[[ $(jq length "$target") == $(jq length "$source_catalog") ]] || fail 'sync preserves catalog-only entries' ''
# Simulate upstream metadata drift and a user override.
jq 'map(if .id == "gpt-6.1-sol" then .name = "Personal name" else . end)' "$target" >"$tmp/edited"
mv "$tmp/edited" "$target"
jq '.[0].contextWindow = 600000 | .[0].name = "New upstream name"' "$TEST_PI_MODELS" >"$tmp/new"
mv "$tmp/new" "$TEST_PI_MODELS"
"$command" sync --apply >"$tmp/resync"
[[ $(jq -r '.[0].name' "$target") == 'Personal name' ]] || fail 'sync must preserve user overrides' ''
[[ $(jq -r '.[0].contextWindow' "$target") == 600000 ]] || fail 'sync updates managed metadata' ''
pass 'model sync previews, preserves overrides and removed entries, and updates managed metadata'
"$command" doctor >"$tmp/doctor"
grep -Fq 'Live checks skipped' "$tmp/doctor" || fail 'doctor must be offline by default' ''
printf '[]' >"$tmp/invalid.json"
if "$command" doctor --models-file "$tmp/invalid.json" >"$tmp/error" 2>&1; then fail 'doctor rejects invalid catalogs' ''; fi
pass 'model doctor validates catalogs and performs no live probes by default'
