# Map drawing copy review

2026-10-24. Independent Spec/copy review of the frozen 42-message [English draft](COPY-DRAFT.json), SHA256 `21810242627075d350190c1e589f94d3d1ddff7f68baaa76bbfa121dc3a9282f`. Read against the actual working files based on HEAD `43297ecf5673fa5f29c82f90fbe583666a5e3e15`; the owner was refining implementation concurrently. This records wording decisions, not native UI, engineering or production acceptance.

## Spec and factual findings

Two wording/state issues were found in the frozen draft. The owner accepted corrections during review; source readback subsequently showed the revised introduction, separate storage messages and a no-drawing reading retry. This resolves the identified copy/state mismatch at source level, pending the owner's UI checks.

1. **P2: one storage notice covers states in which no drawing is open.** [useMapRoofDraft.ts](../../../../../apps/planner/src/data/useMapRoofDraft.ts):95–120 sets `storageFailed` on initial listing failure. [MapRoofWorkspace.tsx](../../../../../apps/planner/src/components/design/MapRoofWorkspace.tsx):324–352 renders the notice but hides both actions when `drawing` is null. “It remains open here” is false in that state, and the user has no reading retry. Split read failure from a failure involving an open drawing and expose a reading retry. “Protected” also implies more than a successful browser write. The storage comparison is exact-version based, not a chronological “newer” comparison ([MapRoofDraftStore.ts](../../../../../apps/planner/src/data/MapRoofDraftStore.ts):169–173,189–197).
2. **P2: the introduction overstates verification of slope, height and source.** [mapRoofDraft.ts](../../../../../apps/planner/src/domain/mapRoofDraft.ts):212–288 validates required entries, ranges and declared permission, then constructs a source and roof command. [MapRoofWorkspace.tsx](../../../../../apps/planner/src/components/design/MapRoofWorkspace.tsx):214–244 checks review completeness and specified roof geometry issues. These operations do not independently verify the source measurements or establish engineering approval. State the editable result and retained source declarations instead.

The other retention claims fit the inspected boundaries: pause waits for a successful flush; an input failure leaves the previous app-owned drawing; applying the roof first journals the prepared result; retirement waits for exact confirmed native geometry ([useMapRoofDraft.ts](../../../../../apps/planner/src/data/useMapRoofDraft.ts):137–183,210–239,280–312). “Added to the project draft” must remain distinct from “saved project.” This is a new roof-face workflow, not an existing-roof, hole or obstacle editing promise. Source export permission remains independent of retain/derive permission. The street map is orientation; declared spatial precision is a source claim.

Browser storage copy must not become an “only on this device” or “never uploaded” privacy promise: checking sends the proposed geometry, including its source declarations, to `geometry/review` (Workspace:214–224). No such promise has been added.

## Accepted English replacements

| Frozen message | Final replacement |
| --- | --- |
| “A drawing becomes a roof face after its outline, slope, height and source have been checked. It then appears in the plan and 3D views of this project.” | **The outline and roof properties form an editable roof face. The source and permissions stay with it in the project, alongside the plan and 3D views.** |
| “The drawing could not be protected in browser storage. It remains open here. Retrying preserves any newer copy saved by another tab.” when no drawing is open | **Saved drawings could not be read from this browser. Retry to check for an unfinished drawing.** Action: **Retry reading saved drawings**. |
| Same frozen storage message when a drawing is open | **The browser recovery copy could not be updated. The drawing remains open in this tab. Retrying keeps a different version saved by another tab.** |

The final open-drawing message also covers failed journal removal, not merely a failed save. It was read back at Workspace:327, with reading retry at :349 and `reload` in the hook. The earlier agreed intermediate text, “The drawing could not be saved in this browser. It remains open in this tab. Retrying keeps a different version saved by another tab.”, remains a translation key for review traceability; the recovery-copy key above is the final version. No interaction or native UI acceptance is inferred from source readback.

## Proposed English polish

These eight changes improve instructions or consistency without expanding capability. They are recommendations until incorporated by the owner.

| Frozen English | Recommended final English | Reason |
| --- | --- | --- |
| The roof needs valid plane values, a source reference and permission to use the drawing. The entered values have been kept. | **Some roof or source details are missing or invalid. Review the roof properties and source permissions. Your entries have been kept.** | The catch includes name, calibration, rights, numeric and shape errors. Avoids the internal term “plane values” and an incomplete list of required inputs. Does not promise a marked field for errors without a field identifier. |
| %d recorded vertices | **Recorded corners: %d** | Works for zero, one or many points without a plural API. Uses the same noun as the collection instructions. |
| Unfinished roof face | **Unfinished roof drawing** | A saved raw prefix is not yet an accepted project roof face. |
| Vertices can be dragged on the map. Edge midpoints add a corner. The roof plane uses the marked height reference even if the outline changes. | **Drag a corner to move it, or use an edge midpoint to add a corner. The marked height reference stays fixed when the outline changes.** | Gives the actual edit actions and distinguishes the fixed reference point from the editable outline. Supported by the staged Select flags (Controller:175–186) and separate stored reference (mapRoofDraft:188–208). |
| The reference identifies the measurements or drawing used for the outline, slope and height. The street map provides orientation. | **The source reference identifies the measurements or drawing used for the outline, slope and height. The street map provides orientation.** | Distinguishes this field from the nearby height reference. |
| Check and add roof | **Check and add roof face** | One boundary creates one roof face, not a whole building roof. |
| The check tests roof polygon geometry. Measurement accuracy, structural safety and engineering approval remain separate. | **This check tests roof boundary geometry. It does not verify measurement accuracy, structural safety or engineering approval.** | Plainly names the check's limit without implying a later approval service or workflow. This factual scope statement is useful, not defensive marketing. |
| Add vertex at map centre | **Add corner at map centre** | Matches the visible corner instructions and keyboard-accessible collection action. |

Keep the remaining frozen wording. Roof pitch, down-slope bearing, true north, reference height relative to the project origin, and declared precision are meaningful inputs here. The first recorded map point remains the height reference even if removed from the outline; do not rewrite it as “the first current corner.” Pausing, resuming, discarding and adding corners are legitimate app actions. No marketing conversion language is needed.

## German handoff and standards check

[COPY-DE.json](COPY-DE.json) independently composes formal German for **all 42 original exact keys**, plus **5 keys from the accepted replacement sequence and 8 keys for the recommended polish**. Keep original keys for traceability; superseded keys do not approve their old claim and must not remain visible after the corresponding English replacement. Match the selected final English key when importing translations. The file is a handoff, not an applied locale catalog.

`Dachfläche`, `Richtung des Dachgefälles`, `Aufmaß- oder Zeichnungsreferenz`, `Angegebene räumliche Genauigkeit` and `Projekt speichern` follow the existing formal German catalog (respectively lines 4169–4170,4193–4194,4233–4234,4353–4354,2624–2625). `Eckpunkt` names the same map corner throughout. `Projektentwurf` preserves the existing project draft distinction from the commercial `Lösungsentwurf`. Placeholder spellings and coordinate order are preserved. Numeric ranges, height reference and units do not change.

Applied [linker-copywriting](../../../../../../../../.agents/skills/linker-copywriting/SKILL.md) Hard Stops and the required `anti-patterns.md`, `positive-examples.md` and `industry-and-linker-encyclopedia.md`; applied [humanizer](../../../../../../../../.agents/skills/humanizer/SKILL.md) to remove vague verification, internal shorthand and forced reassurance. Those skill files are local references at `/Users/chesterjohn/.agents/skills/`. The encyclopedia's older tool names, commerce facts and design restrictions are superseded by current AGENTS and the workbench spec; they are not used to remove this approved design capability.

Pre-delivery:

- [x] Encyclopedia loaded. One dimension: editing a declared roof drawing into shared project geometry; no invented product class.
- [x] Hard Stops 1–9 reviewed. Tool instructions remain task actions under the owner's explicit brief; no marketing homework or invented customer future.
- [x] Public labels are plain; technical details stay beside the relevant engineering inputs.
- [x] No borrowed credibility, invented timings, promotional intensifiers, slogan formulas, quotations or new brand claims.
- [x] Retention, local/project save and check scope tied to the inspected branches; accepted corrections recorded above.
- [x] Formal German, consistent nouns and existing catalog terms; all frozen keys and placeholders covered.

Verification: JSON parses with 55 unique keys and nonempty string values; all 42 frozen keys are present; all 13 additional keys are listed above; each `%d`, `%1$s` and `%2$s` is preserved on its corresponding key. The frozen draft hash is unchanged. No application, catalog, test, build, dependency, instance or production changes were made by this reviewer.
