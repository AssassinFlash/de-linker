# #496 Ask Genie on the design report — local snapshot walk

2026-10-21. Instance `w496` (`http://127.0.0.1:9267`, snapshot `20261021-1023`), engine
`http://127.0.0.1:9268`, Genie `http://127.0.0.1:9269`. No inquiry, no registration, no
login form mail: the two walk accounts were created with WP-CLI. No mail was sent.

Accounts: **owner** user 43 (`w496owner`, email withheld; approved, and set to pending and
restricted for those gates), **other** user 44 (`w496other`). Fixture: PLZ 80538, 5000 kWh,
10 kWp, three-phase, no backup.

Run at the PR head after the rebase onto main (#500/#499/#498). The walk (`walk.mjs`) clicks the configurator: inputs → solution → design report →
**Ask Genie**. It records the save response, the Genie turn's page context, the answer
text, the product cards' price lines, and direct ability calls. `record.json` is the raw
record; the screenshots are in `shots/`.

## The flow

| State | Saves | Genie turns (`page.solution_id`) | Evidence |
| --- | --- | --- | --- |
| approved EN 1440 | 201, id 8048 | 1 turn, `8048` | [answer](shots/approved-en-1440-answer.png), [cards](shots/approved-en-1440-cards.png) |
| approved EN 390 | 201, id 8050 | 1 turn, `8050` | [answer](shots/approved-en-390-answer.png), [cards](shots/approved-en-390-cards.png) |
| approved DE 1440 | 201, id 8052 | 1 turn, `8052` | [answer](shots/approved-de-1440-answer.png), [cards](shots/approved-de-1440-cards.png) |
| approved DE 390 | 201, id 8054 | 1 turn, `8054` | [answer](shots/approved-de-390-answer.png), [cards](shots/approved-de-390-cards.png) |
| guest EN 1440 | 202, `id: 0` | 0 | [report + sign-in note](shots/guest-en-1440-report.png) |
| guest EN 390 | 202, `id: 0` | 0 | [report + sign-in note](shots/guest-en-390-report.png) |
| guest DE 1440 | 202, `id: 0` | 0 | [report + sign-in note](shots/guest-de-1440-report.png) |
| guest DE 390 | 202, `id: 0` | 0 | [report + sign-in note](shots/guest-de-390-report.png) |

The save precedes the turn in every approved case: the recorded `/linker/v1/solutions`
response is 201 with the id the turn then carries. The guest's save is the session keep
(202, `id: 0`, C30): the report shows “Your saved solution stays in this browser for
now…” / “Ihre gespeicherte Lösung bleibt vorerst in diesem Browser…” and **no** Genie turn
is sent.

**Save once, ask once:** `record.json` → `reuse = {savePosts: 1, statuses: [201]}` after
clicking **Save solution** and then **Ask Genie**: the report's button reuses the save,
and the single turn carries `solution_id: 8056`. A save in flight is awaited, not
repeated (the promise both paths share, tested in `App.test.tsx`).

## The answer cites the report's own figures

Report values (screen, both languages): annual yield 10,034 – 12,164 kWh, mean 11,190 kWh;
proposed usable capacity 5.8 kWh; self-sufficiency with storage 61 % – 71 %;
self-consumption with storage 33 % – 38 %.

| Answer | Figures cited | Cards |
| --- | --- | --- |
| EN 1440 | 10,034 · 12,164 · 11,190 · 5.8 · 61 · 71 · 33 · 38 | 2, `€1,090.00`, `€1,430.00` |
| EN 390 | the same, “10,034 to 12,164 kWh, on average 11,190” | 2, `€1,090.00`, `€1,430.00` |
| DE 1440 | 10.034 · 12.164 · 11.190 · 5,8 · 61 · 71 · 33 · 38 | 2, `1.090,00 €`, `1.430,00 €` |
| DE 390 | the same German marks | 2, `1.090,00 €`, `1.430,00 €` |

The figures are `{fact:solution.nK}` hydrations of the read-solution text; the selection
basis (rules and the battery release condition) is in the same answers.

## Another customer's solution

Direct ability call (`linker/read-solution`, GET `/wp-abilities/v1/abilities/…/run`):

| Caller | Status | Body |
| --- | --- | --- |
| owner (cookie) | 200 | the figures above, title `GoodWe GW10K-ETA-G20, 80538`, no amount |
| guest (no token) | 401 | `rest_ability_cannot_execute` |
| other customer (user 44) | 403 | `linker_solution_owner`, “This saved solution belongs to another account.” |

The same three cells are asserted by
`plugins/linker-commerce/tests/php/Integration/ReadSolutionRestTest.php` on a bare instance,
including the Genie token path with no cookie session.

## Price gate per account state

| State | Ability | Amount in the payload | Card price line |
| --- | --- | --- | --- |
| approved | 200 | no | `€1,090.00` / `€1,430.00` (net) |
| pending | 200 | no | “Account under review. Prices after approval.” |
| restricted | 200 | no | “Not available for your account” |
| guest | 401 (no reference, no turn) | no | — (no cards) |

The read-solution payload carries no price-bearing fact at any state. The cards the answer
shows take their price line from the account's own product ability (`prices.fill`), the
one price rule of the site. Pending/restricted screenshots:
[pending](shots/pending-en-1440-answer.png), [restricted](shots/restricted-en-1440-answer.png).

## Regression row and tests

- `services/genie/tests/fixtures/339/manifest.json` → `496-saved-solution` (locales en/de;
  accounts approved/pending/restricted/guest; names the 401/403 and no-money conditions).
  `services/genie/tests/test_solution.py` names the row and holds the reader/route tests.
- PHP: `ReadSolutionTest` 10 tests/46 assertions; `ReadSolutionRestTest` 6 tests/57
  assertions on `w496` and in CI (`mu-smoke`, filter `ReadSolutionRestTest`);
  Registrar/PageContext/UserContext/Entries tests updated.
- Python: `services/genie` pytest 1838 passed, 1 skipped; ruff, mypy clean.
- JS: linker-tools vitest 355 passed; types, ESLint, Prettier clean.
- `just check` exit 0 (PHPCS + PHPStan level 8 all projects, JS checks, Python checks,
  German copy, i18n coverage/validity, build manifest).
- Build: `npm run build` + `build:check` in linker-tools.

## Open

- **Coordinator sign-off: pending** on `copy-review.md`.
- This is the local snapshot walk; production re-verification happens with the deploy
  (the ticket's acceptance is local, and AGENTS.md keeps production out of first looks).
- The owner's conversations from the walk remain in `w496` (local only); the walk deletes
  the thread at the start of each case.
