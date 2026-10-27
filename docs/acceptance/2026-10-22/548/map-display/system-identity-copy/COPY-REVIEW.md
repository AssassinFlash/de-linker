# Solution Configurator identity and disclosure

Verdict: **PASS for this corrected copy proposal.** One usable option, ten EN/DE messages including the existing product name and privacy-link label. Four draft corrections are recorded in `copy-review.json`. Application changes and rendered acceptance remain with the implementation owner.

The product identity is **Solution Configurator / Lösungskonfigurator**, followed by **by Linker / von Linker**. Its compact role statement is:

> Linker brings your inputs into an editable project for solar and storage planning.

> Linker bündelt Ihre Angaben in einem bearbeitbaren Projekt für die PV- und Speicherplanung.

Use the same identity and native `<details>` disclosure in the project list and project editor. The summary is **About this tool / Über dieses Werkzeug**. Linker's contribution leads the expanded content; geometry/source limits follow. **Software and data credits / Software und Datenquellen** is a subordinate heading. Keep the disclosure available across application sections and at phone widths. Preserve provider attribution inside the map itself.

`copy-final.json` contains the complete final messages and actual credit-link destinations. `copy-draft.json` retains the initial English draft; German was written independently for the corrected meaning. These are proposed strings, not a record that the application or locale files have changed.

## Review corrections

| Draft problem | Final correction |
| --- | --- |
| A site/roof/energy list repeats section labels and makes the product sound like data collection. | Name the complete solar/storage planning role through an editable project. |
| Inputs are described as saved and recovered without conditions. | Describe save controls and restoration of available drafts. |
| An installation-approval disclaimer applies to the whole tool; map and 3D lead the explanation. | Start with all design views sharing the project geometry. Attach the approval limit specifically to the displayed model. |
| Drei is credited from the installed stack rather than current imports. | Credit the current React/Query/Ajv, Three/Fiber and MapLibre use. Installed Drei, Terra Draw and ECharts are not presented as active interface capabilities. |

## Source to claim mapping

| Message or placement | Source and supported meaning |
| --- | --- |
| Product name and Linker ownership | Current owner clarification; `AGENTS.md` §1; `Workspace.tsx` product captions; `ProjectEditor.tsx` product navigation. The attribution identifies this application, without claiming authorship of its third-party components. |
| `system_role` | `AGENTS.md` §1 gives the whole Solution Configurator purpose. `Workspace.tsx` passes the selected project to `ProjectEditor`; the editor connects site/energy inputs and design through the same draft. No completed calculation or equipment outcome is promised. |
| `linker_contribution` | `ProjectEditor.tsx`: `useProjectDraft`, shared `editDraft`, `editGeometry`, profile attachment, save/recovery controls and revision/conflict states. `Workspace.tsx` owns project opening/listing; `ProjectOverview.tsx` summarises current inputs. |
| `geometry_source_boundary` | `DesignEditor.tsx` supplies the same geometry to plan/map/3D; `mapGeometry.ts` creates a read-only display projection. The map/3D dossiers separate rendering from measurement accuracy and engineering approval. `ProjectOverview.tsx` explicitly describes inputs rather than verified yield/equipment/release. |
| Software credits | Actual imports in `Workspace.tsx`, `ProjectEditor.tsx`, `readProtocol.ts`, geometry/profile validators, `SceneViewport.tsx`, `SceneCamera.tsx`, `SceneControls.tsx` and `MapViewport.tsx`. The installed publishers' package metadata supplies their homepage links; the stored 3D/map dossiers support their roles. |
| Street-map and privacy credits | Stored Apify OpenFreeMap quick-start: OpenFreeMap, © OpenMapTiles and OpenStreetMap data attribution; stored privacy page and `MAP-DISPLAY.md`. `MapViewport.tsx` supplies the explicit external-load action and provider privacy destination. Credits describe this component, not the entire product. |
| Shared native disclosure | Owner's implementation direction. Discoverability and keyboard/phone behaviour require later rendered verification; no custom modal is proposed. |

`copy-review.json` records hashes for the inspected source and dossier files. They are readback metadata from the moving shared checkout, not another source snapshot or a pinned full code review.

## Current wording and complete product scope

The current wording describes the implemented project/input/editing/revision workflow and shared design views. Current source inspection does not establish accepted calculations, equipment qualification, BOM or report delivery in the new workbench.

The full product obligation remains `AGENTS.md` §1 and `548-workbench-application.md`: inputs lead to a whole-system proposal, with calculation/equipment evidence and a design report; BOM, report and inquiry handoff retain their required contracts. `CAPABILITY-MAP.md` explicitly says implementation slices do not narrow that goal. The roof and map remain optional parts of the product. This identity proposal does not revise that scope or claim those remaining paths are complete.

## Checked copy gate

Applied `linker-copywriting`, with `humanizer` first and the required encyclopedia, anti-pattern and positive-example references already read in this copy-review task. Current project/owner rulings override conflicting older offer/tool terminology in those references.

- [x] Encyclopedia loaded. Dimension: Linker's complete planning application and the provenance of its components; no new hardware category or invented tool name.
- [x] Hard Stops 1–9 checked against every final visible string.
- [x] Actor: Linker supplies the application; no customer homework in body copy.
- [x] Future: no invented customer trajectory, motive or completion promise.
- [x] Weight: project workflow leads; map/3D and component credits retain their actual size.
- [x] Duration: no uninterrupted recovery, automatic save or ongoing-service guarantee.
- [x] No slogan formulas, promotional three-item filler, em/en dashes or borrowed-credibility claims. Component names are factual credits.
- [x] No banned hardware-brand claims. Third-party names identify actual software/data/providers, without endorsement language.
- [x] Quotes gate: no testimonials or copied third-party prose. The block quotations above show our proposed messages, not customer speech.

Verification was limited to copy and read-only source/dossier inspection. No application, locale, runtime, production or other evidence was edited. No external network research, native execution, legal acceptance, engineering-accuracy approval or full-goal completion is claimed.
