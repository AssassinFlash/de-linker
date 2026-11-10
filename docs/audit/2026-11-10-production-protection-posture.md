# Production protection posture (read-only, 2026-11-10 21:05 local)

Domain-D evidence: which guards are actually armed on production, and how
they treat attack records. Nothing was modified.

> **Correction, 2026-11-11.** The sweep below read option rows. The decisive
> settings are private `wp-config.php` constants, which an option-row sweep
> cannot see, so it reported them absent and inferred the rest from that
> absence. Corrected against
> `docs/acceptance/2026-11-11/security-dual-proof/security-dual-proof.json`
> (finding F1, issue #1075) and the source paths cited on each row. The guard
> table and the reading are corrected; the attack-record conclusion is unchanged
> and only its parenthetical now names the path that actually runs.

## Armed guards (private configuration read-back plus live rows)

| guard | production state |
| --- | --- |
| PublicGuard honeypot + signed start-clock | armed in every mode — both doors call `allows()` before any write (`plugins/linker-commerce/includes/Inquiry/Handler.php:50`, `plugins/linker-commerce/includes/Contact/Handler.php:100`); every one of the 196 external inquiries was received through it |
| PublicGuard 3 s fill floor | armed only while the shared admission is `off` — both doors pass `! Business::enabled()` as the guard's minimum flag on that same call (`plugins/linker-commerce/includes/Inquiry/Handler.php:50`, `plugins/linker-commerce/includes/Contact/Handler.php:100`), and production runs `enforce` (`plugins/linker-commerce/includes/Protection/Business.php:147`), so the floor is replaced by the proof and does not run |
| Public-connection rate limiter (3/hour) | **not running under `enforce`** — `PublicGuard::take()` is called only behind `! Business::enabled()` (`plugins/linker-commerce/includes/Inquiry/Handler.php:57`, `plugins/linker-commerce/includes/Contact/Handler.php:105`). The live `linker_commerce_limit_public_connection.<conn>.<window>` row at 1 of 3 is a counter from that `off` path; it is not evidence that production traffic is being metered there. What meters production is the shared journal's business allowances: 10/hour and 20/day per anonymous browser, 20/hour and 100/day signed in, 100/hour per direct connection (`plugins/linker-commerce/includes/Protection/BusinessPolicy.php:31-53`) |
| Public-receipts limiter | **not the operative path under `enforce`** — `ReceiptLimit` is spent only when the mode is not `enforce` (`plugins/linker-commerce/includes/Inquiry/Assessment/SendAuthorization.php:466`, `plugins/linker-commerce/includes/Contact/Handler.php:159-165`). Enforce spends `ReceiptBudget` instead: 2/hour and 5/day per recipient target, 10/day site-wide (`plugins/linker-commerce/includes/Protection/ReceiptBudget.php:34-63`) |
| Session verification trust | armed — `linker_commerce_trust_genie.*` rows present. Keyed by identity binding (account or browser), 12-hour window, `genie` only; inquiry/contact proofs stay single-use and never read it (`plugins/linker-commerce/includes/Protection/Trust.php:41-46,164`) |
| Cloudflare Turnstile | **armed and enforcing** — `Configuration::current()->health()` returns `mode=enforce`, `configured=true`, `ready=true`, `test_keys=false`. The keys are `wp-config.php` constants (`LINKER_TURNSTILE_SITE_KEY`, `LINKER_TURNSTILE_SECRET_KEY`, `LINKER_TURNSTILE_HOSTNAME`) resolved by `defined()` ahead of `getenv()` (`plugins/linker-commerce/includes/Protection/Configuration.php:30-35,108-111`), so an option-only sweep reports them absent. There is no `linker_public_protection` option to find: that name only exists as the maintenance cron hook `linker_public_protection_maintenance` (`plugins/linker-commerce/includes/Protection/Module.php:17`). Enforcement governs the challenge door itself; `genie` and `design` still require a solved challenge |
| Business verification (`LINKER_BUSINESS_VERIFICATION`) | `optional` (private constant, not an option row) — `inquiry` and `contact` proceed without a challenge while keeping their journal allowances; `genie` and `design` still require one (`plugins/linker-commerce/includes/Protection/Configuration.php:51-54`) |

## Attack-record isolation

The guards persist **counters only** — there is no table or option storing
submitted attack content (`RateLimit` rows only exist off enforce; under it the
shared journal records a reason and a count; the tamper branch proven in the
e2e spec returns the customer's own entries client-side via the one-use flash
and writes nothing of the attacker's payload). Sweep of postmeta/comments for
secret material (see the credential sweep) also returned zero hits — attack
submissions do not leak into order notes or metadata.

## Reading

The production posture matches the owner's first principle once the mode is
read correctly: the challenge layer is armed with real keys and enforcing, and
the two business doors are exempt from it by `LINKER_BUSINESS_VERIFICATION=optional`.
A real installer submitting an inquiry meets the honeypot, the signed
start-clock and, only if a confirmation receipt is due, the receipt budget —
never a Turnstile widget. The abuse direction is carried by the shared admission
journal and the protection quota, not by an unconfigured layer.

Bidirectional proof stands
(`docs/acceptance/2026-11-11/security-dual-proof/`):
- abuse direction — a 38.4 requests/min flood is cut to `429 linker_verification_quota`
  after exactly 20 attempts in the browser-minute window; 12 concurrent verifies
  are cut by the in-flight guard (3 x 429); both refusals are journaled
  one-to-one (`verification_browser_minute count=6`,
  `verification_browser_flight count=3`) and the probe token appears in 0 rows
  of postmeta/posts/options/comments
- human direction — 196 external inquiries received over 22 days, plus the
  reused EN/DE guest inquiries `#8703`/`#8704` completed with zero blocking
- cadence — three cycles at 2 s spacing are refused only for their own bad
  token (`linker_verification_rejected`), never for the quota, so ordinary
  reload rhythm is not mistaken for a flood
