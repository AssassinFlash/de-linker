# German document descriptions — local content repair

Snapshot: `/Users/chesterjohn/de-linker-data/20261029-1601`. Instance: `i18n765` at `http://127.0.0.1:8904`. No production write. The local WordPress 7.1.4 loader change is not part of this content branch.

The migration stores exact English display strings and their existing reviewed German titles in `linker_de_document_titles`. German pages use that title only on an exact match. English stored wording is unchanged. Official document titles that are not in this map stay as published.

## Verified consumer pages

| URL | After apply |
| --- | --- |
| http://127.0.0.1:8904/de/faq-dokumente/ | 200. `names the` / `covers the` / `chint dtsu666 catalog en` absent. Reviewed German descriptions present. Catalog row displays `Chint DTSU666 Produktübersicht (EN)`. |
| http://127.0.0.1:8904/faq-download/ | 200. English descriptions and `chint dtsu666 catalog en` remain. `Produktübersicht` absent. |
| http://127.0.0.1:8904/de/produkt/saj-h2-12k-t3/ | 200. `nennt den H2-12K-T3` present. `names the H2-12K-T3` absent. |
| http://127.0.0.1:8904/product/saj-h2-12k-t3/ | 200. `names the H2-12K-T3` present. German title absent. |
| http://127.0.0.1:8904/thank-you/ | 200. Already paired with `/de/danke/`. |
| http://127.0.0.1:8904/de/danke/ | 200. hreflang English alternate is `/thank-you/`. |

Rollback restored the English descriptions on the German pages, and a second apply was a no-op after the option was stored again.

## Not changed

- `29,999 kW` and `3,125 MWh` on German pages are German decimal notation for 29.999 kW and 3.125 MWh. They match GW29.999K and CESS-L3125. They are not English thousands separators, so they were not rewritten.
- `/thank-you/` and `/de/danke/` are already a native Polylang pair (posts 623 and 6873). Production readback on 2026-10-29 also returned 200 for both, with matching hreflang. Bare `/danke/` is 404 because German URLs are prefixed. No page was created.
- Official document titles such as `GoodWe ESA Series 5–30 kW Datasheet (EN)` stay in English on German pages.
- English `/faq-download/` still shows `chint dtsu666 catalog en`. The reviewed English title is `Chint DTSU666 catalog (EN)`, which still uses catalog. No new English title was invented.
- `chint dtsu666 dssu666 user manual en` is the same kind of filename title on the Chint row, with reviewed German `Chint DTSU666 / DSSU666 Benutzerhandbuch (EN)`. It was not in the confirmed catalog finding, so it was left unchanged.

## Exact reviewed pairs

78 pairs, zero blockers from the planner.

- `Certificate of conformity VDE-AR-N 4105:2018-11 for the SAJ CHS2 series, German and English (names the CHS2-29.9K-T4-X)` → `Konformitätszertifikat VDE-AR-N 4105:2018-11 für die SAJ CHS2 Serie, Deutsch und Englisch (nennt den CHS2-29.9K-T4-X)`
- `Certificate of conformity VDE-AR-N 4105:2018-11 for the SAJ CHS2 series, German and English (names the CHS2-30K-T4-X)` → `Konformitätszertifikat VDE-AR-N 4105:2018-11 für die SAJ CHS2 Serie, Deutsch und Englisch (nennt den CHS2-30K-T4-X)`
- `Certificate of conformity VDE-AR-N 4105:2018-11 for the SAJ CHS2 series, German and English (names the CHS2-50K-T6-X)` → `Konformitätszertifikat VDE-AR-N 4105:2018-11 für die SAJ CHS2 Serie, Deutsch und Englisch (nennt den CHS2-50K-T6-X)`
- `EU declaration of conformity for the SAJ BU3 battery and the BC3-TV, several languages including English and German (names the BU3-5.0-TV2-PRO)` → `EU-Konformitätserklärung für die SAJ Batterie BU3 und die BC3-TV, mehrere Sprachen, darunter Deutsch und Englisch (nennt das BU3-5.0-TV2-PRO)`
- `EU declaration of conformity for the SAJ CB2 battery systems, 13 languages including English and German (names the CB2-100.3-HV5)` → `EU-Konformitätserklärung für die SAJ CB2 Batteriesysteme, 13 Sprachen einschließlich Englisch und Deutsch (nennt den CB2-100.3-HV5)`
- `EU declaration of conformity for the SAJ CB2 battery systems, 13 languages including English and German (names the CB2-57.3-HV5)` → `EU-Konformitätserklärung für die SAJ CB2 Batteriesysteme, 13 Sprachen einschließlich Englisch und Deutsch (nennt den CB2-57.3-HV5)`
- `EU declaration of conformity for the SAJ CB2 battery systems, 13 languages including English and German (names the CB2-71.6-HV5)` → `EU-Konformitätserklärung für die SAJ CB2 Batteriesysteme, 13 Sprachen einschließlich Englisch und Deutsch (nennt den CB2-71.6-HV5)`
- `EU declaration of conformity for the SAJ CB2 battery systems, 13 languages including English and German (names the CB2-85.9-HV5)` → `EU-Konformitätserklärung für die SAJ CB2 Batteriesysteme, 13 Sprachen einschließlich Englisch und Deutsch (nennt den CB2-85.9-HV5)`
- `EU declaration of conformity for the SAJ H2 inverters, 13 languages including English and German (names the H2-10K-T3)` → `EU-Konformitätserklärung für die SAJ H2 Wechselrichter, 13 Sprachen, darunter Deutsch und Englisch (nennt den H2-10K-T3)`
- `EU declaration of conformity for the SAJ H2 inverters, 13 languages including English and German (names the H2-12K-T3)` → `EU-Konformitätserklärung für die SAJ H2 Wechselrichter, 13 Sprachen, darunter Deutsch und Englisch (nennt den H2-12K-T3)`
- `EU declaration of conformity for the SAJ H2 inverters, 13 languages including English and German (names the H2-15K-T3)` → `EU-Konformitätserklärung für die SAJ H2 Wechselrichter, 13 Sprachen, darunter Deutsch und Englisch (nennt den H2-15K-T3)`
- `EU declaration of conformity for the SAJ H2 inverters, 13 languages including English and German (names the H2-20K-T3)` → `EU-Konformitätserklärung für die SAJ H2 Wechselrichter, 13 Sprachen, darunter Deutsch und Englisch (nennt den H2-20K-T3)`
- `EU declaration of conformity for the SAJ H2 inverters, 13 languages including English and German (names the H2-25K-T3)` → `EU-Konformitätserklärung für die SAJ H2 Wechselrichter, 13 Sprachen, darunter Deutsch und Englisch (nennt den H2-25K-T3)`
- `EU declaration of conformity for the SAJ H2 inverters, 13 languages including English and German (names the H2-30K-T3-DE)` → `EU-Konformitätserklärung für die SAJ H2 Wechselrichter, 13 Sprachen, darunter Deutsch und Englisch (nennt den H2-30K-T3-DE)`
- `EU declaration of conformity for the SAJ HS3 systems, several languages including English and German (names the HS3-10K-T2-W/G-PX)` → `EU-Konformitätserklärung für die SAJ HS3 Systeme, mehrere Sprachen, darunter Deutsch und Englisch (nennt den HS3-10K-T2-W/G-PX)`
- `EU declaration of conformity for the SAJ HS3 systems, several languages including English and German (names the HS3-12K-T2-W/G-PX)` → `EU-Konformitätserklärung für die SAJ HS3 Systeme, mehrere Sprachen, darunter Deutsch und Englisch (nennt den HS3-12K-T2-W/G-PX)`
- `EU declaration of conformity for the SAJ HS3 systems, several languages including English and German (names the HS3-5K-T2-W/G-PX)` → `EU-Konformitätserklärung für die SAJ HS3 Systeme, mehrere Sprachen, darunter Deutsch und Englisch (nennt den HS3-5K-T2-W/G-PX)`
- `EU declaration of conformity for the SAJ HS3 systems, several languages including English and German (names the HS3-6K-T2-W/G-PX)` → `EU-Konformitätserklärung für die SAJ HS3 Systeme, mehrere Sprachen, darunter Deutsch und Englisch (nennt den HS3-6K-T2-W/G-PX)`
- `EU declaration of conformity for the SAJ HS3 systems, several languages including English and German (names the HS3-8K-T2-W/G-PX)` → `EU-Konformitätserklärung für die SAJ HS3 Systeme, mehrere Sprachen, darunter Deutsch und Englisch (nennt den HS3-8K-T2-W/G-PX)`
- `EU declaration of conformity for the SAJ eManager-C1 Pro, 8 languages including English and German` → `EU-Konformitätserklärung für den SAJ eManager-C1 Pro, 8 Sprachen einschließlich Englisch und Deutsch`
- `SAJ CB2 57.3-100.3-HV5 quick installation guide, English (covers the CB2-100.3-HV5)` → `SAJ CB2 57.3-100.3-HV5 Kurzanleitung zur Installation, Englisch (gilt für den CB2-100.3-HV5)`
- `SAJ CB2 57.3-100.3-HV5 quick installation guide, English (covers the CB2-57.3-HV5)` → `SAJ CB2 57.3-100.3-HV5 Kurzanleitung zur Installation, Englisch (gilt für den CB2-57.3-HV5)`
- `SAJ CB2 57.3-100.3-HV5 quick installation guide, English (covers the CB2-71.6-HV5)` → `SAJ CB2 57.3-100.3-HV5 Kurzanleitung zur Installation, Englisch (gilt für den CB2-71.6-HV5)`
- `SAJ CB2 57.3-100.3-HV5 quick installation guide, English (covers the CB2-85.9-HV5)` → `SAJ CB2 57.3-100.3-HV5 Kurzanleitung zur Installation, Englisch (gilt für den CB2-85.9-HV5)`
- `SAJ CB2 57.3-100.3-HV5 user manual, English, V0.0 (covers the CB2-100.3-HV5)` → `SAJ CB2 57.3-100.3-HV5 Handbuch, Englisch, V0.0 (gilt für den CB2-100.3-HV5)`
- `SAJ CB2 57.3-100.3-HV5 user manual, English, V0.0 (covers the CB2-57.3-HV5)` → `SAJ CB2 57.3-100.3-HV5 Handbuch, Englisch, V0.0 (gilt für den CB2-57.3-HV5)`
- `SAJ CB2 57.3-100.3-HV5 user manual, English, V0.0 (covers the CB2-71.6-HV5)` → `SAJ CB2 57.3-100.3-HV5 Handbuch, Englisch, V0.0 (gilt für den CB2-71.6-HV5)`
- `SAJ CB2 57.3-100.3-HV5 user manual, English, V0.0 (covers the CB2-85.9-HV5)` → `SAJ CB2 57.3-100.3-HV5 Handbuch, Englisch, V0.0 (gilt für den CB2-85.9-HV5)`
- `SAJ CHS2 29.9-50K user manual, English, V0.2 (covers the CHS2-29.9K-T4-X)` → `SAJ CHS2 29.9-50K Handbuch, Englisch, V0.2 (gilt für den CHS2-29.9K-T4-X)`
- `SAJ CHS2 29.9-50K user manual, English, V0.2 (covers the CHS2-30K-T4-X)` → `SAJ CHS2 29.9-50K Handbuch, Englisch, V0.2 (gilt für den CHS2-30K-T4-X)`
- `SAJ CHS2 29.9-50K user manual, English, V0.2 (covers the CHS2-50K-T6-X)` → `SAJ CHS2 29.9-50K Handbuch, Englisch, V0.2 (gilt für den CHS2-50K-T6-X)`
- `SAJ CHS2 30-50K datasheet with the CB2 battery table, English (covers the CB2-100.3-HV5)` → `SAJ CHS2 30-50K Datenblatt mit der CB2-Batterietabelle, Englisch (gilt für den CB2-100.3-HV5)`
- `SAJ CHS2 30-50K datasheet with the CB2 battery table, English (covers the CB2-57.3-HV5)` → `SAJ CHS2 30-50K Datenblatt mit der CB2-Batterietabelle, Englisch (gilt für den CB2-57.3-HV5)`
- `SAJ CHS2 30-50K datasheet with the CB2 battery table, English (covers the CB2-71.6-HV5)` → `SAJ CHS2 30-50K Datenblatt mit der CB2-Batterietabelle, Englisch (gilt für den CB2-71.6-HV5)`
- `SAJ CHS2 30-50K datasheet with the CB2 battery table, English (covers the CB2-85.9-HV5)` → `SAJ CHS2 30-50K Datenblatt mit der CB2-Batterietabelle, Englisch (gilt für den CB2-85.9-HV5)`
- `SAJ CHS2 30-50K datasheet with the CB2 battery table, German (covers the CB2-100.3-HV5)` → `SAJ CHS2 30-50K Datenblatt mit der CB2-Batterietabelle, Deutsch (gilt für den CB2-100.3-HV5)`
- `SAJ CHS2 30-50K datasheet with the CB2 battery table, German (covers the CB2-57.3-HV5)` → `SAJ CHS2 30-50K Datenblatt mit der CB2-Batterietabelle, Deutsch (gilt für den CB2-57.3-HV5)`
- `SAJ CHS2 30-50K datasheet with the CB2 battery table, German (covers the CB2-71.6-HV5)` → `SAJ CHS2 30-50K Datenblatt mit der CB2-Batterietabelle, Deutsch (gilt für den CB2-71.6-HV5)`
- `SAJ CHS2 30-50K datasheet with the CB2 battery table, German (covers the CB2-85.9-HV5)` → `SAJ CHS2 30-50K Datenblatt mit der CB2-Batterietabelle, Deutsch (gilt für den CB2-85.9-HV5)`
- `SAJ CHS2 30-50K datasheet, English (covers the CHS2-29.9K-T4-X)` → `SAJ CHS2 30-50K Datenblatt, Englisch (gilt für den CHS2-29.9K-T4-X)`
- `SAJ CHS2 30-50K datasheet, English (covers the CHS2-30K-T4-X)` → `SAJ CHS2 30-50K Datenblatt, Englisch (gilt für den CHS2-30K-T4-X)`
- `SAJ CHS2 30-50K datasheet, English (covers the CHS2-50K-T6-X)` → `SAJ CHS2 30-50K Datenblatt, Englisch (gilt für den CHS2-50K-T6-X)`
- `SAJ CHS2 30-50K datasheet, German (covers the CHS2-29.9K-T4-X)` → `SAJ CHS2 30-50K Datenblatt, Deutsch (gilt für den CHS2-29.9K-T4-X)`
- `SAJ CHS2 30-50K datasheet, German (covers the CHS2-30K-T4-X)` → `SAJ CHS2 30-50K Datenblatt, Deutsch (gilt für den CHS2-30K-T4-X)`
- `SAJ CHS2 30-50K datasheet, German (covers the CHS2-50K-T6-X)` → `SAJ CHS2 30-50K Datenblatt, Deutsch (gilt für den CHS2-50K-T6-X)`
- `SAJ H2 10-30K datasheet, English (covers the H2-10K-T3)` → `SAJ H2 10-30K Datenblatt, Englisch (gilt für den H2-10K-T3)`
- `SAJ H2 10-30K datasheet, English (covers the H2-12K-T3)` → `SAJ H2 10-30K Datenblatt, Englisch (gilt für den H2-12K-T3)`
- `SAJ H2 10-30K datasheet, English (covers the H2-15K-T3)` → `SAJ H2 10-30K Datenblatt, Englisch (gilt für den H2-15K-T3)`
- `SAJ H2 10-30K datasheet, English (covers the H2-20K-T3)` → `SAJ H2 10-30K Datenblatt, Englisch (gilt für den H2-20K-T3)`
- `SAJ H2 10-30K datasheet, English (covers the H2-25K-T3)` → `SAJ H2 10-30K Datenblatt, Englisch (gilt für den H2-25K-T3)`
- `SAJ H2 10-30K datasheet, English (covers the H2-30K-T3-DE)` → `SAJ H2 10-30K Datenblatt, Englisch (gilt für den H2-30K-T3-DE)`
- `SAJ H2 10-30K user manual, German and English (covers the H2-10K-T3)` → `SAJ H2 10-30K Handbuch, Deutsch und Englisch (gilt für den H2-10K-T3)`
- `SAJ H2 10-30K user manual, German and English (covers the H2-12K-T3)` → `SAJ H2 10-30K Handbuch, Deutsch und Englisch (gilt für den H2-12K-T3)`
- `SAJ H2 10-30K user manual, German and English (covers the H2-15K-T3)` → `SAJ H2 10-30K Handbuch, Deutsch und Englisch (gilt für den H2-15K-T3)`
- `SAJ H2 10-30K user manual, German and English (covers the H2-20K-T3)` → `SAJ H2 10-30K Handbuch, Deutsch und Englisch (gilt für den H2-20K-T3)`
- `SAJ H2 10-30K user manual, German and English (covers the H2-25K-T3)` → `SAJ H2 10-30K Handbuch, Deutsch und Englisch (gilt für den H2-25K-T3)`
- `SAJ H2 10-30K user manual, German and English (covers the H2-30K-T3-DE)` → `SAJ H2 10-30K Handbuch, Deutsch und Englisch (gilt für den H2-30K-T3-DE)`
- `SAJ H2 15-30K datasheet, German (covers the H2-15K-T3)` → `SAJ H2 15-30K Datenblatt, Deutsch (gilt für den H2-15K-T3)`
- `SAJ H2 15-30K datasheet, German (covers the H2-20K-T3)` → `SAJ H2 15-30K Datenblatt, Deutsch (gilt für den H2-20K-T3)`
- `SAJ H2 15-30K datasheet, German (covers the H2-25K-T3)` → `SAJ H2 15-30K Datenblatt, Deutsch (gilt für den H2-25K-T3)`
- `SAJ H2 15-30K datasheet, German (covers the H2-30K-T3-DE)` → `SAJ H2 15-30K Datenblatt, Deutsch (gilt für den H2-30K-T3-DE)`
- `SAJ HS3 5-12K three-phase datasheet, English (covers the HS3-10K-T2-W/G-PX)` → `SAJ HS3 5-12K Datenblatt, dreiphasig, Englisch (gilt für den HS3-10K-T2-W/G-PX)`
- `SAJ HS3 5-12K three-phase datasheet, English (covers the HS3-12K-T2-W/G-PX)` → `SAJ HS3 5-12K Datenblatt, dreiphasig, Englisch (gilt für den HS3-12K-T2-W/G-PX)`
- `SAJ HS3 5-12K three-phase datasheet, English (covers the HS3-5K-T2-W/G-PX)` → `SAJ HS3 5-12K Datenblatt, dreiphasig, Englisch (gilt für den HS3-5K-T2-W/G-PX)`
- `SAJ HS3 5-12K three-phase datasheet, English (covers the HS3-6K-T2-W/G-PX)` → `SAJ HS3 5-12K Datenblatt, dreiphasig, Englisch (gilt für den HS3-6K-T2-W/G-PX)`
- `SAJ HS3 5-12K three-phase datasheet, English (covers the HS3-8K-T2-W/G-PX)` → `SAJ HS3 5-12K Datenblatt, dreiphasig, Englisch (gilt für den HS3-8K-T2-W/G-PX)`
- `SAJ HS3 5-12K three-phase datasheet, German (covers the HS3-10K-T2-W/G-PX)` → `SAJ HS3 5-12K Datenblatt, dreiphasig, Deutsch (gilt für den HS3-10K-T2-W/G-PX)`
- `SAJ HS3 5-12K three-phase datasheet, German (covers the HS3-12K-T2-W/G-PX)` → `SAJ HS3 5-12K Datenblatt, dreiphasig, Deutsch (gilt für den HS3-12K-T2-W/G-PX)`
- `SAJ HS3 5-12K three-phase datasheet, German (covers the HS3-5K-T2-W/G-PX)` → `SAJ HS3 5-12K Datenblatt, dreiphasig, Deutsch (gilt für den HS3-5K-T2-W/G-PX)`
- `SAJ HS3 5-12K three-phase datasheet, German (covers the HS3-6K-T2-W/G-PX)` → `SAJ HS3 5-12K Datenblatt, dreiphasig, Deutsch (gilt für den HS3-6K-T2-W/G-PX)`
- `SAJ HS3 5-12K three-phase datasheet, German (covers the HS3-8K-T2-W/G-PX)` → `SAJ HS3 5-12K Datenblatt, dreiphasig, Deutsch (gilt für den HS3-8K-T2-W/G-PX)`
- `SAJ HS3 three-phase user manual, English, V4 (covers the BU3-5.0-TV2-PRO)` → `SAJ HS3 Handbuch, dreiphasig, Englisch, V4 (gilt für das BU3-5.0-TV2-PRO)`
- `SAJ HS3 three-phase user manual, English, V4 (covers the HS3-10K-T2-W/G-PX)` → `SAJ HS3 Handbuch, dreiphasig, Englisch, V4 (gilt für den HS3-10K-T2-W/G-PX)`
- `SAJ HS3 three-phase user manual, English, V4 (covers the HS3-12K-T2-W/G-PX)` → `SAJ HS3 Handbuch, dreiphasig, Englisch, V4 (gilt für den HS3-12K-T2-W/G-PX)`
- `SAJ HS3 three-phase user manual, English, V4 (covers the HS3-5K-T2-W/G-PX)` → `SAJ HS3 Handbuch, dreiphasig, Englisch, V4 (gilt für den HS3-5K-T2-W/G-PX)`
- `SAJ HS3 three-phase user manual, English, V4 (covers the HS3-6K-T2-W/G-PX)` → `SAJ HS3 Handbuch, dreiphasig, Englisch, V4 (gilt für den HS3-6K-T2-W/G-PX)`
- `SAJ HS3 three-phase user manual, English, V4 (covers the HS3-8K-T2-W/G-PX)` → `SAJ HS3 Handbuch, dreiphasig, Englisch, V4 (gilt für den HS3-8K-T2-W/G-PX)`
- `chint dtsu666 catalog en` → `Chint DTSU666 Katalog (EN)`
