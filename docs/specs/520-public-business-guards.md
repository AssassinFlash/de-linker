# Public business and account guards

Issue #520; policies #507/#508; shared mechanism #519 / PR #523.
Work in progress, not a delivery or a claim of production protection.

The real contact/inquiry/account handlers remain native Woo/WordPress. Shared
verification is consumed before external VAT calls, account/order creation or
mail. A valid verified customer must not be rejected by the old three-second
fill-time or three-per-connection rule. Direct requests and native aliases must
be checked at their actual side-effect boundary. Keep success login free of a
forced challenge, preserve non-password fields and the solution draft on error,
and keep an explicit retry/team-contact path. No automatic country/language/
free-email/link/Jev-content rejection is introduced.

## Shared business policy seam

The trusted PHP filters `linker_commerce_public_business_limits` and
`linker_commerce_public_business_carry` take existing policy, server action and
Protection Identity. They cover contact, inquiry, genie_contact, genie_inquiry
and conversation_mail with the same dimensions. Initial limits accepted in #508:
anonymous 10/hour and 20/UTC day; signed-in 20/hour and 100/UTC day; direct
connection 100/hour, never forwarded headers. Account requests preserve the
browser's actual accumulated usage and import anonymous spending once into the
account. Changing entry or logging in/out cannot reset the budget.
Draft/product mutations do not consume this business-message budget.

Resource adapters in #521 consume these filters at their native handler boundary.
Commerce does not debit them again in Sender. A trusted callback-scoped context
filter `linker_commerce_public_business_context` carries the original server
permit for native UUID/subject/input association and crash recovery. Client data
cannot supply this context and each adapter clears it in finally.

Two real native-journal fixtures currently prove cross-action/shared-NAT policy
and 20 guest messages carried into account allowance, with logout not restoring a
new guest budget: 2 tests / 78 assertions. This checkpoint does not yet wire the
forms, account paths, recovery metadata or fixed/recipient-capped receipts.
