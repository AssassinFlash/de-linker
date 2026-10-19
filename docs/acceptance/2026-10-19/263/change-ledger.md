# #263 ruled German changes

Authority: AGENTS.md §2 (owner 2026-10-17, "switched to German, everything is
German-only — addresses, titles, copy") and the audit findings of ticket #255
(`docs/research/2026-10-17-i18n-audit/AUDIT.md`, H1, H2, H3, H5, M2, M8, M9).
English pages are unchanged: the EN pixel gate below reports zero differing
pixels outside the regions other tickets already registered.

| Change | Before | After / bounded region |
|---|---|---|
| German category breadcrumb names (H5) | `before/category-breadcrumb-1440-live.jpg`, `before/category-breadcrumb-390-live.jpg` (audit: "STARTSEITE / PRODUKTE / INVERTERS" above the German heading) | `after/category-breadcrumb-1440-local.png`, `after/category-breadcrumb-390-local.png`: every segment is the queried German term's name; the home segment links `/de/`. The whole breadcrumb row is the ruled region; nothing else on the page changes. |
| German product page "Produkt anfragen" target (H1) | audit `h1-pdp-anfragen-button-1440.jpg` | `after/pdp-1440-local.png`: href-only change to `/de/kontakt/?intent=product…`; no pixel change. |
| German legal pages' document links (H3) | audit `h3-legal-links-impressum-1440.jpg` | `after/legal-impressum-1440-local.png`: the right-column links target `/de/impressum/`, `/de/datenschutz/`, `/de/verkaufsbedingungen/`, `/de/rueckgabe-erstattung/`; href-only. |
| German footer language switch (H2) | audit `h2-footer-lang-de-page-1440.jpg` | the footer's "Englisch" now opens the English twin of the current page, not `/de/`; the header and footer share one implementation. Href-only; the visible words and layout are unchanged. |
| German blog post category links and `/de/danke/` (M2) | audit `m2-blog-cta-english-category-1440.jpg`, `m2-danke-blog-link-1440.jpg` | render-time localization points them at the German current categories and `/de/blog/`; href-only. |
| German compare breadcrumb (M2) | audit text finding: "Startseite" → `/` | `after/compare-1440-local.png`: "Startseite" → `/de/`; href-only. |
| Polylang canonical redirect query value (M8) | audit `text-m8-redirect-strips-de.txt` | the requested `source` value keeps its `/de/` (no 301 for the checked request; unit fixture `CanonicalQueryTest`); no pixel change. |

No mask, tolerance or dynamic-region exemption is introduced. Browser titles
and SEO metadata are not changed by this ticket.
