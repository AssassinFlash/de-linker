# Coordinator deployment and owner device handoff

This branch is local preparation. It has not installed Two-Factor or enrolled any
factor in production. Local synthetic accounts, TOTP seeds, recovery codes and
application passwords are disposable test data. They must not be reused.

## Back up and install the official dependency

Use the existing cutover `Target` bound to the already verified production
WordPress docroot; the calls below are native WP-CLI arguments, not commands to
run in an arbitrary SSH home directory. Take and verify the normal recoverable
database backup streamed to this Mac first. Also save existing `two-factor/`
files, plugin activation state and `two-factor-de_DE_formal.*` language files to
the same private local backup if present; record absence if this is first install.
No backup belongs on the web host or in Git.

```python
# Read before writing; if an unexpected version/state exists, review it.
target.wp("plugin", "get", "two-factor", "--fields=name,status,version", "--format=json")
# For first installation, or a reviewed update to the pinned stable version:
target.wp("plugin", "install", "two-factor", "--version=0.17.0", "--activate")
target.wp("plugin", "verify-checksums", "two-factor", "--strict")
target.wp("plugin", "get", "two-factor", "--fields=name,status,version", "--format=json")
target.wp("language", "plugin", "install", "two-factor", "de_DE_formal")
```

An absent-plugin read returns nonzero and is expected only when confirming first
install. Do not mask a different read failure. Do not run the synthetic test
recipe against production; it explicitly accepts only native local instances.

Official stable archive:
`https://downloads.wordpress.org/plugin/two-factor.0.17.0.zip`, SHA256
`4d1b0f8e5d82e24876c2b4e86f119122e28a8dbaf76dfde495173226c3356f37`.
Verify installed files through the official checksum service, rather than using
an unreviewed free/beta substitute. Do not copy third-party plugin source into
our plugins.

## Native German language supplement

The dependency preparation uses the official formal German pack and only one
additional plural entry from `tools/admin-mfa/two-factor-de_DE_formal.po`.
Compile on the Mac with existing gettext and WP-CLI (the official archive is in
the native local download cache). The already-tested m565 artifacts are under
`wp-content/languages/plugins/two-factor-de_DE_formal.*`. Reproduction:

```sh
# In an isolated local instance, after official pack extraction:
msgcat --use-first tools/admin-mfa/two-factor-de_DE_formal.po \
  "$catalog_dir/two-factor-de_DE_formal.po" -o "$merged_po"
msgfmt --check -o "$catalog_dir/two-factor-de_DE_formal.mo" "$merged_po"
cp "$merged_po" "$catalog_dir/two-factor-de_DE_formal.po"
wp i18n make-php "$catalog_dir/two-factor-de_DE_formal.po" "$catalog_dir"
```

`catalog_dir` is that instance's actual language directory and `merged_po` is a
temporary local PO path. `just admin-mfa INSTANCE --prepare` performs these exact
operations automatically with paths resolved from the native instance registry.
Copy only the verified `.po`, `.mo`, `.l10n.php` language artifacts to the matching
production language directory through the backed-up deployment transport. Read
back their hashes. No PHP gettext filter/map or inline snippet is installed.
After installing the language files, match WordPress's language upgrader cache
invalidation; never flush the quota ledger:

```python
target.wp("eval", "wp_cache_delete(md5(WP_LANG_DIR . '/plugins/'), 'translation_files');")
```

Native readback must show `Authentifizierungscode:` and the German singular and
plural failed-attempt notice, with counts/times substituted correctly. Keep
plugin checksum verification green. A future official language update may
replace this site supplement; reapply after reviewing that update, or retire the
supplement once the official pack supplies the exact translation.

## One continuous owner-device handoff

1. Coordinator confirms official version/checksums, current administrators and
   no customer enforcement policy. Installation alone is **not MFA enabled**.
2. Owner opens their own [WordPress Profile](https://de-linker.com/wp-admin/profile.php),
   finds **Two-Factor Options**, and registers TOTP in their own authenticator.
   Owner enters/verifies the current dynamic code; choose TOTP primary and
   Backup Codes secondary. Leave email OTP unselected for this rollout.
3. Owner generates and saves recovery codes directly to their own password
   manager/offline copy. Do not export the seed, QR or recovery codes into an
   agent screenshot, ticket, chat, shared file or Git. Keep the current working
   session while testing one separate login with the authenticator.
4. Owner opens the already verified [Hostinger Security page](https://hpanel.hostinger.com/profile/security/two-factor-auth)
   in the correct hosting account and completes its authenticator setup and
   offered recovery procedure on their own device. New-device verification is
   a different setting and does not prove 2FA is on.
5. Coordinator records only booleans: TOTP enabled, primary/backup providers,
   owner saved recovery material, and separate-login success. No real factor is
   generated or retained by this engineering branch.

Keep the existing `terravolt` application password: its native hash/config match
and inventory-reader purpose were established in #564. This is a separate API
credential that continues to work without interactive TOTP, proven here with a
synthetic credential. It needs its own least-privilege migration; do not revoke
it, block all REST, or call the whole administrator identity MFA-covered.

## Rollback boundary

Restore the backed-up plugin version/files and language artifacts if installation
or language loading fails, and read back the resulting version/checksums. Keep
user/provider metadata and the existing API credential intact. Do not use
uninstall as a rollback after real enrolment: vendor uninstall removes factor
metadata. After owner enrolment, any change that removes the active factor gate
requires a deliberate recovery decision with the owner and an available working
session; this branch does not perform that operation.
