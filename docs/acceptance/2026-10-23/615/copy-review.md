# Publication-state wording

Scope: Genie identification-only handoff after Woo confirms a supplied model unavailable, or after an uploaded file cannot be tied to a currently published product. Rules: [confirmed publication behavior](https://github.com/AssassinFlash/de-linker/issues/609).

Draft: “I can identify the model in your file. It is not available for current product advice or system selection. Please contact the Linker team at sales@de-linker.com.” German draft independently states recognition, current-use limitation and the existing team address.

Adversarial concerns for final full-diff review: a typed model is not necessarily a file; recognition must not imply the file's ratings remain usable; “not available” must not be mistaken for stock quantity/status; do not claim current technical advice or compatibility; an unknown file must not falsely claim that its model has been identified. Historical text is preserved, while the new answer has no current technical facts or next-step selection action.

The first revision changed “in your file” to “you supplied” for typed and attached models. Final sentences are owned in `services/genie/src/linker_genie/publication_copy.py`; the English and German variants must be read as part of the Spec/Standards full-diff review. This record is preparation for that review, **not a fabricated independent approval**.
