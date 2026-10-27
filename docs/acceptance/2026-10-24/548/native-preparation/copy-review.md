# Native preparation copy review

Date: 2026-10-24. Copy-only adversarial review for the native weather and PV preparation increment. The final English and independently written German drafts are in [copy-final.json](copy-final.json).

Status: English final copy accepted by this copy reviewer. German is an independent draft for the integrating agent's separate review; it is not yet a German final acceptance record. This document does not assert rendered, installed or production acceptance. The review changes only these two copy artifacts.

## Authority and scope

The current `/Users/chesterjohn/Documents/de-linker/AGENTS.md` governs this review. Its current tool names, customer scope and factual decisions override older naming or commercial definitions in copywriting references. The copy must distinguish a frozen saved revision, provider progress, a retained original, a published project source, selection in the current open draft and persistence through Save project.

References read and applied:

- `/Users/chesterjohn/.agents/skills/humanizer/SKILL.md`, limited to removing its named patterns and preserving facts and prescribed formality.
- `/Users/chesterjohn/.agents/skills/linker-copywriting/SKILL.md`, including Hard Stops 1–9 and the Preservation List.
- The skill's `references/industry-and-linker-encyclopedia.md`, `references/anti-patterns.md`, `references/positive-examples.md`, and the relevant terminology/tool evidence lanes (`26-tools-not-linker.md` and `31-terminology-memodo-map.md`). Older names and unsupported scope in that background material are not treated as current product authority.
- `docs/specs/548-weather-acquisition.md` and `docs/specs/548-pv-preparation.md`.
- Existing `plugins/linker-tools/languages/linker-tools-de_DE_formal.po` terms, specifically the approved energy-state labels, Version, Projekt speichern, Projektentwurf and reused record labels.
- Read-only inspection of `selectPreparation` and the weather-status reader to check what the visible messages can actually assert. No Standards or Spec review reports were read.

This section adds one customer dimension: understanding which prepared data can be used in the current project and which action saves that choice. It adds no new service, product category, model route, accuracy promise or production claim. The existing browser journal, identity, ownership, revision authority and live p548 data/runtime are outside this copy increment.

The owner's clarification is systemic: Linker attribution and value describe the complete tool. The existing app-level by Linker / von Linker identity remains the attribution surface. This increment adds no map-specific ownership or technology claim. It does not change or reaccept that previously exercised identity surface.

Reviewed source text after the preparation-specific notice and READY/RUNNING split, before English integration:

| File | SHA-256 |
| --- | --- |
| `apps/planner/src/components/energy/PreparationResult.tsx` | `17d93440fc7f4bbf60babc52aa90537fcc866db33a3e377e5b1091809977639c` |
| `apps/planner/src/components/energy/WeatherProgress.tsx` | `4fa794bebff085435dcb651a1dfcb215726313fdcf7fcb478f8a7ad73e78ad19` |
| `apps/planner/src/components/energy/planningLabels.ts` | `c2d526167a9ec36d39983467195d9ea7dd7ebfdcb82a36e973e7537fe0d1a814` |

## Concrete opposition and resolution

1. **Publication is separate from provider completion and capture.** A succeeded provider can still fail original-data validation. A validated retained original can survive a failed or cancelled local producer without an owned source. The two corresponding messages now name successful preparation and the exact Source ready status as the publication boundary. No message turns retained evidence into a selected source or a successful project result.
2. **Draft selection is separate from persistence.** “Save project confirms it” can sound like an acknowledgement of a choice already saved. The final says it saves the selection on the server. The selection buttons name the object; the immediately preceding helper specifies the current open draft and Save project. The selected state says “this draft” and makes no saved-project claim.
3. **Unknown starts remain unknown.** An unacknowledged start can represent a real remote operation. The final assigns verification to Linker, retains uncertainty and explicitly excludes an automatic second start. Contact Linker remains an invitation, not an instruction to guess an ID or restart a provider job.
4. **A stopping operation is unfinished.** “Terminal state” and “completion of the stop” expose queue terminology. The final says the stop is not yet confirmed. A failed stop check says only that the check failed and identifies any visible provider status as a recorded observation. It does not assert that the provider is still running or already stopped.
5. **A generic selection failure cannot prove an edit occurred.** The original branch used the same notice for mismatched source evidence as for changed source inputs. “The source request, roof or model has changed” diagnosed more than that branch proved. The integrating agent has now constrained that notice to `preparation_source_changed` (409). An unverifiable source record (502) uses the separate saved-source-check failure. With that separation, the original changed-input English notice is accurate and is retained. No 502 message tells the customer that the roof changed.
6. **Reference generation is not site approval.** The final keeps the unshaded-reference boundary and unassessed site shading, equipment compatibility and country requirements explicit. “Modelled PV generation” describes the kWh total without an accuracy, yield-guarantee, equipment-release or country-release claim.
7. **Record details must name their contents.** This disclosure contains checksums, not a full readable source/model dossier. Its title now says so. Task manifest and execution environment avoid calling a weather-preparation task an energy calculation; the existing energy-state labels remain unchanged.
8. **Queued recovery is not confirmed active human work.** A reconciliation record can be queued, running or waiting to retry. The final says verification is pending or in progress instead of implying a person is already investigating. The private recovery mechanism and credentials do not appear in customer copy.
9. **Waiting and processing are different.** The integrating agent split provider READY from RUNNING. READY now reuses the waiting-to-start message. The original processing message is retained for RUNNING alone; no new heading symbols or provider codes enter the copy.
10. **Preparation and edit failures need preparation-specific copy.** The two added notices say that the source could not be prepared, or that project editing is unavailable and the source was not selected. Neither calls weather preparation an energy-calculation failure, invents a provider state or implies that preparation changed project inputs.
11. **Root opposition: “uniform” added an unsupported model claim.** The first copy final added “uniform” in English and “ein einheitliches Modell” in German. Neither appeared in the source draft, and the roof arrays each have declared model settings. The added wording could therefore imply one shared model across all arrays. The root review rejected that implication. Row 10 now says only that this is an unshaded reference profile and preserves all three unassessed scope limits. Its German sentence states that the reference profile does not account for shading without making a claim about model uniformity. Semantic fidelity was rechecked: neither language claims an assessed site, compatible equipment, country release or one common model. The root reviewer found the other 57 mappings semantically suitable; the separate German final acceptance record remains with the integrating agent after integration.

## Draft to English final ledger

Every unique translated public literal in the three reviewed files appears below and in the JSON array in the same order. The section heading and aria label use the same Weather request status mapping. Units, formatting punctuation and machine identifiers are not English prose and remain unchanged. “Retain” records a positive decision, not an unreviewed string.

| # | English draft | Opposition / decision | English final |
| --- | --- | --- | --- |
| 1 | Revision %d | Retain the established saved-version label and placeholder. | Revision %d |
| 2 | This result belongs to an earlier saved revision. Its original inputs remain available. | Retain: states immutable history without restoring it into the current draft. | This result belongs to an earlier saved revision. Its original inputs remain available. |
| 3 | Latitude | Retain the standard coordinate name. | Latitude |
| 4 | Longitude | Retain the standard coordinate name. | Longitude |
| 5 | Altitude | Retain; German uses geographic Höhe, not the product operating-altitude term Betriebshöhe. | Altitude |
| 6 | Hourly weather records | Retain: describes the count of hourly records, not hours of guaranteed coverage or accuracy. | Hourly weather records |
| 7 | Modelled PV energy | State the actual generation total in kWh; retain the model qualifier. | Modelled PV generation |
| 8 | Start | Retain the existing interval label and approved German term. | Start |
| 9 | End | Retain the existing interval label and approved German term. | End |
| 10 | This profile is an unshaded reference scenario. Site shading, electrical compatibility and country requirements remain unassessed. | Root opposition removed the added “uniform” claim because arrays have declared model settings. Keep only the unshaded-reference boundary and unassessed equipment/country scope. The three limits are separate factual constraints, not a rhetorical trio. | This is an unshaded reference profile. Site shading, equipment compatibility and country requirements remain unassessed. |
| 11 | Preparing a source leaves your project inputs unchanged. Selection is recorded in the open draft; Save project confirms it on the server. | “Confirms” obscures persistence. Name the current open draft and the saving action, with no body-copy command. | Preparation leaves your project inputs unchanged. Selecting a source updates the current open draft. Save project saves that selection on the server. |
| 12 | Checking the saved source… | Retain: the UI reads the saved revision and owned source, not a new provider run. | Checking the saved source… |
| 13 | The saved source could not be checked. Existing project inputs remain unchanged. | Retain: describes a failed read and unchanged inputs without guessing a provider failure. | The saved source could not be checked. Existing project inputs remain unchanged. |
| 14 | Try again | Retain the established read-retry action; this button repeats the source read, not provider start. | Try again |
| 15 | The source request, roof or model has changed. A source matching the current inputs is required. | Original objection: generic evidence failures did not prove an input change. Resolved by a 409-only changed-input branch; 502 now uses the separate source-check message. Retain this notice only for the changed-input case. | The source request, roof or model has changed. A source matching the current inputs is required. |
| 16 | Selected in the open draft | Keep draft-only scope and shorten the disabled selected-state label. The helper names the current open draft. | Selected in this draft |
| 17 | Use this weather source in the open draft | Keep an explicit selection action and object. The adjacent helper carries draft/persistence scope without an overlong mobile button. | Use this weather source |
| 18 | Use this PV profile in the open draft | Same explicit selection/persistence distinction; retain PV profile as the object. | Use this PV profile |
| 19 | Source and model records | Five hash values are checksums, not a complete readable dossier. Name the actual disclosure. | Source and task checksums |
| 20 | Input SHA-256 | Retain the existing deep record label and German term. | Input SHA-256 |
| 21 | Manifest SHA-256 | The manifest belongs to the task. Use a distinct label to avoid changing the reused German Berechnungsmanifest label on energy results. | Task manifest SHA-256 |
| 22 | Result SHA-256 | Retain the exact deep record label. A checksum is not an accuracy claim. | Result SHA-256 |
| 23 | Runtime SHA-256 | Name the execution environment in plain language; avoid reusing the energy-only German Berechnungsumgebung label for a weather task. | Execution environment SHA-256 |
| 24 | Source content SHA-256 | Retain the exact content-checksum distinction. | Source content SHA-256 |
| 25 | The weather request is waiting to start. | Retain for a pending not-yet-issued request and provider READY. A remote run can exist in READY without processing yet. No duration or completion promise. | The weather request is waiting to start. |
| 26 | The weather provider is processing the saved request. | Original objection: READY can precede processing. The integrating agent separated READY into the waiting message, so retain this exact message for RUNNING alone. | The weather provider is processing the saved request. |
| 27 | The provider is stopping a run that exceeded its time limit. A terminal state has not been confirmed. | Remove terminal-state jargon while preserving unfinished stopping. | The provider is stopping the run after its time limit was reached. The stop is not yet confirmed. |
| 28 | The provider has accepted a stop request. Completion of the stop has not been confirmed. | Shorten the nominal phrase; accepted stop request remains distinct from confirmed stopped. | The provider accepted the stop request. The stop is not yet confirmed. |
| 29 | The provider run completed. This alone does not confirm a valid project weather source. | State the two actual conditions for readiness; provider success is insufficient. Validation refers to original-data acceptance, not a human accuracy assessment. | The provider has finished the request. A project source is ready only after the original data is validated and preparation succeeds. |
| 30 | The original weather data has been validated and retained. The local task state indicates whether the project source was published. | Retained data can coexist with cancelled or failed preparation. Replace publication jargon with the exact visible Source ready boundary. | The original weather data has passed validation and is retained. A project source is available only when the preparation status above shows "Source ready". |
| 31 | The provider confirmed that the run was stopped. | Retain: this sentence is used only for observed ABORTED, not ABORTING. | The provider confirmed that the run was stopped. |
| 32 | The provider run ended without a usable weather source. | Retain for failed/timed-out provider runs; only succeeded, validated data can supply this source. No retry or recovery promise. | The provider run ended without a usable weather source. |
| 33 | The service has not confirmed whether the provider started this request. The original request is retained for verification; another start is not sent automatically. | Put uncertainty first, give verification to Linker and preserve the no-automatic-restart rule. No customer recovery controls or provider ID instructions. | The provider may have started this request. Linker must verify the original request. The system will not start it again automatically. |
| 34 | Weather acquisition status | Acquisition is internal vocabulary. The visible status concerns the weather request, distinct from the preparation-task status above. | Weather request status |
| 35 | Reading weather acquisition status… | Match the request-status heading and describe loading recorded status rather than contacting the provider. | Loading weather request status… |
| 36 | Weather status could not be refreshed. Any visible state is the last confirmed response. | Use status consistently. “Any” keeps the message true when the first read fails and there is no prior displayed observation. | Weather status could not be refreshed. Any status shown comes from the last confirmed response. |
| 37 | The local task ended before a provider start was recorded. | “No start recorded” must not become “the provider never started.” State only the recorded evidence. | Weather preparation has ended. No provider start has been recorded. |
| 38 | The stop verification is still in progress. | Describe pending confirmation without asserting the provider is stopped or still running. | Confirmation that the provider run has ended is still pending. |
| 39 | The stop verification task failed. The last observed provider state is shown. | A failed check is not a running-provider fact. Conditional wording also covers an unknown start with no recorded provider observation. | The stop check failed. Any provider status shown is the last recorded observation. |
| 40 | Linker is verifying the retained provider operation. | Pending/retry recovery is not proof of active human investigation. Remove retained-operation jargon. | Verification of the recorded weather request is pending or in progress. |
| 41 | Contact Linker | Retain the contact invitation and existing sales address; no data-submission homework. | Contact Linker |
| 42 | Refresh weather status | Retain: this reads journal status and cannot start an Actor. | Refresh weather status |
| 43 | Weather acquisition | Name the task's customer deliverable in ordinary language. | Weather data preparation |
| 44 | PV generation profile | Retain the standard modelled-series name; it does not assert a released design. | PV generation profile |
| 45 | Energy calculation | Retain the approved existing task label and German Energieberechnung. | Energy calculation |
| 46 | Saved task | Retain a neutral fallback; do not pretend an unknown task is an energy calculation. | Saved task |
| 47 | Queued | Retain the approved shared queue label and German. | Queued |
| 48 | Preparing source | Retain: clearly separates source work from an energy calculation. | Preparing source |
| 49 | Calculating | Retain the approved existing energy-state label and German. | Calculating |
| 50 | Waiting to retry | Retain the approved shared retry-state label and German; no countdown or second-start promise. | Waiting to retry |
| 51 | Source ready | Retain: successful task result and owned source publication, without selection or project-save implication. | Source ready |
| 52 | Calculation complete | Retain the approved existing energy-state label and German. | Calculation complete |
| 53 | Source preparation failed | Retain: failure belongs to preparation, without inferring remote/provider state. | Source preparation failed |
| 54 | Calculation failed | Retain the approved existing energy-state label and German. | Calculation failed |
| 55 | Source preparation cancelled | Retain: local preparation cancellation does not claim that a provider stop is confirmed. | Source preparation cancelled |
| 56 | Calculation cancelled | Retain the approved existing energy-state label and German. | Calculation cancelled |
| 57 | This source could not be prepared. Your project inputs remain unchanged. | Retain the new precise preparation-failure notice. It reports local failure without inferring remote stop, source selection or input changes. | This source could not be prepared. Your project inputs remain unchanged. |
| 58 | This project cannot be edited right now. The source has not been selected. | Retain the new precise edit-unavailable notice. It states the failed selection consequence without inventing a cause or a save. | This project cannot be edited right now. The source has not been selected. |

## Pre-delivery checklist

- [x] Encyclopedia loaded for a non-PDP surface. The dimension is prepared-source selection and provenance; no new category or proprietary tool name is invented.
- [x] Hard Stops 1–9 checked against every final English line and the German draft. No borrowed credibility, proof inventory in a title/button, defensive company negation, service intensifier, invented logistics or timing, helpdesk initiation or repair-shop selling.
- [x] Actor: explanatory body copy assigns no homework. Buttons describe deliberate in-tool actions; Contact Linker is an allowed contact invitation. The English Save project label is the subject of a factual persistence sentence, not an imperative.
- [x] Future: no invented customer trajectory, motive, response time or eventual successful recovery.
- [x] Weight: a provider finish or retained capture is not described as a saved project, full engineering assessment or released system.
- [x] Duration: no ongoing/long-after claims or invented work duration.
- [x] No slogan formulas, dramatic fragment sequence, forced marketing trio, invented synonym loop or generic optimistic ending. The factual scope list and the three separate unknown-start facts remain because deleting them would remove contract information.
- [x] No banned brands on the surface. Linker is named only for a real contact/recovery responsibility.
- [x] Quote source gate checked. No testimonial or invented quotation. The quoted Source ready and Projekt speichern strings refer to actual interface labels.
- [x] Humanizer patterns checked before argument review: internal nominal phrases, unclear actors, unsupported diagnosis and unnecessary vocabulary changes were addressed. Formal Sie register is retained. No personality-restoration or theatrical voice was added.
- [x] No em/en dash in final English or German copy. SHA-256 and German compounds keep their grammatical hyphens.
- [x] Unshaded reference scope survives. Root opposition removed the added model-uniformity implication; no site-shading assessment, equipment/country release, manufacturer-parameter or human accuracy claim is introduced.
- [x] SUCCEEDED, captured, ABORTING, TIMING-OUT, unknown start, cancelled producer and cleanup failure keep their separate factual meanings.
- [x] Explicit current-draft selection and server persistence through Save project remain separate from background preparation and historical revision inputs.
- [x] The 409 changed-input notice is separate from the 502 unverifiable-source-record notice; neither is presented as an energy-calculation failure.
- [x] Provider READY uses waiting-to-start copy; only RUNNING uses processing copy.
- [x] App-wide by Linker / von Linker attribution is retained at systemic scope. No map-specific technology attribution is added.
- [x] All 58 unique public translated literals inventoried; `%d` and the reused energy-state labels preserved.
- [x] Independent formal-German draft supplied for each new/changed string; approved reused EN/DE energy-state labels copied without polishing.
- [ ] Integrating agent's independent German review and final acceptance record.
- [ ] Native EN/DE rendering, interaction and responsive acceptance by the integrating workflow. This copy review makes no visual or live acceptance claim.

## Artifact verification and retention

Read-only artifact verification passed: 58 unique source literals across 62 literal occurrences match exactly 58 JSON objects and 58 ledger rows. Each JSON object contains exactly `{draft, en, de}` with nonempty strings. There are 22 English revisions. The `%d` placeholder is preserved in both languages, all seven approved reused energy labels match the existing `.po` unchanged, no final English or German string contains an em/en dash, and the captured-status reference matches the final Source ready / Quelle bereit labels. Source integration and translation compilation remain with the integrating agent.

After the root opposition, the row-10 English/German correction was rechecked in the two copy artifacts only. JSON structure, 58-entry/58-row inventory, placeholder preservation, unchanged other 57 mappings and forbidden-dash checks passed. The initial source-coverage and hash record above identifies the reviewed draft before integration; this correction makes no new source/runtime acceptance claim.

No backup, snapshot, runtime, dependency tree, extra worktree or intermediate copy was created for this review. The two small artifacts are the current task's unique copy evidence. Retention therefore adds no disposable running copy or redundant full backup; no shared process or instance is changed.

## Integrator German review

Root independently reviewed all 58 German entries against the actual source behavior. Provider completion, retained original validation, published source readiness, current editable selection and server save remain distinct; READY does not claim active processing, ABORTING does not claim a completed stop, and unknown start forbids automatic repetition. Formal address, placeholders, source labels and units agree with the approved vocabulary. The unsupported uniform-model addition was removed from EN and DE before integration.

A real catalog collision was found for the proposed `Selected in this draft`: existing approved German `Für diese Eingaben ausgewählt` describes another selection surface. Preserve that approved message. This new context instead uses `Selected in the current draft` / `Im aktuellen Projektentwurf ausgewählt`, keeping the current draft boundary explicit. This supersedes the corresponding proposed ledger final. Source integration and the final JSON agree. Copy accepted for this consumer increment; this is not native or full-product acceptance.
