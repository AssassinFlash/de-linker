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
