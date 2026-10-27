# Standards — corrected owned roof import

**Scoped PASS.** Fixed `eff8341d5a0eaf24999f42854da6339032c65c9c` against `367e454c23f542632258e1440387c4c9e7825e17`, covering3225fc55 and eff8341d. Full scoped review carries the prior documented findings and rechecks their corrections. AGENTS, CONTEXT, isolated-runtime decision and workflow/geographic specifications govern; no additional contribution/coding-standard file was found. The prior3225 FAIL and red evidence remain unchanged.

**Documented rules:** no open breach found.

- inputRefusal.ts excludes the shared response/request `invalid_json_object` code. The original four test files reproduce byte-for-byte against the corrected application: all9 cases pass. HTTP200/422/500 malformed responses retain the committed exact original; genuine input refusal still releases it. This satisfies the workflow's unknown-result boundary. Existing CSV/revision parser cases also pass in the full suite.
- geoJsonChoices.ts:18–27 documents the256-code-point display/default policy and preserves complete characters, adding an ellipsis only when shortened. The original Unicode counterexample passes; source bytes and feature/part selection remain unchanged. This closes both the malformed label and numeric-policy documentation findings.
- GeometryIntake.ts skips an explicitly bypassed height without erasing its raw value or prior error. Six additional independent EN/DE cases cover empty/invalid height→explicit zero→typed refusal→switch back; unchecked rights block dispatch with the approved localized message. Picker labels and description references resolve in each language. Area displays187.66/187,66 while the accepted underlying area remains unchanged after adoption. No source-precision or engineering claim is introduced.
- All76 final pairs match GNU and WordPress JSON, including the previously narrowed GEO-010 branch. The correction adds one planner reference to the pre-existing site term Choose file/Datei auswählen; syntax-tree/catalog checks find no unreviewed wording. No file selected and required-field terms are also reused correctly.
- Runtime dependencies remain unchanged, the pinned IndexedDB library remains dev-only with primary Apify provenance, styles remain within native WindPress, and source/emitted graph checks pass. No added legacy identifiers.

Independent baseline:62 domain/data +87 DOM; emitted graph1; unchanged probes9; new boundary cases6. Initial reviewer-only area-wait and message-inventory assumptions were corrected; their records remain in harness-notes.md.

**Heuristic judgement:** no actionable Mysterious Name, Duplicated Code, Feature Envy, Data Clumps, Primitive Obsession, Repeated Switches, Shotgun Surgery, Divergent Change, Speculative Generality, Message Chains, Middle Man or Refused Bequest. Repo conventions override heuristics; tooling-enforced style and preserved raw-log whitespace are excluded.

Unique probes/logs/rebuild hashes and cleanup remain here. Native rendering/gestures, later camera work and full-goal acceptance are separate.
