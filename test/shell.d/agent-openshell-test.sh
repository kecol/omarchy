#!/bin/bash

set -euo pipefail

source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/base-test.sh"

test_tmp=$(mktemp -d)
trap 'rm -rf "$test_tmp"' EXIT

mock_bin="$test_tmp/bin"
test_home="$test_tmp/home"
auth_file="$test_tmp/codex-auth.json"
openshell_log="$test_tmp/openshell-log"
mkdir -p "$mock_bin" "$test_home"

cat >"$auth_file" <<'JSON'
{
  "tokens": {
    "access_token": "access-secret-test",
    "refresh_token": "refresh-secret-test",
    "account_id": "account-test",
    "id_token": "id-secret-test"
  }
}
JSON

cat >"$mock_bin/openshell" <<'SH'
#!/bin/bash
printf '%s\0' "$@" >>"$OMARCHY_TEST_OPENSHELL_LOG"
printf '\n' >>"$OMARCHY_TEST_OPENSHELL_LOG"
case "$1 ${2:-}" in
  "--version ")
    printf 'openshell 0.1-test\n'
    ;;
  "doctor check")
    ;;
  "gateway list")
    printf '{"gateways":[{"name":"local"}]}\n'
    ;;
  "gateway info")
    printf '{"name":"local"}\n'
    ;;
  "profile lint")
    ;;
  "profile describe")
    exit 1
    ;;
  "profile import")
    ;;
  "provider get")
    [[ ${OMARCHY_TEST_PROVIDER_EXISTS:-false} == true ]]
    ;;
  "provider create")
    [[ -n ${CODEX_AUTH_ACCESS_TOKEN:-} && -n ${CODEX_AUTH_ACCOUNT_ID:-} ]] || exit 2
    ;;
  "provider update")
    [[ -n ${CODEX_AUTH_ACCESS_TOKEN:-} && -n ${CODEX_AUTH_ACCOUNT_ID:-} ]] || exit 2
    ;;
  "provider refresh")
    if [[ ${3:-} == "configure" ]]; then
      [[ -n ${CODEX_AUTH_REFRESH_TOKEN:-} ]] || exit 3
    fi
    ;;
  "sandbox create")
    printf 'OpenShell provider: codex\nCredential env: CODEX_AUTH_ACCESS_TOKEN=set CODEX_AUTH_ACCOUNT_ID=set\nPrompt: mocked\n'
    ;;
  *)
    echo "unexpected openshell call: $*" >&2
    exit 1
    ;;
esac
SH
chmod +x "$mock_bin/openshell"

output=$(env HOME="$test_home" CODEX_AUTH_FILE="$auth_file" OMARCHY_TEST_OPENSHELL_LOG="$openshell_log" PATH="$mock_bin:$ROOT/bin:/usr/bin" \
  "$ROOT/bin/omarchy-agent-openshell-provider-import" codex)
[[ $output == *"Imported Codex credentials"* ]] || fail "Codex provider import reports success" "$output"
if grep -Eq 'access-secret-test|refresh-secret-test|id-secret-test' <<<"$output"; then
  fail "Codex provider import does not print credential values" "$output"
fi
tr '\0' ' ' <"$openshell_log" >"$test_tmp/openshell-log-text"
grep -Fq -- 'provider create --name codex --type codex --credential CODEX_AUTH_ACCESS_TOKEN --credential CODEX_AUTH_ACCOUNT_ID --credential CODEX_AUTH_ID_TOKEN' "$test_tmp/openshell-log-text" ||
  fail "Codex provider import creates provider with credential env lookups" "$(cat "$test_tmp/openshell-log-text")"
grep -Fq -- 'provider refresh configure codex --credential-key CODEX_AUTH_ACCESS_TOKEN --strategy oauth2-refresh-token' "$test_tmp/openshell-log-text" ||
  fail "Codex provider import configures gateway-owned refresh" "$(cat "$test_tmp/openshell-log-text")"
pass "Codex account import stores minimal OpenShell provider credentials without printing secrets"

pi_auth="$test_tmp/pi-auth.json"
jq -n --argjson expires "$(( $(date +%s) * 1000 + 3600000 ))" '
  {"openai-codex": {type: "oauth", access: "pi-access-secret-test", accountId: "pi-account-test",
    refresh: "pi-refresh-never-import", expires: $expires}}
' >"$pi_auth"
: >"$openshell_log"
output=$(env HOME="$test_home" PI_AUTH_FILE="$pi_auth" OMARCHY_TEST_OPENSHELL_LOG="$openshell_log" PATH="$mock_bin:$ROOT/bin:/usr/bin" \
  "$ROOT/bin/omarchy-agent-openshell-provider-import" pi)
[[ $output == *"Imported Pi Codex access-token snapshot"* ]] || fail "Pi importer reports snapshot" "$output"
tr '\0' ' ' <"$openshell_log" >"$test_tmp/pi-import-log"
grep -Fq 'provider create --name pi-codex --type codex' "$test_tmp/pi-import-log" || fail "Pi import uses dedicated provider" ""
if grep -Eq 'provider refresh|pi-access-secret-test|pi-refresh-never-import' "$test_tmp/pi-import-log" ||
  grep -Eq 'pi-access-secret-test|pi-refresh-never-import' <<<"$output"; then
  fail "Pi importer must not share refresh ownership or print secrets" ""
fi
jq '.["openai-codex"].expires = 1' "$pi_auth" >"$test_tmp/expired-auth.json"
: >"$openshell_log"
if env HOME="$test_home" PI_AUTH_FILE="$test_tmp/expired-auth.json" OMARCHY_TEST_OPENSHELL_LOG="$openshell_log" PATH="$mock_bin:$ROOT/bin:/usr/bin" \
  "$ROOT/bin/omarchy-agent-openshell-provider-import" pi >"$test_tmp/pi-error" 2>&1; then
  fail "expired Pi credentials must be rejected" ""
fi
if grep -aq 'provider create' "$openshell_log"; then fail "expired credentials must not be imported" ""; fi
pass "Pi import snapshots access credentials without importing refresh material and rejects expiry"

: >"$openshell_log"
output=$(env HOME="$test_home" OMARCHY_TEST_PROVIDER_EXISTS=true OMARCHY_TEST_OPENSHELL_LOG="$openshell_log" PATH="$mock_bin:$ROOT/bin:/usr/bin" \
  "$ROOT/bin/omarchy-agent-openshell-prompt" --provider codex "hello openshell")
[[ $output == *"Credential env: CODEX_AUTH_ACCESS_TOKEN=set CODEX_AUTH_ACCOUNT_ID=set"* ]] ||
  fail "OpenShell prompt smoke verifies credential presence" "$output"
tr '\0' ' ' <"$openshell_log" >"$test_tmp/openshell-prompt-log-text"
grep -Fq -- 'sandbox create --no-keep --no-tty --provider codex --env OMARCHY_OPEN_SHELL_PROMPT=hello openshell' "$test_tmp/openshell-prompt-log-text" ||
  fail "OpenShell prompt smoke creates a disposable provider sandbox" "$(cat "$test_tmp/openshell-prompt-log-text")"
pass "OpenShell prompt smoke runs a disposable provider-backed sandbox"

: >"$openshell_log"
output=$(env HOME="$test_home" OMARCHY_TEST_PROVIDER_EXISTS=true OMARCHY_TEST_OPENSHELL_LOG="$openshell_log" PATH="$mock_bin:$ROOT/bin:/usr/bin" \
  "$ROOT/bin/omarchy-agent-openshell-pi" --model gpt-6.1-sol "hello pi")
[[ $output == *"OpenShell provider: codex"* ]] || fail "OpenShell Pi proof invokes sandbox" "$output"
tr '\0' ' ' <"$openshell_log" >"$test_tmp/openshell-pi-log-text"
grep -Fq -- 'sandbox create --no-keep --no-tty --from localhost/omarchy-harness-pi:latest --provider codex' "$test_tmp/openshell-pi-log-text" ||
  fail "OpenShell Pi proof creates a disposable Pi sandbox" "$(cat "$test_tmp/openshell-pi-log-text")"
grep -Fq -- '--extension /opt/omarchy/pi/extensions/openshell-codex.ts' "$test_tmp/openshell-pi-log-text" ||
  fail "OpenShell Pi proof loads the OpenShell Codex Pi extension" "$(cat "$test_tmp/openshell-pi-log-text")"
if grep -Fq -- '--no-extensions' "$test_tmp/openshell-pi-log-text"; then
  fail "OpenShell Pi proof must not disable its provider extension" "$(cat "$test_tmp/openshell-pi-log-text")"
fi
pass "OpenShell Pi proof wires the OpenShell Codex Pi extension"

: >"$openshell_log"
output=$(env HOME="$test_home" OMARCHY_TEST_PROVIDER_EXISTS=true OMARCHY_TEST_OPENSHELL_LOG="$openshell_log" PATH="$mock_bin:$ROOT/bin:/usr/bin" \
  "$ROOT/bin/omarchy-agent-openshell-pi" --tools --model gpt-6.1-sol "use tools")
[[ $output == *"Pi tools:      true"* ]] || fail "OpenShell Pi proof reports tools mode" "$output"
tr '\0' ' ' <"$openshell_log" >"$test_tmp/openshell-pi-tools-log-text"
grep -Fq -- '--env OMARCHY_OPEN_SHELL_TOOLS=true' "$test_tmp/openshell-pi-tools-log-text" ||
  fail "OpenShell Pi proof passes tools mode into sandbox" "$(cat "$test_tmp/openshell-pi-tools-log-text")"
grep -Fq -- 'tools_flag="--no-tools"' "$test_tmp/openshell-pi-tools-log-text" ||
  fail "OpenShell Pi proof keeps no-tool mode explicit by default in sandbox script" "$(cat "$test_tmp/openshell-pi-tools-log-text")"
pass "OpenShell Pi proof supports explicit Pi tools mode"

catalog="$ROOT/containers/harnesses/pi/extensions/openshell-codex-models.json"
jq '.[0].id = "test-sol"' "$catalog" >"$test_tmp/models.json"
: >"$openshell_log"
output=$(env HOME="$test_home" OMARCHY_TEST_PROVIDER_EXISTS=true OMARCHY_TEST_OPENSHELL_LOG="$openshell_log" PATH="$mock_bin:$ROOT/bin:/usr/bin" \
  "$ROOT/bin/omarchy-agent-openshell-pi" --models-file "$test_tmp/models.json" --model test-sol "hello")
tr '\0' ' ' <"$openshell_log" >"$test_tmp/catalog-log"
grep -Fq 'OMARCHY_OPEN_SHELL_MODELS_JSON=' "$test_tmp/catalog-log" || fail "catalog is passed to sandbox" "$output"
grep -Fq 'test-sol' "$test_tmp/catalog-log" || fail "custom model is passed to sandbox" "$output"
if env HOME="$test_home" PATH="$mock_bin:$ROOT/bin:/usr/bin" \
  "$ROOT/bin/omarchy-agent-openshell-pi" --models-file "$test_tmp/models.json" --model missing "hello" >"$test_tmp/error" 2>&1; then
  fail "unknown model must be rejected" ""
fi
grep -Fq 'Model not in catalog' "$test_tmp/error" || fail "unknown model has useful error" ""
pass "OpenShell Pi accepts custom catalogs and rejects missing models"
