# Contact form mount — 2026-10-14 (recheck lane, branch `fix/recheck-contact-form`)

The deployed `/contact/` and `/de/kontakt/` store the old fallback mount and rendered no form (recheck: `form=0`). This note is this branch's rendering evidence: the form renders, the shortcode is expanded, the fallback line is gone, and the styles come from the page content's own style block plus the compiled WindPress cache.

## Instance

`contactform`, `http://127.0.0.1:9002`. Its `linker-commerce`, `linker-i18n` and `linker-tools` are symlinks into this worktree, so every capture below runs this branch's `Contact\Module`. The instance's pages keep the old stored mount — no `[linker_contact_form]`, no content write by this lane (the mount happens at render time, which is the fix).

Two stored shapes were exercised, one per page:

- **EN post 10 (`contact`)** — the deployed shape, restored verbatim from the recorded live snapshot (`plugins/linker-i18n/tests/fixtures/live/pages.json`, entry `contact`): fallback div plus the line wrapped in `<noscript>`. Exercises the swap branch (`mount_form` replaces the mount with the shortcode).
- **DE post 11 (`kontakt`)** — the migrated shape, restored verbatim from the t110 instance's post 6917: mount already `[linker_contact_form]`, no fallback. Exercises the already-mounted branch (only leftover cleanup can act).

Why a restore was needed: both instance pages had been re-saved at 13:33 UTC (before this session) through a path that stripped `<script>`, `<style>` and `<noscript>` from the content — the page's own design CSS then printed as text and the fallback line lost its wrapper (`wp post get` evidence, `post_modified` 2026-10-14 13:33:29 on posts 10 and 11; every other page 12:58–12:59). The deployed site does not have this damage — `de-linker.com/contact/` and `/de/kontakt/` fetched 2026-10-14 still carry the tags and the `<noscript>`-wrapped line. The restore puts the two real stored shapes back; the bare-paragraph shape that the stripped save produced is the `contact-page-snapshot.html` fixture, which the unit tests run through the same mount.

## Front end, fetched this session

- `GET /contact/` — one `<form class="linker-contact-form">` (fields `message` / `name` / `company` / `email` / `consent`), `cp-contact-fallback` count 0, no shortcode text, `<style data-site-css>` intact.
- `GET /de/kontakt/` — the same form, `name="lang" value="de"`, labels `Ihre Frage` / `Nachricht senden`, `cp-contact-fallback` count 0.
- `GET /contact/?contact=sent` — `linker-form-success` with "Thank you. Your message is with the Linker team.", no form fields.
- With the previous session's build (main before this branch) the same instance rendered the form but kept the bare fallback line under it (`cp-contact-fallback` count 1) — the residual this branch removes.

The page links `wp-content/uploads/windpress/cache/tailwind.css`. That compiled file carries the `#contact-form .linker-contact-form` rules from `plugins/linker-commerce/content/windpress/auth.css`, which `WindPressVolume::files()` globs into the volume.

## Screenshots (this session, Playwright, 1440×900 and 390×844, EN and DE, idle and sent)

| file | what it shows |
|---|---|
| `en-1440-idle.png` / `-full.png` | EN 1440: hero left, rebuilt form right, no fallback line |
| `en-1440-idle-form.png` | the form region itself: fields in order, teal Send message |
| `en-1440-sent.png` / `-full.png` | EN 1440 thank-you card ("Send another message") |
| `en-390-idle.png` / `-full.png` | EN 390: stacked form |
| `en-390-sent.png` | EN 390 sent |
| `de-1440-idle.png` / `-full.png` | DE 1440: `Ihre Frage` / `Nachricht senden`, no fallback line |
| `de-1440-sent.png` | DE 1440 sent |
| `de-390-idle.png` / `-full.png` | DE 390 |
| `de-390-sent.png` / `-full.png` | DE 390 sent |

The sent state is the redirect state (`?contact=sent`), not a posted message — the test-mail rule is one letter to the tester, and a render of the state does not need one.

At 390 the submit row is `position: sticky` (`auth.css`, the 639px rule, "52px = 44px touch floor + 8px"): a viewport shot can show the button over the fields that follow it. Document order stays question, name, company, email, consent, submit.

## What this is not

The old live card (What can we help with?, the topic select, Prefer email / Still exploring) is the retired runtime. #68 recorded the contact form as a rebuilt surface, not a replica (`docs/acceptance/2026-10-11/68/README.md` §4). These shots are that rebuilt form, in the restored page design.

Two local artifacts are visible and out of scope: hero photos are broken (the snapshot's media files are not in this instance's uploads) and the page script logs two console errors against the local stack. Neither exists on the deployed site's content, and neither touches the form mount.
