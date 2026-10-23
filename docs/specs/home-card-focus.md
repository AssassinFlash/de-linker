# Homepage white card focus

The real EN/DE homepage → offer-contact walkthrough showed a focused scene card
CTA with `2px solid white` and a `4px` offset on the card's white background, at
1440, 390 and 320. Its hover text already changes from dark green to teal, and
Enter reaches the localized offer form. Fix the visible keyboard indicator.

The saved LC scene shares a white focus ring between links over the photograph
and this nested white card. Preserve the existing LC structure and all content,
targets, JavaScript, font, geometry, outline width/style/offset and other scene
links. Override only this homepage card CTA's focus outline color with the
existing `--proto-teal-600` token, through WindPress. The selector must outrank
the later saved LC rule, and work without the script's `body[data-page]` flag.
No PHP presentation, inline CSS, second pipeline or new interaction is needed.

Reuse the owned 9410 instance and its verified recovery baseline. Save the
current small WindPress entry and new-volume absence before installation; install
only the native WindPress volume and rebuild using its official Generate UI.
Do not run full present. Rollback removes the new volume and restores the exact
previous entry, then regenerates the official cache.

Acceptance: EN/DE × 1440/390/320 actual native keyboard focus with visible teal
ring and the original two-pixel width/four-pixel offset; no clipping, text/CTA
geometry change or lost hover feedback; actual Enter reaches localized contact
with offer intent, no submit/POST. Inspect native screenshots and platform fonts.
Recheck photo-background scene links retain their existing white ring, plus a
no-script card focus check. Source dual review, CI and deployed readback remain
separate from these local checks. The independently discovered German source
context defect remains active in the full-site goal and is not fixed by this CSS.
