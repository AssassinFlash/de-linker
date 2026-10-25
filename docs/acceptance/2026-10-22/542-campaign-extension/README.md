# Confirmed transfer-activity domain extension

On22October2026 the15:37:52UTC native readback showed440 prior campaign matches,
three retained campaign samples and21 separately saved verification-held records.
A subsequent read captured24 such records; this is a later, different observation.

Two independent local inspections verified all24 saved-body SHA256 values and
strict whole-message matches to the existing transfer-bait pattern, with exactly
the new host `xtimex.buzz`:14 `забрать`,10 `получить`. No record contained extra
business text. All24 were held; all24 did not match the earlier host-only rule.
The raw private evidence file SHA256 is
`417035fd356ab7739f81d393d40626271cd2c01312fee4845d92970e90f4ec32`.
No attack link was visited and no raw customer identity or message is published.
This finding only covers those24 records; it does not classify every review hold.

The narrow rule now recognizes the same complete transfer sentence followed by
a URL whose parsed host is exactly `fredmer.buzz` or `xtimex.buzz`. The rule ID
advances to `transfer-confirmed-20261022-v2`; the disable option, shared existing
three-sample pool and accumulated count are preserved. Existing saved records
keep their historical rule IDs. No record, notification or quota is removed,
reset, released or retroactively reclassified.

Russian technical requests, ordinary links, quotations/reporting, added business
text, host substrings and userinfo-host tricks remain outside the rule. Jev
labels do not participate in this decision. The independent general intake and
mail capacity work remains required: this is a confirmed-activity extension,
not protection against every future domain or different message.

The isolated native instance `c542` (WordPress7.1.3/WooCommerce11.2.0, port9356)
first ran the expanded checks against the old rule:2tests/109assertions, two
failures. The second host created an extra normal order instead of using the
existing three-sample pool, and direct matching returned false. After the narrow
change, the entire real `SafeIntakeTest` suite passes **21tests/360assertions**.
The two touched PHP files pass WPCS. The tests keep exact routing, record counts,
whole messages, no extra jobs, disable behavior and the independent review path.

Exact-head CI, independent diff review, browser acceptance and the guarded
current-source publication/readback remain required before a production claim.
