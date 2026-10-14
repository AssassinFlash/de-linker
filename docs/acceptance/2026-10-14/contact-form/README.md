# Contact form mount — 2026-10-14

The deployed `/contact/` and `/de/kontakt/` stored the old fallback mount and rendered no form (recheck: `form=0`). This note is the rendering evidence for the follow-up: the form renders, the shortcode is expanded, and the styles come from the compiled WindPress cache.

## Instance

`contactform`, `http://127.0.0.1:9002`. Its `linker-commerce` is a symlink to this worktree's plugin. The pages keep the old stored mount (`cp-contact-fallback` in `post_content`, no `[linker_contact_form]`). What follows is the front-end response, not the stored content.

## Front end

Fetched this session:

- `GET /contact/` — one `<form class="linker-contact-form">`, fields `message` / `name` / `company` / `email` / `consent`, no shortcode text, no `cp-contact-fallback`.
- `GET /de/kontakt/` — the same form, `name="lang" value="de"`, labels `Ihre Frage` / `Nachricht senden`, no fallback.
- `GET /contact/?contact=sent` — `linker-form-success` with "Thank you. Your message is with the Linker team.", no fields.

The page links `wp-content/uploads/windpress/cache/tailwind.css`. That compiled file contains `#contact-form .linker-contact-form .linker-form-label`, `.linker-form-input` and `.linker-form-primary` (line 23235 and the rules after it, measured 2026-10-14). Those rules are the ones in `plugins/linker-commerce/content/windpress/auth.css`, which `WindPressVolume::files()` globs into the volume.

## Screenshots

1440 and 390, EN and DE, idle and sent. Taken on this instance. The sent state is the redirect state (`?contact=sent`), not a posted message — the test-mail rule is one letter to the tester, and a render of the state does not need one.

| file | what it shows |
|---|---|
| `en-1440-idle.png` | EN 1440, fields in order, teal Send message |
| `en-1440-sent.png` | EN 1440, thank-you card, Send another message |
| `en-390-idle.png` | EN 390 |
| `en-390-sent.png` | EN 390 sent |
| `de-1440-idle.png` | DE 1440, Ihre Frage / Nachricht senden |
| `de-1440-sent.png` | DE 1440 sent |
| `de-390-idle.png` | DE 390 |
| `de-390-sent.png` | DE 390, Vielen Dank / Weitere Nachricht senden |

`*-full.png` are the same pages, full height. `en-1440-idle-form.png` is the form region.

At 390 the submit row is `position: sticky` (`auth.css`, the 639px rule, "52px = 44px touch floor + 8px"). A viewport shot can show the button over the fields that follow it. Document order stays question, name, company, email, consent, submit — measured in the browser on this instance (document tops 559 / 800 / 932 / 1065 / submit wrap 716 because it is sticky). That stickiness is the existing mobile rule, not this mount.

## What this is not

The old live card (What can we help with?, the topic select, Prefer email / Still exploring) is the retired runtime. #68 recorded the contact form as a rebuilt surface, not a replica (`docs/acceptance/2026-10-11/68/README.md` §4). These shots are that rebuilt form.
