# Blog adjacent post navigation

The first and last published articles in each language retain an empty
Previous/Next caption when the native adjacent post does not exist. Their
remaining link is confined to half of the reader column; phone titles pile up
in two narrow tracks. Actual native LC output for all twenty published EN/DE
articles reproduces the four empty captions. Adjacent post IDs, URLs and titles
already follow the current language and native WordPress order.

Reuse `lc_the_previous_post_link` and `lc_the_next_post_link` with their native
`format` and `link` attributes. Put each existing direction caption and title
inside its link, so native WordPress emits neither when that direction has no
post. Do not introduce custom queries, JavaScript, PHP or a replacement data
store. Article prose, titles, dates, language pairs and adjacency remain native.
The same EN/DE caption strings are retained without a copy rewrite.

WindPress owns the existing reader navigation. Give its actual links a coherent
card target using the current control height, spacing, border, color, focus and
radius tokens. Hover must visibly change the card, keyboard focus must be
visible, and the entire labelled card must navigate. One available link spans
the reader column; two links stack at the existing 999px reader breakpoint.
Manual title hyphenation preserves model words, with existing emergency
wrapping for long titles. A navigation region with no links is hidden. Preserve
the surrounding reader, article contents map and other components.

Retain exact source and native template preimages and reuse the existing full
recovery baseline with a scoped incremental backup. Apply only the two actual
LC template records through the existing guarded native content writer; compare
the exact saved bytes, native pairs and metadata before and after. Compile only
the existing WindPress volume through official Generate, then log out.

The same twenty native cases must remove the four empty captions and preserve
all adjacent URLs/titles/languages. Actual browser checks cover all twenty at
1440/390 for navigation layout and first/middle/last link consumers, hover and
keyboard focus; add 320 for the longest German case. Keep actual capture
positions and reject blank or moving images. No submission, model or mail is
needed. Full source reviews, CI, integration, production readback and full-site
acceptance remain separate gates.

Rollback restores the two LC template contents and blog stylesheet from their
exact preimages, using the guarded writer and native WindPress compilation.
There is no schema migration or article-data mutation.


## Bounded current-source delivery

Integrated with the accepted `a77c1be4` font/PDP/FAQ baseline. Both blog changes form one delivery: exactly two LC article templates and `blog.css`; all three runtime files remain byte-identical to the reviewed `1203363d` candidate. No article title/prose, marketing body, header or business behavior changes. Existing complete article and interaction proofs are reused under AGENTS.md section0.1; do not repeat the44-layout or41-case matrices, image CRC counts or whole-site scans. Current-source integration checks the native two-template save/metadata/pair boundary and representative EN/DE1440/390 first/middle/last adjacent cards, one long German TOC, one real keyboard/pointer consumer, official Generate and protected data readback. Production requires a current fullSQL backup, narrow two-template content transaction, exact runtime/source/volume readback and affected online consumers. Broader full-site requirements remain open.
