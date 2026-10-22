# Preserve conversation-mail pending state

Owner-authorized pre-send protection, strict deployed entry-block base `97ef132f`. The content-mail producer in Commerce must not be bypassed by Genie conversation sharing. Commerce owns its durable job, classifier and final Message permit. This Tools change supplies the native conversation ID with the complete transcript and consumes the producer's three distinct answers: true means permitted Outbox acceptance, `{status: pending}` means a durable request still awaiting automatic checks, false means not accepted. It does not classify or grant permission itself.

Return HTTP202/pending for an accepted automatic check. The existing feedback position says the request is saved and asks the visitor not to repeat it; it does not claim an email was dispatched. Disable the repeated request button for that state. A guest's original confirmation link retains its one-use token capability and may be opened from another browser. Session ownership still governs the initial request and signed-in account address; a request parameter cannot substitute another conversation ID or recipient.

Commerce can ask `linker_commerce_conversation_mail_source_current(false, native_id, frozen_messages)` at a background sending boundary. Tools answers true only for the complete unchanged nonempty transcript of a current private conversation that the native retention policy does not mark for deletion. This proves source continuity only. Recipient, policy, purpose, Message, attachment, erasure/staff version and classification authorization remain Commerce responsibilities. A prior hook answer is not permission. A missing consumer fails closed in Commerce.

## Copy record

Draft EN: “Your email request is saved and awaiting automatic checks. You do not need to submit it again.”

Independent DE draft: “Ihre E-Mail-Anfrage ist gespeichert und wartet auf die automatische Prüfung. Bitte senden Sie sie nicht erneut.”

Independent adversarial review by assessment_spec_review: PASS, using linker-copywriting hard stops and the actual state contract. Neither language says normal, sent or guaranteed delivery; DE uses Sie. Review condition: use this text only after durable storage while automatic recovery is still pending. Terminal malicious, exhausted/manual or missing-job states must not reuse this response. The Commerce producer owns that mapping. Final EN/DE retain these drafts. Private review: `attack-continuity/conversation-pending-copy-review.md`.

## Executed local evidence and remaining gates

Owned bare mechanism instance p533copy, port9389: ConversationRoutesTest **12 tests /108 assertions PASS**, including actual signed-in account binding, supplied-ID rejection, guest confirmation from another browser with one-use token, pending without a duplicate mail call, and changed/empty/expired/deleted source refusal. Native mail and HTTP isolation remain active; fixture addresses use tester@example.test. This is the consumer/provider contract seam, not a claim that a fake provider implements the Commerce security gate.

Affected API/component JS tests **16 tests PASS**; complete Tools PHPStan, changed PHP WPCS, TS types, changed JS ESLint and formatting PASS. Final build/translation reproducibility, independent full-diff review, integrated real Commerce producer tests, snapshot-backed EN/DE desktop/mobile browser acceptance and production readback remain required before release. This branch alone is not deployed protection and does not change inquiry receipt semantics: their existing “We have not sent a confirmation email” remains a statement of the current state, with submission success retained.
