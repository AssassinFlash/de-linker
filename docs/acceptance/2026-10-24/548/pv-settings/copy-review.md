# Independent PV-settings copy review

Date: 2026-10-24. Scope: the 71 initial strings in `copy-draft.json`, plus the two explicitly added strings for an unmatched module specification and invalid coefficient document reference. The complete 73-entry disposition is in `copy-final.json`: `en` preserves the original key, `final_en` is the approved English, and `de` is independently written German. No runtime code or language catalog was edited by this reviewer.

This is a technical input surface for a named, uniform and unshaded PV reference model. Its added dimension is **Tools: defining a reproducible roof-based PV scenario and carrying its saved inputs into calculation history**. It does not advertise equipment suitability, country approval, near-shading calculation, or completed full-system engineering.

## Instructions and evidence read

Applied `linker-copywriting/SKILL.md`, the shared `humanizer/SKILL.md`, and the required industry encyclopedia, anti-pattern and positive-example references. Technical density is appropriate inside these model controls; merchant slogans and third-party example claims were not copied. The encyclopedia's older product names, commercial process and limits on which tools Linker may build conflict with current owner instructions. Current project instructions and the approved unified-planner specifications govern this review; the older reference supplied language and mutation checks only.

Read the current `PvForm`, `PvModuleParameters`, `PvArrayParameters`, `PvConverterParameters`, `PvSetup`, `EnergyError`, `ScenarioNumber`, `NumberField` and locale-explicit decimal parser. Checked the actual `pv-generation.schema.json`, `solarSetup.ts`, engine PV parameter and physics modules, `548-pv-generation.md` and the retained `WEATHER-AND-MODELS.md`. The installed, pinned pvlib 0.16.1 `temperature.sapm_cell` documentation and equations confirm the wind-height and reference-irradiance meanings. No new external research or acquisition was needed.

## Initial copy, opposition and approved result

| Initial wording or behavior | Independent opposition | Approved result |
| --- | --- | --- |
| “Roof-to-PV model” | An invented connective label adds no information about the actual result. | “PV generation model”; German “PV-Ertragsmodell”. |
| Initial reference-model introduction | “Uniform” must not imply identical irradiance across differently oriented arrays. Scope must travel with this reference calculation. | English names a uniform, unshaded **array** model implemented with pvlib. German explicitly applies uniform irradiance within each Modulfeld. Both preserve typical-year weather and separate shading, string, equipment and country assessment. |
| Layout update and empty sections | Layout reconciliation can remove stale entries; it must not look like model selection, evidence acquisition or automatic group design. | The update description says matching parameters survive, new fields are empty, inactive entries are removed, and new physical values/group assignments are not supplied. |
| “DC maximum power before one shared conversion curve” | The actual sum is DC after declared array losses. Independent MPPT is an assumption about each array; this is not a released physical inverter configuration. | The helper names DC after declared losses, a shared PVWatts curve and AC limit, one group per array, and independent tracking per array. String planning and real inverter suitability remain separate. |
| Power temperature coefficient and `−0.29` example | The field uses percentage per degree but stores a per-degree fraction. A Unicode minus is rejected by the real decimal parser; a decimal point is rejected in German. | “Temperature coefficient of maximum power”; the explanation retains the 25 °C reference. Enterable examples are ASCII `-0.29` in English and `-0,29` in German. No coefficient is assigned to an unknown module. |
| “Temperature-coefficient evidence” | Selecting a source kind is not document verification. | “Temperature-coefficient source”. The document helper says a URL, checksum and page reference are recorded without downloading or verifying the document. |
| “Reference curve efficiency” and DC reference power | The curve reference must not be confused with array STC power or a hardware port limit. | “PVWatts reference efficiency”. The helper states the implemented cap relation, reference DC power × nominal efficiency, with the exact positive/percentage bounds. |
| “Soiling/DC wiring/DC mismatch transmission” | “Transmission” is particularly obscure for an electrical-power multiplier and invites loss-versus-retained inversion. | Optical and electrical labels explicitly name the retained irradiance or DC power. The explanatory text distinguishes reflected albedo from the remaining retained percentage factors; 98% means a 2% reduction. |
| “Cell-to-module temperature difference ΔT” | SAPM scales ΔT by irradiance/reference irradiance. The coefficient is not a constant instantaneous temperature difference. | “Cell-to-module ΔT at 1000 W/m²”; German also names the reference. SAPM help retains incident plane irradiance, air temperature, 10 m wind and construction/mounting dependence. No preset is implied. |
| Prepare, save and start messages | Preparation must not imply saving, native acceptance or a started job. A saved weather identity is not a meteorological accuracy guarantee. | Preparation stays a distinct draft state. The save text records the roof/model/weather prerequisite; the start button names saved inputs. Weather text describes source-record/location checks only. |
| Generic incomplete-model error | Fraction bounds, efficiency bounds and positive reference power are not interchangeable. | The final message separates closed 0–100% factors, efficiencies greater than 0% and at most 100%, and strictly positive DC reference power. These are bounds of this named model, not universal equipment limits. |
| New coefficient-reference error | A 64-character arbitrary string is insufficient, and “credential-free” is internal shorthand. | The final message names an HTTP/HTTPS URL without login credentials, exactly 64 checksum characters using `0-9` and `a-f`, and a positive whole page number. |

The five strings already present in the approved catalog are reused unchanged in both languages: “User-declared values”, “Referenced datasheet”, “Source document URL”, “Source document SHA-256”, and “Source page”. References to “Save project”, “Saved calculations” and “Roof design” follow the existing German “Projekt speichern”, “Gespeicherte Berechnungen” and “Dachplanung”. The three `%d` placeholders remain unchanged.

German was written for the control's meaning and workflow, rather than translated line by line. It uses Modul, Modulfeld, Dachbelegung, Nennwirkungsgrad, Einstrahlung and Nordbezug consistently. No `du`, `dein` or informal imperative is used. Technical declarations and action-button infinitives fit the formal Sie register without adding unnecessary personal address. English and German describe the same numerical bounds and scope.

## Non-copy findings and disposition

1. The source displayed an internal `module_spec_id` as the fallback heading for a module missing from the current geometry. This was reported to the implementer, who introduced the separately reviewed “Module specification outside the current layout” key. Copy acceptance does not substitute for the implementer's runtime verification of that fallback.
2. Manual SHA-256 entry is an advanced source-reference mechanism, not usable novice document acquisition. The text accurately describes that mechanism and keeps the complete source reference requirement. Document intake, source discovery, checked defaults and progressive guidance remain requirements of the full unified-planner goal. This review does not claim them delivered or waive them.
3. The SAPM reference-ΔT clarification and parseable gamma examples are scientific/usability corrections captured in the approved text, not cosmetic rewrites.

## Pre-delivery

- [x] Encyclopedia loaded (non-PDP): one new dimension; category words attested. Model-specific scientific terms are supported by the retained primary-source/model evidence.
- [x] Hard Stops 1–9 hold on every visible line. The form's functional controls and necessary field requirements are assessed as controls, not merchant claims or customer-homework marketing.
- [x] Actor: no second-person imperative that assigns the reader a task in body copy.
- [x] Future: no invented customer trajectory or “We know you…” claim.
- [x] Weight: no small real slice written as the whole offer. This form is not presented as a complete engineered solution.
- [x] Duration: no “ongoing” or “long after” badge without a continuing action.
- [x] No slogan formulas (“From X to Y”, “One X. One Y.”, “Instead of”).
- [x] No banned brand on this surface. Scientific model/software names identify the calculation, not borrowed prestige.
- [x] Quotes: source gate satisfied; no testimonial or attributed customer speech was created.
- [x] Humanizer pass: no em/en dashes, forced three-part slogans, inflated credibility, fake alternatives, generic endings or chat residue. Scientific scope statements and real parameter distinctions are preserved.
- [x] Scientific pass: gamma units/reference, retained factors, SAPM wind/reference ΔT, group sum/clipping, positive/efficiency bounds and saved-input gating match the actual model.
- [x] German pass: independently composed formal German, existing UI terminology retained, number examples use decimal comma, no English-only framework/debug terms or internal IDs introduced.
- [x] Artifact pass: all 73 original keys are represented exactly once; five existing catalog translations and all integer placeholders are preserved. Integration into catalogs and rendered EN/DE layouts remains the implementer's verification responsibility.

Approved for integration with the stated reference-model scope. This review approves the text and identifies its remaining product boundaries; it is not native-runtime, visual, equipment, country or production acceptance.

## Rendered count-label closure

Actual browser observation showed the initial sentence rendering as “1 active arrays.” The original opposition record above is retained. The entry with original key `Current roof layout: %d active arrays.` is now independently approved as:

- English: `Active arrays in the current roof layout: %d.`
- German: `Aktive Modulfelder in der aktuellen Dachbelegung: %d.`

This names the counted category before the value, so zero, one and multiple arrays do not create a singular/plural sentence mismatch. It preserves the original `%d`, the active-layout meaning and the existing German Modulfeld terminology. All 73 original keys remain unchanged; no other approved text was altered. Runtime/catalog integration and the separate percentage-rounding correction are outside this review-file change.

## German mobile step-label closure

Independently inspected the actual 390-width capture `pv-de-390-negative-error.jpg`. In the three-column step navigation, “Leistungsumwandlung” breaks mid-word as “Leistungsumwand” / “lung”. The original `Power conversion` entry now retains its English text and uses **“Umwandlung”** in German for this step label only.

“Umwandlung” is clear in the surrounding PV-model workflow and avoids an arbitrary word break in the narrow navigation column. The detailed section heading remains “Gemeinsame Leistungsumwandlung”, and its explanation retains the full electrical meaning. This is a contextual navigation abbreviation, not a renamed model or reduced scope. Only this entry's `de` value changed; all 73 original keys, every other approved entry and the prior review record remain unchanged. No source, catalog or CSS was edited by this reviewer.
