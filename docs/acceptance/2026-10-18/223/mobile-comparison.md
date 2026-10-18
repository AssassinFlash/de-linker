# Comparison page: superseding review-round-2 decision

All comparison and Genie work remains in #223 and PR #312, following the owner's
2026-10-18 ruling. No ticket was split.

The earlier column-only adjustment and then the `.sf-compare` shell rebuild are
superseded. The owner returned the branch with an explicit requirement to restore
live page dimensions and narrow the declaration to changed rows/cells. The
final source restores the live EN/DE LC templates and comparison table geometry.
It removes the comparison aliases from products.css/storefront.css; the 224px
minimum columns and the changed shell typography/padding are no longer active.

Only the guest net-price cells change. Their native sign-in link uses the already
reviewed **Sign in / Anmelden**, beside **Create account / Konto erstellen**.
The original price explanation remains in an escaped accessible label beginning
with the visible sign-in label. No hidden sizing prompt is used. There is no
whole `.sf-compare` declaration and no page-height padding, image resizing,
cropping, canvas resizing or RGB tolerance.

| Locale / width | Live full-page height required | Result location |
| --- | ---: | --- |
| EN 1440 | 4212 | pixels-review2/en-compare-1440-*.png |
| DE 1440 | 4098 | pixels-review2/de-compare-1440-*.png |
| EN 390 | 5730 | pixels-review2/en-compare-390-*.png |
| DE 390 | 4900 | pixels-review2/de-compare-390-*.png |

The native comparison region retains its keyboard access and horizontal scroll
when the translated or four-product table needs it. Product names remain whole.
The account browser tests verify both destinations, two/four-model access and
no document overflow. Exact pixel results, full source images and the measured
price-cell rectangles are in pixels-review2/ and pixel-results.md. The wider
interim captures remain historical evidence, not the current allowed regions.
