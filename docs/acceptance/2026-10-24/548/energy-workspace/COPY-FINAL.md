# Customer copy disposition

English source was drafted, independently challenged against the actual model,
then corrected before native publication. The reviewed corrections include the
absence of controller-requested grid recharge, queued/retry lifecycle, actual
not-assessed equipment/country scope, final-state semantics and exact PV ratio.
The new customer controls use clear recovery actions; machine references and
hashes stay in expandable calculation details.

The separately authored formal German corpus contains 187 new entries. An
independent German reviewer required four semantic corrections and suggested two
terminology refinements; all six were applied. The final 187 entries match the
PO, compiled MO and native generated planner JSON. Existing human German remains
byte-for-byte intact as the PO prefix. Draft, adversarial findings and final
corpora are retained beside this record; neither copy review accepts the entire
planner or replaces native/browser/engineering validation.

Pre-delivery copy checks: encyclopedia context loaded; Hard Stops 1-9 checked;
Actor/Future/Weight/Duration and quote/source tests checked; humanizer pattern
removal applied without loss of factual limits. No invented product values,
service promise, payback, country release, engineering approval or automatic
grid-recharge claim was introduced. Operational field instructions and exact
formula/units/placeholders are preserved.

Hashes at copy closure:

```json
{
  "copy-draft.json": "7a847d2d61ffd1af383754962777e0db4ddd71091bfc07f121febfad91f3e452",
  "COPY-DRAFT.md": "46013c233a643beff6c9004efc10c66a05e399265d7da59e6c9a07c4b58b9052",
  "COPY-REVIEW-EN.md": "c217035ae385c58802556fb447737e61359933832be22c50bd00b4227e660f74",
  "copy-final-en.json": "68fbdcb4604d396b6e040f526ca13f742405926cd78cc307d9666e4a3deca21a",
  "copy-german-draft.json": "422baf34e9f884cc8559c1a3d32514eadd7a5117c065e035118333bfe2eabca7",
  "copy-german-final.json": "53ae563d319dcd5a9ed02930038c09196f9cbe0b9bc743d209df83d829bf9b0b",
  "COPY-REVIEW-DE.md": "56980bdda9d2b06f78a50479949e6b7113619066a8364343acdc58b75534b64a"
}
```

After copy closure, the PO trailing blank line was normalized for git whitespace validation. No message, translation, existing PO prefix or generated MO/JSON data changed; the final source pin supplies the resulting file identity.
