# Existing map-boundary editing: customer copy review

Date: 2026-10-24. Independent adversarial copy review of the 29 frozen English drafts in [COPY-DRAFT.json](COPY-DRAFT.json), SHA256 `0d28de0740e74ecc781fb959f0710d97c7c43f7ac5352b8a7306f8acf50bc446`. Working-tree context: HEAD `252a022e41f8ca5426d6463206c8346eb89da5f1` plus the current map-ring increment. Application changes belong to the implementing agent.

The complete original-to-final mapping is [COPY-FINAL.json](COPY-FINAL.json): 29 objects containing `en`, `final_en` and independently composed formal `final_de`, in draft order. Twelve English messages change; seventeen remain. The frozen draft is unchanged.

## Scope and evidence

This increment lets the customer edit an existing roof boundary, an existing roof opening, an obstacle footprint or a keep-out boundary. It does not introduce new openings, obstacles or keep-out areas. The added dimension is **editing an existing project boundary while preserving its plane and recorded source information**. The parent identity remains **Solution Configurator by Linker**; “Map drawing” labels a subordinate region.

Wording was checked against [SPEC.md](SPEC.md), particularly its source/precision/permissions requirement, geometry-check limits and common project/save behavior; the current `MapRingSelector`, `MapRingProperties`, `MapDrawingWorkspace`, `MapViewport` and `mapDrawingLabels`; and existing formal German terms in `plugins/linker-tools/languages/linker-tools-de_DE_formal.po`. This is a copy review, not a code correctness, native browser, engineering or production acceptance report.

## Required English corrections

Numbers below are the one-based frozen entry order. The JSON contains the exact original strings and final strings, including messages retained without change.

| Entry | Original wording | Final wording | Adversarial finding and decision |
| --- | --- | --- | --- |
| 1 | Select a roof face, obstacle or keep-out area to edit its boundary on the map. | Select a roof face, obstacle or keep-out area on the map or in the object list. For a roof face, choose its outer boundary or an existing opening. | The first instruction leaves the selection route implicit and does not explain the opening selector. State the available routes and restrict openings to existing ones. |
| 5 | Drag a corner or an edge midpoint to edit this boundary. The existing roof plane, other boundaries and source statements are retained. | Drag a corner to move it, or use an edge midpoint to add a corner. The roof plane, other boundaries and recorded source details stay unchanged. | A corner and midpoint perform different operations. Name them. “Source statements” sounds like an internal data model; “recorded source details” matches the read-only customer information and does not imply verification. |
| 12 | Check and apply boundary | Check and apply changes | The customer is applying edits to an existing boundary. The new verb-object pair names that action without implying a new object. |
| 13 | The geometry check does not verify measurements or source permissions. If the recorded source does not cover these edits, pause the drawing and review the project inputs. | The geometry check does not verify measurements or source permissions. Your confirmation does not change the recorded export permission. If the source or permissions do not cover your changes, pause the drawing and review the project's source details. | “Project inputs” gives no clear destination. The checkbox beside the export-permission row could be misread as granting broader rights. Retain the useful check limit, explicitly separate confirmation from export permission, and name the source details to review. |
| 15 | Review the boundary and its source declaration. Your edits have been kept. | Review the boundary and its recorded source details. Your edits have been kept. | Replace the abstract “declaration” with the information shown in the form. Preserve the statement that the edit remains available; do not promise that failed storage succeeded. |
| 16 | This boundary did not pass the geometry check. Its points are kept for correction. | The geometry check could not validate this boundary. Your edits remain available for correction. | This notice also covers incomplete or numerically unsupported checks. It must not assert that the shape alone is invalid. Keep the scope explicitly geometric and retain a correction path. |
| 18 | The boundary check or local save could not be completed. Your edits remain available. | The boundary check or browser save could not be completed. Your edits remain available. | “Local save” could mean Save project or a downloaded file. “Browser save” identifies the temporary storage involved. It does not claim a successful browser write or server save. |
| 20 | Boundary unchanged. No project edit was added. | The boundary is unchanged. No project change was made. | “An edit was added” describes history implementation. State the customer-visible outcome in ordinary language. |
| 21 | Boundary edit added to the project draft. Save project stores it with the project. | Boundary changes applied to the project draft. Choose Save project to save them. | Keep the distinction between application to the draft and project saving. Refer to the existing button as an action, rather than making its label a stiff sentence subject. |
| 23 | Edit existing boundary | Edit an existing boundary | Add the natural English article, consistent with the neighboring “Draw a roof face” heading. |
| 24 | The selected boundary is edited in the existing roof plane. Confirmed changes use the same project, plan and 3D views. | The roof plane stays fixed while you edit this boundary. Applied changes appear in this project's map, plan and 3D views. | “Confirmed” can mean the source checkbox; “changes use views” is unnatural. Name the fixed plane and the result after applying the edit. |
| 25 | The map, plan and 3D views use the same project geometry. Map controls change the view; confirmed boundary edits change the project. | The map, plan and 3D views use the same project geometry. Panning and zooming change the view. Boundary edits update the project when you apply them. | Name recognizable camera actions and the application boundary. Pointer editing alone must not sound like an immediate project change. |

## Retained wording and German decisions

Entries 2–4 retain clear selector/action/property labels. Entries 6–10 retain the established source labels, units and “Unknown”; “Declared” remains essential because the app does not establish measurement accuracy. Entry 11 remains a first-person **user declaration**, not a claim that Linker checked the source. Entries 14, 17 and 19 accurately name the available numeric fallback, concurrent project change and current checking state. Entries 22 and 26–29 remain modest region/target labels. “Opening %d” is a display label, not a promise of creation or a permanent object identifier.

Formal German was composed for the interface, using **Sie** for instructions and **Ich** for the customer's checkbox declaration. Existing terms remain: `Dachfläche`, `Dachrand`, `Dachöffnung`, `Hindernis`, `Grundriss`, `Sperrfläche`, `Aufmaß- oder Zeichnungsreferenz`, `Angegebene räumliche Genauigkeit (m)` and `Projekt speichern`. Generic boundary editing uses `Umriss`; footprint uses the established `Grundriss`, not an invented literal “Fußabdruck”. `Projektentwurf` denotes this tool's unsaved project state and does not rename the commercial `Lösungsentwurf`. The `%d` opening placeholder and metre unit are preserved.

The supplemental read-only export row was inspected without adding entries to the frozen 29: **Permission to export geometry / Berechtigung zum Export der Geometrie**, **Permitted / Erlaubt**, **Prohibited / Untersagt**, **Unknown / Unbekannt** retain the previously reviewed catalog wording. They display the recorded value; neither the checkbox nor the check/apply action is described as changing it. The revised entry 13 makes that distinction explicit. No statement here treats the recorded source, rights, precision or calibration as independently verified.

## Rules applied

Read: [linker-copywriting](/Users/chesterjohn/.agents/skills/linker-copywriting/SKILL.md), its `industry-and-linker-encyclopedia.md`, `anti-patterns.md` (SOP bragging, research-note leakage, public jargon and customer homework), `positive-examples.md` (engineering-tool actions), and [humanizer](/Users/chesterjohn/.agents/skills/humanizer/SKILL.md). The active AGENTS and this explicit task supersede obsolete tool names and scope in the encyclopedia. No third-party sentences or external facts were acquired.

- [x] Encyclopedia loaded: one added dimension; existing project nouns and the current product identity retained.
- [x] Hard Stops 1–9 checked across all 29 messages: no borrowed credibility, proof inventory, defensive category claims, reassurance intensifiers, invented services, counters or helpdesk initiation.
- [x] Actor: instructions describe actual controls and source confirmation in this application. Per the task's explicit instruction, these legitimate tool actions are retained; no marketing homework is introduced.
- [x] Future: no invented customer trajectory or future overall capability is presented as implemented.
- [x] Weight: boundary editing and map orientation do not replace the whole Solution Configurator offer.
- [x] Duration: no undefined “ongoing”, permanent availability or guaranteed retention claim.
- [x] No slogan formulas, forced contrasts, promotional tricolons, inflated verification claims or internal research shorthand.
- [x] No banned brand or fabricated quotation; source gate requires no testimonial here.
- [x] Humanizer pass: simple verbs, concrete actions, natural German, no ornamental rewrite of labels that already work. Useful scope and rights limits retained.
- [x] Data/scope truth: browser draft, project application and Save project remain distinct; source confirmation cannot widen recorded export permission.
- [x] Delivery validation: all 29 originals map once in frozen order; 12 EN changes and 17 retained; all DE strings present; `%d` and units preserved; draft hash unchanged.

Only the two assigned copy artifacts were written. Applying the mapping and verifying actual EN/DE rendering, geometry refusal and project behavior remain implementation/acceptance work outside this copy review.
