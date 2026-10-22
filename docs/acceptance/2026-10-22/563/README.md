# #563 — normal Genie product/document and retry acceptance

Base: `1f0547574a1a2582cf3ded2f6bf807dfc7284ea4` on `origin/codex/533-production-security`. Worktree: `codex/563-genie-normal-acceptance`. This evidence is local and offline; independent Spec/Standards review, CI, merge and production readback are separate gates.

## Diagnosis and bounded change

The verified synthetic German captures had a qualified product and documents, but the documents fallback returned before cards, while the route's `show_products` was false. An independent valid CAN protocol sentence failed the German guard because lowercasing made CAN an English function word. The rejected original model drafts were not saved, so CAN is a reproduced guard defect, **not a proven explanation of those original drafts**. The first browser HTTP failure remains unknown; service completion timing does not establish a timeout.

The native App and Hero component fixtures confirmed a second defect: after an ambiguous request failure, Retry read an already completed Thread and still appended the same question, sending a second turn. The fix retains the live sender's actual enforced operation UUID, exact posted messages, files, locale, page context and trusted server conversation ID in memory, then requires the fresh native reader to return the same completed UUID and that prefix plus exactly one complete assistant. It also compares the assistant text with the parsed turn. A workspace history switch invalidates the witness, and marketing entry ownership is still rechecked. A reload has no live witness. The shared failure reconciliation therefore retains unknown input instead of clearing it merely because old history contains the same text.

The route uses the existing field and searches; the template uses native qualified card, document hydration and account price fill. Pure documents, negation, quotations and empty qualified results keep their old scope. Fatal document fallbacks retain the existing degraded sentence, with requested qualified findings below it. CAN is ignored only in exact uppercase technical contexts, never as a general uppercase-word exemption. Customer-facing strings, model routes, retries, quotas, resource operation keys, timeouts, mail and sending permissions are unchanged.

Precedents read before implementation: spec 13 goals and existing Route/Thread behavior; `2026-10-17-knocket/TRIAL.md`; `2026-10-18-judge-remit/README.md`; `2026-10-19-genie-campaign-gaps/DOSSIER.md` §1.13/§1.15; international assistant research §2.13. The exact completion-witness rule has no published competitor implementation. It reuses the existing resource UUID and native admission HMAC over the semantic body; it introduces no parallel idempotency mechanism. The Thread receipt is saved under the existing commit lock and rollback. A digest binds it to both stored messages and stream. Only the currently enforced callback supplies its UUID and internal fingerprint. The owned Thread GET exposes only operation_id, only after the native Ledger says completed and the original Replies result remains readable; the internal fingerprint stays server-side. Unresolved, off/observe, old, torn, expired, erased and deleted records have no usable completion identity.

## Red → green evidence

| Seam | Before | After |
| --- | --- | --- |
| Private synthetic capture replay, real collect/merge/template/cycle, sockets disabled | Acceptance assertion: captures 672 and 673 have no requested product card | Both retain card 2067; original document blocks match exactly; two attempts; zero network calls |
| Native route / language / fallback tests | 11 failures: eight explicit EN/DE route cases, one CAN sentence, two fallback cases | Positive and negative route cases, guard boundaries and fallback coverage pass |
| Real App + actual readThread with the proxy's JSON and SSE shape | Expected one send; observed two | Completed same request recovers with one send; other/missing ID, changed prefix, historical text and unfinished stream still retry; deliberate new same-text question sends |
| Real HeroConversation + HeroSession + actual readThread | Expected one send; observed two | One send, restored complete answer; entry-owner checks remain |
| Real cycle with synthetic native tool payloads | Product request could lose its card after language repair | EN/DE × approved/guest/pending/restricted × normal/two language misses = 16 passing combinations, card 2067 + both documents + original account price line |
| Real cycle with grounded German CAN/RS485 prose | Guard independently reproduced the false mixed-language vote | One grounded attempt, no language retry |

The raw captures, temporary fixture and detailed red/green logs are private machine artifacts under `~/de-linker-data/incident-20261022/genie-acceptance-diagnosis/`; none are committed. Repository tests use synthetic inputs and native mocked network seams. The old failure record's reload test now explicitly requires preserving input beside historical matching text.

## Review follow-up evidence

Independent review found two incomplete boundaries in `4ec67af7`: empty document results could still reach generic/clarification/fatal card paths, and local attachment comparison did not bind another tab's completed server operation. The added empty-document matrix first produced **28 failing cases / 4 passing cases**; the multi-model pure-document example added another red case. The first full regression run also caught four hidden unknown/unsearched explanations after an overly broad early return. The final change restricts only the document route's displayable qualified set inside clarification, preserving those existing explanations and all non-document qualification behavior.

The existing two index-error stock fixtures asked “Do you stock the SAJ H2-10K-T2?” / “Haben Sie den SAJ H2-10K-T2 auf Lager?” while hard-coding a documents route and expecting six product cards. Before correcting that fixture, native `Understander.prepare` + the captured Store API vocabulary + synthetic `find_products` Reading + mocked native abilities prove these inputs produce the products route. The same real route/cycle still keeps all qualified stock cards on an index failure. This is a synthetic understanding test, not a claim about an uncaptured live Jev response. Empty documents now run through real cycle for EN/DE × affirmative/pure/negated/quoted × qualified/page-only × language/fatal failure, without changing attempts or model budgets.

The App fixture first showed **three failures** for a different or missing completed operation; Thread first showed **three failures** for missing receipt persistence, invalidation and rollback. Native Hero fixtures now use actual `sendTurn`, `resourceFetch`, UUID headers and `readThread`: identical message prefixes/question/filename with different file bytes or page context receive different UUIDs and cannot satisfy the original pending turn. Native PHP exercises trusted permit → Thread commit → owned Thread GET, same UUID/different semantic body rejection before a second callback, off/observe, other-browser ownership, expiry, reply deletion, native journal erasure and conversation clear. Main-message, stream and receipt write failures/throws restore the prior answer and receipt together.

## Native checks

Run from this checkout:

```sh
cd services/genie
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy .
.venv/bin/pytest -q --tb=short

cd ../../plugins/linker-tools
npm run lint:types
npm run lint:js
npm run lint:format
npm run test:unit -- --run
npm run build
npm run build:check
vendor/bin/phpunit
vendor/bin/phpstan analyse --no-progress --memory-limit=512M
vendor/bin/phpcs includes/Genie/Thread.php includes/Genie/Proxy.php includes/Protection/Resources.php tests/php/Unit/RecordingThread.php tests/php/Unit/ThreadTest.php tests/php/Integration/ResourceAdmissionTest.php

LINKER_WP_ROOT=~/de-linker-local/g563/wordpress vendor/bin/phpunit -c phpunit.integration.xml.dist --filter test_genie_completion_is_bound
```

- Genie: **2061 passed, 1 skipped, 195 deselected, 6 existing xfailed**; no skips or xfails were added. Ruff and mypy pass (184 source files).
- Tools: **54 files / 482 tests pass**. TypeScript, ESLint, Prettier, production build and source/build manifest check pass. The build retains the existing asset-size/runtime warnings; this change adds no dependency or CSS.
- PHP: **297 unit tests / 2389 assertions**, PHPStan (512 MiB process flag) and WPCS for all six changed PHP files pass. Native g563: **26 integration tests / 481 assertions** pass, including the four new permit → actual Proxy → Thread → owned GET lifetime variants (135 assertions). The broader existing engineering fixtures require a synthetic process-only service-token constant and an unused `127.0.0.1:9` engine URL: a private bootstrap saved/restored the local option at shutdown and used their existing native HTTP mocks. The first broad run without those prerequisites reported setup failures; the final run has no errors, skipped cases or real service calls. No real credential was copied.
- Full diff whitespace check passes. Added source lines contain no retired implementation identifiers or debug instrumentation. High-risk language/routing and account-price paths are exercised through the real cycle and all existing service and frontend suites.

## Computer Use matrix

`just up g563` allocated WordPress `http://127.0.0.1:9329`, with its own `linker_g563` database. `just pull scan 20261022-1653` was clean; loading that snapshot preserved all 212 published products and 2756 attachments, with zero missing files and no production address left in local data. The current worktree plugins are symlinked into that instance. No `just serve`, provider credential or production SMTP configuration was used. The Genie URL was set to an unused local service address.

The temporary fixture existed **only** inside this instance's mu-plugin directory and checked the exact g563 filesystem path. It returned synthetic native Thread JSON, saved the offline-generated completed output, and returned a controlled 502 to the first POST. It ran after native dispatch filters so the UI exercised the intended ambiguity. Product image, model, URL, document metadata and current guest price presentation came from the real local Woo Store API and get-product ability. The fixture checks this UI/Thread boundary; it does not claim a full paid provider or production-security end-to-end test.

The matrix below records the presentation and interactions at head `4ec67af7`, before the review follow-up added the server operation receipt. The follow-up changes no visible surface; its stricter identity boundary is verified by native PHP and real App/Hero component fixtures rather than a repeated browser matrix. CUA drove real text entry, Submit/Send, Retry, language navigation and mobile scroll. At each row, the first POST yielded the existing failure message with the question retained; clicking Retry displayed the completed product/document answer and left the POST counter at **1**. No add-to-draft, inquiry, email or vote button was used. Workspace rows were rerun after the final shared helper build. Viewport overrides were reset at completion.

The native viewport capability was set to **1440×1000** or **390×844**. These are browser viewport settings, not the saved image widths. The original read-only mobile evaluation returned `innerWidth: 390` and `document.documentElement.scrollWidth: 375` in both languages. Every desktop image is **1425 pixels wide** and every mobile image is **375 pixels wide**, matching the content area with the native scrollbar excluded; full-page heights vary. The native screenshot bytes are JPEG/JFIF, preserved without conversion and now named `.jpg`. Existing CUA setup/readback calls and decoded image-header dimensions are retained privately in `563-viewport-evidence.json`. No new UI interaction was used for this correction.

| Surface | Language / configured viewport | Failure | Recovered result | POSTs after Retry |
| --- | --- | --- | --- | --- |
| Workspace | EN / 1440×1000 | [failed](screenshots/en-1440-failed.jpg) | [recovered](screenshots/en-1440-recovered.jpg) | 1 |
| Workspace | DE / 1440×1000 | [failed](screenshots/de-1440-failed.jpg) | [recovered](screenshots/de-1440-recovered.jpg) | 1 |
| Workspace | EN / 390×844 | [failed](screenshots/en-390-failed.jpg) | [documents](screenshots/en-390-recovered.jpg), [card after native scroll](screenshots/en-390-recovered-card.jpg) | 1 |
| Workspace | DE / 390×844 | [failed](screenshots/de-390-failed.jpg) | [documents](screenshots/de-390-recovered.jpg), [card after native scroll](screenshots/de-390-recovered-card.jpg) | 1 |
| Homepage Hero | EN / 1440×1000 | [failed](screenshots/hero-en-1440-failed.jpg) | [recovered](screenshots/hero-en-1440-recovered.jpg) | 1 |
| Homepage Hero | DE / 1440×1000 | [failed](screenshots/hero-de-1440-failed.jpg) | [recovered](screenshots/hero-de-1440-recovered.jpg) | 1 |
| Homepage Hero | EN / 390×844 | [failed](screenshots/hero-en-390-failed.jpg) | [documents](screenshots/hero-en-390-recovered.jpg), [card after native scroll](screenshots/hero-en-390-recovered-card.jpg) | 1 |
| Homepage Hero | DE / 390×844 | [failed](screenshots/hero-de-390-failed.jpg) | [documents](screenshots/hero-de-390-recovered.jpg), [card after native scroll](screenshots/hero-de-390-recovered-card.jpg) | 1 |

The native presentation merges repeated references to pages of the same PDF into one visible link. Offline assertions preserve every original service document block before that existing presentation pass. Product card actions and stock/guest-price wording remain localized; the mobile transcript scroll exposes the full card. The local mailbox remains empty. The follow-up rebuild also regenerates the configurator bundle because it shares the optional resource transport callback; its callers and behavior are unchanged, and the full frontend suite passes.

## Review and release boundary

Rollback is a code revert and normal rebuild. The optional completion receipt uses native conversation post meta and is written lazily; no table/schema migration is needed. Old code ignores that meta. New writes without a trusted operation clear its receipt, native conversation deletion removes it, and journal/reply erasure makes it unusable. Unknown or reload cases intentionally keep the failure and input for an explicit customer decision, rather than inferring completion from historical text. Display detection is deliberately narrow and may leave unfamiliar wording to the existing model route. The first browser HTTP fault is still unclassified, and the original rejected drafts remain unavailable. Independent full-diff Spec/Standards review and deployment/readback belong to the coordinating root task. This branch is not deployed or merged.
