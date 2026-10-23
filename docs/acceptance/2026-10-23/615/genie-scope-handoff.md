# Genie publication scope handoff

This is a source and local-fixture handoff for ticket 615. The source fixes are
on `codex/615-publication-genie`; no production deployment or permission write
was performed in this worktree. The captured source snapshot has 85 ordinary
published products and 142 documents. These are captured local Woo facts, not a
claim about the current live site.

**The corpus measurements below are a replay of the older immutable cached
index. They are not coverage/readiness results for the new normal-worker build.**
The root integration session reports that its new build has 10,894 chunks from
142 cached documents, while this replay uses 11,413 associated older chunks.
New Woo-derived metadata and chunk boundaries can differ. Recheck coverage,
scope proofs, loaded versions and acknowledgement from that actual build when
it finishes; these replay counts cannot replace that acceptance.

The final runtime scope source is `e08a60c9`, including the two original-table
axis review fixes after `2c309da6`. Local verification:

- Complete selected Genie Python suite: 2,148 passed, 1 skipped, 195 deselected,
  6 expected failures, 53.63 seconds.
- Scope/extraction/build/MariaDB selection: 113 passed. After the final type-only
  fixture corrections, the native-column and failed-generation fixtures pass
  together (20 tests).
- The exact Genie `py-check` commands pass: `ruff check .`, `ruff format --check .`
  (197 files) and `mypy .` (192 source files, including index/eval/tests). The
  earlier src/index/ops-only 84-file check is not presented as this complete gate.
- The failed-generation fixture now uses the existing typed Words tokenizer;
  no runtime signature or type-check policy was weakened. The new frozen JSON
  fixture validates its decoded dictionary before returning it.

Final read-only measurements on that runtime source:

| Measure | Result |
| --- | ---: |
| Current ordinary products / associated documents / unique document SHA | 85 / 142 / 142 |
| Associated cached chunks / exact native-parse matches | 11,413 / 11,413 |
| Cached parses decoded / failures | 142 / 0 |
| Table fragments with source provenance | 1,691 |
| Proven chunks, earlier guard / final | 165 / 813 |
| New proven original-table-column fragments | 20 |
| Documents with proven passages | 76 |
| Products with a usable retrievable passage | 70 of 85 |
| Complete preparation | false |
| Original 632 goldens with an eligible expected page, earlier guard / final | 52 / 154 |
| Remaining unnamed/variant / unknown-or-unassociated / unavailable-model cases | 374 / 72 / 32 |
| Native-unavailable-model passages / those released | 1,817 / 0 |
| Unassociated passages released | 0 |
| Simulated H2-10K-T3 withdrawal: stale IDs / explicit withdrawn passages released | 0 / 0 |

All 142 actual document identities have distinct SHA values in this captured
snapshot. Joint-identity authorization is tested separately; it is not credited
with an invented coverage improvement in this corpus. Decoding/rechunking the
cached parses took 41.97 seconds, and subsequent proof/replay took 97.22 seconds.
No PDF parsing, OCR, embedding or paid provider was started for this audit.

## Implemented boundaries

Woo remains the sole product/document permission authority. Published products,
product revisions, exact document identities/revisions and actual per-product
associations are required. SHA only reuses bytes and parses. Genie excludes the
Woo engineering-reference role from products, documents and new signed actions.
The signed Genie product list remains independent of an engineering calculation.
Root owns the trusted receipt-kind integration and native REST acceptance.

Ordinary engineering tokens such as IP65, 50Hz and IEC standards are not products
just because they contain letters and digits. Authored current-model passages,
unambiguous single-model sections/documents and explicit general Woo document
purposes provide recorded scope. Mixed files never assign an unnamed parameter
table to a surviving product by association alone. Manufacturer common-terms
statements authorize only the proven non-parameter prose allowed by the contract.

A whole passage naming A and B can bind their two separate current document
identities with matching bytes. Every exact document/product revision and
association remains required; withdrawing either refuses the whole passage.

Split technical tables now record native Docling TableItem, page/origin and
preceding continuous text chunk IDs. Original Technical Data model columns can
supply scope only to the immediately following table. All fragments retain the
complete original columns and their order. Unknown column models, new tables,
new sections, incomplete columns and a partial/different/reversed local model
axis refuse the group. The last two review findings are covered by original
TableItem mutations, with `header_rows=0`, matching-order controls and a different
currently published model actually associated with the same document. Runtime
returns the proven column heading with each fragment; it does not use alphabetic
model metadata to guess column order.

Native Woo language/type labels are normalized in derived build metadata only.
The original manifest is preserved. EN/DE/MUL/MULTI/EN/DE/DE/EN/empty map to
`en`/`de`/`mul`/`und`; ES remains `es`. Known EN/DE document roles/types follow
Materials' vocabulary, with role first. Unknown labels fail visibly. Warranty
purpose remains available to the scope guard although the five-type index uses
`other` for its descriptive metadata.

Availability means at least one proven retrievable passage. It does not mean
all associated documents are prepared. Missing/ambiguous documents remain visible
as `preparation_complete=false` and `unprepared_documents`; the PHP acknowledgement
contract is foundation commit `55a66f0b`. No incomplete preparation is reported as
complete simply because products have partial evidence.

## Fixed representative and rejected counterexample

The original HCA datasheet places `Technical Data GW7K-HCA-20` in a text block,
then `GW11K-HCA-20` and `GW22K-HCA-20` before one native TableItem. The table's
three value columns are in that order. All three current models have actual Woo
associations to `doc-9b809373f9d915cfd74012104fbf8e70c3cdf31c62714e5b0758b5c1aacd04af`,
revision `c4648c72de0b19c28d66b9a4ac5d8b9148841cabdbde7634a9b98ccca0a5fd44`.
The recovered grid-voltage fragment is `0fdeaf90548f-p2-a369018b` in the older
cached chunk layout. Its columns are 230 L/N/PE, 400 3L/N/PE, 400 3L/N/PE.
The actual Docling fixture proves the original structure and every column.

The G10 ESA source remains refused: original chunk
`c95aef48b1ea-p2-9b1de5f3` explicitly says G11, while current Woo associates the
file with G10. The 198.5 A parameter page cannot acquire G10 scope from another
page or a generic shared heading. This remains an explicit regression fixture.

## Unchanged twelve-sample quality review

The deterministic first twelve English `(model, question category)` samples are
unchanged. Raw expected-page retrieval was 7/12 before the publication guard and
2/12 after it. Those are page hits, not generated-answer accuracy. The 632-question
corpus statistics use the same original golden data; no suspect question was
deleted to improve the result.

| Sample | Before / after page hit | Original source and current permission assessment |
| --- | --- | --- |
| `00506d0f0c-en` CHS2-29.9K-T4-X meter | yes / no | The manufacturer explicitly states CHINT DTSU666 compatibility. The manual's application scope also includes unknown CHS2-49.9K-T6-X, and the meter has no association to that document. Genuine source content exists; the required complete current scope is not proven. |
| `005ddc4c7d-en` BU3 certification marks | no / no | No prior hit or correctness claim. The original expected page is a generic battery-symbol explanation, which does not by itself establish this model's certification marks. |
| `0065e3e240-en` GW261.2 maximum current | yes / yes | The source columns explicitly name GW208.9 then GW261.2, with 180/180 A in the second column. The parameter fragment also names unknown GW52.2-PACK-LC-G10. Its model-heading page hit is not proof that the numeric answer fragment is authorized. |
| `009ea1c839-en` HS2 user interface | no / no | No prior hit or correctness claim; not restored in this bounded replay. |
| `00cc9d826a-en` G10 ESA maximum AC current | yes / no | Wrong variant: original parameter-page heading is G11. Its 198.5 A value is not valid G10 evidence. |
| `0121878b05-en` L260 depth of discharge | yes / yes | Original L260-OMNI section and battery fragment explicitly give 98% (single string); current model/document scope permits this numeric fragment. |
| `015253f935-en` GW30K STS warranty | yes / no | Original row genuinely says STS series / five years. Woo types this association as generic document; exact current model membership and releasable whole-table scope have not been proven. No family inference was added. |
| `015d0655fa-en` GW3K / battery compatibility | no / no | No prior hit or correctness claim. A battery technical-data page alone does not prove inverter compatibility, and the battery lacks that current document association. |
| `0172d5937a-en` GW80K ETR communication | no / no | No prior hit or correctness claim; no unproven broken-line model mapping or broad section scope was added. |
| `01dfea3e55-en` H2-30K-T3-DE warranty | yes / no | The DE variant is explicitly named on manual page 38, alongside unknown BE/standard variants; its row refers to the warranty policy. Some expected pages do not name DE. Mixed datasheet tables are not a current-only numeric-duration proof. |
| `01f767ac23-en` GW5.1 accessories | no / no | No prior hit or correctness claim; not restored in this bounded replay. |
| `0212b70d6e-en` GW61.4 BMS | yes / no | The original paragraph defines/includes a BMS, without a BMS model/brand, and mixes unknown GW92.1/GW102.4. It does not prove a current specific BMS answer. |

All seven original hits have exact document IDs/revisions, original pages and
chunk IDs in `genie-old-seven-quality.json`. The raw page-hit regression remains
disclosed. Neither seven old hits nor two new hits is presented as answer-quality
acceptance. No production or live-answer parity is claimed.

## Read-only corpus reproduction

`genie-scope-audit.json` records the final measured source, counts and source
hashes. `genie-scope-baseline.json` preserves the separately measured earlier
baseline; the replay checks the same manifest/identity snapshot hashes. The
identity fixture was generated by reading native Woo model/status records; it
is not a maintained production product list or a runtime permission fallback.

From the repository root, with the already locked Genie environment:

```sh
services/genie/.venv/bin/python docs/acceptance/2026-10-23/615/replay_genie_scope.py \
  --manifest /tmp/615-current-scope-manifest.json \
  --woo-identities /tmp/615-woo-scope-identities.json \
  --cached-index /Users/chesterjohn/de-linker-data/index/builds/20261018T173840Z/index.sqlite \
  --parsed-root /Users/chesterjohn/de-linker-data/parsed \
  --tokenizer /Users/chesterjohn/.cache/huggingface/hub/models--BAAI--bge-m3/snapshots/5617a9f61b028005a4858fdac845db406aefb181/tokenizer.json \
  --baseline-report docs/acceptance/2026-10-23/615/genie-scope-baseline.json \
  --output /tmp/615-replayed-scope.json
```

The SQLite connection is read-only. Cached Docling JSON is decoded, not parsed
from PDFs; no OCR or embedding/model provider runs. Native provenance is copied
only when every original chunk text/header/section exactly matches. This
establishes cached-source behavior, not real HTTP authority or live answers.

One normal proof build sends about 370 bounded original-text identify requests,
not one request per chunk. Two proof passes in the audit report 740. The earlier
baseline's 692 exact-label calls are not new-build calls. At the reviewed PHP
source, each identify dispatch called `Publication::manifest()` first; at the
root owner's measured three seconds per full manifest this alone is roughly
1,110 seconds. The offline replay time cannot be used as a real build budget.
Root owns endpoint performance work while preserving current authority checks.

## Normal worker local rehearsal

Use the existing private mode-0600 env and REST config, the existing assigned
service and the service's actual index root. The env supplies queue credentials,
service token, `GENIE_WP_URL`, existing embedding credentials and `LINKER_DATA` for
the reused Mac cache/build root. No launchd installation, new instance, tunnel,
port, model route or source manifest is needed for this local command:

```sh
cd services/genie
.venv/bin/python ops/install_publication_worker.py run "$PUBLICATION_ENV_FILE" \
  --rest-config "$PUBLICATION_REST_CONFIG" \
  --worker-id "$PUBLICATION_WORKER_ID" \
  --lease-seconds "$PUBLICATION_LEASE_SECONDS" \
  --loaded-url "$PUBLICATION_LOADED_URL" \
  --root "$PUBLICATION_SERVICE_INDEX_ROOT"
```

These variables are the root integration session's existing non-secret paths,
identity, measured lease and loopback URL. Credentials remain inside the private
env/config. Without `--host`, publish and loaded verification use the local
service; remote operation adds the existing SSH alias. The worker automatically
performs claim, inventory, cached parse/build, publish, process-loaded check and
acknowledgement. Read back the actual `/knowledge/loaded` response and Woo job
state. Process source/index revisions must match the claimed job and published
index, and diagnostics must remain visible. A successful command exit alone is
not complete-preparation acceptance; the safe partial product subset can load
while the acknowledged job remains pending.

Failed worker-owned generations are removed by their explicit pending journal;
only after accepted loaded/ack does retention rotate successful managed builds
to current and previous. Unrelated/shared originals and historical account files
are preserved. This worktree created no site instance, daemon, port, snapshot or
backup; its tests and bounded source fixtures remain for root review. The native
cached originals are read-only inputs and must remain available to the ongoing
root acceptance.
