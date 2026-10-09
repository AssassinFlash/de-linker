"""Customer-facing wording of the engine's results, in English and German.

The engine words its own results (rule labels, Stückliste lines, warnings,
report sections) so that the screen and the PDF show one text, never two
translations of the same sentence. Wording follows AGENTS.md section 3:
Solution draft / Lösungsentwurf, Bill of materials / Stückliste, formal
German (Sie). Each string was written per language and reviewed adversarially;
the review record is in docs/acceptance/2026-10-09/14/copy-review.md.
"""

from __future__ import annotations

from typing import Literal

Locale = Literal["en", "de"]

_TEXTS: dict[str, tuple[str, str]] = {
    # Rule labels -------------------------------------------------------------
    "rule.application": ("Application", "Anwendung"),
    "rule.phase": ("Grid connection phases", "Phasen des Netzanschlusses"),
    "rule.single_phase_limit": (
        "Single-phase feed-in at most 4.6 kVA (VDE-AR-N 4105)",
        "Einphasige Einspeisung höchstens 4,6 kVA (VDE-AR-N 4105)",
    ),
    "rule.pv_input": (
        "Maximum PV input of the inverter covers the array",
        "Maximale PV-Eingangsleistung des Wechselrichters deckt den Generator ab",
    ),
    "rule.dc_ac_ratio": (
        "DC/AC ratio within the manufacturer's limit",
        "DC/AC-Verhältnis innerhalb der Herstellergrenze",
    ),
    "rule.backup": ("Backup supply", "Notstrom- oder Ersatzstromversorgung"),
    "rule.engineering_data": (
        "Cited datasheet values for the string layout",
        "Belegte Datenblattwerte für die Stringauslegung",
    ),
    "rule.string_voltage": (
        "String voltage within the MPPT window",
        "Strangspannung im MPPT-Bereich",
    ),
    "rule.string_current": (
        "String current within the MPPT input limits",
        "Strangstrom innerhalb der MPPT-Eingangsgrenzen",
    ),
    "rule.string_count": (
        "Array fits the MPPT inputs",
        "Generator passt auf die MPPT-Eingänge",
    ),
    "rule.battery_release": (
        "Battery released by the manufacturers",
        "Batterie von den Herstellern freigegeben",
    ),
    "rule.existing_inverter": (
        "Existing inverter in our product range",
        "Vorhandener Wechselrichter in unserem Sortiment",
    ),
    "rule.htw_min_pv": (
        "PV at least 0.5 kWp per MWh of annual consumption (HTW Berlin)",
        "PV-Leistung mindestens 0,5 kWp je MWh Jahresverbrauch (HTW Berlin)",
    ),
    "rule.htw_max_per_kwp": (
        "Usable capacity at most 1.5 kWh per kWp (HTW Berlin)",
        "Nutzbare Kapazität höchstens 1,5 kWh je kWp (HTW Berlin)",
    ),
    "rule.htw_max_per_mwh": (
        "Usable capacity at most 1.5 kWh per MWh of annual consumption (HTW Berlin)",
        "Nutzbare Kapazität höchstens 1,5 kWh je MWh Jahresverbrauch (HTW Berlin)",
    ),
    "rule.backup_reserve": (
        "Backup reserve on top: {load} kW for {hours} h",
        "Zusätzliche Notstromreserve: {load} kW für {hours} h",
    ),
    # Stückliste --------------------------------------------------------------
    "line.inverter": ("Hybrid inverter", "Hybridwechselrichter"),
    "line.battery_modules": ("Battery modules", "Batteriemodule"),
    "line.battery_units": ("Battery system", "Batteriesystem"),
    "line.accessory": (
        "Accessory named in the release",
        "In der Freigabe genanntes Zubehör",
    ),
    "line.meter": ("Energy meter", "Energiezähler"),
    "line.backup": (
        "Transfer switch for backup supply",
        "Umschalteinrichtung für die Ersatzstromversorgung",
    ),
    "line.controller": (
        "Controller for parallel operation",
        "Steuerung für den Parallelbetrieb",
    ),
    "line.pv_module": (
        "PV modules of your choice (layout checked with {model})",
        "PV-Module nach Ihrer Wahl (Auslegung geprüft mit {model})",
    ),
    "line.mounting": (
        "Mounting system for {count} modules",
        "Montagesystem für {count} Module",
    ),
    "line.dc_cable": (
        "PV string cable for both poles; measure the route on site",
        "PV-Strangkabel für beide Pole; Leitungsweg vor Ort aufmessen",
    ),
    "line.connector": (
        "PV connector pairs, mating the module and the inverter connectors",
        "PV-Steckverbinderpaare, passend zu Modul- und Wechselrichterstecker",
    ),
    "line.string_fuse": (
        "gPV string fuses with holders, rated {low}–{high} A",
        "gPV-Strangsicherungen mit Halter, Bemessungsstrom {low}–{high} A",
    ),
    "line.ac_protection": (
        "AC protection and grid connection to VDE-AR-N 4105",
        "AC-Absicherung und Netzanschluss nach VDE-AR-N 4105",
    ),
    "line.na_protection": (
        "Central grid and system protection (NA-Schutz), required above 30 kVA",
        "Zentraler NA-Schutz, erforderlich über 30 kVA",
    ),
    "scope.ours": ("Linker product", "Linker-Produkt"),
    "scope.installer": ("Installer's scope", "Leistung des Installateurs"),
    # Bases of lines ----------------------------------------------------------
    "basis.ranked": (
        "Of the inverters that pass every rule: AC power closest to {kwp} kWp, "
        "then the released battery closest to the HTW limit",
        "Von den Wechselrichtern, die alle Regeln erfüllen: AC-Leistung am nächsten an {kwp} kWp, "
        "danach die freigegebene Batterie am nächsten an der HTW-Grenze",
    ),
    "basis.chosen": ("Chosen by you", "Von Ihnen gewählt"),
    "basis.existing": (
        "Your existing inverter; it is not part of this Stückliste",
        "Ihr vorhandener Wechselrichter; er ist nicht Teil dieser Stückliste",
    ),
    "basis.battery_fit": (
        "Largest released configuration within the HTW limit of {upper} kWh",
        "Größte freigegebene Konfiguration innerhalb der HTW-Grenze von {upper} kWh",
    ),
    "basis.battery_above": (
        "Smallest released configuration; it exceeds the HTW limit of {upper} kWh",
        "Kleinste freigegebene Konfiguration; sie überschreitet die HTW-Grenze von {upper} kWh",
    ),
    "basis.stacks.one": (
        "{quantity} modules in one stack",
        "{quantity} Module in einem Stapel",
    ),
    "basis.stacks.other": (
        "{quantity} modules in {stacks} stacks",
        "{quantity} Module in {stacks} Stapeln",
    ),
    "basis.module.one": ("One module in one stack", "Ein Modul in einem Stapel"),
    "basis.accessory_per_stack": ("{quantity} per stack", "{quantity} je Stapel"),
    "basis.meter_included": (
        "The inverter ships with its meter",
        "Der Wechselrichter wird mit seinem Zähler geliefert",
    ),
    "basis.meter_documented": (
        "The manufacturer names this meter for the inverter",
        "Der Hersteller nennt diesen Zähler für den Wechselrichter",
    ),
    "basis.backup_accessory": (
        "The inverter supplies backup only with this switch",
        "Der Wechselrichter versorgt nur mit diesem Umschalter im Ersatzstrombetrieb",
    ),
    "basis.modules.one": (
        "{count} modules of {wp} Wp in one string",
        "{count} Module mit {wp} Wp in einem Strang",
    ),
    "basis.modules.other": (
        "{count} modules of {wp} Wp in {strings} strings of {length}",
        "{count} Module mit {wp} Wp in {strings} Strängen zu je {length}",
    ),
    "basis.cable.one": (
        "One string × 2 poles × {length} m",
        "Ein Strang × 2 Pole × {length} m",
    ),
    "basis.cable.other": (
        "{strings} strings × 2 poles × {length} m",
        "{strings} Stränge × 2 Pole × {length} m",
    ),
    "basis.connectors.other": ("{pairs} pairs per string", "{pairs} Paare je Strang"),
    "basis.fuses": (
        "{fuses} fuses on MPPT {mppts}: the reverse current of the parallel strings exceeds the module's fuse rating",
        "{fuses} Sicherungen an MPPT {mppts}: Der Rückstrom der parallelen Stränge übersteigt die Sicherungsgrenze des Moduls",
    ),
    "basis.no_fuses": (
        "No string fuses: on every MPPT the reverse current stays within the module's fuse rating",
        "Keine Strangsicherungen: An jedem MPPT bleibt der Rückstrom innerhalb der Sicherungsgrenze des Moduls",
    ),
    # Release verdicts ----------------------------------------------------------
    "verdict.released": ("Released", "Freigegeben"),
    "verdict.released_with_accessory": (
        "Released with accessory",
        "Freigegeben mit Zubehör",
    ),
    "verdict.not_released": ("Not released", "Nicht freigegeben"),
    "verdict.unknown": ("No release document", "Kein Freigabedokument"),
    # Warnings ------------------------------------------------------------------
    "warn.no_storage": (
        "With less than 0.5 kWp of PV per MWh of consumption, HTW Berlin advises against a battery. "
        "The proposal covers the inverter; a battery can be added later.",
        "Bei weniger als 0,5 kWp PV-Leistung je MWh Verbrauch rät die HTW Berlin von einem Batteriespeicher ab. "
        "Der Vorschlag umfasst den Wechselrichter; ein Speicher lässt sich später ergänzen.",
    ),
    "warn.outside_table": (
        "The HTW tables cover 2,000 to 10,000 kWh per year in homes without heat pump or electric car; "
        "for this household the self-sufficiency figures are a rough guide.",
        "Die HTW-Tabellen gelten für 2.000 bis 10.000 kWh pro Jahr in Haushalten ohne Wärmepumpe und Elektroauto; "
        "für diesen Haushalt sind die Autarkiewerte nur ein grober Anhaltspunkt.",
    ),
    "warn.battery_above": (
        "No released battery configuration fits within the HTW limit of {upper} kWh. "
        "The smallest released configuration, {usable} kWh, is proposed and marked.",
        "Keine freigegebene Batteriekonfiguration passt in die HTW-Grenze von {upper} kWh. "
        "Vorgeschlagen und markiert ist die kleinste freigegebene Konfiguration mit {usable} kWh.",
    ),
    "warn.backup_reserve_missing": (
        "Backup supply is selected without a load and duration, so no reserve is added to the capacity.",
        "Notstrom ist gewählt, aber ohne Last und Dauer; der Kapazität wird daher keine Reserve hinzugefügt.",
    ),
    "warn.existing_unknown": (
        "Your existing inverter {model} is not in our product range. "
        "A battery for it needs a manufacturer release, which our team checks per project.",
        "Ihr vorhandener Wechselrichter {model} ist nicht in unserem Sortiment. "
        "Ein Speicher dafür braucht eine Herstellerfreigabe, die unser Team pro Projekt prüft.",
    ),
    "warn.no_battery_release": (
        "No battery in our range has a manufacturer release for {model}.",
        "Für {model} hat keine Batterie unseres Sortiments eine Herstellerfreigabe.",
    ),
    "warn.na_protection": (
        "Above 30 kVA, VDE-AR-N 4105 requires central grid and system protection (NA-Schutz).",
        "Über 30 kVA verlangt die VDE-AR-N 4105 einen zentralen NA-Schutz.",
    ),
    "warn.vde_4110": (
        "Above 135 kW the grid connection follows VDE-AR-N 4110.",
        "Über 135 kW richtet sich der Netzanschluss nach VDE-AR-N 4110.",
    ),
    # Relaxations (no candidate) -------------------------------------------------
    "relax.phase": (
        "Three-phase connection: more inverters qualify.",
        "Dreiphasiger Anschluss: Mehr Wechselrichter kommen in Frage.",
    ),
    "relax.backup": (
        "Accept an accessory for backup supply.",
        "Zubehör für die Ersatzstromversorgung zulassen.",
    ),
    "relax.backup_none": ("Plan without backup supply.", "Ohne Notstrom planen."),
    "relax.kwp": (
        "Smaller array: the largest PV input in this selection is {kwp} kWp.",
        "Kleinerer Generator: Die größte PV-Eingangsleistung dieser Auswahl beträgt {kwp} kWp.",
    ),
    "relax.existing": (
        "Leave the existing inverter empty to plan a new system.",
        "Feld für den vorhandenen Wechselrichter leer lassen, um eine neue Anlage zu planen.",
    ),
    # Rule values ---------------------------------------------------------------------
    "value.application.home": ("home", "Wohngebäude"),
    "value.application.commercial": ("commercial", "Gewerbe"),
    "value.application.unknown": ("not stated", "nicht angegeben"),
    "value.unknown": ("not in the datasheet data", "nicht in den Datenblattwerten"),
    "value.phase": (
        "{value}-phase, {limit}-phase requested",
        "{value}-phasig, {limit}-phasig verlangt",
    ),
    "value.application": ("{value}, {limit} requested", "{value}, {limit} verlangt"),
    "value.single_phase_limit": (
        "{value} kVA, at most {limit} kVA",
        "{value} kVA, höchstens {limit} kVA",
    ),
    "value.pv_input": (
        "{value} kW for a {limit} kWp array",
        "{value} kW für einen Generator mit {limit} kWp",
    ),
    "value.dc_ac_ratio": (
        "{value}, manufacturer limit {limit}",
        "{value}, Herstellergrenze {limit}",
    ),
    "value.backup.native": ("backup output {value} kVA", "Notstromausgang {value} kVA"),
    "value.backup.accessory": (
        "with the documented accessory",
        "mit dem dokumentierten Zubehör",
    ),
    "value.backup.none": (
        "no backup output in the datasheet data",
        "kein Notstromausgang in den Datenblattwerten",
    ),
    "value.modules": ("{value} modules connected", "{value} Module angeschlossen"),
    "value.batteries.one": ("one released battery", "eine freigegebene Batterie"),
    "value.batteries.other": (
        "{value} released batteries",
        "{value} freigegebene Batterien",
    ),
    "value.htw_min_pv": (
        "{value} kWp per MWh, at least {limit}",
        "{value} kWp je MWh, mindestens {limit}",
    ),
    "value.htw_max_per_kwp": (
        "1.5 kWh × {kwp} kWp = {value} kWh",
        "1,5 kWh × {kwp} kWp = {value} kWh",
    ),
    "value.htw_max_per_mwh": (
        "1.5 kWh × {mwh} MWh = {value} kWh",
        "1,5 kWh × {mwh} MWh = {value} kWh",
    ),
    "value.backup_reserve": ("{value} kWh added", "{value} kWh zusätzlich"),
    "yield.source": (
        "PVGIS 5 ({db}) through pvlib, system loss {loss} %",
        "PVGIS 5 ({db}) über pvlib, Systemverluste {loss} %",
    ),
    "basis.meter_in_box": (
        "Ships with its meter: {text}",
        "Wird mit Zähler geliefert: {text}",
    ),
    # Commercial ------------------------------------------------------------------------
    "ci.basis.backup": (
        "Backup reserve: {load} kW for {hours} h, {kwh} kWh",
        "Notstromreserve: {load} kW für {hours} h, {kwh} kWh",
    ),
    "ci.basis.shaving": (
        "Peak of {peak} kW capped at {cap} kW: {power} kW of battery power and {energy} kWh of usable "
        "energy for the day with the largest area above the cap",
        "Lastspitze von {peak} kW auf {cap} kW begrenzt: {power} kW Batterieleistung und {energy} kWh "
        "nutzbare Energie für den Tag mit der größten Fläche über der Grenze",
    ),
    "ci.basis.options": (
        "Choose a cap in the table to size the battery from your load profile.",
        "Wählen Sie in der Tabelle eine Grenze, um den Speicher aus Ihrem Lastgang auszulegen.",
    ),
    "ci.basis.peak_indicative": (
        "Peak reduction of {power} kW, with energy for one to two hours at that power "
        "(Intilion: about 1C for peak shaving, 0.5C for self-consumption)",
        "Spitzenkappung um {power} kW, mit Energie für ein bis zwei Stunden bei dieser Leistung "
        "(Intilion: etwa 1C für Spitzenkappung, 0,5C für Eigenverbrauch)",
    ),
    "ci.basis.self_pv": (
        "Self-consumption: about 1 kWh of usable storage per kWp of PV, so {kwh} kWh for {kwp} kWp (Voltfang)",
        "Eigenverbrauch: etwa 1 kWh nutzbarer Speicher je kWp PV, also {kwh} kWh für {kwp} kWp (Voltfang)",
    ),
    "ci.basis.self_consumption": (
        "Self-consumption without a PV figure: {low}–{high} kWh, from 0.8–1.0 kWp of PV per MWh "
        "of consumption and 1 kWh per kWp (Voltfang)",
        "Eigenverbrauch ohne PV-Angabe: {low}–{high} kWh, aus 0,8–1,0 kWp PV je MWh Verbrauch "
        "und 1 kWh je kWp (Voltfang)",
    ),
    "ci.basis.indicative": (
        "These are indicative figures. Send us your 15-minute load profile and we size the system.",
        "Dies sind Richtwerte. Senden Sie uns Ihren 15-Minuten-Lastgang, dann legen wir die Anlage aus.",
    ),
    "ci.warn.short_profile": (
        "The profile covers {days} days; a full year shows the true annual peak.",
        "Der Lastgang umfasst {days} Tage; erst ein volles Jahr zeigt die tatsächliche Jahresspitze.",
    ),
    "ci.warn.recharge": (
        "On {days} days the load leaves too little room below the cap to recharge; choose a higher cap.",
        "An {days} Tagen bleibt unter der Grenze zu wenig Raum zum Nachladen; wählen Sie eine höhere Grenze.",
    ),
    "ci.warn.pick_cap": (
        "Peak shaving needs a cap: pick one in the table or enter a target peak.",
        "Für die Spitzenkappung fehlt eine Grenze: Wählen Sie eine in der Tabelle oder geben Sie eine Zielspitze ein.",
    ),
    "ci.warn.rlm": (
        "Above 100,000 kWh a year your grid operator meters a 15-minute load profile; ask them for last year's data.",
        "Ab 100.000 kWh im Jahr misst Ihr Netzbetreiber einen 15-Minuten-Lastgang; fordern Sie die Daten des "
        "Vorjahres bei ihm an.",
    ),
    "pdf.footer": (
        "Linker Solution Configurator · de-linker.com · Yield: PVGIS © European Union · "
        "Self-sufficiency: HTW Berlin · Postcodes: GeoNames (CC BY 4.0)",
        "Linker Lösungskonfigurator · de-linker.com · Ertrag: PVGIS © Europäische Union · "
        "Autarkie: HTW Berlin · Postleitzahlen: GeoNames (CC BY 4.0)",
    ),
    # Report ------------------------------------------------------------------------
    "report.title": ("Design report", "Auslegungsbericht"),
    "report.subtitle": (
        "Solution Configurator, residential system",
        "Lösungskonfigurator, Anlage für ein Wohngebäude",
    ),
    "report.site": ("Site and inputs", "Standort und Eingaben"),
    "report.yield": ("PV yield", "PV-Ertrag"),
    "report.storage": ("Storage sizing", "Speicherauslegung"),
    "report.metrics": (
        "Self-sufficiency and self-consumption",
        "Autarkiegrad und Eigenverbrauchsanteil",
    ),
    "report.basis": ("Selection basis", "Auswahlgrundlage"),
    "report.releases": (
        "Manufacturer releases and documents",
        "Herstellerfreigaben und Dokumente",
    ),
    "report.bom": ("Bill of materials", "Stückliste"),
    "report.assumptions": ("Assumptions and limits", "Annahmen und Grenzen"),
    "report.next": ("Next steps", "Nächste Schritte"),
    "report.warnings": ("Notes", "Hinweise"),
    "row.postcode": ("Postcode", "Postleitzahl"),
    "row.position": ("Position", "Position"),
    "row.consumption": ("Annual consumption", "Jahresverbrauch"),
    "row.consumption_range": (
        "Annual consumption with additions",
        "Jahresverbrauch mit Zusatzverbrauchern",
    ),
    "row.array": ("PV array", "PV-Generator"),
    "row.plane": ("Roof plane {index}", "Dachfläche {index}"),
    "row.plane_value": (
        "{kwp} kWp, tilt {tilt}°, facing {azimuth}°",
        "{kwp} kWp, Neigung {tilt}°, Ausrichtung {azimuth}°",
    ),
    "row.phase": ("Grid connection", "Netzanschluss"),
    "row.phase_value": ("{phase}-phase", "{phase}-phasig"),
    "row.backup": ("Backup supply", "Notstrom"),
    "backup.none": ("Not needed", "Nicht benötigt"),
    "backup.needed": ("Needed", "Benötigt"),
    "backup.needed_accessory_ok": (
        "Needed, accessory accepted",
        "Benötigt, Zubehör zulässig",
    ),
    "row.heat_pump": ("Heat pump", "Wärmepumpe"),
    "row.ev": ("Electric car", "Elektroauto"),
    "row.existing": ("Existing inverter", "Vorhandener Wechselrichter"),
    "yes": ("Yes", "Ja"),
    "no": ("No", "Nein"),
    "row.yield_year": (
        "Annual yield, range over {first}–{last}",
        "Jahresertrag, Spanne {first}–{last}",
    ),
    "row.yield_specific": ("Specific yield", "Spezifischer Ertrag"),
    "row.yield_mean": ("Mean annual yield", "Mittlerer Jahresertrag"),
    "row.yield_source": ("Source", "Quelle"),
    "row.storage_range": (
        "Usable capacity, HTW upper limit",
        "Nutzbare Kapazität, HTW-Obergrenze",
    ),
    "row.storage_range_reserve": (
        "Usable capacity, HTW upper limit plus backup reserve",
        "Nutzbare Kapazität, HTW-Obergrenze zuzüglich Notstromreserve",
    ),
    "row.storage_reserve": ("Backup reserve included", "Enthaltene Notstromreserve"),
    "row.storage_selected": (
        "Proposed usable capacity",
        "Vorgeschlagene nutzbare Kapazität",
    ),
    "row.autarky": ("Self-sufficiency with storage", "Autarkiegrad mit Speicher"),
    "row.autarky_without": (
        "Self-sufficiency without storage",
        "Autarkiegrad ohne Speicher",
    ),
    "row.share": (
        "Self-consumption with storage",
        "Eigenverbrauchsanteil mit Speicher",
    ),
    "row.share_without": (
        "Self-consumption without storage",
        "Eigenverbrauchsanteil ohne Speicher",
    ),
    "row.metrics_basis": ("Method", "Methode"),
    "metrics.basis": (
        "HTW Berlin Unabhängigkeitsrechner, tables of 2024-08-23",
        "Unabhängigkeitsrechner der HTW Berlin, Tabellen vom 23.08.2024",
    ),
    "metrics.method": (
        "HTW Berlin Unabhängigkeitsrechner tables; the range covers the spread of real households "
        "(most within 5 percentage points of the table value)",
        "Tabellen des Unabhängigkeitsrechners der HTW Berlin; die Spanne deckt die Streuung realer "
        "Haushalte ab (meist innerhalb von 5 Prozentpunkten des Tabellenwerts)",
    ),
    "row.rule_value": ("{value} (limit {limit})", "{value} (Grenze {limit})"),
    "row.passed": ("met", "erfüllt"),
    "row.failed": ("not met", "nicht erfüllt"),
    "row.strings": ("String layout", "Stringauslegung"),
    "row.strings_value.other": (
        "{count} × {wp} Wp in {strings} strings; Voc at {tmin} °C: {voc} V per module",
        "{count} × {wp} Wp in {strings} Strängen; Voc bei {tmin} °C: {voc} V je Modul",
    ),
    "row.strings_value.one": (
        "{count} × {wp} Wp in one string; Voc at {tmin} °C: {voc} V per module",
        "{count} × {wp} Wp in einem Strang; Voc bei {tmin} °C: {voc} V je Modul",
    ),
    "row.document": ("Document", "Dokument"),
    "row.page": ("page {page}", "Seite {page}"),
    "col.quantity": ("Qty", "Menge"),
    "col.item": ("Item", "Position"),
    "col.model": ("Model", "Modell"),
    "col.scope": ("Supplied by", "Lieferung"),
    "unit.pcs": ("pcs", "Stk."),
    "unit.m": ("m", "m"),
    "unit.pairs": ("pairs", "Paare"),
    "unit.set": ("set", "Satz"),
    "next.draft": (
        "Add the Linker products to your solution draft and request a Proforma; we reply within one business day.",
        "Übernehmen Sie die Linker-Produkte in Ihren Lösungsentwurf und fordern Sie eine Proforma an; "
        "wir antworten innerhalb eines Werktags.",
    ),
    "next.installer": (
        "Before ordering, confirm the string layout with the module you install, the cable routes and the grid connection on site.",
        "Prüfen Sie vor der Bestellung die Stringauslegung mit dem tatsächlich verbauten Modul, die Leitungswege "
        "und den Netzanschluss vor Ort.",
    ),
    "limit.no_payback": (
        "This report contains no economics: no payback period, cash flow or feed-in tariff.",
        "Dieser Bericht enthält keine Wirtschaftlichkeitsrechnung: keine Amortisationszeit, keinen Cashflow, "
        "keine Einspeisevergütung.",
    ),
    "limit.reference_module": (
        "The string layout uses {model} as a reference module; the module you install can change it.",
        "Die Stringauslegung verwendet {model} als Referenzmodul; das tatsächlich verbaute Modul kann sie verändern.",
    ),
    "limit.default_orientation": (
        "Without a roof plane, the yield assumes 35° tilt facing south (HTW Berlin calculator default).",
        "Ohne Dachfläche nimmt der Ertrag 35° Neigung nach Süden an (Vorgabe des HTW-Rechners).",
    ),
    "limit.household": (
        "Self-sufficiency figures describe an average household; measured values differ with each household's habits.",
        "Die Autarkiewerte beschreiben einen durchschnittlichen Haushalt; Messwerte weichen je nach Verbrauchsverhalten ab.",
    ),
    "limit.unverified": (
        "Planning assumption without a published source",
        "Planungsannahme ohne veröffentlichte Quelle",
    ),
    "assume.string_t_min": (
        "Open-circuit voltage checked at −10 °C cell temperature.",
        "Leerlaufspannung geprüft bei −10 °C Zelltemperatur.",
    ),
    "assume.string_t_cell_max": (
        "MPP voltage checked at 70 °C cell temperature, with the module's Voc temperature coefficient.",
        "MPP-Spannung geprüft bei 70 °C Zelltemperatur, mit dem Voc-Temperaturkoeffizienten des Moduls.",
    ),
    "assume.dc_cable_length": (
        "DC cable: 15 m per string and pole until the route is measured.",
        "DC-Kabel: 15 m je Strang und Pol, bis der Leitungsweg aufgemessen ist.",
    ),
    "assume.connector_pairs": (
        "Two connector pairs per string: one at the array, one at the inverter.",
        "Zwei Steckverbinderpaare je Strang: eines am Generator, eines am Wechselrichter.",
    ),
    "assume.pvgis_timeout": (
        "PVGIS requests time out after 120 s.",
        "PVGIS-Anfragen brechen nach 120 s ab.",
    ),
    "assume.roof_flat": (
        "Roof planes below 10° count as flat; module rows face south.",
        "Dachflächen unter 10° gelten als flach; Modulreihen zeigen nach Süden.",
    ),
    "assume.roof_max_tilt": (
        "Roof planes steeper than 60° carry no modules.",
        "Dachflächen steiler als 60° tragen keine Module.",
    ),
    "assume.roof_north": (
        "Pitched planes facing within 45° of north carry no modules.",
        "Geneigte Flächen mit Ausrichtung innerhalb von 45° um Nord tragen keine Module.",
    ),
    "assume.roof_edge_inset": (
        "Modules keep 0.3 m from every roof edge.",
        "Module halten 0,3 m Abstand zu jeder Dachkante.",
    ),
    "assume.module_gap": (
        "Modules sit 2 cm apart for the clamps.",
        "Module liegen für die Klemmen 2 cm auseinander.",
    ),
}


def t(key: str, locale: Locale, **params: object) -> str:
    english, german = _TEXTS[key]
    text = german if locale == "de" else english
    return text.format(**{name: fmt(value, locale) for name, value in params.items()})


def fmt(value: object, locale: Locale, digits: int | None = None) -> str:
    """Numbers in the locale's style (1,234.5 / 1.234,5); other values as they are."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return str(value)
    if value < 0:
        return "\u2212" + fmt(-value, locale, digits)
    if digits is None:
        digits = 1 if abs(value) >= 10 else 2
        text = f"{value:,.{digits}f}".rstrip("0").rstrip(".")
    else:
        text = f"{value:,.{digits}f}"
    if locale == "de":
        text = text.replace(",", "\0").replace(".", ",").replace("\0", ".")
    return text


def tn(key: str, n: float, locale: Locale, /, **params: object) -> str:
    """`key.one` for a count of one where that text exists, else `key.other`."""
    one = f"{key}.one"
    if n == 1 and one in _TEXTS:
        return t(one, locale, **params)
    return t(f"{key}.other", locale, **params)


def has(key: str) -> bool:
    return key in _TEXTS
