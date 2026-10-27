# Spec review — eefe7c0b FAIL

Target `eefe7c0b060214b60ba7a012ff206e668dbce6d3`; base `7e96b88dd902ea64fd27250494d3129783d7f307`. Commits: 563e0387 and eefe7c0b. One P2 implemented-wrong finding remains in the Journal presentation increment; no separate scope-creep or missing-capability finding is counted against the broader, active goal.

**P2: a resolved invalid-input refusal reappears as a false error for a valid staged roof form.**

`WORKSPACE-VISUAL-CORRECTION.md:27–31` distinguishes unapplied properties from invalid properties and permits continuation after applying, correcting or cancelling. Fixed `ProjectEditor.tsx:109–113,155–158,424–438` retains `closeBlocked="invalid"` after the original problem is resolved. Meanwhile `DesignEditor.tsx:94–97` sets design validity false for every open, unapplied form. Their combination revives “Correct the highlighted input before leaving this project” even when no field is invalid and the user has not attempted to leave the new form.

Independent exact sequence: annual 10→25→invalid `1,` in English; selector switch is correctly blocked; Escape corrects it; Undo returns to Saved revision 7; switch to Design and open existing roof properties without editing. The old error reappears with zero `aria-invalid=true` fields. The new counterexample is red. Clear resolved refusal state and distinguish an unapplied form's Apply/Cancel action from a genuinely invalid brief field.

The retained 563 Site-start counterexample now passes unchanged. All 19 original probe cases pass; its copied source SHA256 is recorded and verified before execution. The new selector otherwise passes active-state/focus consistency, same-workspace reveal, invalid-raw rollback, unapplied and invalid geometry guards, two-step mixed-input undo/redo, retained sources, late hidden-file completion without focus theft, initial legacy aliases and withdrawn-scope admission/reveal checks. Overview missing/zero/multi-roof quantities and read-only preview behavior remain correct.

Execution: 54 fixed domain/data and 54 DOM tests pass. The composed independent probe passes 35 cases with one intended product failure. An initial deferred-effect test revoked admission after React had already revealed; its retained harness failure was corrected by injecting withdrawal before the reveal effect, without application changes.

Scope: actual fixed React/Query components in JSDOM, with synthetic transport/storage fixtures. No native WordPress, other-chat SDK fixture, Computer Use, pixel layout or physical-touch PASS is claimed. The 563 FAIL archive remains intact; later corrections are outside this fixed review.
