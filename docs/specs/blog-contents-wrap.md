# Blog contents rail wrapping

The German inverter/battery pairing article has a 182.68px minimum-content
contents track inside its existing 180px desktop rail. At the narrower reader
breakpoint the rail is 160px, while every link still uses that oversized track.
The sticky rail's vertical overflow makes horizontal overflow scrollable too.
Actual browser inspection of all twenty articles at 1440px identifies this
article; English remains within its rail. The German defect also reproduces at
1120px. Phone contents disclosure already opens and fits at 390px and 320px.

Reuse the existing WindPress contents grid with `minmax(0,1fr)` so its track
can shrink within the rail. Use native `hyphens: auto` with `overflow-wrap:
break-word` for labels, allowing language-based hyphenation before emergency
wrapping. The two `anywhere` candidates fit the rail but stranded one or two
German letters on a separate line in the actual 1440px render; those candidates
remain rejected visual evidence. Native word breaking then produced a real
hyphen but still left two letters on the final line. Use the native minimum
fragment length of three on both sides of a hyphen, the smallest limit that
excludes that observed two-letter orphan. Keep
all labels, native heading IDs, links, disclosure behavior, reading dimensions,
typography, spacing, scroll offset and active-location behavior. Do not clip or
hide overflow, abbreviate labels, or introduce PHP/JavaScript or another layout.

Retain the exact stylesheet preimage, reuse the active snapshot instance, and
copy only blog.css into its existing WindPress volume after a guarded hash check.
Run official Generate and read back the actual compiled file before anonymous
browser acceptance. No LC record or article-data write is required.

Read both rails and all contents links in all twenty EN/DE articles at 1440 and
390. Open the native phone disclosure before checking labels. Include 1120 and
320 for the affected German article and its English pair. Require each rail's
scroll width to equal its client width and each anchor to fit the contents
track, without hiding text. Exercise overview, a middle heading, article details
and related-reading targets, native keyboard focus, phone open/close and active
location feedback. Check that the sticky header does not cover the destination.
Preserve actual screenshots and reject captures with moving scroll/state.

Independent full-diff Spec/Standards review, native/browser evidence, CI and
production readback remain distinct. Previous adjacent-navigation evidence is
fixed to its earlier source/cache; this batch must not rewrite those records.
Rollback restores the exact blog.css preimage and uses official Generate.


## Bounded current-source delivery

Integrated with the accepted `a77c1be4` font/PDP/FAQ baseline. Both blog changes form one delivery: exactly two LC article templates and `blog.css`; all three runtime files remain byte-identical to the reviewed `1203363d` candidate. No article title/prose, marketing body, header or business behavior changes. Existing complete article and interaction proofs are reused under AGENTS.md section0.1; do not repeat the44-layout or41-case matrices, image CRC counts or whole-site scans. Current-source integration checks the native two-template save/metadata/pair boundary and representative EN/DE1440/390 first/middle/last adjacent cards, one long German TOC, one real keyboard/pointer consumer, official Generate and protected data readback. Production requires a current fullSQL backup, narrow two-template content transaction, exact runtime/source/volume readback and affected online consumers. Broader full-site requirements remain open.
