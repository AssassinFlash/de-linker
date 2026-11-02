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
candidate adds 60 facts across these three products only. The BAT-C 61.4 and
112.6 kWh products are a different family. Their linked two-page quick guide
does not establish a complete, model-specific delivery list; the ET manual's
112.6 kWh table cannot be extended to the 61.4 kWh model. A manufacturer
packing list or equivalent product-linked original is still needed for that
family. ET delivery facts and project-dependent items remain in the existing
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
