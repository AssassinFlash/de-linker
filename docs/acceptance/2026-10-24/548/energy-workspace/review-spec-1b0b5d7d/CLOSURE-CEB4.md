# Layout, validation and first-history-selection Spec closure

**Zero additional Spec findings at `ceb4a896bd39ffaa4ca72ae24eff6b73f3af6f8a`.** Independently reviewed the complete actual delta from `0836c245de92ebe8c6348ebfa322fd4fe632becb`: five commits, thirteen files. This extends the original full review and its prior narrow closures; it does not accept the complete goal or claim native execution.

The changes address native-discovered defects within the existing contract:

- **Result context and late layout:** the selected-result reveal waits for the
  next application frame, keeps focus on the semantic heading and scrolls its
  complete marked heading/revision context. The shared helper checks clearance
  once more on the following frame, only while that exact connected target
  retains focus and native admission remains current. Same-run polling still
  does not trigger the selection effect. This supports result presentation and
  keyboard navigation without seizing focus from another control.
- **Obsolete validation:** effective scenario-document or profile changes clear
  local scenario validation, including Undo/redo paths that bypass form
  `onChange`. Transport/recovery errors in `operations.error` are not retired by
  this effect. Request identities and protected intents remain intact.
- **First verified history selection:** the automatic history choice is now
  written into the existing guarded same-project run URL only after a full run
  read validates the selected ID. The effect requires active view, admission and
  no explicit prior selection; `select` independently checks current admission
  and current URL project. A list row is not a receipt, withdrawn admission
  prevents a late response from navigating, and an explicit deep-linked choice
  remains stable. This closes the energy spec's reload/history requirement
  (lines 51–59) and the existing language-context contract.

Focused independent verification at the exact pin passed: energy workspace,
energy-runs and workspace-lifecycle tests **19/19**; actual build/source hashes
match and lazy-entry execution guard **1/1**. Raw logs are
`closure-ceb4-focused.txt` and `closure-ceb4-build.txt`. The new real-hook test uses
the recorded managed-result response as a read-only transport fixture; it proves
selection/admission behavior, not a new physical calculation or browser geometry.

Earlier native occlusion captures remain failed intermediate evidence; these
source/fixture checks do not convert them into passing acceptance. Fresh native
reload/clearance, failure/cancellation and final EN/DE viewport/keyboard evidence
remain the enclosing implementer's gate. No numerical/default, copy, backend or
CSS-source change occurred in this delta. HEAD was read back as the exact final
pin; this reviewer wrote only the assigned review directory and did not change
source, builds, native data, browser or services. The full goal and production
remain separate and open.
