"""Report wording shared by its immutable screen model and PDF."""

from __future__ import annotations

TEXT = {
    "title": ("Project planning report", "Projektplanungsbericht"),
    "subtitle": (
        "Saved project inputs and selected calculation results",
        "Gespeicherte Projekteingaben und ausgewählte Berechnungsergebnisse",
    ),
    "status": ("Assessment status", "Prüfstatus"),
    "scope": (
        "This report presents saved project inputs and the original results of the selected calculations. Country-specific requirements, electrical design and installation checks remain open. It does not approve the complete installation.",
        "Dieser Bericht enthält gespeicherte Projekteingaben und die ursprünglichen Ergebnisse der ausgewählten Berechnungen. Landesspezifische Anforderungen sowie die elektrische Auslegung und die Installation müssen noch geprüft werden. Der Bericht erteilt keine Freigabe für die Gesamtanlage.",
    ),
    "project": ("Project", "Projekt"),
    "project_id": ("Project reference", "Projektreferenz"),
    "revision": ("Input revision", "Eingabeversion"),
    "site": ("Site and project inputs", "Standort und Projekteingaben"),
    "location": ("Location", "Standort"),
    "country": ("Country", "Land"),
    "timezone": ("Time zone", "Zeitzone"),
    "note": ("Project note", "Projektnotiz"),
    "equipment": ("Equipment checks", "Prüfung der Geräteauswahl"),
    "satisfied": ("Checked requirements met", "Geprüfte Anforderungen erfüllt"),
    "violated": ("Requirements not met", "Anforderungen nicht erfüllt"),
    "unresolved": ("Further checks required", "Weitere Prüfung erforderlich"),
    "actual": ("Result", "Ergebnis"),
    "required": ("Requirement", "Anforderung"),
    "data_source": ("Data source", "Datenquelle"),
    "source": ("Source document", "Quelldokument"),
    "page": ("Page", "Seite"),
    "conditions": (
        "Components and manufacturer conditions",
        "Komponenten und Herstellervorgaben",
    ),
    "country_open": (
        "Country requirements are not assessed by the selected calculations.",
        "Landesspezifische Anforderungen werden in den ausgewählten Berechnungen nicht bewertet.",
    ),
    "bom": ("Provisional bill of materials", "Vorläufige Stückliste"),
    "bom_scope": (
        "This provisional list comes from the selected saved equipment result. Quantities are shown only where established. It is not a complete installation bill of materials. Further components and open requirements need project-specific assessment.",
        "Diese vorläufige Stückliste stammt aus dem ausgewählten gespeicherten Ergebnis zur Geräteauswahl. Mengen werden nur angegeben, soweit sie ermittelt sind. Die Liste ist noch keine vollständige Stückliste für die Installation. Weitere Komponenten und offene Anforderungen müssen projektspezifisch geprüft werden.",
    ),
    "quantity": ("Quantity", "Menge"),
    "product": ("Product", "Produkt"),
    "model": ("Model", "Modell"),
    "reference": ("Reference", "Referenz"),
    "energy": ("Energy scenario", "Energieszenario"),
    "energy_equipment": (
        "Energy scenario and selected equipment",
        "Energieszenario und ausgewählte Geräte",
    ),
    "energy_equipment_scope": (
        "These checks compare the saved scenario parameters with the equipment selected for this calculation. They do not establish manufacturer performance.",
        "Diese Prüfung vergleicht die gespeicherten Szenarioparameter mit den für die Berechnung ausgewählten Geräten. Die Leistungsfähigkeit der Geräte wird dadurch nicht nachgewiesen.",
    ),
    "check": ("Check", "Prüfung"),
    "scenario_scope": (
        "These values come from the selected saved energy result and reflect its original scenario parameters. The general energy-flow model does not establish the performance of the selected equipment.",
        "Die Werte stammen aus dem gespeicherten Ergebnis der ausgewählten Energieberechnung und beruhen auf den damaligen Szenarioparametern. Das allgemeine Energiemodell belegt nicht die Leistungsfähigkeit der ausgewählten Geräte.",
    ),
    "pv": ("PV generation scenario", "PV-Erzeugungsszenario"),
    "pv_scope": (
        "This section presents the selected saved PV profile and its original assumptions. Detailed shading and electrical design require separate assessment.",
        "Dieser Abschnitt zeigt das ausgewählte gespeicherte PV-Profil mit den damaligen Annahmen. Detaillierte Verschattung und elektrische Auslegung müssen gesondert geprüft werden.",
    ),
    "period": ("Calculation period (UTC)", "Berechnungszeitraum (UTC)"),
    "intervals": ("Calculated intervals", "Berechnete Intervalle"),
    "generation": ("PV generation", "PV-Erzeugung"),
    "load": ("Simulated load demand", "Simulierter Strombedarf"),
    "import": ("Grid import", "Netzbezug"),
    "export": ("PV export", "PV-Einspeisung"),
    "curtailed": ("PV curtailment", "PV-Abregelung"),
    "unserved": ("Unserved simulated load", "Ungedeckter simulierter Strombedarf"),
    "autarky": (
        "Solar share of gross demand",
        "Solarer Deckungsanteil am Gesamtbedarf",
    ),
    "self_use": (
        "PV used or stored on site",
        "PV-Energie für Verbrauch und Speicherung vor Ort",
    ),
    "not_defined": (
        "Not defined for this calculation",
        "Für diese Berechnung nicht definiert",
    ),
    "basis": (
        "Saved calculation references",
        "Referenzen der gespeicherten Berechnungen",
    ),
    "run": ("Calculation reference", "Berechnungsreferenz"),
    "credits": (
        "Sources and methods are identified in this report.",
        "Quellen und Methoden sind in diesem Bericht angegeben.",
    ),
}

CHECKS = {
    "converter_identity": ("Converter output", "Ausgang des Umrichters"),
    "grid_phase": ("Grid phases", "Netzphasen"),
    "pv_dc_input": ("PV input power", "PV-Eingangsleistung"),
    "pv_electrical_topology": ("PV strings and inputs", "PV-Strings und Eingänge"),
    "manufacturer_pair": ("Manufacturer pairing", "Herstellerangaben zur Kombination"),
    "modules_per_stack": ("Module count", "Anzahl der Module"),
    "parallel_stacks": ("Parallel arrangement", "Parallelschaltung"),
    "required_accessory": ("Required accessory", "Erforderliches Zubehör"),
    "battery_voltage": ("Battery voltage", "Batteriespannung"),
    "battery_sales_unit": ("Sales unit", "Verkaufseinheit"),
    "usable_energy": ("Usable energy", "Nutzbare Speicherenergie"),
    "continuous_battery_ac_output": (
        "Continuous AC discharge power",
        "AC-Dauerleistung bei Entladung",
    ),
    "continuous_battery_ac_charge": (
        "Continuous AC charge power",
        "AC-Dauerleistung bei Ladung",
    ),
    "scenario_operating_mode": ("Scenario operating mode", "Betriebsart im Szenario"),
    "scenario_parameter_basis": (
        "Storage losses and operating conditions",
        "Speicherverluste und Betriebsbedingungen",
    ),
    "scenario_model_domain": (
        "Converter ports and system topology",
        "Umrichteranschlüsse und Systemtopologie",
    ),
    "battery_discharge_path": ("Battery discharge path", "Entladepfad der Batterie"),
    "backup_mode": ("Backup transfer", "Umschaltung auf Ersatzstrom"),
    "integrated_sales_unit": (
        "Integrated storage system",
        "Integriertes Speichersystem",
    ),
    "accessory_quantity": ("Accessory quantity", "Menge des Zubehörs"),
}


def text(key: str, locale: str) -> str:
    return TEXT[key][1 if locale == "de" else 0]


def check_label(key: str, locale: str) -> str:
    return CHECKS.get(key.split(":")[0], TEXT["equipment"])[1 if locale == "de" else 0]
