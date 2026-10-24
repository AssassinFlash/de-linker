# Saved energy trace: Standards review

Reviewed frozen `535d19af..131e412e` (one commit), against `AGENTS.md`
§§0.1, 3–5, `CONTEXT.md`, and ADRs 0001/0002. Spec findings were not read.
Incrementally inspected the UTC/single-interval-symbol correction and boundary
extraction in the working tree.

**Verdict: PASS; no open documented breaches.**

- **Closed [P3]: one component/class per file.** The frozen diff defined
  `ChartBoundary` beside `TraceExplorer`, contrary to `AGENTS.md:82`.
  The parent moved the class unchanged into
  `apps/planner/src/components/energy/ChartBoundary.tsx`; `TraceExplorer.tsx`
  now imports it. Inspection confirmed identical boundary behavior and copy.

**Heuristics:** no additional Fowler smell warrants a change in this bounded
diff. No optional architecture work is requested.

Confirmed: the isolated React runtime and scoped query admission remain intact;
the private service reads an owned, hash-verified saved trace without rerunning
physics. No new SKU, country, compatibility or model-channel claims appear.
Styles use shared WindPress; chart colors/fonts inherit existing tokens.
All 19 reviewed EN/DE pairs match the compiled MO and browser JSON.
Added-source legacy-identifier/inline-style checks found no return of the old
implementation.

The installed ECharts declaration file reverses exactly to the pinned original
SHA: one `hoverLayer` and two `focus` declarations only. Runtime files and
project-wide strict/library checks remain unchanged. The UTC and
single-interval-symbol delta introduces no further Standards finding.

Reused the parent's targeted HTTP/parser/CSV, mypy and frontend build/type
results; no suite rerun or new tests. The parent owns the final corrected
candidate build/manifest refresh and browser/site/service acceptance.
