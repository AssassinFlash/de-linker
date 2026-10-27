# Preparation source-basis copy review

2026-10-24. English copy final for the nine visible literals in `PreparationBasis.tsx`; independent formal-German drafts are in [source-copy-final.json](source-copy-final.json). German final acceptance remains with the integrating agent. This review writes only these two new artifacts.

## Evidence and scope

Applied the current main-repo AGENTS rules, the already-loaded linker-copywriting skill and required references, and the humanizer's pattern-removal rules. Read the current `PreparationBasis.tsx`, `data/preparationBasis.ts`, the source-presentation case in `data/preparationProtocol.test.ts`, relevant `tests/fixtures/preparation-flow.json` data, root `CONTEXT.md` planning terms and existing formal-German `.po` terms. No code-review reports, external services or runtime were used.

The added dimension is the actual weather/model basis of the prepared source. `readPreparationWeather` joins an owned weather asset to the task's frozen `weather.raw`/`weather.metadata` pins, or to the published weather result. It verifies that the request and declared interpretation match. The visible database fields therefore describe the retained source used by that task, rather than the current editable project or a guessed provider default. PV settings come from the historical project's `pv_generation` input.

The fixture distinguishes source-request years 2005/2023 from synthetic calculation year 2023. It records stitched typical months, original solar-date interpretation, modelled PV output and reconstructed interval averages. These are fixture facts used to check wording; the copy does not hardcode those numbers or database values. The source-reader test checks the actual database projection and rejects changed metadata pins and a foreign project. This review inspected that test but did not run it or infer native acceptance from it.

Linker's by Linker / von Linker attribution continues to describe the complete system. This surface attributes the retained weather source and explains its interpretation. It adds no claim of measured PV, one observed historical weather year, a common model across all arrays, shading analysis, equipment release or country approval. Source/database identifiers and technical JSON stay within their factual source role and deep expandable records. The disclosure does not promise a download of the full raw provider response.

Reviewed source SHA-256: `PreparationBasis.tsx` = `448315d9d9a001a11eca591e38c2e1cca50127dacb3f9648189da9bec7b7c793`; `data/preparationBasis.ts` = `1127a9f2c75b3dfdc3e11ef23c8d8e9911602fed7f65fae0770d39a267a39d12`.

## Draft, opposition and English final

| Draft | Concrete opposition / decision | English final |
| --- | --- | --- |
| Weather source | Retain the root glossary term. This names the retained source; it does not assign ownership of PVGIS or the original weather data to Linker. | Weather source |
| Radiation database | Retain the standard source-data label. The value is the retained source's actual database identifier, not merely the requested or expected identifier. | Radiation database |
| Meteorological database | Retain the standard source-data label. The actual meteorological and radiation databases remain distinct. | Meteorological database |
| Source year range | The displayed endpoints come from the verified source request. This label could be mistaken for the years actually selected for the twelve months, or for continuous observed coverage. Name the requested range. German can say Angefragter Zeitraum because the weather-source context and year endpoints are directly adjacent. | Requested source year range |
| Synthetic energy year | Energy year is an internal field name. The value places the interpreted output on a synthetic calculation calendar; it is not the observed year of the weather or measured PV. | Synthetic calculation year |
| A typical meteorological year combines selected months from different years. | Retain: states the defining interpretation and prevents the synthetic year from being read as a single observed historical year. No added accuracy or forecast promise. | A typical meteorological year combines selected months from different years. |
| Some interval means were reconstructed. Finer output intervals do not create finer original observations. | “Means” and “finer original observations” are hard to decode. The retained record marks reconstructed interval averages, without a count. Name the PV profile and original weather-data time resolution; do not imply that these are measured PV observations or that interpolation increases source resolution. | The PV profile includes reconstructed interval averages. Shorter output intervals do not increase the time resolution of the original weather data. |
| Original source and interpretation record | Retain the approved existing English and German label exactly. This is a deep source/interpretation record, not a new accuracy badge or raw-file delivery promise. | Original source and interpretation record |
| PV model settings | Retain: identifies the task's historical settings without saying that one uniform setting applies to every array. German PV-Modelleinstellungen avoids adding a uniform-model claim. | PV model settings |

## Pre-delivery

- [x] Encyclopedia loaded for this non-PDP surface: one new dimension, source interpretation; category terms are not invented.
- [x] Hard Stops 1–9 hold on all nine final lines. The standard source/database labels describe data rather than borrowing brand credibility.
- [x] Actor: no second-person body-copy command or customer homework.
- [x] Future: no invented customer trajectory or outcome.
- [x] Weight: data attribution does not become engineering approval, measured PV or a full site assessment.
- [x] Duration: no ongoing/long-after or timing promise.
- [x] No slogan formula, forced rhetorical trio, invented synonym loop or dramatic fragments. Humanizer fixes preserve the actual numerical/source interpretation.
- [x] No banned-brand selling point. Original source/database names remain data attribution; systemic Linker identity is unchanged.
- [x] Quotes source gate: no testimonial or invented speaker.
- [x] Existing Original source and interpretation record / Originalquelle und Interpretationsprotokoll preserved exactly; Wetterquelle follows the existing glossary and source-selection terminology.
- [x] Independent German draft for every new/changed string, neutral formal register, no uniform-model or assessment claim.
- [ ] Root independent German review and final acceptance after integration.

Artifact checks passed: nine unique source literals match nine JSON rows; schema, nonempty EN/DE, no added placeholders, approved reused label, and no em/en dashes in final copy. These were read-only checks without modifying source or running tests. The three English revisions are the requested source-year range, synthetic calculation year and interval-reconstruction explanation.

No runtime, snapshot, backup, dependency tree or additional worktree was created. Only the two small current-task copy artifacts are retained.

## Integrator German review

Root independently reviewed all nine DE entries. Requested source years remain request bounds, and the synthetic calculation year remains a calendar mapping. Typical selected months are not described as one observed year. Reconstructed interval averages do not imply higher original weather resolution. Source names and actual database identifiers stay source facts. The approved existing source-record label is retained; the other terms agree with the current technical context. All nine pairs accepted and integrated.
