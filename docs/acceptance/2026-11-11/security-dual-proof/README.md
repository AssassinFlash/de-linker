# Security dual proof (2026-11-11)

Bidirectional evidence for the goal's domain-D criterion: abuse defence and
real-person passage both hold, on production, at the same time.

Evidence file: [`security-dual-proof.json`](security-dual-proof.json).

## What this run does and does not do

It is an **unarmed** abuse simulation against `https://de-linker.com`, plus a
read-only read-back of the site's own admission journal. Nothing was created:
no order, no account, no inquiry, no mail. Every `verify` call carries the
literal token `probe-invalid-token-00000000`, so Turnstile fails by
construction and the request cannot reach a business handler even if the
quota had let it through.

The human leg is **not re-run**. It reuses this goal's existing first-hand
evidence (orders `#8703`/`#8704`, EN and DE, zero blocking) from
`docs/acceptance/2026-11-10/goal-state-ledger.md`, and adds only what that
evidence could not cover.

## Results

| leg | what was proven | result |
| --- | --- | --- |
| human passage | 2 real EN/DE guest inquiries completed and read back as `#8703`/`#8704`; 196 external inquiries over 22 days | pass (reused) |
| human cadence | 3 cycles at 2 s spacing: every refusal is `linker_verification_rejected` (bad token), never `linker_verification_quota` | pass |
| rate limit, per minute | 38.4 req/min: `400x20` then `429x6` then `400x4` at the window boundary, matching `BROWSER_MINUTE=20` | pass |
| rate limit, in flight | 12 concurrent verifies: 3 x 429 `linker_verification_quota` | pass |
| authorization | `mail-health` 401, `accounts` 403, `publication/jobs/claim` 401, planning report 404 with no existence oracle | pass |
| login wall | `/my-account/documents/` and `/de/mein-konto/dokumente/` render the sign-in surface, zero document rows | pass |
| isolation record | journal records `verification_browser_minute count=6` and `verification_browser_flight count=3` — one-to-one with the two floods | pass |
| payload retention | probe token found in 0 rows of postmeta/posts/options/comments; `php.log` unchanged | pass |
| credential sweep | 0 secret-shaped values in options; the 2 postmeta `sk-` matches are image-rendition filenames | pass |

## Two corrections recorded rather than smoothed over

**F1 — the prior posture audit understates production.** 
`docs/audit/2026-11-10-production-protection-posture.md` says Turnstile is "not
configured on production — no option row, no keys". Live read-back of
`Configuration::current()->health()` returns `mode=enforce`,
`configured=true`, `ready=true`, `test_keys=false`. The earlier sweep searched
option rows; the keys are `wp-config.php` **constants**, so an option-only
search reports them absent. The accurate statement is: Turnstile is armed and
ready, and `LINKER_BUSINESS_VERIFICATION=optional` exempts the inquiry and
contact doors from it, which is the owner's 2026-10-22 availability priority.

**F2 — the task's literal assertion targets a door with no limiter.** 
15 consecutive `prepare` calls returned 200; no 429 is producible there.
`prepare` verifies same-origin and mints an HMAC stamp — no database write, no
business record, no provider call. The quota is applied one step later in
`verify` via `Ledger::reserve()`. Putting a limiter on `prepare` would refuse
the challenge the page needs. The assertion was therefore restated on the door
that owns the limiter, and proven there.

**F3 — probe cost, stated because the probes caused it.** 
`verification_connection_hour` reached 81/100 in the 20:00Z hour, leaving 19
attempts of headroom for any real submission in that same hour. The allowance
is per direct connection and resets hourly; human behaviour is nowhere near
it, so no customer could have been blocked, but the number is recorded rather
than omitted.

## Provenance

- Source constants: `plugins/linker-commerce/includes/Protection/Controller.php:21-25`
  (`LEASE=10`, `BROWSER_MINUTE=20`, `CONNECTION_HOUR=100`, `SITE_DAY=5000`,
  `IN_FLIGHT=2`), `Ledger.php:16` (`OPTION = 'linker_public_admission_ledger'`).
- Journal read via `wp eval` on production SSH; credential sweep via
  `wp db query` with counts only — no row values exported.
- Probe window: `2026-11-10T20:31:39Z` .. `2026-11-10T20:43:06Z`.
