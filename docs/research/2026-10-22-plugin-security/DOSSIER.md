# Installed plugin security and ACF PRO upgrade readiness

Execution ticket: [#538](https://github.com/AssassinFlash/de-linker/issues/538). Incident map: [#533](https://github.com/AssassinFlash/de-linker/issues/533). Date: 2026-10-22. Scope: installed third-party plugins/themes, official update channels, and a separate local ACF staging instance. No production plugin update, disable, deletion, account login or licence activation was performed by this worker.

## Decision

Prioritize **Advanced Custom Fields PRO 6.3.1 → genuine stable PRO 6.8.10**, retaining the same plugin slug, existing field groups, field values and Repeater capability. Do not replace it with free ACF, a beta, a mixed old/new plugin tree, or an unlicensed download. Fixing only the originally flagged 6.3.2 boundary would leave later vendor-documented security changes unapplied. The local staging baseline is ready, but the current official licensed updater returns HTTP 403 from both tested networks, so a genuine target package and post-upgrade acceptance are still unavailable. [V1–V3, E1–E7]

The coordinator's hPanel review identified ACF PRO as the only installed plugin with a vulnerability issue; the summary count of five must not be interpreted as five different vulnerable components. Seven other components have available updates and were marked secure in that view. This research independently verified installed versions and native update targets; it did not establish that every unflagged plugin is free of all vulnerabilities. [E1, E2, coordinator #538]

## Installed inventory and available update targets

Native installed inventory: 17 plugins, 16 active. The three Linker plugins are repository-owned implementations rather than third-party packages. The update target column is from the authorized native metadata refresh after the existing 06:49 backup, not an inferred version number. No listed update was installed in production by this worker. [E1, E2]

| Component | Installed | State | Available target found in this task | Channel / preservation concern |
|---|---:|---|---:|---|
| Advanced Custom Fields PRO | 6.3.1 | Active | Official stable 6.8.10; native package blocked | Existing PRO licence; vendor connect updater or authorised account ZIP. Preserve Repeater and data. |
| Classic Editor | 1.7.0 | Active | No target selected | WordPress.org channel; preserve editing workflow. |
| CookieYes / cookie-law-info | 3.5.7 | Active | No target selected | WordPress.org channel; preserve consent behavior. |
| Hostinger Reach | 1.8.4 | Inactive | 1.8.7 | Native update metadata includes a package; inactive status is intentional. |
| LiveCanvas | 4.9.3 | Active | 4.9.5 | Installed source uses `updater.livecanvas.com` with existing site API key. Preserve all LC templates and admin editor. |
| Polylang | 3.8.11 | Active | 3.9.1 | WordPress.org channel; preserve EN/DE pairing, URLs and formal German. |
| Redis Object Cache | 3.0.0 | Active | No target selected | WordPress.org channel; do not invoke local drop-in operations that flush the shared Redis database. |
| SEOPress | 10.3 | Active | No target selected | WordPress.org channel; preserve paired PRO integration and metadata. |
| SEOPress PRO | 10.2.1 | Active | 10.3 | Native licensed updater reports a package; preserve existing licence and schema/SEO settings. |
| Site Kit by Google | 1.189.0 | Active | 1.190.0 | Native updater reports a package; preserve current account/service associations. |
| User Switching | 1.12.2 | Active | No target selected | WordPress.org channel; preserve employee customer-view testing. |
| WindPress | 3.2.88 | Active | 3.2.92 | Native updater reports a package; rebuild cache and prove rendered parity before production. |
| WooCommerce | 11.2.0 | Active | 11.2.1 | Native updater reports a package; preserve HPOS and inquiry/Proforma behavior. |
| WP Consent API | 2.1.0 | Active | No target selected | WordPress.org channel; preserve consent integration. |
| Linker Commerce | 0.2.0 | Active | Repository-owned | No third-party replacement or update in this task. |
| Linker i18n | 0.3.0 | Active | Repository-owned | No third-party replacement or update in this task. |
| Linker Tools | 0.1.0 | Active | Repository-owned | No third-party replacement or update in this task. |

Themes: active child `picostrap5-child-base` 3.1.4; its required parent `picostrap5` 3.5.0; inactive fallback Twenty Twenty-Five 1.5. Neither child nor parent had an update package in the inspected cached metadata. This is update-channel evidence, not a security certification or a reason to replace the live design. [E1]

## Vendor-confirmed ACF security gap

The official 6.3.2 security release documents field-specific AJAX nonce isolation, permission checks for editor-only actions, removal of an unsafe legacy output field, and escaping/directory-listing improvements. It describes impacts on subscribers and front-end form users, so the hPanel contributor-level summary should not be used to rule out lower-privilege exposure. No mapping from a particular CVE to the actual transfer-lure incident has been proven. [V1]

The official changelog's most recent stable entry retrieved in this research is **6.8.10, released September 10, 2026**. Subsequent fixes after 6.3.2 include security changes to shortcode/private data access, upload and REST permissions, frontend form validation and token binding. A particularly relevant later entry is **6.8.5**, which fixes unauthenticated field-value writes through the WooCommerce HPOS save integration. Native production and the cloned local site both report HPOS enabled. That makes this configured integration relevant to the upgrade, without proving that anyone exploited it. [V2, E5]

The official update guide distinguishes free ACF from PRO: PRO downloads come from the owner's account, and native PRO updates require an active licence. It explains that overwriting the plugin with the proper package preserves fields and settings, while some releases may require an admin database upgrade. Therefore preserve a recoverable database as well as the previous plugin tree; do not assume file rollback reverses a database migration. The guide also describes a one-time genuine-download path for old versions, rather than substituting a third-party mirror. [V3]

## Existing PRO capability and licence readiness

Native production evidence establishes two published field groups, 90 field definitions, **10 Repeater definitions**, and 93 stored ACF field-reference/value rows. Repeater is registered as a PRO field type. The repository's current custom code principally reads preserved product data directly rather than calling ACF frontend helpers; that does not prove ACF can be removed, because its group editor, Repeater authoring and stored-data workflows remain. [E1, E5]

Only boolean licence state was published:

| Readiness fact | Observed result |
|---|---|
| ACF PRO licence value present | True |
| Cached licence status present and active | True |
| Cached status expired/cancelled | False |
| Cached next check still in future | True |
| Cached licence error present | False |
| Native updater enabled and PRO basename registered | True |
| Effective licence key present in the production context | True |
| Fresh vendor entitlement / signed package obtained | **No: HTTP 403** |

The cached licence metadata contains no `manage_subscription_url`, `view_licenses_url`, `account_url` or `download_url`. The vendor's official public account entry is `https://www.advancedcustomfields.com/my-account/`; the installed client's official licence-management entry is `https://www.advancedcustomfields.com/my-account/view-licenses/`. Neither path identifies an already authenticated account. No third-party account login was attempted by this worker. [V3, E8]

An active cached status is insufficient to assert fresh download entitlement. Conversely, HTTP 403 with an HTML body does not establish an expired licence. No renewal, additional account, licence seat assignment or paid purchase follows from these observations alone. [E1, E3, E4]

## Exact official updater block

The installed 6.3.1 PRO updater's canonical server is `connect.advancedcustomfields.com`. Its update-check route is `/v2/plugins/update-check`; the installed code also exposes `/v2/plugins/get-info?p=pro`. Both checks use the existing licence and site context; this worker did not guess alternative endpoint grids or attempt account logins. [E3, installed `pro/class-acf-updates.php`]

| Network / request | Result | Interpretation |
|---|---|---|
| Production Hostinger, native update-check | HTTP **403 Forbidden**, HTML, 134 bytes | Registered updater and effective key present; no package metadata returned. |
| Production Hostinger, native get-info | `server_error` | No package obtained through the info path either. |
| Mac, first diagnostic with mismatched local context | HTTP 400 JSON, 76 bytes | Discarded as an invalid comparison because the native client did not have an effective key for that context. |
| Mac, corrected original site context established before bootstrap, 07:48:04 UTC | HTTP **403**, HTML, 134 bytes, server Cloudflare | Effective key present; reproduces the substantive refusal on a second network. |

The valid Mac response included Cloudflare ray `a4e6e5cf4bd15e53-IAD` and no Retry-After header. Do not infer the exact provider rule or entitlement decision from those headers. Further identical retries were stopped. No 6.8.10 ZIP exists in this evidence, so its download SHA256 is deliberately **unavailable**, rather than a placeholder or invented checksum. [E3, E4]

The temporary Mac diagnostic allowed only HTTPS POST to those two canonical API paths within one CLI process. All activation/deactivation/seat endpoints and other external destinations retained local isolation. It established the original site context before plugin bootstrap and set AJAX context to suppress the old client's automatic URL-reactivation path. The copied local licence state was removed afterwards, restoring the clone's prior licence-absent state, so ordinary future admin visits cannot attempt to reassign the production licence through this staged copy. Production licence state was not reassigned. Private licence captures remain mode 0600 outside Git. [E4]

The currently installed ACF tree's **580 files match the owner's existing 6.3.1 archive byte for byte, with no extras**. The archive's SHA256 is `49cbdd37f809d4e3507514f180dd3ddb3c753c6ce8526e2dc5b85a499b114ddf`. This is useful local provenance and drift evidence; that older archive was not freshly authenticated against the vendor, and it is not a target update package. [E6]

## Concrete staged work already completed

Independent instance **a538**, URL `http://127.0.0.1:9305/`, uses this research worktree's unchanged baseline custom plugins and a production content/theme/uploads snapshot. Its mail is captured locally and outbound WordPress requests remain isolated. The snapshot's recorded content capture is 2026-10-21 16:21:32 UTC; current ACF parity was separately verified rather than assuming that older capture was still exact. The loader verified 212 products, 2,756 attachments and zero missing attachment files. [E5, E7]

The initial local provisioning's child WP-CLI process hit a 128 MiB memory failure during rewrite despite the parent instance php.ini. The owned local wp-config was backed up, then its `WP_MEMORY_LIMIT` and `WP_MAX_MEMORY_LIMIT` were set to the already intended 2048M instance limit. Re-running the failed rewrite completed successfully, provisioning resumed, and the server started. No shared/global PHP setting or custom repository source was changed. This is local setup evidence, not a claim about production PHP repair. [E7]

Before any vendor-file change, PHP 8.3.35 loaded ACF PRO 6.3.1 and the Repeater type successfully. Current production and a538 match all three canonical data digests:

| Data boundary | Current production and a538 baseline |
|---|---|
| Two groups + 90 field definitions | `287b307c2c902cef6e4c15b5c5364ce080054573d451f519fab60eba98496afe` |
| 93 ACF reference rows | `cf076b635ed83999c8c404b6179ea4b27085f0450e41a7de87e85d0bdad3546e` |
| 93 associated value rows | `ffd4bed4e522d4e3f81326ad12a97be9e746880a0c5a5b90227defe87c83ccbf` |

These checks were repeated after diagnostic cleanup and remained unchanged. The target package was **not installed**. Therefore there is no post-upgrade PHP compatibility claim, no after-upgrade field-preservation pass, and no after-upgrade EN/DE 1440/390 Computer Use acceptance claim. Completing those gates requires a genuine PRO package first. [E5]

## Next executable handoff

1. Obtain the genuine stable PRO 6.8.10 ZIP through an existing authorised vendor download route. The tested native route is blocked on both networks; resolve that vendor refusal or use the owner's existing account download. No new licence purchase or password reuse is presumed.
2. Save the package privately with source provenance, exact version and SHA256. Inspect its plugin slug and stable version before changing a538. Back up a538's current ACF plugin tree and database, retain the three data digests, and install the complete PRO tree atomically in that local instance only.
3. Run the vendor's required admin upgrade, then verify version 6.8.10, PHP 8.3 compatibility, field/group/reference/value preservation and existing Repeater editing. Recheck installed package files against the saved ZIP; preserve the current LC/WindPress theme and data.
4. Exercise EN/DE product display, account/registration, contact, inquiry submission and confirmation on desktop/mobile. Use captured local mail and native queue assertions. Capture required Computer Use states at 1440 and 390, inspect PHP errors and rendered LC/WindPress behavior. Do not manufacture an after-upgrade comparison from the unchanged baseline.
5. Only after those gates pass should the coordinator review and execute the separately authorised production upgrade with full database/plugin rollback coverage. Read back the actual web runtime and updated version, preserve accepted inquiries and pending notifications, and recheck the native path. This dossier does not close #538 or the larger security goal.

## Evidence and official sources

Private evidence root: `/Users/chesterjohn/de-linker-data/incident-20261022/plugin-security/`. No licence values or credential-bearing URLs are committed.

- E1: `installed-sanitized.json`, native versions, active states, cached licence booleans and field-type counts.
- E2: `vendor-update.sanitized.json`, native refresh at 07:17:57 UTC after the existing `cutover-20261022-0649` backup; seven update versions and package-present booleans.
- E3: `acf-plugin-info.sanitized.json`, `acf-plugin-updates.sanitized.json`; production canonical updater diagnostics.
- E4: `local-acf-updates.sanitized.json` and private diagnostic process recipe; corrected Mac request and response metadata. Invalid earlier-context result is described above and excluded from the valid comparison.
- E5: `a538-fields.before.json`, `a538-fields.ready.json`, `production-fields.current.json`, `field-comparison-summary.json`; reproducible native canonical data digests.
- E6: `acf-source-provenance-summary.json`, full file hash map and the owner's existing 6.3.1 archive.
- E7: local a538 snapshot note, loader readback, `a538-ready.json`, instance config backup and provisioning logs; `a538-config.before.php` remains private.
- E8: `license-portal-readiness.json`, boolean-only inspection of existing cached portal-link fields.
- V1: [ACF 6.3.2 Security Release](https://www.advancedcustomfields.com/blog/acf-6-3-2-security-release/), retrieved through Apify.
- V2: [Official ACF changelog](https://www.advancedcustomfields.com/changelog/), retrieved through Apify; latest stable 6.8.10 and later security boundaries.
- V3: [Official ACF update guide](https://www.advancedcustomfields.com/resources/how-to-update/), retrieved through Apify; PRO licence/download path and preserved fields/settings.

Apify run `IFEEYLpfbOB1eGRQ7`, dataset `WwwmxkmnfFpL2vFw9`, succeeded at 07:14:12 UTC with four pages; the unrelated beta-document page is excluded from the recommendation. Native licensed metadata requests used the installed vendor client under explicit coordinator authorisation. No model call, real test mail or malicious-destination request was made.
