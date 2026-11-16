# Catalog-reader implementation outcome

## Delivered source

The user approved the bounded implementation after reviewing the original extraction proposal. The working-tree implementation adds `default/agents/catalog.js` and changes only the embedded Node imports/projections in `default/agents/command-guards.py` and `default/agents/launch-menu.py`. The base HEAD remains `68d22643e4bd4df623977d125da7ce3b06f3a30f`; the extraction was subsequently committed as `d2471ba1d` (`Extract bundled agent catalog reader`), not deployed. That atomic commit contains the three runtime files, two fixtures and only the catalog-reader subsection of `docs/managed-agents.md`. Earlier setup/inventory/tracking and broader documentation edits remain uncommitted.

The pure `agentCatalog(raw)` CommonJS function retains the limited parser's whole-line comments/trailing-comma transformation, flat/wrapped object handling, object-row filtering, enumeration order, exact agent-ID pattern and `label || id` fallback. It performs no I/O, state/environment reads or execution. The bundled menu remains the single catalog.

Guard and picker policies are unchanged: different subprocess environments/cwd/stdin handling, five-second Node timeouts, guard output/list limits, picker record/label checks and empty-catalog outcomes. Missing files/module, Node failure and timeout do not gain a fallback. Definitions, registrations, installed-command checks and picker eligibility stay with their existing owners.

The two runtime imports of `MenuModel.js` are removed from these consumers. The shared menu model is still a test oracle for synthetic parser compatibility, not a runtime dependency. Menu data format/location, Node availability and `OMARCHY_PATH` remain coupling points. No conflict-rate, elapsed-time improvement or whole-layer extraction is claimed.

## Focused verification

| Execution | Actual outcome | Scope |
| --- | --- | --- |
| `bash test/shell.d/agent-command-guards-test.sh` | Passed once: 27 test methods; no skips. | Existing guard behavior plus real installed-Node future-product discovery with scratch catalog/state and inert executable metadata; malformed/empty catalog registration path; missing file/module refusal; substituted transport failure and response-limit cases. |
| `bash test/shell.d/agent-menu-test.sh` | Passed once: 26 launcher methods and 19 menu methods; no skips; help route also succeeded. | Launcher/picker/menu dispatch fixtures; real reader transport and synthetic parser parity; invalid records, control characters and record limits; missing file/module and error propagation. Existing clone coverage uses real temporary Git/key creation with mocked engine/editor/agent execution. |
| Future-ID negative control | Expected semantic failure observed in a disposable copy: removing `future-catalog` from projection made the existing discovery assertion fail. | Confirms the new real-discovery case detects loss of a future product, not merely a missing module import. |
| Label-fallback negative control | Expected Node deep-equality assertion failure observed in a disposable copy: missing label became undefined instead of its ID fallback. | Confirms the parser-compatibility case detects changed projection behavior. |
| Source checks | Python syntax passed; targeted diff retains caller policy; shared runtime surfaces remain unchanged. | Source structure, not native runtime enforcement. |

The expected missing-file/module cases emit Node error messages in the menu log; their enclosing tests passed by verifying error propagation. Those messages are not unexplained suite failures. The semantic mutation failures are intentional negative controls, not defects in the delivered source. No positive suite was repeated to recover output or confirm a pass.

Tests used preinstalled Node 26.13.0 without shim/tool installation. They ran sequentially in a transient user test unit configured with UID/GID 1000, nice 10, memory 2 GiB, swap 512 MiB, CPU 200%, tasks 512 and runtime 150 seconds. Each suite had an outer 45-second limit with a two-second termination grace. Negative controls used a separate bounded 45-second unit. These are configured test limits, not an assertion of a new production sandbox or binary attestation.

Portable local receipts are under `$HOME/Work/omarchy-catalog-extraction-02/`: `agent-command-guards.log`, `agent-menu.log`, `test-status.txt`, `negative-controls.log`, the two semantic-negative logs, `source.patch`, `source-check.log` and `tested-source.sha256`. They contain scoped local test evidence, not release artifacts. No private account/session state or credentials were used as fixture data.

## Preserved contracts and exclusions

The [implemented entrypoint supplement](../../../docs/agent-safety-boundaries.md#implemented-entrypoint-contracts) remains the preservation checklist. No public CLI, mode/default behavior, picker eligibility, menu options/confirmation, widget click/right-click action, workspace-file sharing, guard registration, account/session sharing, image selection, resource policy or lifecycle controller was changed. Shared `shell/`, menu data, `bin/`, Bash startup, workspace backend, image/installation/migration/configuration sources were left unchanged; the two pre-existing modified harness Containerfiles retain their hashes.

These passes qualify only the described parser/metadata/fixture-dispatch behavior. They do not qualify actual agent/container execution, credential/provider behavior, cloud session separation, native Qt/menu/widget interaction, attach/stop signals, hardware, full suites, CI or a release. Existing malformed-catalog/admission/identity/engine/credential limitations remain documented, not fixed by this extraction.

During implementation and fixture verification, no installation, activation, package operation, migration, live guard synchronization, live agent/workspace/doctor/provider action, GUI/VM operation, commit, push or archive was performed. After the user separately accepted the source review and authorized a commit, the six-file extraction commit above was created with the repository-local public `noreply` identity. No push, activation or archive followed. The inactive merge and VM/tracer work remain paused.

## Rollback and review

Restore the two Python consumers and their fixture changes from the same pre-extraction revision before removing the new module. Leave unrelated edits and user data intact. No account, default, guard registry, workspace or volume rollback is required by this source refactor. The [approved design](../../../plans/agent-safety-first-extraction.md) retains the detailed rollback/deployment constraints.

Review the working-tree source diff and scoped logs before any separately approved deployment or publication. Task completion is not activation or archive approval.
