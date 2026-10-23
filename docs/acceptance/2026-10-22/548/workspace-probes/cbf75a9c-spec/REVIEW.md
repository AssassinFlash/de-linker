# Spec review — cbf75a9c FAIL

Target `cbf75a9cead3b3c87c0cb2f206a1cd7e6226551e`; base `7e96b88dd902ea64fd27250494d3129783d7f307`. One P2 presentation finding remains; no separate scope-creep or missing-capability finding is counted against the broader active goal.

**P2: refused workspace navigation gives its actionable explanation outside the persistent navigation region.**

`WORKSPACE-VISUAL-CORRECTION.md:119–121` says a staged form, “only after a refused departure, explains finishing or cancelling that edit.” Fixed `ProjectEditor.tsx:236–254` places the mobile selector in the sticky project bar, but the corresponding refusal Notice at lines429–448 remains below the title in the main document. A long form can therefore leave the attempted control visible while the explanation is above the viewport. The parent's separate actual DE390 sequence confirms precisely that behavior. The independent DOM counterexample opens existing roof properties, retains a raw name, attempts Overview, proves the correct refusal text exists, then fails because that Notice is outside `.lp-project-bar`. Move the existing guarded feedback into a persistent visible region; retain the form and draft.

Both earlier defects are resolved: the original 563 Site-start probe and eefe resolved-invalid→clean Undo→existing roof form counterexample run unchanged and pass. The complete retained composed probe passes 36 cases; all three retained prior probe files are SHA-verified against the earlier archive.

New checks pass all 12 roof-editor contexts, including source/module/coordinate/array/constraint forms and removal confirmation. Invalid brief errors take precedence; correcting them restores staged guidance; cancellation resumes navigation. In-flight save acknowledgement preserves later edits, uncertain-save retry retains exact bytes/key, and unavailable browser recovery continues to warn and block closing without losing the document. Controlled selector rollback, scope withdrawal, shared history, truthful overview quantities and read-only preview remain correct.

Execution: 54 fixed domain/data + 54 DOM tests pass. The complete independent refusal suite passes 53 cases with one intentional feedback-location failure. No new behavioral validation/copy-state defect was found.

This is actual fixed React/Query execution in JSDOM with explicit synthetic storage/transport fixtures. Physical offscreen evidence is the parent's separately reported native observation; this reviewer did not operate native WordPress, other-chat fixtures, Computer Use or production. No pixel/physical-touch or full A–D acceptance is claimed. Earlier 563/eefe FAIL records remain unchanged.
