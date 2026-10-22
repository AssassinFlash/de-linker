# Legible authentication and registration choices

The full buyer-path review reaches the actual EN/DE registration form and
finds its business-type labels pushed against the right side. Native CSS
inspection shows the cause: the component library's generic `.radio::before`
has empty generated content with 100% width and height. Woo's native option
label also uses `radio`; that extra flex item consumes space before the real
text even though the label correctly requests centered alignment.

Remove generated content only from `.linker-auth .form-row label.radio::before`.
Keep Woo's labels, IDs, native inputs, full-control transparent input overlay,
order, required semantics and checked/focus rules. No PHP or JS change is
needed. Actual pointer tests also find no visual change on any unselected
choice hover. Use the existing account hover fill and teal border to expose
that affordance; the existing checked rule keeps its stronger selected fill.

The same live DOM review finds the authentication content inheriting
`Inter, ui-sans-serif, system-ui, sans-serif` rather than the existing site
font token. In the recorded Chrome document, its actual Inter-Medium glyphs
come from a browser extension, while all four site-hosted Plus faces succeed.
This is different from the earlier cross-origin font failure. Set the existing
`.linker-auth` wrapper's font family to `var(--proto-font-sans)` so sign-in,
registration and password surfaces explicitly use the already hosted site
font. Keep all words, sizes, weights, colors and page structures. Resulting
text-width and line-wrap changes inside auth are an intentional typography
correction; account dashboards, marketing, header/footer, prices and business
rules are outside the change.

Work from the deployed 1dce2406 source and an owned, fully loaded snapshot
instance. Back up its full database and exact source before changes. Preserve
EN/DE privacy source fingerprints and backslashes. Record actual custom-font
requests and actual consumers independently: a successful request or loaded
FontFaceSet does not establish which font renders a label.

Compare EN/DE at 1440/390/320 with unselected, hover, chosen and native keyboard
states. Inspect actual rendered text centering and contrast, whole-control
hit areas, exactly one checked value, arrows and visible focus. Check the
sign-in and lost-password layouts and registration's second step/error
presentation without submitting registration, accepting Terms, sending mail
or calling a model. Record intended auth reflow separately from unchanged
surfaces. Follow native WindPress Generate/present/readback, source and Spec
review, meaningful checks/CI and eventual production readback as distinct
gates; local screenshots alone do not close the full-site objective.
