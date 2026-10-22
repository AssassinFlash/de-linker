# Library navigation — production readback

Scoped online acceptance of the navigation repair in PR #528, merged as `a33a0bcec5b8067d81b2bd5071ae7435d85abe7b`. This does not close the whole-page visual review, the shared header defect, or the full-site goal.

## Release and native readback

- PR CI `39691967487` and post-merge CI `39693009936`: success.
- Release `20261021T233044862570Z-a33a0bce`: archived after the official `finish_deploy` completed 41 actions with no notes. All nine deployed identities matched the release manifest. Native package readback matched all 1,151 files in the three staged plugins, both before and after browser acceptance.
- A first SSH upload was interrupted before any code switch. The retained native readback proved all nine previous identities unchanged. The second native deployment succeeded; its code switch took 0.019 seconds. The first after-browser read attempt also lost its SSH connection; the second completed. These failures remain in private deployment logs; neither was counted as successful verification.
- Database snapshot streamed to the local machine: `db-20261021T233044Z.sql.gz`, 7,079,562 bytes. This code-deployment snapshot omits the reproducible `genie_chunks` index. Its full SHA is recorded in `navigation-production-readback.json`; it is not a complete data-migration backup.
- The official WindPress Settings → Performance → Generate action completed. Native cache mtime advanced from `1792620880` to `1792626156`; 701,525 bytes, SHA-256 `4d6074dd98f7bd580671ddda12a60b35896d1b4a5449ae27bb5a8799c4320a3a`, defect `null`. The unchanged CSS hash is expected for this JavaScript-only repair. No network HTTP status was captured for the admin compile request; the native output and completion UI are the evidence.
- Privacy EN post 1673 and DE post 6827 retained their complete pre-release content hashes and 29 backslashes each, before and after browser acceptance. No privacy content was rewritten during this release.

## Actual online browser consumers

Original screenshots and DOM geometry are in `navigation-cua-online-20261022T0752/`; the checked state mapping is `navigation-online-cua-summary.json`.

| Language and viewport | Motion exercised | Native hash versus stale tab query | Directory → keyboard suggestion | Deep filtered FAQ → documents |
| --- | --- | --- | --- | --- |
| DE 1440 × 1000 | normal | documents selected | actual SAJ question focused; SAJ marker after smooth scroll settles | precondition y=1356.5; first document y=178.96, below sticky bottom 137 |
| EN 1440 × 1000 | reduced | documents selected | actual SAJ question focused; SAJ marker | precondition y=1307; first document y=179.16, below sticky bottom 137 |
| DE 390 × 1000 | reduced | documents selected | actual SAJ question focused; SAJ marker | precondition y=1811; first document y=170.91, below sticky bottom 129 |
| EN 390 × 1000 | normal | documents selected | actual SAJ question focused; SAJ marker after smooth scroll settles | precondition y=1712; first document y=170.91, below sticky bottom 129 |

In every deep transition, the query remained `AIO3`, the first document fitted within the viewport, its thumbnail loaded, and focus stayed on the Documents tab. Fonts were loaded, no horizontal document overflow was observed, and acceptance captures had no admin bar. The online script URL carried `ver=1792624197`; the corresponding deployed file is part of the exact native package readback. The code hash remains the reviewed `d611a9778d9cc2a4f3478830c27b937cca666507487b0fbd9c816139cd7b155c`.

The online native-hash check is direct address/hash navigation with a conflicting old query parameter. It is not the local held-script/early native click test. That race is separately exercised by the 24-case local browser suite and bound to the same shipped bytes.

Actual EN390 same-document native hash change, Back and Forward selected FAQ → Documents → FAQ while retaining `AIO3`. The separately named `cross-document-*-observation` captures navigate between full documents and reset the search; they do not prove same-document retention. The DE1440 unsuffixed directory/suggestion frame is a mid-animation observation, not the settled marker acceptance. Earlier failing candidates and geometry remain retained under their original names.

## Session cleanup and remaining scope

The routine session created only for the official compile was revoked, its scoped browser cookies removed, and the parked guest WooCommerce cookie restored exactly. Creating the later online test tab seeded two existing browser login cookies that did not belong to that temporary session. They were parked privately during guest acceptance and restored exactly afterwards; no new session was created or existing user token revoked. Native staff persistent-cart data remained unchanged after the complete browser round. Raw cookie/token material remains outside the repository.

The shared translucent header still shows underlying scrolling text; current screenshots deliberately retain that defect. The EN/DE document totals differ (159/160) and need content-identity assessment in the full-site review. These observations do not invalidate the scoped navigation behavior, and they remain open rather than being silently accepted as page-wide PASS.

Rollback uses the native atomic deployment mechanism, `just cutover rollback-deploy`, while this release is the latest manifest; it restores the retained previous code. Re-run the native presentation/official cache verification and source/content readback for the selected release. Database recovery, if separately needed, uses `just cutover restore-snapshot db-20261021T233044Z.sql.gz`; no database restore was required here. A later release changes which manifest is latest, so inspect that manifest before rollback.
