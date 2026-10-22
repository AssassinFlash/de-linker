# Inquiry availability correction: local proof

Source reviewed: `2b2e826768aa640fca386289ef69dad6b0dc3b6b...582756b852db9d0119fcf112d072694970f537d0`.
Spec and Standards independent full-diff reviews both PASS. The reviewers checked
the exact trusted-action scope, native validation, atomic quota/dispatch,
operation binding/recovery, no-JavaScript path, unchanged resource proof policy,
staff diagnostic and unchanged Jev/model/mail policy.

## Executed checks

- Native WordPress `BusinessAdmissionTest`: 25 tests,383 assertions PASS on g522.
  Includes proof/keyless guest contact and inquiry saves, stable retry, native
  invalid-input guards and atomic quota refusal; all other action proofs remain
  strict. Native tests ran before the temporary browser-only opt-in fixture.
- Protection forms JavaScript:11 tests PASS, including both business actions
  avoiding focus/pointer challenge prewarming and submit interception, while
  draft writes still require verification.
- Changed PHP:PHPStan and PHPCS PASS. Protection JavaScript lint/format,
  TypeScript and generated build PASS. `git diff --check` PASS.
- Actual live-snapshot browser: guest EN/DE contact and inquiry submits all
  reached their native confirmation without a third-party challenge, with
  private `enforce` + business `optional` and no Turnstile keys. Four native
  records8532–8535 have customer_id0 and status `inquiry-received`; the exact
  synthetic identities are in `local-native-records.json`.
- Confirmation states captured at390 and1440 pixels under `screenshots/`;
  contact images are full-page, inquiry images viewport. The capture checked
  actual responsive layout before taking the screenshot. No stylesheet or
  customer copy changed in this correction; these are interaction/confirmation
  checks, not a new claim of whole-site pixel parity.
- Local mail stayed on disk isolation with one synthetic tester; no external
  local test mail. Jev disabled in this local fixture, no paid classification
  calls. After evidence collection the exact original wp-config bytes were
  restored, temporary include removed and local TestMode switched off.

## Before and remaining live gate

`screenshots/before-chrome-verification-failed.jpg` is the actual failed
production guest Chrome sample. No inquiry or mail was created. The same
challenge passed in a different browser; precise provider cause remains
unproven. This correction follows the owner's renewed availability priority.

Production remains on the previous version at this record. Required next gate:
green CI, merge, backed-up atomic deployment/private opt-in/cache readback,
then the authorized single-recipient synthetic submission and actual inbox
receipt. A saved inquiry or successful mail() alone will not satisfy that gate.
