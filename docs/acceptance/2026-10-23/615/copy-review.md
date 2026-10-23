# Publication-state wording

Scope: Genie identification-only handoff after Woo confirms a supplied model unavailable, or after an uploaded file cannot be tied to a currently published product. Rules: [confirmed publication behavior](https://github.com/AssassinFlash/de-linker/issues/609).

Draft: “I can identify the model in your file. It is not available for current product advice or system selection. Please contact the Linker team at sales@de-linker.com.” German draft independently states recognition, current-use limitation and the existing team address.

Adversarial concerns for final full-diff review: a typed model is not necessarily a file; recognition must not imply the file's ratings remain usable; “not available” must not be mistaken for stock quantity/status; do not claim current technical advice or compatibility; an unknown file must not falsely claim that its model has been identified. Historical text is preserved, while the new answer has no current technical facts or next-step selection action.

The first revision changed “in your file” to “you supplied” for typed and attached models. Final sentences are owned in `services/genie/src/linker_genie/publication_copy.py`; the English and German variants must be read as part of the Spec/Standards full-diff review. This record is preparation for that review, **not a fabricated independent approval**.


Final candidates for the independent review:

- Known unavailable model EN: “This model is outside our current product range. I can help identify it. For technical advice or system selection, please contact the Linker team at sales@de-linker.com.”
- Known unavailable model DE: “Dieses Modell gehört derzeit nicht zu unserem Produktangebot. Ich kann Ihnen bei der Identifizierung helfen. Für technische Beratung oder die Systemauswahl wenden Sie sich bitte an das Linker-Team: sales@de-linker.com.”
- Unverified file EN: “I could not verify a current product for this file. Please contact the Linker team at sales@de-linker.com.”
- Unverified file DE: “Ich konnte dieser Datei kein aktuell angebotenes Produkt zuordnen. Bitte wenden Sie sich an das Linker-Team: sales@de-linker.com.”

The unavailable-model sentence distinguishes product-range permission from stock. The unverified-file branch makes no identification claim. The code removes technical ratings and text before recording a fresh identification-only reading, and supplies no technical facts/actions to the model for that turn.

## Signed product-list actions

Dimension: the next current product-list action after a previously displayed
Genie list has lost its current permission. This is a tool outcome, with no
claim about inventory quantity, compatibility, warranty or delivery.

Initial draft: “Ask Genie again before saving or adding these products.”
Adversarial reading found the imperative assigned work to the visitor and the
engineering alternative “new calculation” incorrectly described ordinary
product cards. The final candidate instead names Genie's required check:

- EN: “Genie needs to check this product list again before it can be saved or added.”
- DE, independently written: “Diese Produktliste muss Genie vor dem Speichern oder Hinzufügen erneut prüfen.”

The root integration owner accepted this candidate on 2026-10-23 and owns its
PO/MO/JSON extraction. It must still appear in the complete Spec/Standards review.
No statement implies that withdrawal is merely out of stock.

The definite retry state now uses the existing “Not added. Try again.” only
when the action is known not to have committed. Unknown POST/network outcomes
retain the common reviewed “Addition not confirmed.” or the full common
sentence acknowledging the draft may already contain these products. Saving
with an unknown acknowledgement uses the existing translated resource outcome
“The request status could not be confirmed. Please check before sending it
again.” The historical account record is preserved in all those cases.

Pre-delivery:

- [x] Encyclopedia loaded (non-PDP): one tool-action dimension; existing product/list vocabulary.
- [x] Hard Stops 1–9 hold on the new visible sentence.
- [x] Actor: Genie performs the necessary check; no new visitor homework.
- [x] Future: no invented customer trajectory.
- [x] Weight: an action refusal is not promoted to a service claim.
- [x] Duration: no continuing-service language.
- [x] No slogan formulas.
- [x] No banned brand in new customer copy.
- [x] No invented quotes.
