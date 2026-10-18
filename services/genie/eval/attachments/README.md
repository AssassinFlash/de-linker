# Nameplate photos and datasheets (#236)

`nameplates.py` runs the evaluation (usage in its docstring); `cases.json` holds the
expected readings and the turns. Results: `docs/acceptance/2026-10-18/236/eval/`.

## Where the images are

The photographs of `photos/` are in the repository, next to this file: their use as
evaluation material here was confirmed with the owner on 2026-10-18, so the set needs
no re-fetch to run. The label images taken from the PDFs we host stay outside the
repository, in `~/de-linker-data/eval/attachments/labels/` (`--labels` of
`nameplates.py`); each row below names its PDF and sums, so the set can be made again
from the snapshot's uploads (`--uploads`).

- `photos/`: the photographs below, each stored the way the shell sends a photo (a
  JPEG of at most 1.69 megapixels, no metadata);
- `labels/`: nameplate images taken from PDFs we host on de-linker.com.

The tables name each file's source and two sha256 sums: the source as fetched, and
the stored file (`stored sha256`), so anyone can check a file against its row.

## Photos (`photos/`)

Image search went through Apify (`hooli/google-images-scraper`, runs
`HWHtAdf6mVagjkv9K`, `0nYZmSetSYTMYpWuB` and the first run of 2026-10-18 01:36 UTC);
the image files were then fetched from the addresses it returned. Where the full
source sum was not recorded at the time and the page now refuses a plain fetch
(HTTP 403 on 2026-10-18), the first eight hex digits recorded then are given.

| File | Device (as printed) | Source | source sha256 | stored sha256 |
|---|---|---|---|---|
| saj-sununo-plus-4k-m.jpg | SAJ Sununo Plus 4K-M | installer blog, camera photo (serial number pixelated by the author): https://blog.carroarmato0.be/content/images/2024/01/IMG_20231127_151458.jpg on https://blog.carroarmato0.be/2024/01/18/saj-solar-inverter-and-home-assistant/ | 482cfc3c5437526a… (re-fetched 2026-10-18, matches) | 9a2e4d3eaa6ef367b2d250f66abdcb25bd3e41940cc37ada280e496b4b2704eb |
| saj-r5-6k-s2-15.jpg | SAJ R5-6K-S2-15 (the label prints no maker; the SAJ logo on the device stands upside down) | https://sunriver-inverter.com/wp-content/uploads/2025/09/saj-r5-serial-number-sticker-label-close-up.webp | 927d710a24b9fc5937c11846c8f5dbc89b6f5742f8cd749b0233d5fa5e78f402 | 52e50c7cc3aa6636453b8d49c65f222a001febdd463dcdb889849683ae905897 |
| goodwe-gw10k-et.jpg | GoodWe GW10K-ET | listing photo https://ct.lnwfile.com/_/ct/_raw/ka/vf/fu.jpg on http://www.technosolars.com/product/341/ | 1a33a5077474c7dbf1c8ee5af721d49fec371248c678d2f1d0919491b516237f | 99efdd81dbde02984a02af7dad3e411f12c247ea2a9f5d21d12947f7194645c6 |
| goodwe-gw3648-em.jpg | GoodWe GW3648-EM (photographed sideways) | https://powerforum.co.za/topic/31162-goodwe-hybrid-inverter-gw-3648-em-r3200/ | 76906b95… | e185577027b0f728f98f5220b20516fbce91590d8471c57cdf395024ab5862fb |
| goodwe-gw5048-em.jpg | GoodWe GW5048-EM | https://www.reddit.com/r/diySolar/comments/1svytyp/ | 6e3ffd2a… | e2c8b4f00a79cb7d72f7b87aebc7eb51e9f5bfe38443d30aa7a56b4f9c468fd1 |
| goodwe-gw7600a-es.jpg | GoodWe GW7600A-ES | https://www.reddit.com/r/SolarDIY/comments/1lm6kvy/ | f631403b… | 892bceaec63174527a5e1890ceb412add019c930dd011893014ee703c639ab6f |
| goodwe-gw5048d-es.jpg | GoodWe GW5048D-ES | https://diysolarforum.com/threads/goodwe-hybrid-inverter-off-grid-only-install.85806/ | 4bbbc315… | 985d347fc35c4fee2f90e00e8a516bd8e7b50adafc28210c7b229c2271050850 |
| goodwe-bat-c-label.jpg | GoodWe battery label for five models, none ticked | the label image on page 6 of our hosted `2026/10/GW_BAT-C-60-112kWh_Test-Report_IEC-62619.pdf` | 6129c36f5b91a0f78e43136bfa37880c542a4ce1f0ba275d953bcbbfab80bc12 (the PDF) | 59d40deb19139218c7cbf8bcd26634aad8b6be643663bbdd7bd492825e3eaf08 |
| pylontech-us3000c.jpg | Pylontech US3000C (a pen line crosses the model field) | https://powerforum.co.za/topic/33738-pylontech-us-3000-briked/ | 6bf3c14f… | 50a8e412ada8ccc1c783a8202f967f1225596d9154ea4680677348f3b33b3ce8 |
| pylontech-us3000c-thumbnail.jpg | the same photo cut to 140 px: nothing legible but the logo | derived from the row above | — | 0618bfbbc71df9f55957b0c98d7469a0d0cbeaeb436663da2fcfe5749fc0a4a8 |
| ecoflow-powerocean-bd-5.1-s1.jpg | EcoFlow EF BD-5.1-S1 | our upload `2026/07/ecoflow-powerocean-lfp-battery-module-label-specs.webp` | 1d64da100daf559c8e1b1ea8655e943e24f7f07e42ac9d896464551db725a017 | 420a8816ac22987e589cb2a928fee3b1b20aa661d8cd5c062b754793ca6f6fef |

None of these photos shows a model we carry: the devices customers photograph are
mostly their own installed ones.

## Labels from our hosted documents (`labels/`)

Review round 1 of PR #309, item 12: real label images of models we carry, taken from
the manuals, datasheets, certificates and test reports we host (live snapshot
2026-10-18 10:43, `uploads/`). Every SAJ, GoodWe and Pylontech PDF was searched by
its text layer for nameplate words (nameplate, name plate, label, Typenschild,
Etikett), and the knowledge index's chunks for the same words; the hits, and the
product chapters of the manuals of models we carry, were then looked at page by
page. A photo inside a PDF is taken out as the PDF holds it (nothing redrawn or
generated); a drawn label is rendered from its page and cut to the label.

| File | Device (as printed) | In our range | Source | source sha256 (the PDF) | stored sha256 |
|---|---|---|---|---|---|
| goodwe-gw112.6-bat-ac-g10-report-p8.jpg | GoodWe GW112.6-BAT-AC-G10, ticked among six models | yes (product 1955): exact | photo on page 8 of `2026/10/GW112.6-BAT-AC-G10_UN38.3_Test-Report.pdf` | 000592098663cf71f5ea583073e3b41696bb0b19670336d9cd208d5a52d0740c | 310e0c6b39f79aae3561a8cf435fda975cce3c951e81479cbe31e722110758fd |
| goodwe-gw112.6-bat-ac-g10-report-p13.jpg | the same label model in a second photo (no serial number) | yes (product 1955): exact | photo on page 13 of the same report | as above | 20dbf751e77c73c4f4b26148c887677160df931a9cbfa1ca447d8a5cd3f6a44b |
| goodwe-gw5kn-et-manual-p26.jpg | GoodWe GW5KN-ET (drawn label) | no: a GoodWe ET model we do not carry | page 26 of `2026/07/goodwe_et_plus_user_manual.pdf`, rendered at 4× and cut to the label | 09f0b936745903fd309fc7cc21d88fc7ae534fdf5e42d79c4b5cf4c6a7c96bc4 | 85c84a5f58649057c686587afc89e1ac209e683ed7e5e868efb5943facfa1198 |

- **SAJ: none available.** No hosted SAJ PDF shows a nameplate: the text layers name
  only an LED status label and the Caro wallbox's placeholder label
  (`ACXXXX-XE-XX`, not in our range), and the product chapters of the H2
  (5–12K-LS2, 10–30K-T3), B2 and CB2 manuals and the H2 and B2/BU2 declarations of
  conformity show none.
- **Pylontech: none available.** The one Pylontech model we carry is the OPTIM US
  L260-OMNI (product 2003); its hosted documents are two-page datasheets without a
  label. The Pylontech manuals we host (US3000C, US5000, Force H2/H3, PowerCube)
  show symbol and danger labels, never a rating label with a model, and those
  models are not in our range.
- The exact-match tier is therefore measured on the two real GoodWe photos, and on
  the research's synthetic SAJ H2-10K-T3 label
  (`docs/research/2026-10-17-deepseek-flash-vision/raw/nameplate-probe.png`, drawn
  for the research and kept in the repository), marked `synthetic` in the results.
