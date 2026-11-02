# Genie knowledge preparation for the 217 affected Woo associations

## November 2 remaining 19: original and customer-title review

Read-only Woo manifest returned source `f797916bbe1f5b3177cf5198b832ef5a9a90dc5b866b86e030c63d0ac38d1003`. The current Genie index selector points to `20261101T200109Z-826802000`, whose SQLite metadata gives epoch 60, the same source and `preparation_complete=false`. A fresh private `/knowledge/loaded` call failed; the selector and historical ACK are not a fresh serving-process readback. All 19 original associations below still exist in the current Woo manifest. The diagnostic concerns sufficient evidence for the exact product and document purpose; it does not mean all original PDFs are absent.

| Associations | Finding and next evidence |
|---|---|
| SAJ HS3 IDs 1185, 1186, 1187, 2198, 2199 × declaration `43d6efd869b4` (5) | The original names W and G models separately and `X=1…8`; the existing conditional, nameplate-dependent passages remain available. The composite W/G listing does not itself identify which version was delivered. Obtain the actual equipment nameplate and module count; do not replace the conditional declaration with an unconditional model claim. |
| The same five HS3 IDs × German datasheet `e00f9645d187` (5) | The original gives P1–P5 and a 5–12 kW family table; the five product labels use the unspecified composite W/G-PX. A concrete device and module count, plus a manufacturer sheet explicitly covering that designation, are needed for a model-specific numeric answer. The already obtained SAJ quick guide `af04ae86ea3c…` names the (5K–12K)-T2-(W,G)-(B,P)X family and can support guide scope, but it does not by itself establish the specific German sheet's model-column values. |
| GoodWe HCA ID 3557 × certificate `8158c2cc2ff1` (1) | Certificate RED_1003 p1 prints `GW11KHCA- 20`, while Woo has `GW11K-HCA-20`. Request the certifier or GoodWe's corrected model listing or written cross-reference; do not silently insert the missing hyphen in the certificate. |
| SAJ eSolar ID 3573 × declaration `9bc6ae93800c` (1) | PDF extraction gives `AlO3`; the actual p1 glyph is a straight vertical stroke and does not by itself distinguish lowercase l from uppercase I. The site calls it AIO3. Preserve the original and association; ask SAJ for a machine-readable corrected declaration or explicit model correspondence. |
| GoodWe LCD cabinet ID 1957 × EN/DE battery compatibility `8951dd1d8a64`, `ea081f6f6fb2` (2) | The exact `GW208.9-BAT-LCD-G10` is absent from these matrices; the LC and other LCD entries do not prove this specific combination. Request an exact-model current matrix or manufacturer compatibility statement with inverter and applicable limits. |
| SAJ CB2 IDs 4103, 4104, 4105, 4106 × quick guide `a70cb4c39824` (4) | Page 1 calls the guide `CB2-(57.3K-100.3K)-HV5`; Woo's EN/DE titles assert separately that it covers the four non-K models. K-to-non-K equivalence is not established. The original and all four associations stay. The candidate below removes only the unsupported title assertion and repeats the original designation; request an explicit SAJ model cross-reference or corrected guide before asserting applicability. |
| SAJ BU3 ID 2093 × warranty `be0569b4602a` (1) | Its p2 lists `BU3-5.0-TV2(-PRO)` as a battery in an HS3 BESS performance-warranty table. That does not establish separate standalone-BU3 policy terms. Request SAJ's applicable standalone battery warranty or written confirmation of scope and conditions. |

The two CHS2 datasheets also associated with those CB2 products are **not** an established wrong pairing: their actual EN and DE originals each list all four CB2 models in the battery table on pp3–4. Their associations remain. The separately verified SGS certificate/annex boundary is unchanged; no absence of a publicly accessible annex is inferred from the failed lookup.

### Draft CB2 title correction and receipt

`tools/migrate/548-cb2-guide-titles.py` and its PHP companion prepare one locked, receipt-backed change to the four products' English, German and saved English translation-baseline ACF rows, plus one additive German library-title mapping. They preserve attachment 6337, original SHA `a70cb4c39824185fb9f570a59f4966c54ec94a33c870d00c7ccd756393321dac`, URLs, all unrelated rows and existing translations. The exact source-literal replacement is **SAJ CB2-(57.3K-100.3K)-HV5 quick installation guide (English)** / **SAJ CB2-(57.3K-100.3K)-HV5 Kurzanleitung zur Installation (englisches Original)**. Neither says the original applies to a non-K model. The migration checks the original, all four identities and current associations, refuses document-revision bindings to installation facts, package contents or compatibility claims, and records whole-field before/after bytes and SHA-256 in a private receipt. A partial result must be inspected against that same receipt; apply/rollback use compare-and-swap and refuse conflicting edits.

The read-only production preview recorded 12 metadata rows and the option transition in `/private/tmp/548-remaining-source-evidence/cb2-title-preview.receipt.json` (0600, owner this task, 341,994 bytes, SHA-256 `18ebf93d1e6f305de3b20b95f8bb0035d2343b42316eb58cb08fb72af6a4d491`). Its individual before/after field hashes and original values are in that receipt; it is a **preview**, not an applied change. Retain this one receipt for review and the coordinated data window; discard only after verified completion or deliberate cancellation. The PHP in-memory native fixture covers preview, a post-preview engineering binding, failed binding query, interrupted apply and resume, unrelated concurrent edit, verify, blocked rollback, successful rollback and changed PDF. Ruff and PHP syntax checks passed. Local p548 preview and real product-page, library and Genie consumer checks, independent review, and any later production backup/write/republication/readback remain outstanding.

These title changes can alter product/document and Woo source revisions and the knowledge index's title-dependent chunks. Engine and Genie runtime source do not change. A production data window must use the existing full recovery point and the same receipt, then run the native paired publication guard to preserve the existing 598 authorized associations and the conditional HS3/warranty boundaries before treating the new source as loaded. Roll back the Woo fields and option using the same receipt together with the matching knowledge generation; do not roll back only one side.

## November 2 production readback

The serving Genie index at epoch 60 contains 18,899 passages from 142 original PDFs. The preactivation comparison preserved 598 usable product–document associations across 85 ready products. Nineteen associations still lack the evidence needed for that product and document purpose. Woo's ready acknowledgement and Genie's loaded-index readback agreed. See the PR842 paired-publication entry in [the production acceptance record](INDEX.md).

On the public site, Genie answered the German GW11K-HCA warranty question with the two-year duration and its start conditions. For the English ETR installation question, it distinguished securing the inverter to the bracket (M6, 3–5 N·m) from fixing the bracket to the wall. The epoch 56 table below preserves the first recovery batch and the original failed answers.

## November 1 publication at epoch 56

The baseline was Woo source `c849a2b51dbea4bdc3e2dcc4269be23834175f3395e4af08198a40c90af9d74e`, index `20261101T105022Z-660599000`, epoch 54. Its 217 incomplete product/document associations referred to 55 distinct originals and 73 products within a corpus of 142 PDF originals.

The final native build and preactivation consumer comparison recovered usable passages for 188 of those same associations. Three old HCA warranty associations were replaced by three prepared associations to a verified newer manufacturer original. The remaining 26 associations still lack sufficient evidence. All 85 previously ready products and all 391 previously usable product/document pairs remained available. The new index has 592 usable product/document pairs across the whole corpus. Two older passage projections for products 6513 and 6517 contained a truncated MPPT current value. Those rows were omitted while other proven data from the same sheet remained available.

The actual API and judge now run `20261101T163031000000Z-c56e38fa`. The serving index is `20261101T164225Z-190141000`, SHA-256 `2cc40c72e1a67d0e106f38befa5bce00384be4ca84316998df7d6c8afc2adba0`. Native ready ACK and authenticated loaded readback agree on epoch 56, source `4c0ba90ebc0e03fcacc6209c11072c2257005f3227f05a9fc1136e5bb2ee4400`, recipe `5dc1c22cc0798fc7fbf474f66eb2e33bc37a6005d4678b03016cd79fc741385a` and serving identity `504c9e40dab4129ec65db3dee4ac9a6032a08c6cc44f6422a26e8686dc5e954b`. No lease or paired-release journal remains. The restored 900-second worker completed its first scheduled startup poll with exit 0 and left epoch 56 unchanged.

The final build reused 142 cached originals and all 18,893 passage vectors, with zero provider calls during generation. Earlier preparation had supplied the genuinely missing vectors through the approved OpenRouter route. The final preactivation checks used the old and new native runtime authorization paths, exact product/document associations, and HS3 searches. Five HS3 data sheets and five conditional certificate searches passed together after the anchor namespace repair.

| Document purpose | Same association recovered | Still incomplete | Replaced by new original | Baseline total |
|---|---:|---:|---:|---:|
| certificate | 71 | 7 | 0 | 78 |
| compatibility | 34 | 4 | 0 | 38 |
| datasheet | 10 | 5 | 0 | 15 |
| manual | 73 | 4 | 0 | 77 |
| other | 0 | 6 | 3 | 9 |
| Total | 188 | 26 | 3 | 217 |

## Physical original documents and the HCA replacement

The physical-original additions recovered eight installation-guide associations and twenty-one compatibility associations beyond the first candidate's 159. Each condition and model-axis inference retains its source references. For five HS3 models, the DoC lists the individual W and G designations. The verified model-axis table on data sheet page 2 and manufacturer manual page 18 explain how to distinguish them. A conditional answer links all three documents and asks the customer to read the nameplate. The combined W/G model remains incomplete as a certificate association.

GoodWe's EU EV charger warranty Rev. 1.2 names all three currently listed HCA-20 models. For Europe excluding the UK it specifies two years from the earlier of first installation and six months after production. The full policy contains regional, reporting and exclusion conditions. Source PDF SHA-256 is `88a8a5bd9e70bc398fe990069272526c660c1731103ff113e53f93f7fd789307`. Woo attachment 8474 is now linked to products 3557, 3586 and 3587. All six ordinary EN/DE product pages displayed the correct localized title and hosted link after native post-cache purge. The hosted PDF returned 200 with 491,728 bytes and the verified hash. The retired public URL returned 410 while its original attachment was retained. A native German download click opened the actual three-page original. [Manufacturer original](https://en.goodwe.com/Public/Uploads/uploadfile/files/20261014/GOODWELimitedWarrantyforEVChargerforEURev_1_220260917.pdf)

## Customer question readback

The initial controlled DE Genie tab failed conversation creation and ordinary HCA Send with Cloudflare code 300030, preserving the question and reporting no dispatch. Through 16:51:43 UTC, server-side inspection found zero completed turns and zero outstanding starts since 16:35 UTC. A foreground reload restored history but the controlled retry again failed. The read-only browser diagnostic API also reported a paused document response.

Closing that controlled test tab and opening a fresh tab through native Chrome UI changed the result without changing site settings, keys or protection. Native New conversation succeeded. Native Send visibly passed the real Cloudflare challenge and produced a model response. This is an observed difference in control mode, not proof of a specific provider-internal cause.

The actual German question asked the warranty duration and starting date for GW11K-HCA-20 in Germany. The answer cited the correct new hosted warranty on pages 1, 3 and 2 but gave a generic introduction and thirteen English condition quotations. It omitted the two-year duration and failed the German direct-answer requirement. Inspection confined to this test turn found thirteen correct source hits, including the complete German protected warranty answer. Both model attempts failed grounding; the documents fallback omitted the protected warranty answer and hydration appended the source conditions. This is an open consumer defect under active repair. The screen evidence is `genie-hca-de-fallback.png` in this acceptance directory. English ETR readback also failed the action-specific answer requirement. A fresh native Chrome conversation asked for the torque fixing GW80K-ETR-G10 to its mounting plate. The answer cited the original quick guide page 1 but returned M10 14–24 N·m from wall-mounting figure ETR12510INT0002. Physical review of that same original confirms inverter-to-plate figure ETR12510INT0004 step 3 specifies M6 3–5 N·m. The correct figure was absent from the production retrieved passages and grounding accepted a sourced number for the wrong fastening action. Both the missing figure evidence and action matching are under repair. `genie-etr-en-mounting.jpg` retains the actual answer. Both task-owned production question tabs are closed, and the existing customer revision-5 tabs remain open.

## Product and original document

| Purpose | Original SHA-256 prefix | Woo ID | Published model | Candidate finding |
|---|---|---:|---|---|
| certificate | `000592098663` | 1955 | GW112.6-BAT-AC-G10 | Usable passage in the loaded epoch 56 index. |
| certificate | `07f4ab631389` | 2394 | GM330 | Usable passage in the loaded epoch 56 index. |
| certificate | `07f4ab631389` | 2397 | GMK330 | Usable passage in the loaded epoch 56 index. |
| certificate | `0d33ea23ff2d` | 1956 | GW208.9-BAT-LC-G10 | Usable passage in the loaded epoch 56 index. |
| certificate | `0d33ea23ff2d` | 1957 | GW208.9-BAT-LCD-G10 | Usable passage in the loaded epoch 56 index. |
| certificate | `0d33ea23ff2d` | 1958 | GW261.2-BAT-LCD-G10 | Usable passage in the loaded epoch 56 index. |
| certificate | `43d6efd869b4` | 1185 | HS3-12K-T2-W/G-PX | Conditional evidence for the separate W and G variants, using declaration p1, data sheet p2 and manual p18. Combined-model certificate remains incomplete. |
| certificate | `43d6efd869b4` | 1186 | HS3-6K-T2-W/G-PX | Conditional evidence for the separate W and G variants, using declaration p1, data sheet p2 and manual p18. Combined-model certificate remains incomplete. |
| certificate | `43d6efd869b4` | 1187 | HS3-8K-T2-W/G-PX | Conditional evidence for the separate W and G variants, using declaration p1, data sheet p2 and manual p18. Combined-model certificate remains incomplete. |
| certificate | `43d6efd869b4` | 2198 | HS3-5K-T2-W/G-PX | Conditional evidence for the separate W and G variants, using declaration p1, data sheet p2 and manual p18. Combined-model certificate remains incomplete. |
| certificate | `43d6efd869b4` | 2199 | HS3-10K-T2-W/G-PX | Conditional evidence for the separate W and G variants, using declaration p1, data sheet p2 and manual p18. Combined-model certificate remains incomplete. |
| certificate | `576232ede954` | 3557 | GW11K-HCA-20 | Usable passage in the loaded epoch 56 index. |
| certificate | `576232ede954` | 3586 | GW7K-HCA-20 | Usable passage in the loaded epoch 56 index. |
| certificate | `576232ede954` | 3587 | GW22K-HCA-20 | Usable passage in the loaded epoch 56 index. |
| certificate | `5e9f4b467d5d` | 3595 | GW125K-ETR-G10 | Usable passage in the loaded epoch 56 index. |
| certificate | `5e9f4b467d5d` | 6507 | GW80K-ETR-G10 | Usable passage in the loaded epoch 56 index. |
| certificate | `5e9f4b467d5d` | 6508 | GW99.99K-ETR-G10 | Usable passage in the loaded epoch 56 index. |
| certificate | `5e9f4b467d5d` | 6509 | GW100K-ETR-G10 | Usable passage in the loaded epoch 56 index. |
| certificate | `5e9f4b467d5d` | 6510 | GW110K-ETR-G10 | Usable passage in the loaded epoch 56 index. |
| certificate | `5e9f4b467d5d` | 6511 | GW124.99K-ETR-G10 | Usable passage in the loaded epoch 56 index. |
| certificate | `6820813acbec` | 3595 | GW125K-ETR-G10 | Usable passage in the loaded epoch 56 index. |
| certificate | `6820813acbec` | 6507 | GW80K-ETR-G10 | Usable passage in the loaded epoch 56 index. |
| certificate | `6820813acbec` | 6508 | GW99.99K-ETR-G10 | Usable passage in the loaded epoch 56 index. |
| certificate | `6820813acbec` | 6509 | GW100K-ETR-G10 | Usable passage in the loaded epoch 56 index. |
| certificate | `6820813acbec` | 6510 | GW110K-ETR-G10 | Usable passage in the loaded epoch 56 index. |
| certificate | `6820813acbec` | 6511 | GW124.99K-ETR-G10 | Usable passage in the loaded epoch 56 index. |
| certificate | `6a45702bfe4a` | 1832 | B2-5.0-HV1 | Usable passage in the loaded epoch 56 index. |
| certificate | `6a45702bfe4a` | 2067 | B2-10.0-HV1 | Usable passage in the loaded epoch 56 index. |
| certificate | `6a45702bfe4a` | 2068 | B2-15.0-HV1 | Usable passage in the loaded epoch 56 index. |
| certificate | `6a45702bfe4a` | 2069 | B2-20.0-HV1 | Usable passage in the loaded epoch 56 index. |
| certificate | `6a45702bfe4a` | 2070 | B2-25.0-HV1 | Usable passage in the loaded epoch 56 index. |
| certificate | `6a45702bfe4a` | 2090 | BU2-5.0-HV1 | Usable passage in the loaded epoch 56 index. |
| certificate | `6cd7792a5287` | 1954 | GW61.4-BAT-AC-G10 | Usable passage in the loaded epoch 56 index. |
| certificate | `6cd7792a5287` | 1955 | GW112.6-BAT-AC-G10 | Usable passage in the loaded epoch 56 index. |
| certificate | `75a3a83432a9` | 1182 | HS2-10K-T2-X | Usable passage in the loaded epoch 56 index. |
| certificate | `75a3a83432a9` | 1183 | HS2-6K-T2-X | Usable passage in the loaded epoch 56 index. |
| certificate | `75a3a83432a9` | 1184 | HS2-8K-T2-X | Usable passage in the loaded epoch 56 index. |
| certificate | `75a3a83432a9` | 4109 | HS2-5K-T2-X | Usable passage in the loaded epoch 56 index. |
| certificate | `8158c2cc2ff1` | 3557 | GW11K-HCA-20 | Certificate lists GW11KHCA- 20. Woo lists a different hyphenated model. |
| certificate | `8158c2cc2ff1` | 3586 | GW7K-HCA-20 | Usable passage in the loaded epoch 56 index. |
| certificate | `8158c2cc2ff1` | 3587 | GW22K-HCA-20 | Usable passage in the loaded epoch 56 index. |
| certificate | `9881d06dabba` | 1179 | H2-25K-T3 | Usable passage in the loaded epoch 56 index. |
| certificate | `9881d06dabba` | 1181 | H2-30K-T3-DE | Usable passage in the loaded epoch 56 index. |
| certificate | `9881d06dabba` | 2063 | H2-15K-T3 | Usable passage in the loaded epoch 56 index. |
| certificate | `9881d06dabba` | 2064 | H2-20K-T3 | Usable passage in the loaded epoch 56 index. |
| certificate | `9881d06dabba` | 4107 | H2-10K-T3 | Usable passage in the loaded epoch 56 index. |
| certificate | `9881d06dabba` | 4108 | H2-12K-T3 | Usable passage in the loaded epoch 56 index. |
| certificate | `9bc6ae93800c` | 3573 | eSolar AIO3 | Certificate lists AlO3. The published product is AIO3. |
| certificate | `9cb10f8699f6` | 1832 | B2-5.0-HV1 | Usable passage in the loaded epoch 56 index. |
| certificate | `9cb10f8699f6` | 2067 | B2-10.0-HV1 | Usable passage in the loaded epoch 56 index. |
| certificate | `9cb10f8699f6` | 2068 | B2-15.0-HV1 | Usable passage in the loaded epoch 56 index. |
| certificate | `9cb10f8699f6` | 2069 | B2-20.0-HV1 | Usable passage in the loaded epoch 56 index. |
| certificate | `9cb10f8699f6` | 2070 | B2-25.0-HV1 | Usable passage in the loaded epoch 56 index. |
| certificate | `9cb10f8699f6` | 2092 | BC2-HV1 | Usable passage in the loaded epoch 56 index. |
| certificate | `9ec440d37e80` | 3595 | GW125K-ETR-G10 | Usable passage in the loaded epoch 56 index. |
| certificate | `9ec440d37e80` | 6507 | GW80K-ETR-G10 | Usable passage in the loaded epoch 56 index. |
| certificate | `9ec440d37e80` | 6508 | GW99.99K-ETR-G10 | Usable passage in the loaded epoch 56 index. |
| certificate | `9ec440d37e80` | 6509 | GW100K-ETR-G10 | Usable passage in the loaded epoch 56 index. |
| certificate | `9ec440d37e80` | 6510 | GW110K-ETR-G10 | Usable passage in the loaded epoch 56 index. |
| certificate | `9ec440d37e80` | 6511 | GW124.99K-ETR-G10 | Usable passage in the loaded epoch 56 index. |
| certificate | `c0aa75c957e2` | 2409 | SEC3000C | Usable passage in the loaded epoch 56 index. |
| certificate | `ca7f328ac99c` | 1178 | ATS1-T63-A | Usable passage in the loaded epoch 56 index. |
| certificate | `d110c7ee8cfd` | 2409 | SEC3000C | Usable passage in the loaded epoch 56 index. |
| certificate | `d5b4a361d712` | 4103 | CB2-57.3-HV5 | Usable passage in the loaded epoch 56 index. |
| certificate | `d5b4a361d712` | 4104 | CB2-71.6-HV5 | Usable passage in the loaded epoch 56 index. |
| certificate | `d5b4a361d712` | 4105 | CB2-85.9-HV5 | Usable passage in the loaded epoch 56 index. |
| certificate | `d5b4a361d712` | 4106 | CB2-100.3-HV5 | Usable passage in the loaded epoch 56 index. |
| certificate | `d80f9722131d` | 6321 | GW125/261-ESA-LCN-G10 | Usable passage in the loaded epoch 56 index. |
| certificate | `da4d0f336bb0` | 1946 | GW80K-ET-G10 | Usable passage in the loaded epoch 56 index. |
| certificate | `da4d0f336bb0` | 1947 | GW99.99K-ET-G10 | Usable passage in the loaded epoch 56 index. |
| certificate | `da4d0f336bb0` | 1948 | GW100K-ET-G10 | Usable passage in the loaded epoch 56 index. |
| certificate | `da4d0f336bb0` | 6506 | GW75K-ET-G10 | Usable passage in the loaded epoch 56 index. |
| certificate | `ecd12d114411` | 2093 | BU3-5.0-TV2-PRO | Usable passage in the loaded epoch 56 index. |
| certificate | `f43c5fe00fda` | 3557 | GW11K-HCA-20 | Usable passage in the loaded epoch 56 index. |
| certificate | `f43c5fe00fda` | 3586 | GW7K-HCA-20 | Usable passage in the loaded epoch 56 index. |
| certificate | `f43c5fe00fda` | 3587 | GW22K-HCA-20 | Usable passage in the loaded epoch 56 index. |
| certificate | `f4de612e4a7c` | 6521 | GW5.1-BAT-D-G21 | Usable passage in the loaded epoch 56 index. |
| certificate | `f4de612e4a7c` | 6522 | GW8.3-BAT-D-G21 | Usable passage in the loaded epoch 56 index. |
| compatibility | `5e40da8282b1` | 1946 | GW80K-ET-G10 | Usable passage in the loaded epoch 56 index. |
| compatibility | `5e40da8282b1` | 1947 | GW99.99K-ET-G10 | Usable passage in the loaded epoch 56 index. |
| compatibility | `5e40da8282b1` | 1948 | GW100K-ET-G10 | Usable passage in the loaded epoch 56 index. |
| compatibility | `5e40da8282b1` | 1954 | GW61.4-BAT-AC-G10 | Usable passage in the loaded epoch 56 index. |
| compatibility | `5e40da8282b1` | 1955 | GW112.6-BAT-AC-G10 | Usable passage in the loaded epoch 56 index. |
| compatibility | `6f33b8361fe2` | 2394 | GM330 | Loaded index binds G10 to GM330 and SEC3000C, with the full p7 single-unit condition and the p9 controller, firmware and parallel-operation restrictions. |
| compatibility | `6f33b8361fe2` | 2397 | GMK330 | Parsed rows mix G10/G11 or lose the required version footnote, or the exact device pairing cannot be established. |
| compatibility | `6f33b8361fe2` | 2409 | SEC3000C | Loaded index binds G10 to GM330 and SEC3000C, with the full p7 single-unit condition and the p9 controller, firmware and parallel-operation restrictions. |
| compatibility | `6f33b8361fe2` | 2415 | EzManager3000 | Parsed rows mix G10/G11 or lose the required version footnote, or the exact device pairing cannot be established. |
| compatibility | `6f33b8361fe2` | 6321 | GW125/261-ESA-LCN-G10 | Loaded index binds G10 to GM330 and SEC3000C, with the full p7 single-unit condition and the p9 controller, firmware and parallel-operation restrictions. |
| compatibility | `8951dd1d8a64` | 1946 | GW80K-ET-G10 | Loaded index binds the p6 compatibility matrix and the separate manufacturer model-axis data sheet. The power limit stays with the answer. |
| compatibility | `8951dd1d8a64` | 1947 | GW99.99K-ET-G10 | Loaded index binds the p6 compatibility matrix and the separate manufacturer model-axis data sheet. The power limit stays with the answer. |
| compatibility | `8951dd1d8a64` | 1948 | GW100K-ET-G10 | Loaded index binds the p6 compatibility matrix and the separate manufacturer model-axis data sheet. The power limit stays with the answer. |
| compatibility | `8951dd1d8a64` | 1954 | GW61.4-BAT-AC-G10 | Usable passage in the loaded epoch 56 index. |
| compatibility | `8951dd1d8a64` | 1955 | GW112.6-BAT-AC-G10 | Usable passage in the loaded epoch 56 index. |
| compatibility | `8951dd1d8a64` | 1956 | GW208.9-BAT-LC-G10 | Usable passage in the loaded epoch 56 index. |
| compatibility | `8951dd1d8a64` | 1957 | GW208.9-BAT-LCD-G10 | LCD variant absent from matrix. |
| compatibility | `8951dd1d8a64` | 1958 | GW261.2-BAT-LCD-G10 | Usable passage in the loaded epoch 56 index. |
| compatibility | `8951dd1d8a64` | 3595 | GW125K-ETR-G10 | Loaded index binds the p6 compatibility matrix and the separate manufacturer model-axis data sheet. The power limit stays with the answer. |
| compatibility | `8951dd1d8a64` | 6507 | GW80K-ETR-G10 | Loaded index binds the p6 compatibility matrix and the separate manufacturer model-axis data sheet. The power limit stays with the answer. |
| compatibility | `8951dd1d8a64` | 6508 | GW99.99K-ETR-G10 | Loaded index binds the p6 compatibility matrix and the separate manufacturer model-axis data sheet. The power limit stays with the answer. |
| compatibility | `8951dd1d8a64` | 6509 | GW100K-ETR-G10 | Loaded index binds the p6 compatibility matrix and the separate manufacturer model-axis data sheet. The power limit stays with the answer. |
| compatibility | `8951dd1d8a64` | 6510 | GW110K-ETR-G10 | Loaded index binds the p6 compatibility matrix and the separate manufacturer model-axis data sheet. The power limit stays with the answer. |
| compatibility | `8951dd1d8a64` | 6511 | GW124.99K-ETR-G10 | Loaded index binds the p6 compatibility matrix and the separate manufacturer model-axis data sheet. The power limit stays with the answer. |
| compatibility | `ea081f6f6fb2` | 1946 | GW80K-ET-G10 | Loaded index binds the p6 compatibility matrix and the separate manufacturer model-axis data sheet. The power limit stays with the answer. |
| compatibility | `ea081f6f6fb2` | 1947 | GW99.99K-ET-G10 | Loaded index binds the p6 compatibility matrix and the separate manufacturer model-axis data sheet. The power limit stays with the answer. |
| compatibility | `ea081f6f6fb2` | 1948 | GW100K-ET-G10 | Loaded index binds the p6 compatibility matrix and the separate manufacturer model-axis data sheet. The power limit stays with the answer. |
| compatibility | `ea081f6f6fb2` | 1954 | GW61.4-BAT-AC-G10 | Usable passage in the loaded epoch 56 index. |
| compatibility | `ea081f6f6fb2` | 1955 | GW112.6-BAT-AC-G10 | Usable passage in the loaded epoch 56 index. |
| compatibility | `ea081f6f6fb2` | 1956 | GW208.9-BAT-LC-G10 | Usable passage in the loaded epoch 56 index. |
| compatibility | `ea081f6f6fb2` | 1957 | GW208.9-BAT-LCD-G10 | LCD variant absent from matrix. |
| compatibility | `ea081f6f6fb2` | 1958 | GW261.2-BAT-LCD-G10 | Usable passage in the loaded epoch 56 index. |
| compatibility | `ea081f6f6fb2` | 3595 | GW125K-ETR-G10 | Loaded index binds the p6 compatibility matrix and the separate manufacturer model-axis data sheet. The power limit stays with the answer. |
| compatibility | `ea081f6f6fb2` | 6507 | GW80K-ETR-G10 | Loaded index binds the p6 compatibility matrix and the separate manufacturer model-axis data sheet. The power limit stays with the answer. |
| compatibility | `ea081f6f6fb2` | 6508 | GW99.99K-ETR-G10 | Loaded index binds the p6 compatibility matrix and the separate manufacturer model-axis data sheet. The power limit stays with the answer. |
| compatibility | `ea081f6f6fb2` | 6509 | GW100K-ETR-G10 | Loaded index binds the p6 compatibility matrix and the separate manufacturer model-axis data sheet. The power limit stays with the answer. |
| compatibility | `ea081f6f6fb2` | 6510 | GW110K-ETR-G10 | Loaded index binds the p6 compatibility matrix and the separate manufacturer model-axis data sheet. The power limit stays with the answer. |
| compatibility | `ea081f6f6fb2` | 6511 | GW124.99K-ETR-G10 | Loaded index binds the p6 compatibility matrix and the separate manufacturer model-axis data sheet. The power limit stays with the answer. |
| datasheet | `31e691602178` | 3611 | GW6.0-BAT-D-G20 | Usable passage in the loaded epoch 56 index. |
| datasheet | `31e691602178` | 3612 | GW9.0-BAT-D-G20 | Usable passage in the loaded epoch 56 index. |
| datasheet | `31e691602178` | 6519 | GW5.1-BAT-D-G20 | Usable passage in the loaded epoch 56 index. |
| datasheet | `31e691602178` | 6520 | GW8.3-BAT-D-G20 | Usable passage in the loaded epoch 56 index. |
| datasheet | `b681fbb51b16` | 3611 | GW6.0-BAT-D-G20 | Usable passage in the loaded epoch 56 index. |
| datasheet | `b681fbb51b16` | 3612 | GW9.0-BAT-D-G20 | Usable passage in the loaded epoch 56 index. |
| datasheet | `b681fbb51b16` | 6519 | GW5.1-BAT-D-G20 | Usable passage in the loaded epoch 56 index. |
| datasheet | `b681fbb51b16` | 6520 | GW8.3-BAT-D-G20 | Usable passage in the loaded epoch 56 index. |
| datasheet | `b681fbb51b16` | 6521 | GW5.1-BAT-D-G21 | Usable passage in the loaded epoch 56 index. |
| datasheet | `b681fbb51b16` | 6522 | GW8.3-BAT-D-G21 | Usable passage in the loaded epoch 56 index. |
| datasheet | `e00f9645d187` | 1185 | HS3-12K-T2-W/G-PX | The sheet lists -P and the product is -PX. The extracted table also has displaced rows. |
| datasheet | `e00f9645d187` | 1186 | HS3-6K-T2-W/G-PX | The sheet lists -P and the product is -PX. The extracted table also has displaced rows. |
| datasheet | `e00f9645d187` | 1187 | HS3-8K-T2-W/G-PX | The sheet lists -P and the product is -PX. The extracted table also has displaced rows. |
| datasheet | `e00f9645d187` | 2198 | HS3-5K-T2-W/G-PX | The sheet lists -P and the product is -PX. The extracted table also has displaced rows. |
| datasheet | `e00f9645d187` | 2199 | HS3-10K-T2-W/G-PX | The sheet lists -P and the product is -PX. The extracted table also has displaced rows. |
| manual | `0adfb3d5e6df` | 6321 | GW125/261-ESA-LCN-G10 | Usable passage in the loaded epoch 56 index. |
| manual | `0ef4b1ccdcc4` | 6506 | GW75K-ET-G10 | Usable passage in the loaded epoch 56 index. |
| manual | `26a5052fc859` | 1946 | GW80K-ET-G10 | Usable passage in the loaded epoch 56 index. |
| manual | `26a5052fc859` | 1947 | GW99.99K-ET-G10 | Usable passage in the loaded epoch 56 index. |
| manual | `26a5052fc859` | 1948 | GW100K-ET-G10 | Usable passage in the loaded epoch 56 index. |
| manual | `29bb252c549a` | 3556 | GW10K-ETA-G20 | Usable passage in the loaded epoch 56 index. |
| manual | `29bb252c549a` | 3584 | GW12K-ETA-G20 | Usable passage in the loaded epoch 56 index. |
| manual | `29bb252c549a` | 3585 | GW15K-ETA-G20 | Usable passage in the loaded epoch 56 index. |
| manual | `29bb252c549a` | 6514 | GW9.999K-ETA-G20 | Usable passage in the loaded epoch 56 index. |
| manual | `29bb252c549a` | 6515 | GW20K-ETA-G20 | Usable passage in the loaded epoch 56 index. |
| manual | `29bb252c549a` | 6516 | GW25K-ETA-G20 | Usable passage in the loaded epoch 56 index. |
| manual | `29bb252c549a` | 6517 | GW29.999K-ETA-G20 | Usable passage in the loaded epoch 56 index. |
| manual | `29bb252c549a` | 6518 | GW30K-ETA-G20 | Usable passage in the loaded epoch 56 index. |
| manual | `307b704c87f2` | 3595 | GW125K-ETR-G10 | Candidate adds p1 clearance and wall mounting figures. Both the figure region and the exact cover model list match the original PDF. |
| manual | `307b704c87f2` | 6507 | GW80K-ETR-G10 | Candidate adds p1 clearance and wall mounting figures. Both the figure region and the exact cover model list match the original PDF. |
| manual | `307b704c87f2` | 6508 | GW99.99K-ETR-G10 | Candidate adds p1 clearance and wall mounting figures. Both the figure region and the exact cover model list match the original PDF. |
| manual | `307b704c87f2` | 6509 | GW100K-ETR-G10 | Candidate adds p1 clearance and wall mounting figures. Both the figure region and the exact cover model list match the original PDF. |
| manual | `307b704c87f2` | 6510 | GW110K-ETR-G10 | Candidate adds p1 clearance and wall mounting figures. Both the figure region and the exact cover model list match the original PDF. |
| manual | `307b704c87f2` | 6511 | GW124.99K-ETR-G10 | Candidate adds p1 clearance and wall mounting figures. Both the figure region and the exact cover model list match the original PDF. |
| manual | `363be3f64d74` | 6508 | GW99.99K-ETR-G10 | Usable passage in the loaded epoch 56 index. |
| manual | `363be3f64d74` | 6511 | GW124.99K-ETR-G10 | Usable passage in the loaded epoch 56 index. |
| manual | `4b1a5d6dc379` | 6321 | GW125/261-ESA-LCN-G10 | Usable passage in the loaded epoch 56 index. |
| manual | `4cc6c9d37afa` | 2281 | DTSU666 | Usable passage in the loaded epoch 56 index. |
| manual | `50bdd49b7be0` | 3595 | GW125K-ETR-G10 | Usable passage in the loaded epoch 56 index. |
| manual | `50bdd49b7be0` | 6507 | GW80K-ETR-G10 | Usable passage in the loaded epoch 56 index. |
| manual | `50bdd49b7be0` | 6508 | GW99.99K-ETR-G10 | Usable passage in the loaded epoch 56 index. |
| manual | `50bdd49b7be0` | 6509 | GW100K-ETR-G10 | Usable passage in the loaded epoch 56 index. |
| manual | `50bdd49b7be0` | 6510 | GW110K-ETR-G10 | Usable passage in the loaded epoch 56 index. |
| manual | `50bdd49b7be0` | 6511 | GW124.99K-ETR-G10 | Usable passage in the loaded epoch 56 index. |
| manual | `5876178f27d0` | 6321 | GW125/261-ESA-LCN-G10 | Usable passage in the loaded epoch 56 index. |
| manual | `5cd104b9e006` | 6523 | GW3K-EHA-G20 | Usable passage in the loaded epoch 56 index. |
| manual | `5cd104b9e006` | 6524 | GW3.6K-EHA-G20 | Usable passage in the loaded epoch 56 index. |
| manual | `5cd104b9e006` | 6525 | GW5K-EHA-G20 | Usable passage in the loaded epoch 56 index. |
| manual | `5cd104b9e006` | 6526 | GW6K-EHA-G20 | Usable passage in the loaded epoch 56 index. |
| manual | `5cd104b9e006` | 6527 | GW8K-EHA-G20 | Usable passage in the loaded epoch 56 index. |
| manual | `5cd104b9e006` | 6528 | GW10K-EHA-G20 | Usable passage in the loaded epoch 56 index. |
| manual | `627e5444f47b` | 1954 | GW61.4-BAT-AC-G10 | Candidate adds the p2 floor mounting figure and the exact model listed on the p1 cover. |
| manual | `627e5444f47b` | 1955 | GW112.6-BAT-AC-G10 | Candidate adds the p2 floor mounting figure and the exact model listed on the p1 cover. |
| manual | `67a7f715ca9d` | 3556 | GW10K-ETA-G20 | Usable passage in the loaded epoch 56 index. |
| manual | `67a7f715ca9d` | 3584 | GW12K-ETA-G20 | Usable passage in the loaded epoch 56 index. |
| manual | `67a7f715ca9d` | 3585 | GW15K-ETA-G20 | Usable passage in the loaded epoch 56 index. |
| manual | `67a7f715ca9d` | 6514 | GW9.999K-ETA-G20 | Usable passage in the loaded epoch 56 index. |
| manual | `67a7f715ca9d` | 6515 | GW20K-ETA-G20 | Usable passage in the loaded epoch 56 index. |
| manual | `67a7f715ca9d` | 6516 | GW25K-ETA-G20 | Usable passage in the loaded epoch 56 index. |
| manual | `67a7f715ca9d` | 6517 | GW29.999K-ETA-G20 | Usable passage in the loaded epoch 56 index. |
| manual | `67a7f715ca9d` | 6518 | GW30K-ETA-G20 | Usable passage in the loaded epoch 56 index. |
| manual | `6bdd27e577fc` | 6321 | GW125/261-ESA-LCN-G10 | Usable passage in the loaded epoch 56 index. |
| manual | `6fbecc058303` | 2394 | GM330 | Usable passage in the loaded epoch 56 index. |
| manual | `894ef3bd6dac` | 3611 | GW6.0-BAT-D-G20 | Usable passage in the loaded epoch 56 index. |
| manual | `894ef3bd6dac` | 3612 | GW9.0-BAT-D-G20 | Usable passage in the loaded epoch 56 index. |
| manual | `a470d6e1be68` | 1179 | H2-25K-T3 | Usable passage in the loaded epoch 56 index. |
| manual | `a470d6e1be68` | 1181 | H2-30K-T3-DE | Usable passage in the loaded epoch 56 index. |
| manual | `a470d6e1be68` | 1182 | HS2-10K-T2-X | Usable passage in the loaded epoch 56 index. |
| manual | `a470d6e1be68` | 1183 | HS2-6K-T2-X | Usable passage in the loaded epoch 56 index. |
| manual | `a470d6e1be68` | 1184 | HS2-8K-T2-X | Usable passage in the loaded epoch 56 index. |
| manual | `a470d6e1be68` | 1185 | HS3-12K-T2-W/G-PX | Usable passage in the loaded epoch 56 index. |
| manual | `a470d6e1be68` | 1186 | HS3-6K-T2-W/G-PX | Usable passage in the loaded epoch 56 index. |
| manual | `a470d6e1be68` | 1187 | HS3-8K-T2-W/G-PX | Usable passage in the loaded epoch 56 index. |
| manual | `a470d6e1be68` | 2063 | H2-15K-T3 | Usable passage in the loaded epoch 56 index. |
| manual | `a470d6e1be68` | 2064 | H2-20K-T3 | Usable passage in the loaded epoch 56 index. |
| manual | `a470d6e1be68` | 2198 | HS3-5K-T2-W/G-PX | Usable passage in the loaded epoch 56 index. |
| manual | `a470d6e1be68` | 2199 | HS3-10K-T2-W/G-PX | Usable passage in the loaded epoch 56 index. |
| manual | `a470d6e1be68` | 4107 | H2-10K-T3 | Usable passage in the loaded epoch 56 index. |
| manual | `a470d6e1be68` | 4108 | H2-12K-T3 | Usable passage in the loaded epoch 56 index. |
| manual | `a470d6e1be68` | 4109 | HS2-5K-T2-X | Usable passage in the loaded epoch 56 index. |
| manual | `a70cb4c39824` | 4103 | CB2-57.3-HV5 | The quick guide includes K in the capacity range. The other manufacturer manual lists the models without K. |
| manual | `a70cb4c39824` | 4104 | CB2-71.6-HV5 | The quick guide includes K in the capacity range. The other manufacturer manual lists the models without K. |
| manual | `a70cb4c39824` | 4105 | CB2-85.9-HV5 | The quick guide includes K in the capacity range. The other manufacturer manual lists the models without K. |
| manual | `a70cb4c39824` | 4106 | CB2-100.3-HV5 | The quick guide includes K in the capacity range. The other manufacturer manual lists the models without K. |
| manual | `af395be79aee` | 3573 | eSolar AIO3 | Usable passage in the loaded epoch 56 index. |
| manual | `d5167d27d5e4` | 6321 | GW125/261-ESA-LCN-G10 | Usable passage in the loaded epoch 56 index. |
| manual | `f4d53810d74c` | 6321 | GW125/261-ESA-LCN-G10 | Usable passage in the loaded epoch 56 index. |
| manual | `f66efb70d0d8` | 1946 | GW80K-ET-G10 | Usable passage in the loaded epoch 56 index. |
| manual | `f66efb70d0d8` | 1947 | GW99.99K-ET-G10 | Usable passage in the loaded epoch 56 index. |
| manual | `f66efb70d0d8` | 1948 | GW100K-ET-G10 | Usable passage in the loaded epoch 56 index. |
| manual | `f66efb70d0d8` | 1956 | GW208.9-BAT-LC-G10 | Usable passage in the loaded epoch 56 index. |
| manual | `f66efb70d0d8` | 6506 | GW75K-ET-G10 | Usable passage in the loaded epoch 56 index. |
| other | `9f5b0d2b2430` | 3557 | GW11K-HCA-20 | Retired association. Replacement original `88a8a5bd9e70` is hosted, linked to this product and prepared in loaded epoch 56. |
| other | `9f5b0d2b2430` | 3586 | GW7K-HCA-20 | Retired association. Replacement original `88a8a5bd9e70` is hosted, linked to this product and prepared in loaded epoch 56. |
| other | `9f5b0d2b2430` | 3587 | GW22K-HCA-20 | Retired association. Replacement original `88a8a5bd9e70` is hosted, linked to this product and prepared in loaded epoch 56. |
| other | `be0569b4602a` | 1185 | HS3-12K-T2-W/G-PX | Page 4 conditional claims procedure searchable locally. Full policy terms remain unproven. |
| other | `be0569b4602a` | 1186 | HS3-6K-T2-W/G-PX | Page 4 conditional claims procedure searchable locally. Full policy terms remain unproven. |
| other | `be0569b4602a` | 1187 | HS3-8K-T2-W/G-PX | Page 4 conditional claims procedure searchable locally. Full policy terms remain unproven. |
| other | `be0569b4602a` | 2093 | BU3-5.0-TV2-PRO | Scope and conditions of the full policy remain unproven for this exact product. |
| other | `be0569b4602a` | 2198 | HS3-5K-T2-W/G-PX | Page 4 conditional claims procedure searchable locally. Full policy terms remain unproven. |
| other | `be0569b4602a` | 2199 | HS3-10K-T2-W/G-PX | Page 4 conditional claims procedure searchable locally. Full policy terms remain unproven. |
