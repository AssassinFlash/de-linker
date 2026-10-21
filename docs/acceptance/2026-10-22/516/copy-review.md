# Staff copy review

This is internal inquiry-review copy. It adds no customer form or email copy.
EN and DE are in the Commerce gettext catalogs. Existing terms are reused from
the account, VAT and contact modules.

## Draft

The first implementation showed all saved request/account/VAT fields openly,
followed by the existing Jev observation and a correction form. Source values
and the VAT result used their raw stored keys. A current correction showed its
label while the note was available only in the event history.

## Critique

- Raw `contact`/`valid` keys are hard to read and remain English in the German
  staff view. Use the existing contact and VAT labels, retaining the underlying
  values in the frozen record.
- A valid VAT result could be mistaken for a verified customer. Keep the exact
  checked number and original time visible on demand and state the limited
  meaning in the review point. Missing provenance and differing results must
  each have their own wording.
- Showing every field at once makes a short guest message unnecessarily long.
  Keep the request, company/account section and review points as the main path;
  expand contact/account/check details only when needed.
- A legacy correction has no event history yet. Show its current note directly;
  import its original actor/time when the next staff change starts history.
- A staff-entered register URL is a recorded source, not an automatic independent
  check. Say who recorded it. AI replies and attachment extractions must retain
  their AI attribution.

## Revised copy and interaction

`EvidenceView`, `ReviewView` and the DE catalog implement the revised wording.
The card uses “Not recorded” for absent fields and explicitly says guest company
and VAT information are optional. It offers no customer-value, identity or risk
score. Country, language, email provider, short messages and complaints do not
participate in a rule. Sources, original model output and staff corrections
remain separate. Staff actions say that they do not send mail or change approval.

The German copy uses Sie and the existing USt-IdNr./Kontofreigabe/Lösungsentwurf
terms. The review still needs the final rendered EN/DE desktop/mobile check and
the independent source reviews; this record does not claim those gates passed.
