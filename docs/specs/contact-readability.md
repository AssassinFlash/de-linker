# Contact reading and disclosure clarity

The public EN/DE Contact page crowds its secondary headings with display tracking, splits short German prose words, and presents a mobile introduction disclosure as the same action as the separate form link. On the actual current native page the mobile summary is24px high and retains a plus when open. Desktop consent labels measured20.34375px high. These are this batch's defects; the cold-loading global header is a separate repair.

Use the existing Contact LC composition and WindPress surface. Keep the hero H1, authored line breaks, sizes, fonts, widths and native form/draft/language behavior. Preserve all paragraphs, real CTA labels/links, privacy content and stored script escapes.

## Intended changes

- Apply the existing `--proto-track-title` token to intro/form/reply/rail/story/afterword secondary headings only. Keep the verified H1 wrapping at800/801/1440 and both languages.
- Use manual hyphenation for Contact German paragraphs, retaining ordinary wrapping and long-token fallback.
- Keep native details/summary. The mobile summary uses the existing44px control target, constant descriptive label, and decorative CSS plus/minus according to `[open]`; clear hover/focus feedback on the dark hero. No second toggle handler.
- Native required consent label uses the existing12px small-text token and44px control target. Checkbox, required validation, native label activation and state retain their original semantics.

The two LC page bodies need one exact reviewed label substitution each inside the existing script: `t('Start a conversation','Gespräch beginnen')` in `aboutDrawer.innerHTML` becomes `t('About contacting Linker','Kontakt mit Linker')`. Do not replace the separate actual CTA or any other occurrence. English and German final wording underwent adversarial copy review; draft, review and final record are in the bounded evidence directory.

## Verification and publication

Use the existing9410 native snapshot instance. Before/after EN/DE ×1440/801/800/390 in normal and no-script modes: actual headings, prose, word ranges, native summary closed/open/closed, focus/keyboard/pointer, consent label and checked state, no new horizontal overflow, form inputs and language persistence. Scroll through reply and lower story/afterword; capture actual intended reflow rather than treating it as unapproved parity. Any already-existing loading-header overflow stays an independent failure.

Source Spec/Standards reviews use the full batch diff. Data label writes use the existing reviewed `repair-legal-script.py/.php` transport/write mechanism, not a new WordPress writer: base64 JSON via stdin, exact old bytes under row locks, native `wp_update_post(wp_slash(...))`, two-row transaction, byte-exact readback and rollback on failure. Verify reciprocal native EN/DE pair and exact one old/new label, preserve all outside bytes and backslash counts; repeat must be a no-op. Keep current complete native controls and scoped per-page recovery before writing. A production data write additionally requires the completed current full incremental backup, independent native readback and actual online matrix. No form Send, registration, real mail or model test.

Evidence root: `/Users/chesterjohn/de-linker-data/privacy-visual-20261021/home-image-loading-20261023T0130Z/contact-readability-20261024`. This batch cannot close whole-page or whole-site acceptance or claim loading-performance gains.
