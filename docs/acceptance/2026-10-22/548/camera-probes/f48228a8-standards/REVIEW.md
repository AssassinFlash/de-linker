# Standards: FAIL — f48228a8

Fixed diff: `eff8341d5a0eaf24999f42854da6339032c65c9c...f48228a87894c23f68d180675d05b902139d531e`.

**Documented Standards breach**

- **[P3] Publish the matching GNU catalog.** The three approved camera messages added at `plugins/linker-tools/languages/linker-tools-de_DE_formal.po:4728–4741` are absent from this SHA’s `.mo`. Their English originals are returned by GNU gettext. Source, emitted module, PO and WP JSON agree. `AGENTS.md:60,64,72` requires synchronized EN/DE delivery and shipped PO/MO catalogs. `catalogs.log` proves the fixed artifact discrepancy; the parent’s regenerated working MO is excluded. This does not assert that the browser’s correct WP JSON leaks English.

**Behavioral counterexamples forwarded to Spec; distinct from Standards/Fowler findings**

- **[P2] Resize fits a captured extent.** `SceneViewport.tsx:493–496,634` retains the first framing. After adding a second roof, resize uses the old centre/radius: four actual vertices are outside the frustum, NDC x approximately −3.47. `controlled-lifecycle.log` reproduces the violation of `548-roof-import-workflow.md:98–99` (“current extent”). Keep latest bounds separate from explicit orbit-reset intent.
- **[P2] Selected panel loses roof ownership.** `sceneCamera.ts:17–24` matches arrays/obstacles/keepouts, while `SceneViewport.tsx:205–208` selects panel IDs. Actual `array:0:0` belongs to roof `second`, but Fit gets roof one’s direction. `selected-panel.log` violates the selected-object requirement at spec lines 91–92. Resolve actual pose ownership, without parsing ID punctuation.

**Heuristics, not hard rules**

Possible **Primitive Obsession**: interpreting heterogeneous selection strings locally duplicates selection responsibility; use an explicit resolved selection/owner. All twelve baseline smells were considered; no additional actionable smell is asserted. See `FULL-REPORT.md` for each judgment and repository overrides.

**Independent evidence and limits**

Seven camera/buffer/lifetime cases and the actual emitted-ESM/source graph pass. Real React/Three through a controlled Canvas boundary passes initial narrow fit, selected-roof Fit, unchanged geometry, zero commits, stable Canvas mount, and help/label association. Resize and panel counterexamples fail. Approved three-pair copy remains unchanged from its recorded SHA. No new CSS pipeline/global React change was introduced. These probes do not establish native GPU, physical touch, production, or complete-workbench acceptance. Snapshot and dependency-link reclamation are recorded in `cleanup.json`.
