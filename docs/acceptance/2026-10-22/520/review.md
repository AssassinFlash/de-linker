# Independent review and corrections

Initial fixed range: 23516938...d2432cb3. Spec: five findings (two P1, three P2),
Standards: two findings (one P1, one P2). Neither initial axis passed. Both final
axes PASS at 8dedcbc43f09a104d9001d11a8252ec960fcea31 after full initial review
and independent delta checks.

| Axis | Finding | Correction and evidence |
| --- | --- | --- |
| Spec P1 | Store API collection/item aliases bypassed the narrow action-route list | Every native mutating cart route, native case-insensitive matching; actual REST aliases and batch refusal, plus valid proof success |
| Spec P1 | Woo delegated AJAX serialized before verification and replacement forms were disconnected | Capture submit and stop propagation until verified native resubmit; reconnect after native cart events; delegated-submit regression and actual CUA quantity update |
| Spec P2 | Existing signed start and trap were bypassed with the old fill-delay check | Preserve signature/trap in contact/inquiry/Woo registration, skip only old time and connection checks; actual valid-proof trap/signature rejection and fast autofill fixtures |
| Spec P2 | Retired checkout rejected after customer/session totals were updated | Move an additional closure to native before_checkout_process; actual native checkout leaves billing country and cart unchanged |
| Spec P2 | Registration receipt assumed unverified recipient was submitter | Neutral fixed EN/DE paragraphs and subject, ignore-email route; actual native template assertions and copy-review.md |
| Standards P1 | Correctable empty/stock errors were dispatched and could not be retried | Read-only preflight after completed native recovery and before reservation; same UUID/proof correction fixtures |
| Standards P2 | Native UUID/subject associations survived live pull | Clear three meta fields in classic and HPOS SQL anonymization fixtures; unrelated order total retained |

The case-insensitive native routing fact also applies to verification body caps
and retired Store API checkout closure; those paths are normalized and tested.
No additional model, content auto-rejection, customer CSS, global configuration
change or production operation was introduced in these corrections.

Final delta review also confirmed cart-only quantity Enter, native coupon POST
carrying proof and cart nonce, early closure of the disabled shipping calculator,
and actual native registration completion. Actual CUA discovered and reproduced
the account-ui capture-handler conflict: the first unverified submit marked busy
and the verified resubmit was discarded. Both reviewers checked the correction
and native-validation interaction; the transient DOM marker grants no server
permission and is cleared in finally. Real EN outage retry and DE draft-to-inquiry
then succeeded. This source PASS does not replace combined #522 acceptance.
