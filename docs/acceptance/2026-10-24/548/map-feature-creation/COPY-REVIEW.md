# Roof-feature creation: independent adversarial copy review

Date: 2026-10-24. Scope: the 27 fixed English messages in `COPY-DRAFT.json`, SHA256 `810cf1bc78cf733b17002dd2023427a1f2a6fcc61406026afa75c029fb8d0e8a`, read before review and verified unchanged afterwards. Context was base HEAD `81524ca90795f4f26e80c59e5a63c63e23bd80c9` with the implementing agent's feature-creation changes in progress. No implementation pin or acceptance is asserted here.

`COPY-FINAL.json` contains every original once, in frozen order, as `{en, final_en, final_de}`. Four new English messages change; twenty-three retain their original English. Thirteen exact existing English/approved German pairs are preserved. Fourteen exact catalogue pairs receive independently composed German, including four short terms whose established German vocabulary already appears in longer approved messages. Final JSON SHA256: `cc2ed09d028f1db3dbad44e7f881427a1bacd68896737d8ab495eec9c5b376c4`.

## Dimension and scope

The added dimension is **drawing a new opening, obstacle or keep-out area on an existing roof face, then adding it to the project draft**. These are objects within the current Solution Configurator, not another named tool. German uses the existing generic `Objekt` terminology for the umbrella and the established `Dachfläche`, `Dachöffnung`, `Hindernis` and `Sperrfläche` for actual choices. No new product category or branded vocabulary is introduced.

Read `docs/specs/548-map-feature-creation.md` and the current `MapFeatureSelector`, `MapFeatureProperties`, `MapSourceDetails`, `MapDrawingWorkspace`, `mapDrawingLabels` and `mapFeatureDraft`. Existing shared consumers in `ShapeForm`, `NumberField`, `GeometryForm`, `MapRoofProperties`, `SourceForm` and geometry-import controls were inspected. Approved German reuse was checked against the existing compiled catalogue; corresponding established terms were checked in the PO. This is a wording review of the specified UI, not a correctness review or a browser/engineering/production acceptance.

## Draft, opposition and final wording

Numbers refer to the frozen one-based entry order. The JSON carries the exact complete EN/DE result.

| Entry | Draft | Opposition | Final English / independently composed German |
| --- | --- | --- | --- |
| 6 | Draw roof feature | The shared heading/button omits the natural article. Keep the action and its scope; do not replace it with a new tool name. | **Draw a roof feature** / **Objekt auf der Dachfläche zeichnen** |
| 10 | Feature to add | The selector chooses a type, rather than a saved object or instance. Name that distinction. | **Feature type** / **Objekttyp** |
| 22 | Select a feature | Match the type selector's final label so the placeholder does not suggest choosing an existing object. | **Select a feature type** / **Objekttyp auswählen** |
| 26 | The outline uses the selected roof plane. Review its source and feature properties before applying. | “Its source” has an unclear antecedent and “applying” leaves the destination implicit. Name the source details and project draft. The instruction concerns the actual form being operated. | **The outline lies in the selected roof plane. Check the source details and feature properties before adding it to the project draft.** / **Der Umriss liegt in der gewählten Dachebene. Prüfen Sie die Quellenangaben und Objekteigenschaften, bevor Sie das Objekt zum Projektentwurf hinzufügen.** |

The remaining new exact catalogue pairs were challenged and retained in English:

| Entries | Opposition considered and final decision |
| --- | --- |
| 1, 2, 9 | An umbrella “feature” could obscure the object type if presented alone. The adjacent roof/type selectors and actual options supply that context. Keep these modest action/property labels. German uses `Objekt auf der Dachfläche hinzufügen`, `Prüfen und Objekt hinzufügen` and `Objekteigenschaften`, rather than a literal or promotional term for a software feature. |
| 8 | “Added” could imply a server save. The draft sentence explicitly says **project draft** and separately names **Save project**. Preserve it. German: `Das Objekt wurde dem Projektentwurf hinzugefügt. Mit „Projekt speichern“ wird es im Projekt gespeichert.` `Projektentwurf` does not rename the commercial `Lösungsentwurf`. |
| 12 | A checkbox must not make Linker the party that verified measurements or rights. Retain the first-person customer declaration. German: `Ich habe geprüft, dass die erfasste Quelle und die Nutzungsberechtigungen dieses neue Objekt abdecken.` It grants no additional export right. |
| 13, 15, 19, 20 | These short exact msgids are absent from the approved MO, but their nouns are already established throughout the tool. Preserve EN and use `Sperrfläche`, `Hindernis`, `Dachfläche`, `Dachöffnung`; do not invent alternatives. |
| 24 | “Kept” must not promise a successful server or browser save after an input error. This message reports retained current entries; it makes no persistence claim. Keep EN. German: `Einige Objekt- oder Quellenangaben fehlen oder sind ungültig. Ihre Eingaben bleiben erhalten.` |

## Exact shared-pair reuse

Entries **3, 4, 5, 7, 11, 14, 16, 17, 18, 21, 23, 25 and 27** retain both their exact English and approved German. They cover continuing corners, decimal conventions, extrusion direction, the positive-height condition, object name, obstacle height, roof-normal/vertical choices, the reason field, roof/direction selection and source reference. These messages already serve other forms. Rewriting them here would silently affect those consumers, so this increment does not alter them.

The height label's metre unit is rendered beside the shared message. The decimal helper follows the drawing's retained numeric locale. Neither requires a new number, tolerance or unit convention. `Extrusionsrichtung` remains the established field term, with the two concrete direction choices providing its meaning.

## Source-to-claim check

| Claim or instruction | Local basis | Wording boundary |
| --- | --- | --- |
| Roof/type selection and drawing | Feature spec; current selector and type labels | Only the three specified object types on a chosen existing roof. No claim of automatic detection. |
| Outline in the roof plane | Feature spec; current geographic-to-parent-plane command path | A geometric input convention, not a measured or newly fitted roof. |
| Source reference and customer declaration | Feature spec; existing source selector, inherited roof source for openings, and recorded-source display | No new verified accuracy, licence, unrestricted export or Linker attestation. The existing source-limit helper remains unchanged. |
| Height in metres along an explicit direction; reason | Feature spec; current height/axis/reason controls and validation requirements | The positive-height rule and available axes are model inputs. No default height, shading, structural or country approval is asserted. |
| Check/add and result status | Feature spec; explicit submission and protected project-draft result | Addition to the shared draft is distinct from Save project and server acknowledgement. No bankable, engineering or product-selection outcome is claimed. |
| Correction and retained entries | Feature spec; field feedback and existing journal workflow | Entries remain available for correction; text does not promise a successful remote write. |

No external factual claims, third-party sentences, network research, quotations or testimonials were introduced.

## Applied copy checklist

Read the complete [linker-copywriting skill](/Users/chesterjohn/.agents/skills/linker-copywriting/SKILL.md), its `industry-and-linker-encyclopedia.md`, mandatory `anti-patterns.md` and `positive-examples.md`, plus the complete [humanizer skill](/Users/chesterjohn/.agents/skills/humanizer/SKILL.md). Active project instructions/specification supersede the encyclopedia's historic tool/commerce naming and scope. Benchmark sentences supplied no claims for this increment.

- [x] Encyclopedia loaded: one new editing dimension; existing project and object vocabulary retained.
- [x] Hard Stops 1–9 checked on every message: no borrowed credibility, proof inventory, category denial, reassurance intensifier, invented service/time, helpdesk initiation or repair-shop marketing.
- [x] Actor: no marketing body homework. The explicit task permits actual editing instructions; selector placeholders, continued drawing and checking this form describe those controls. The permission checkbox remains the customer's first-person declaration.
- [x] Future: no invented next job, motive or development trajectory.
- [x] Weight: this subordinate map operation is not described as the entire system or as engineering approval.
- [x] Duration: no permanent availability, ongoing service or guaranteed retention claim.
- [x] No slogan formulas, forced advertising tricolons, false contrasts or artificial labels. The three type options are the actual specified options.
- [x] No banned brand, fabricated testimonial or sourced quotation. Quote gate satisfied by writing no quotation.
- [x] Formal German composed for the UI, using Sie for the form instruction and Ich for the declaration. Exact approved shared German preserved.
- [x] Humanizer pass: plain verbs, natural labels, no em/en dashes, inflated significance, synonym cycling, chatbot residue or invented fact. Necessary source and numeric scope survive.
- [x] Pre-flight relevance: each line identifies an input/action, explains its geometric meaning, reports a state or enables correction. No marketing was added to the field form.
- [x] Frozen input/output validation: 27 unique originals, same order; 4 EN changes; 13 exact approved pairs unchanged; all final DE present; original draft hash unchanged.

Only `COPY-FINAL.json` and this report were written. Application, translation generation, independent code review and native EN/DE rendering remain the implementing agent's work. Copy-review ownership is finished and released.
