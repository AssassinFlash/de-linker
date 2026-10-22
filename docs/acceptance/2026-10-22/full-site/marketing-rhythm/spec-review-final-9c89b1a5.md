# Marketing rhythm 9c89b1a5 — independent Spec and saved-view review

**Bounded source PASS and three-group CTA visual PASS. Photo-header/menu runtime acceptance remains PENDING.** This is not overall page/site completion or a production verdict.

Reviewed on 2026-10-22 against `9aa0ffe43d65e3ed822ce085e346941c9953a5ef`. Both file hashes and the stated aggregate algorithm were independently checked. Aggregate `9c89b1a5b425cb684342175ec7d7f744ddf35724059d597bb7f512ea33547c8d` is SHA-256 of UTF-8 `path + NUL + file SHA256 + LF`, in manifest array order.

| Source | SHA-256 |
| --- | --- |
| `plugins/linker-commerce/content/windpress/chrome.css` | `a43202bb828ad63b0d7d49881af91be9bc42cd88c7bdd4aedb338d939aa905f9` |
| `plugins/linker-commerce/content/windpress/marketing-rhythm.css` | `7357cfbcc59b6450a47fbb3f577f202ec2bc27803ea2db40a06ea5be3d2ca5c3` |

Exact reviewer copies and manifest are retained at `/var/folders/mr/x4yftk6s7ql600b99wzjxs0w0000gn/T/marketing-spec-9c89-6lqogzle/`. This reviewer changed only this report. No product source, previous report, tracked test, browser, instance, build, or production was changed.

## Narrow source delta

The preserved b278 source was compared directly with this candidate. Chrome is byte-identical to its previous reviewed opaque-default-header repair. All three CTA groups’ declarations are unchanged. The only new declarations in marketing-rhythm are the inset photo-language focus offset (`-3px`) and the open-mobile-panel header surface/control reset.

The inset focus ring keeps the existing 2px white outline on the language half’s solid dark-green surface, rather than outside it on an uncontrolled photo. The language halves remain native 44×44px anchors, with current-language underline following `currentColor`; href, labels, current state, and routing are unchanged.

The menu reset requires the existing `#tv-mobile-panel[data-open="true"]` under `#lc-header`. It sets an opaque white header surface, restores the original logo filter, changes nav/search/close foreground to the existing ink token, and restores a teal/white CTA. It neither opens the panel nor changes disclosure semantics, focus handling, layout dimensions, or language. The selector applies to any existing open mobile panel, including non-photo pages; those pages already use this normal palette. No direct source-level conflict or unnecessary business behavior change was found. Actual effective cascade, hover/focus, menu close/reopen, and photo-to-scrolled transitions remain runtime checks, especially because the cover pages carry saved styles.

The earlier page-root-wide Service `br` and Application outline selector scope remains the same and is accurately bounded by the producer’s actual published-page inventory: one action group in each of the corresponding EN/DE pages. Capability and Thank You use different roots and are not matched. Existing PHP/LC prose and native links are untouched. The repair remains in WindPress, as required for page design.

## Twelve CTA views actually opened

Every JPEG below was opened individually and its matching JSON read. Captures were taken locally at `http://127.0.0.1:9290`, 06:25:07–06:25:58 UTC, after the accepted CTA cascade correction and before this header-only source delta. Those CTA declarations and chrome bytes are unchanged in 9c89; these images therefore support the unchanged CTA portion, not the newly added header states. JSON does not itself contain a CSS source/runtime fingerprint, so it is not represented as a cryptographic full-candidate runtime binding.

| Group | EN 1440 | EN 390 | DE 1440 | DE 390 |
| --- | --- | --- | --- | --- |
| Installer | [view](cua-local-20261022T0602/final-installer-en-1440.jpg) | [view](cua-local-20261022T0602/final-installer-en-390.jpg) | [view](cua-local-20261022T0602/final-installer-de-1440.jpg) | [view](cua-local-20261022T0602/final-installer-de-390.jpg) |
| Services | [view](cua-local-20261022T0602/final-services-en-1440.jpg) | [view](cua-local-20261022T0602/final-services-en-390.jpg) | [view](cua-local-20261022T0602/final-services-de-1440.jpg) | [view](cua-local-20261022T0602/final-services-de-390.jpg) |
| Application | [view](cua-local-20261022T0602/final-application-en-1440.jpg) | [view](cua-local-20261022T0602/final-application-en-390.jpg) | [view](cua-local-20261022T0602/final-application-de-1440.jpg) | [view](cua-local-20261022T0602/final-application-de-390.jpg) |

All 12 show clear separation of explanatory text from actions, complete button labels, and a visible primary/secondary hierarchy. Each matching readback confirms 32px paragraph-to-action gap, 12px action gap, 16px paragraph text, 14px action text, and 48px height for all 24 links; all report no horizontal overflow. Phone actions are a full-width column. Service’s direct line break is `display:none` in all four cases and no longer makes an empty row. Application’s outline has a complete 1px teal border in all four cases, matching its visual button shape.

German Application desktop naturally wraps its two long actions into two rows within the text column; both remain complete and aligned. This is allowed flex wrapping, not a clipped label or a forced English-length button. The other desktop action pairs fit side by side. Existing hyphenation in some German prose remains visible and does not lose text.

These captures intentionally locate the action region. Several Installer/Services headings have already scrolled partially behind the sticky header; this is not evidence of a missing top offset, and these action-positioned images do not establish full heading-top visibility. The earlier full Installer heading views remain separate evidence for unchanged heading declarations. No actual link-arrival, form submission, or full-page reading acceptance was executed by this reviewer.

## Header evidence rejected; no premature PASS

The original `header-residential-en-390-menu.jpg` was actually inspected: on the white panel, the cover’s white logo/search/close/CTA treatment is invisible. It is a genuine failed state, not a successful example.

The three subsequently named final Residential EN390 top/focus/menu records captured at 06:33:43–06:33:44 UTC were also individually inspected. They still show the old behavior: menu header computed transparent and missing visible top controls, with language focus offset `+2px` rather than the new `-3px`. This reviewer immediately reported that the runtime did not carry the new rules. The producer independently confirmed official generation had not advanced the cache/UI timestamp, rejected those records, and is preserving them as `compile6-rejected-*`. They are not evidence that 9c89 is active, and they grant no new-header PASS. The rejected compile3 CTA records likewise remain historical failure evidence.

Before the header portion can be accepted, verify actual compiled cache advancement/readback and inspect new-source EN/DE Residential and Commercial photo states at 1440/390: top/cover, scrolled opaque default, keyboard focus, mobile menu open/close/reopen, and readable visible logo/search/Close/CTA. Existing language destination/current state must remain correct. This is a runtime gate, not a reason to replace native markup or modify unrelated source speculatively.

No source-level Spec blocker is identified in these exact two files. The currently available evidence supports only the bounded source and unchanged CTA verdict above. New-header runtime, production readback, and the user’s broader all-site audit remain open.
