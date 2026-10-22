# Administrator MFA without customer enrolment

Issue [#565](https://github.com/AssassinFlash/de-linker/issues/565), based on the
[fixed identity research](https://github.com/AssassinFlash/de-linker/blob/81cd4a63235bf77cc76dd865e1e71001fcfb9f44/docs/research/2026-10-22-admin-identity/DOSSIER.md).
Implementation base: `1f0547574a1a2582cf3ded2f6bf807dfc7284ea4`.

## Decision

Use the official free Two-Factor **0.17.0** dependency. An administrator explicitly
registers their own TOTP authenticator and backup codes in WordPress Profile.
No customer role, registration, account approval, session policy, REST permission
or public form is changed. Installing the plugin does not enrol an administrator.

| Need | Native owner | Evidence required |
|---|---|---|
| Per-user TOTP setup | Two-Factor REST setup | Wrong setup code leaves no usable key; correct code enables the user's provider |
| Administrator login | WordPress authentication / Two-Factor | Password alone creates no authenticated cookie/session; both wp-login and Woo reach factor challenge |
| Recovery | Two-Factor Backup Codes | One successful use consumes one code; replay fails |
| Customers | Native Woo login / registration / reset | Approved and pending customers have no configured factor and gain no MFA step, EN/DE |
| Public submissions | Existing Protection + native forms/Woo | Real proof/ledger/save under enforce; provider outage retains review intake; no account requirement |
| API credentials | Native application-password authentication | Ordinary password refused in REST for MFA user; synthetic application password remains a separate lane |
| German provider notice | Native gettext PO/MO/PHP catalog | Merge only the observed missing vendor notice; keep official translations and vendor source intact |

Native testing found no authentication bridge necessary. Accordingly this change
contains no new production PHP authentication filter, inline translation map,
Code Snippet, role enforcement or public-page design change. The two-form German
supplement is dependency data, compiled with native gettext/WP-CLI.

## Execution boundary

`just admin-mfa INSTANCE --prepare` accepts a registered isolated local instance
whose Commerce symlink points to this checkout. It verifies the pinned official
archive and installed plugin checksums, installs the official formal German pack,
merges the site supplement, compiles native language artifacts and invalidates
only WordPress's translation-directory index. It then uses disposable local
users, factors and application passwords. No remote target argument exists.

The opt-in public-provider fixture requires an exact owned docroot, local
environment and local mail capture. Only the challenge SDK and canonical
siteverify response are synthetic; browser identity, prepare/verify endpoints,
proof signatures, quota ledger, preflight, dispatch and native records remain
real. Success and outage must be distinguished in evidence. It never substitutes
a success page. Existing quota journals are not reset.

The production installer and real factors are coordinator/owner work after
review and CI. Runbook and actual acceptance are in
[the acceptance record](../../acceptance/2026-10-22/565/README.md). The owner must
control their own authenticator, recovery material and final device verification.
