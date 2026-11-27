"""Preview the #1143 installer blog edits with --wp and a read-only WP-CLI prefix.

After review and backup, pass plan_pair's payload to reviewed_page_pair.invoke.
The native transaction saves the bilingual copy and adopts its German baseline.
"""

from __future__ import annotations

import argparse
from difflib import unified_diff
from typing import Any

import reviewed_page_pair

# Each replacement is anchored to an exact fragment of the native article.
REVISIONS = {
    (551, 6883): (
        (
            (
                "The two inverters communicate through the AC bus.",
                "Both inverters connect to the site’s AC wiring. The storage system uses its metering and controls to decide when to charge or discharge.",
            ),
            (
                "They reduce component count, simplify wiring, and offer higher round-trip efficiency because energy is converted only once between DC and AC. The switchover time to backup differs by model; each product page gives it from the datasheet.",
                "A hybrid can reduce component count and simplify wiring. With DC-coupled storage, surplus PV can charge the battery without first being converted to AC. For systems with backup, check the switchover time for the chosen model in its datasheet.",
            ),
            (
                "The trade-off is slightly lower efficiency and a more complex commissioning process.",
                "AC-coupled charging from PV adds conversion steps. When comparing options, look at measured system efficiency at the loads you expect and allow for commissioning a separate battery inverter.",
            ),
        ),
        (
            (
                "Die beiden Wechselrichter kommunizieren über den AC-Bus.",
                "Beide Wechselrichter sind an die AC-Installation angeschlossen. Das Speichersystem steuert das Laden und Entladen anhand seiner Messwerte.",
            ),
            (
                "Sie reduzieren die Anzahl der Komponenten, vereinfachen die Verkabelung und erreichen einen höheren Round-Trip-Wirkungsgrad, da die Energie nur einmal zwischen DC und AC umgewandelt wird. Die Umschaltzeit auf Notstrom unterscheidet sich je nach Modell; jede Produktseite nennt sie laut Datenblatt.",
                "Ein Hybrid-Wechselrichter kann den Verkabelungsaufwand und die Zahl der Geräte reduzieren. Bei DC-Kopplung lässt sich der Speicher direkt aus der PV-Anlage laden, ohne den Solarstrom vorher in Wechselstrom umzuwandeln. Für Systeme mit Notstrom finden Sie die Umschaltzeit des jeweiligen Modells im Datenblatt.",
            ),
            (
                "Der Kompromiss ist eine etwas geringere Effizienz und ein komplexerer Inbetriebnahmeprozess.",
                "Beim Laden aus der PV-Anlage fallen bei AC-Kopplung zusätzliche Umwandlungsschritte an. Für den Vergleich zählt die gemessene Effizienz des jeweiligen Systems bei den erwarteten Lasten. Planen Sie auch die Inbetriebnahme des zusätzlichen Batteriewechselrichters ein.",
            ),
        ),
    ),
    (552, 6885): (
        (
            (
                "Confirm the battery's operating voltage range matches the inverter's DC input window. Low-voltage batteries (40-59 V) must pair with low-voltage hybrid inverters. High-voltage battery stacks require high-voltage inverter inputs.",
                "Check the battery’s operating voltage range against the inverter’s battery input range for the planned number of modules.",
            ),
            (
                "Check whether the inverter and battery support CAN bus or RS485 communication and whether the battery brand is listed in the inverter's compatible-battery menu.",
                "Use the manufacturer’s compatibility list for the exact inverter and battery models. Check the specified communication interface and any firmware requirements for that pairing.",
            ),
            (
                "Follow the documented power-up sequence: battery breaker first, then inverter DC, then AC grid, then PV. Configure the battery type, verify SOC and voltage readings, and run a charge/discharge test before customer handover.",
                "Use the startup instructions for the installed inverter, battery and accessories. The switching sequence varies by system. Once the system is running, configure the battery as specified, check its state of charge and voltage readings, and test charging and discharging before handover.",
            ),
        ),
        (
            (
                "Bestätigen Sie, dass der Betriebsspannungsbereich der Batterie mit dem DC-Eingangsfenster des Wechselrichters übereinstimmt. Niederspannungsbatterien (40-59 V) müssen mit Niederspannungs-Hybridwechselrichtern kombiniert werden. Hochspannungs-Batteriestapel erfordern Hochspannungs-Wechselrichtereingänge.",
                "Vergleichen Sie den Betriebsspannungsbereich des Speichers bei der geplanten Modulzahl mit dem zulässigen Bereich am Batterieeingang des Wechselrichters.",
            ),
            (
                "Prüfen Sie, ob Wechselrichter und Batterie CAN-Bus- oder RS485-Kommunikation unterstützen und ob die Batteriemarke im Menü der kompatiblen Batterien des Wechselrichters aufgeführt ist.",
                "Maßgeblich ist die Kompatibilitätsliste des Herstellers für die konkreten Modelle von Wechselrichter und Speicher. Dort sind auch die vorgesehene Schnittstelle und etwaige Firmware-Vorgaben für die Kombination zu prüfen.",
            ),
            (
                "Halten Sie die dokumentierte Einschaltreihenfolge ein: zuerst den Batterieschutzschalter, dann die DC-Seite des Wechselrichters, dann das AC-Netz, dann die PV-Anlage. Stellen Sie den Batterietyp ein, prüfen Sie die SOC- und Spannungswerte und führen Sie vor der Übergabe an den Kunden einen Lade-/Entladetest durch.",
                "Die Einschaltreihenfolge richtet sich nach den Anleitungen für den eingebauten Wechselrichter, den Speicher und das Zubehör. Sobald das System läuft, richten Sie die Batterie nach Vorgabe ein und prüfen Ladezustand und Spannung. Testen Sie vor der Übergabe das Laden und Entladen.",
            ),
        ),
    ),
    (553, 6887): (
        (
            (
                "List every circuit you want to power during a grid outage: refrigerator, lights, router, security system, garage door opener. Sum their continuous watts and estimate daily kWh consumption by multiplying watts by hours of use.",
                "Start with the circuits that need to run during an outage, such as refrigeration, lighting, the router and security equipment. Their highest simultaneous load determines the continuous backup power in kW. Motors and compressors can also draw a brief surge at startup, so check that against the system’s backup rating.",
            ),
            ("Apply the autonomy factor", "Calculate energy for the outage window"),
            (
                "How many hours of backup without solar recharge? A typical European residential backup target is 8-24 hours for essential loads. Multiply daily kWh by autonomy hours divided by 24 to get the target usable capacity.",
                "For backup without solar recharge, multiply each load’s power in kW by the hours it runs during the planned outage, then add the results. Loads averaging 0.3 kW over a four-hour outage use 1.2 kWh at the circuits. Use the loads expected in that window, including equipment that cycles or runs only at certain times.",
            ),
            (
                "LFP batteries are typically rated at 90% depth of discharge. A 5 kWh LFP battery provides approximately 4.5 kWh of usable energy. Always size around usable, not nameplate, capacity.",
                "Use the selected battery’s stated usable energy. For example, SAJ lists 4.5 kWh of usable energy for the B2-5.0-HV5, which has 5 kWh of nominal energy. The energy available at the circuits also depends on the battery’s state of charge when the outage begins, the system’s discharge limits and conversion losses.",
            ),
            (
                "Stackable battery systems let you start with one or two modules and add more later. Leave space in your rack and ensure your inverter can handle the expanded DC input range.",
                "A modular battery can leave room for expansion. Check the permitted module counts and expansion rules for the selected battery and inverter, and allow space for the expanded system.",
            ),
        ),
        (
            (
                "Listen Sie jeden Stromkreis auf, den Sie bei einem Netzausfall mit Strom versorgen möchten: Kühlschrank, Beleuchtung, Router, Sicherheitssystem, Garagentoröffner. Summieren Sie deren kontinuierliche Watt und schätzen Sie den täglichen kWh-Verbrauch, indem Sie die Watt mit den Nutzungsstunden multiplizieren.",
                "Legen Sie zuerst fest, welche Stromkreise bei einem Netzausfall versorgt werden sollen, etwa für Kühlung, Beleuchtung, Router und Alarmanlage. Aus der höchsten gleichzeitigen Last ergibt sich die nötige Dauerleistung in kW. Bei Motoren und Kompressoren zählt zusätzlich die kurzzeitige Anlaufleistung, die das System im Notstrombetrieb liefern kann.",
            ),
            (
                "Wenden Sie den Autonomiefaktor an",
                "Energiebedarf während des Ausfalls berechnen",
            ),
            (
                "Wie viele Stunden Backup ohne Solaraufladung? Ein typisches europäisches Wohn-Backup-Ziel liegt bei 8-24 Stunden für wesentliche Lasten. Multiplizieren Sie die täglichen kWh mit den Autonomiestunden geteilt durch 24, um die Ziel-Nutzungskapazität zu erhalten.",
                "Für Notstrom ohne Nachladen aus der PV-Anlage zählt die Laufzeit jedes Verbrauchers im geplanten Ausfallzeitraum. Multiplizieren Sie je Verbraucher die Leistung in kW mit der Laufzeit in Stunden und addieren Sie die Ergebnisse. Bei einer mittleren Last von 0,3 kW über vier Stunden benötigen die versorgten Stromkreise 1,2 kWh. Berücksichtigen Sie auch Geräte, die sich zwischendurch ein- und ausschalten.",
            ),
            (
                "LFP-Batterien sind typischerweise mit 90 % Entladetiefe bewertet. Eine 5-kWh-LFP-Batterie liefert ungefähr 4,5 kWh nutzbare Energie. Dimensionieren Sie immer um die nutzbare, nicht die Nennkapazität.",
                "Maßgeblich ist die nutzbare Energie laut Datenblatt des gewählten Speichers. SAJ gibt für den B2-5.0-HV5 zum Beispiel 4,5 kWh nutzbare Energie bei 5 kWh Nennenergie an. Wie viel davon an den Stromkreisen ankommt, hängt auch vom Ladezustand zu Beginn des Ausfalls, den Entladegrenzen des Systems und den Umwandlungsverlusten ab.",
            ),
            (
                "Stapelbare Batteriespeichersysteme ermöglichen es Ihnen, mit einem oder zwei Modulen zu starten und später weitere hinzuzufügen. Lassen Sie Platz in Ihrem Rack und stellen Sie sicher, dass Ihr Wechselrichter den erweiterten DC-Eingangsbereich bewältigen kann.",
                "Ein modularer Speicher kann Spielraum für eine spätere Erweiterung bieten. Prüfen Sie die zulässigen Modulzahlen und die Erweiterungsvorgaben für den gewählten Speicher und Wechselrichter. Planen Sie auch die nötige Stellfläche ein.",
            ),
        ),
    ),
    (554, 6889): (
        (
            (
                "Indoor batteries need adequate ventilation, fire-rated wall mounting, and clearance from combustible materials. Wall-mounted LFP batteries fit neatly into utility rooms and garages.",
                "For an indoor installation, use a location permitted by the battery manual. Check its ventilation, clearances and mounting requirements alongside local fire-safety rules. A wall-mounted model can save floor space in a suitable utility room or garage.",
            ),
            (
                "Outdoor batteries require IP65 or higher enclosure ratings, UV-resistant housings, and wider operating temperature ranges. Purpose-built outdoor models are designed for -20 C to +50 C ambient conditions.",
                "Choose a battery approved by the manufacturer for outdoor installation. Match the enclosure and siting instructions to the site’s exposure to rain and sun, and check the separate charging and discharging temperature limits against the expected conditions.",
            ),
        ),
        (
            (
                "Innenbatterien benötigen ausreichende Belüftung, feuerfeste Wandmontage und Abstand zu brennbaren Materialien. Wandmontierte LFP-Batterien passen ordentlich in Technikräume und Garagen.",
                "Für die Montage im Innenraum muss der Standort laut Installationsanleitung geeignet sein. Maßgeblich sind die Vorgaben zu Lüftung, Abständen und Befestigung sowie die örtlichen Brandschutzanforderungen. Ein Modell für die Wandmontage spart Stellfläche in einem geeigneten Technikraum oder einer geeigneten Garage.",
            ),
            (
                "Außenbatterien erfordern Gehäuseschutzarten von IP65 oder höher, UV-beständige Gehäuse und größere Betriebstemperaturbereiche. Speziell für den Außenbereich entwickelte Modelle sind für Umgebungstemperaturen von -20 °C bis +50 °C ausgelegt.",
                "Für die Außenmontage eignen sich Modelle, die der Hersteller dafür freigibt. Prüfen Sie die Schutzart und die Vorgaben zum Aufstellort bei Regen und Sonneneinstrahlung. Entscheidend sind auch die zulässigen Temperaturen am Standort, getrennt für das Laden und Entladen.",
            ),
        ),
    ),
    (555, 6891): (
        (
            (
                "Update the inverter to the latest firmware. Select the correct country grid code—this controls voltage/frequency windows, ramp rates, and export limits.",
                "Use a firmware version the manufacturer specifies for the installed equipment combination. Apply the grid settings required for the connection, including any export limit agreed with the network operator.",
            ),
            (
                "Power up battery breakers first, then the inverter. Select the battery brand and model, verify SOC and voltage readings, and run a short charge cycle.",
                "Follow the startup sequence in the manuals for the installed inverter, battery and accessories. Set up the battery as specified, check the reported state of charge and voltage, and run the functional check described in the commissioning instructions.",
            ),
        ),
        (
            (
                "Aktualisieren Sie den Wechselrichter auf die neueste Firmware. Wählen Sie den korrekten länderspezifischen Netzcode – dieser steuert die Spannungs-/Frequenzfenster, Rampenraten und Einspeisegrenzen.",
                "Für die installierte Gerätekombination gilt die vom Hersteller angegebene Firmware-Version. Stellen Sie die für den Anschluss vorgeschriebenen Netzparameter ein, einschließlich einer gegebenenfalls mit dem Netzbetreiber vereinbarten Einspeisegrenze.",
            ),
            (
                "Schalten Sie zuerst die Batterie-Leistungsschalter ein, dann den Wechselrichter. Wählen Sie die Batteriemarke und das Modell aus, verifizieren Sie SOC- und Spannungswerte und führen Sie einen kurzen Ladezyklus durch.",
                "Die Anleitungen für Wechselrichter, Speicher und Zubehör geben die Einschaltreihenfolge vor. Richten Sie den Speicher nach Herstellervorgabe ein, prüfen Sie den angezeigten Ladezustand und die Spannung und führen Sie den vorgesehenen Funktionstest durch.",
            ),
        ),
    ),
    (559, 6899): (
        (
            (
                "In backup mode, the inverter isolates the home from the grid during an outage and forms a local microgrid powered by batteries and solar. The switchover time differs by model; each product page gives it from the datasheet.",
                "During a grid outage, a system designed for backup isolates the backup circuits from the grid and supplies them from the battery. The models and wiring determine whether PV can help supply those circuits during an outage. The inverter datasheet gives the switchover time for a model that supports backup.",
            ),
            ("Maximum self-consumption", "Increasing solar self-consumption"),
            (
                "Without a battery, a typical residential PV system exports 50-70% of its production. With storage and a smart EMS, self-consumption can exceed 80%. The battery stores surplus solar during the day and discharges to cover evening loads.",
                "A battery can store surplus solar generation and supply loads later, for example in the evening. To estimate the share of solar generation the household can use, compare PV output and electricity demand over time. Compare the same household with and without storage, accounting for usable battery energy, charging and discharging limits, and losses.",
            ),
        ),
        (
            (
                "Im Notstrombetrieb trennt der Wechselrichter das Haus bei einem Netzausfall vom Netz und bildet ein lokales Microgrid, das von Batteriespeicher und PV-Anlage versorgt wird. Die Umschaltzeit unterscheidet sich je nach Modell; jede Produktseite nennt sie laut Datenblatt.",
                "Ein notstromfähiges System trennt bei einem Netzausfall die für Notstrom vorgesehenen Stromkreise vom Netz und versorgt sie aus der Batterie. Ob die PV-Anlage im Notstrombetrieb zur Versorgung beitragen kann, hängt von den Geräten und ihrer Verschaltung ab. Die Umschaltzeit für den Notstrombetrieb steht im Datenblatt des Wechselrichters.",
            ),
            ("Maximaler Eigenverbrauch", "Mehr Solarstrom selbst nutzen"),
            (
                "Ohne Batterie exportiert eine typische PV-Anlage für Privathaushalte 50-70 % ihrer Erzeugung. Mit Speicher und intelligentem Energiemanagementsystem kann der Eigenverbrauch über 80 % steigen. Die Batterie speichert tagsüber überschüssigen Solarstrom und entlädt sich, um den Abendbedarf zu decken.",
                "Ein Speicher nimmt überschüssigen Solarstrom auf und stellt ihn später bereit, etwa für den Verbrauch am Abend. Für die Abschätzung des Eigenverbrauchsanteils kommt es darauf an, wann die PV-Anlage Strom erzeugt und wann der Haushalt ihn benötigt. Vergleichen Sie denselben Haushalt mit und ohne Speicher und berücksichtigen Sie dabei nutzbare Energie, Lade- und Entladegrenzen sowie Verluste.",
            ),
        ),
    ),
    (560, 6901): (
        (
            (
                "Commercial electricity bills often include demand charges based on the highest 15-minute average power draw each month. A battery system can shave these peaks by discharging during high-demand periods and recharging when demand is low.",
                "Where a site pays a demand charge, lowering its billed peak grid import can reduce that part of the bill. The applicable tariff defines the measurement interval, the billing period and the price per kW. A battery can discharge during peaks and recharge when there is room below the import target.",
            ),
            (
                "The battery management system monitors real-time load and triggers discharge when demand approaches a pre-set threshold. For a 500 kW-peak facility capped at 350 kW with a 150 kW / 300 kWh battery, annual demand charge savings can reach tens of thousands of euros.",
                "A site controller can use grid import measurements to control battery charging and discharging. For example, if grid import would stay at 500 kW for a full 15-minute interval, holding it at 350 kW takes 150 kW of battery output and 37.5 kWh delivered during that interval. A system rated at 150 kW / 300 kWh must be able to deliver the full 150 kW at that point and have enough usable energy after allowing for losses. Longer or repeated peaks need more energy before the battery can recharge.\r\n\r\nIf the tariff charges for the highest 15-minute average and the billed peak across the whole period falls from 500 to 350 kW, the reduction in the demand charge at the same rate is 150 kW multiplied by the tariff’s price per kW for that period. Compare the measured load profile with and without battery operation to estimate the reduction.",
            ),
            (
                "Size the battery to sustain these loads for the required autonomy period, typically 2-4 hours.",
                "Size backup power for the loads that can run together and backup energy for the time those loads need to stay on. If the same battery also shaves peaks, account for the energy reserved for outages.",
            ),
        ),
        (
            (
                "Gewerbliche Stromrechnungen enthalten oft Leistungsentgelte, die sich nach dem höchsten 15-Minuten-Mittelwert des Leistungsbezugs im Monat richten. Ein Batteriespeicher kann diese Spitzen kappen, indem er bei hohem Leistungsbedarf entlädt und bei geringem Bedarf wieder lädt.",
                "Wenn für einen Standort ein Leistungsentgelt anfällt, kann eine niedrigere abrechnungsrelevante Bezugsspitze diesen Teil der Stromkosten senken. Messintervall, Abrechnungszeitraum und Preis je kW stehen im geltenden Tarif. Der Speicher kann Lastspitzen abfangen und wieder laden, wenn der Netzbezug Spielraum unter der Zielgrenze lässt.",
            ),
            (
                "Das Batteriemanagementsystem überwacht die Last in Echtzeit und löst die Entladung aus, sobald sich der Leistungsbezug einem voreingestellten Schwellenwert nähert. Bei einem Betrieb mit 500 kW Spitzenlast, der mit einem Batteriespeicher von 150 kW / 300 kWh auf 350 kW begrenzt wird, können die jährlichen Einsparungen beim Leistungsentgelt Zehntausende Euro erreichen.",
                "Das Energiemanagement am Standort kann den Speicher anhand des gemessenen Netzbezugs steuern. Ein Beispiel: Würde der Netzbezug eine Viertelstunde lang durchgehend bei 500 kW liegen, müsste der Speicher 150 kW liefern, um ihn auf 350 kW zu begrenzen. In dieser Viertelstunde liefert er 37,5 kWh. Ein System mit 150 kW / 300 kWh muss die vollen 150 kW in diesem Moment abgeben können und unter Berücksichtigung der Verluste genügend nutzbare Energie verfügbar haben. Längere oder wiederkehrende Spitzen brauchen mehr Energie, bevor der Speicher nachladen kann.\r\n\r\nWird der höchste Viertelstundenmittelwert abgerechnet und sinkt der Höchstwert im gesamten Abrechnungszeitraum von 500 auf 350 kW, ergibt sich die Verringerung des Leistungsentgelts bei gleichem Tarif aus 150 kW mal dem Leistungspreis je kW für diesen Zeitraum. Grundlage der Abschätzung ist der gemessene Lastgang, den Sie mit und ohne Speichereinsatz vergleichen.",
            ),
            (
                "Dimensionieren Sie die Batterie so, dass diese Lasten für die erforderliche Autonomiezeit, in der Regel 2-4 Stunden, aufrechterhalten werden.",
                "Für die Notstromleistung zählt die höchste gleichzeitige Last, für den Energiebedarf die erforderliche Laufzeit der Verbraucher. Wenn derselbe Speicher auch Lastspitzen kappt, planen Sie die für Netzausfälle vorgesehene Energiereserve ein.",
            ),
        ),
    ),
}

HOME_STORAGE_LINKS = {
    552: (
        '<a href="/product-category/residential-storage/res-batteries/">Explore compatible batteries</a>',
        '<a href="/product-category/home-storage/">Explore home storage</a>',
    ),
    6885: (
        '<a href="/product-category/residential-storage/res-batteries/">Kompatible Batteriespeicher entdecken</a>',
        '<a href="/de/produkt-kategorie/heimspeicher/">Heimspeicher entdecken</a>',
    ),
}

EXCERPT_REVISIONS = {
    553: (
        "A step-by-step method for calculating battery storage capacity based on daily load curves, backup duration targets, and depth-of-discharge constraints.",
        "Size a home battery for the loads that need to run during an outage, using their power demand, runtime and the battery’s usable energy.",
    ),
    6887: (
        "Eine Schritt-für-Schritt-Methode zur Berechnung der Batteriespeicherkapazität basierend auf täglichen Lastkurven, Backup-Dauerzielen und Entladetiefe-Beschränkungen.",
        "So dimensionieren Sie einen Heimspeicher nach der Leistung der Notstromverbraucher, ihrer Laufzeit und der nutzbaren Energie des Speichers.",
    ),
}


def plan_pair(ids: tuple[int, int], snapshot: dict[str, Any]) -> dict[str, Any] | None:
    """Apply the reviewed fragments only if both articles match the same version."""
    changes = []
    versions: set[str] = set()
    link_versions: set[str] = set()
    for post_id, revisions in zip(ids, REVISIONS[ids], strict=True):
        key = str(post_id)
        before = after = snapshot["pages"][key]
        for original, final in revisions:
            counts = before.count(original), before.count(final)
            if counts == (1, 0):
                after = after.replace(original, final, 1)
                versions.add("original")
            elif counts == (0, 1):
                versions.add("final")
            else:
                raise ValueError(
                    f"Article {post_id} has an ambiguous body fragment: {original}"
                )
        if post_id in HOME_STORAGE_LINKS:
            original, final = HOME_STORAGE_LINKS[post_id]
            counts = before.count(original), before.count(final)
            if counts == (1, 0):
                after = after.replace(original, final, 1)
                link_versions.add("original")
            elif counts == (0, 1):
                link_versions.add("final")
            else:
                raise ValueError(
                    f"Article {post_id} has an ambiguous home-storage link"
                )
        change = {"id": post_id, "before": before, "after": after}
        if post_id in EXCERPT_REVISIONS:
            original, final = EXCERPT_REVISIONS[post_id]
            excerpt = snapshot["excerpts"][key]
            if excerpt == original:
                versions.add("original")
            elif excerpt == final:
                versions.add("final")
            else:
                raise ValueError(f"Article {post_id} has an unreviewed excerpt")
            change.update(before_excerpt=excerpt, after_excerpt=final)
        changes.append(change)
    if (
        len(versions) > 1
        or len(link_versions) > 1
        or (versions == {"original"} and link_versions == {"final"})
    ):
        raise ValueError(f"Pair {ids} contains a partial revision of the reviewed copy")
    if versions == {"final"} and link_versions != {"original"}:
        if not snapshot["current"]:
            raise ValueError(
                f"Pair {ids} has final copy but a stale translation baseline"
            )
        return None
    return {
        "mode": "adopt",
        "post_type": "post",
        "changes": changes,
        "metadata_before": snapshot["metadata"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wp", required=True, help="Read-only WP-CLI prefix")
    args = parser.parse_args()
    for ids in REVISIONS:
        snapshot = reviewed_page_pair.read(args.wp, *ids, post_type="post")
        print(snapshot["home"], *ids)
        try:
            payload = plan_pair(ids, snapshot)
        except ValueError as error:
            parser.exit(1, f"{error}\n")
        if payload is None:
            print("Already applied")
            continue
        for change in payload["changes"]:
            fields = [("body", change["before"], change["after"])]
            if "before_excerpt" in change:
                fields.append(
                    ("excerpt", change["before_excerpt"], change["after_excerpt"])
                )
            for field, before, after in fields:
                label = f"{change['id']} {field}"
                for line in unified_diff(
                    before.splitlines(), after.splitlines(), label, label, lineterm=""
                ):
                    print(line)


if __name__ == "__main__":
    main()
