# English copy adversarial review

Status: changes required. Final text below is proposed for implementation; this review does not change application source or approve the complete product.

Draft: `copy-draft.json` and `COPY-DRAFT.md`, 241 strings, energy-workspace increment based on `71b54073`. Reviewed every snapshot string, all seven `apps/planner/src/components/energy/` components and the calculation entry context. Paths below are relative to `apps/planner/`; snapshot numbers are stable literal anchors because concurrent source edits move line numbers.

## Basis and coverage

Applied `linker-copywriting` Hard Stops, preservation and relevance rules, its encyclopedia/anti-pattern/positive-example references, and `humanizer`. This is a tool input/result surface: useful units, model limits and necessary action instructions stay. Homepage sales templates and the reference library's older Articles/Planner/transaction/ROI claims do not override current AGENTS facts, the energy-workspace spec or the actual implementation. The dimension here is calculation of this project's energy flows, not an invented product qualification service.

Truth was checked against `EnergyKernel`, `energy_metrics.py`, `dispatch.py`, `dispatch_checks.py`, the workspace's recovery code and the recorded managed-worker `http.json`. The recorded synthetic result covers two intervals: 4 kWh demand, 3.62 kWh solar supply, 0.38 kWh grid import, 90.5% solar share and 100% PV input self-use. Equipment and country status are both `not_assessed`. These are fixture observations, not annual estimates or customer defaults.

Snapshot 1–179 covers the new energy wording and shared entry label; 205 is the new overview link description. All remaining snapshot entries (180–204 and 206–241) were read as existing overview/editor context and are excluded from proactive rewriting. They describe unrelated saved-project, roof, intake and recovery behaviour. The current source additionally contains “The solar share is undefined when gross demand is zero.” Keep it: that reason matches the metric's null denominator.

## 1. Correct operation, assessment and lifecycle claims

These are necessary factual changes, not optional tone preferences.

| File and draft literal | Adversarial finding | Proposed final text |
| --- | --- | --- |
| `src/components/energy/ScenarioForm.tsx`, #178: “PV supplies the simulated load and AC auxiliary demand before charging storage. Storage covers remaining demand above its reserve. Grid charging, when allowed, restores the reserve. Surplus PV is exported within the cap and then curtailed.” | False grid-recharge promise. `dispatch.py:self_consumption_with_reserve` requests charge only from PV surplus and explicitly documents no grid-recharge promise. Reserve is stored energy, not a demand threshold. | “PV supplies the simulated load and AC auxiliary demand first. Surplus PV charges the battery within the specified power and energy limits. The battery supplies remaining demand using stored energy above the reserve. When connected, the grid supplies any remaining demand within the import limit. This controller does not request grid charging. Remaining PV is exported within the export limit, then curtailed.” |
| Same file, #154: “These declared parameters describe a storage scenario at one AC connection. Product suitability is assessed separately.” | Passive present tense implies an assessment happens. The kernel returns `not_assessed`; no completed or promised product review is established. | “These values define a storage scenario at one AC connection. This calculation does not assess product suitability.” |
| `src/components/energy/RunResult.tsx`, #119: “The saved task runs on the server. Leaving this workspace keeps it running; cancellation uses the separate cancel action.” | Also shown for queued and retry-wait states. It incorrectly says they are already running. | “Leaving this workspace does not cancel the calculation. Its status is saved on the server.” |
| `src/components/energy/EnergyError.tsx`, #15: “New calculations are temporarily unavailable while the service is being updated. This request is kept for retry.” | A drain gate records no reason. An update is an inferred cause. | “New calculations are temporarily unavailable. This request remains available for retry.” |
| Same file, #13: “The inputs changed while this request was being prepared. The current draft is kept; the saved request can be retried explicitly.” | Scenario-change refusals also arise during local preparation/range application. A saved retryable request is not guaranteed in every case. | “The inputs changed before preparation finished. Your current draft remains open.” |
| Same file, #19: “The request could not be confirmed. The original request and open inputs are kept.” | Generic fallback also covers a failure before recovery storage succeeds. It must not promise that the request was retained. | “The request could not be confirmed. Your inputs remain open here.” |

Keep #129–130 verbatim: “Equipment suitability: not assessed by this calculation.” and “Country requirements: not assessed by this calculation.” No “approved”, “verified for installation”, “ready for the grid” or promised human review is warranted.

## 2. Clarify the final state and PV percentage

| File and draft literal | Finding | Proposed final text |
| --- | --- | --- |
| `ScenarioForm.tsx`, #173 “End-of-period requirement” | There are multiple operating periods; this is the end of the entire calculation. | “Stored energy at the end of the calculation” |
| Same file, #174 “No minimum final inventory”; #175 “Minimum final inventory”; #176 “Minimum stored energy at the end” | “Inventory” adds bookkeeping jargon to a kWh choice. | Respectively: “No minimum required”; “Specify a minimum”; “Minimum final stored energy” |
| Same file, #155 “Source for storage parameters” | Explicit assumptions are valid inputs; the label currently suggests only sourced product facts qualify. | “Source or assumption for storage parameters” |
| `RunResult.tsx`, #125 “PV energy used on site” | The numerator includes charging input even if some energy remains stored at the end. Make that scope visible. | “PV used or stored on site” |
| Same file, #137: “PV energy used on site divides PV supplied to load, AC auxiliaries and battery charging by generated PV after curtailment. Battery conversion losses remain in the energy balance.” | Preserve the post-curtailment denominator and charging-input basis in natural English. | “This percentage divides PV supplied to load, AC auxiliary demand and battery charging by generated PV after curtailment. Battery charging is counted before conversion losses, including energy still stored at the end. Curtailed PV is excluded from the denominator.” |

Keep the period-only result statement (#126), origin accounting, gross-demand definition, zero-denominator explanations, losses formula and no-midnight-reset statement. Do not relabel the result as annual yield, independence, payback, backup approval or a manufacturer prediction. A zero input remains an explicit choice; blank must not become zero.

## 3. Translate recovery and record terminology into customer language

| File and draft literal | Proposed final text |
| --- | --- |
| `EnergyWorkspace.tsx`, #21 “A saved scenario calculates energy flows over your interval data. The result retains its input revision, sources and model.” | “Calculate this project's energy flows over the selected periods. Each saved result keeps the inputs, sources and model used.” |
| Same file, #25 “Calculation-request recovery could not be stored or checked. New requests need durable recovery before they can be sent.” | “This browser could not save or read the information needed to recover calculation requests. New requests are paused until this is available.” |
| Same file, #26 “Check request recovery” | “Check browser storage” |
| Same file, #28 “Retry keeps the original request and key. Restoring storage parameters changes that part of the open draft; calculation requests keep their original saved revision.” | “Retrying a calculation uses its original request and saved input revision. Restoring storage settings replaces those settings in your open draft.” |
| Same file, #29 “Stored storage parameters” | “Saved storage settings” |
| `RunResult.tsx`, #111 “A pinned model or source is unavailable. This calculation has been kept with its original inputs.” | “A model or source used by this calculation is unavailable. Its original inputs remain saved.” |
| `RunBasis.tsx`, #93 “Reading the pinned input sources…” | “Reading the sources used for this result…” |
| Same file, #94 “The pinned source records could not be read. The saved result has been kept without substituting newer sources.” | “The sources used for this result could not be read. The saved result still refers to its original sources.” |
| Same file, #95 “Retry source records” | “Retry reading sources” |
| `RunResult.tsx`, #147 “Pinned calculation records” | “Calculation records” |

The recovery paragraph must keep the explicit replacement warning; shortening it to “Retry” would hide an action that changes the open draft. Technical keys, hashes and stored request bodies remain implementation data. SHA-256 labels (#96–97, #148–152) are acceptable inside the existing collapsed records, not as summary benefits.

## 4. Keep numerical verification at the appropriate depth

`RunResult.tsx` also renders `String(check.code)`, which is absent from the 241-string inventory. The fixture includes machine references such as `reserve_maintained`, `terminal_inventory` and `origin_transition_kw_initial_unknown_kwh`. These are technical references, not customer explanations of feasibility. Keep their current collapsed placement; name the panel accordingly:

- #138 “Calculation checks” → “Numerical verification details”.
- #140 “Frozen verification checks” → “Checks recorded with this result”.
- #141 “Check” → “Check reference”.
- #143 “Largest violation” → “Largest deviation”.
- #144 “Numerical allowance” → “Arithmetic tolerance”.

Keep #139's distinction between arithmetic allowances and installation safety margins. If an unmet scenario requirement is to guide a customer, give that requirement a plain label, for example `reserve_maintained` → “Stored-energy reserve”, `terminal_inventory` → “Final stored-energy requirement”, `load_supplied` → “Simulated demand supplied”. Raw references alone do not explain corrective action. No invented engineering pass statement should replace “Calculation complete”.

## Proposed-final disposition

All new strings not listed above remain unchanged, including input units, required field/refusal conditions, timestamp examples, status labels, history/pagination, cancellation uncertainty, historical revision warnings and the calculation entry labels (#20/#205). Necessary numerical or scope qualifiers were preserved. No borrowed credibility, fake service/timing promise, slogan formula, invented customer future or quotation was introduced. Operational controls retain clear action verbs; the marketing homework rule is not used to delete necessary form controls.

The proposed text contains no prose em/en dashes, invented manufacturer values or hidden physical constants. Mathematical minus signs, units and missing-value markers are data, not rhetorical dashes. English source changes need the corresponding separately reviewed German text before delivery. No builds, runtime changes, services, git commands, external research or credentials were used for this review.

## Addendum: revised English and German source draft

Reviewed `copy-final-en.json` (251 strings), including the new `evaluation_revision_changed` explanation, acknowledged-request dismissal, eight plain constraint labels and the gross-zero reason. No additional English factual issue was found in these additions. Revision refusal occurs after exact receipt replay and before run creation; therefore “This request did not create a calculation” is supported. Dismissal clears an acknowledged local recovery record, not the server result. The constraint labels identify requirements under the failure notice and do not claim that they passed. The gross-zero explanation matches the metric's recorded reason.

The independent German draft is `copy-german-draft.json`: all 187 exact English keys from `copy-german-needed.json`, each with a nonempty German string. It uses formal Sie where addressing the customer, preserves the four `%d` occurrences and the exact loss formula/units, and follows existing terms such as “Projekt speichern”, “Version” and “Energiedaten”. No existing German entry was changed. Equipment/country assessment remains absent; grid-charge permission does not become an automatic recharge promise. A separate German adversarial review and subsequent native rendering remain the enclosing task's gates.
