# Final 95-width header sweep

Base: `0fddf100`; source: `c24326c3`. Final reboot recovery run: 24 tests passed (47.0s).

| Engine | Widths | Fold mismatch | Actual visibility mismatch | Direction |
|---|---:|---|---|---|
| chromium | 95 | [] | [] | identical |
| webkit | 95 | [] | [] | identical |
| firefox | 95 | [1283, 1284, 1285, 1286, 1287] | [1283, 1284, 1285, 1286, 1287] | EN expanded / DE folded |

Raw measurements: [checks/header-matrix.log](checks/header-matrix.log); machine data: [sweep-summary.json](sweep-summary.json). No breakpoint or fit-budget change.
