# Production protection posture (read-only, 2026-11-10 21:05 local)

Domain-D evidence: which guards are actually armed on production, and how
they treat attack records. Nothing was modified.

## Armed guards (evidenced by live option rows)

| guard | production state |
| --- | --- |
| PublicGuard honeypot + signed clock + 3s fill floor | armed (native to the inquiry/contact handlers; every one of the 196 external inquiries passed it) |
| Public-connection rate limiter (3/hour) | armed and counting — live option `linker_commerce_limit_public_connection.<conn>.<window>` at **1 of 3**, i.e. real traffic is being metered without blocking humans |
| Public-receipts limiter | armed — `linker_commerce_limit_public_receipts` present (5 receipts) |
| Session verification trust (per-connection challenge counters) | armed — `linker_commerce_trust_genie.*` counters present (the 会话级验证信任 batch's counters, live) |
| Cloudflare Turnstile (`linker_public_protection`) | **not configured on production** — no option row, no keys; the optional enforce-mode protection is off, consistent with "尽可能简单，绝不阻挡真人" (the first principle) while the native guards carry the abuse direction |
| Business mode | no option row — the off default, so the connection limiter applies |

## Attack-record isolation

The guards persist **counters only** — there is no table or option storing
submitted attack content (the refusal paths in `PublicGuard`/`RateLimit`
increment counts; the tamper branch proven in the e2e spec returns the
customer's own entries client-side via the one-use flash and writes nothing
of the attacker's payload). Sweep of postmeta/comments for secret material
(see the credential sweep) also returned zero hits — attack submissions do
not leak into order notes or metadata.

## Reading

The production posture matches the owner's first principle: native,
invisible-to-humans guards (honeypot, timing, rate limits, session trust)
are armed and metering; the friction-adding Turnstile layer stays
unconfigured on production by design. Bidirectional proof stands:
- abuse direction — spec-proven refusals (tamper 409, rate limits, timing)
- human direction — 196 external inquiries received over 22 days.
