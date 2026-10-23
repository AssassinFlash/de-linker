# Guided roof import — source and component checkpoint

Base: `367e454c23f542632258e1440387c4c9e7825e17`.
Specification: [guided workflow](../../../specs/548-roof-import-workflow.md).
The complete unified-workbench goal remains active. This document does not
accept map drawing, image calibration, engineering, full site consumers or
production. Native and independent review results must be added separately.

## Implemented path

The Journal Roof design workspace now offers a three-step owned GeoJSON import:
file/roof selection; declared roof plane; source and rights. File inspection
offers actual named Polygon/MultiPolygon parts instead of asking customers for
zero-based indexes. The original is not rewritten and all openings remain in
the authoritative server candidate. Relative height is explicitly located at
the selected outer ring's first point. Unknown precision stays unknown.

Preview preparation retains its exact file/options/key before dispatch. The
server's accepted candidate is reviewed separately and enters the existing
project history only after an explicit Add action. Imported geometry/source/
original association is one undoable addition, followed by a distinct project
save. Existing unaligned geometry cannot silently acquire a geographic frame.

Recovery uses real IndexedDB transactions and native-granted scopes. Unknown
acknowledgements, including unidentified 4xx, preserve the original request for
explicit retry. The same refusal correction also applies to existing CSV
imports and revision saves; a status number alone cannot prove no mutation.
Acknowledged source IDs are cleared only when included in the confirmed project
baseline, including a save completed during the same open editor session.

## Defects caught while composing the actual controls

- Hiding the form by unmounting it during dispatch erased raw values on typed
  refusal. It remains mounted and hidden during the frozen request/preview;
  correction returns the same controls and values. Moving Back also preserves
  the raw locale-specific text.
- Focusing the entry button synchronously during Close failed while the button
  was still disabled by the open state. Focus restoration waits for the real
  enabled button and current native admission.
- Using the original opening project for confirmed source IDs missed a save
  acknowledged in the same editor. The consumer now reads `draft.baseline`,
  matching the existing profile-selection consumer.
- A newly attached roof now becomes the active roof rather than leaving the
  previous roof selected.

These observations came from component execution. They do not substitute for
native geometry, touch or browser persistence evidence.

## Owner verification before independent review

- TypeScript strict check passed.
- 61 domain/data tests and 66 DOM tests passed, including the actual
  ProjectEditor import → refused navigation → preview → one history addition →
  undo/redo → save → exact recovery cleanup path. The transport and project
  reply in that component fixture are synthetic; the geometry asset is the
  existing actual server wire fixture with an opening.
- Built-module graph/source-manifest check passed. No standalone CSS build or
  site-global React change was introduced. The existing scene remains lazy;
  Vite continues to report its chunk-size warning, not a capacity/performance
  acceptance result.
- Scoped formatting and `git diff --check` passed.
- Complete German coverage and generated WordPress JSON check passed after
  adding the missing planner reference for the reused Back message.
- EN/DE draft → independent opposition → final records: [draft](import-copy-draft.json),
  [feedback](import-copy-feedback.json), [final](import-copy-final.json). The
  generic recovery warning was adapted to the actual read/write/ack/cleanup
  branches: it must not say every upload is blocked after a confirmed preview.

The dev-only IndexedDB test library was acquired through Apify, not a default
search fallback. The Actor's first refusal was traced to the required proxy
configuration and repaired by using its valid existing Apify Proxy setting.
[Primary source capture](../../../research/2026-10-23-map-workbench-integration/dependency-fake-indexeddb/run.json).
No token, account configuration or new full-permission Actor approval was stored.
