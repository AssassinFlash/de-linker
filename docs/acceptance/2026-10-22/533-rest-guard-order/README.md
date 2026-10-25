# REST guard ordering — local acceptance

Base: reviewed `b29a979a16c39651fdbfb265413621f9d96f599f`; branch `codex/533-rest-guard-order`. Runtime change is only MU user-guard registration priority10→20, after the observed ACF6.3.1 initializer. Reminder stop behavior remains inherited unchanged.

Production diagnosis was read-only: ordinary anonymous GETs, matching MU hashes, actual callback provenance and native user0 direct/REST comparisons. No account values are copied into the evidence. ACF's initialization callback erased an earlier WP_Error. This source repair has not been deployed by the implementer.

## Executed checks

- New native regression against the unchanged guard: **RED1 test /5 assertions**, actual anonymous response200 instead of403.
- SiteGuardsSmokeTest after repair: **4 tests /25 assertions PASS**, including the same-priority null initializer, anonymous collection/item refusals, administrator list_users positive control, unrelated public REST positive control, HTTP baseline headers/refusal and engine-pin installation.
- MU unit scope: **12 tests /40 assertions PASS**; complete MU PHPStan and changed-file WPCS **PASS**.
- Separate owned s533rem native probe loaded the actual production-byte-equal ACF6.3.1 initializer class with a minimal disabled-setting getter, not full plugin activation. With the new MU file temporarily installed: anonymous collection/mixed-case item403, authorized administrator200, unrelated public types200. The original local MU file was restored in finally; no source/config/credential or business data changes were made by that probe.
- The pending inventory candidate was examined only in a private harness: an injected already-authenticated selected state plus native administrator showed its priority10 denial erased to200, and request-local priority20 restored403. This isolates ordering; it is not a revalidation of actual application-password authentication. No candidate source is part of this branch.

Private incident evidence lives under `attack-continuity/`: `wp-rest-user-filter-trace.json`, `wp-acf-cause-evidence.json`, `wp-guard-order-red.txt`, `wp-guard-order-green.txt`, `wp-guard-actual-acf-fixed.json`. No keys, credentials, returned user values or proprietary plugin copy are committed.

## Remaining gates

Independent full-diff Spec/Standards reviews, exact-head CI, coordinator-owned production backup/deployment and fresh HTTP403 readback remain pending. Local status is not production enforcement. No UI/copy/CSS changed, and no new visual acceptance is claimed.
