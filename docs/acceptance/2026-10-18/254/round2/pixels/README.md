# Actual current English pixel readback — open acceptance gate

This is an honest **failed comparison against an older baseline**, not a fresh latest-main parity pass. Source `bd862bdd5253ed246ab0fa5267f2b5defd6a8c4c` was captured natively in c254 and compared with immutable accepted frames at `aa552bdf3ba4423ff34d032e116dadb1af8fd615`. The fixed latest-main revision for this delivery is `1a277c1e51e3f6acb04771a3277b7960f2f36d3b`, which is newer than that archived baseline.

The shared comparator returned **exit1: 9 comparisons zero, 9 nonzero**. No input was edited; no masks, tolerance, crop, alignment or ruled region was used. The saved difference images retain every mismatch. Run `python3 docs/acceptance/2026-10-18/254/round2/pixels/recompare.py` to recount; exit1 is expected from these unchanged inputs and remains a failed parity result.

| Current frame | Different RGB pixels | Bounds (left, top, right, bottom) |
|---|---:|---|
| [home-1440.png](home-1440.png) | 0 | `None` |
| [products-1440.png](products-1440.png) | 316,340 | `[57, 20, 1379, 8792]` |
| [category-1440.png](category-1440.png) | 38,852 | `[348, 1034, 1379, 1734]` |
| [login-1440.png](login-1440.png) | 0 | `None` |
| [register-1440.png](register-1440.png) | 0 | `None` |
| [password-1440.png](password-1440.png) | 1,625 | `[610, 547, 831, 563]` |
| [faq-1440.png](faq-1440.png) | 0 | `None` |
| [compare-1440.png](compare-1440.png) | 0 | `None` |
| [draft-1440.png](draft-1440.png) | 9,266 | `[562, 417, 874, 464]` |
| [home-390.png](home-390.png) | 0 | `None` |
| [products-390.png](products-390.png) | 213,117 | `[32, 770, 357, 11683]` |
| [category-390.png](category-390.png) | 26,577 | `[32, 822, 357, 2335]` |
| [login-390.png](login-390.png) | 0 | `None` |
| [register-390.png](register-390.png) | 0 | `None` |
| [password-390.png](password-390.png) | 1,767 | `[32, 440, 306, 629]` |
| [faq-390.png](faq-390.png) | 0 | `None` |
| [compare-390.png](compare-390.png) | 38 | `[32, 621, 50, 624]` |
| [draft-390.png](draft-390.png) | 9,458 | `[37, 416, 349, 464]` |

## What can and cannot be concluded

Native main commit `15bed261` added separate create-account entries. The archived images predate that change, whereas current product/category actions, reset-password and empty-draft actions visibly include it. Those upstream behaviors are preserved in this branch. The EN footer template is byte-identical between fixed main `1a277c1e` and current source. The bounded transparent header end-padding repair is the only chrome stylesheet delta from that fixed main; the existing 36-case header/service browser suite is green.

These source facts explain why the older images cannot be used as a latest-main baseline. They do **not** convert any nonzero pixel count into zero or authorize a mask. Small logo/footer pixel differences are retained without a claimed root cause or waiver. In particular, the product desktop capture contains logo differences as well as repeated action-row differences; the 390px compare frame has38 footer pixels different.

The historical complete main/feature comparison in `../../pixel-results.json` remains18×0 at its actual older source pins. The fresh current check remains an **open strict pixel acceptance gate**; neither local root checks nor green CI closes it. Current twelve EN/DE service/journal/inquiry screenshots and native geometry are separate positive evidence, without a claim of current-main whole-page parity.

The shared c254 source/database was not switched to obtain a baseline while another session was modifying that instance. This evidence package makes the limit reviewable rather than relabelling historical captures.
