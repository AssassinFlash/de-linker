# Spec review: PASS for the fixed source/DOM increment

Fixed `eff8341d5a0eaf24999f42854da6339032c65c9c` versus `367e454c23f542632258e1440387c4c9e7825e17`, commits 3225fc55+eff8341d. No actionable Spec finding remains within this reviewed scope.

The original main and revision probes were rerun **byte-for-byte unchanged**: 20/20 and 1/1 pass, including all four formerly failing leaf variants. The 3225 FAIL archive and original probe hashes remain intact.

- **Uncertain requests:** the spec at 55–56 states, “Shared JSON/shape parser errors never identify a pre-mutation refusal.” `inputRefusal.ts:9–22` removes that ambiguous code. Additional actual-client tests retain exact originals after unusable HTTP 200/422/500/502 replies in both `GeometryImportStore` and `DraftStore`, then explicitly retry the identical body/key before typed correction. A real revision-parser case also retains the pending snapshot and preserves later edits.
- **Relative zero:** lines 25–26 require bypassing a rejected height “without erasing its raw string”; switching back requires correction. `GeometryIntake.tsx:231` skips only that overridden field. Independent blank/invalid-string sequences prove a 0 m request, unchanged raw value/error, blocked unchecking, explicit correction, then a fresh request/key with the corrected negative height.
- **Associated presentation:** lines 76–82 govern localization, complete Unicode and display precision. Executed controls verify the fixed German catalog, file-label/described-by references, filename updates and required-retention feedback. Unicode name/id boundary cases preserve full characters, visible ellipsis and exact original bytes/part identity. `GeometryIntake.tsx:648–650` rounds area only for display; the prepared 187.66430950859078 m² and null source precision remain unchanged.

**Verification:** 62 domain/data and 87 DOM tests pass; TypeScript and emitted graph/source-manifest checks pass. In addition to the 21 retained cases, 20 follow-up cases and one revision-parser case pass. These execute real React/Query/client/store code with isolated IndexedDB and controlled HTTP replies.

No missing, incorrectly implemented or extraneous requirement was found in this source/DOM scope. Catalog-driven fixture tests are not native language/layout proof. The parent-reported native camera/framing correction, physical touch, production and full A–D acceptance remain outside this verdict. No implementation or native/production edits were made.
