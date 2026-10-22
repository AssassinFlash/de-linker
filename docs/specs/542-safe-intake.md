# Bounded contact and inquiry reception

Owner contract: issue #542, part of #533. Production source base is dcd5560d
plus the persistent notification hold in #537. Jev remains label-only, with
the existing ten-second background deadline. No public browsing challenge.

| Validated submission | Stored result | Model / mail | Customer result |
|---|---|---|---|
| Valid server proof, unrelated content | Existing Woo inquiry | Existing background classification and notifications | Existing received page |
| Missing, failed, unavailable, forged or wrongly scoped proof | Native Woo inquiry, verification-review hold | None until staff releases the record | Real inquiry number, saved for review; no claim of team notification |
| Entire confirmed transfer lure, exact host, first three samples | Native Woo inquiry, campaign hold | None | Saved for review, real number |
| Same campaign after three samples | Atomic aggregate count and existing admission receipt | None | Explicit grouped acknowledgement; original input remains; individual-review resubmission is available |
| Explicit individual review after grouping | Native Woo inquiry in the independent review capacity | None until staff release | Real inquiry number and saved-for-review state |
| Review capacity full | No new inquiry | None | Explicit failure, original fields and draft remain, direct email alternative |
| Invalid nonce, honeypot, forged start, invalid fields/draft/stock | Existing native refusal | None | Existing validation and retained input |

The campaign rule is human-confirmed, versioned and revocable. It matches the
entire message only: Russian transfer phrase + decimal amount + получить/забрать
тут + one http(s) URL, whose parsed host is exactly fredmer.buzz. Language,
nationality, free email, empty company/VAT, ordinary links, technical Russian,
quoted scams, domain substrings and mixed technical messages do not match.

## Initial operating budget

This is an operating allocation, not measured legitimate demand or a false-positive
rate. Reserve 32 MiB of native review-record storage at a conservative 256 KiB per
record: **128 unresolved records**. The existing validated field shape is at most
three 190-character fields and a 5,000-character message (22,280 UTF-8 bytes at
four bytes per character). The review path additionally bounds its semantic JSON
at 32 KiB and its saved solution draft at 20 lines. The 256 KiB allocation provides
space for native Woo rows, line items and metadata; it is not an assertion about
database engine physical allocation. Native records remain authoritative.

The three campaign samples cover one representative and two independent variants;
later accepted activity is a counter, not an invented new inquiry. Staff can
recover each retained sample. An individual-review retry explicitly stores the
complete submission in a separate 16-record individual-review capacity (4 MiB
of the same conservative storage allocation). It cannot consume the ordinary
128-record verification-review capacity. Grouped requests do not
pretend their raw content was retained. The original form remains populated.

Capacity is persistent across UTC days, cookies, email addresses and connections.
One database mutex covers reservation, first native save and readback. Unresolved
reservations never expire into an automatic capacity refund: an interrupted write
is recovered by the original UUID and HMAC association. Staff release frees one
review slot only after durable notification handoff. Erasure removes the native
PII and retry associations, with no raw content in the capacity registry. All
pre-existing browser/account/connection limits and global mail/model budgets remain.
The verified path never consults the review capacity.

## Recovery and privacy

Server-only context stamps the hold before the first Woo save, before receipt
budget or status-driven listeners. A hold never arises from a Jev label. Held
submissions have no immutable model snapshot, scheduled assessment or mail job.
Staff release has capability and record-bound nonce checks; it creates exactly
one internal job when there was no original job, otherwise #537 preserves the
original message. An explicit authenticated staff release promotes its immutable
job into the reserved critical allocation through #545's private JobStore API;
ordinary public submissions cannot promote themselves. The same transaction
rolls back a failed capture, promotion, audit or schedule while preserving the
hold and existing transport history. Release schedules through the existing throttle and never
creates a customer acknowledgement. Registry entries contain HMACs and native IDs,
not messages, email addresses or URLs. Native erasure covers the added metadata.

Client verification warms on interaction. On submit, contact/inquiry uses an
already completed proof if available; otherwise it submits immediately into the
bounded review path. It does not wait two minutes. Account/resource flows retain
their strict proof behavior. UI composition stays in existing LC/semantic form
surfaces; no new customer CSS or layout.

## Operational consumer

The trusted PHP filter `linker_commerce_pending_review_summary` returns
`array{count:int,oldest:int,url:string}|WP_Error` from `Intake::pending_summary()`.
`count` includes only complete native held verification and individual-review
records; `oldest` is the earliest Unix timestamp among them, or zero when empty.
The URL is the native staff-only filtered Woo list. Confirmed-campaign samples,
ordinary Jev labels, erased records and unwritten reservations are excluded.
An unavailable producer returns the consumer's default null; a busy/corrupt
registry returns `WP_Error`. Neither means an empty queue. This read-only seam
contains no customer content or addresses and performs no model or mail call.
The operational mail module owns aggregate alerts and its delivery budget.
