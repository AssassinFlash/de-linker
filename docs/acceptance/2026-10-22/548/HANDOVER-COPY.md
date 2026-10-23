# Native recovery discovery copy

2026-10-23. One new message; adjacent Check session/Try again labels are reused.
This operational error surface follows the native recovery-handover contract.

Parent draft: “Unconfirmed requests from earlier sessions could not be checked.
Recovery data stored in this browser has been kept.” / “Unbestätigte Vorgänge
aus früheren Sitzungen konnten nicht geprüft werden. In diesem Browser
gespeicherte Wiederherstellungsdaten bleiben erhalten.”

Independent adversarial review required the actual kinds of work to be named
so requests is not mistaken for an inquiry. “Already stored” must preserve the
distinction between old retained data and a new storage write that may fail.
The parent selected and applied the reviewer's exact final pair:

EN: “Unconfirmed project creations and CSV imports from earlier sessions could
not be checked. Any recovery data already stored in this browser remains
unchanged.”

DE: “Unbestätigte Projekterstellungen und CSV-Importe aus früheren Sitzungen
konnten nicht geprüft werden. Bereits in diesem Browser gespeicherte
Wiederherstellungsdaten bleiben unverändert.”

It appears only when the native prior-scope discovery fails. Stored records
are retained; project saves remain available. New creation waits until discovery
can be checked. The message promises neither successful new browser persistence
nor automatic replay. Source/PO application is done; fixed-source/native render
acceptance is recorded with the implementation increment, not assumed here.

## Original settings review: draft

Native CUA exposed a usability gap: the pending request's only settings view
was raw JSON. The replacement uses read-only semantic facts from the exact
frozen command: column names, measurement, unit, delimiter/decimal, origin,
interval boundaries/duration, time zone/repeated-time columns and source/rights.
Existing independently reviewed EN/DE field labels and choices are reused.
No browser form state, new default or retranslation becomes the saved intent.

One new explanatory sentence is needed for the fixed interpretation assumption:

EN draft: “For this interpretation, average power is treated as constant within
each original interval. No additional measurements are created.”

DE draft: “Bei dieser Interpretation wird die mittlere Leistung innerhalb jedes
ursprünglichen Intervalls als konstant behandelt. Es werden keine zusätzlichen
Messwerte erzeugt.”

The existing explicit-UTC-offset precedence sentence is reused. The new sentence
describes piecewise constant interval means, including energy-to-mean conversion;
it does not imply filling gaps, actual meter resolution or instantaneous peaks.
Dimension: checking a frozen import before explicit recovery. Encyclopedia tool
and Lastgang vocabulary consulted; no new product category or commercial claim.
Parent preflight: Hard Stops1–9, actor/future/weight/duration, no slogan, no
unattested brand or fabricated quote all checked. Sentence cleanup keeps the
technical condition and avoids a marketing claim. Independent opposition and
final selection are still pending; this draft has not been rebuilt for native use.

Independent opposition found no false statement but required the kWh-to-mean
step to be explicit: otherwise a user who selected interval energy suddenly
sees an unexplained average-power assumption. Parent selected the reviewer's
complete pair without adding claims about missing intervals or instantaneous
power:

EN final: “If the file contains energy per interval, average power is calculated
using the interval duration. For this interpretation, average power is treated
as constant within each original interval. No additional measurements are created.”

DE final: “Bei Energiemengen je Intervall wird die mittlere Leistung anhand der
jeweiligen Intervalldauer berechnet. Für diese Interpretation wird sie innerhalb
jedes ursprünglichen Intervalls als konstant angenommen. Es entstehen keine
zusätzlichen Messwerte.”

The parent applied this final pair. Fixed-source and native rendered readback
remain distinct acceptance gates below; the initial draft is kept as history.

## Applied copy acceptance

ef30778d passed both fixed-source review axes. Native discovery503 showed the
selected recovery message in EN/DE at1440/390; existing save remained usable.
The original frozen settings and exact interpretation pair were opened and
read in both languages at those viewports. The native module/gettext hash and
phase-specific PNGs are pinned in [the manifest](handover-native/acceptance.json).
No additional customer message was added during this acceptance.
