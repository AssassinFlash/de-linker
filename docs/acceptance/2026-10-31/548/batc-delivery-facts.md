# BAT-C 208.9–261.2 cabinet delivery facts

This reviewed data candidate covers the complete manufacturer delivery table for
GW208.9-BAT-LC-G10 (1956), GW208.9-BAT-LCD-G10 (1957) and
GW261.2-BAT-LCD-G10 (1958). Its source is the product-linked GoodWe BAT-C
208.9–261.2 kWh User Manual, V1.0, 2026-04-03, PDF pages 34–36 (printed pages
33–35), SHA-256 `ef85dd1a58fc06e52f2dff79dda228884b412d17db7035aa45d41c57840f3f10`.
The cover lists all three models. PDF page 47 depicts the manufacturer's
four-anchor cabinet installation; that does not assess the project foundation.

The cabinet itself is the selected Woo product and is not duplicated as an
accessory. Each cabinet has fourteen unconditional delivery rows: one 50 mm²
power cable terminal; two 10 m and one 3.8 m communication cables; four
expansion bolts; three grounding terminals; one AC connector; three PIN
terminals; twelve M8 screws; four bellows joints; one flat-head screwdriver; six
pieces of fireproofing mud; twenty cable ties; one liquid-cooling drain pipe;
and one documentation set. Cable lengths are specifications of each cable,
not a total length. The manual states no putty mass or drain-pipe length.

Six further rows preserve the manual's conditions: two 25 mm² cables and two
matching terminals for ET100 or ET G3 only; one 70 mm² cable and one matching
terminal for ETR125 only; and one each of the optional positive and negative
optimizer terminal release tools. The manual describes those tools as intended
for maintenance. The report keeps these conditional quantities open until the
actual order and supplied items are confirmed; it does not assume that an ET
75/80/99.99 configuration is covered by the ET100 wording.

The plan uses the existing `_linker_installation_facts` authority, not a second
package entry for the same items. It preserves the seven previously published
interface, cable-specification and switch facts for each model and adds twenty
distinct delivery facts per model. Unconditional quantities are multiplied by
the selected whole-cabinet count; labels state the per-cabinet basis. A user
material declaration remains a separate project row. No automatic identity
match, deduction, net-purchase quantity, alternate specification or complete
BOS approval is inferred.

The existing 79 facts cover four ET products and five BAT-C products; this
candidate adds 60 facts across these three products only. The BAT-C 61.4 and 112.6 kWh products are a different family. Their separate
delivery tables and source availability are recorded below. ET delivery facts and project-dependent items remain in the existing
sources and are not re-entered by this candidate.

Use `tools/migrate/548-installation-facts.py` with `--plan
tools/migrate/548-batc-delivery.json` for a read-only preview and a new private
receipt. Preview checks exact Woo model/revision and document identity; stale
product or document revisions must be reviewed and refreshed against the same
original bytes before applying. Apply, verify and rollback consume the same
receipt without a plan. Then preview `tools/migrate/548-controller-facts.py`
with `--plan tools/migrate/548-batc-sales-unit.json` against the resulting
source revision and use its separate receipt to apply and verify the sourced
`battery_system` sales unit. Woo identifies these three simple products as
cabinets; the linked manual page 3 specifies four, four and five battery packs
respectively. Existing product figures and evidence bindings are preserved.
Rollback is in reverse order: sales-unit receipt first, delivery-facts receipt
second. The existing native transaction, protected metadata, source readback
and rollback checks remain authoritative. Preparing and locally testing this
candidate did not write production.

An isolated local native test applied both reviewed plans, loaded the resulting
engineering feed and selected two 1956 cabinets with four packs each through
the normal project gateway. The equipment worker returned two `battery_system`
units; same-revision English and German report PDFs and materials CSVs contained
the manufacturer's included expansion bolts. The English CSV readback recorded
`Expansion bolt (4 per cabinet)` as `8 pc`. The owned local project, session,
release and publication changes were rolled back; existing local files were
unchanged. This proves the selected cabinet and its supplied materials flow to
the report; it does not establish site installation suitability or an automatic
net procurement quantity.

The first local run's EN PDF/CSV SHA-256 values were
`8bfa1348bd5fbf457c9b787861a4b441d57a66952d76f56d3d7867665ff68ba9` /
`fa863b5cedef9c9091daa47e7cf7a384164c929f8ba829f5573d2408d0a1ff1e`;
the DE PDF/CSV values were
`e1ab28ee7d7ff8cc54a5e743e258bc2c2c0e8cb6d4dbd46013d21fa263f64cbe` /
`9448233df4840c5f5dfc6f4427f0a944629c569cb91e909014b4f787f62c3721`.
The focused CSV quantity readback used a separate temporary local project and
its CSV SHA-256 was
`e5edca3086701b6724b73124f29b3e4921857100b543ca5e4a2ae35e38f51afd`.

## Production readback for the large cabinets

On 2026-11-02 Woo, both engineering readers and Genie epoch 66 loaded source
`dd9ba12fc54ea7f3b38eb99d7c8273fbd51e2b91a1a27a8e59fd6ba400d4c29a`.
Production guest project `90e7c146419b454fa295b45c21ee5004` revision 1
selected two GW208.9-BAT-LC-G10 cabinets. The downloaded English report PDF
and materials CSV both give eight expansion bolts. The CSV identifies four
per cabinet, PDF page 35 and the included-equipment category.

## BAT-C 61.4 and 112.6: locally verified source candidate

The reviewed, source-neutral delivery rows for products 1954 and 1955 are in
`tools/migrate/548-batc-small-delivery-source.json`. They cite the 87-page
[GoodWe manual, V1.0, 2026-10-10](https://admin.goodwe.com/En/Api/downloadFile?id=4626&mid=60&type=2),
SHA-256 `c29cbf257d51559ef53f5da36a46ca10b4e5738fbd4a0d06fd74fbaff4a7fcb7`.
PDF pages 33–35 were checked visually and against the text. The five and ten
pack-interconnection harnesses per respective cabinet are separate from the
six and eleven packs in the respective cabinet. The two ET100 adapter mounting
brackets remain conditional. Cable lengths, package internals, quantities to
purchase and installation suitability are not inferred.

Both products already expose `sales_unit_kind=battery_system` and the six/eleven
fixed pack counts from their existing source in the current Woo engineering
feed, so the candidate does not rewrite those facts. In an isolated p548 claim,
the manual bytes were temporarily associated with each Woo product, the five
pre-existing reviewed facts were preserved and nineteen supplied-item facts
added per product. The actual loaded engineering source acknowledged both
products. Two cabinets of each model passed the native equipment worker, and
same-revision English and German reports, PDF assets and material CSV assets
were generated. An actual English CSV readback for product 1954 showed the
quantity **8**, unit **pc**, `Expansion anchor (4 per cabinet)`, the original
PDF page 33 and `Included with the equipment`. The second CSV readback was not
completed: the temporary verifier incorrectly expected quantity and unit in
one CSV cell, while the native CSV has separate columns. Therefore the 1955
material quantities and the complete rendered PDF content are not claimed as
read back. The original metadata and publication options were restored, the
two temporary product associations and manual copy removed, and native claim
cleanup verified 1,710 original workspace files unchanged and both ports free.

The manufacturer's official URL is the public link. Its text prohibits
unauthorized public copying or upload; this candidate does not authorize a
public mirror. Current `DocumentFiles::locate` requires a same-site uploads PDF
and rejects an external host or query string, so the official URL cannot yet
be the directly bound document for these facts. The source-neutral data above
is an evidence candidate only: production Woo publication and consumer use
require a supported, byte-verified original-link binding with the existing
source revision and withdrawal guarantees. No production product was changed.

## A hosted original for the 112.6 kWh cabinet

The existing [ET user manual V1.2](https://de-linker.com/wp-content/uploads/2026/10/GW_ET-100kW_User-Manual-EN_V1.2.pdf),
SHA-256 `0ef4b1ccdcc418e3ca8de31194b3d9e2969be39aa739ffa0ca1f038fcfac6615`,
PDF pages 100–102 (printed 99–101), lists the BAT 92.1–112.6 kWh delivery
items and explicitly identifies `GW112.6-BAT-AC-G10` with ten inter-pack
harnesses. Eighteen items agree with the separately reviewed BAT-C 60–112
manual. The latter's ET100-only adapter brackets are absent from this ET table
and are not imported. The ET table does not list `GW61.4-BAT-AC-G10`; no
association or package claim is inferred for product 1954.

The checked association plan `548-batc-112-manual.json` adds this already
hosted manual to product 1955 only. The checked facts plan
`548-batc-112-delivery.json` preserves its five existing facts and adds eighteen
items using the ET manual's actual page citations. Sales-unit data remain as
currently maintained. A private source refresh is required after the document
association because that association changes the product revision.

In p548 the native association preview/apply, facts preview/apply, engineering
feed and product-download readback succeeded: 1955 had 23 facts and the manual,
and 1954 was not associated. Facts and then association were rolled back; the
original source revision `e1773a35f189b2eec9267b9f757a55c60bd996e62df9e5d1812d90f0b8c337d4`
and publication options were restored. The previous two-cabinet local worker
and report results were not rerun. An in-memory scope compilation using the
existing epoch66 corpus's 623 original ET chunks, the local Woo model statuses
and a hypothetical 1955 association admitted zero passages for 1955; it does
not authorize unrelated ET passages or claim that Genie can answer this table.
No vector build or production write was performed.

For the single production data window, after the normal verified full backup,
use private 0600 paths for `DOC_RECEIPT`, `FACT_RECEIPT` and `PRIVATE_PLAN`:

```sh
python tools/migrate/548-controller-facts.py --production preview --plan tools/migrate/548-batc-112-manual.json --receipt "$DOC_RECEIPT"
python tools/migrate/548-controller-facts.py --production apply --receipt "$DOC_RECEIPT"
python tools/migrate/548-controller-facts.py --production verify --receipt "$DOC_RECEIPT"
install -m 600 tools/migrate/548-batc-112-delivery.json "$PRIVATE_PLAN"
python tools/migrate/548-installation-facts.py --production refresh --plan "$PRIVATE_PLAN" --write
python tools/migrate/548-installation-facts.py --production preview --plan "$PRIVATE_PLAN" --receipt "$FACT_RECEIPT"
python tools/migrate/548-installation-facts.py --production apply --receipt "$FACT_RECEIPT"
python tools/migrate/548-installation-facts.py --production verify --receipt "$FACT_RECEIPT"
```

Review that the facts receipt preserves the current five facts and adds only
the eighteen reviewed rows before applying it. To roll back, use the facts
receipt first, then the association receipt; verify each restored state and
reconcile the matching Woo/knowledge publication before retiring receipts.
