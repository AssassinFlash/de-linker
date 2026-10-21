# Customer evidence in the inquiry staff view

Issue: https://github.com/AssassinFlash/de-linker/issues/516

Base: `36dae3737e79530d7124cd8cb0e98cf70fda4961` (the inquiry observation PR).
Research: [fixed evidence dossier](https://github.com/AssassinFlash/de-linker/blob/31f606d98ab1629dd0168c222a5a7beec7d51dc1/docs/research/2026-10-22-customer-assessment-evidence/DOSSIER.md).

The owner wants a useful first review of a customer's situation while retaining
the decision. Use three parts: the accepted request and its owned context;
company/account/VAT evidence; explicit missing or different values. Reuse the
existing Jev observation. No extra model, website lookup, service, customer field,
approval decision, message, or customer-page change belongs to this ticket.

## Evidence contract

- Freeze the existing request, products, owned context and local account records
  at the existing acceptance point. Later account edits cannot alter them. Account
  values are current at acceptance, not proof of original registration values.
- Store the local record separately from the model snapshot. Staff decision
  actor/reason/time are local only. Reading or capturing evidence has no network I/O.
- Show source kinds (customer statement, site record, recorded VAT check, model
  observation, staff record, missing) and fixed field/hash references. A hash does
  not verify a company. No source is invented from an absent value.
- Treat `general` as the default form option; the record does not establish
  whether the customer deliberately selected it.
- Preserve submitted VAT, saved VAT, checked VAT, original check time, status and
  detail separately. A successful recorded check only applies to its exact
  normalized number and original time. Missing provenance, conflicting numbers,
  unavailable service, invalid, outside EU VIES scope and not supplied are distinct.
  No age threshold or identity/name/address verification is inferred.
- An optional blank guest company/VAT, free email, language, country, unfamiliar
  domain, short request, complaint or supplier enquiry is never an adverse score.
  No purchasing-power, value, overall-risk or fake-company score is produced.
- Legacy inquiries without this frozen record say evidence was not captured;
  never reconstruct an old check from today's account.

## Staff review and privacy

Use native Woo private order notes for appended events, with a generic note body
and protected structured comment metadata. Corrections, withdrawing a correction
and staff-recorded evidence append events. Keep revision/current correction in
order metadata. Check capability, per-record nonce, expected revision and a
connection-owned lock. Bind the nonce/form to the displayed observation and
frozen-evidence hash; reject changed sources as stale even if the staff revision
is unchanged. Each new event keeps the observation itself, evidence reference and
previous label/source/event/revision, so a later model update cannot change its
meaning. Reject stale/busy submissions explicitly. Persist event
and pointer in one transaction with readback. Preserve a pre-history correction
with its existing actor/time on the first change; do not invent earlier events.
Never rewrite Jev raw, the first notification, account status or the request.

Extend native Woo privacy export/removal for new frozen evidence and review
metadata, and live-pull anonymization for their order/comment metadata. Existing
mail copies and pre-existing assessment data remain governed by their owning
modules; this ticket must not claim to erase all message/history data. Erasure
must serialize with review changes and be visible on failure. Privacy removal is
an explicit exception to preserving the staff audit content.

## Native mechanisms and validation

LC does not own staff order meta boxes. Woo has order CRUD/private notes/privacy
hooks, but no typed evidence provenance or optimistic review revision. Reuse
these native mechanisms; add only the provenance builder and review guard. Use
native WordPress markup without CSS. Both classic orders and HPOS use WC_Order.

Cover the dossier's 29-case matrix: optional/unknown/international/short/complaint
requests; exact/mismatched/incomplete/old/unavailable/out-of-scope VAT; frozen
account changes; owned context only; no extra calls/mail/status changes; repeat
correction/withdrawal/import/stale/concurrent/unauthorized requests; privacy and
anonymization in both stores; EN/DE at 390/1440. Run real Woo fixtures, the normal
static checks, and independent Spec and Standards reviews against the fixed base.
