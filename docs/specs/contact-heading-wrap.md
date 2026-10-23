# Contact heading word boundaries

At a 390px viewport the native German Contact hero renders `gemeinsam` as
`gemein-sam`, and the utility Contact invitation renders `Gesamtlösung` as
`Gesamtlö-sung`. Both use the loaded Plus Jakarta Sans font and fit within their
current columns. The headings inherit automatic German dictionary hyphenation
from the site base. The existing installer heading already uses manual
hyphenation to keep words readable.

In the existing WindPress Contact styles, apply manual hyphenation only to
German Contact h1/h2/h3 and shared Contact invitation h2. Preserve the words,
authored breaks, fonts, widths, columns, spacing, body text and all interactions.
English selectors must not match. Long words may still use existing wrapping;
do not add nowrap or hide overflow. This is a rendering correction with no
customer copy, markup, PHP, JavaScript or page-content change.

LiveCanvas already supplies the heading markup. No composition or Woo behavior
needs to change. Two inherited typography overrides belong in the existing
WindPress pipeline. There is no new shortcode, handler or styling channel.

Before editing retain exact stylesheet preimages. Compile in the existing
snapshot through native WindPress and log out after local administration.
Check both languages at 1440/390/320 for Contact and utility, plus actual EPC,
services, product-list and blog invitation consumers at 1440/390. Verify loaded
fonts, complete words, container/viewport containment, heading visibility and
unchanged body styles; exercise the phone intro and form anchor. Keep baseline
and final source identities separate. No CSS-mirroring unit test is needed for
these reversible declarations; real rendered checks and full source reviews are
the acceptance seam.

Restore the two stylesheet preimages and compile them for rollback. No database
migration or saved-page mutation is involved. Integration, production readback
and complete full-site/pixel acceptance remain independent gates.
