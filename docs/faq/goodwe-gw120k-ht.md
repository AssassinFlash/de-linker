# GoodWe GW120K-HT (120 kW three-phase commercial string inverter)

- id: 9340
- slug: `goodwe-gw120k-ht`
- sku: `DLK-GOODWE-GW120KHT`
- model: GW120K-HT

## 1. Which grid earthing systems and AC wiring modes does the GW120K-HT support?

**Status:** pass
**Review:** pass

**EN Q:** Which grid earthing systems and AC wiring modes does the GW120K-HT support?

The GW120K-HT supports TN-S, TN-C, TN-C-S, TT and IT grids at 400 V. The manual shows connections with and without neutral (3L/N/PE or 3L/PE). On TT grids the neutral-to-earth voltage must be below 20 V RMS. Each inverter needs its own AC circuit breaker. GoodWe recommends 250 A and, if local rules call for an external RCD, a Type A device rated at 1,200 mA or higher (manual, PDF pp. 10 and 28).

**DE Q:** Welche Netzformen und AC-Anschlussarten unterstützt der GW120K-HT?

Der GW120K-HT unterstützt TN-S-, TN-C-, TN-C-S-, TT- und IT-Netze mit 400 V. Das Handbuch zeigt Anschlüsse mit und ohne Neutralleiter (3L/N/PE oder 3L/PE). Im TT-Netz muss der Effektivwert der Spannung zwischen Neutralleiter und Erde unter 20 V liegen. Jeder Wechselrichter benötigt einen eigenen AC-Leistungsschalter. GoodWe empfiehlt 250 A. Ist nach den örtlichen Vorschriften ein externer Fehlerstromschutzschalter erforderlich, empfiehlt GoodWe Typ A mit einem Bemessungsdifferenzstrom ab 1 200 mA (englische PDF-S. 10 und 28).

**Citation:** GoodWe HT 100–136K Series User Manual V1.7 (EN) · p.10 · https://de-linker.com/wp-content/uploads/2026/11/GW_HT_100-136K_User_Manual-EN.pdf

## 2. What happens if PV string open-circuit voltage on the GW120K-HT exceeds 1,000 V?

**Status:** pass
**Review:** pass

**EN Q:** What happens if PV string open-circuit voltage on the GW120K-HT exceeds 1,000 V?

Per the user manual (pp. 25 and 53), open-circuit voltage on each MPPT must never exceed 1,100 V. When PV input voltage is between 1,000 V and 1,100 V, the GW120K-HT enters waiting mode and automatically resumes normal operation once the input voltage returns to the 180–1,000 V MPPT operating range (500–850 V MPPT range at nominal power; maximum DC input power 180 kW).

**DE Q:** Was geschieht, wenn die Leerlaufspannung eines PV-Strings am GW120K-HT über 1.000 V steigt?

Laut Betriebshandbuch (S. 28 und 58) darf die Leerlaufspannung je MPPT 1.100 V keinesfalls überschreiten. Liegt die PV-Eingangsspannung zwischen 1.000 V und 1.100 V, wechselt der Wechselrichter GW120K-HT in den Wartemodus und nimmt den Normalbetrieb automatisch wieder auf, sobald die Spannung in den MPPT-Betriebsspannungsbereich von 180–1.000 V zurückkehrt (500–850 V bei Nennleistung; maximale DC-Eingangsleistung 180 kW).

**Citation:** GoodWe HT 100–136K Series User Manual V1.7 (EN) · p.25 · https://de-linker.com/wp-content/uploads/2026/11/GW_HT_100-136K_User_Manual-EN.pdf

## 3. Which grid-connection documents cover the GW120K-HT?

**Status:** pass
**Review:** pass

**EN Q:** Which grid-connection documents cover the GW120K-HT?

The GW120K-HT holds a German medium-voltage VDE-AR-N 4110 unit certificate (SGS CEBEC Unit Certificate No. 2621/0136-CER, software version 04.04.04, p. 1), an NC RfG equipment certificate covering Poland’s PTPiREE/PSE implementation for types A–D (DNV Certificate No. TC-GCC-DNVGL-SE-0124-07790-1, p. 1), and an EN 50549-1 certificate.

**DE Q:** Welche Netzanschlussnachweise liegen für den GW120K-HT vor?

Für den Wechselrichter GW120K-HT liegen ein Einheitenzertifikat nach VDE-AR-N 4110 für den Mittelspannungsanschluss (SGS CEBEC Nr. 2621/0136-CER, Softwareversion 04.04.04, S. 1), ein NC-RfG-Gerätezertifikat für die Typen A bis D nach den polnischen PTPiREE/PSE-Anforderungen (DNV Nr. TC-GCC-DNVGL-SE-0124-07790-1, S. 1) sowie ein Zertifikat nach EN 50549-1 vor.

**Citation:** GoodWe HT Series VDE-AR-N 4110 Unit Certificate (SGS CEBEC) · p.1 · https://de-linker.com/wp-content/uploads/2026/11/GW_HT_1100V_Certificate-VDE-AR-N_4110.pdf

## 4. How is grid export power limitation and plant monitoring configured on the GW120K-HT?

**Status:** pass
**Review:** pass

**EN Q:** How is grid export power limitation and plant monitoring configured on the GW120K-HT?

For a plant with several GW120K-HT inverters, the GoodWe manual shows the SEC1000 controlling export via RS485 on COM2. It separately shows the EzLogger Pro and EzLogger3000C for monitoring. For a single inverter, the optional COM4 port connects the meter for export control. The manual shows the GM3000C, and the HT 1100 V compatibility list also includes the GM330 (IoT compatibility list V18, PDF p. 7).

**DE Q:** Wie werden Einspeisebegrenzung und Anlagenüberwachung beim GW120K-HT umgesetzt?

Bei mehreren Wechselrichtern des Typs GW120K-HT zeigt GoodWe die Einspeisebegrenzung mit dem SEC1000 über RS485 an COM2. Für die Anlagenüberwachung zeigt das Handbuch den EzLogger Pro und den EzLogger3000C. An einem Einzelgerät verbindet der optionale Anschluss COM4 den Zähler für die Einspeisebegrenzung. Das Handbuch zeigt den GM3000C. Die Kompatibilitätsliste für die HT-Serie mit 1.100 V nennt auch den GM330 (IoT-Kompatibilitätsliste V18, PDF-S. 7).

**Citation:** GoodWe HT 100–136K Series User Manual V1.7 (EN) · p.31 · https://de-linker.com/wp-content/uploads/2026/11/GW_HT_100-136K_User_Manual-EN.pdf

## 5. Can the GW120K-HT connect directly to a battery cabinet?

**Status:** pass
**Review:** pass

**EN Q:** Can the GW120K-HT connect directly to a battery cabinet?

The GW120K-HT is a grid-tied PV string inverter. Its DC inputs accept PV strings. There is no battery connection. A storage installation needs a separate battery inverter or a hybrid inverter with a compatible battery port.

**DE Q:** Kann an den GW120K-HT direkt ein Batterieschrank angeschlossen werden?

Der GW120K-HT ist ein netzgekoppelter PV-Stringwechselrichter. Seine DC-Eingänge sind für PV-Strings vorgesehen. Einen Batterieanschluss hat er nicht. Ein Speichersystem benötigt einen separaten Batteriewechselrichter oder einen Hybridwechselrichter mit passendem Batterieanschluss.

**Citation:** GoodWe HT 100–136K Series User Manual V1.7 (EN) · p.8 · https://de-linker.com/wp-content/uploads/2026/11/GW_HT_100-136K_User_Manual-EN.pdf

## 6. What European manufacturer warranty applies to the GW120K-HT?

**Status:** pass
**Review:** pass

**EN Q:** What European manufacturer warranty applies to the GW120K-HT?

GoodWe’s European inverter warranty gives the GW120K-HT five years of cover. The period starts at first installation or twelve months after production, whichever is earlier. If the installation date cannot be documented, GoodWe uses its shipment date in place of the installation date.

**DE Q:** Welche europäische Herstellergarantie gilt für den GW120K-HT?

Für den GW120K-HT gewährt GoodWe nach den europäischen Garantiebedingungen fünf Jahre Herstellergarantie. Die Frist beginnt mit der Erstinstallation, spätestens zwölf Monate nach Herstellung. Fehlt ein ausreichender Nachweis des Installationsdatums, zählt für GoodWe der Tag, an dem das Gerät das Werk verlassen hat.

**Citation:** GoodWe Limited Warranty for Inverter System Europe Rev 3.9 (EN) · p.1 · https://de-linker.com/wp-content/uploads/2026/10/GW_Limited-Warranty_Inverter-System_Europe.pdf
