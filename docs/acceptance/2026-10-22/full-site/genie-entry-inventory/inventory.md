# All published-page Genie entry inventory — local read-only

This audit reads the current `privacyviz` snapshot at `http://127.0.0.1:9270`; it is not a production acceptance claim. All 50 published WordPress Pages were resolved through their real current URLs and rendered in Chromium. The page list was taken from WordPress, not a guessed sitemap. Every response was HTTP 200, with no page JavaScript errors and zero attempted turn calls during the passive inventory.

Only this evidence directory was written. No product source, build, model, routing, database, production session or email was changed. The active history-locale/layout source stayed frozen. Interactive checks used fresh guest browser contexts; turn/conversation endpoints were intercepted locally. No real model or mail call was made. Source snippets in `source-excerpts.json` are current rendered local HTML, not instructions.

## Findings with actual consumers distinguished

1. **Residential and Commercial (four EN/DE Pages): the editable question is lost on Send.** At both 1440 and 390, entering a question and clicking the real `.lk-send-btn` navigates to the correct-language Genie page. There is no `linker-genie-ask` event, turn POST, question query parameter, or question in destination input/session storage. The destination loader emits only an empty `linker-genie-open`. This is a stable missing handoff, not a model failure.
2. **Installer (two EN/DE Pages): mobile question and device actions are not connected.** The visible mobile `#installer-mobile-query` plus `.installer-assistant-send` loses the question in the same way. Nameplate, attachment and voice buttons are enabled but their clicks produce no current ask event, picker, or speech start. Their `data-linker-assistant-open` attribute is consumed by the current hero controller only inside the homepage hero; that bundle is deliberately enqueued only on the front page. There is no global consumer for this attribute.
3. **Installer desktop has a separate destination contract.** `#lki-hero-query` is next to “Plan a Project Solution”; Enter clicks the fixed `.lk-btn-query` link to the current-locale Solution Configurator. The input value is never read. The configuration page currently supports structured size-hint fields, not arbitrary raw query text. This must preserve its planning purpose when repaired; it must not be silently rerouted or lose the useful input. Details and reproduction below.
4. **Residential/Commercial suggestions are working prefill controls.** All twelve suggestion anchors have a page-specific listener which prevents navigation, copies the label into `.lk-dialog-prompt`, and focuses that field. The eight first-suggestion clicks across EN/DE and both widths all match exactly. They do not promise an automatic answer in the current implementation. The subsequent Send still loses the prefilled question. Do not report these as dead links merely from their `href`, or change this interaction accidentally.
5. **Residential photo/voice affordances are disabled; Commercial affordances are enabled but inert.** These are different states. The two Residential pages each contain disabled attachment/voice buttons, so no click was forced. Commercial has both enabled at both widths: every click is inert. Across Commercial and mobile Installer, 14 visible enabled action-button clicks produced no file chooser, no speech start, and no current event. A stub browser speech constructor was available; native microphone access was not used.
6. **Current supported entries work in the same local runtime.** Homepage EN/DE typing reaches the intercepted turn with the complete question and locale; its attachment picker opens once, and voice starts the shared browser dictation with `en-US`/`de-DE`. Products EN/DE question chips deliver the complete text through `linker-genie-ask` to one intercepted turn. Ordinary Contact “Explore with Genie” links navigate without a turn, as appropriate for pure navigation. These positive controls separate missing marketing wiring from a broken global loader.
7. **Legacy mentions are not themselves failing controls.** Twenty page sources contain the inherited `lia:ask` script. Its old `initHome` is gated by home page/root selectors and emits an event with no current Genie listener. On most of these pages there are no corresponding editable assistant controls. The table therefore marks actual controls separately from this residue; it does not turn 20 source-text occurrences into 20 buyer-facing failures.

The raw DOM includes 196 `/genie/` anchors, 54 current-loader trigger elements, 18 `data-lk-ask` suggestions and 20 legacy-mode device controls. These are **DOM counts including responsive/menu/fallback elements**, not counts of visible independent tasks. The four-page marketing composer heuristic in `pages.json` was supplemented by reading **all input and textarea elements**, which is how the Installer pair was found.

## Complete 50-page table

`N` is the number of generic Genie anchors in the real DOM; `O` is current `[data-linker-genie-open]` triggers. Counts include hidden responsive alternatives. A current trigger is identified by the common loader consumer; only named interactive controls in the matrix below were individually clicked. Ordinary contact/inquiry forms were read, never submitted.

| ID | Locale | Page and current route | Question/control classification | N / O | Legacy source mention |
|---:|:---:|---|---|:---:|:---:|
| 13 | EN | Home<br>`/` | Homepage prompt + 3 direct-question capsules + photo/attach/voice; current hero consumer verified | 7 / 1 | yes |
| 14 | EN | Blog<br>`/blog/` | Journal search, ordinary local search; current helper opener | 3 / 1 | no |
| 28 | EN | Contact<br>`/contact/` | Contact form is human contact; standalone Genie link pure navigation | 4 / 1 | yes |
| 623 | EN | Thank You<br>`/thank-you/` | Generic Genie navigation + current helper opener; no question-like editor | 3 / 1 | no |
| 746 | EN | Application<br>`/solution/` | Generic Genie navigation + current helper opener; no question-like editor | 3 / 1 | yes |
| 749 | EN | Residential Storage<br>`/solution/residential-storage/` | Question Send loses input; 3 capsules correctly prefill; attach/voice disabled | 8 / 1 | yes |
| 792 | EN | Commercial Storage<br>`/solution/commercial-storage/` | Question Send loses input; 3 capsules correctly prefill; enabled attach/voice inert | 8 / 1 | yes |
| 826 | EN | For Installer<br>`/for-installer/` | Mobile Ask/device actions missing consumer; desktop Plan navigates without consuming input | 5 / 1 | yes |
| 842 | EN | For EPC<br>`/for-epc/` | Generic Genie navigation + current helper opener; no question-like editor | 3 / 1 | yes |
| 862 | EN | About<br>`/about/` | Generic Genie navigation + current helper opener; no question-like editor | 3 / 1 | yes |
| 874 | EN | Capability<br>`/about/capability/` | Generic Genie navigation + current helper opener; no question-like editor | 3 / 1 | no |
| 932 | EN | FAQ Download<br>`/faq-download/` | Questions/documents library search, ordinary filtering; current helper opener | 3 / 1 | no |
| 1034 | EN | Products<br>`/products/` | Product search: current question detector/chip verified; numeric filters ordinary | 3 / 4 | no |
| 1035 | EN | Cart<br>`/cart/` | Generic Genie navigation + current helper opener; no question-like editor | 3 / 1 | no |
| 1036 | EN | Proforma request<br>`/proforma-request/` | Inquiry form, ordinary buyer submission; current helper opener; no send tested | 3 / 1 | no |
| 1037 | EN | My account<br>`/my-account/` | Account credentials, ordinary form; current helper opener | 3 / 1 | no |
| 1038 | EN | Refund and Returns Policy<br>`/refund-returns/` | Generic Genie navigation + current helper opener; no question-like editor | 3 / 1 | no |
| 1672 | EN | Imprint<br>`/imprint/` | Generic Genie navigation + current helper opener; no question-like editor | 3 / 1 | no |
| 1673 | EN | Privacy Policy<br>`/privacy-policy/` | Generic Genie navigation + current helper opener; no question-like editor | 3 / 1 | no |
| 1674 | EN | Terms of Sale<br>`/terms-of-sale/` | Generic Genie navigation + current helper opener; no question-like editor | 3 / 1 | no |
| 1755 | EN | Utility-Scale Storage<br>`/solution/utility-storage/` | Generic Genie navigation + current helper opener; no question-like editor | 3 / 1 | yes |
| 2748 | EN | Services & Support<br>`/services-support/` | Generic Genie navigation + current helper opener; no question-like editor | 3 / 1 | yes |
| 3302 | EN | Solution Configurator<br>`/solution-configurator/` | Structured Configurator fields; current helper opener; not a free-text assistant prompt | 3 / 1 | no |
| 4083 | EN | Genie - Linker's AI assistant<br>`/genie/` | Current Genie workspace composer (history/live/reload covered by prior 12-case matrix) | 9 / 0 | no |
| 5385 | EN | Compare products<br>`/compare-products/` | Generic Genie navigation + current helper opener; no question-like editor | 3 / 1 | no |
| 6600 | DE | Produkte vergleichen<br>`/de/produkte-vergleichen/` | Generic Genie navigation + current helper opener; no question-like editor | 3 / 1 | no |
| 6633 | DE | Genie – der KI-Assistent von Linker<br>`/de/genie/` | Current Genie workspace composer (history/live/reload covered by prior 12-case matrix) | 9 / 0 | no |
| 6693 | DE | Lösungskonfigurator<br>`/de/loesungskonfigurator/` | Structured Configurator fields; current helper opener; not a free-text assistant prompt | 3 / 1 | no |
| 6698 | DE | Rückerstattungs- und Rücksenderichtlinie<br>`/de/rueckgabe-erstattung/` | Generic Genie navigation + current helper opener; no question-like editor | 3 / 1 | no |
| 6700 | DE | Kundendienst<br>`/de/kundendienst/` | Generic Genie navigation + current helper opener; no question-like editor | 3 / 1 | yes |
| 6825 | DE | Verkaufsbedingungen<br>`/de/verkaufsbedingungen/` | Generic Genie navigation + current helper opener; no question-like editor | 3 / 1 | no |
| 6827 | DE | Datenschutzerklärung<br>`/de/datenschutz/` | Generic Genie navigation + current helper opener; no question-like editor | 3 / 1 | no |
| 6829 | DE | Impressum<br>`/de/impressum/` | Generic Genie navigation + current helper opener; no question-like editor | 3 / 1 | no |
| 6853 | DE | Wechselrichter, Speicher und Systeme<br>`/de/produkte/` | Product search: current question detector/chip verified; numeric filters ordinary | 3 / 4 | no |
| 6855 | DE | Lösungsentwurf<br>`/de/loesungsentwurf/` | Generic Genie navigation + current helper opener; no question-like editor | 3 / 1 | no |
| 6857 | DE | Proforma-Anfrage<br>`/de/proforma-anfrage/` | Inquiry form, ordinary buyer submission; current helper opener; no send tested | 3 / 1 | no |
| 6859 | DE | Mein Konto<br>`/de/mein-konto/` | Account credentials, ordinary form; current helper opener | 3 / 1 | no |
| 6863 | DE | FAQ & Dokumente<br>`/de/faq-dokumente/` | Questions/documents library search, ordinary filtering; current helper opener | 3 / 1 | no |
| 6865 | DE | Über uns<br>`/de/ueber-uns/` | Generic Genie navigation + current helper opener; no question-like editor | 3 / 1 | yes |
| 6867 | DE | Für EPC<br>`/de/fuer-epc/` | Generic Genie navigation + current helper opener; no question-like editor | 3 / 1 | yes |
| 6869 | DE | Für Installateure<br>`/de/fuer-installateur/` | Mobile Ask/device actions missing consumer; desktop Plan navigates without consuming input | 5 / 1 | yes |
| 6871 | DE | Anwendung<br>`/de/loesung/` | Generic Genie navigation + current helper opener; no question-like editor | 3 / 1 | yes |
| 6873 | DE | Vielen Dank<br>`/de/danke/` | Generic Genie navigation + current helper opener; no question-like editor | 3 / 1 | no |
| 6907 | DE | Kontakt<br>`/de/kontakt/` | Contact form is human contact; standalone Genie link pure navigation | 4 / 1 | yes |
| 6913 | DE | Startseite<br>`/de/` | Homepage prompt + 3 direct-question capsules + photo/attach/voice; current hero consumer verified | 7 / 1 | yes |
| 6915 | DE | Blog<br>`/de/blog/` | Journal search, ordinary local search; current helper opener | 3 / 1 | no |
| 6917 | DE | Großspeicher<br>`/de/loesung/grossspeicher/` | Generic Genie navigation + current helper opener; no question-like editor | 3 / 1 | yes |
| 6919 | DE | Leistungsfähigkeit<br>`/de/ueber-uns/leistungsfaehigkeit/` | Generic Genie navigation + current helper opener; no question-like editor | 3 / 1 | no |
| 6921 | DE | Gewerblicher Speicher<br>`/de/loesung/gewerbespeicher/` | Question Send loses input; 3 capsules correctly prefill; enabled attach/voice inert | 8 / 1 | yes |
| 6923 | DE | Heimspeicher<br>`/de/loesung/heimspeicher/` | Question Send loses input; 3 capsules correctly prefill; attach/voice disabled | 8 / 1 | yes |

## Interactive matrix (fresh guest contexts)

All text cases have a real visible editable input; none used force clicks. File choosers were canceled with an empty selection. Speech was a deterministic browser capability stub which records `start()`; this audit proves the caller is or is not wired, not microphone recognition quality.

| Page type | Locale | Width | Actual destination | Question turn / ask event | Enabled visible device controls | Suggestion behavior |
|---|:---:|---:|---|:---:|---|---|
| residential | EN | 1440 | `/genie/` | 0 / 0 | none (disabled or desktop-hidden) | prefills exact label |
| commercial | EN | 1440 | `/genie/` | 0 / 0 | attach, voice → no action | prefills exact label |
| installer | EN | 1440 | `/solution-configurator/` | 0 / 0 | none (disabled or desktop-hidden) | not present |
| residential | EN | 390 | `/genie/` | 0 / 0 | none (disabled or desktop-hidden) | prefills exact label |
| commercial | EN | 390 | `/genie/` | 0 / 0 | attach, voice → no action | prefills exact label |
| installer | EN | 390 | `/genie/` | 0 / 0 | nameplate, attach, voice → no action | not present |
| residential | DE | 1440 | `/de/genie/` | 0 / 0 | none (disabled or desktop-hidden) | prefills exact label |
| commercial | DE | 1440 | `/de/genie/` | 0 / 0 | attach, voice → no action | prefills exact label |
| installer | DE | 1440 | `/de/loesungskonfigurator/` | 0 / 0 | none (disabled or desktop-hidden) | not present |
| residential | DE | 390 | `/de/genie/` | 0 / 0 | none (disabled or desktop-hidden) | prefills exact label |
| commercial | DE | 390 | `/de/genie/` | 0 / 0 | attach, voice → no action | prefills exact label |
| installer | DE | 390 | `/de/genie/` | 0 / 0 | nameplate, attach, voice → no action | not present |

`actions.json` records the empty destination input, no query-string handoff, no storage handoff and individual click deltas. A blank workspace `linker-genie-open` event is expected when the destination mounts; it is not delivery of the source question. The before/after PNGs are named exactly by the matrix key, e.g. `residential-de-390-before.png` / `-after.png` and `installer-en-1440-before.png` / `-after.png`.

The six positive controls are in `supported.json` and `supported-{home,search,nav}-{en,de}-1440.png`. Home and Products each produce exactly one **intercepted** turn per language carrying the original question. Navigation produces zero turns. These fixtures did not contact a model.

## Root cause and existing replication seams

- Current loader: `plugins/linker-tools/includes/Genie/Entries.php`, current ask listener and delegated `data-linker-genie-open` listener. It queues delivery until `linker-genie-ready`. Current Product search, PDP and proactive previews already use this seam.
- Current home: `src/hero/controller.tsx` binds real textarea/Send/Enter/capsules and mode buttons inside `.hero-cinematic`; `includes/Genie/Hero.php` limits loading to front pages. The migration-era modes on non-home marketing pages are not global entry registration.
- Marketing page-specific suggestion JS exists and populates input correctly. Marketing Send anchors have only normal Genie `href`; no consumer reads the actual marketing prompt on click/Enter. Renaming the legacy `lia:ask` event alone would not bind `.lk-send-btn` or Installer controls, or fix the old page/root guard.
- The current Genie workspace does not read arbitrary incoming question URL arguments or a general source-page question store. Session storage is only the existing unfinished/failed turn contract. Adding a raw `?q=` alone would still have no consumer.
- Current attachment seam: the proactive preview emits `{attach:true}`; the loader opens the app and shows the existing explicit Choose photo/file action. This respects browser user-gesture restrictions. The homepage can open its already-created picker within the original click. Current `{message:...}` and `{attach:true}` branches are mutually exclusive: a combined payload cannot be assumed to preserve both draft and attachment.
- Current voice seam: `src/genie/shared/dictation.ts`, already shared by App and homepage. It uses browser speech recognition; there is no `voice` loader event contract. Do not enable a button without wiring its result to the same editable draft, or add a new speech/model channel.

## Installer desktop: preserve the destination and inputs

Rendered `installer-journal.js` reads the input element only to attach keydown; Enter calls `planLink.click()`. The anchor is fixed `/solution-configurator/` or `/de/loesungskonfigurator/`. Neither click nor Enter takes `.value`.

The established structured handoff is `linker/size-hint` → `configurator_url`: `pv_kwp`, `annual_kwh`, `phase`, `backup`, `plz`. `plugins/linker-commerce/includes/Abilities/SizeHint.php` constructs it; `includes/Configurator/Mount.php` validates these public fields; `src/configurator/config.ts` reads their mount attributes into the form. The current Genie sizing route already supplies these values and produces an `open_configurator` action. The Configurator does not currently accept free-form equipment/manufacturer/manual questions, and a bare `?query=` has no consumer.

The additional EN/DE sizing reproduction enters 10 kWp, 6000 kWh/year, single-phase, backup and postcode 80538, then presses Enter. Both arrive at the bare locale Configurator URL, with no size-hint mount attributes; the form still has empty postcode/annual/PV inputs, three-phase and no-backup defaults. The evidence excludes public REST nonces.

The Plan CTA must keep planning as its destination. The next implementation should reuse the established structured handoff for stated sizing values, and preserve the original requirement when it does not map to those fields. The existing same-page Genie helper can resolve an arbitrary model/compatibility/document query and use its current sizing action to continue to a prefilled Configurator. Any direct plan-entry requirement carry needs an explicit consumer on the Configurator page; silently adding a parameter, blindly parsing numbers into sizing, deleting the input, or changing every Plan CTA into a direct Genie navigation is not a complete fix. The input currently advertises equipment/manual search while its adjacent CTA plans a project; this is the specific semantic conflict to settle, with the useful input retained.

This recommendation follows `docs/specs/13-genie.md` (one assistant, current entry loader, structured sizing and original-question preservation), `docs/specs/14-solution-configurator.md` (structured inputs) and the already collected Configurator sources dossier (short planning entry with carried project facts). No new competitor claim or model integration was invented.

## Unified narrow repair plan (not implemented here)

1. Preserve LC layout and current labels/locale routes. Keep ordinary “Open Genie” navigation as navigation. Add a single current marketing-entry binder for the **actual** marketing textarea/Send/Enter and Installer mobile field. Use the common loader's ready/pending-delivery path; no parallel app or home-only controller copied wholesale.
2. Preserve Residential/Commercial suggestion-as-prefill behavior and focus. Sending then delivers exactly that edited text once. Cover click, Enter, blank text and repeated click while booting; prevent a default navigation when the common loader accepts the handoff.
3. Device actions use existing App/hero attachment preparation and shared dictation. Preserve any unsent source draft. If a narrow draft-to-app context is needed, define it in the current loader/open contract and test draft+file together; do not rely on the current mutually-exclusive message/attach branch. A file chooser after lazy boot needs an explicit visitor click just as the existing preview does.
4. Installer desktop separately preserves the Configurator destination and consumes the requirement through the established sizing handoff or an explicit current-page requirement consumer. Its contract must be tested with supported sizing fields **and** a non-sizing model/document query, with no numeric guessing.
5. Add the real marketing fixtures (three page types × EN/DE × 1440/390), plus loading/error/retry/cancel and dictated/attached-draft preservation. Verify requests, actual rendered result and destination consumption, not only event dispatch or attribute presence. Then repeat online buyer-path acceptance with the authorized current model route; do not use live mail.

## Evidence and limits

- `pages.json`: complete real-page inventory, source marker counts, actual DOM controls, status, errors.
- `actions.json`: all 12 negative handoff reproductions and device/suggestion behavior.
- `supported.json`: six positive same-runtime controls with intercepted question payloads.
- `source-excerpts.json`: precise current rendered listeners/navigation snippets.
- `installer-size-handoff.json`: additional EN/DE stated-sizing reproduction and destination mount/form values, when present.
- PNGs: actual local browser states, not mockups; source question versus empty workspace/empty configuration state. Scroll-position screenshots may show sticky header overlap with content scrolled behind it; that alone is not reported as a layout defect.

The scope is the 50 published **Pages** requested. Product single URLs, taxonomy archives, blog post singles, login-only state variants and generated order endpoints are not silently claimed as exhaustively covered by this table; their common loader is the same seam, and existing dedicated fixtures remain separate evidence. Ordinary forms were not submitted. Source patterns and the positive controls support the common-loader classification; individual generic navigation links were not all clicked.
