# Standards — guided owned roof import

**FAIL.** Fixed `3225fc552a89c406f685bfc5643d50745e58baa9` against `367e454c23f542632258e1440387c4c9e7825e17`; full single-commit diff reviewed. Standards inventory found AGENTS.md, CONTEXT, the isolated-runtime decision and supplied workflow/geographic specifications; no other contribution/coding-standard file. Current storage rules also apply.

**Documented-rule breaches**

1. **[P2] Retain uncertain originals when response parsing fails.** inputRefusal.ts:11 treats `invalid_json_object/422` as proven pre-mutation; useGeometryImport.ts:217–226 then deletes the intent and durable original. Yet readObject emits that same error when parsing responses. Independent actual PlannerClient + hook + IndexedDB cases return JSON arrays with HTTP200,422 or500 after a committed recovery write. Every case dispatches once, synthesizes `invalid_json_object/422`, and leaves intent=null/journal=0. This violates 548-roof-import-workflow.md, Interruption: unknown acknowledgements retain the exact request; only identified pre-mutation refusals release it. Remove this ambiguous code or carry trustworthy error-origin information. The genuine `invalid_input` control still releases correctly.

2. **[P3] Bound source labels without creating malformed Unicode.** geoJsonChoices.ts:47–49 slices at256 UTF-16 units. A valid UTF-8 name containing255 ASCII characters followed by🙂 becomes an unpaired high surrogate, then supplies the roof-name default. The256 bound also lacks a source/policy comment, contrary to AGENTS §4's numeric-threshold rule. Use a documented presentation bound that preserves complete characters, or keep the full allowed value. Original file bytes remain intact; this finding concerns the derived label/default.

**Other verified scope**

Independent baseline61 domain/data +66 DOM and emitted/source graph1 pass. Four additional cases pass: EN/DE recovery-update warnings permit confirmed preview/adoption, an actual ProjectEditor still saves server revision2 despite local acknowledgement/read failures, and concurrent quota writes retain32 originals without eviction. All76 final pairs match GNU/WP catalogs;75 match the reviewed proposals and GEO-010's narrowed wording matches these runtime branches. Primary Apify captures support the pinned dev-only IDBFactory dependency. Runtime dependencies are unchanged;18 new style rules use native WindPress. No added legacy identifiers.

**Heuristic judgement:** no additional actionable finding across Mysterious Name, Duplicated Code, Feature Envy, Data Clumps, Primitive Obsession, Repeated Switches, Shotgun Surgery, Divergent Change, Speculative Generality, Message Chains, Middle Man or Refused Bequest. Repository conventions override heuristics; tooling-enforced issues are skipped.

Unique probes/logs/rebuild hashes and cleanup remain here. No implementation/native/production writes. This fixed source remains FAIL; full-goal and native acceptance remain separate.
