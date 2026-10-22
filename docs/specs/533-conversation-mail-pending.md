# Preserve conversation-mail pending state

Owner-authorized pre-send protection, strict deployed entry-block base `97ef132f`. The content-mail producer in Commerce must not be bypassed by Genie conversation sharing. Commerce owns its durable job, classifier and final Message permit. This Tools change supplies the native conversation ID with the complete transcript and consumes the producer's three distinct answers: true means permitted Outbox acceptance, `{status: pending}` means a durable request still awaiting automatic checks, false means not accepted. It does not classify or grant permission itself.

Return HTTP202/pending for an accepted automatic check. The existing feedback position says the request is saved and asks the visitor not to repeat it; it does not claim an email was dispatched. Disable the repeated request button for that state. A guest's original confirmation link retains its one-use token capability and may be opened from another browser. Session ownership still governs the initial request and signed-in account address. Both admission and the producer use the native URL capture for the conversation ID, so JSON or query id parameters cannot substitute another source. Conditional deletion of the exact guest token value permits only one concurrent confirmation producer.

Commerce can ask `linker_commerce_conversation_mail_source_current(false, native_id, frozen_messages)` at a background sending boundary. Tools answers true only for the complete unchanged nonempty transcript of a current private conversation that the native retention policy does not mark for deletion. This proves source continuity only. Recipient, policy, purpose, Message, attachment, erasure/staff version and classification authorization remain Commerce responsibilities. A prior hook answer is not permission. A missing consumer fails closed in Commerce.

## Copy record

Draft EN: “Your email request is saved and awaiting automatic checks. You do not need to submit it again.”

Independent DE draft: “Ihre E-Mail-Anfrage ist gespeichert und wartet auf die automatische Prüfung. Bitte senden Sie sie nicht erneut.”

Independent adversarial review by assessment_spec_review: PASS, using linker-copywriting hard stops and the actual state contract. Neither language says normal, sent or guaranteed delivery; DE uses Sie. Review condition: use this text only after durable storage while automatic recovery is still pending. Terminal malicious, exhausted/manual or missing-job states must not reuse this response. The Commerce producer owns that mapping. Final EN/DE retain these drafts. Private review: `attack-continuity/conversation-pending-copy-review.md`.

## Executed local evidence and remaining gates

Owned bare mechanism instance p533copy, port9389: full ConversationRoutesTest plus ResourceAdmissionTest **39 tests /614 assertions PASS**, including actual signed-in account binding, native URL versus JSON/query ID precedence before admission, guest confirmation from another browser with one-use token, a controlled real conditional-token race producing one handoff, pending without a duplicate mail call, changed/empty/expired/deleted source refusal, and producer-hook callback restoration. Native mail and HTTP isolation remain active; fixture addresses use tester@example.test. This is the consumer/provider contract seam, not a claim that a fake provider implements the Commerce security gate.

Affected API/component JS tests **16 tests PASS**; complete Tools PHPStan, changed PHP WPCS, TS types, changed JS ESLint and formatting PASS. Build/translation reproducibility checks passed for the existing JS delta; independent full-diff review, integrated real Commerce producer tests, snapshot-backed EN/DE desktop/mobile browser acceptance and production readback remain required before release. This branch alone is not deployed protection. The existing initial inquiry/contact “We have not sent a confirmation email” remains accurate while checks are pending, with submission success retained. Fresh conversation history and repeated native inquiry/contact reads resolve the current bound Woo receipt metadata after the background handoff, rather than treating the immutable initial false note as a permanent failure. Integrated real-producer verification of that later transition remains required.


## Confirmation notice correction

The previous UI sentence said that the conversation follows once a guest opens the confirmation link. That promise is incompatible with mandatory pre-send checks. Final EN is “A confirmation link is on its way to %s.” Independent DE is “Ein Bestätigungslink an %s ist unterwegs.” assessment_spec_review adversarial copy review: PASS; both preserve the address and describe only accepted fixed confirmation mail, without promising conversation delivery. Confirmation-mail failure still uses unavailable, not this notice. This is a necessary consequence of the new sending contract.

The confirmation notice delta passed the full affected App/API/component group:86tests, TypeScript, changed-file ESLint/Prettier, reproducible build manifest and complete i18n coverage. The prior a963 PHP review/native39/614 remain separate evidence; final combined native producer/browser acceptance is still required.
