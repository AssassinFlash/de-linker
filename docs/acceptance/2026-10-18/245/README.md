# #245 · Customer wp-admin explanation

Implementation branch: `feat/245-wp-admin-notice`. Instance: **c245**, `http://127.0.0.1:9096`.

## Local baseline

`just sync c245` created only this instance; the shared snapshot lock was held by another session. Without changing its lock/process, this session completed `just pull load c245 latest` using snapshot `20261018-0218` (read-back timestamp `2026-10-17T18:25:44+00:00`, local 2026-10-18). Loader readback: 212/212 published products, 2755/2755 attachments, no missing attachment files, no live-origin addresses left, LC/SEOPress licences applied. User Switching **1.12.2** is active from the snapshot. Admin entry was `just login c245 --user 857558227@qq.com`. No production write/deploy/merge, other instance change or real mail send.

## Completion evidence

| Criterion | Status | Evidence |
| --- | --- | --- |
| Keep Woo's protective redirect | Done | `AdminAccessNotice::protect()` returns Woo's boolean unchanged; one-use redirect destination adapter. `docs/specs/245-admin-access.md` explains native-first choices. |
| Customer `/wp-admin`, `/wp-admin/`, `/wp-admin/users.php` | Done | Browser assertions across approved, pending, restricted and rejected existing sessions; 48 address/state/language/viewport combinations. |
| EN/DE, 1440/390, every approval state | Done | `{en,de}-{1440,390}-{approved,pending,restricted,rejected}-{admin,users}.png`. Same explanation for each approval state. |
| EN-first / independently written formal DE, copy challenge recorded | Done | `copy-review.md`; five source strings and compiled German MO. |
| One click signs out and presents staff login; real staff login reaches wp-admin | Done | Native WordPress form submitted in EN/DE; `{en,de}-staff-login.png` and `{en,de}-staff-after-login.png`. Fixed return target asserted before submit; actual admin body/URL asserted after. |
| Go to my account | Done | Correct translated marker-free account URL asserted in every combination. Existing account approval gate remains unchanged. |
| User Switching unaffected | Done locally | Real user-list Switch To → customer → denied admin explanation → plugin's original fixed Switch back → staff wp-admin. `user-switching-customer.png`, `user-switching-back.png`. |
| Language switching and native exemptions | Done locally | EN↔DE keeps the explanation; AJAX/admin-post have no notice redirect, guests keep native staff-login. |
| LC composition / WindPress style | Done | New LC account fragment under existing account page, scalar data adapter, no PHP layout. WindPress compiled through c245 admin; `windpress.txt`. |
| Existing account design pixel parity | Done | `pixel-parity.json`: EN/DE × 1440/390, every full-page pair has **0 unmasked different pixels**, no masks. Raw `parity-{live,local}-*.png` attached. |
| Spec + Standards | Self-review done; independent Claude review pending | `review.md` records both; Claude reviews the PR. |
| Live customer/staff/User Switching walk | **未完成** | Explicitly reserved for Claude after deployment; this session cannot deploy or write production. |

The new explanation is the owner-authorised #245 change. It has no live counterpart before deployment; the pixel comparison proves preservation of the existing account sign-in design, not live presence of the new behaviour.

## Repeatable validation

```sh
# Only c245. Services are not used by this account-only suite.
cd tests/e2e
LINKER_E2E_INSTANCE=c245 LINKER_E2E_SKIP_SERVICES=1 npx playwright test specs/admin-access.spec.ts

# From the worktree root: read-only live/local visual comparison.
node docs/acceptance/2026-10-18/245/capture-parity.mjs
python3 docs/acceptance/2026-10-18/245/compare-parity.py

just check
just test
```

Browser fixtures create and delete their own users in `finally`; no existing user's password, locale, approval or site option is changed. The rejected fixture uses a pre-existing session to test the denial explanation without relaxing rejection at sign-in. Mail remains the local file recorder. The suite can run again without clearing a table or manually resetting state.

TDD evidence: `tdd-red.txt` is the original failed real-browser notice assertion. `tdd-language-switch-red.txt` is the failed language-toggle regression discovered during Computer Use. Final results are in `e2e.txt`, `check.txt`, `test.txt`; screenshot rerun and fixture repeatability are recorded alongside them. Computer Use inspected the actual EN/DE card at 1440 and 390 and caught/fixed the long German primary action by stacking only this card's buttons in WindPress.

## Scope and change ledger

- Owner-authorised change (#245): customers receive the staff-area explanation after Woo's native redirect; EN/DE card and two actions; language-switch state is retained.
- Existing account design, approval rules and authentication remain in their own channels. Pending accounts staying signed in is **#222**; inquiry submission is **#246**. No implementation from either ticket is included.
- Claude owns the independent review, deployment and production readback. Rollback requires the preceding commerce plugin version and its preceding WindPress volume/cache; no content or database migration was introduced.

The standard PHP run skips its 72 opt-in integration tests when the WordPress integration bootstrap is absent; the ticket's real HTTP/session fixtures run separately against c245 and are not skipped.

Final repeatability readback: the 9-test suite passed, then the four parameterised approval-state tests passed again while capturing all 32 state screenshots. `just wp c245 user list --search='c245-*' --fields=ID,user_login` returned no fixture users after both suites and the Computer Use fixture were cleaned up. The migration suite additionally has 9 environment-gated integration skips in the standard run; see the complete test log.
