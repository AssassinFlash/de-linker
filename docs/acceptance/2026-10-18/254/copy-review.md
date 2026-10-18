# German title copy review

Scope: document titles and the few visible names required by renamed routes. Existing independent German SEO copy stays intact. The inquiry design uses existing EN/DE text; it adds no new marketing promise or form requirement.

| Initial candidate | Adversarial objection | Final German wording |
|---|---|---|
| Partnerkonto: Anmelden oder Registrieren | One title describes two different pages and does not identify the current task. | Login: **Beim Partnerkonto anmelden**; registration: **Partnerkonto erstellen** |
| Partnerkonto / lost password | The account label does not identify password recovery; an English endpoint is unsuitable for German visitors. | **Passwort zurücksetzen** |
| Warenkorb | Prohibited customer vocabulary; the workflow is an inquiry, with a solution draft as its input. | **Lösungsentwurf** |
| FAQ & Downloads | Descriptive English is unnecessary for the document destination. | **FAQ & Dokumente** |
| Service & Support | The destination is the customer's service page. | **Kundendienst** |
| All-in-One-Systeme / EMS-Monitoring | The route must contain German descriptions; the visible category name must agree with it. | **Komplettsysteme** / **EMS und Überwachung** |
| EcoFlow Battery Stack Bridge | A descriptive English product accessory is not a model identifier. | **EcoFlow Verbinder für Batteriestapel** |
| Anfrage / Anfrage eingegangen | Repeated inquiry pages would share a title and lose their identity in browser tabs. | **Anfrage {number}** / **Anfrage eingegangen – {number}** |
| Products / Posts / Page 2 | Generic English labels cannot identify a German archive. | **Produkte: {German category}**, **Beiträge: {German category}**, **{title} – Seite {number}** |

English message identifiers identify each task (sign in, create an account, reset password, solution draft, FAQ and documents). German wording was composed for the German task and formal locale, using the existing project terminology. Brand and model tokens remain unchanged. No body copy, dates, product claims or general descriptions are rewritten here.

The final full route table is the review surface for uniqueness and German expression. Automated checks decode HTML entities and normalise whitespace before comparing actual document titles. Model-only titles are allowed where the native German product's title is its proper model name. Full Spec review includes this table and these copy decisions.

## Topic navigation label review

Initial EN “All articles” / DE “Alle Artikel” was both prohibited vocabulary and misleading as a selected pill on a category page. “All topics” / “Alle Themen” describes the route back to the journal index; it remains a quiet unselected link. The native category list selects only the current topic with `aria-current="page"`. No category names, summaries, product facts or promises are rewritten.

## Content-platform journal copy

The owner supplied visual references for a YouTube-like browsing experience. Draft EN “Know more. Plan with confidence.” was rejected in review as a vague benefit claim. Final EN **“Knowledge for your next project.”** / DE **“Wissen für Ihr nächstes Projekt.”** names the reading task without a promise. The supporting lines are **“Technical guidance for installers and EPCs.”** / **“Praxiswissen für Installationsbetriebe und EPCs.”**

Navigation and actions: **All topics / Alle Themen**, **Topics / Themen**, **Search the journal / Journal durchsuchen**, **Search / Suche**, **Latest / Aktuell**, **All posts / Alle Beiträge**, **Read more / Weiterlesen**, **More from the journal / Mehr aus dem Journal**, **Resources / Ressourcen**. “Latest” is backed by the native descending publication-date query. The rail is described as more reading; it makes no invented popularity, watch-history or recommendation-personalization claim.

Empty search: **“No matching posts found. Try another search term or choose a topic.”** / **“Keine passenden Beiträge gefunden. Versuchen Sie einen anderen Suchbegriff oder wählen Sie ein Thema.”** Both explain a real next action. The configurator remains **“Open the Solution Configurator” / “Lösungskonfigurator öffnen”**, with **“From reading to a system plan.” / “Von der Recherche zur Planung.”** Existing product/post facts and titles are not rewritten. German collection metadata uses a German description of this same audience and subject.

## Reading-page navigation

The reader reference calls for clear reading controls. Final labels: **On this page / Auf dieser Seite**, **Post sections / Abschnitte dieses Beitrags**, **Overview / Überblick**, **Post details / Beitragsdetails**, **Related reading / Passende Beiträge**, **Share / Teilen**, **Published / Veröffentlicht**, **Previous post / Vorheriger Beitrag**, **Next post / Nächster Beitrag**. Existing **Back to blog / Zurück zum Blog** and project-quote labels stay. Review rejected invented watch history, rating, follower, like, read-time or popularity indicators: none has a backing data contract here. Post body, facts and actual author/date remain native.

Sharing detail review: the native LC tooltip “Share on …” is hard-coded English even in the German template. The final toolbar uses the actual platform name for both `title` and `aria-label`, under the localized **Share / Teilen** heading. Brand names and native share destinations are preserved; no new marketing claim or body copy is added.

## Owner-requested concise discovery labels

The owner found full headings too dense in both the mobile list and desktop content-dashboard view. Initial proposal: truncate full titles to two lines. Review objection: mechanical truncation can hide the actual comparison or decision. Final: separately reviewed short labels for discovery, while the native full title remains in the reader and browser title.

Independent adversarial review requested five refinements: make the first comparison explicitly about a hybrid inverter; retain the home-storage qualifier in sizing; use PV rather than the vague German Solar; preserve monitoring in the data-layer label; and name the concrete home-storage backup/expansion subjects. All five were incorporated below. The other five pairs were assessed as natural and accurate.

The checked-in copy resolves through English source identity and Polylang; a new or subsequently changed post falls back to its native full title. No native post title, SEO title, excerpt, body or URL is overwritten.

| English short label | Independently written German short label |
|---|---|
| Hybrid inverter or AC storage? | Hybridwechselrichter oder AC-Speicher? |
| Pairing inverters and batteries | Wechselrichter und Batterie kombinieren |
| Sizing home storage for backup | Heimspeicher für Notstrom auslegen |
| Battery storage: indoors or outdoors? | Batteriespeicher: innen oder außen? |
| Commissioning solar and storage | PV und Speicher in Betrieb nehmen |
| Documents for project handover | Dokumente für die Projektübergabe |
| Remote monitoring after installation | Fernüberwachung nach der Installation |
| Gateways, meters and cloud monitoring | Gateway, Zähler und Fernüberwachung |
| Home storage: backup and expansion | Heimspeicher: Notstrom und Ausbau |
| Planning commercial battery storage | Gewerbespeicher planen |

The labels retain specific subjects without invented popularity or technical outcomes. German uses natural noun/verb phrases without informal address. The native LC post-field callback receives each exact loop item, and unrelated fields return null to continue native behavior.
