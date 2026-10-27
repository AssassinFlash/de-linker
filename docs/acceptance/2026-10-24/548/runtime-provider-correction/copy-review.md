# Copy review: weather acquisition status

Scope: two operational status messages for European installers and EPCs.
Dimension: the current weather task's progress and terminal result. The first
appears after local work begins, before the complete original passes validation;
the second appears after a failed/cancelled task with no retained validated
capture. Existing waiting, captured and Source ready wording is outside this
copy change. Model limitations remain unchanged.

Reviewed with `linker-copywriting` Hard Stops and its required
`references/industry-and-linker-encyclopedia.md`, `references/anti-patterns.md`
and `references/positive-examples.md`, after the `humanizer` sentence checks.
Current owner instructions and repository terminology take precedence over
older reference examples. The source name comes from the supplied runtime
contract; no additional product or source capability is inferred. Read-only UI
inspection confirmed the two strings' intended locations. No external lookup
was performed.

## Draft

1. EN: Weather data is being downloaded from JRC PVGIS and checked.

   Independent DE draft: Wetterdaten werden von JRC PVGIS heruntergeladen und
   geprüft.

2. EN: Weather preparation has ended without a validated weather source.

   Independent DE draft: Die Wettervorbereitung ist beendet. Es liegt keine
   validierte Wetterquelle vor.

## Opposition

- **Progress versus successful validation:** message 1 must describe the active
  download/checking phase. Its present progressive does not claim that the
  original is already complete, valid, saved, selected or ready for calculation.
  Neither language promises completion, timing or meteorological accuracy.
- **Borrowed credibility / SOP bragging mutation test:** JRC PVGIS identifies
  the weather source. There is no prestige adjective, quality badge, authority
  endorsement or claim of engineering approval. Checking is the operation whose
  progress this row reports, rather than a marketing differentiator.
- **Terminal scope:** message 2 must cover failure and cancellation without
  inventing a reason, implying a successful source, or saying that older saved
  sources disappeared. The German draft's separate existential sentence could
  sound broader than the current task. Tie the absence of a validated source
  to the concluded preparation in one sentence.
- **Naturalness and restraint:** the neutral passive fits an application status.
  Both English lines are sound and remain unchanged. German uses the existing
  terms Wettervorbereitung and Wetterquelle, with formal register and no du
  address. Validiert refers to the data-validation state, without adding an
  accuracy, equipment-suitability or country-release promise.

## Final

1. EN: Weather data is being downloaded from JRC PVGIS and checked.

   DE: Wetterdaten werden von JRC PVGIS heruntergeladen und geprüft.

2. EN: Weather preparation has ended without a validated weather source.

   DE: Die Wettervorbereitung wurde ohne validierte Wetterquelle beendet.

Copy verdict: accepted for these two visibility contracts. No further wording
change is required. This verdict concerns copy, not runtime installation or
full product acceptance. The machine-readable final text is `copy-final.json`.

## Pre-delivery

- [x] Encyclopedia loaded (non-PDP): one dimension, tool status; no new category words.
- [x] Hard Stops 1–9 hold on every visible line.
- [x] Actor: no second-person imperative that assigns the reader a task.
- [x] Future: no invented customer trajectory or We know you wording.
- [x] Weight: no small real slice written as the whole offer.
- [x] Duration: no ongoing or long after claim requiring a continuing action.
- [x] No slogan formulas (From X to Y, One X. One Y., Instead of).
- [x] No banned brand on this surface; JRC PVGIS is factual source attribution.
- [x] Quotes: source gate holds; no testimonial or attributed customer speech.

Only this record and `copy-final.json` were authored. Source, catalogues, native
DB/processes and frozen historical Standards evidence were left untouched.
