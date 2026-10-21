# Current Genie artifacts and native product entry

## Trigger and result

A product link added an item at `/proforma-request/?add-to-cart=ID`. Because the successful command remained in the address, reload and Woo undo refresh could add it again. The native successful-add redirect now consumes that command before rendering the current-language inquiry page, preserving any earlier explicit redirect. The real-entry regression follows the product link without normalizing its URL, edits quantity to two, removes/undoes, reloads, and finally removes by zero while retaining an unsent message. It submits no inquiry.

Restoring a German Genie answer on an English page mixed current English actions with German stored price/document copy. Historical approved amounts could also outlive current authority. Workspace, dock and homepage now share a current-language document formatter and refresh historical prices through the existing read-only product authority. Missing, contradictory, failed or timed-out authority clears the old amount. Live prices remain service-filled; historical dialogue stays unchanged. Shared PDFs respect an explicit cited product owner; unknown metadata uses the actual filename. The design and copy review is recorded in design-and-copy-review.md.

## Visual scope

Only expanded Genie cards change in WindPress. A single desktop homepage result occupies the answer width with a 120px square image and existing 34rem reading measure. The 400px dock reuses the established phone card geometry so a desktop viewport does not force its 120px image into a narrow panel. Desktop multi-card answers keep their existing columns and align the action areas at the bottom of each equal-height card. Full titles, native action states, phone layouts and the unopened homepage retain their behavior.

## Evidence and review

- Native entry: the original URL assertion failed before the change; EN/DE × 1440/390 now pass the actual add → quantity → remove → undo → reload → zero chain. PHP native entry tests pass 10 tests / 19 assertions. The final combined native draft/inquiry/actual-entry run passes all 12 browser cases.
- Genie/hero: all 270 unit cases pass. Boundary regressions cover all history entry points, late refresh versus a new ask, strict current permissions, shared PDFs, stuck headers/body and a valid answer completing before its independent metadata budget.
- Browser fixtures: workspace/homepage/dock × EN/DE × 1440/390 cover restore → fresh fixture response → reload. Two extra desktop EN/DE fixtures load four real product models and check aligned Add and Save actions. Only history/turn responses are deterministic fixtures; product/document/commerce reads use real local WordPress. No model or email is called by these cases.
- Independent Spec and Standards reviews pass the PHP/native entry and TypeScript changes. Each CSS increment is separately reviewed; final build manifests match sources and the complete `just check` passes. Official local WindPress compilation and rendered geometry are checked separately.

## Publication boundary

Source, local fixture and CI evidence do not establish production behavior. The native WordPress deployment requires a local database snapshot and retained previous runtime, official WindPress regeneration, deployment readback, fresh guest EN/DE desktop/phone entry journeys and restored-card inspection. These results are recorded alongside this file after publication. Full-site coverage remains open in ../full-site/GOAL.md; this batch closes only its proven defects.
