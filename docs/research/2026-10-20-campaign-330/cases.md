# #330 逐例表

全文（请求、SSE meta、回答块、工具调用）在 `~/de-linker-data/campaign-330/evidence/final.jsonl`；
本表是压缩视图。`hits` = 卡片/对比里的产品型号；`numbers` = 数字复核结论。

| case | class | lang | route | 请求（截断） | hits（型号） | numbers | 耗时 s | 判定 |
|---|---|---|---|---|---|---|---|---|
| A1-EN | misspelling | en | products | Do you have the SAJ H2-1OK-T3? Letter O, I never know. | H2-10K-T3 | 无未解释数字 | 6.8 | pass |
| A2-EN | misspelling | en | documents | Is the Goodwe GW1OK-ETA-G20 three-phase? | GW10K-ETA-G20 | 无未解释数字 | 12.3 | pass |
| A3-EN | misspelling | en | products | Looking for Ecoflow Ocean two batteries, the BD-8 one. | OCEAN 2 LFP Battery Base | 无未解释数字 | 22.5 | defect D7 |
| A4-EN | misspelling | en | documents | what is the output of the GooodWe GW5K-ETA-G2O? | GW5K-ETA-G20 | 待核→已核：全部可追溯 | 12.3 | pass |
| A5-EN | misspelling | en | products | hybrid inverter SAJJ HS3 1OK T2 W/G PX - do you carry it? | HS3-10K-T2-W/G-PX | 无未解释数字 | 5.3 | pass |
| A1-DE | misspelling | de | products | Haben Sie den SAJ H2-1OK-T3? Ich meine das Buchstaben-O. | H2-25K-T3, H2-30K-T3-DE, H2-15K-T3, H2-20K-T3, H2-10K-T3,… | 无未解释数字 | 8.3 | pass |
| A2-DE | misspelling | de | documents | Ist der Goodwe GW1OK-ETA-G20 dreiphasig? | — | 待核→已核：全部可追溯 | 7.9 | pass |
| A3-DE | misspelling | de | products | Ich suche die Pylontech L26O-OMNI, mit Buchstabe O geschrieben. | L260-OMNI | 无未解释数字 | 5.6 | pass |
| A4-DE | misspelling | de | documents | Welche Kapazität hat die Bu3-5.0-TV2-Pro Batterie? | — | 待核→已核：全部可追溯 | 20.0 | pass |
| A5-DE | misspelling | de | products | Gibt es den Hybridwechselrichter H2 15 K T3 von Saj? | H2-15K-T3 | 无未解释数字 | 3.1 | pass |
| B1-EN | emoji | en | model | 🔋⚡? | B2-5.0-HV1, BU2-5.0-HV1, EF BD-5-S2, GW6.0-BAT-D-G20, GW5… | 无未解释数字 | 9.5 | pass |
| B2-EN | emoji | en | model | 🔥🔥🔥👍 | — | 无未解释数字 | 4.1 | pass |
| B3-EN | emoji | en | products | Is the H2-10K-T3 in stock? 🙏🙏 | H2-10K-T3 | 无未解释数字 | 12.6 | pass |
| B4-EN | emoji | en | documents | ⚡ what is the AC output of the GW5K-ETA-G20? 📁 | GW5K-ETA-G20 | 无未解释数字 | 13.3 | pass |
| B5-EN | emoji | en | products | 🔍 ESA inverters 🔍 which ones do you have? | GW10K-ETA-G20, GW8K-ETA-G20, GW12K-ETA-G20, GW5K-ETA-G20,… | 无未解释数字 | 9.8 | pass |
| B1-DE | emoji | de | model | 🔋⚡? | BU2-5.0-HV1, BC2-HV1, BU3-5.0-TV2-PRO, GW5.1-BAT-D-G20, G… | 无未解释数字 | 11.5 | pass |
| B2-DE | emoji | de | model | 👍👍😅 | — | 无未解释数字 | 3.3 | pass |
| B3-DE | emoji | de | products | Ist der H2-10K-T3 auf Lager? 🙏🙏 | H2-10K-T3 | 无未解释数字 | 9.7 | pass |
| B4-DE | emoji | de | documents | 🔧 Welche Nennleistung hat der HS2-10K-T2-X? 🔧 | HS2-10K-T2-X | 待核→已核：全部可追溯 | 11.1 | pass |
| B5-DE | emoji | de | products | 🌊 OCEAN 2 🌊 dreiphasig 10 kW - welche Variante? | EF HD-P3-10K0-S2, EF HD-P1-10K0-S2 | 无未解释数字 | 23.9 | pass |
| C1-EN | overlong | en | parts | Here is my equipment list: ⏎ 1. GW3K-EHA-G20 x 2 ⏎ 2. GW5K-EH… | — | 无未解释数字 | 0.1 | pass |
| C2-EN | overlong | en | documents | What about the GW10K-ETA-G20? What about the GW10K-ETA-G20? W… | GW10K-ETA-G20 | 无未解释数字 | 11.6 | pass |
| C3-EN | overlong | en | documents | H2-10K-T3 specificationsspecificationsspecificationsspecifica… | H2-10K-T3 | 待核→已核：全部可追溯 | 19.1 | pass |
| C4-EN | overlong | en | products | Sorry for the long message. Sorry for the long message. Sorry… | B2-15.0-HV1 | 无未解释数字 | 4.7 | pass |
| C5-EN | overlong | en | parts | Parts list: ⏎ 1. GW3K-EHA-G20 x 2 ⏎ 2. GW5K-EHA-G20 x 2 ⏎ 3. … | — | 无未解释数字 | 0.0 | pass |
| C1-DE | overlong | de | parts | Meine Liste: ⏎ 1. GW3K-EHA-G20 x 2 ⏎ 2. GW5K-EHA-G20 x 2 ⏎ 3.… | — | 无未解释数字 | 0.0 | pass |
| C2-DE | overlong | de | documents | Wie ist das beim GW10K-ETA-G20? Wie ist das beim GW10K-ETA-G2… | — | 无未解释数字 | 8.1 | pass |
| C3-DE | overlong | de | model | DonaudampfschifffahrtsgesellschaftskapitänDonaudampfschifffah… | — | 无未解释数字 | 4.2 | pass |
| C4-DE | overlong | de | products | Entschuldigen Sie die lange Nachricht. Entschuldigen Sie die … | B2-15.0-HV1 | 无未解释数字 | 6.2 | pass |
| C5-DE | overlong | de | parts | Stückliste: ⏎ 1. GW3K-EHA-G20 x 2 ⏎ 2. GW5K-EHA-G20 x 2 ⏎ 3. … | — | 无未解释数字 | 0.0 | pass |
| D1-EN | mixed | en | documents | What is the Wirkungsgrad of the GW5K-ETA-G20 please? | — | 待核→已核：全部可追溯 | 9.0 | pass |
| D2-EN | mixed | en | products | Do you have Wechselrichter from SAJ in the h2 series? | H2-25K-T3, H2-30K-T3-DE, H2-15K-T3, H2-20K-T3, H2-10K-T3,… | 无未解释数字 | 3.4 | pass |
| D3-EN | mixed | en | pairing | Welche Batterien sind mit dem H2-10K-T3 kompatibel? | B2-5.0-HV1, B2-10.0-HV1, B2-15.0-HV1, B2-20.0-HV1, B2-25.… | 无未解释数字 | 6.7 | pass |
| D4-EN | mixed | en | products | I need a Speicher for my 10 kWp roof, maybe Goodwe? | GW6.0-BAT-D-G20, GW9.0-BAT-D-G20, GW5.1-BAT-D-G20, GW8.3-… | 无未解释数字 | 17.5 | pass |
| D5-EN | mixed | en | products | Ich brauche an inverter that is dreiphasig, around 10 kW. | HS2-8K-T2-X, GW10K-ETA-G20, GW8K-ETA-G20, GW12K-ETA-G20, … | 无未解释数字 | 6.3 | pass |
| D1-DE | mixed | de | pairing | Welche battery passt zum H2-10K-T3? | B2-5.0-HV1, B2-10.0-HV1, B2-15.0-HV1, B2-20.0-HV1, B2-25.… | 无未解释数字 | 18.8 | pass |
| D2-DE | mixed | de | products | Gibt es die GW5.1-BAT-D-G20 als single-phase Variante? | GW5.1-BAT-D-G20 | 无未解释数字 | 8.4 | pass |
| D3-DE | mixed | de | pairing | Which batteries are compatible with the H2-10K-T3? | B2-5.0-HV1, B2-10.0-HV1, B2-15.0-HV1, B2-20.0-HV1, B2-25.… | 无未解释数字 | 19.5 | pass |
| D4-DE | mixed | de | products | Ich suche a hybrid inverter with 10 kW, dreiphasig. | GW10K-ETA-G20, GW8K-ETA-G20, GW12K-ETA-G20, GW9.999K-ETA-G20 | 待核→已核：全部可追溯 | 11.6 | pass |
| D5-DE | mixed | de | documents | Was ist der efficiency vom HS2-10K-T2-X? | — | 待核→已核：全部可追溯 | 10.8 | pass |
| E1-EN | case-variants | en | documents | is the gw10k eta g20 single-phase? | GW10K-ETA-G20 | 无未解释数字 | 8.2 | pass |
| E2-EN | case-variants | en | products | Do you have Gw10k-Eta-G20 in stock? | GW10K-ETA-G20 | 无未解释数字 | 9.4 | pass |
| E3-EN | case-variants | en | documents | H210KT3 - what is the AC output? | H2-10K-T3 | 待核→已核：全部可追溯 | 16.8 | pass |
| E4-EN | case-variants | en | products | h2 10k t3 availability please | H2-10K-T3 | 无未解释数字 | 9.6 | pass |
| E5-EN | case-variants | en | products | Tell me about gw 5.1 bat d g20 | GW5.1-BAT-D-G20 | 待核→已核：全部可追溯 | 14.6 | pass |
| E6-EN | case-variants | en | products | GOODWE inverters - which GOODWE models do you carry? | GW3K-EHA-G20, GW3.6K-EHA-G20, GW5K-EHA-G20, GW6K-EHA-G20,… | 无未解释数字 | 3.8 | pass |
| E1-DE | case-variants | de | documents | ist der gw10k eta g20 dreiphasig? | GW10K-ETA-G20 | 无未解释数字 | 6.9 | pass |
| E2-DE | case-variants | de | documents | H210KT3 - welche Nennleistung? | H2-10K-T3 | 待核→已核：全部可追溯 | 8.6 | pass |
| E3-DE | case-variants | de | products | Haben Sie GW5,1-BAT-D-G20 auf Lager? | GW5.1-BAT-D-G20 | 无未解释数字 | 10.7 | pass |
| E4-DE | case-variants | de | products | saj hs2 5k t2 x verfügbar? | HS2-5K-T2-X | 无未解释数字 | 10.4 | pass |
| E5-DE | case-variants | de | products | Zeigen Sie mir GOODWE GW25K-ETA-G20 | GW25K-ETA-G20 | 无未解释数字 | 3.6 | pass |
| F1-EN | brand-conflict | en | products | Is the SAJ GW10K-ETA-G20 in stock? | — | 无未解释数字 | 5.4 | defect D1 |
| F2-EN | brand-conflict | en | products | Do you have the Trina Solar H2-10K-T3? | H2-10K-T3 | 无未解释数字 | 4.7 | pass |
| F3-EN | brand-conflict | en | products | GoodWe H2-15K-T3 - is that one of yours? | H2-15K-T3 | 无未解释数字 | 10.3 | pass |
| F4-EN | brand-conflict | en | products | EcoFlow GW5K-ETA-G20 availability? | GW5K-ETA-G20 | 无未解释数字 | 13.2 | pass |
| F5-EN | brand-conflict | en | pairing | Does the SAJ B2-5.0-HV1 battery work with the GoodWe GW5K-ETA… | — | 无未解释数字 | 4.1 | pass |
| F1-DE | brand-conflict | de | products | Haben Sie den SAJ GW10K-ETA-G20? | HS2-10K-T2-X, GW10K-ETA-G20 | 无未解释数字 | 7.8 | pass |
| F2-DE | brand-conflict | de | products | Gibt es den Trina Solar H2-10K-T3 bei Ihnen? | H2-10K-T3 | 无未解释数字 | 4.9 | pass |
| F3-DE | brand-conflict | de | products | Ist der GoodWe H2-15K-T3 von euch? | GW10K-ETA-G20, GW8K-ETA-G20, GW12K-ETA-G20, GW5K-ETA-G20,… | 无未解释数字 | 8.2 | pass |
| F4-DE | brand-conflict | de | products | EcoFlow GW5K-ETA-G20 - lieferbar? | — | 无未解释数字 | 11.2 | defect D5 |
| F5-DE | brand-conflict | de | pairing | Passt die SAJ B2-5.0-HV1 Batterie zum GoodWe GW5K-ETA-G20 Wec… | B2-5.0-HV1, GW5K-ETA-G20 | 无未解释数字 | 10.7 | pass |
| G1-EN | fake-model | en | model | Do you have the GW50K-ETA-G20 in stock? | — | 无未解释数字 | 7.3 | defect D1 |
| G2-EN | fake-model | en | products | Is the SAJ H2-35K-T3 available? | H2-25K-T3, H2-30K-T3-DE, H2-15K-T3, H2-20K-T3, H2-10K-T3,… | 无未解释数字 | 6.7 | pass |
| G3-EN | fake-model | en | products | I need the SAJ R5-8K-T3 hybrid inverter, 8 kW. | HS2-10K-T2-X, HS2-6K-T2-X, HS2-8K-T2-X, HS3-6K-T2-W/G-PX,… | 无未解释数字 | 9.1 | pass |
| G4-EN | fake-model | en | products | Can you quote 20 pieces of DLK-SAJ-CHS2-75K-T8-X? | CHS2-29.9K-T4-X, CHS2-30K-T4-X, CHS2-50K-T6-X | 无未解释数字 | 16.4 | pass |
| G5-EN | fake-model | en | products | Do you carry the EcoFlow OCEAN 3 HD-P3-20K0-S2? | OCEAN 2 LFP Battery Base | 无未解释数字 | 17.8 | defect D4 |
| G1-DE | fake-model | de | model | Haben Sie den GW50K-ETA-G20 auf Lager? | — | 无未解释数字 | 4.7 | defect D1 |
| G2-DE | fake-model | de | products | Ist der SAJ H2-35K-T3 verfügbar? | H2-25K-T3, H2-30K-T3-DE, H2-15K-T3, H2-20K-T3, H2-10K-T3,… | 无未解释数字 | 9.0 | pass |
| G3-DE | fake-model | de | products | Ich brauche den SAJ R5-8K-T3 Hybridwechselrichter mit 8 kW. | HS2-5K-T2-X | 无未解释数字 | 11.7 | pass |
| G4-DE | fake-model | de | products | Können Sie 20 Stück DLK-SAJ-CHS2-75K-T8-X anbieten? | ATS1-T63-A, BU2-5.0-HV1, BC2-HV1, eSolar AIO3, eManager, … | 无未解释数字 | 6.8 | pass |
| G5-DE | fake-model | de | products | Führen Sie den EcoFlow OCEAN 3 HD-P3-20K0-S2? | EF HD-P1-6K0-S2, EF HD-P1-8K0-S2, EF HD-P1-10K0-S2, EF HD… | 无未解释数字 | 28.5 | pass |
| H1-EN | multi-product | en | compare | Compare the H2-10K-T3, HS2-10K-T2-X and GW10K-ETA-G20 for me. | HS2-10K-T2-X, GW10K-ETA-G20, H2-10K-T3 | 待核→已核：全部可追溯 | 5.1 | pass |
| H2-EN | multi-product | en | documents | Are the GW5K-ETA-G20, GW6K-ETA-G20 and GW8K-ETA-G20 all three… | — | 无未解释数字 | 8.1 | pass |
| H3-EN | multi-product | en | compare | Which of B2-5.0-HV1, B2-10.0-HV1 and B2-15.0-HV1 has the most… | B2-5.0-HV1, B2-10.0-HV1, B2-15.0-HV1 | 无未解释数字 | 3.1 | pass |
| H4-EN | multi-product | en | products | Do you have HS3-5K-T2-W/G-PX, HS3-8K-T2-W/G-PX and HS3-12K-T2… | HS3-5K-T2-W/G-PX | 无未解释数字 | 8.8 | defect D2 |
| H5-EN | multi-product | en | products | Show me GW3K-EHA-G20, GW5K-EHA-G20, GW8K-EHA-G20, GW10K-EHA-G… | GW3K-EHA-G20, GW5K-EHA-G20, GW8K-EHA-G20, GW10K-EHA-G20 | 无未解释数字 | 8.1 | pass |
| H1-DE | multi-product | de | compare | Vergleichen Sie H2-10K-T3, HS2-10K-T2-X und GW10K-ETA-G20. | HS2-10K-T2-X, GW10K-ETA-G20, H2-10K-T3 | 待核→已核：全部可追溯 | 6.9 | pass |
| H2-DE | multi-product | de | documents | Sind GW5K-ETA-G20, GW6K-ETA-G20 und GW8K-ETA-G20 alle dreipha… | — | 无未解释数字 | 9.4 | pass |
| H3-DE | multi-product | de | compare | Welche von B2-5.0-HV1, B2-10.0-HV1 und B2-15.0-HV1 hat die me… | B2-5.0-HV1, B2-10.0-HV1, B2-15.0-HV1 | 无未解释数字 | 3.5 | pass |
| H4-DE | multi-product | de | products | Haben Sie HS3-5K-T2-W/G-PX, HS3-8K-T2-W/G-PX und HS3-12K-T2-W… | HS3-12K-T2-W/G-PX, HS3-8K-T2-W/G-PX, HS3-5K-T2-W/G-PX | 无未解释数字 | 12.4 | pass |
| H5-DE | multi-product | de | products | Zeigen Sie mir GW3K-EHA-G20, GW5K-EHA-G20, GW8K-EHA-G20, GW10… | GW3K-EHA-G20, GW5K-EHA-G20, GW8K-EHA-G20, GW10K-EHA-G20 | 无未解释数字 | 6.8 | pass |
| I1-EN | units | en | products | I need a 10 kWh inverter. | EF HD-P1-3K-S2, EF HD-P1-3K68-S2, EF HD-P1-4K6-S2, EF HD-… | 无未解释数字 | 10.2 | pass |
| I2-EN | units | en | model | Which battery gives me 10 kW of storage? | B2-10.0-HV1, BC2-HV1, GW9.0-BAT-D-G20, GW8.3-BAT-D-G20, G… | 待核→已核：全部可追溯 | 14.5 | pass |
| I3-EN | units | en | sizing | I have 8 kWp on the roof and use 4000 kWh a year, three-phase. | — | 无未解释数字 | 4.1 | pass |
| I4-EN | units | en | products | I need a single-phase 10 kW hybrid inverter. | GW8K-EHA-G20, GW10K-EHA-G20 | 无未解释数字 | 7.5 | pass |
| I5-EN | units | en | sizing | My PV is 12 kWp and I want 15 kWh of battery storage. | — | 无未解释数字 | 3.3 | pass |
| I6-EN | units | en | documents | Does the CHS2-29.9K-T4-X output 29.9 kW or 29.999 kW? | CHS2-29.9K-T4-X | 待核→已核：全部可追溯 | 9.6 | pass |
| I1-DE | units | de | products | Ich brauche einen 10-kWh-Wechselrichter. | EF HD-P1-3K-S2, EF HD-P1-3K68-S2, EF HD-P1-4K6-S2, EF HD-… | 无未解释数字 | 11.3 | pass |
| I2-DE | units | de | model | Welche Batterie liefert mir 10 kW Speicher? | B2-10.0-HV1, BC2-HV1 | 无未解释数字 | 9.5 | pass |
| I3-DE | units | de | sizing | Ich habe 8 kWp auf dem Dach und verbrauche 4.000 kWh pro Jahr… | — | 无未解释数字 | 2.9 | pass |
| I4-DE | units | de | model | Ich brauche einen einphasigen 10-kW-Hybridwechselrichter. | GW10K-EHA-G20 | 无未解释数字 | 23.7 | pass |
| I5-DE | units | de | model | Meine PV-Anlage hat 12 kWp und ich möchte 15 kWh Batteriespei… | — | 无未解释数字 | 7.0 | defect D3 |
| I6-DE | units | de | documents | Gibt der CHS2-29.9K-T4-X 29,9 kW oder 29,999 kW ab? | — | 待核→已核：全部可追溯 | 27.3 | pass |
| J1-EN | contradiction | en | products | I need a single-phase and three-phase 10 kW inverter at the s… | H2-10K-T3, GW10K-EHA-G20 | 无未解释数字 | 8.1 | pass |
| J2-EN | contradiction | en | sizing | I want a 10 kW system but my roof only fits 1 kW of PV. | — | 无未解释数字 | 5.6 | pass |
| J3-EN | contradiction | en | products | I want the GW10K-EHA-G20 but three-phase. | GW10K-ETA-G20 | 无未解释数字 | 5.0 | pass |
| J4-EN | contradiction | en | products | Please quote the three-phase GW5K-EHA-G20. | GW5K-EHA-G20 | 无未解释数字 | 15.1 | pass |
| J5-EN | contradiction | en | products | What is your smallest inverter with at least 30 kW? | GW80K-ET-G10, GW125K-ETR-G10, GW75K-ET-G10, GW80K-ETR-G10 | 无未解释数字 | 11.6 | defect D6 |
| J1-DE | contradiction | de | products | Ich brauche einen einphasigen und dreiphasigen 10-kW-Wechselr… | EF HD-P3-10K0-S2, GW10K-ETA-G20, EF HD-P1-10K0-S2, H2-10K… | 无未解释数字 | 23.3 | pass |
| J2-DE | contradiction | de | sizing | Ich möchte eine 10-kW-Anlage, aber auf mein Dach passen nur 1… | — | 无未解释数字 | 7.3 | pass |
| J3-DE | contradiction | de | products | Ich möchte den GW10K-EHA-G20, aber dreiphasig. | GW10K-ETA-G20, GW8K-ETA-G20, GW12K-ETA-G20, GW9.999K-ETA-G20 | 无未解释数字 | 9.4 | pass |
| J4-DE | contradiction | de | products | Bitte bieten Sie den dreiphasigen GW5K-EHA-G20 an. | GW5K-ETA-G20, GW5K-EHA-G20 | 无未解释数字 | 7.7 | pass |
| J5-DE | contradiction | de | products | Was ist Ihr kleinster Wechselrichter mit mindestens 30 kW? | GW30K-ETA-G20 | 待核→已核：全部可追溯 | 8.3 | pass |
| K1-EN | parts-boundary | en | parts | Here is my parts list. | — | 无未解释数字 | 1.5 | pass |
| K2-EN | parts-boundary | en | model | Please match this list. | — | 无未解释数字 | 6.1 | pass |
| K3-EN | parts-boundary | en | parts | Here is my parts list. | — | 无未解释数字 | 1.5 | pass |
| K4-EN | parts-boundary | en | parts | Please match this list. | — | 无未解释数字 | 0.0 | pass |
| K5-EN | parts-boundary | en | parts | Here is my parts list. | — | 待核→已核：全部可追溯 | 0.0 | pass |
| K6-EN | parts-boundary | en | model | Please match this list. | — | 无未解释数字 | 5.4 | pass |
| K7-EN | parts-boundary | en | model | Please match this list. | — | 无未解释数字 | 5.9 | pass |
| K8-DE | parts-boundary | de | parts | Hier meine Stückliste. | — | 无未解释数字 | 0.0 | pass |

`class` 缩写与 README 的十一类一致；defect 号对应 NOTES.md 的 D1–D7。
