# Solar settings copy review, 2026-10-24

Independent adversarial copy review of the increment after fixed base `367640fcf09eba92eb77b8e61aaedaa6957cdd7b`. The reviewed surface is `WeatherForm.tsx`, `WeatherSetup.tsx`, `EnergyWorkspace.tsx`, `EnergyError.tsx` and `ScenarioNumber.tsx`, plus the four new integer messages in `NumberField.tsx`. This records copy approval for the weather input workflow. It does not accept the complete unified Solution Configurator, native acquisition, installation, country or equipment support, reports, commerce or production behavior.

The inventory contains **98 unique gettext literals**: 31 have new independently written German, while 67 retain the existing formal German from `plugins/linker-tools/languages/linker-tools-de_DE_formal.po`. The JSON retains every exact original English literal in `msgid`; `approved_en` is the source wording to publish and `de` its approved German. Twelve original English literals require replacement. `ScenarioNumber.tsx` introduces no literal of its own. PVGIS-SARAH3, PVGIS-ERA5, ERA5, UTC and WGS 84 remain identifiers, not invented product names.

The factual basis is the retained [weather/model evidence](../../../../research/2026-10-24-pv-generation/WEATHER-AND-MODELS.md), [weather acquisition contract](../../../../specs/548-weather-acquisition.md), [native task contract](../../../../specs/548-native-solar-tasks.md), the exported weather schema and `solarSetup.ts`. Review followed the current main-repository `AGENTS.md`, the Linker copywriting Hard Stops, the non-PDP encyclopedia and the anti-pattern/positive references, with the humanizer sentence checks. Current project rulings take precedence over older vocabulary and product boundaries in the skill references. No fresh external factual research was needed.

The added product dimension is the explicit weather basis for later PV and energy calculations. Linker's system-level identity remains Solution Configurator / Lösungskonfigurator; this form makes no map-only identity claim and does not portray a returned weather source as an entire system assessment. Provider attribution belongs beside the weather source. It supplies neither an equipment release nor an accuracy promise.

The implementation's original strings were the initial draft. The opposition and approved disposition are recorded below; the JSON contains the complete final text, including unchanged literals.

| Initial draft | Opposition | Approved final disposition |
| --- | --- | --- |
| “PVGIS supplies a typical meteorological year…” | A novice cannot tell whether this means one historical year or a forecast. “Interpretation” hides the actual time handling. | Explain representative months from the source period; name returned databases, selected months and timestamp handling. No actual-year generation promise. |
| “Use roof location” and the coordinates explanation | The button copies an existing reference point; it does not find, geocode or verify a roof. | “Use roof coordinates.” Retain WGS 84 and explain that a postcode alone does not locate the roof. |
| “The available source years depend…” | Source years and the later synthetic year could be mistaken for the same choice. | State that PVGIS selects representative months from the source period. Require whole calendar years without inventing a four-digit restriction or universal coverage period. |
| “The TMY service chooses its radiation database…” | A database dropdown commonly means the application selects the provider's database. TMY is unexplained shorthand here. | Name PVGIS, say it chooses the database, and explicitly explain that this field checks that choice without changing it. Keep the ERA5 meteorological requirement. |
| “Calculation time axis” and the long axis explanation | The heading is implementation language. The forecast limit and original source dates are necessary facts. | Heading “Calculation year.” Explain the shared UTC timeline, preserve the original source dates and provider irradiance offset, and retain the forecast limit. “Synthetic calculation year” remains the established field term. |
| “Preparing these settings only changes…” | Preparation, saving, requesting and selecting are different operations. A novice needs their order. | Preparation updates the open draft; Save project records it before the request; selecting the returned source remains separate. Existing saved-revision notices retain approved translations. |
| “Acquire weather for saved inputs” | “Acquire” sounds like an immediate result and is less familiar than the action the button starts. | “Request weather for saved inputs.” No implication that clicking guarantees a usable result. |
| Weather status reused “a new calculation” | A weather request retrieves a source and must not be described as an energy calculation. | Add “Save project records these settings before a weather request can start.” and “A weather request uses saved input revision %d.” Both English drafts are approved unchanged, with independent formal German. Keep the earlier calculation strings for the scenario surface. |
| The broad incomplete-settings and leap-year errors | “Whole calculation year” is awkward. The model interval count needs an ordinary explanation. | Name the required coordinate, year, database and horizon inputs. Require a non-leap calculation year and state 8,760 hourly intervals. |
| Decimal guidance under year fields | Decimal instructions conflict with whole-year inputs; one broad preparation error gives poor recovery guidance. | The implementer added integer validation, numeric input mode and four dedicated messages. These are reviewed and included. The admissible range remains 1–9998; provider availability is separate. |

The terrain-horizon limitation survives unchanged in English and is independently written in German: nearby buildings, trees and roof obstacles remain outside it. This is a necessary model boundary. Removing it would change the customer's interpretation of the result. The source-read error now names weather settings, while preserving access to saved inputs and task history. No copy offers payback, financial returns, near-shading assessment, bankable yield, manufacturer suitability or country release.

German follows the established formal register and existing interface vocabulary. “Offene Eingaben” identifies editable project inputs and avoids using the commerce term “Lösungsentwurf” for this form. The German descriptions were written for their function rather than copied sentence by sentence from English. Database names and all `%d`, `%s`, `%1$s` and `%2$s` placeholders retain their exact identity.

Pre-delivery checklist:

- [x] Initial source draft, opposition and final wording are recorded; all 98 literals have final EN and DE.
- [x] Encyclopedia loaded; the added dimension is the weather basis for later calculations, not a new offer or invented tool name.
- [x] Hard Stops 1–9 hold at the appropriate depth; no borrowed credibility, defensive company claim, fabricated logistics or reassurance intensifier.
- [x] Actor: input instructions and action labels describe required application operations. They are not customer homework used as marketing body copy.
- [x] Future, Weight and Duration: no invented buyer trajectory, inflated component claim or unsupported continuing service.
- [x] No slogan formula, fabricated quotation, banned equipment brand, em dash or en dash in final public copy.
- [x] Source period, synthetic year, provider database validation, terrain limit, draft/save/request/selection boundaries and request uncertainty remain distinct.
- [x] Four integer messages preserve range placeholders; existing decimal behavior stays the default.
- [x] JSON parses, original keys are unique, required source literals are covered, placeholders match and existing approved German is preserved for reused text.

**Disposition: final copy approved for this increment, subject to applying the 12 English replacements and the corresponding German entries.** This is source-level copy review. Rendered EN/DE at 1440/390, native requests, returned-source selection, saving, deployment and production readback require their own evidence. No runtime or production action was performed by this reviewer. Only the two owned copy artifacts were created; no instance, snapshot, dependency tree or temporary worktree was added.
