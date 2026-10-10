# Spot-check 20 passed FAQ items

Pool: 168 passed. Sample indices: [0, 8, 16, 24, 32, 40, 48, 56, 64, 72, 80, 88, 96, 104, 112, 120, 128, 136, 144, 152].

## 1. `ecoflow-battery-stack-bridge` (3609)

- Q EN: Can one bridge join different battery models?
- Q DE: Darf eine Brücke zwei unterschiedliche Batteriemodelle verbinden?
- Cite: Battery Stack Bridge Installation Guide (EN) p.3
- URL: https://de-linker.com/wp-content/uploads/2026/08/ecoflow_battery-stack-bridge_install-guide_en_v1.0.pdf#page=3
- Verdict: **PASS**

No. Both battery units interconnected by this bracket must be of identical model specifications. The bracket is designed for the EcoFlow PowerOcean LFP Battery (EF BD-5.1-S1), the EcoFlow OCEAN 2 LFP Battery 5kWh (EF BD-5-S2) and the EcoFlow OCEAN 2 LFP Battery 8kWh (EF BD-8-S2).

Nein. Beide Batterieeinheiten, die mit dieser Halterung verbunden werden, müssen identische Modellspezifikationen aufweisen. Die Halterung ist für die EcoFlow PowerOcean LFP Battery (EF BD-5.1-S1), die EcoFlow OCEAN 2 LFP Battery 5kWh (EF BD-5-S2) und die EcoFlow OCEAN 2 LFP Battery 8kWh (EF BD-8-S2) ausgelegt.

## 2. `ecoflow-ocean-2-hd-p1-3k68-s2-3-68-kw-single-phase-hybrid` (6484)

- Q EN: Is the IOT dongle required?
- Q DE: Ist der IOT-Dongle Pflicht?
- Cite: OCEAN 2 Single-Phase Installation Guide V1.7 (DE) p.12
- URL: https://de-linker.com/wp-content/uploads/2026/10/ecoflow-ocean2-single-phase-installation-guide-de-v1-7.pdf#page=12
- Verdict: **PASS**

Yes. The EcoFlow IOT-Dongle ESS is listed as "Muss konfiguriert werden" (must be configured). The 4G dongle is listed separately as an option.

Ja. Der EcoFlow IOT-Dongle ESS ist mit "Muss konfiguriert werden" aufgeführt. Der 4G-Dongle ist separat als Option aufgeführt.

## 3. `ecoflow-ocean-2-hd-p1-5k75-s2-5-75-kw-single-phase-hybrid` (6487)

- Q EN: Is the IOT dongle required?
- Q DE: Ist der IOT-Dongle Pflicht?
- Cite: OCEAN 2 Single-Phase Installation Guide V1.7 (DE) p.12
- URL: https://de-linker.com/wp-content/uploads/2026/10/ecoflow-ocean2-single-phase-installation-guide-de-v1-7.pdf#page=12
- Verdict: **PASS**

Yes. The EcoFlow IOT-Dongle ESS is listed as "Muss konfiguriert werden" (must be configured) in the system overview and in the installation section. The 4G dongle is listed as an option.

Ja. Der EcoFlow IOT-Dongle ESS ist in der Systemübersicht und im Installationsabschnitt mit "Muss konfiguriert werden" angegeben. Der 4G-Dongle ist als Option aufgeführt.

## 4. `ecoflow-ocean-2-lfp-battery-base` (3608)

- Q EN: How many OCEAN 2 floor bases does one battery tower use?
- Q DE: Wie viele OCEAN-2-Bodensockel braucht ein Batterieturm?
- Cite: OCEAN 2 three-phase installation guide V1.5 (EN, DE, FR, IT, ES, NL, SV) p.11
- URL: https://de-linker.com/wp-content/uploads/2026/09/ecoflow-ocean2-p3-s2-installation-guide-v1-5.pdf#page=11
- Verdict: **PASS**

One battery tower uses one battery base. The installation guide lists the battery base as C1 ×1.

Ein Batterieturm verwendet einen Batteriesockel. Die Installationsanleitung führt den Batteriesockel als C1 ×1 auf.

## 5. `goodwe-esa-gw125-261-esa-lcn-g10` (6321)

- Q EN: Can the cabinet supply the site when the grid fails?
- Q DE: Kann der Schrank den Standort bei Netzausfall versorgen?
- Cite: GoodWe ESA 261 kWh microgrid user manual, V1.1 (EN) p.26
- URL: https://de-linker.com/wp-content/uploads/2026/10/GW_ESA-261kWh_Microgrid-User-Manual-EN_V1.1.pdf#page=26
- Verdict: **PASS**

Yes. Off-grid operation is supported. When the grid fails, the PCS controls the switching cabinet to disconnect from the grid and establishes AC voltage. The system switches to off-grid operation, and PV is connected to supply power to loads; the priority for supplying power to loads is PV > Energy Storage. When the grid recovers, the PCS issues a command to close the STS On/Off-grid transfer switch, and the system returns to grid-connected operation.

Ja. Der Inselbetrieb wird unterstützt. Bei Netzausfall steuert der PCS das Umschaltgehäuse, um vom Netz zu trennen, und baut AC-Spannung auf. Das System wechselt in den Inselbetrieb, und PV wird angeschlossen, um Lasten zu versorgen; die Priorität für die Versorgung der Lasten ist PV > Energiespeicher. Wenn das Netz wiederhergestellt ist, gibt der PCS einen Befehl zum Schließen des STS-On/Off-Grid-Umschalters, und das System kehrt in den netzgekoppelten Betrieb zurück.

## 6. `goodwe-esa-gw25k-eta-g20-25-kw-three-phase-power-module` (6516)

- Q EN: What backup rating does GW25K-ETA-G20 have?
- Q DE: Welche Notstromwerte hat der GW25K-ETA-G20?
- Cite: GoodWe ESA Series 5–30 kW datasheet (EN) p.2
- URL: https://de-linker.com/wp-content/uploads/2026/09/GW_ESA-5-30kW_Datasheet-EN.pdf#page=2
- Verdict: **PASS**

The GW25K-ETA-G20 is listed with a rated apparent power of 25 kVA on the AC side (back-up port).

Der GW25K-ETA-G20 ist auf der AC-Seite (Back-up-Port) mit einer Nennscheinleistung von 25 kVA angegeben.

## 7. `goodwe-esa-gw30k-eta-g20-30-kw-three-phase-power-module` (6518)

- Q EN: What backup rating does GW30K-ETA-G20 have?
- Q DE: Welche Notstromwerte hat der GW30K-ETA-G20?
- Cite: GoodWe ESA Series 5–30 kW user manual (EN, V1.5) p.306
- URL: https://de-linker.com/wp-content/uploads/2026/10/GW_ESA-5-30kW_User-Manual-EN_V1.5.pdf#page=306
- Verdict: **PASS**

On the AC side (Back-up Port) the rated apparent power is 30 kVA. The maximum apparent power is 33 kVA off-grid (45.0 kVA for 10 s) and 55.2 kVA on-grid.

Auf der AC-Seite (Back-up-Anschluss) beträgt die Nennscheinleistung 30 kVA. Die maximale Scheinleistung beträgt 33 kVA im Off-Grid-Betrieb (45,0 kVA für 10 s) und 55,2 kVA im On-Grid-Betrieb.

## 8. `goodwe-esa-gw6k-eha-g20-6-kw-single-phase-power-module` (6526)

- Q EN: What backup rating does GW6K-EHA-G20 have?
- Q DE: Welche Notstromwerte hat der GW6K-EHA-G20?
- Cite: GoodWe ESA Series 3–10 kW user manual (EN, V1.8) p.281
- URL: https://de-linker.com/wp-content/uploads/2026/10/GW_ESA-3-10kW_User-Manual-EN_V1.8.pdf#page=281
- Verdict: **PASS**

The GW6K-EHA-G20 has a nominal backup output apparent power of 6.0 kVA and a maximum backup output apparent power of 6.0 kVA (12.0 kVA for 10 s). The maximum backup output current is 27.3 A at 220 V, 26.1 A at 230 V, and 25 A at 240 V. The maximum bypass output apparent power is 12 kVA, with a maximum bypass output current of 50 A.

Der GW6K-EHA-G20 hat eine nominale Notstrom-Ausgangsscheinleistung von 6,0 kVA und eine maximale Notstrom-Ausgangsscheinleistung von 6,0 kVA (12,0 kVA für 10 s). Der maximale Notstrom-Ausgangsstrom beträgt 27,3 A bei 220 V, 26,1 A bei 230 V und 25 A bei 240 V. Die maximale Bypass-Ausgangsscheinleistung beträgt 12 kVA, der maximale Bypass-Ausgangsstrom 50 A.

## 9. `goodwe-esa-gw8k-eta-g20-8-kw-three-phase-all-in-one` (3583)

- Q EN: Which meter and CT arrangement must be planned for this inverter?
- Q DE: Welche Zähler- und Stromwandleranordnung ist für diesen Wechselrichter einzuplanen?
- Cite: GoodWe ESA Series 5–30 kW user manual (EN, V1.5) p.35
- URL: https://de-linker.com/wp-content/uploads/2026/10/GW_ESA-5-30kW_User-Manual-EN_V1.5.pdf#page=35
- Verdict: **PASS**

Use the built-in meter with the CT provided with the inverter. CT ratio: 120A:40mA. If the built-in meter of the inverter does not meet usage requirements, contact a dealer to purchase a GMK330 or GM330 Smart Meter. GMK330: CT is not replaceable; CT ratio: 120A:40mA. GM330: the CT can be purchased from GoodWe or purchased separately; CT ratio requirement: nA/5A, where nA is the CT primary input current with n ranging from 200 to 5000, and 5A is the CT secondary output current. If more than 2 inverters are paralleled, or the wire diameter or measuring range of the standard CT does not meet the total current requirements of the on-site parallel system, use the GM330 Smart Meter. In the whole-house backup power scenario, there is no need to connect additional meters or CTs; simply set the "Meter Type" to "Built-in CT, External No Meter No CT" in the App to achieve the Power Limit function.

Verwenden Sie den integrierten Zähler mit dem mitgelieferten CT zum Anschluss an den Wechselrichter. CT-Übersetzungsverhältnis: 120A:40mA. Wenn der integrierte Zähler des Wechselrichters für den Einsatz nicht ausreicht, können Sie über den Händler den intelligenten Zähler GMK330 oder GM330 erwerben. GMK330: CT nicht austauschbar, CT-Übersetzungsverhältnis 120A:40mA. GM330: Der CT kann von GoodWe oder selbst gekauft werden. Erforderliches CT-Übersetzungsverhältnis: nA/5A, wobei nA der Primärstrom des CT ist und der n-Bereich 200-5000 beträgt, und 5A der Sekundärstrom des CT ist. Wenn die Anzahl der parallel geschalteten Wechselrichter 2 übersteigt oder der Leiterquerschnitt oder Messbereich des Standard-CTs die Anforderungen an den gesamten Parallelstrom vor Ort nicht erfüllt, verwenden Sie den intelligenten Zähler GM330. Im Szenario mit Hausvollabsicherung müssen keine zusätzlichen Zähler oder CTs angeschlossen werden. Stellen Sie einfach den "Zählertyp" in der App auf "Integrierter CT, extern kein Zähler kein CT" ein, um die Power-Limit-Funktion zu erreichen.

## 10. `goodwe-gm330` (2394)

- Q EN: Are current transformers included with GM330?
- Q DE: Sind beim GM330 Stromwandler im Lieferumfang?
- Cite: GoodWe Smart Meter User Manual: GM330 / GMK330 / GMK360 (EN) p.8
- URL: https://de-linker.com/wp-content/uploads/2026/09/GW_Smart-Meter-EU_User-Manual-EN_V1.5.pdf#page=8
- Verdict: **PASS**

No. The deliverables list states GM330: CT x 0, while GMK330 ships with CT x 3 and GMK360 with CT x 6. The GM330 scope includes the smart meter, 2PIN, 6PIN and 7PIN communication terminals, an RS485 communication terminal, a 2PIN terminal and RJ45 terminal connector, a screwdriver, 6 PIN terminals and documents.

Nein. Die Lieferliste gibt für GM330 an: CT x 0, während GMK330 mit CT x 3 und GMK360 mit CT x 6 geliefert wird. Zum Lieferumfang des GM330 gehören der Smart Meter, 2PIN-, 6PIN- und 7PIN-Kommunikationsklemmen, eine RS485-Kommunikationsklemme, ein 2PIN-Klemmen- und RJ45-Klemmenstecker, ein Schraubendreher, 6 PIN-Klemmen und Dokumente.

## 11. `goodwe-gw124-99k-etr-g10-124-99-kw-three-phase-hybrid-inverter` (6511)

- Q EN: Is an external STS needed for the ETR backup path?
- Q DE: Ist für den ETR-Notstrompfad ein externer STS nötig?
- Cite: GoodWe ETR 50–125 kW User Manual (EN) p.57
- URL: https://de-linker.com/wp-content/uploads/2026/10/GW_ETR-50-125kW_User-Manual-EN_V1.0.pdf#page=57
- Verdict: **PASS**

Yes. The manual states that the inverter can only use the BACK-UP function when paired with STS. The datasheet footnote also states that the STS Box or STS Cabinet is needed. The inverter-to-STS communication cable is shipped with the unit.

Ja. Das Handbuch gibt an, dass der Wechselrichter die BACK-UP-Funktion nur in Verbindung mit STS nutzen kann. Die Datenblatt-Fußnote gibt ebenfalls an, dass die STS-Box oder der STS-Schrank benötigt wird. Das Kommunikationskabel vom Wechselrichter zum STS wird mit dem Gerät geliefert.

## 12. `goodwe-gw5-1-bat-d-g21-esa-battery-module-5-12-kwh` (6521)

- Q EN: How many modules in one column?
- Q DE: Wie viele Module in einer Säule?
- Cite: GoodWe ESA Series 5–30 kW user manual (EN, V1.5) p.80
- URL: https://de-linker.com/wp-content/uploads/2026/10/GW_ESA-5-30kW_User-Manual-EN_V1.5.pdf#page=80
- Verdict: **PASS**

A single column can stack up to 6 batteries. For more energy demand or other scenarios requiring capacity expansion, contact GoodWe or a dealer to purchase a battery expansion kit.

Eine einzelne Säule kann bis zu 6 Batterien stapeln. Bei höherem Energiebedarf oder anderen Szenarien, die eine Kapazitätserweiterung erfordern, wenden Sie sich an GoodWe oder einen Händler, um ein Batterieerweiterungsset zu erwerben.

## 13. `goodwe-gw80k-etr-g10-80-kw-three-phase-hybrid-inverter` (6507)

- Q EN: Which BAT-C cabinet is listed for GW80K-ETR-G10?
- Q DE: Welcher BAT-C-Schrank ist für GW80K-ETR-G10 gelistet?
- Cite: GoodWe ETR Series 80–125 kW Datasheet (EMEA, EN) p.1
- URL: https://de-linker.com/wp-content/uploads/2026/09/GW_ETR_Datasheet_EMEA-EN_V1.1.pdf#page=1
- Verdict: **PASS**

The datasheet lists the GoodWe BAT-C 261kWh battery system as compatible with the ETR series, which includes the GW80K-ETR-G10.

Das Datenblatt listet das GoodWe BAT-C 261kWh-Batteriesystem als kompatibel mit der ETR-Serie, zu der auch der GW80K-ETR-G10 gehört.

## 14. `goodwe-hca-g2-gw11k-hca-20-11-kw-three-phase-ev-charger` (3557)

- Q EN: What comes with the charger?
- Q DE: Was gehört zum Lieferumfang?
- Cite: GoodWe HCA G2 User Manual (EN) p.33
- URL: https://de-linker.com/wp-content/uploads/2026/09/GW_HCA-G2_User-Manual-EN.pdf#page=33
- Verdict: **PASS**

The scope of delivery includes: Charger x 1, AC connector x 1, Dummy socket x 1, fastening screws x 4, Expansion bolt x 4, RS485 communication connector x 1, LAN communication connector x 1, Screwdriver x 1, AC cable pin terminal x 2, RS485 cable pin terminal x 1, RFID card x 5, RJ45 terminal x 4, Waterproof rubber plug x 2, Documents x 1.

Zum Lieferumfang gehören: Charger x 1, AC connector x 1, Dummy socket x 1, Befestigungsschrauben x 4, Expansion bolt x 4, RS485 communication connector x 1, LAN communication connector x 1, Schraubendreher x 1, AC cable pin terminal x 2, RS485 cable pin terminal x 1, RFID card x 5, RJ45 terminal x 4, Waterproof rubber plug x 2, Documents x 1.

## 15. `goodwe-sec3000c-smart-energy-controller` (2409)

- Q EN: What sits inside the cabinet, and which CTs does the meter take?
- Q DE: Was steckt im Schrank, und welche Stromwandler braucht der Zähler?
- Cite: GoodWe SEC3000C User Manual (EN) p.155
- URL: https://de-linker.com/wp-content/uploads/2026/09/GW_SEC3000C_User-Manual-EN.pdf#page=155
- Verdict: **PASS**

The cabinet contains an EzLogger3000C datalogger, a 15-port switch, and a GM330 smart meter. The meter takes CTs with a ratio of nA/5A, where n is the CT primary side input current and ranges from 200 to 5000. The CT cable length should not exceed 30m.

Der Schrank enthält einen EzLogger3000C-Datenlogger, einen 15-Port-Switch und einen GM330-Smart-Meter. Der Zähler benötigt Stromwandler mit einem Verhältnis von nA/5A, wobei n der Primärstrom des Stromwandlers ist und von 200 bis 5000 reicht. Die Länge des Stromwandlerkabels sollte 30 m nicht überschreiten.

## 16. `saj-b2-15-0-hv1` (2068)

- Q EN: Where and how is the stack installed?
- Q DE: Wo und wie wird der Stapel montiert?
- Cite: SAJ B2 high-voltage battery, B2-5.0 to B2-25.0: user manual V1.2 (English) p.14
- URL: https://de-linker.com/wp-content/uploads/2026/10/B2-5.0-HV1-HV5-user-manual-EN-EU.pdf#page=14
- Verdict: **PASS**

The battery employs either ground mounting or wall mounting, and its position is determined by the drilled holes of the bracket. Mount vertically; never install the battery tilted forwards, sideways, horizontally or upside down. For wall mounting, a solid wall is recommended; cavity wall and timber wall are not allowed.

Der Akku wird entweder am Boden oder an der Wand montiert, die Position ergibt sich aus den Bohrlöchern der Halterung. Vertikal montieren; den Akku niemals nach vorne, seitlich, horizontal oder kopfüber geneigt installieren. Für die Wandmontage wird eine massive Wand empfohlen; Hohlraumwände und Holzwände sind für die Installation des Akkusystems nicht zulässig.

## 17. `saj-bu2-5-0-hv1` (2090)

- Q EN: Which systems use the BU2-5.0-HV1?
- Q DE: In welchen Systemen wird das BU2-5.0-HV1 eingesetzt?
- Cite: SAJ B2 high-voltage battery, B2-5.0 to B2-25.0: user manual V1.2 (English) p.5
- URL: https://de-linker.com/wp-content/uploads/2026/10/B2-5.0-HV1-HV5-user-manual-EN-EU.pdf#page=5
- Verdict: **PASS**

The BU2-5.0-HV1 is the battery module of the B2-5.0-HV1. The B2 battery can only be used as a set with SAJ's H2 high voltage series storage inverter.

Das BU2-5.0-HV1 ist das Akku-Modul des B2-5.0-HV1. Der Akku B2 kann nur als Satz mit dem Hochspannungs-Speicherwechselrichter der H2-Serie von SAJ verwendet werden.

## 18. `saj-cb2-85-9-hv5` (4105)

- Q EN: What are the dimensions and the weight of the cabinet?
- Q DE: Welche Abmessungen und welches Gewicht hat der Schrank?
- Cite: SAJ CHS2 30-50K datasheet with the CB2 battery table, English (covers the CB2-100.3-HV5) p.2
- URL: https://de-linker.com/wp-content/uploads/2026/10/SAJ_CHS2_30-50K_Datasheet_EN-BEU.pdf#page=2
- Verdict: **PASS**

The cabinet dimensions are 1980 mm (H) x 988 mm (W) x 1065 mm (D). The weight is 1255 kg for the 85.9 kWh model.

Die Abmessungen des Schranks betragen 1980 mm (H) x 988 mm (B) x 1065 mm (T). Das Gewicht beträgt 1255 kg für das Modell mit 85,9 kWh.

## 19. `saj-emanager-emanager-5-0-residential-energy-manager` (3618)

- Q EN: Which inverter firmware does the eManager need?
- Q DE: Welche Wechselrichter-Firmware braucht der eManager?
- Cite: SAJ eManager user manual (English) p.45
- URL: https://de-linker.com/wp-content/uploads/2026/08/saj_emanager_manual_en_v3.pdf#page=45
- Verdict: **PASS**

A firmware update is only applicable when the inverter firmware version is not compatible with the EMS firmware version. The manual lists the minimum DSP and ARM versions per inverter model, for example H2-(3K-6K)-S2: DSP V1.030, ARM V6.040; H2-(5K-10K)-T2: DSP V4.066, ARM V1.070; HS2-(5K-10K)-T2: DSP V4.066, ARM V1.070; HS2-(3K-6K)-S2: DSP V1.030, ARM V6.040; R6-(5K-10K)-(S2, S3): DSP V1.041, ARM V1.069; R6-(5K-15K)-T2: DSP V2.318, ARM V1.069; R6-(15K-50K)-(T2, T3, T4): DSP V2.580, ARM V6.196; R5-(0.7K-3K)-S1: DSP V1.234, ARM V3.100; R5-(3K-8K)-S2: DSP V1.524, ARM V3.100; H2-(10K-30K)-(T2, T3): DSP V3.061, ARM V8.035; HS3-(3K-6K)-S2: DSP V1.135, ARM V1.040; HS3-(5K-12K)-T2: DSP V2.103, ARM V2.030. Check whether your inverter firmware version (DSP version and ARM version) is earlier than the listed ones.

Ein Firmware-Update ist nur dann anwendbar, wenn die Wechselrichter-Firmware-Version nicht mit der EMS-Firmware-Version kompatibel ist. Das Handbuch nennt die Mindestversionen für DSP und ARM je Wechselrichtermodell, zum Beispiel H2-(3K-6K)-S2: DSP V1.030, ARM V6.040; H2-(5K-10K)-T2: DSP V4.066, ARM V1.070; HS2-(5K-10K)-T2: DSP V4.066, ARM V1.070; HS2-(3K-6K)-S2: DSP V1.030, ARM V6.040; R6-(5K-10K)-(S2, S3): DSP V1.041, ARM V1.069; R6-(5K-15K)-T2: DSP V2.318, ARM V1.069; R6-(15K-50K)-(T2, T3, T4): DSP V2.580, ARM V6.196; R5-(0.7K-3K)-S1: DSP V1.234, ARM V3.100; R5-(3K-8K)-S2: DSP V1.524, ARM V3.100; H2-(10K-30K)-(T2, T3): DSP V3.061, ARM V8.035; HS3-(3K-6K)-S2: DSP V1.135, ARM V1.040; HS3-(5K-12K)-T2: DSP V2.103, ARM V2.030. Prüfen Sie, ob Ihre Wechselrichter-Firmware-Version (DSP-Version und ARM-Version) älter ist als die aufgeführten Versionen.

## 20. `saj-h2-20k-t3` (2064)

- Q EN: What does the H2-20K-T3 package contain?
- Q DE: Was gehört zum Lieferumfang des H2-20K-T3?
- Cite: SAJ H2 10-30K user manual, German and English (covers the H2-10K-T3) p.36
- URL: https://de-linker.com/wp-content/uploads/2026/10/SAJ_H2_10-30K_User-Manual_DE-EN_EU.pdf#page=36
- Verdict: **PASS**

The packaging list covers the H2 inverter, a mounting bracket, PV connectors (T3*6 x2, T2*4 x2), pluggable terminal blocks (2-pin x2, 3-pin x1, 6-pin x1), a waterproof communication terminal cover, a waterproof AC terminal cover, an AC terminal, an M6*50 screw set x4, positive battery connectors x2, negative battery connectors x2, an eSolar AIO3, a smart meter, current transformers x3, a meter COMM cable (10 m), RJ45 plugs x10, and documents (user manual, quick installation guide, warranty card, packaging list).

Die Verpackungsliste umfasst den H2-Wechselrichter, einen Befestigungswinkel, PV-Steckverbinder (T3*6 x2, T2*4 x2), steckbare Klemmleisten (2-polig x2, 3-polig x1, 6-polig x1), eine wasserdichte Abdeckung für Kommunikationsklemmen, eine wasserdichte AC-Klemmenabdeckung, eine AC-Klemme, einen M6 x 50 Schraubensatz x4, Plus-Akku-Steckverbindungen x2, Minus-Akku-Steckverbindungen x2, ein eSolar AIO3, eine intelligente Messuhr, Stromwandler x3, ein Messuhr-COMM-Kabel (10 m), RJ45-Stecker x10 und Dokumente (Handbuch, Kurzanleitung zur Installation, Garantiekarte, Verpackungsliste).

Summary: 20/20 clean of listed copy gates. Facts vs datasheet pages are cited; numbers not re-extracted in this check.
