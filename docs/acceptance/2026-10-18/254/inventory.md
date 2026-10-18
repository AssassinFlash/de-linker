# Live discovery and English segments

Read-only Apify evidence, 2026-10-18. Exact actor inputs are `discovery-input.json` and `sitemap-input.json`. Sitemap run `7h540xcedbJaZbP1t`, dataset `QfBRrNIaDX8wp97dE`; crawl run `lmsSlRuDxc2Kc8uTa`, dataset `RNBfC286NwNzP0ZEn`. All five XML responses and all 165 crawl responses returned 200. Query strings were excluded from crawl deduplication.

Sitemap: 149 German URLs; crawl: 165; union: 166. Supplementary entries cover native account functions, reset, paging and historical category aliases. Confirmation and inquiry detail use owned ephemeral records in integration tests rather than publishing a real customer record.

Descriptive English segments found: `category`, `applications-blog`, `battery-storage-blog`, `installation-commissioning`, `monitoring-energy-management`, `system-design`, `compare-products`, `faq-download`, `gateway`, `cloud`, `register`, `lost-password`, `service-support`, `ems-monitoring`, `all-in-one-systeme`, `page`; product phrases `battery`, `battery-module`, `battery-stack-bridge`, `lfp-battery-base`, `single-phase-hybrid`, `three-phase-hybrid`, `hybrid-inverter`, `power-module`, `all-in-one`, `flagship`, `ev-charger`, `smart-energy-controller`, `residential-energy-manager`, `data-collector`. Supplementary functional segments: `inquiries`, `inquiry`, `saved-solutions`, `documents`, `company`, `billing`, `shipping`, `edit-account`, `customer-logout`, `inquiry-received`.

The German old draft word is prohibited customer vocabulary and is replaced by `loesungsentwurf`. Proper names EcoFlow, Ocean, GoodWe, SAJ, eManager, eSolar, EZManager and model/SKU tokens remain; technical abbreviations LFP, EMS, HEMS, C&I/CI, EV, WiFi, LAN, Bluetooth, NFC, CT, AC/DC, kW/kWh, V and HV remain. `Blog`, `FAQ`, `Hybrid`, `Manager` and `Monitoring` in German copy are established loanwords, but descriptive English URL phrases above receive the explicit German forms in the table. No remaining segment is silently exempted as a product description.

| Previous German URL | Discovery | New canonical URL |
|---|---|---|
| `/de/` | crawl, sitemap | `/de/` |
| `/de/batteriegroesse-heimspeicher-notstrom/` | crawl, sitemap | `/de/batteriegroesse-heimspeicher-notstrom/` |
| `/de/blog/` | crawl, sitemap | `/de/blog/` |
| `/de/category/anwendungen/` | supplement | `/de/kategorie/anwendungen/` |
| `/de/category/applications-blog/` | crawl | `/de/kategorie/anwendungen/` |
| `/de/category/batteriespeicher/` | supplement | `/de/kategorie/batteriespeicher/` |
| `/de/category/battery-storage-blog/` | crawl | `/de/kategorie/batteriespeicher/` |
| `/de/category/installation-commissioning/` | crawl | `/de/kategorie/installation-inbetriebnahme/` |
| `/de/category/installation-inbetriebnahme/` | supplement | `/de/kategorie/installation-inbetriebnahme/` |
| `/de/category/monitoring-energy-management/` | crawl | `/de/kategorie/ueberwachung-energiemanagement/` |
| `/de/category/system-design/` | crawl | `/de/kategorie/systemauslegung/` |
| `/de/category/systemauslegung/` | supplement | `/de/kategorie/systemauslegung/` |
| `/de/category/uberwachung-energiemanagement/` | supplement | `/de/kategorie/ueberwachung-energiemanagement/` |
| `/de/category/ueberwachung-energiemanagement/` | supplement | `/de/kategorie/ueberwachung-energiemanagement/` |
| `/de/compare-products/` | crawl, sitemap | `/de/produkte-vergleichen/` |
| `/de/danke/` | crawl, sitemap | `/de/danke/` |
| `/de/datenschutz/` | crawl, sitemap | `/de/datenschutz/` |
| `/de/faq-download/` | crawl, sitemap | `/de/faq-dokumente/` |
| `/de/fernueberwachung-nach-installation/` | crawl, sitemap | `/de/fernueberwachung-nach-installation/` |
| `/de/fuer-epc/` | crawl, sitemap | `/de/fuer-epc/` |
| `/de/fuer-installateur/` | crawl, sitemap | `/de/fuer-installateur/` |
| `/de/gateway-zaehler-cloud-ueberwachung-datenebene/` | crawl, sitemap | `/de/kommunikationsschnittstelle-zaehler-fernueberwachung-datenebene/` |
| `/de/genie/` | crawl, sitemap | `/de/genie/` |
| `/de/gewerbespeicher-lastspitzenkappung-notstrom-skalierbarkeit/` | crawl, sitemap | `/de/gewerbespeicher-lastspitzenkappung-notstrom-skalierbarkeit/` |
| `/de/heimspeicher-notstrom-eigenverbrauch/` | crawl, sitemap | `/de/heimspeicher-notstrom-eigenverbrauch/` |
| `/de/hybridwechselrichter-vs-ac-speicher/` | crawl, sitemap | `/de/hybridwechselrichter-vs-ac-speicher/` |
| `/de/impressum/` | crawl, sitemap | `/de/impressum/` |
| `/de/innen-vs-aussen-akku-planung/` | crawl, sitemap | `/de/innen-vs-aussen-akku-planung/` |
| `/de/installateur-checkliste-wechselrichter-akku/` | crawl, sitemap | `/de/installateur-checkliste-wechselrichter-akku/` |
| `/de/installateur-uebergabe-dokumentation-checkliste/` | crawl, sitemap | `/de/installateur-uebergabe-dokumentation-checkliste/` |
| `/de/kontakt/` | crawl, sitemap | `/de/kontakt/` |
| `/de/loesung/` | crawl, sitemap | `/de/loesung/` |
| `/de/loesung/gewerbespeicher/` | crawl, sitemap | `/de/loesung/gewerbespeicher/` |
| `/de/loesung/grossspeicher/` | crawl, sitemap | `/de/loesung/grossspeicher/` |
| `/de/loesung/heimspeicher/` | crawl, sitemap | `/de/loesung/heimspeicher/` |
| `/de/loesungskonfigurator/` | crawl, sitemap | `/de/loesungskonfigurator/` |
| `/de/mein-konto/` | sitemap | `/de/mein-konto/` |
| `/de/mein-konto/company/` | supplement | `/de/mein-konto/unternehmen/` |
| `/de/mein-konto/company/billing/` | supplement | `/de/mein-konto/unternehmen/rechnungsadresse/` |
| `/de/mein-konto/company/shipping/` | supplement | `/de/mein-konto/unternehmen/lieferadresse/` |
| `/de/mein-konto/customer-logout/` | supplement | `/de/mein-konto/abmelden/` |
| `/de/mein-konto/documents/` | supplement | `/de/mein-konto/dokumente/` |
| `/de/mein-konto/edit-account/` | supplement | `/de/mein-konto/kontodaten/` |
| `/de/mein-konto/inquiries/` | supplement | `/de/mein-konto/anfragen/` |
| `/de/mein-konto/inquiries/2/` | supplement | `/de/mein-konto/anfragen/2/` |
| `/de/mein-konto/lost-password/` | supplement | `/de/mein-konto/passwort-zuruecksetzen/` |
| `/de/mein-konto/register/` | crawl | `/de/mein-konto/registrieren/` |
| `/de/mein-konto/saved-solutions/` | supplement | `/de/mein-konto/gespeicherte-loesungen/` |
| `/de/mein-konto/unternehmen/billing/` | supplement | `/de/mein-konto/unternehmen/rechnungsadresse/` |
| `/de/mein-konto/unternehmen/shipping/` | supplement | `/de/mein-konto/unternehmen/lieferadresse/` |
| `/de/produkt-kategorie/ems-monitoring/` | crawl, sitemap | `/de/produkt-kategorie/ems-ueberwachung/` |
| `/de/produkt-kategorie/gewerbespeicher/` | crawl, sitemap | `/de/produkt-kategorie/gewerbespeicher/` |
| `/de/produkt-kategorie/gewerbespeicher/all-in-one-systeme/` | crawl, sitemap | `/de/produkt-kategorie/gewerbespeicher/komplettsysteme/` |
| `/de/produkt-kategorie/gewerbespeicher/batteriesysteme/` | crawl, sitemap | `/de/produkt-kategorie/gewerbespeicher/batteriesysteme/` |
| `/de/produkt-kategorie/heimspeicher/` | crawl, sitemap | `/de/produkt-kategorie/heimspeicher/` |
| `/de/produkt-kategorie/ladestationen/` | crawl, sitemap | `/de/produkt-kategorie/ladestationen/` |
| `/de/produkt-kategorie/wechselrichter/` | crawl, sitemap | `/de/produkt-kategorie/wechselrichter/` |
| `/de/produkt-kategorie/wechselrichter/page/2/` | crawl | `/de/produkt-kategorie/wechselrichter/seite/2/` |
| `/de/produkt-kategorie/wechselrichter/page/3/` | crawl | `/de/produkt-kategorie/wechselrichter/seite/3/` |
| `/de/produkt-kategorie/wechselrichter/page/4/` | crawl | `/de/produkt-kategorie/wechselrichter/seite/4/` |
| `/de/produkt-kategorie/zubehoer/` | crawl, sitemap | `/de/produkt-kategorie/zubehoer/` |
| `/de/produkt-kategorie/zubehoer/energiezaehler-stromwandler/` | crawl, sitemap | `/de/produkt-kategorie/zubehoer/energiezaehler-stromwandler/` |
| `/de/produkt-kategorie/zubehoer/notstrom/` | crawl, sitemap | `/de/produkt-kategorie/zubehoer/notstrom/` |
| `/de/produkt/chint-dtsu666/` | crawl, sitemap | `/de/produkt/chint-dtsu666/` |
| `/de/produkt/ecoflow-battery-stack-bridge/` | crawl | `/de/produkt/ecoflow-verbinder-fuer-batteriestapel/` |
| `/de/produkt/ecoflow-ocean-2-battery-5-02-kwh-ef-bd-5-s2/` | crawl, sitemap | `/de/produkt/ecoflow-ocean-2-batterie-5-02-kwh-ef-bd-5-s2/` |
| `/de/produkt/ecoflow-ocean-2-battery-8-0-kwh-ef-bd-8-s2/` | crawl, sitemap | `/de/produkt/ecoflow-ocean-2-batterie-8-0-kwh-ef-bd-8-s2/` |
| `/de/produkt/ecoflow-ocean-2-hd-p1-10k0-s2-10-kw-single-phase-hybrid-2026-flagship/` | crawl, sitemap | `/de/produkt/ecoflow-ocean-2-hd-p1-10k0-s2-10-kw-einphasiger-hybridwechselrichter-2026-spitzenmodell/` |
| `/de/produkt/ecoflow-ocean-2-hd-p1-12k0-s2-12-kw-single-phase-hybrid-2026-flagship/` | crawl, sitemap | `/de/produkt/ecoflow-ocean-2-hd-p1-12k0-s2-12-kw-einphasiger-hybridwechselrichter-2026-spitzenmodell/` |
| `/de/produkt/ecoflow-ocean-2-hd-p1-3k-s2-3-kw-single-phase-hybrid/` | crawl, sitemap | `/de/produkt/ecoflow-ocean-2-hd-p1-3k-s2-3-kw-einphasiger-hybridwechselrichter/` |
| `/de/produkt/ecoflow-ocean-2-hd-p1-3k68-s2-3-68-kw-single-phase-hybrid/` | crawl, sitemap | `/de/produkt/ecoflow-ocean-2-hd-p1-3k68-s2-3-68-kw-einphasiger-hybridwechselrichter/` |
| `/de/produkt/ecoflow-ocean-2-hd-p1-4k6-s2-4-6-kw-single-phase-hybrid/` | crawl, sitemap | `/de/produkt/ecoflow-ocean-2-hd-p1-4k6-s2-4-6-kw-einphasiger-hybridwechselrichter/` |
| `/de/produkt/ecoflow-ocean-2-hd-p1-5k-s2-5-kw-single-phase-hybrid/` | crawl, sitemap | `/de/produkt/ecoflow-ocean-2-hd-p1-5k-s2-5-kw-einphasiger-hybridwechselrichter/` |
| `/de/produkt/ecoflow-ocean-2-hd-p1-5k75-s2-5-75-kw-single-phase-hybrid/` | crawl, sitemap | `/de/produkt/ecoflow-ocean-2-hd-p1-5k75-s2-5-75-kw-einphasiger-hybridwechselrichter/` |
| `/de/produkt/ecoflow-ocean-2-hd-p1-6k-s2-6-kw-single-phase-hybrid/` | crawl, sitemap | `/de/produkt/ecoflow-ocean-2-hd-p1-6k-s2-6-kw-einphasiger-hybridwechselrichter/` |
| `/de/produkt/ecoflow-ocean-2-hd-p1-6k0-s2-6-kw-single-phase-hybrid-2026-flagship/` | crawl, sitemap | `/de/produkt/ecoflow-ocean-2-hd-p1-6k0-s2-6-kw-einphasiger-hybridwechselrichter-2026-spitzenmodell/` |
| `/de/produkt/ecoflow-ocean-2-hd-p1-8k0-s2-8-kw-single-phase-hybrid-2026-flagship/` | crawl, sitemap | `/de/produkt/ecoflow-ocean-2-hd-p1-8k0-s2-8-kw-einphasiger-hybridwechselrichter-2026-spitzenmodell/` |
| `/de/produkt/ecoflow-ocean-2-hd-p3-10k0-s2-10-kw-three-phase-hybrid-2026-flagship/` | crawl, sitemap | `/de/produkt/ecoflow-ocean-2-hd-p3-10k0-s2-10-kw-dreiphasiger-hybridwechselrichter-2026-spitzenmodell/` |
| `/de/produkt/ecoflow-ocean-2-hd-p3-12k0-s2-12-kw-three-phase-hybrid-2026-flagship/` | crawl, sitemap | `/de/produkt/ecoflow-ocean-2-hd-p3-12k0-s2-12-kw-dreiphasiger-hybridwechselrichter-2026-spitzenmodell/` |
| `/de/produkt/ecoflow-ocean-2-hd-p3-15k-g2-15-kw-three-phase-hybrid/` | crawl, sitemap | `/de/produkt/ecoflow-ocean-2-hd-p3-15k-g2-15-kw-dreiphasiger-hybridwechselrichter/` |
| `/de/produkt/ecoflow-ocean-2-hd-p3-15k-g2f-15-kw-three-phase-hybrid/` | crawl, sitemap | `/de/produkt/ecoflow-ocean-2-hd-p3-15k-g2f-15-kw-dreiphasiger-hybridwechselrichter/` |
| `/de/produkt/ecoflow-ocean-2-hd-p3-5k0-s2-5-kw-three-phase-hybrid/` | crawl, sitemap | `/de/produkt/ecoflow-ocean-2-hd-p3-5k0-s2-5-kw-dreiphasiger-hybridwechselrichter/` |
| `/de/produkt/ecoflow-ocean-2-hd-p3-6k0-s2-6-kw-three-phase-hybrid-2026-flagship/` | crawl, sitemap | `/de/produkt/ecoflow-ocean-2-hd-p3-6k0-s2-6-kw-dreiphasiger-hybridwechselrichter-2026-spitzenmodell/` |
| `/de/produkt/ecoflow-ocean-2-hd-p3-8k0-s2-8-kw-three-phase-hybrid-2026-flagship/` | crawl, sitemap | `/de/produkt/ecoflow-ocean-2-hd-p3-8k0-s2-8-kw-dreiphasiger-hybridwechselrichter-2026-spitzenmodell/` |
| `/de/produkt/ecoflow-ocean-2-lfp-battery-base/` | crawl | `/de/produkt/ecoflow-ocean-2-lfp-batteriesockel/` |
| `/de/produkt/goodwe-esa-gw10k-eha-g20-10-kw-single-phase-power-module/` | crawl, sitemap | `/de/produkt/goodwe-esa-gw10k-eha-g20-10-kw-einphasiges-leistungsmodul/` |
| `/de/produkt/goodwe-esa-gw10k-eta-g20-10-kw-three-phase-all-in-one/` | crawl, sitemap | `/de/produkt/goodwe-esa-gw10k-eta-g20-10-kw-dreiphasiges-komplettsystem/` |
| `/de/produkt/goodwe-esa-gw125-261-esa-lcn-g10/` | crawl, sitemap | `/de/produkt/goodwe-esa-gw125-261-esa-lcn-g10/` |
| `/de/produkt/goodwe-esa-gw12k-eta-g20-12-kw-three-phase-all-in-one/` | crawl, sitemap | `/de/produkt/goodwe-esa-gw12k-eta-g20-12-kw-dreiphasiges-komplettsystem/` |
| `/de/produkt/goodwe-esa-gw15k-eta-g20-15-kw-three-phase-all-in-one/` | crawl, sitemap | `/de/produkt/goodwe-esa-gw15k-eta-g20-15-kw-dreiphasiges-komplettsystem/` |
| `/de/produkt/goodwe-esa-gw20k-eta-g20-20-kw-three-phase-power-module/` | crawl, sitemap | `/de/produkt/goodwe-esa-gw20k-eta-g20-20-kw-dreiphasiges-leistungsmodul/` |
| `/de/produkt/goodwe-esa-gw25k-eta-g20-25-kw-three-phase-power-module/` | crawl, sitemap | `/de/produkt/goodwe-esa-gw25k-eta-g20-25-kw-dreiphasiges-leistungsmodul/` |
| `/de/produkt/goodwe-esa-gw29-999k-eta-g20-29-999-kw-three-phase-power-module/` | crawl, sitemap | `/de/produkt/goodwe-esa-gw29-999k-eta-g20-29-999-kw-dreiphasiges-leistungsmodul/` |
| `/de/produkt/goodwe-esa-gw3-6k-eha-g20-3-6-kw-single-phase-power-module/` | crawl, sitemap | `/de/produkt/goodwe-esa-gw3-6k-eha-g20-3-6-kw-einphasiges-leistungsmodul/` |
| `/de/produkt/goodwe-esa-gw30k-eta-g20-30-kw-three-phase-power-module/` | crawl, sitemap | `/de/produkt/goodwe-esa-gw30k-eta-g20-30-kw-dreiphasiges-leistungsmodul/` |
| `/de/produkt/goodwe-esa-gw3k-eha-g20-3-kw-single-phase-power-module/` | crawl, sitemap | `/de/produkt/goodwe-esa-gw3k-eha-g20-3-kw-einphasiges-leistungsmodul/` |
| `/de/produkt/goodwe-esa-gw5k-eha-g20-5-kw-single-phase-power-module/` | crawl, sitemap | `/de/produkt/goodwe-esa-gw5k-eha-g20-5-kw-einphasiges-leistungsmodul/` |
| `/de/produkt/goodwe-esa-gw5k-eta-g20-5-kw-three-phase-power-module/` | crawl, sitemap | `/de/produkt/goodwe-esa-gw5k-eta-g20-5-kw-dreiphasiges-leistungsmodul/` |
| `/de/produkt/goodwe-esa-gw6k-eha-g20-6-kw-single-phase-power-module/` | crawl, sitemap | `/de/produkt/goodwe-esa-gw6k-eha-g20-6-kw-einphasiges-leistungsmodul/` |
| `/de/produkt/goodwe-esa-gw6k-eta-g20-6-kw-three-phase-power-module/` | crawl, sitemap | `/de/produkt/goodwe-esa-gw6k-eta-g20-6-kw-dreiphasiges-leistungsmodul/` |
| `/de/produkt/goodwe-esa-gw8k-eha-g20-8-kw-single-phase-power-module/` | crawl, sitemap | `/de/produkt/goodwe-esa-gw8k-eha-g20-8-kw-einphasiges-leistungsmodul/` |
| `/de/produkt/goodwe-esa-gw8k-eta-g20-8-kw-three-phase-all-in-one/` | crawl, sitemap | `/de/produkt/goodwe-esa-gw8k-eta-g20-8-kw-dreiphasiges-komplettsystem/` |
| `/de/produkt/goodwe-esa-gw9-999k-eta-g20-9-999-kw-three-phase-power-module/` | crawl, sitemap | `/de/produkt/goodwe-esa-gw9-999k-eta-g20-9-999-kw-dreiphasiges-leistungsmodul/` |
| `/de/produkt/goodwe-etr-125-kw-ci-three-phase-hybrid-inverter-1000v/` | crawl, sitemap | `/de/produkt/goodwe-etr-125-kw-ci-dreiphasiger-hybridwechselrichter-1000v/` |
| `/de/produkt/goodwe-ezmanager3000-hems-gateway/` | crawl, sitemap | `/de/produkt/goodwe-ezmanager3000-hems-kommunikationsschnittstelle/` |
| `/de/produkt/goodwe-gm330/` | crawl, sitemap | `/de/produkt/goodwe-gm330/` |
| `/de/produkt/goodwe-gmk330/` | crawl, sitemap | `/de/produkt/goodwe-gmk330/` |
| `/de/produkt/goodwe-gw100k-et-g10/` | crawl, sitemap | `/de/produkt/goodwe-gw100k-et-g10/` |
| `/de/produkt/goodwe-gw100k-etr-g10-100-kw-three-phase-hybrid-inverter/` | crawl, sitemap | `/de/produkt/goodwe-gw100k-etr-g10-100-kw-dreiphasiger-hybridwechselrichter/` |
| `/de/produkt/goodwe-gw110k-etr-g10-110-kw-three-phase-hybrid-inverter/` | crawl, sitemap | `/de/produkt/goodwe-gw110k-etr-g10-110-kw-dreiphasiger-hybridwechselrichter/` |
| `/de/produkt/goodwe-gw112-6-bat-ac-g10/` | crawl, sitemap | `/de/produkt/goodwe-gw112-6-bat-ac-g10/` |
| `/de/produkt/goodwe-gw124-99k-etr-g10-124-99-kw-three-phase-hybrid-inverter/` | crawl, sitemap | `/de/produkt/goodwe-gw124-99k-etr-g10-124-99-kw-dreiphasiger-hybridwechselrichter/` |
| `/de/produkt/goodwe-gw125k-sts-g10/` | crawl, sitemap | `/de/produkt/goodwe-gw125k-sts-g10/` |
| `/de/produkt/goodwe-gw208-9-bat-lc-g10/` | crawl, sitemap | `/de/produkt/goodwe-gw208-9-bat-lc-g10/` |
| `/de/produkt/goodwe-gw208-9-bat-lcd-g10/` | crawl, sitemap | `/de/produkt/goodwe-gw208-9-bat-lcd-g10/` |
| `/de/produkt/goodwe-gw261-2-bat-lcd-g10/` | crawl, sitemap | `/de/produkt/goodwe-gw261-2-bat-lcd-g10/` |
| `/de/produkt/goodwe-gw30k-sts-g10/` | crawl, sitemap | `/de/produkt/goodwe-gw30k-sts-g10/` |
| `/de/produkt/goodwe-gw5-1-bat-d-g20-esa-battery-module-5-12-kwh/` | crawl, sitemap | `/de/produkt/goodwe-gw5-1-bat-d-g20-esa-batteriemodul-5-12-kwh/` |
| `/de/produkt/goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh/` | crawl, sitemap | `/de/produkt/goodwe-gw5-1-bat-d-g21-esa-batteriemodul-5-12-kwh/` |
| `/de/produkt/goodwe-gw6-0-bat-d-g20-esa-battery-module-6-0-kwh/` | crawl, sitemap | `/de/produkt/goodwe-gw6-0-bat-d-g20-esa-batteriemodul-6-0-kwh/` |
| `/de/produkt/goodwe-gw60k-sts-g10/` | crawl, sitemap | `/de/produkt/goodwe-gw60k-sts-g10/` |
| `/de/produkt/goodwe-gw61-4-bat-ac-g10/` | crawl, sitemap | `/de/produkt/goodwe-gw61-4-bat-ac-g10/` |
| `/de/produkt/goodwe-gw75k-et-g10/` | crawl, sitemap | `/de/produkt/goodwe-gw75k-et-g10/` |
| `/de/produkt/goodwe-gw8-3-bat-d-g20-esa-battery-module-8-32-kwh/` | crawl, sitemap | `/de/produkt/goodwe-gw8-3-bat-d-g20-esa-batteriemodul-8-32-kwh/` |
| `/de/produkt/goodwe-gw8-3-bat-d-g21-esa-battery-module-8-32-kwh/` | crawl, sitemap | `/de/produkt/goodwe-gw8-3-bat-d-g21-esa-batteriemodul-8-32-kwh/` |
| `/de/produkt/goodwe-gw80k-et-g10/` | crawl, sitemap | `/de/produkt/goodwe-gw80k-et-g10/` |
| `/de/produkt/goodwe-gw80k-etr-g10-80-kw-three-phase-hybrid-inverter/` | crawl, sitemap | `/de/produkt/goodwe-gw80k-etr-g10-80-kw-dreiphasiger-hybridwechselrichter/` |
| `/de/produkt/goodwe-gw9-0-bat-d-g20-esa-battery-module-9-0-kwh/` | crawl, sitemap | `/de/produkt/goodwe-gw9-0-bat-d-g20-esa-batteriemodul-9-0-kwh/` |
| `/de/produkt/goodwe-gw99-99k-et-g10/` | crawl, sitemap | `/de/produkt/goodwe-gw99-99k-et-g10/` |
| `/de/produkt/goodwe-gw99-99k-etr-g10-99-99-kw-three-phase-hybrid-inverter/` | crawl, sitemap | `/de/produkt/goodwe-gw99-99k-etr-g10-99-99-kw-dreiphasiger-hybridwechselrichter/` |
| `/de/produkt/goodwe-hca-g2-gw11k-hca-20-11-kw-three-phase-ev-charger/` | crawl, sitemap | `/de/produkt/goodwe-hca-g2-gw11k-hca-20-11-kw-dreiphasige-ladestation/` |
| `/de/produkt/goodwe-hca-gw22k-hca-22-kw-three-phase-ev-charger/` | crawl, sitemap | `/de/produkt/goodwe-hca-gw22k-hca-22-kw-dreiphasige-ladestation/` |
| `/de/produkt/goodwe-hca-gw7k-hca-7-kw-single-phase-ev-charger/` | crawl, sitemap | `/de/produkt/goodwe-hca-gw7k-hca-7-kw-einphasige-ladestation/` |
| `/de/produkt/goodwe-sec3000c-smart-energy-controller/` | crawl, sitemap | `/de/produkt/goodwe-sec3000c-intelligente-energiesteuerung/` |
| `/de/produkt/pylontech-optim-us-l260-omni/` | crawl, sitemap | `/de/produkt/pylontech-optim-us-l260-omni/` |
| `/de/produkt/saj-ats1-t63-a/` | crawl, sitemap | `/de/produkt/saj-ats1-t63-a/` |
| `/de/produkt/saj-b2-10-0-hv1/` | crawl, sitemap | `/de/produkt/saj-b2-10-0-hv1/` |
| `/de/produkt/saj-b2-15-0-hv1/` | crawl, sitemap | `/de/produkt/saj-b2-15-0-hv1/` |
| `/de/produkt/saj-b2-20-0-hv1/` | crawl, sitemap | `/de/produkt/saj-b2-20-0-hv1/` |
| `/de/produkt/saj-b2-25-0-hv1/` | crawl, sitemap | `/de/produkt/saj-b2-25-0-hv1/` |
| `/de/produkt/saj-b2-5-0-hv1/` | crawl, sitemap | `/de/produkt/saj-b2-5-0-hv1/` |
| `/de/produkt/saj-bc2-hv1/` | crawl, sitemap | `/de/produkt/saj-bc2-hv1/` |
| `/de/produkt/saj-bu2-5-0-hv1/` | crawl, sitemap | `/de/produkt/saj-bu2-5-0-hv1/` |
| `/de/produkt/saj-bu3-5-0-tv2-pro/` | crawl, sitemap | `/de/produkt/saj-bu3-5-0-tv2-pro/` |
| `/de/produkt/saj-cb2-100-3-hv5/` | crawl, sitemap | `/de/produkt/saj-cb2-100-3-hv5/` |
| `/de/produkt/saj-cb2-57-3-hv5/` | crawl, sitemap | `/de/produkt/saj-cb2-57-3-hv5/` |
| `/de/produkt/saj-cb2-71-6-hv5/` | crawl, sitemap | `/de/produkt/saj-cb2-71-6-hv5/` |
| `/de/produkt/saj-cb2-85-9-hv5/` | crawl, sitemap | `/de/produkt/saj-cb2-85-9-hv5/` |
| `/de/produkt/saj-chs2-29-9k-t4-x/` | crawl, sitemap | `/de/produkt/saj-chs2-29-9k-t4-x/` |
| `/de/produkt/saj-chs2-30k-t4-x/` | crawl, sitemap | `/de/produkt/saj-chs2-30k-t4-x/` |
| `/de/produkt/saj-chs2-50k-t6-x/` | crawl, sitemap | `/de/produkt/saj-chs2-50k-t6-x/` |
| `/de/produkt/saj-emanager-c1-pro/` | crawl, sitemap | `/de/produkt/saj-emanager-c1-pro/` |
| `/de/produkt/saj-emanager-emanager-5-0-residential-energy-manager/` | crawl, sitemap | `/de/produkt/saj-emanager-emanager-5-0-heim-energiemanager/` |
| `/de/produkt/saj-esolar-aio3-data-collector-wifi-lan-bluetooth/` | crawl, sitemap | `/de/produkt/saj-esolar-aio3-datensammler-wifi-lan-bluetooth/` |
| `/de/produkt/saj-h2-10k-t3/` | crawl, sitemap | `/de/produkt/saj-h2-10k-t3/` |
| `/de/produkt/saj-h2-12k-t3/` | crawl, sitemap | `/de/produkt/saj-h2-12k-t3/` |
| `/de/produkt/saj-h2-15k-t3/` | crawl, sitemap | `/de/produkt/saj-h2-15k-t3/` |
| `/de/produkt/saj-h2-20k-t3/` | crawl, sitemap | `/de/produkt/saj-h2-20k-t3/` |
| `/de/produkt/saj-h2-25k-t3/` | crawl, sitemap | `/de/produkt/saj-h2-25k-t3/` |
| `/de/produkt/saj-h2-30k-t3-de/` | crawl, sitemap | `/de/produkt/saj-h2-30k-t3-de/` |
| `/de/produkt/saj-hs2-10k-t2-x/` | crawl, sitemap | `/de/produkt/saj-hs2-10k-t2-x/` |
| `/de/produkt/saj-hs2-5k-t2-x/` | crawl, sitemap | `/de/produkt/saj-hs2-5k-t2-x/` |
| `/de/produkt/saj-hs2-6k-t2-x/` | crawl, sitemap | `/de/produkt/saj-hs2-6k-t2-x/` |
| `/de/produkt/saj-hs2-8k-t2-x/` | crawl, sitemap | `/de/produkt/saj-hs2-8k-t2-x/` |
| `/de/produkt/saj-hs3-10k-t2-w-p/` | crawl, sitemap | `/de/produkt/saj-hs3-10k-t2-w-p/` |
| `/de/produkt/saj-hs3-12k-t2-w-p/` | crawl, sitemap | `/de/produkt/saj-hs3-12k-t2-w-p/` |
| `/de/produkt/saj-hs3-5k-t2-w-p/` | crawl, sitemap | `/de/produkt/saj-hs3-5k-t2-w-p/` |
| `/de/produkt/saj-hs3-6k-t2-w-p/` | crawl, sitemap | `/de/produkt/saj-hs3-6k-t2-w-p/` |
| `/de/produkt/saj-hs3-8k-t2-w-p/` | crawl, sitemap | `/de/produkt/saj-hs3-8k-t2-w-p/` |
| `/de/produkte/` | crawl, sitemap | `/de/produkte/` |
| `/de/produkte/page/2/` | crawl | `/de/produkte/seite/2/` |
| `/de/produkte/page/3/` | crawl | `/de/produkte/seite/3/` |
| `/de/produkte/page/4/` | crawl | `/de/produkte/seite/4/` |
| `/de/produkte/page/5/` | crawl | `/de/produkte/seite/5/` |
| `/de/produkte/page/6/` | crawl | `/de/produkte/seite/6/` |
| `/de/produkte/page/7/` | crawl | `/de/produkte/seite/7/` |
| `/de/proforma-anfrage/` | crawl, sitemap | `/de/proforma-anfrage/` |
| `/de/rueckgabe-erstattung/` | crawl, sitemap | `/de/rueckgabe-erstattung/` |
| `/de/service-support/` | crawl, sitemap | `/de/kundendienst/` |
| `/de/solar-speicher-inbetriebnahme-checkliste/` | crawl, sitemap | `/de/solar-speicher-inbetriebnahme-checkliste/` |
| `/de/ueber-uns/` | crawl, sitemap | `/de/ueber-uns/` |
| `/de/ueber-uns/leistungsfaehigkeit/` | crawl, sitemap | `/de/ueber-uns/leistungsfaehigkeit/` |
| `/de/verkaufsbedingungen/` | crawl, sitemap | `/de/verkaufsbedingungen/` |
| `/de/warenkorb/` | crawl, sitemap | `/de/loesungsentwurf/` |
