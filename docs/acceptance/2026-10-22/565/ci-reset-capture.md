# Native reset-mail capture regression

PR580's `mu-smoke` run `39819112754` reached the EN native reset link and
`reset-link-sent=true` without a customer factor challenge, then the actual
`admin-mfa.php reset-link customer` fixture threw its missing-message exception.
The original CI message was not retained. This record proves a deterministic
counterexample in that fixture; it does not claim to know the original random key.

## Cause and minimal correction

The local native Woo mailer produced a single-part MIME message declaring
`Content-Transfer-Encoding: 8bit`. The fixture nevertheless applied
`quoted_printable_decode()` to every complete EML. In a plain URL, `key=ab…`
contains a valid quoted-printable byte sequence: the decoder consumes `=ab`, so
the reset-URL expression cannot find it. Plain `id=42` can likewise be changed.
Queue bodies are already native decoded Message bodies and do not need this step.
This is an input-dependent test-reader failure, independent of Genie rendering.

The fixture now splits the captured MIME headers/body, leaves 7bit/8bit/binary
bodies unchanged, decodes quoted-printable only when declared, and decodes base64
only when declared. Unreadable or unsupported captures do not become a valid
link. The existing local-origin, same native user and
`check_password_reset_key()` checks remain intact. No mail producer, reset key
semantics, authentication policy or production behavior changed.

## Evidence

The dedicated registered `m565ci` instance owns WordPress9344. Its plugin symlink
was first verified against the unchanged565 checkout and then refreshed with
native `just up` to the isolated `codex/fix-565-reset-capture` tree, based on
`origin/main 8cbb3432`. No database rebuild, production access or shared viewport
change was involved.

| Layer | Before | After |
|---|---|---|
| Actual Woo reset and native key | EN native request returned sent/no-factor; a scoped synthetic key prefix `ab` was applied only during native `get_password_reset_key()` for the fixture customer. Woo emitted a real8bit capture; raw URL/key passed the native verifier, blanket QP decoding removed the URL, and the old fixture threw the same critical error | Same controlled prefix, native generation/verification and Woo capture; revised fixture found the valid URL |
| Actual fixture with offline mailbox/native-check seams | 6 failures across 7bit/8bit/base64 and URL-byte preservation; declared QP and invalid-key/origin/user rejection already passed | **20 tests PASS**, including all existing safety cases,8 encoding cases and3 rejection boundaries. These seams are fast parser regressions, not a substitute for native key proof |
| Complete native runner | Prior CI failed during reset-link extraction | **36/36 PASS**: official exact dependency/checksum verification; native wp-login and Woo EN/DE; TOTP and backup-code replay; approved/pending customer lanes; actual password reset completion and login with the changed synthetic password; API password lanes |

`ruff check`, `ruff format --check` and strict mypy pass for the runner and its
Python safety tests. The CI-equivalent WPCS command passes for both MFA PHP
fixtures; diff whitespace is clean. No frontend/build/CUA rerun is claimed for
this test-reader-only change.

Private evidence is under `incident-20261022/565-ci-diagnosis`: `minimal-reset.json`,
`forced-reset.json`, `forced-reset-green.json`, `capture-red.txt`,
`capture-green.txt`, `native36-green.json`, static-check outputs and
`cleanup-readback.json`. Actual tokens, passwords, factors, cookies and complete
messages stay private. Captures remain local; no external mail was sent.

Final native readback confirms `en/de`, both local mail/HTTP guards, the new
checkout symlink, no remaining owned fixture option and zero `mfa565_` users.
The original565 checkout stayed clean and its published browser evidence was not
edited. New combined CI/release work remains with the coordinator.
