# Nameplate photos and datasheets (#236)

`nameplates.py` runs the evaluation (usage in its docstring); `cases.json` holds the
expected readings and the turns. Results: `docs/acceptance/2026-10-18/236/eval/`.

## Photos

Real photographs of nameplates, kept here as evaluation material only: never
published or served by the site. Each is stored the way the shell sends a photo
(JPEG, at most 1.69 megapixels, no metadata); `source sha256` is the file as fetched.
Image search went through Apify (`hooli/google-images-scraper`, runs
`HWHtAdf6mVagjkv9K`, `0nYZmSetSYTMYpWuB` and the first run of 2026-10-18 01:36 UTC);
the image files were then fetched from the addresses it returned.

| File | Device (as printed) | Source | source sha256 |
|---|---|---|---|
| saj-sununo-plus-4k-m.jpg | SAJ Sununo Plus 4K-M | installer blog, camera photo: https://blog.carroarmato0.be/2024/01/18/saj-solar-inverter-and-home-assistant/ (serial number pixelated by the author) | 482cfc3c… |
| saj-r5-6k-s2-15.jpg | SAJ R5-6K-S2-15 (label prints no maker; the SAJ logo on the device stands upside down) | https://sunriver-inverter.com/de/leitfaden-zur-uberwachung-von-netzgekoppelten-wechselrichtern-von-saj/ | 927d710a… |
| goodwe-gw10k-et.jpg | GoodWe GW10K-ET | listing photo, http://www.technosolars.com/product/341/ (image https://ct.lnwfile.com/_/ct/_raw/ka/vf/fu.jpg) | 1a33a507… |
| goodwe-gw3648-em.jpg | GoodWe GW3648-EM (photographed sideways) | https://powerforum.co.za/topic/31162-goodwe-hybrid-inverter-gw-3648-em-r3200/ | 76906b95… |
| goodwe-gw5048-em.jpg | GoodWe GW5048-EM | https://www.reddit.com/r/diySolar/comments/1svytyp/ | 6e3ffd2a… |
| goodwe-gw7600a-es.jpg | GoodWe GW7600A-ES | https://www.reddit.com/r/SolarDIY/comments/1lm6kvy/ | f631403b… |
| goodwe-gw5048d-es.jpg | GoodWe GW5048D-ES | https://diysolarforum.com/threads/goodwe-hybrid-inverter-off-grid-only-install.85806/ | 4bbbc315… |
| goodwe-bat-c-label.jpg | GoodWe battery label for five models, none ticked | the label image in our hosted `GW_BAT-C-60-112kWh_Test-Report_IEC-62619.pdf`, page 6 | 204f5d48… |
| pylontech-us3000c.jpg | Pylontech US3000C (a pen line crosses the model field) | https://powerforum.co.za/topic/33738-pylontech-us-3000-briked/ | 6bf3c14f… |
| pylontech-us3000c-thumbnail.jpg | the same photo cut to 140 px: nothing legible but the logo | derived from the row above | — |
| ecoflow-powerocean-bd-5.1-s1.jpg | EcoFlow EF BD-5.1-S1 | our own upload `2026/07/ecoflow-powerocean-lfp-battery-module-label-specs.webp` | 1d64da10… |

None of the real photos shows a model we carry: the devices customers photograph are
mostly their own installed ones. The exact-match path is therefore run on the one
image that names a model of ours, the research's **synthetic** label
(`docs/research/2026-10-17-deepseek-flash-vision/raw/nameplate-probe.png`, SAJ
H2-10K-T3), marked `synthetic` in the results. A real photo of a nameplate of a model
we carry was searched for (SAJ H2/HS2/HS3/CB2, GoodWe ET/ETR/ESA, Pylontech Force H2,
US5000) and not found.

## PDFs

From the live snapshot's uploads (`--uploads`): `H2-10-30K-T2T3-datasheet-EN-BEU.pdf`
(two text pages), `SAJ_H2_15-30K-T3_Datasheet_DE.pdf` (two text pages) and
`GW_ETR_Quick-Installation-Guide-POLY.pdf` (four drawn pages without a text layer, so
each is rendered and read).
