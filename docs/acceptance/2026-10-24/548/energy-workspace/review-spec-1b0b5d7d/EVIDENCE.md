# Review evidence and boundaries

Reviewer ownership is confined to this directory. No source, native database,
browser, process, dependency, settings, credentials, index, commit, merge or
deployment was changed. Temporary empty directories accidentally created under
`apps/planner/docs` before test redirection were removed immediately with `rmdir`;
no file was written there.

## Fixed comparison

```text
git diff 71b54073622117c12953cd40957ec1f5d4d827a6...1b0b5d7d0cafd29ca6ee9ed8ac6850ae228dc4eb
git log 71b54073622117c12953cd40957ec1f5d4d827a6..1b0b5d7d0cafd29ca6ee9ed8ac6850ae228dc4eb --oneline
1b0b5d7d Connect project energy scenarios to managed calculations (#548)
```

Reviewed hand-authored source, schema exports, tests, fixture provenance, copy
disposition/review artifacts, CSS and the build manifest/graph. Generated vendor
chunks were validated through actual source/build hashes and the lazy-entry
execution guard rather than treated as hand-authored semantics.

## Executed checks

| Working directory | Command | Evidence | Result |
| --- | --- | --- | --- |
| `apps/planner` | `npm test` | `planner-tests.txt` | Exit 0: domain/data 115/115; JSDOM/component 156/156, no skips |
| `apps/planner` | `npm run lint:types` | `types.txt` | Exit 0 |
| `apps/planner` | `npm run build:check` | `build-check.txt` | Exact source/build hashes match; lazy built chunk/versioned WP entry guard 1/1 |
| `services/engine` | `uv run pytest -q tests/planning/test_browser_energy_contracts.py tests/planning/test_workspace.py tests/planning/test_private_http.py` | `engine-focused.txt` | Exit 0: 104/104 |

The Node build-module probe emits the existing module-type advisory. It does not
fail or alter package metadata. No service restart or build was performed.

`artifact-checks.json` records current source pin, exact equality of the managed
worker's recorded `http.json.finished` response and the browser fixture, and actual
GNUTranslations/native JSON readback of all 187 final German entries. These
checks concern committed artifacts and fixtures, not new native calculations.

## Contract trace

| Spec obligation | Reviewed implementation / meaningful probes |
| --- | --- |
| Versioned explicit scenario, no defaults | `energyScenario.ts`, both generated schemas, exporter and shared positive/negative Pydantic/Ajv fixtures |
| Provenance and correct source roles | Gross/PV-available/aux selection, outage critical input, owned battery source, source-range microsecond tests, result model/pinned-source checks, `RunBasis` historical read and asset/hash agreement |
| Save and preparation cannot rewrite later edits | Scenario document/source selection guards; domain undo/effective replay invalidation; component late-preparation-response probe |
| One original protected run intent | Real FakeIndexedDB persistence, namespace/body conflict/retention/corruption tests; double-activation, lost response/exact retry, storage refusal, unmount and native account withdrawal probes |
| Specific safe stale-revision handling | Backend tests prove no stale-new run/job/receipt publication and successful old receipt replay; generic conflict retains the browser intent |
| Durable task/result history | Actual state enum/cursors, scoped Query keys, explicit server cancel, response and cancellation lifecycle fencing; no pause/progress fiction |
| Result truth | Managed fixture totals 3.62 kWh solar / 0.38 kWh grid; wrong identity/source/model/status/shape mutants rejected; mixed/zero-scope undefined reasons preserved; no equipment/country release claim |
| EN/DE context | Same-project run/hash allowlist, project switch removal, native URL preservation tests, reviewed and compiled 187-entry German corpus |

The fixture totals above come from the previously recorded managed worker. The
component mock reuses that response only as a transport/shape fixture and is not
counted as independent numerical or native-browser proof. No external factual
claim was researched or introduced in this review.
