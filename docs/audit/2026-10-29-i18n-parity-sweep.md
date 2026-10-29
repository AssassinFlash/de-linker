# EN/DE localisation parity sweep — customer surface (2026-10-29)

Whole-surface inventory of localisation violations over the live customer
surface, per the parity rules in `AGENTS.md` §3. Evidence is read-only:
production sitemap crawl + `curl`, plus repo catalogue gates. Worktree
branch `codex/sweep-i18n-parity`.

## Method

- `https://de-linker.com/sitemaps.xml` → 5 sub-sitemaps (post, page,
  product, product_cat) → **261 unique URLs** (130 `en-US`, 132 `de-DE`
  by sitemap `lang`), plus one URL listed in the EN sitemap that serves
  404 (`/danke/`). 262 pages fetched; visible body text and hreflang
  alternates extracted; pages paired by hreflang → **130 EN/DE pairs**.
- Surface covered: marketing, blog (index/single/category/search),
  product, product category, legal, header/footer, Genie page and panel
  mount, solution draft, configurator, compare, my-account, proforma
  request, error and empty states (404 body, empty search/archive
  branches verified in the LC templates).
- Repo side: `msgfmt --statistics` / `msgattrib` over all three
  `*-de_DE_formal.po` catalogues, `just i18n-coverage` and
  `just i18n-validity` gates, and the DE LiveCanvas templates under
  `plugins/linker-commerce/content/livecanvas/de/`.

## Verdict

**Every repo-owned localisation surface is clean.** All remaining
violations live in production database content (WooCommerce product
long descriptions, document-library meta, Polylang page pairing) and
cannot be fixed from this repo. This task's scope is read-only against
production, so they are inventoried below with exact locations and the
exact blocker.

## Inventory by sub-kind

### 1. Mixed language (English sentences on DE pages)

**99 English document-library description strings on 35 DE pages.**
One pattern — the document-library *description* field was written in
English and renders verbatim on German pages. Exact recurring strings:

- "Certificate of conformity VDE-AR-N 4105:2018-11 for the SAJ CHS2
  series, German and English (names the CHS2-29.9K-T4-X)"
- "EU declaration of conformity for the SAJ BU3 battery and the
  BC3-TV, several languages including English and German (names the
  BU3-5.0-TV2-PRO)"
- "SAJ CHS2 30-50K datasheet with the CB2 battery table, English
  (covers the CB2-100.3-HV5), S. 2"
- …same construction for every SAJ/GoodWe/Pylontech document row.

Pages (35): `de_faq-dokumente_.html` carries 20; the rest are SAJ and
GoodWe product pages (`/de/produkt/saj-*`, `/de/produkt/goodwe-*`),
1–4 strings each (full per-page counts in
`/tmp/sweep-i18n/` on the sweep machine; reproducible with the
pattern `names the|covers the|including English|German and English`
over extracted DE body text).

Borderline (owner call, not counted as violations): 95 English
*official document titles* on 57 DE pages, e.g. "Certificate of
conformity, Low Voltage Directive, AN 50703461 0001" — official names
of the source PDFs, proper-noun-like, but a German label row would
read better.

English pages carrying German: **0**.

### 2. Missing EN/DE counterpart

**1 violation.** `/de/danke/` (DE thank-you, in the DE sitemap) has no
working EN counterpart. Its own footer language switcher and the EN
sitemap list `https://de-linker.com/danke/`, which serves
"Page not found" (404); `/thank-you/` also 404s. Blocker: the EN twin
page must be created in production (Polylang pairing) — a production
data write.

### 3. Terminology (CONTEXT.md / AGENTS.md §3)

**1 candidate.** Document title `chint dtsu666 catalog en` (lowercase,
English, uses "catalog") renders on `/faq-download/` (EN),
`/de/faq-dokumente/` and `/de/produkt/chint-dtsu666/`. The title is
production document-library data.

All other vocabulary checks: **0 violations**. Product/Produkt,
Produktkategorie, Lösungsentwurf, Stückliste, the four inquiry status
terms, no cart/basket/Warenkorb words anywhere on either language.

### 4. Sie-form and banned constructions

**0 violations.** No du/dich/dein forms; no "nicht … sondern"; no
triple-parallel constructions in German copy.

### 5. Date / number / currency formatting

**27 EN-style comma-thousands numbers on 14 DE pages** (German must
use `29.999 kW`):

- `29,999 kW` / `9,999 kW` (power figures in product descriptions and
  cross-links): `/de/produkte/`, `/de/produkt-kategorie/wechselrichter/`,
  `/de/faq-dokumente/`, `/de/produkt/goodwe-esa-gw29-999k-*`,
  `/de/produkt/goodwe-esa-gw9-999k-*`, `/de/produkt/saj-chs2-29-9k-t4-x/`,
  `/de/produkt/saj-h2-30k-t3-de/`, and the GoodWe ESA battery-module
  pages `gw5-1-bat-*`, `gw6-0-bat-*`, `gw8-3-bat-*`, `gw9-0-bat-*` (ESA
  cross-links in the description).
- `59,998 kW` (CHS2 29.9K pairing note on its product page).
- `3,125 / 5,015 / 5,016 / 6,901 MWh` on `/de/loesung/grossspeicher/`.

Dates: **0 violations** — DE pages render `d.m.Y` / German dates
("7. April 2025", "29. September 2026"); the DE LC templates use
`date_format="d.m.Y"` throughout. Currency: none rendered.

### 6. .po/.mo gaps for customer-visible strings

**0 violations.** `linker-i18n` (46/0), `linker-tools` (2352/0) fully
translated. `linker-commerce` has 58 untranslated entries, all exempted
by `tools/checks/i18n-exempt.json` with audited evidence: 41 WordPress
Abilities labels/descriptions (consumed by the Genie service over
`wp-abilities/v1`, not rendered on any page — confirmed: the Genie
conversation UI in `plugins/linker-tools/src/genie/` renders only its
own catalogued strings), 2 internal digest lines, 15 ERP stock-push /
engineering-feed REST schema descriptions. `just i18n-coverage` and
`just i18n-validity` both pass clean on this branch.

During the sweep all 41 Abilities strings were provisionally
translated into formal German and compiled; the change was reverted
because it contradicts the audited exemption list (the gate rejects
stale exemptions) and no customer page renders these strings. The
translations are recorded here should the Abilities UI ever become
customer-visible:

- Check inverter and battery compatibility → Wechselrichter und
  Batterie auf Kompatibilität prüfen
- Compare products → Produkte vergleichen
- Get a product → Ein Produkt abrufen
- Hand off to the Linker team → An das Linker-Team übergeben
- List my inquiries → Meine Anfragen auflisten
- Read a saved solution → Eine gespeicherte Lösung lesen
- Open the Solution Configurator with these inputs →
  Lösungskonfigurator mit diesen Eingaben öffnen
- (34 further descriptions in the sweep transcript)

## Fixed in this round

Nothing in the repo — the repo-owned surfaces were already clean:
DE templates use `d.m.Y`, own share markup and `/de/`-prefixed links
(the 2026-10-17 audit's M1/M2 findings are fixed in
`plugins/linker-commerce/content/livecanvas/de/`), catalogues cover
every customer-visible string, and both i18n gates pass.

## Not fixed, with exact blockers

| Violations | Location | Blocker |
|---|---|---|
| 99 EN doc descriptions (35 DE pages) | production document-library meta | production data write; this task is read-only against production |
| 1 missing EN twin | `/danke/` page creation + Polylang pairing | production data write |
| 1 `chint dtsu666 catalog en` title | production document-library title | production data write; owner should also confirm the German title wording |
| 27 comma-thousands numbers (14 DE pages) | production product long descriptions | production data write |
| 95 EN official doc titles (57 DE pages, borderline) | production document-library titles | owner decision + production data write |

All five rows are one content-repair pass over the production DB
(document-library meta + product descriptions + one new EN page),
executable under the standing production-write rules (backup → write →
read back) once a session with write scope picks it up.
