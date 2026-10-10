# GoodWe EzManager3000 HEMS Gateway

- id: 2415
- slug: `goodwe-ezmanager3000-hems-gateway`
- sku: `DLK-GOODWE-EZMANAGER3000`
- model: EzManager3000

## 1. Will one EzManager3000 cover this inverter and device mix?

**Status:** withdrawn
**Review:** withdrawn — a number is not in the cited passage

**EN Q:** Will one EzManager3000 cover this inverter and device mix?

The datasheet lists the device management limits per EzManager3000: hybrid inverter up to 4, grid-tied inverter up to 4, EV charger up to 2, heat pump 1 (SG-Ready), Shelly device up to 12. The user manual technical parameters state different figures: energy storage inverter maximum 1 unit, grid-tied inverter maximum 1 unit, charging pile maximum 2 units, heat pump maximum 1 unit (SG-Ready), Shelly device maximum 12. The manual also notes that the number of hybrid connections supported is subject to the actual model, and refers to the Inverter and IoT Device Compatibility List for supported inverter models and quantities. Check the compatibility list for your specific mix.

**DE Q:** Deckt ein EzManager3000 diese Wechselrichter- und Gerätekombination ab?

Das Datenblatt nennt die Gerätemanagement-Grenzen pro EzManager3000: Hybrid-Wechselrichter bis 4, Netzgekoppelter Wechselrichter bis 4, EV-Ladegerät bis 2, Wärmepumpe 1 (SG-Ready), Shelly-Gerät bis 12. Die technischen Parameter des Benutzerhandbuchs nennen abweichende Werte: Energiespeicher-Wechselrichter maximal 1 Einheit, netzgekoppelter Wechselrichter maximal 1 Einheit, Ladepunkt maximal 2 Einheiten, Wärmepumpe maximal 1 Einheit (SG-Ready), Shelly-Gerät maximal 12. Das Handbuch weist zudem darauf hin, dass die Anzahl der unterstützten Hybrid-Anbindungen vom tatsächlichen Modell abhängt, und verweist für unterstützte Wechselrichtermodelle und Stückzahlen auf die Inverter and IoT Device Compatibility List. Prüfen Sie die Kompatibilitätsliste für Ihre konkrete Kombination.

**Citation:** GoodWe EzManager3000 Datasheet (EMEA, EN) · p.1 · https://de-linker.com/wp-content/uploads/2026/10/GW_EzManager3000_Datasheet_EMEA-EN_V1.1.pdf

## 2. What power supply does the gateway need?

**Status:** withdrawn
**Review:** withdrawn — a number is not in the cited passage

**EN Q:** What power supply does the gateway need?

Connect the power adapter supplied with the unit to the DC IN port. The power adapter specifications are 12V/1.5A. The datasheet lists the power adapter as AC input 100 ~ 240V, 50/60Hz, DC output 12V, with DC power supply 12V and power consumption ≤7 W. The unit can draw power from the grid as a load or from the backup side of the inverter. When the ET series inverter is used in a hybrid grid-tied scenario, it does not support powering the HEMS from the backup side.

**DE Q:** Welche Stromversorgung braucht das Gateway?

Schließen Sie das mitgelieferte Netzteil am DC-IN-Anschluss an. Die Netzteil-Spezifikationen sind 12V/1,5A. Das Datenblatt nennt für das Netzteil AC-Eingang 100 ~ 240V, 50/60Hz, DC-Ausgang 12V, dazu DC-Versorgung 12V und Leistungsaufnahme ≤7 W. Das Gerät kann Strom aus dem Netz als Last oder von der Backup-Seite des Wechselrichters beziehen. Wird der ET-Serien-Wechselrichter in einem hybriden netzgekoppelten Szenario eingesetzt, unterstützt er die Versorgung des HEMS von der Backup-Seite nicht.

**Citation:** GoodWe EzManager3000 User Manual (EN) · p.32 · https://de-linker.com/wp-content/uploads/2026/09/GW_EzManager3000_User-Manual-EN_V1.3.pdf

## 3. Does the gateway work with dynamic tariffs and trading platforms?

**Status:** pass
**Review:** pass

**EN Q:** Does the gateway work with dynamic tariffs and trading platforms?

The datasheet states auto-connect to electricity trading platforms, dynamic and negative tariff support, AI-optimized scheduling for maximum tariff savings, and AI forecasting for personalized, habit-based energy optimization. In the tariff setting you select export energy tariff or import energy tariff and set the tariff type, supporting fixed tariff, time-of-use tariff and dynamic pricing. Dynamic pricing obtains dynamic pricing from the utility company and combines it with user-set tariff surcharges to adjust the actual electricity buying and selling tariffs; it is applicable only to certain regions and certain equipment. The manual notes that only some European countries or regions support the use of electricity market tariff, and the current electricity market only supports Nord Pool.

**DE Q:** Arbeitet das Gateway mit dynamischen Tarifen und Handelsplattformen?

Das Datenblatt nennt die automatische Verbindung mit Stromhandelsplattformen, Unterstützung dynamischer und negativer Tarife, KI-optimierte Planung für maximale Tarifeinsparungen und KI-Prognose für personalisierte, gewohnheitsbasierte Energieoptimierung. In den Tarifeinstellungen wählen Sie Export-Energietarif oder Import-Energietarif und legen den Tariftyp fest, unterstützt werden Festtarif, Time-of-Use-Tarif und Dynamic Pricing. Dynamic Pricing bezieht dynamische Preise vom Energieversorger und kombiniert sie mit benutzerdefinierten Tarifzuschlägen, um die tatsächlichen Strombezugs- und Einspeisetarife anzupassen; anwendbar nur in bestimmten Regionen und mit bestimmten Geräten. Das Handbuch weist darauf hin, dass nur einige europäische Länder oder Regionen die Nutzung des Strommarkttarifs unterstützen und der aktuelle Strommarkt nur Nord Pool unterstützt.

**Citation:** GoodWe EzManager3000 Datasheet (EMEA, EN) · p.1 · https://de-linker.com/wp-content/uploads/2026/10/GW_EzManager3000_Datasheet_EMEA-EN_V1.1.pdf

## 4. How do the inverters, meters and heat pump connect?

**Status:** pass
**Review:** pass

**EN Q:** How do the inverters, meters and heat pump connect?

Smart meters and grid-tied inverters connect via RS485. The SG Ready heat pump connects via DO, supporting a maximum of 1 heat pump. Energy storage inverters, AC charger, smart sockets and GoodHeat connect to the router via WiFi/LAN, and the gateway connects to the router via WiFi/LAN; up to 12 smart devices are supported, and LAN is recommended for communication stability. The wiring diagram shows the smart meter on RS485, the SG Ready heat pump on DO, and the grid-tied inverter on RS485. To set the heat pump working mode, select the desired working mode via the SEMS+ App after completing the wiring.

**DE Q:** Wie werden Wechselrichter, Zähler und Wärmepumpe angebunden?

Smart Meter und netzgekoppelte Wechselrichter werden über RS485 angebunden. Die SG-Ready-Wärmepumpe wird über DO angebunden, maximal 1 Wärmepumpe. Energiespeicher-Wechselrichter, AC-Ladegerät, Smart Sockets und GoodHeat werden über WiFi/LAN mit dem Router verbunden, das Gateway ebenfalls über WiFi/LAN; unterstützt werden bis zu 12 Smart-Geräte, für Kommunikationsstabilität wird LAN empfohlen. Das Verdrahtungsdiagramm zeigt den Smart Meter an RS485, die SG-Ready-Wärmepumpe an DO und den netzgekoppelten Wechselrichter an RS485. Um den Betriebsmodus der Wärmepumpe einzustellen, wählen Sie nach Abschluss der Verdrahtung den gewünschten Modus über die SEMS+ App.

**Citation:** GoodWe EzManager3000 User Manual (EN) · p.12 · https://de-linker.com/wp-content/uploads/2026/09/GW_EzManager3000_User-Manual-EN_V1.3.pdf
