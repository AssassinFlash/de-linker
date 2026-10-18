# Final exact live/local pixels — #223

Source: `27a128ab` on `05a3fbc1`; c223 snapshot `20261018-2057`.

**56/56 PASS**. Every full canvas has identical live/local dimensions and zero RGB pixels differing outside its declared ruled changes. No tolerance, crop, padding, broad header mask or image rescaling is used.

Full raw pairs, raw differences, measured region bounds and responsive image metadata are in [desktop capture](pixels-final-desktop/capture.json) and [mobile capture](pixels-final-mobile/capture.json). The native filled-draft comparison also passed a separate repeated 4-case run; no order, inquiry or mail was submitted, and the disposable Woo session was emptied.

The earlier 10 DE desktop header differences attributed to #229 remain preserved in [historical results](pixel-results-before-review2.md) and its JSON. This fresh live/snapshot capture has zero outside differences for those surfaces; no header exception has been added and no deployment cause is inferred.

| Case | Canvas live = local | Raw differing pixels | Outside ruled | Full raw pair |
|---|---|---:|---:|---|
| en-header-1440 | 1440×8278 | 39503 | **0** | [live](pixels-final-desktop/en-header-1440-live.png) · [local](pixels-final-desktop/en-header-1440-local.png) |
| en-footer-1440 | 1440×8278 | 615 | **0** | [live](pixels-final-desktop/en-footer-1440-live.png) · [local](pixels-final-desktop/en-footer-1440-local.png) |
| en-draft-1440 | 1440×1239 | 9260 | **0** | [live](pixels-final-desktop/en-draft-1440-live.png) · [local](pixels-final-desktop/en-draft-1440-local.png) |
| en-inquiry-1440 | 1440×1789 | 731 | **0** | [live](pixels-final-desktop/en-inquiry-1440-live.png) · [local](pixels-final-desktop/en-inquiry-1440-local.png) |
| en-lost-1440 | 1440×1276 | 1625 | **0** | [live](pixels-final-desktop/en-lost-1440-live.png) · [local](pixels-final-desktop/en-lost-1440-local.png) |
| en-lost-confirmation-1440 | 1440×1196 | 1625 | **0** | [live](pixels-final-desktop/en-lost-confirmation-1440-live.png) · [local](pixels-final-desktop/en-lost-confirmation-1440-local.png) |
| en-document-1440 | 1440×900 | 691 | **0** | [live](pixels-final-desktop/en-document-1440-live.png) · [local](pixels-final-desktop/en-document-1440-local.png) |
| de-header-1440 | 1440×8591 | 39611 | **0** | [live](pixels-final-desktop/de-header-1440-live.png) · [local](pixels-final-desktop/de-header-1440-local.png) |
| de-footer-1440 | 1440×8591 | 604 | **0** | [live](pixels-final-desktop/de-footer-1440-live.png) · [local](pixels-final-desktop/de-footer-1440-local.png) |
| de-draft-1440 | 1440×1239 | 9845 | **0** | [live](pixels-final-desktop/de-draft-1440-live.png) · [local](pixels-final-desktop/de-draft-1440-local.png) |
| de-inquiry-1440 | 1440×1831 | 743 | **0** | [live](pixels-final-desktop/de-inquiry-1440-live.png) · [local](pixels-final-desktop/de-inquiry-1440-local.png) |
| de-lost-1440 | 1440×1301 | 2087 | **0** | [live](pixels-final-desktop/de-lost-1440-live.png) · [local](pixels-final-desktop/de-lost-1440-local.png) |
| de-lost-confirmation-1440 | 1440×1217 | 2087 | **0** | [live](pixels-final-desktop/de-lost-confirmation-1440-live.png) · [local](pixels-final-desktop/de-lost-confirmation-1440-local.png) |
| de-document-1440 | 1440×900 | 688 | **0** | [live](pixels-final-desktop/de-document-1440-live.png) · [local](pixels-final-desktop/de-document-1440-local.png) |
| en-shop-1440 | 1440×9238 | 308278 | **0** | [live](pixels-final-desktop/en-shop-1440-live.png) · [local](pixels-final-desktop/en-shop-1440-local.png) |
| en-category-1440 | 1440×9264 | 308222 | **0** | [live](pixels-final-desktop/en-category-1440-live.png) · [local](pixels-final-desktop/en-category-1440-local.png) |
| en-product-1440 | 1440×7737 | 551 | **0** | [live](pixels-final-desktop/en-product-1440-live.png) · [local](pixels-final-desktop/en-product-1440-local.png) |
| en-compare-1440 | 1440×4212 | 3097 | **0** | [live](pixels-final-desktop/en-compare-1440-live.png) · [local](pixels-final-desktop/en-compare-1440-local.png) |
| en-genie-dock-1440 | 1440×8278 | 103318 | **0** | [live](pixels-final-desktop/en-genie-dock-1440-live.png) · [local](pixels-final-desktop/en-genie-dock-1440-local.png) |
| en-genie-workspace-1440 | 1440×2050 | 175355 | **0** | [live](pixels-final-desktop/en-genie-workspace-1440-live.png) · [local](pixels-final-desktop/en-genie-workspace-1440-local.png) |
| de-shop-1440 | 1440×9238 | 313820 | **0** | [live](pixels-final-desktop/de-shop-1440-live.png) · [local](pixels-final-desktop/de-shop-1440-local.png) |
| de-category-1440 | 1440×9264 | 313743 | **0** | [live](pixels-final-desktop/de-category-1440-live.png) · [local](pixels-final-desktop/de-category-1440-local.png) |
| de-product-1440 | 1440×7913 | 536 | **0** | [live](pixels-final-desktop/de-product-1440-live.png) · [local](pixels-final-desktop/de-product-1440-local.png) |
| de-compare-1440 | 1440×4098 | 3749 | **0** | [live](pixels-final-desktop/de-compare-1440-live.png) · [local](pixels-final-desktop/de-compare-1440-local.png) |
| de-genie-dock-1440 | 1440×8591 | 106851 | **0** | [live](pixels-final-desktop/de-genie-dock-1440-live.png) · [local](pixels-final-desktop/de-genie-dock-1440-local.png) |
| de-genie-workspace-1440 | 1440×2050 | 180357 | **0** | [live](pixels-final-desktop/de-genie-workspace-1440-live.png) · [local](pixels-final-desktop/de-genie-workspace-1440-local.png) |
| en-filled-draft-1440 | 1440×1421 | 3035 | **0** | [live](pixels-final-desktop/en-filled-draft-1440-live.png) · [local](pixels-final-desktop/en-filled-draft-1440-local.png) |
| de-filled-draft-1440 | 1440×1421 | 3281 | **0** | [live](pixels-final-desktop/de-filled-draft-1440-live.png) · [local](pixels-final-desktop/de-filled-draft-1440-local.png) |
| en-mobile-390 | 390×9254 | 1001 | **0** | [live](pixels-final-mobile/en-mobile-390-live.png) · [local](pixels-final-mobile/en-mobile-390-local.png) |
| en-footer-390 | 390×8809 | 607 | **0** | [live](pixels-final-mobile/en-footer-390-live.png) · [local](pixels-final-mobile/en-footer-390-local.png) |
| en-draft-390 | 390×1317 | 9260 | **0** | [live](pixels-final-mobile/en-draft-390-live.png) · [local](pixels-final-mobile/en-draft-390-local.png) |
| en-inquiry-mobile-390 | 390×1999 | 9509 | **0** | [live](pixels-final-mobile/en-inquiry-mobile-390-live.png) · [local](pixels-final-mobile/en-inquiry-mobile-390-local.png) |
| en-lost-390 | 390×1199 | 1625 | **0** | [live](pixels-final-mobile/en-lost-390-live.png) · [local](pixels-final-mobile/en-lost-390-local.png) |
| en-lost-confirmation-390 | 390×1144 | 1625 | **0** | [live](pixels-final-mobile/en-lost-confirmation-390-live.png) · [local](pixels-final-mobile/en-lost-confirmation-390-local.png) |
| en-document-390 | 390×900 | 691 | **0** | [live](pixels-final-mobile/en-document-390-live.png) · [local](pixels-final-mobile/en-document-390-local.png) |
| de-mobile-390 | 390×9710 | 1027 | **0** | [live](pixels-final-mobile/de-mobile-390-live.png) · [local](pixels-final-mobile/de-mobile-390-local.png) |
| de-footer-390 | 390×9265 | 596 | **0** | [live](pixels-final-mobile/de-footer-390-live.png) · [local](pixels-final-mobile/de-footer-390-local.png) |
| de-draft-390 | 390×1437 | 16357 | **0** | [live](pixels-final-mobile/de-draft-390-live.png) · [local](pixels-final-mobile/de-draft-390-local.png) |
| de-inquiry-mobile-390 | 390×2131 | 11607 | **0** | [live](pixels-final-mobile/de-inquiry-mobile-390-live.png) · [local](pixels-final-mobile/de-inquiry-mobile-390-local.png) |
| de-lost-390 | 390×1312 | 2087 | **0** | [live](pixels-final-mobile/de-lost-390-live.png) · [local](pixels-final-mobile/de-lost-390-local.png) |
| de-lost-confirmation-390 | 390×1272 | 2087 | **0** | [live](pixels-final-mobile/de-lost-confirmation-390-live.png) · [local](pixels-final-mobile/de-lost-confirmation-390-local.png) |
| de-document-390 | 390×900 | 688 | **0** | [live](pixels-final-mobile/de-document-390-live.png) · [local](pixels-final-mobile/de-document-390-local.png) |
| en-shop-390 | 390×12252 | 210602 | **0** | [live](pixels-final-mobile/en-shop-390-live.png) · [local](pixels-final-mobile/en-shop-390-local.png) |
| en-category-390 | 390×12270 | 210553 | **0** | [live](pixels-final-mobile/en-category-390-live.png) · [local](pixels-final-mobile/en-category-390-local.png) |
| en-product-390 | 390×11781 | 545 | **0** | [live](pixels-final-mobile/en-product-390-live.png) · [local](pixels-final-mobile/en-product-390-local.png) |
| en-compare-390 | 390×5730 | 3199 | **0** | [live](pixels-final-mobile/en-compare-390-live.png) · [local](pixels-final-mobile/en-compare-390-local.png) |
| en-genie-workspace-390 | 390×2238 | 76955 | **0** | [live](pixels-final-mobile/en-genie-workspace-390-live.png) · [local](pixels-final-mobile/en-genie-workspace-390-local.png) |
| de-shop-390 | 390×12590 | 215499 | **0** | [live](pixels-final-mobile/de-shop-390-live.png) · [local](pixels-final-mobile/de-shop-390-local.png) |
| de-category-390 | 390×12619 | 215373 | **0** | [live](pixels-final-mobile/de-category-390-live.png) · [local](pixels-final-mobile/de-category-390-local.png) |
| de-product-390 | 390×12561 | 16 | **0** | [live](pixels-final-mobile/de-product-390-live.png) · [local](pixels-final-mobile/de-product-390-local.png) |
| de-compare-390 | 390×4900 | 1827 | **0** | [live](pixels-final-mobile/de-compare-390-live.png) · [local](pixels-final-mobile/de-compare-390-local.png) |
| de-genie-workspace-390 | 390×2364 | 80375 | **0** | [live](pixels-final-mobile/de-genie-workspace-390-live.png) · [local](pixels-final-mobile/de-genie-workspace-390-local.png) |
| en-genie-dock-mobile-390 | 390×12252 | 73154 | **0** | [live](pixels-final-mobile/en-genie-dock-mobile-390-live.png) · [local](pixels-final-mobile/en-genie-dock-mobile-390-local.png) |
| de-genie-dock-mobile-390 | 390×12590 | 99285 | **0** | [live](pixels-final-mobile/de-genie-dock-mobile-390-live.png) · [local](pixels-final-mobile/de-genie-dock-mobile-390-local.png) |
| en-filled-draft-390 | 390×1901 | 4245 | **0** | [live](pixels-final-mobile/en-filled-draft-390-live.png) · [local](pixels-final-mobile/en-filled-draft-390-local.png) |
| de-filled-draft-390 | 390×2011 | 5162 | **0** | [live](pixels-final-mobile/de-filled-draft-390-live.png) · [local](pixels-final-mobile/de-filled-draft-390-local.png) |
