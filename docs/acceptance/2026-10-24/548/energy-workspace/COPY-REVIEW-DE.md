# Independent German customer-copy adversarial review

Status: **changes required**. Four exact entries need the corrections below before the German draft can pass. Two additional terminology refinements are optional. This is an independent copy review of the energy-workspace increment, not an approval of the complete planner or a native visual acceptance.

## Reviewed corpus and basis

Read all **187 new German entries** in `copy-german-draft.json`, matched each exact English key against the 251-string `copy-final-en.json`, and read the English review and its addendum. Existing German PO entries were excluded and remain outside this rewrite scope.

Reviewed snapshots:

- `copy-final-en.json`: SHA-256 `68fbdcb4604d396b6e040f526ca13f742405926cd78cc307d9666e4a3deca21a`.
- `copy-german-draft.json`: SHA-256 `422baf34e9f884cc8559c1a3d32514eadd7a5117c065e035118333bfe2eabca7`.
- `copy-german-needed.json`: SHA-256 `114f962a71f7b4592c4d4ba4e8885d14d85680e17572bdb09807eafcceaf5aac`.

Applied AGENTS terminology and formal Sie, `linker-copywriting` Hard Stops, surface/relevance rules and encyclopedia, and `humanizer` factual-preservation and pattern rules. The dimension is the project's explicit interval energy scenario, its saved calculation and its source/model context. Older reference-library audience, commerce, tool or ROI claims do not override the current user/AGENTS decisions. Necessary operational form instructions and actual model limits are retained; they are not marketing homework or defensive company positioning.

Independently checked the semantics against `services/engine/src/linker_engine/planning/energy_kernel.py`, `energy_metrics.py`, `dispatch.py`, `battery_model.py`, `docs/specs/548-energy-workspace.md` and the current energy UI, especially `ScenarioForm.tsx`, `OperatingPeriodForm.tsx`, `RunResult.tsx`, `RunBasis.tsx` and the calculation/recovery controls in `EnergyWorkspace.tsx`. No external fact or new numerical constant was needed for this source-grounded review.

## Required corrections

The numbered entry anchors refer to the insertion order of the reviewed 187-entry German JSON snapshot. Each replacement preserves its exact English key.

### DE-01 · P2 · Factual model scope: losses apply during every interval

**English key (entry 91):**

> Standing-loss coefficient

**German draft:**

> Verlustkoeffizient im Stillstand

**Required final German:**

> Koeffizient der zeitabhängigen Speicherverluste

`dispatch._losses` applies the exponential loss in every interval, before internal auxiliary withdrawal, irrespective of charging, discharging or idle operation. “im Stillstand” incorrectly restricts the parameter to an idle state. The replacement describes the implemented time-dependent loss without claiming a particular chemical self-discharge mechanism or additional product behaviour.

### DE-02 · P2 · Paired model explanation: use the same unambiguous loss term

**English key (entry 157):**

> Internal auxiliary power is drawn from stored energy. Separate AC auxiliary demand comes from its interval profile. Standing loss uses E × (1 − exp(−r × hours)), with r in 1/h. Zero losses are explicit scenario assumptions.

**German draft:**

> Der interne Hilfsverbrauch wird aus der gespeicherten Energie gedeckt. Für den separaten AC-Hilfsverbrauch gilt das zugehörige Zeitreihenprofil. Die Standverluste folgen E × (1 − exp(−r × hours)); dabei ist hours die Dauer in Stunden und r der Koeffizient in 1/h. Verlustwerte von null sind ausdrücklich gewählte Szenarioannahmen.

**Required final German:**

> Der interne Hilfsverbrauch wird aus der gespeicherten Energie gedeckt. Für den separaten AC-Hilfsverbrauch gilt das zugehörige Zeitreihenprofil. Die zeitabhängigen Speicherverluste folgen E × (1 − exp(−r × hours)); dabei ist hours die Dauer in Stunden und r der Koeffizient in 1/h. Verlustwerte von null sind ausdrücklich gewählte Szenarioannahmen.

This is the paired terminology correction for DE-01. The formula, `hours`, `1/h`, origin of internal auxiliary energy, separate AC profile and explicit zero assumption are unchanged. It avoids retaining an idle-only reading in the explanation after the parameter label is corrected.

### DE-03 · P2 · Factual time semantics: operating boundary is temporal

**English key (entry 102):**

> Time alignment preserves interval energy under a constant-mean assumption. A finer display or operating boundary does not create new measured peaks.

**German draft:**

> Bei der zeitlichen Angleichung bleibt die Energie je Quellintervall erhalten. Innerhalb dieses Intervalls wird eine konstante mittlere Leistung angenommen. Eine feinere Darstellung oder eine zusätzliche Betriebsgrenze liefert keine neuen gemessenen Leistungsspitzen.

**Required final German:**

> Bei der zeitlichen Angleichung bleibt die Energie je Quellintervall erhalten. Innerhalb dieses Intervalls wird eine konstante mittlere Leistung angenommen. Eine feinere zeitliche Darstellung oder eine zusätzliche Grenze zwischen Betriebszeiträumen liefert keine neuen gemessenen Leistungsspitzen.

The UI displays source resolution and reconstructed means next to operating-period start/end times. The boundary is a time cut between periods; “Betriebsgrenze” ordinarily suggests an operating or capability limit. The replacement preserves both energy conservation under the constant-mean assumption and the absence of new measured peak information.

### DE-04 · P2 · Outcome precision: requirements have failed, not merely remained open

**English key (entry 119):**

> The calculation checks need attention. The detailed checks identify unmet requirements or inconsistencies.

**German draft:**

> Bei den Berechnungsprüfungen wurden offene Anforderungen oder Unstimmigkeiten festgestellt. Die Einzelprüfungen zeigen die betroffenen Punkte.

**Required final German:**

> Bei den Berechnungsprüfungen wurden nicht erfüllte Anforderungen oder Unstimmigkeiten festgestellt. Die Einzelprüfungen zeigen die betroffenen Punkte.

This notice is rendered for `scenario_constraint_status === "violated"`. “offene Anforderungen” can suggest an assessment is still pending; the checks have completed and recorded failed requirements or inconsistencies. “nicht erfüllte” matches that result without implying product or installation rejection.

## Optional terminology refinements

These do not independently block the draft once the required corrections are applied. They keep the new surfaces internally consistent and avoid unusual German labels.

| Severity / type | Exact English key | German draft | Recommended final German |
| --- | --- | --- | --- |
| P3 / label style | `Internal auxiliary power` | Interne Hilfsleistung | Interner Hilfsverbrauch |
| P3 / ratio terminology consistency | `The PV-use percentage is undefined when generated PV energy is zero.` | Wenn keine PV-Energie erzeugt wird, ist der prozentuale PV-Eigenverbrauch nicht definiert. | Wenn keine PV-Energie erzeugt wird, ist der Anteil der vor Ort genutzten oder gespeicherten PV-Energie nicht definiert. |

The internal auxiliary field displays `kW`, and its explanation already uses “interner Hilfsverbrauch”. The optional ratio wording follows the new summary label's consumed-or-stored scope rather than introducing a shorter conventional self-consumption label only in the undefined-value explanation. Neither refinement changes a value, denominator or model behaviour.

## Findings checked and retained

All other entries were reviewed and are retained. In particular:

- Formal customer address uses **Sie/Ihre** consistently. The `Ihr` in “Ihr Status bleibt auf dem Server gespeichert” refers to the calculation; it is not informal plural address. No colloquial du/euch address was found.
- `kWh`, `kW`, percentages, `1/h`, UTC, `Z`, the `+01:00` example and the distinction between energy and power are preserved. “Speicherenergie”, “Energiereserve”, conversion directions and the initial PV/grid/unknown-origin amounts retain their meaning. Empty fields are not presented as zero; the explicit zero-start action remains an explicit scenario choice.
- The four `%d` placeholders occur in the same exact keys and order as English. There are no `%s` placeholders in this new corpus and no placeholder mismatches. The loss expression **`E × (1 − exp(−r × hours))`** is byte-identical in the relevant EN and DE strings.
- The controller explanation says **“Diese Regelung veranlasst kein Laden aus dem Netz.”** Grid-charge permission is not changed into a promise to replenish the reserve or to optimise a tariff. PV priority, stored-energy reserve, import/export caps and curtailment remain consistent with the actual policy.
- Outage wording retains the critical-load profile and explicit PV-availability requirement. It does not claim a product is backup-capable, switching is modelled, or the installation is approved.
- Solar supply includes PV-origin battery discharge. Grid and unknown origin remain separate. The gross-demand fraction is explicitly undefined for critical/mixed load scope and a zero denominator. The PV-use definition preserves the post-curtailment generated-PV denominator, pre-conversion-loss charging input, energy still stored at the end, and exclusion of curtailed PV from the denominator.
- Equipment and country wording clearly states **not assessed by this calculation**. Fixed capacity/power/efficiency and omitted temperature, ageing, shared DC, phase and switching effects remain visible, with no claim of a completed separate assessment or promised expert review.
- Pending, completed, failed, cancelled and historical-input wording stays distinct. Leaving the workspace is not cancellation. Retry uses the original saved request/revision; restoring storage settings explicitly replaces that part of the open draft. No recovery key/body jargon appears in the high-level customer wording.
- SHA-256 and manifest labels stay in the existing deep calculation/source records. There is no synthetic SDK panel, internal event log, borrowed-credibility claim, invented service SLA, payback claim, quotation, slogan formula or fabricated customer trajectory in the reviewed new corpus.

## Pre-delivery checklist

- [x] Encyclopedia loaded; the single dimension is calculation of the selected project scenario, not an invented qualification service.
- [x] Hard Stops 1–9 checked on all 187 entries, with technical terms limited to operational/deep tool context.
- [x] Actor/Future/Weight/Duration tests checked; operational controls retained and no invented ongoing service added.
- [x] No slogan formula, banned brand or fabricated quotation introduced.
- [x] Humanizer pass: checked inflated claims, false contrasts, filler, staged reassurance, repetitive fragments and unsupported additions. Precise model limits and necessary instructions retained.
- [x] Exact English-key membership, placeholder parity and loss formula checked mechanically.
- [ ] Required DE-01–DE-04 corrections implemented and independently read back.
- [ ] Native German rendering and layout acceptance completed by the enclosing implementation task.

No PO/source, build output, service, database, git state, settings or credential was changed by this review. Only this review document is owned and written by the reviewer. The current draft remains **changes required** until the four required entries are replaced and read back.


## Closure addendum · independent compiled-catalogue readback

**German copy disposition: PASS for this 187-entry increment. Zero required copy findings remain open.** This supersedes the draft's changes-required status above for the verified final artifacts only. Native rendering and layout acceptance remain a separate gate for the enclosing task; this readback does not claim that a browser has executed these artifacts or that the complete planner is accepted.

Independently read `copy-german-final.json`, the actual PO, the compiled MO through Python's GNUTranslations reader, and the WordPress-generated planner JSON. The final contains the same 187 exact English keys as the draft, with no missing/extra keys and exactly six changed translations: required DE-01–DE-04 plus both optional refinements. Every changed string matches the complete recommended final wording above. The other 181 translations are unchanged.

Verified artifact identities:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `docs/acceptance/2026-10-24/548/energy-workspace/copy-german-final.json` | 23,822 | `53ae563d319dcd5a9ed02930038c09196f9cbe0b9bc743d209df83d829bf9b0b` |
| `plugins/linker-tools/languages/linker-tools-de_DE_formal.po` | 263,899 | `29f7da2e3c7389440ce1ad2417b00a431a2af7b7d7028009508ba9da5d5949d9` |
| `plugins/linker-tools/languages/linker-tools-de_DE_formal.mo` | 154,737 | `c68505fa5794928bf71bbb2e0ff9cd0a86d11778048b31d4ae716d01537e088a` |
| `plugins/linker-tools/languages/linker-tools-de_DE_formal-cf89287c9001d7518d0d20e58c3eb721.json` | 101,805 | `c857034f3390630b0e38a08fef91592d0ab8cd6fb4861cb8f6e997419cc3d7c0` |

Readback assertions all passed:

- All **187/187** final German values equal their active PO translations, actual MO lookup values, and generated planner JSON `locale_data.messages` values. The JSON's declared source is `build/planner/assets/planner.js`. No new entry is fuzzy/absent from the compiled lookup or replaced by an English fallback.
- The four `%d` placeholders remain present in the same four exact English keys and order: calculation-request revision, new-calculation input revision, operating-period number and result input revision. There is no `%s` placeholder or mismatch.
- The exact expression `E × (1 − exp(−r × hours))`, `hours` and `1/h` are preserved in the final explanation and all three catalogue representations. The label and explanation now consistently describe time-dependent storage losses, without restricting them to an idle state.
- The source-resolution paragraph explicitly names a boundary **between operating periods**, and the failed-check notice explicitly names **unmet requirements**. The optional auxiliary label and undefined-PV-use explanation are also present exactly as proposed.
- Existing German preservation was checked against the committed PO at `71b54073622117c12953cd40957ec1f5d4d827a6`. The complete prior **219,917-byte PO is a byte-identical prefix** of the current PO. Its SHA-256 is `e23d7c27c937eddf3cf3548038656b3e98e0632301a3a1db2b5030f592a3ca08`. All **1,156** prior active entries remain identical; none of the 187 new keys was already active. The current PO has **1,343** active entries, with no duplicate keys found.
- The approved negative assessment boundaries, no-grid-recharge controller statement, source-origin separation, loss assumptions, formal Sie and numerical definitions remain unchanged from the reviewed final proposal.

Checklist closure:

- [x] Required DE-01–DE-04 corrections implemented and independently read back.
- [x] Both optional terminology refinements implemented and independently read back.
- [x] Final JSON, active PO, compiled MO and generated planner JSON agree for all 187 entries.
- [x] Existing German catalogue content preserved byte for byte.
- [ ] Native German rendering and layout acceptance, owned by the enclosing implementation task.

The reviewer only appended this addendum to the assigned review document. Verification was read-only for source/catalogues and used no build, service, database, git-state, settings or credential mutation. Remaining copy findings: **none**.
