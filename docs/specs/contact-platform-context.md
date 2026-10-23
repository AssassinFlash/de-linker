# Selected product and documents in Contact

The published utility pages have four product cards in each language. Their
project and document links include `platform`, `document` and an entry identifier.
The Contact source page and intent arrive, but the platform and document labels
are absent from the form checkbox transport. Native normalization and
`Submission::from_post` then lose them in the team/admin record too. A no-send
native control of all 16 language/product/intent cases reproduces the loss.

## Required behavior

- Carry the selected `platform` and requested `document` text into the existing
  Contact selection, inclusion checkbox, language URL, recovery transport,
  native submission, native order metadata and existing team/admin views.
- These values are customer request labels, like selected search text. They
  do not establish product identity, stock, specifications, price, compatibility,
  document ownership or permission. Page titles still come from the current
  public native object. An `entry_ref`, supplied title, ID, token or arbitrary
  query field never gains authority through this change.
- Accept only scalar text, sanitize it through the existing text boundary,
  escape it in HTML, preserve it in plain team text, and retain the existing
  total recovery limit. Reject invalid public sources as before. Do not silently
  truncate a selected request or import Contact context into other doors.
- Unchecking the selection excludes all its fields. Native language navigation
  retains the verified translated source, selected request and intent. Customer
  receipt content stays unchanged; no additional email is sent.

## Native implementation

LiveCanvas already emits the links. WooCommerce owns the existing inquiry and
metadata; its ordinary fields do not carry these Contact query values. The
existing `SelectionContext`, `SelectionView`, submission and native team consumer
are the current mechanism. Extend their allowlist and semantic data labels.
Reuse the same selection JSON and metadata key. No second handler, store, form
protection, JavaScript, layout, stylesheet or stored-page rewrite is needed.

`platform` is displayed using the existing Product / Produkt label; Documents /
Dokumente is also an existing native term. This follows the customer vocabulary
instead of exposing a raw transport key. The known document family uses the
existing English link value “Datasheets & certificates”; its German display is
“Datenblätter und Zertifikate”. Other requested document names remain escaped
customer text. These labels and the German wording require independent copy
review along with the behavior; they make no new product claim.

## Acceptance and rollback

Regressions must catch the previous empty selection and prove native submission,
escaping, array/unknown-field rejection and language transport. Use the same
snapshot's 16 actual entry cases to check form transport and unsaved native order
team/admin views without sending or persisting an inquiry. CUA acceptance covers
both language pages and viewports, project/document intents, exclusion and
language switching. Record correct long-label layout and source-link hover/focus.

Keep the preceding Contact source release frozen. This is a separate diff based
on `aaf46e95`; restore these runtime and language-catalog bytes for rollback.
No saved prose or schema migration is involved. Integration and production
acceptance remain separate from local proof and the full-site coverage matrix.
