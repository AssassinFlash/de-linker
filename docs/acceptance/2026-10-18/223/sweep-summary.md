# Final 95-width header sweep

Base: `05a3fbc1`; source: `27a128ab`. Final three-engine run: **24 passed (42.0s)**.
The only later source delta is a browser-fixture reachability assertion; header
markup, fit() and breakpoints are unchanged.

| Engine | Widths | Fold mismatch | Actual visibility mismatch | Direction |
|---|---:|---|---|---|
| Chromium | 95 | [] | [] | identical |
| WebKit | 95 | [] | [] | identical |
| Firefox | 95 | [1283,1284,1285,1286,1287] | [1283,1284,1285,1286,1287] | EN expanded / DE folded |

The sweep retains the original 90 widths and adds 389,391,1275,1301,1366.
It also tests headroom, all six primary links/contact CTA, disclosures, keyboard,
Escape, resize recovery, registration reachability, overlap and actual visibility.
Raw: [matrix](checks/header-matrix.log), [machine rows](sweep-summary.json).
No fit budget or engine exception is added.
