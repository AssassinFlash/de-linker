# Exact live/local pixel results

**未完成** — 34/52 cases have zero pixels outside ruled regions; 10 have remaining DE desktop header pixels; 8 fail full-page dimensions.

No color tolerance, crop, padding or dimension normalization is used. Each result retains unmasked differences, exact ruled boundaries and the original full screenshots. All dynamic masks are empty.

| Case | Outside ruled pixels | Original dimensions / status | Capture |
| --- | ---: | --- | --- |
| en-header-1440 | 0 | PASS | [live](pixels/en-header-1440-live.png), [local](pixels/en-header-1440-local.png) |
| en-footer-1440 | 0 | PASS | [live](pixels/en-footer-1440-live.png), [local](pixels/en-footer-1440-local.png) |
| en-draft-1440 | 0 | PASS | [live](pixels-final-fixes/en-draft-1440-live.png), [local](pixels-final-fixes/en-draft-1440-local.png) |
| en-inquiry-1440 | dimension FAIL | FAIL: live [1440, 1429], local [1440, 1804] | [live](pixels/en-inquiry-1440-live.png), [local](pixels/en-inquiry-1440-local.png) |
| en-lost-1440 | 0 | PASS | [live](pixels/en-lost-1440-live.png), [local](pixels/en-lost-1440-local.png) |
| en-lost-confirmation-1440 | 0 | PASS | [live](pixels/en-lost-confirmation-1440-live.png), [local](pixels/en-lost-confirmation-1440-local.png) |
| en-document-1440 | 0 | PASS | [live](pixels/en-document-1440-live.png), [local](pixels/en-document-1440-local.png) |
| de-header-1440 | 6166 | FAIL: main/live DE header drift | [live](pixels/de-header-1440-live.png), [local](pixels/de-header-1440-local.png) |
| de-footer-1440 | 13059 | FAIL: main/live DE header drift | [live](pixels/de-footer-1440-live.png), [local](pixels/de-footer-1440-local.png) |
| de-draft-1440 | 13061 | FAIL: main/live DE header drift | [live](pixels-final-fixes/de-draft-1440-live.png), [local](pixels-final-fixes/de-draft-1440-local.png) |
| de-inquiry-1440 | dimension FAIL | FAIL: live [1440, 1429], local [1440, 1846] | [live](pixels/de-inquiry-1440-live.png), [local](pixels/de-inquiry-1440-local.png) |
| de-lost-1440 | 13061 | FAIL: main/live DE header drift | [live](pixels/de-lost-1440-live.png), [local](pixels/de-lost-1440-local.png) |
| de-lost-confirmation-1440 | 13061 | FAIL: main/live DE header drift | [live](pixels/de-lost-confirmation-1440-live.png), [local](pixels/de-lost-confirmation-1440-local.png) |
| de-document-1440 | 0 | PASS | [live](pixels/de-document-1440-live.png), [local](pixels/de-document-1440-local.png) |
| en-mobile-390 | 0 | PASS | [live](pixels/en-mobile-390-live.png), [local](pixels/en-mobile-390-local.png) |
| en-footer-390 | 0 | PASS | [live](pixels/en-footer-390-live.png), [local](pixels/en-footer-390-local.png) |
| en-draft-390 | 0 | PASS | [live](pixels-final-fixes/en-draft-390-live.png), [local](pixels-final-fixes/en-draft-390-local.png) |
| en-inquiry-390 | dimension FAIL | FAIL: live [390, 1539], local [390, 2014] | [live](pixels/en-inquiry-390-live.png), [local](pixels/en-inquiry-390-local.png) |
| en-lost-390 | 0 | PASS | [live](pixels/en-lost-390-live.png), [local](pixels/en-lost-390-local.png) |
| en-lost-confirmation-390 | 0 | PASS | [live](pixels/en-lost-confirmation-390-live.png), [local](pixels/en-lost-confirmation-390-local.png) |
| en-document-390 | 0 | PASS | [live](pixels/en-document-390-live.png), [local](pixels/en-document-390-local.png) |
| de-mobile-390 | 0 | PASS | [live](pixels/de-mobile-390-live.png), [local](pixels/de-mobile-390-local.png) |
| de-footer-390 | 0 | PASS | [live](pixels/de-footer-390-live.png), [local](pixels/de-footer-390-local.png) |
| de-draft-390 | 0 | PASS | [live](pixels-final-fixes/de-draft-390-live.png), [local](pixels-final-fixes/de-draft-390-local.png) |
| de-inquiry-390 | dimension FAIL | FAIL: live [390, 1697], local [390, 2167] | [live](pixels/de-inquiry-390-live.png), [local](pixels/de-inquiry-390-local.png) |
| de-lost-390 | 0 | PASS | [live](pixels/de-lost-390-live.png), [local](pixels/de-lost-390-local.png) |
| de-lost-confirmation-390 | 0 | PASS | [live](pixels/de-lost-confirmation-390-live.png), [local](pixels/de-lost-confirmation-390-local.png) |
| de-document-390 | 0 | PASS | [live](pixels/de-document-390-live.png), [local](pixels/de-document-390-local.png) |
| en-shop-1440 | 0 | PASS | [live](pixels-products/en-shop-1440-live.png), [local](pixels-products/en-shop-1440-local.png) |
| en-category-1440 | 0 | PASS | [live](pixels-products/en-category-1440-live.png), [local](pixels-products/en-category-1440-local.png) |
| en-product-1440 | 0 | PASS | [live](pixels-products/en-product-1440-live.png), [local](pixels-products/en-product-1440-local.png) |
| en-compare-1440 | dimension FAIL | FAIL: live [1440, 4212], local [1440, 3979] | [live](pixels-products/en-compare-1440-live.png), [local](pixels-products/en-compare-1440-local.png) |
| en-genie-dock-1440 | 0 | PASS | [live](pixels-genie-final/en-genie-dock-1440-live.png), [local](pixels-genie-final/en-genie-dock-1440-local.png) |
| en-genie-workspace-1440 | 0 | PASS | [live](pixels-genie-final/en-genie-workspace-1440-live.png), [local](pixels-genie-final/en-genie-workspace-1440-local.png) |
| de-shop-1440 | 13061 | FAIL: main/live DE header drift | [live](pixels-products/de-shop-1440-live.png), [local](pixels-products/de-shop-1440-local.png) |
| de-category-1440 | 13061 | FAIL: main/live DE header drift | [live](pixels-products/de-category-1440-live.png), [local](pixels-products/de-category-1440-local.png) |
| de-product-1440 | 13061 | FAIL: main/live DE header drift | [live](pixels-products/de-product-1440-live.png), [local](pixels-products/de-product-1440-local.png) |
| de-compare-1440 | dimension FAIL | FAIL: live [1440, 4098], local [1440, 4002] | [live](pixels-products/de-compare-1440-live.png), [local](pixels-products/de-compare-1440-local.png) |
| de-genie-dock-1440 | 13059 | FAIL: main/live DE header drift | [live](pixels-genie-final/de-genie-dock-1440-live.png), [local](pixels-genie-final/de-genie-dock-1440-local.png) |
| de-genie-workspace-1440 | 13059 | FAIL: main/live DE header drift | [live](pixels-genie-final/de-genie-workspace-1440-live.png), [local](pixels-genie-final/de-genie-workspace-1440-local.png) |
| en-shop-390 | 0 | PASS | [live](pixels-products/en-shop-390-live.png), [local](pixels-products/en-shop-390-local.png) |
| en-category-390 | 0 | PASS | [live](pixels-products/en-category-390-live.png), [local](pixels-products/en-category-390-local.png) |
| en-product-390 | 0 | PASS | [live](pixels-products/en-product-390-live.png), [local](pixels-products/en-product-390-local.png) |
| en-compare-390 | dimension FAIL | FAIL: live [390, 5730], local [390, 5463] | [live](pixels-products/en-compare-390-live.png), [local](pixels-products/en-compare-390-local.png) |
| en-genie-workspace-390 | 0 | PASS | [live](pixels-genie-final/en-genie-workspace-390-live.png), [local](pixels-genie-final/en-genie-workspace-390-local.png) |
| de-shop-390 | 0 | PASS | [live](pixels-products/de-shop-390-live.png), [local](pixels-products/de-shop-390-local.png) |
| de-category-390 | 0 | PASS | [live](pixels-products/de-category-390-live.png), [local](pixels-products/de-category-390-local.png) |
| de-product-390 | 0 | PASS | [live](pixels-products/de-product-390-live.png), [local](pixels-products/de-product-390-local.png) |
| de-compare-390 | dimension FAIL | FAIL: live [390, 4900], local [390, 6006] | [live](pixels-products/de-compare-390-live.png), [local](pixels-products/de-compare-390-local.png) |
| de-genie-workspace-390 | 0 | PASS | [live](pixels-genie-final/de-genie-workspace-390-live.png), [local](pixels-genie-final/de-genie-workspace-390-local.png) |
| en-genie-dock-mobile-390 | 0 | PASS | [live](pixels-genie-final/en-genie-dock-mobile-390-live.png), [local](pixels-genie-final/en-genie-dock-mobile-390-local.png) |
| de-genie-dock-mobile-390 | 0 | PASS | [live](pixels-genie-final/de-genie-dock-mobile-390-live.png), [local](pixels-genie-final/de-genie-dock-mobile-390-local.png) |

## Attribution and limits

- The four inquiry cases compare the current open-inquiry implementation on main with the older live form. Restoring the old guest gate would violate the owner ruling. These dimensional failures remain failures.
- The four comparison cases include the owner-requested storefront visual bug correction. The entire comparison body is a ruled change, but differing full-page dimensions still fail this strict tool; no artificial padding/cropping was added.
- The ten remaining nonzero desktop DE cases are header pixels from the merged header work versus the version still live. Header fit/markup logic is retained; the new create entry is inside its declared account region. No broad header mask was added.
- The local DE390 empty-draft action-height regression was fixed; its final outside count is zero. EN/DE product-card action rows and EN/DE390 product/PDP surfaces are also zero outside their entry regions.
- Filled-draft images use local restored Woo fixtures. Live pixel parity of a populated draft is 未完成: no production cart/session write was performed.

Source data: [pixel-results.json](pixel-results.json). Scenario boundaries: [basic](scenarios.json), [product/tool](product-scenarios.json), [final fixes](final-fix-scenarios.json), [final Genie](genie-final-scenarios.json). The final Genie capture follows completion of stateful account fixtures; its only changes are within the explicitly ruled tool panel.
