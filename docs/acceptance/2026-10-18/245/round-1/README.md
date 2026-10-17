# #245 · PR #293 review round 1 response

Review: [Claude's decided Standards 1–6 and Spec 1–3](https://github.com/AssassinFlash/de-linker/pull/293#issuecomment-6239365278). Branch `feat/245-wp-admin-notice`; only local instance `c245`.

| Review item | Change | Verification |
| --- | --- | --- |
| Standards 1: numeric hook sources | The observer's `PHP_INT_MAX` comment explains that it reads Woo's final decision without changing it; the include filter's 50 comment names PendingGate's 40. | Source comments in `Account/AdminAccessNotice.php`; PHPCS/PHPStan and `just check`. |
| Standards 2: duplicated staff capability list | Removed the list. Store the boolean Woo supplies on the current native `WP_Session_Tokens` session, retaining its other fields and expiry. The redirected page reads this same record. A later allow replaces denial, another session has no inherited decision, and a query marker alone is insufficient. | `AdminAccessNoticeTest` decision/marker/session cases; real browser case `Woo extension decisions control the explanation across requests without a role rule`. No independent role/capability derivation. |
| Standards 3: Polylang primitives | Read the configured `PLL_COOKIE`, validate its scalar value, and use `Languages::exists`, `Languages::SOURCE`, `Languages::post_translation`. Missing/deleted twins and missing account permalink retain usable fallback URLs. | Unit fixture deliberately uses a cookie name different from Polylang's default; EN/DE, absent/invalid/array cookie and twin/permalink fallback cases. |
| Standards 4: repeated query lists | One `LANGUAGE_QUERY_KEYS` constant serves preservation and removal; the comment explains why `admin-access` crosses language changes. `cbq` remains a separately discarded cache-bust key. | Source diff and existing language-toggle browser regression. |
| Standards 5: missing unit tests | Added `AdminAccessNoticeTest`, **15 tests / 28 assertions**: Woo's decision, session isolation and retained metadata/expiry; destination and fallback matrix; every scalar field, escaped email and native URL chain. | `unit.txt`, `tdd-decision-red.txt`, `tdd-record-red.txt`, `tdd-cookie-red.txt`; full `just test`. |
| Standards 6: gettext regeneration | Regenerated POT using `wp i18n make-pot --merge --exclude=tests`, merged PO with `msgmerge --update --backup=none --no-fuzzy-matching`, compiled MO with `msgfmt --check`. The two approved DE decisions are the only changed msgstr values. | `gettext.txt`, `po-proof.py`, `po-proof.json`: **866 existing entries; 864 unchanged; 2 approved changes; 0 unexpected changes**. Translator comment is emitted before source references. |
| Spec 1: independent DE copy | Recorded Claude's challenges and exact final identity/action strings in `../copy-review.md`. EN, DE heading, explanation and account action are unchanged. | Compiled MO; updated `../de-1440-*-*.png` and `../de-390-*-*.png`; Computer Use at both widths. |
| Spec 2: specification hygiene | Removed executor, instance, hand-off/deployment and other process notes from `docs/specs/245-admin-access.md`; linked the account-chain specification `184-account-chain.md`. | Specification now contains behaviour, data flow, presentation, final copy and acceptance only. |
| Spec 3: repeated state screenshots | Explained that each language/width group's eight captures are byte-identical and prove approval-state invariance rather than eight different layouts or independent visual checks. | `state-screenshot-invariance.json`: each of 4 groups has 8 captures and 1 distinct byte content. |

## Current behavioural and visual evidence

The complete real-browser suite is **10/10 passed** (`e2e.txt`), covering the original 48 admin-address/approval-state/language/viewport combinations plus staff login, User Switching, language switching, native AJAX/admin-post/guest behaviour and the additional Woo extension-decision fixture. The latter installs a local test-only mu-plugin for its own customer, observes allow → deny → allow through Woo's existing filter, then removes the fixture and customer in `finally`.

All 32 explanation captures were refreshed by the suite, including DE at 1440 and 390 after the exact reviewed copy changes. Computer Use also signed into c245 as a temporary customer, opened `/wp-admin/users.php`, and inspected the German explanation at both widths. Its temporary customer was deleted, and the viewport restored. No CSS or Tailwind class changed in this review round; the existing compiled WindPress rules handle the longer reviewed label.

The baseline live/local parity report in `../pixel-parity.json` remains evidence for the unchanged account sign-in design, not a claim that the new explanation is deployed.

## Repeatable checks and test isolation

```sh
cd plugins/linker-commerce
/opt/homebrew/opt/php@8.3/bin/php vendor/bin/phpunit --filter AdminAccessNoticeTest

# Worktree root
python3 docs/acceptance/2026-10-18/245/round-1/po-proof.py
just check
just test

cd tests/e2e
LINKER_E2E_INSTANCE=c245 LINKER_E2E_SKIP_SERVICES=1 npx playwright test specs/admin-access.spec.ts
```

`po-proof.py` compares decoded msgstr values against the fixed reviewed commit `61253564`, ignores generated header metadata, retains plural/context keys and includes any obsolete translations. It fails on a missing or unexpected changed existing value, or if either approved DE change does not match the decision. No existing entry was removed.

The first full test attempt encountered Storybook startup exit 255. Running the exact configured `storybook dev --ci --exact-port --port 6006` command immediately afterwards started successfully, so that failure was not reproduced. No settings or product code were changed for it; only this session's diagnostic Storybook PID was stopped before rerunning `just test`. The final logs are `check.txt` and `test.txt`. Standard opt-in integration skips are visible in those logs; this ticket's real c245 browser fixtures do not skip.

No production access/write, deploy, merge, real mail or other instance/process changes. The live walk remains open on #245 for Claude after deploy.
