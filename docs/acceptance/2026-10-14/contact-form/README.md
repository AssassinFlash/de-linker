# Contact form mount — 2026-10-14 (recheck lane, branch `fix/recheck-contact-form`)

The deployed `/contact/` and `/de/kontakt/` store the old fallback mount and rendered no form (recheck: `form=0`). This note is this branch's rendering evidence: the form renders, the shortcode is expanded, the fallback line is gone, and the styles come from the page content's own style block plus the compiled WindPress cache.

## Instance

`contactform`, `http://127.0.0.1:9002`. Its `linker-commerce`, `linker-i18n` and `linker-tools` are symlinks into this worktree, so every capture below runs this branch's `Contact\Module`. The instance's pages keep the old stored mount — no `[linker_contact_form]`, no content write by this lane (the mount happens at render time, which is the fix).

Two stored shapes were exercised, one per page:

- **EN post 10 (`contact`)** — the deployed shape, restored verbatim from the recorded live snapshot (`plugins/linker-i18n/tests/fixtures/live/pages.json`, entry `contact`): fallback div plus the line wrapped in `<noscript>`. Exercises the swap branch (`mount_form` replaces the mount with the shortcode).
- **DE post 11 (`kontakt`)** — the migrated shape, restored verbatim from the t110 instance's post 6917: mount already `[linker_contact_form]`, no fallback. Exercises the already-mounted branch (only leftover cleanup can act).

Why a restore was needed, and what the stripped shape is: both instance pages were re-saved at 2026-10-14 13:26:18–13:33:29 UTC — 56 revisions of posts 10 and 11, every one carrying `post_author = 0`, i.e. saved with no current user (a revision's author is the saving process's user; the instance's other pages were last saved 12:58:45–12:59:05 with author 1). Those saves dropped the tags `<script>`, `<style>` and `<noscript>` and kept their text (the page's own JS/CSS then prints as text). That is the shape kses leaves: a save without `unfiltered_html` runs the content through `wp_filter_post_kses` on `content_save_pre`, and none of the three tags is in the allowed post HTML — probed on this instance 2026-10-15, `wp eval 'echo wp_kses( "<p>alpha</p><script>s()</script><style>.x{}</style><noscript>nos</noscript>", "post" );'` → `<p>alpha</p>s().x{}nos`. Which process ran those saves is not recorded anywhere WordPress keeps, so the writer stays unidentified (routed to the main session, see the PR's openQuestions); the two writers at hand are ruled out by measurement — the snapshot loader runs `kses_remove_filters()` before it inserts (`plugins/linker-i18n/tests/fixtures/seed.php:78`, the code-side evidence) and the snapshot-loaded t110 pages keep `<script>`/`<style>` (posts 6917 and 28, both already in the migrated shape, so the fallback line is not in them at all), and a WP-CLI re-save keeps all three tags (probed here 2026-10-15: `wp post create` and `wp post update`, with and without `--user`). The bare fallback paragraph in the fixture `contact-page-stripped-save.html` is what those saves left in the region. Scope was these two posts alone (revision 77 holds the contact section on its own, revision 78 the whole page without the tags); my own restore landed at 14:19:54/14:19:55 (revisions 79/80, author 1). The deployed site does not have this damage — `de-linker.com/contact/` and `/de/kontakt/` re-fetched 2026-10-15 still carry the tags and the `<noscript>`-wrapped line. The restore puts the two real stored shapes back.

## Rendering path: live versus this instance (read 2026-10-14, re-read 2026-10-15)

This instance is **not** the live rendering path; the captures above prove the mount, not the live page chrome. Measured, read-only:

- **Live** (`ssh hostinger-de-linker /usr/local/bin/wp --path=… post meta get` / `plugin get livecanvas` / `plugin list` / `option get stylesheet`, re-read 2026-10-15): pages 28 (`/contact/`) and 6907 (`/de/kontakt/`) carry `_lc_livecanvas_enabled=1` and template meta `page-templates/empty.php`; livecanvas 4.9.3 is active; theme `picostrap5-child-base`. In non-editing mode LiveCanvas removes the **core** `the_content` callbacks (`livecanvas/modules/content-filtering.php:33-45`: do_blocks(9), wptexturize, convert_smilies(20), wpautop, shortcode_unautop, prepend_attachment, wp_filter_content_tags, wp_replace_insecure_home_url, capital_P_dangit(11), embed(8,8), wp_filter_content_tags(12)); `remove_all_filters('the_content')` runs only in editing mode (same file `:22-25`, `?lc_page_editing_mode` + `edit_pages`). The module's mount filter (priority 9) and `do_shortcode` (11) are not in the removal list. The LC dynamic template does not take LC pages over (`livecanvas/modules/templating.php:19` requires `!lc_post_is_using_livecanvas`); the two line citations are read from the t110 instance's copy of the plugin (`…/plugins/livecanvas/modules/`), 2026-10-15. Consequence, visible in the live HTML re-fetched 2026-10-15: the served region is the stored region byte-for-byte — the `warranty` anchor region of `pages.json`'s `contact` entry appears verbatim in the response, clean newlines between anchors, no `<br />`, no wrapped `<p>`.
- **This instance**: no livecanvas plugin, theme `picostrap5` (parent), post 10 has no `_lc_livecanvas_enabled` (`wp plugin list`, `wp option get stylesheet` → `picostrap5`, `wp post meta get` → no such key, re-read 2026-10-15). The full core `the_content` chain runs here, so local renders carry wpautop artifacts (`</p>` and `<br />` between the anchors, `<p>` around the page script) that live does not have — visible in the re-fetched local HTML.
- **t110** (livecanvas active + child theme) is the live-like comparison instance; its contact pages (posts 6917 and 28, re-read 2026-10-15) are in the migrated shape — mount already `[linker_contact_form]`, no fallback line — and kept `<script>`/`<style>`, which is what rules the loader out as the writer of the stripped save (see above).

The mount conclusion does not depend on the path: both paths feed the filter the same raw stored region (the live shape was read byte-identical in the live fetch, the i18n live fixture and the instance dump).

## Front end, re-fetched 2026-10-15

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

The old live card (What can we help with?, the topic select, Prefer email / Still exploring) is the retired runtime. #68 recorded the contact form as a rebuilt surface, not a replica — verbatim: "线上像素级比对不适用本票两块新面（搜索框芯片与联系表单是新建/重建面，非复刻面）" (`docs/acceptance/2026-10-11/68/README.md` §4). These shots are that rebuilt form, in the restored page design.

That record is not a ruling, and this note neither widens nor narrows it: the owner's 2026-10-10 pixel ruling covers the marketing pages, and which baseline it takes for `/contact/` — the retired card or this rebuilt form — is not ruled. The question goes to the owner with this pull request's open questions; the debt ledger is left as the review round wrote it.

Two local artifacts are visible and out of scope: hero photos are broken (the snapshot's media files are not in this instance's uploads — `2026/08/lk-contact-linker-team-in-barleben.webp` is absent, re-checked 2026-10-15) and the page script logs two console errors against the local stack. Neither exists on the deployed site's content, and neither touches the form mount. They are visible in the viewport shots as the WP admin bar and the broken hero, recorded here rather than shot around; whether to re-shoot with the snapshot's uploads installed is the main session's call.
