# Tasks

Status: IMPLEMENTED SOURCE; focused verification complete, not activated or deployed. The pure reader, two consumer edits and fixture extensions exist. Source syntax/dependency checks passed. Both focused suites passed without skips (27 guard, 26 launcher and 19 menu methods); disposable future-ID and label-fallback mutations produced the expected semantic failures. Documentation, relative links, boundary mapping, whitespace, strict OpenSpec validation and protected-file hashes passed. See `outcome.md` for scope and exclusions. Existing unrelated edits remain protected.

## 1. Extract the bundled catalog reader

- [x] 1.1 Add the pure `default/agents/catalog.js` projection and change only the two consumers' embedded Node imports/projections; extend the existing guard/menu Python fixtures for synthetic parser parity, real future-product discovery, actual picker transport and caller-specific failure/limit behavior. Verify the source diff has no shared menu/QML/public-command or policy changes and no remaining runtime import of the UI model in these two consumers.
- [x] 1.2 Run `test/shell.d/agent-command-guards-test.sh` and `test/shell.d/agent-menu-test.sh` once each in the existing bounded test environment with complete separate logs; demonstrate a meaningful future-ID/projection or label-rule negative control in a disposable copy. Read and record exact outcomes, skips and any failures; rerun only affected cases after a covered change, without tool installation or live agent/engine/provider/UI actions.
- [x] 1.3 Update managed-agent documentation, the inventory, proposal status and work ledger with actual implementation/evidence scope, unchanged entrypoint contracts, remaining coupling and rollback. Verify relative links, whitespace, strict OpenSpec validation and unchanged protected Containerfile hashes; leave deployment/native qualification explicitly not run.

## Workflow follow-up

- Present the source diff and scoped test results for review. Do not treat artifact/task completion as activation approval.
- Keep installation, activation, commits/pushes and archiving excluded. Do not resume the inactive merge or VM/tracer work.
