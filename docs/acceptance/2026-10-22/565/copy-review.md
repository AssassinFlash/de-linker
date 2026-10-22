# Native administrator notice: missing German translation

Scope: one vendor plural entry, observed at runtime with the official Two-Factor
0.17.0 `de_DE_formal` pack. Ordinary prompt, error and recovery labels were already
translated after the native translation-directory cache was invalidated. The
failed-attempt notice remained English. No customer-facing marketing, form or
email copy changes.

## Draft

English source is the vendor's unchanged singular/plural entry:

```po
msgid "%1$s failed verification code attempt on this account. The last attempt was %2$s ago. If you did not make this attempt, someone else may know your password. Change your password after you log in."
msgid_plural "%1$s failed verification code attempts on this account. The last attempt was %2$s ago. If you did not make these attempts, someone else may know your password. Change your password after you log in."
```

German draft preserved the count, elapsed-time placeholder, uncertainty that
someone may know the password, and instruction to change it after login:

> %1$s fehlgeschlagener Verifizierungsversuch für dieses Konto. Der letzte Versuch liegt %2$s zurück. Falls dieser Versuch nicht von Ihnen stammt, kennt möglicherweise jemand Ihr Passwort. Ändern Sie Ihr Passwort nach der Anmeldung.

Plural changes `Verifizierungsversuch` to `Verifizierungsversuche`, and
`dieser Versuch … stammt` to `diese Versuche … stammen`.

## Adverse review and final

Coordinator review on 2026-10-22 confirmed original meaning and formal Sie are
preserved, accepted this wording, and required keeping the change limited to the
exact vendor msgid. Final text is
[`tools/admin-mfa/two-factor-de_DE_formal.po`](../../../../tools/admin-mfa/two-factor-de_DE_formal.po).
Native gettext keeps both `%1$s`/`%2$s` placeholders and plural selection. The
supplement is merged with the official pack; it is not a PHP replacement map and
contains no provider implementation. Official plugin file checksums stay valid.
