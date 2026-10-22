# Project workspace copy: intake and saving

2026-10-23. Local implementation review, not a complete tool or release approval.
Runtime sources are apps/planner/src and the native linker-tools PO/MO/JSON.

## Draft and adversarial pass

The new dimension is a persistent engineering project: available facts, units,
declared sources, edit state and confirmed revisions. The Linker encyclopedia's
tool/engineering and trade terminology lanes were read; product categories,
manufacturer claims, grid qualification and sales promises are not added here.

The first draft used “A place for your next design”; the review rejected the
unnecessary future framing. The final label is “Project workspace”. A generic
“within the field limits” error was also rejected: the displayed error now
states the actual latitude/longitude range or nonnegative lower bound.

The numeric review found that accepting comma and point interchangeably could
silently change the magnitude of an EN or DE grouping separator. The final
control explicitly states the locale's decimal separator and disallows grouping.
Separate fixtures cover EN 1,000 and DE 1.000 refusal, 1.5/1,5, zero and null.
This corrects behavior as well as wording.

The local browser pass also rejected using a generic “newer revision” message
for a recovery after session change: the server revision can be unchanged.
The final status says that open changes and the saved revision have both been
kept, with a field comparison before either explicit choice. Number format
help is a description rather than part of the accessible input name. An
invalid raw numeric edit blocks leaving silently, and Escape restores its
last valid value. A failed local recovery write blocks leaving with unsaved
data while still allowing an actual server save.

New DE recovery/comparison messages use Version, Entwurf, Eingabe and Sie,
consistent with the existing native catalogue. Free-text project facts are
not translated as enum labels or country names. Saved timestamps shown for
local recovery choices are browser metadata, not engineering provenance.

EN is the source. New DE text was written for the same actions and facts,
with Sie-compatible customer wording; existing native German terms are retained.
Project/revision labels use the native term in the existing catalogue where
present. Save status distinguishes local edits, in-flight work, unknown
acknowledgement and confirmed server revision. “Saved” is never a fetch toast.
Annual consumption is labelled an initial estimate, with interval data required
for peak and battery analysis; no annual number is presented as a measured profile.

## Pre-delivery checks

- [x] Encyclopedia loaded; one dimension is project data and save state.
- [x] Hard Stops 1–9 applied to every visible line.
- [x] Actor: no copy assigning customer homework; controls name actual actions.
- [x] Future: the invented next-project framing was removed.
- [x] Weight: no small workflow action presented as the whole Linker service.
- [x] Duration: no unsupported continuing-service claim.
- [x] No slogan formulas or defensive category negation.
- [x] No banned brand on these surfaces; no equipment or grid release claimed.
- [x] No testimonials, quotes, fabricated performance or response-time promises.

This is the implementer's adversarial editorial pass. Independent Spec and
Standards review of the complete app diff, EN/DE browser rendering and actual
state transitions remain mandatory before release. Roof/layout and system
planning copy describes the approved complete workbench; the current local
intake increment is not claimed to have delivered those remaining capabilities.
