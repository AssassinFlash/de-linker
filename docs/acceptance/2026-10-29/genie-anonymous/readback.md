# Anonymous (logged-out) Genie answer chain — proven end to end

Mission b2-genie (map #548). Question under test: the readback
`docs/acceptance/2026-10-22/full-site/marketing-library-online/readback.md`
records that no new production model answer was accepted, so the anonymous
Genie chain was unproven. This note proves it on a local instance built from
the newest live snapshot. No product code was changed — the chain is already
correct; per the mission, only this evidence note is added.

## Environment

- Worktree `/Users/chesterjohn/Documents/de-linker-worktrees/b2-genie`, branch
  `codex/b2-genie-anonymous`, from `origin/main` at `a5cbb4026`.
- Instance `b2genie`: `PHP=/opt/homebrew/opt/php@8.3/bin/php just up b2genie`
  (port 8892), then `PHP=/opt/homebrew/opt/php@8.3/bin/php just pull load
  b2genie latest` → snapshot `20261029-0433` (taken 2026-10-28T20:35:57+00:00,
  `ok: true`, licences applied), then `PHP=/opt/homebrew/opt/php@8.3/bin/php
  just serve b2genie` → engine `http://127.0.0.1:8893`, genie
  `http://127.0.0.1:8894`, knowledge index build `20261029T032904Z-721083000`.
- All turns below were sent with curl, no WordPress login cookies, fresh cookie
  jars per conversation (`-c/-b`), so `is_user_logged_in()` is false and the
  visitor is anonymous.

## 1. Entries visible before scripts (server-rendered HTML, anonymous GET)

| Surface | URL | Evidence in raw HTML |
|---|---|---|
| Home EN | `http://127.0.0.1:8892/` | dock mount `data-page-type="home"`, 4 × `data-linker-genie-open`, `hero-cinematic` (hero entry) |
| Product page EN | `/product/saj-h2-10k-t3/` (4107) | `[data-pdp-ask]` "Ask Genie" button, 5 dock mounts, `data-page-type="product"` |
| Product page DE | `/de/produkt/saj-h2-10k-t3/` | `[data-pdp-ask]`, "Genie fragen", `data-page-type="product"` |
| Marketing EN | `/solution/residential-storage/` | `#system-search` input bound by the marketing entry, `data-page-type="solution"` |
| Marketing DE | `/de/loesung/heimspeicher/` | `#system-search`, "Genie fragen" ×3, `data-page-type="solution"` |

Commands: `curl -s <url> -o page.html` then `grep -o 'data-pdp-ask\|data-page-type="[^"]*"\|system-search\|Ask Genie\|Genie fragen' page.html | sort | uniq -c`.

## 2. Answer turns (anonymous, real model, real index)

Endpoint `POST /wp-json/linker-ai/v1/genie/turn` (`permission_callback:
__return_true`; verified in `plugins/linker-tools/includes/Genie/Proxy.php:169`).
The WP proxy buffers the whole SSE package into a JSON envelope
(`{"conversation_id": …, "stream": "event: meta … event: done"}`), matching the
spec's no-backend-streaming ruling; the raw streams are archived next to this
note (`genie-en.stream`, `genie-de.stream`, `genie-mkt.stream`,
`genie-card.stream`; response headers in `genie-en.headers`/`genie-de.headers`).

| # | Locale / page context | Question | Conversation | Result |
|---|---|---|---|---|
| 1 | EN, product 4107 | "Which batteries have documented pairing with this model?" | 8423 | HTTP 200 in 54.8 s; meta: `grounded: true`, `fallback: false`, `route: pairing`, `failures: []`; text block + document block `p4107.document.0` → hosted PDF `…/uploads/2026/09/H2_HS2_HS3_AS2_AS3_Configuration_Instructions_V1.0_en.pdf`; `done {"ok": true}` (2026-10-29T04:49Z) |
| 2 | DE, product 4107 | "Welche Batterien haben ein dokumentiertes Pairing mit diesem Modell?" | 8424 | HTTP 200 in 64.3 s; meta: `grounded: true`, `route: pairing`, `language: de`; answer fully German, Sie-form, no English function words; document blocks `p4107.document.0` and `.2` with hosted URLs; `done {"ok": true}` (2026-10-29T04:51Z) |
| 3 | EN, marketing page `solution` (from `/solution/residential-storage/`) | "Which battery should I pair with the SAJ H2-10K-T3 for a 10 kWh home storage?" | — | HTTP 200 in 74.7 s; `grounded: true`, `route: pairing`; document block + `open_configurator` action block; `done {"ok": true}` (2026-10-29T04:52Z) |
| 4 | EN, anonymous catalogue question | "Which hybrid inverters do you carry for homes?" | — | HTTP 200 in 33.8 s; `grounded: true`, `route: products`; **cards block** `product_ids [6523…6528]` (GoodWe ESA single-phase set, matches panel A1) with per-card prices `"Net price after partner sign-in"`, `reason: "login"` — the anonymous price gate holds; `done {"ok": true}` (2026-10-29T04:53Z) |

Stream states observed: every turn arrived as one complete buffered stream with
`meta` → `block`* → `done {"ok": true}`; no truncated stream (no
`UnfinishedStreamError` surface), no `fallback: true`, no failure meta. The
failure path was not induced (no defect existed to reproduce); its contract is
covered by the existing #410/#411 suites.

## 3. Model actually used

`~/de-linker-local/b2genie/genie/turns.sqlite` (copied read-only to
`/tmp/turns2.sqlite`):

```
sqlite3 turns.sqlite "SELECT conversation_id, locale, grounded, fallback, provider, model FROM turns ORDER BY id;"
8423|en|1|0|deepseek|deepseek-flash
8424|de|1|0|deepseek|deepseek-flash
```

`deepseek` provider = the official `api.deepseek.com` channel
(`agent.py::CHAT_PROVIDER`, no provider switch). No other model appears in any
anonymous turn; Jev meta is present and `jev_error: null` in all streams.

## 4. Citations resolve to hosted documents; conversation persists

- Document blocks carry `ref` (`p4107.document.N`), a label, and a hosted
  upload URL under `wp-content/uploads/` — resolved server-side, not model
  text. Text-block `refs` (`page`, `4107`) ⊆ this turn's tool results.
- Persistence readback for the anonymous browser keys:
  `GET /wp-json/linker-ai/v1/genie/conversation` with conversation 8423's
  cookies returns `{"conversation_id": 8423, "messages": [user turn], "stream":
  <full stored SSE of the answer>}` — the answer survives reload for an
  anonymous visitor.

## 5. Observations (not defects, no code change)

- Server-side `timing.total` for the four turns: 39.9 / 49.4 / 48.9 / 33.8 s
  (model attempt alone 23–38 s). These are single samples through the local
  stack; the p95 ≤ 30 s gate belongs to campaign #329/#336 and its dedicated
  client-side harness with ≥20 completed turns, not to this proof. Recorded
  here so the latency line is not lost.
- No browser screenshots were taken: all evidence is curl request/response
  plus the service turn database. Visual UI acceptance of the dock is already
  covered by the existing e2e suites and was not repeated here (§0.1: reuse
  valid results).

## Verdict

The anonymous Genie chain — entry (product page, marketing page, home dock),
REST turn with real deepseek-flash over the official API, grounded streaming
answer, hosted-document citations, gated card prices, German-in-German, and
server-side conversation persistence — is **proven end to end** on the
20261029-0433 snapshot. No defect found; product code unchanged.
