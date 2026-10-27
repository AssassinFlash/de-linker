# Standards review: native preparation consumers

Frozen source: `f23d841015362a03fb634f3e3565426d48ce67f2`.
Base: `83f06cafd6dbec886dd1b7ac60a0de5a799da023`.
Reviewed `git diff BASE...SOURCE` and the single consumer commit, including renamed modules, fixtures, generated assets and translations. Authority: current `/Users/chesterjohn/Documents/de-linker/AGENTS.md`, owned `CONTEXT.md`, accepted runtime ADR, native-task specification and package configuration. This review covers this consumer increment only.

## Documented-standard violation

**[P2] Deliver the unknown-start contact action in the planner's German dictionary.** In `apps/planner/src/components/energy/WeatherProgress.tsx:167–170`, the new unknown-start branch renders `__("Contact Linker", "linker-tools")`. The approved final copy, PO and MO all contain `Linker kontaktieren`, but the updated planner module dictionary `plugins/linker-tools/languages/linker-tools-de_DE_formal-cf89287c9001d7518d0d20e58c3eb721.json:1` omits this key. `Planner/Application.php:76` registers this module's translations; the German visual fixture also consumes this exact JSON. A focused check with the installed `@wordpress/i18n.createI18n` and the frozen dictionary returns English `Contact Linker`, while the adjacent heading correctly returns `Status des Wetterabrufs`. This violates current AGENTS.md §3, “英德永远同步交付,” and the 2026-10-17 German ruling at line 51. Include this source reference in the planner JSON generation and verify the German unknown-start state. PO/MO presence alone does not deliver this JavaScript string.

## Remaining review

No additional documented-standard violations or material Fowler-baseline smell findings. The isolated React/Vite runtime is expressly authorised. All 151 source hashes and seven build hashes match frozen blobs; five generated modules parse, and all 55 named imports resolve. All 58 reviewed literals occur in generated modules; the other 57 reviewed translations agree across final copy, PO, MO and planner JSON. Added-line legacy-identifier scanning found no prohibited identifiers. Copy opposition, final English and independent German acceptance are recorded.

No live service, database, browser, network or credential was accessed. No temporary runtime, worktree or backup was created. This report does not establish native integration, publication or full-goal acceptance.
