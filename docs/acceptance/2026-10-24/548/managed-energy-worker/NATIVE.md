# Native project and system-level identity readback

Source pin `b87aa3c9`; existing IAB browser 3, tab 2, same customer session and
owned synthetic project `82a84c56e50c4efb8497d1bfbe106bd1`. The page uses the
existing isolated planner entry `dec8b7a3214ae2d9260eed1112c6907002596e876a14d1f6bbca00258704c90d`.
No frontend code, stylesheet or built asset changed in this increment.

After managed-engine replacement, a real refresh initially showed the localized
workspace opening failure. The backend was healthy; the strict browser runtime
schema rejected the two newly forwarded operator fields. The WordPress gateway
projection fixed that actual consumer failure. It was not treated as a passing
backend-only deployment. The original project then reopened at **saved v14**.

| Page | Viewport | Actual saved status | Document width / scroll width | Product identity |
| --- | --- | --- | --- | --- |
| [DE desktop](native-de-1440.png) | 1440 × 1000 | Gespeichert · Version 14 | 1440 / 1440 | System-level footer + expanded About |
| [DE phone](native-de-390.png) | 390 × 844 | Gespeichert · Version 14 | 390 / 390 | Same product-level wording; wraps within width |
| [EN phone](native-en-390.png) | 390 × 844 | Saved · revision 14 | 390 / 390 | Same project, English workflow explanation |
| [EN desktop](native-en-1440.png) | 1440 × 1000 | Saved · revision 14 | 1440 / 1440 | Same product-level wording; expanded credits |

Each row has its matching `.ax.txt` and `.json` observation. An early capture
console helper searched only the German phrase and printed `version14:false`
for English. The raw English AX/DOM and screenshots show the correct
`Saved · revision 14`; the final matrix assertion uses the actual phrase for
each language and passes. No application behavior was changed to satisfy that
diagnostic. `readback.json` records the independent matrix assertions.

The visible product hierarchy is Solution Configurator / Lösungskonfigurator,
**by Linker / von Linker**, followed by Linker's role in editable project data,
workflow, saving and recovering drafts. About describes shared geometry and
source records before expandable software/data credits. Thus attribution is at
application level across overview and roof workspaces. OpenFreeMap and other
software are credited with their actual narrower role. The wording does not
claim unbuilt customer calculations or engineering release.

The expanded DE/EN copy and actual software/source links were observed; no
external link was followed by this native check. No project input was edited,
no new account/auth helper was created, no real mail/inquiry was sent. The
existing synthetic geometry and its accuracy limitations remain test data.

One additional DE full-page capture is retained as a raw observation. Fixed
header/sidebar appear at the document's then-current scroll position in that
capture API; the ordinary viewport PNGs are the visual acceptance evidence.
This is not a marketing-page pixel parity exercise or a new geometry edit
acceptance. Prior map-feature acceptance remains separate.

After testing, EN navigation returned to the original German project, roof
workspace `#lp-design`, with **v14 saved**. The temporary viewport override was
reset to the browser's default (observed 671 × 796), and the tab was marked for
ongoing goal work. [Restored page](native-restored-de.png).
