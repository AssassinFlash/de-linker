# Bounded inquiry reception acceptance

Local instance: `i542`, `http://127.0.0.1:9308`, isolated worktree
`codex/542-safe-intake`. The instance contains the actual production theme,
uploads and database snapshot `20261022-0018`, with private local overrides.
This is local acceptance; it does not claim production deployment or delivery.
No external model or SMTP call was made. The local mail sink rewrites all
destinations to one synthetic tester before any local staff handoff.

## Customer state evidence

Each filename encodes door, language, viewport width and actual resulting state.
Desktop is 1440 × 1000 and mobile is 390 × 844. All screenshots were captured
through Computer Use against native forms and Woo screens. No prototype states
or custom customer CSS were used.

| Door | State | EN/DE × desktop/mobile |
|---|---|---|
| Contact | Real record saved for review, no confirmation sent | `contact-*-*-saved.png` |
| Inquiry | Real record saved for review, actual authorized inquiry number | `inquiry-*-*-saved.png` |
| Both | Full verification-review capacity; original inputs/draft retained | `*-*-*-full.png` |
| Contact | Exact confirmed campaign beyond three samples; explicitly no separate inquiry saved | `contact-*-*-grouped.png` |
| Contact | Explicit individual review stores a separate complete record | `contact-*-*-individual-review-saved.png` |
| Native staff | Original mail job absent; held record is individually recoverable | `staff-*-*-held.png` |
| Native staff | Actual authorized release creates one queued internal job | `staff-*-*-released.png` |
| Native staff | Aggregate notice opens four genuine waiting records, excluding campaign samples | `staff-*-*-review-list.png` |

The recorded state readback in [native-ui-readback.json](native-ui-readback.json)
contains synthetic native IDs and counts only. UI fixtures 8328 and 8329 were
actually released to local immutable jobs 8413 and 8414. The two saved inquiries
and two individual-review records remain held with job zero. The separate
campaign sample capacity contains three complete records. The aggregate counter
is five; it is not represented as five saved inquiries.

The staff-list screenshot uses actual native HPOS filtering and the click target
from the aggregate notice. Existing local fixtures were backfilled with the
scalar lane marker introduced during implementation. This is fixture repair,
not a production migration; production does not yet contain this intake feature.

## Execution evidence

Native suite command from `plugins/linker-commerce`:

```sh
LINKER_WP_ROOT=/Users/chesterjohn/de-linker-local/i542/wordpress \
  /opt/homebrew/opt/php@8.3/bin/php vendor/bin/phpunit \
  -c phpunit.integration.xml.dist \
  --filter 'SafeIntakeTest|BusinessAdmissionTest|NotificationHoldTest|PublicLedgerTest|PublicControllerTest'
```

The combined suite passed 70 tests / 909 assertions before the additional
erased-record release regression. The final focused SafeIntake run then passed
17 tests / 277 assertions, including that regression and the #545 staff-release
transaction rollback boundary. Coverage exercises native
guest/pending/approved customers, draft lines, successful/failed/forged/wrong-scope
proof, configuration outage, unchanged normal verified admission, stable UUID
retry, interrupted native save recovery, durable occupancy over day boundaries,
last-slot competition between two independent PHP/DB connections, campaign
cross-cookie/email/amount aggregation, exact-match exclusions, separate individual
capacity, capability/record-bound staff release, zero duplicate model/mail jobs,
privacy erasure before and after native write, truthful receipt copy, and the
content-free operational summary producer.

Commerce unit suite: 1484 discovered, 6125 assertions, 260 integration-only
tests skipped by the unit configuration. Protection JavaScript: 24 passing tests;
TypeScript, ESLint and formatting passed. Commerce PHPStan level 8 and WPCS
passed on the implementation. German copy, gettext validity, translation coverage
and internal-home URL gates passed. Build output was regenerated from source.

The selected budget is an explicit initial operating allocation, not a measured
false-positive rate, a production load result or a guarantee of exact physical DB
bytes. See [state table and budget](../../../specs/542-safe-intake.md).
The existing per-browser/account/network policy still applies to both contact
and inquiry. The verified route has independent capacity from review storage.

Copy draft, critique and final EN/formal-DE wording are recorded in
[copy-review.md](copy-review.md). Full-diff independent Spec and Standards review
and exact-head CI remain separate integration gates owned by the security line.
