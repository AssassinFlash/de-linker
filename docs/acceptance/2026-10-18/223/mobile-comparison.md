# Mobile comparison correction

The owner inspected c223 at 390px and rejected the squeezed comparison columns
and wrapped Create account entry. This is an explicit visual bug correction in
this ticket, recorded independently of the original link insertion.

The original two-product table allocated approximately 113px per product,
including 24px horizontal padding. That left about 89px for names and actions;
the account entry occupied two lines. Four products make this worse.

The mobile comparison now retains a 14rem (224px at the site's 16px root)
minimum product column inside the existing horizontally scrollable region.
The 7rem row-label column stays fixed while the products scroll. At 390px,
the first product fits and the next column edge remains visible. This uses the
existing storefront comparison's 600px narrow-table boundary and 7rem label
width; 14rem is the measured space for a readable model and both account links.
No model text is hidden or truncated, and the page itself does not overflow.
The native comparison region keeps its keyboard focus and accessible label.

LC `account/compare-price.html` supplies a real sign-in anchor and an independent
Create account / Konto erstellen anchor. WindPress handles their spacing and
column geometry. No hidden duplicate prompt is used to manufacture page height.

Evidence: `before-products/*-compare-390-before.png`, corrected Computer Use
screens in `computer-use/`, and the two/four-product browser tests in
`checks/entries-report.json`. Full live/local image sizes remain exact inputs
to the comparator. The deliberately corrected mobile table can change page
height; this remains a dimension failure under the strict pixel gate and is
reported **未完成**, not cropped, padded, or silently accepted.

## Whole-page correction after the second owner inspection

The owner rejected the column-only adjustment because the whole comparison page
still broke from the site's design. The LC template used a generic large heading
and never mounted `.sf-compare`; existing storefront rules targeted
`.sf-compare-table` while the live shortcode emitted `.linker-compare-table`.
The font, heading hierarchy, background, container, image treatment, row labels
and actions therefore did not reach the established design layer.

Both language templates now mount the existing `.sf-compare` shell. Its existing
20px/500 heading, Jakarta type, white paper, 1360px container and ghost button are
used directly. Existing storefront comparison rules are shared with the actual
`linker-compare-*` selectors rather than copied into a second design. The LC
breadcrumb and intro use the existing product-list metrics. Customer wording is
retained. Mobile product columns remain readable inside the native scroll region.
`checks/comparison-shell-red.log` records the prior 36px heading against the
existing storefront's 20px design contract. New screenshots must show the whole
page shell, not just the new link.

The base `.sf-compare` rules alone were not the final reference: the served
product list has later overrides in `products.css`. The final shell therefore
shares those actual declarations: paper background, 46px/600 desktop title,
30px/600 phone title, teal uppercase crumbs, the same responsive container and
muted intro scale. Measurements are saved with the product-list reference
screens. This supersedes the interim 20px base-heading check above.
