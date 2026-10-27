# Spec review: PASS, no actionable findings

Fixed `f0df6762fc549bf9251d508a802bb38cd2c258fa` versus `7e96b88dd902ea64fd27250494d3129783d7f307`. Scope: the approved Journal workspace increment and final refusal-feedback correction, not acceptance of the full planner goal.

`WORKSPACE-VISUAL-CORRECTION.md:142–146` requires a “full-width row in the sticky project bar, adjacent to the attempted navigation”, preserving the “open form and exact values” and existing height measurement. `ProjectEditor.tsx:309–331` places the same guarded `Notice` inside that header; `planner.css:71–73` wraps only the affected bar and gives the notice its own row. The unchanged `useProjectBar` observer measures the rendered header. No wording or validation transition changed in this relocation.

Independent executable evidence on the pinned snapshot:

- All **54 retained composed cases pass unchanged**. SHA checks verify all five retained probe/driver files. Earlier counterexamples now pass: Site reveals the first project section; resolved brief validation does not create an old warning when a staged roof form opens; refusal feedback belongs to the persistent navigation bar.
- **Seven additional cases pass**: one accessible pinned alert; exact bar, selector, form node and raw-value retention; brief-error precedence; cancellation and resumed navigation; acknowledgement during an unapplied form; uncertain-save status and byte-identical retry; unavailable recovery and refused close; and admission withdrawal with controlled navigation rollback.
- The fixed client suite passes **54 domain/data and 54 DOM tests**. Retained cases also cover shared history, legacy initial fragments, all 12 roof-editor form contexts, truthful empty/multi-roof quantities and read-only preview behavior, satisfying lines 27–40 and 119–129.

No missing, partially implemented, incorrectly implemented, or extraneous requirement was found within this scoped source/DOM review. Prior 563/eefe/cbf FAIL evidence remains intact. These tests mount real React/Query components in JSDOM with synthetic transport/storage/fixtures; they do not establish native pixel layout, physical touch, expanded-bar visibility, production behavior, or complete A–D acceptance. Those gates remain with the parent review.
