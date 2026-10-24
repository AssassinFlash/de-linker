# Saved interval exploration: Spec review

Source: `535d19af..131e412e`. Scope: appended “Saved interval exploration”
in `docs/specs/548-energy-workspace.md`; final-diff review follows AGENTS §0.1.

## Initial findings (resolved)

1. **[P2] UTC tooltip mismatch** — `EnergyFlowChart.tsx:40–79` formats axis
   labels in UTC but omits ECharts `useUTC: true`. The specification requires
   “their actual UTC start/end” (line 97). With a Europe/Berlin browser,
   `2023-01-01T00:00:00Z` displays under a `00:00` axis tick while its tooltip
   says `2023-01-01 01:00:00`. A focused installed-library SVG-model reproduction
   confirmed `useUTC=false` and both conflicting labels. Set the chart's global
   UTC option so hover and zoom labels retain the advertised time basis.

2. **[P2] Singleton stored-energy value disappears** —
   `EnergyFlowChart.tsx:92–103` suppresses all symbols while storage has only
   interval-end points. Jumping to the last interval creates one row: its
   nonzero stored energy has neither a line segment nor a marker. This fails
   the required storage view at interval end (lines 97–99). The focused
   installed-library reproduction confirmed one point, no point symbol, and
   a path containing only a move coordinate. Render a marker for singleton
   storage windows.

## Coverage and limits

Reviewed ownership-before-blob access, blob hash/manifest/run binding,
deployment cap, unchanged raw download, retained means/origin sum, exact-row
CSV, paging/jump, scope admission and chart-failure isolation. No additional
actionable Spec defect found in those paths. Reused the parent's passing HTTP,
parser/CSV, types and build results; no suite rerun or new test file.
Native browser verification and paired source switch remain with the parent.

## Incremental closure

Reviewed the two-line correction against `131e412e`: `useUTC: true` and
`showSymbol: field === "stored_kwh" && page.rows.length === 1`.
Reran only the focused installed-library reproductions using those source
settings: Berlin tooltip now reads `2023-01-01 00:00:00`; the singleton has a
point symbol. Both P2 findings are closed. No remaining Spec blocker.
