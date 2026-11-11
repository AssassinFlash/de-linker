"""Report wording shared by its immutable screen model and PDF."""

from __future__ import annotations

TEXT = {
    "geometric_pv_series_tracker": (
        "Tracker / input / modules",
        "Tracker / Eingang / Module",
    ),
    "geometric_pv_series_window": (
        "Cited tracker window / maximum current",
        "Belegter Tracker-Spannungsbereich / maximaler Strom",
    ),
    "geometric_pv_series_peak": (
        "Scenario peak string current / DC power",
        "Höchster Strangstrom / DC-Leistung im Szenario",
    ),
    "geometric_pv_title_series": (
        "PV reference with geometric shading and series I–V",
        "PV-Referenz mit geometrischer Verschattung und String-I–V",
    ),
    "geometric_pv_scope_series": (
        "The declared geometry and weather determine each module's irradiance and temperature. A fitted whole-module single-diode curve combines the assigned modules at a common string current; one string per tracker is evaluated within the cited voltage and current limits, followed by the declared PVWatts converter scenario. This is not a validated manufacturer performance curve. Partial-cell shading, bypass diodes, reverse breakdown, parallel strings on one tracker, real MPPT dynamics and equipment or country approval remain unassessed.",
        "Die angegebene Geometrie und Wetterquelle bestimmen Einstrahlung und Temperatur jedes Moduls. Eine angepasste Eindiodenkennlinie für das gesamte Modul verbindet die zugeordneten Module über einen gemeinsamen Stringstrom. Je Tracker wird ein String innerhalb der belegten Spannungs- und Stromgrenzen berechnet; anschließend folgt das angegebene PVWatts-Wechselrichterszenario. Dies ist keine validierte Herstellerkennlinie. Teilzellverschattung, Bypassdioden, Rückwärtsdurchbruch, parallele Strings an einem Tracker, das tatsächliche MPPT-Verhalten sowie Geräte- und Länderfreigaben bleiben ungeprüft.",
    ),
    "geometric_pv_title": (
        "PV reference with geometric direct-beam shading",
        "PV-Referenz: geometrische Verschattung der Direktstrahlung",
    ),
    "geometric_pv_title_perez": (
        "PV reference with geometric direct and Perez diffuse shading",
        "PV-Referenz: geometrische Verschattung der Direktstrahlung und der diffusen Perez-Anteile",
    ),
    "geometric_pv_scope": (
        "The declared opaque geometry reduces only direct irradiance. Sky and ground diffuse irradiance retain an unobstructed reference. Each module is treated as uniformly irradiated, and its temperature uses the mean plane-of-array irradiance. Partial-cell shading, bypass diodes, string I–V and real MPPT behavior are not modelled. This scenario does not establish actual device performance or equipment or country approval.",
        "Die angegebene undurchsichtige Geometrie verringert ausschließlich die direkte Einstrahlung. Diffuse Himmels- und Bodenstrahlung bleiben als unverschattete Referenz erhalten. Für Leistung und Zelltemperatur wird die über das jeweilige Modul gemittelte Einstrahlung angesetzt. Teilzellverschattung, Bypassdioden, die I–V-Kennlinie der Strings und das reale MPPT-Verhalten werden nicht modelliert. Dieses Szenario belegt weder die tatsächliche Geräteleistung noch eine Geräte- oder Länderfreigabe.",
    ),
    "geometric_pv_scope_perez": (
        "The declared opaque geometry reduces direct irradiance, the Perez isotropic and circumsolar components, a positive horizon term, and ground-reflected irradiance, by cosine-weighted visible fractions. Circumsolar light uses the same direct-beam visibility. A negative Perez horizon term is a signed correction from the pinned coefficient set and is retained unchanged. Isotropic sky, the horizon ring and ground are sampled once for each module. Rays into the module back are excluded, including downward rays that would otherwise be treated as ground light. A recomposed sky below zero is set to zero, and the removed amount is recorded. Each module is treated as uniformly irradiated, and its temperature uses the mean plane-of-array irradiance. Partial-cell shading, bypass diodes, string I–V and real MPPT behavior are not modelled. This scenario does not establish complete shading accuracy, a sampling error bound, actual device performance, or equipment or country approval.",
        "Die angegebene undurchsichtige Geometrie verringert die direkte Einstrahlung, die isotropen und zirkumsolaren Perez-Anteile, einen positiven horizontnahen Anteil und die vom Boden reflektierte Einstrahlung, jeweils mit dem kosinusgewichteten sichtbaren Anteil. Zirkumsolares Licht verwendet dieselbe Sichtbarkeit wie die Direktstrahlung. Ein negativer Perez-Horizontterm ist eine vorzeichenbehaftete Korrektur aus dem festgelegten Koeffizientensatz und bleibt unverändert erhalten. Der isotrope Himmel, der Horizontkreis und der Boden werden je Modul einmal abgetastet. Strahlen auf die Modulrückseite zählen nicht, auch nicht abwärts gerichtete Strahlen, die sonst als Bodenlicht gewertet würden. Eine neu zusammengesetzte Himmelstrahlung unter null wird auf null gesetzt, und der abgezogene Betrag wird festgehalten. Für Leistung und Zelltemperatur wird die über das jeweilige Modul gemittelte Einstrahlung angesetzt. Teilzellverschattung, Bypassdioden, die I–V-Kennlinie der Strings und das reale MPPT-Verhalten werden nicht modelliert. Dieses Szenario belegt weder eine vollständige Verschattungsgenauigkeit, eine Fehlerschranke der Abtastung, die tatsächliche Geräteleistung noch eine Geräte- oder Länderfreigabe.",
    ),
    "geometric_pv_axes": (
        "All rows of the retained weather source are used. Interval boundaries belong to the synthetic energy year; solar position retains the original source-month irradiance instants. Calculated point outputs are assigned to those intervals under the stated reconstruction policy. The difference between coarse and fine sampling is not an error bound.",
        "Alle Zeilen der gespeicherten Wetterquelle werden verwendet. Die Intervallgrenzen gehören zum synthetischen Energiejahr; für den Sonnenstand gelten die Strahlungszeitpunkte der ursprünglichen Quellenmonate. Die berechneten Punktwerte werden den Intervallen nach der angegebenen Rekonstruktionsregel zugeordnet. Die Differenz zwischen grobem und feinem Raster ist keine Fehlerschranke.",
    ),
    "geometric_pv_notes_scope_perez": (
        "Notes on coefficients and mounting are preserved verbatim from the reference inputs. Their descriptions of the original unshaded reference are source context. This calculation applies the geometric Perez component-visibility model and the diffuse, thermal and electrical assumptions stated above. Displayed numbers are rounded; the frozen source retains full precision.",
        "Hinweise zu Koeffizienten und Montage werden im ursprünglichen Wortlaut der Referenzeingaben wiedergegeben. Aussagen darin zur ursprünglichen unverschatteten Referenz dienen als Quellenkontext. Für diese Berechnung gelten das geometrische Perez-Komponentenmodell und die oben angegebenen Annahmen zu diffuser Einstrahlung, Temperatur und elektrischem Verhalten. Zahlen sind für die Anzeige gerundet; die gespeicherte Quelle enthält die volle Genauigkeit.",
    ),
    "geometric_pv_notes_scope": (
        "Notes on coefficients and mounting are preserved verbatim from the reference inputs. Their descriptions of the original unshaded reference are source context. This calculation applies the geometric direct-beam model and the diffuse, thermal and electrical assumptions stated above. Displayed numbers are rounded; the frozen source retains full precision.",
        "Hinweise zu Koeffizienten und Montage werden im ursprünglichen Wortlaut der Referenzeingaben wiedergegeben. Aussagen darin zur ursprünglichen unverschatteten Referenz dienen als Quellenkontext. Für diese Berechnung gelten das oben erläuterte geometrische Direktstrahlungsmodell und die angegebenen Annahmen zu diffuser Einstrahlung, Temperatur und elektrischem Verhalten. Zahlen sind für die Anzeige gerundet; die gespeicherte Quelle enthält die volle Genauigkeit.",
    ),
    "geometric_pv_original_note": (
        "Original coefficient or mounting note (verbatim; current method above)",
        "Ursprünglicher Hinweis zu Koeffizienten oder Montage (Wortlaut; aktuelle Methode oben)",
    ),
    "geometric_pv_model": ("Reference model", "Referenzmodell"),
    "geometric_pv_period": (
        "Complete PV calculation period (UTC)",
        "Vollständiger PV-Berechnungszeitraum (UTC)",
    ),
    "geometric_pv_rows": (
        "Retained source intervals",
        "Gespeicherte Quellenintervalle",
    ),
    "geometric_pv_energy": ("Scenario AC energy", "AC-Energie des Szenarios"),
    "geometric_pv_sampling": (
        "Cells per module edge: coarse / fine",
        "Zellen je Modulkante: grob / fein",
    ),
    "geometric_pv_weather": (
        "TMY source years / radiation / weather database",
        "TMY-Quellenjahre / Strahlungs- / Wetterdatenbank",
    ),
    "geometric_pv_year": ("Synthetic interval year", "Synthetisches Intervalljahr"),
    "geometric_pv_used_by": (
        "Used by saved run / revision",
        "Verwendet von Berechnung / Revision",
    ),
    "direct_beam_title": (
        "Geometric direct-beam visibility",
        "Geometrische Sichtbarkeit direkter Sonnenstrahlung",
    ),
    "direct_beam_scope": (
        "This witness covers only the selected weather rows and declared opaque roof surfaces, obstacle extrusions and included modules. Fractions describe geometric visibility of direct sunlight. They are not power or energy losses and do not establish annual yield, diffuse light, reflections, electrical behavior, complete shading assessment or equipment or country approval. The difference between the two sampling grids is an observed resolution difference, not an error bound.",
        "Dieser Nachweis umfasst nur die ausgewählten Wetterzeilen und die angegebenen undurchsichtigen Dachflächen, extrudierten Hindernisse und einbezogenen Module. Die Anteile beschreiben die geometrische Sichtbarkeit direkter Sonnenstrahlung. Sie sind keine Leistungs- oder Energieverluste und belegen weder Jahresertrag, diffuses Licht, Reflexionen, elektrisches Verhalten, eine vollständige Verschattungsbewertung noch eine Geräte- oder Länderfreigabe. Die Differenz zwischen den beiden Abtastgittern ist ein beobachteter Auflösungsunterschied und keine Fehlerschranke.",
    ),
    "direct_beam_axes": (
        "The interval belongs to the synthetic weather time axis. Source labels retain the original selected-month date; solar position uses the irradiance instant including the original reported offset. Module counts are total / sampled / night / back-facing or tangent. The fraction range covers sampled modules only. Resource limits are operational policies, not engineering standards.",
        "Das Intervall gehört zur synthetischen Wetterzeitachse. Quellenzeitstempel behalten das ursprüngliche Datum des ausgewählten Monats bei; für den Sonnenstand gilt der Strahlungszeitpunkt einschließlich des ursprünglich angegebenen Versatzes. Die Modulanzahlen bedeuten gesamt / abgetastet / Nacht / abgewandt oder tangential. Der Anteilsbereich umfasst nur abgetastete Module. Die Ressourcengrenzen sind betriebliche Vorgaben und keine technischen Normen.",
    ),
    "direct_beam_source": (
        "Saved witness / revision",
        "Gespeicherter Nachweis / Revision",
    ),
    "direct_beam_method": (
        "Geometric method / pvlib version",
        "Geometrisches Verfahren / pvlib-Version",
    ),
    "direct_beam_sampling": (
        "Cells per module edge: coarse / fine grid",
        "Zellen je Modulkante: grobes / feines Raster",
    ),
    "direct_beam_counters": (
        "Samples / face intersection checks / bounds checks",
        "Abtastpunkte / Flächenschnittprüfungen / Hüllkörperprüfungen",
    ),
    "direct_beam_limits": (
        "Limits: rows / samples / face checks / bounds checks / BVH leaf size",
        "Grenzen: Zeilen / Abtastpunkte / Flächenprüfungen / Hüllkörperprüfungen / BVH-Blattgröße",
    ),
    "direct_beam_result_hash": (
        "Witness result SHA-256",
        "SHA-256 des Nachweisergebnisses",
    ),
    "direct_beam_manifest_hash": (
        "Witness manifest SHA-256",
        "SHA-256 des Nachweismanifests",
    ),
    "direct_beam_interval": (
        "Synthetic interval (UTC)",
        "Synthetisches Intervall (UTC)",
    ),
    "direct_beam_row": ("Selected source row", "Ausgewählte Quellenzeile"),
    "direct_beam_source_time": (
        "Original source label (UTC)",
        "Ursprünglicher Quellenzeitstempel (UTC)",
    ),
    "direct_beam_irradiance_time": (
        "Irradiance instant (UTC)",
        "Strahlungszeitpunkt (UTC)",
    ),
    "direct_beam_modules": ("Module counts", "Modulanzahlen"),
    "direct_beam_range": (
        "Visible fraction, fine grid: min – max",
        "Sichtbarer Anteil im feinen Raster: Min. – Max.",
    ),
    "direct_beam_delta": (
        "Maximum observed grid difference",
        "Größter beobachteter Gitterunterschied",
    ),
    "pvlib_selected_dc_group": (
        "Selected DC converter group",
        "Ausgewählte DC-Umwandlungsgruppe",
    ),
    "pvlib_dc_energy": (
        "Modelled DC generation of the selected group",
        "Modellierte DC-Erzeugung der ausgewählten Gruppe",
    ),
    "pvlib_dc_scope": (
        "This section covers only the selected converter group's arrays and retained DC output after the declared DC factors, before reference AC conversion. The reference AC conversion parameters are source context and are not applied to this DC output. The source period and synthetic time axis retain their original meaning; the separate energy calculation has its own operating period. Nearby and inter-row shading, real MPPT limits and equipment or country approval are not assessed. Array azimuth is measured clockwise from north.",
        "Dieser Abschnitt umfasst nur die Modulfelder der ausgewählten Umwandlungsgruppe und deren gespeicherte DC-Erzeugung nach Anwendung der angegebenen DC-Faktoren, vor der Referenzumwandlung in AC. Die AC-Umwandlungsparameter dienen als Quellenkontext und werden auf diese DC-Erzeugung nicht angewendet. Quellzeitraum und synthetische Zeitachse behalten ihre ursprüngliche Bedeutung; die gesonderte Energieberechnung hat ihren eigenen Betriebszeitraum. Verschattung durch nahe Objekte und zwischen Modulreihen, reale MPPT-Grenzen sowie Geräte- oder Länderfreigaben werden nicht bewertet. Der Azimut des Modulfelds wird ab Norden im Uhrzeigersinn angegeben.",
    ),
    "pvlib_reference": (
        "Weather-based PV reference: sources and assumptions",
        "Wetterbasierte PV-Referenz: Quellen und Annahmen",
    ),
    "pvlib_reference_scope": (
        "This unshaded reference uses typical weather assembled from the selected source months. Its synthetic calculation year defines only the output time axis. The calculated generation is neither measured generation nor a forecast for that year. Nearby and inter-row shading, real MPPT limits, device-specific inverter behavior and equipment or country approval are not assessed. The generic conversion model uses only the stated parameters; no additional PVGIS system-loss percentage is applied. The AC total shown covers the complete retained PV reference period. The separate energy calculation uses its own period and AC or DC input selection. Array azimuth is measured clockwise from north.",
        "Diese unverschattete Referenz verwendet ein aus den ausgewählten Quellmonaten zusammengesetztes typisches Wetterjahr. Das synthetische Berechnungsjahr legt nur die Zeitachse der Ausgabe fest. Die berechnete Erzeugung ist weder ein Messwert noch eine Prognose für dieses Jahr. Verschattung durch nahe Objekte und zwischen Modulreihen, reale MPPT-Grenzen, das gerätespezifische Verhalten eines Wechselrichters sowie Geräte- oder Länderfreigaben werden nicht bewertet. Das allgemeine Umwandlungsmodell verwendet nur die angegebenen Parameter; es wird kein zusätzlicher PVGIS-Systemverlust angesetzt. Die angegebene AC-Gesamtenergie gilt für den vollständigen Zeitraum der gespeicherten PV-Referenz. Für die gesonderte Energieberechnung gelten ihr eigener Zeitraum und die gewählte AC- oder DC-Eingangsgröße. Der Azimut des Modulfelds wird ab Norden im Uhrzeigersinn angegeben.",
    ),
    "pvlib_thermal_scope": (
        "The stated SAPM thermal coefficients are reference assumptions. Their applicability to the saved module clearance and actual ventilation has not been established. Source notes retain the original declared wording. Each source below belongs to its named calculation; different scenarios are not added together.",
        "Die angegebenen thermischen SAPM-Koeffizienten sind Referenzannahmen. Ihre Eignung für den gespeicherten Abstand der Modulunterkante zur Dachfläche und die tatsächliche Hinterlüftung ist nicht nachgewiesen. Die Quellenhinweise bleiben im ursprünglichen Wortlaut erhalten. Jede nachfolgende Quelle gehört zur genannten Berechnung; unterschiedliche Szenarien werden nicht addiert.",
    ),
    "pvlib_model": (
        "PV model / library version",
        "PV-Modell / Bibliotheksversion",
    ),
    "pvlib_weather_period": (
        "Typical-weather source selection period",
        "Auswahlzeitraum des typischen Wetterjahres",
    ),
    "pvlib_meteo_database": (
        "Meteorological database",
        "Meteorologische Datenbank",
    ),
    "pvlib_synthetic_year": (
        "Synthetic energy-axis year",
        "Synthetisches Jahr der Energiezeitachse",
    ),
    "pvlib_offset": (
        "Original irradiance time offset (hours / microseconds)",
        "Ursprünglicher Strahlungszeitversatz (Stunden / Mikrosekunden)",
    ),
    "pvlib_selected_months": (
        "Selected source month: year (January to December)",
        "Ausgewählter Quellmonat: Jahr (Januar bis Dezember)",
    ),
    "pvlib_temporal": (
        "PV interval reconstruction policy",
        "Rekonstruktionsverfahren der PV-Zeitintervalle",
    ),
    "pvlib_solar_dates": (
        "Solar-position date basis",
        "Datumsgrundlage der Sonnenposition",
    ),
    "pvlib_radiation_semantics": (
        "Native radiation time semantics",
        "Ursprüngliche zeitliche Bedeutung der Strahlungswerte",
    ),
    "pvlib_original_request": (
        "Original official JRC weather request",
        "Ursprüngliche offizielle JRC-Wetteranfrage",
    ),
    "pvlib_capture_time": (
        "Original response received (UTC)",
        "Ursprüngliche Antwort empfangen (UTC)",
    ),
    "pvlib_note": (
        "Original reference assumption or applicability note",
        "Ursprünglicher Hinweis zu Referenzannahmen oder Anwendbarkeit",
    ),
    "pvlib_module": (
        "Included modules: quantity × model / module STC; document SHA-256 / page",
        "Enthaltene Module: Anzahl × Modell / Modul-STC; Dokument-SHA-256 / Seite",
    ),
    "pvlib_array": (
        "Array identity",
        "Kennung des Modulfelds",
    ),
    "pvlib_array_geometry": (
        "Array: module count / STC / tilt / azimuth clockwise from north / ENU normal",
        "Modulfeld: Module / STC / Neigung / Azimut / ENU-Normale",
    ),
    "pvlib_clearance": (
        "Saved module lower-edge clearance",
        "Gespeicherter Abstand der Modulunterkante zur Dachfläche",
    ),
    "pvlib_gamma": (
        "Module power temperature coefficient",
        "Temperaturkoeffizient der Modulleistung",
    ),
    "pvlib_transposition": (
        "Transposition model / albedo",
        "Transpositionsmodell / Albedo",
    ),
    "pvlib_iam": (
        "Incidence modifier: model / beam b0 / sky diffuse / ground diffuse",
        "Einfallswinkelkorrektur: Modell / direkt b0 / Himmel diffus / Boden diffus",
    ),
    "pvlib_retention": (
        "Retained fractions: spectral / soiling / DC wiring / DC mismatch",
        "Verbleibende Anteile: Spektrum / Verschmutzung / DC-Verkabelung / DC-Mismatch",
    ),
    "pvlib_thermal": (
        "Thermal model: a / b (s/m) / delta T (°C)",
        "Temperaturmodell: a / b (s/m) / delta T (°C)",
    ),
    "pvlib_converter": (
        "Generic converter identity / assigned arrays",
        "Kennung des allgemeinen Umwandlungsmodells / zugeordnete Modulfelder",
    ),
    "pvlib_conversion": (
        "Conversion model / DC input assumption",
        "Umwandlungsmodell / Annahme zum DC-Eingang",
    ),
    "pvlib_conversion_power": (
        "Converter reference DC power / modelled AC cap",
        "DC-Referenzleistung des Umwandlungsmodells / modellierte AC-Obergrenze",
    ),
    "pvlib_conversion_eta": (
        "Conversion efficiency: nominal / reference",
        "Umwandlungswirkungsgrad: nominal / Referenz",
    ),
    "pvlib_evidence": (
        "Frozen source artifact / SHA-256",
        "Eingefrorener Quellnachweis / SHA-256",
    ),
    "pvgis_roof_reference": (
        "PVGIS roof AC reference",
        "PVGIS-Referenz der AC-PV-Erzeugung",
    ),
    "pvgis_roof_reference_scope": (
        "PVGIS models AC generation for the saved roof in the stated calendar year, using the stated reference technology, mounting type and system loss setting. Device-specific inverter behavior, nearby obstacles and shading between module rows are outside this model. Electrical design and grid acceptance require separate assessment.",
        "Die AC-Erzeugung der gespeicherten Dachbelegung wird mit PVGIS für das angegebene Kalenderjahr berechnet. Es gelten die angegebene Referenztechnologie, Montageart und Verlustannahme. Das gerätespezifische Verhalten eines Wechselrichters, nahe Hindernisse und die Verschattung zwischen Modulreihen bildet dieses Modell nicht ab. Elektrische Auslegung und Netzfreigabe sind gesondert zu prüfen.",
    ),
    "pvgis_calendar_year": ("Calendar year", "Kalenderjahr"),
    "pvgis_radiation_database": ("Radiation database", "Strahlungsdatenbank"),
    "pvgis_reference_technology": ("PV reference technology", "PV-Referenztechnologie"),
    "pvgis_mounting_type": ("PVGIS mounting type", "PVGIS-Montageart"),
    "pvgis_mounting_free": ("Free-standing (free)", "Freistehend (free)"),
    "pvgis_mounting_building": (
        "Building-integrated (building)",
        "Gebäudeintegriert (building)",
    ),
    "pvgis_system_loss": ("PVGIS system loss setting", "PVGIS-Systemverlustannahme"),
    "pvgis_terrain_horizon": ("Terrain horizon", "Geländehorizont"),
    "pvgis_horizon_included": ("Included", "Berücksichtigt"),
    "pvgis_horizon_omitted": ("Omitted", "Nicht berücksichtigt"),
    "pvgis_reference_note": (
        "Reference model assumption note",
        "Annahmen zum Referenzmodell",
    ),
    "pvgis_ac_energy": ("Modelled AC generation", "Modellierte AC-Erzeugung"),
    "pvgis_source_run": (
        "Source calculation / input revision",
        "Quellberechnung / Eingabeversion",
    ),
    "pvgis_array_source": ("PVGIS source for array", "PVGIS-Quelle der Modulfläche"),
    "certificate_condition_title": (
        "Project device details",
        "Geräteangaben im Projekt",
    ),
    "certificate_condition_scope": (
        "The model and device firmware/software values below were entered for this project. Each comparison refers only to the first page of the named document. A matching field does not establish that the device or installation meets all document conditions.",
        "Die folgenden Angaben zu Modell und Gerätefirmware bzw. Gerätesoftware wurden für dieses Projekt erfasst. Jeder Abgleich bezieht sich nur auf die erste Seite der genannten Unterlage. Eine übereinstimmende Angabe weist nicht nach, dass das Gerät oder die Installation alle Bedingungen der Unterlage erfüllt.",
    ),
    "certificate_condition_source_run": ("Source calculation", "Quellberechnung"),
    "certificate_condition_source_revision": (
        "Source input revision",
        "Eingabeversion der Quellberechnung",
    ),
    "certificate_condition_source_candidate": (
        "Source equipment candidate",
        "Gerätevariante der Quellberechnung",
    ),
    "certificate_condition_recorded_scope": (
        "These device details and comparisons belong to the source calculation and input revision shown here.",
        "Diese Geräteangaben und Abgleiche gehören zur hier genannten Quellberechnung und deren Eingabeversion.",
    ),
    "certificate_condition_device_empty": (
        "No certificate or related product document was recorded for this device.",
        "Für dieses Gerät wurden keine Zertifikate oder zugehörigen Produktunterlagen erfasst.",
    ),
    "certificate_condition_identity": (
        "Declared model and selected product model",
        "Angegebene Modellbezeichnung und Modell des ausgewählten Produkts",
    ),
    "certificate_condition_identity_unprovided": (
        "Project model not entered",
        "Kein Projektmodell erfasst",
    ),
    "certificate_condition_identity_same_text": (
        "Model text is identical",
        "Modellbezeichnungen sind wortgleich",
    ),
    "certificate_condition_identity_different_text": (
        "Model text differs; identity needs clarification",
        "Modellbezeichnungen weichen ab; Zuordnung ungeklärt",
    ),
    "certificate_condition_reference": ("Device reference", "Gerätereferenz"),
    "certificate_condition_single": ("Individual selection", "Einzelauswahl"),
    "certificate_condition_unit": ("System {identity}", "System {identity}"),
    "certificate_condition_controller": (
        "Shared controller for group {identity}",
        "Gemeinsamer Controller der Gruppe {identity}",
    ),
    "certificate_condition_inverter": ("Inverter", "Wechselrichter"),
    "certificate_condition_battery": ("Battery", "Batterie"),
    "certificate_condition_accessory": ("Accessory", "Zubehör"),
    "certificate_condition_product": ("Product ID", "Produkt-ID"),
    "certificate_condition_product_revision": (
        "Recorded product revision",
        "Erfasster Produktstand",
    ),
    "certificate_condition_woo_model": (
        "Selected product model",
        "Modell des ausgewählten Produkts",
    ),
    "certificate_condition_declared_model": (
        "Model recorded for this project",
        "Im Projekt erfasstes Modell",
    ),
    "certificate_condition_declared_firmware": (
        "Device firmware/software recorded for this project",
        "Im Projekt erfasste Gerätefirmware bzw. Gerätesoftware",
    ),
    "certificate_condition_source_note": (
        "Source of project entry",
        "Quelle der Projektangabe",
    ),
    "certificate_condition_document": ("Document ID", "Dokument-ID"),
    "certificate_condition_model_comparison": ("Model comparison", "Modellabgleich"),
    "certificate_condition_firmware_comparison": (
        "Firmware comparison",
        "Firmwareabgleich",
    ),
    "certificate_condition_compared_model": (
        "Compared model designation",
        "Verglichene Modellbezeichnung",
    ),
    "certificate_condition_compared_firmware": (
        "Compared firmware entry",
        "Verglichene Firmwareangabe",
    ),
    "certificate_condition_basis": ("Comparison basis", "Grundlage des Abgleichs"),
    "certificate_condition_project_declared": ("Project entry", "Projektangabe"),
    "certificate_condition_selected_woo_model": (
        "Selected product model",
        "Modell des ausgewählten Produkts",
    ),
    "certificate_condition_listed": (
        "Model listed on this page",
        "Modell auf dieser Seite aufgeführt",
    ),
    "certificate_condition_not_listed": (
        "Model not listed on this page",
        "Modell auf dieser Seite nicht aufgeführt",
    ),
    "certificate_condition_model_unresolved": (
        "Model comparison unresolved",
        "Modellabgleich offen",
    ),
    "certificate_condition_exact_match": (
        "Firmware text matches",
        "Firmwareangabe stimmt überein",
    ),
    "certificate_condition_conflict": (
        "Firmware text differs",
        "Firmwareangabe weicht ab",
    ),
    "certificate_condition_firmware_unresolved": (
        "Firmware comparison unresolved",
        "Firmwareabgleich offen",
    ),
    "certificate_condition_detail": ("Comparison detail", "Erläuterung zum Abgleich"),
    "certificate_condition_model_field_unresolved": (
        "An explicit model list could not be read from this document’s first page.",
        "Auf der ersten Seite dieser Unterlage konnte keine eindeutige Modellliste ausgelesen werden.",
    ),
    "certificate_condition_project_model_unresolved": (
        "The project model entry is not a single model designation that can be compared literally.",
        "Die Modellangabe im Projekt ist keine einzelne Typenbezeichnung, die sich wortgetreu abgleichen lässt.",
    ),
    "certificate_condition_literal_model_list_match": (
        "The compared model appears exactly in the explicit model list on page 1.",
        "Die verglichene Modellbezeichnung ist in der eindeutigen Modellliste auf Seite 1 genau so genannt.",
    ),
    "certificate_condition_literal_model_not_listed": (
        "The compared model is absent from the explicit model list on page 1.",
        "Die verglichene Modellbezeichnung fehlt in der eindeutigen Modellliste auf Seite 1.",
    ),
    "certificate_condition_firmware_field_unresolved": (
        "A single firmware version could not be read unambiguously from page 1. Software platforms, version lists and ranges remain unresolved.",
        "Auf Seite 1 konnte kein einzelner Firmwarestand eindeutig ausgelesen werden. Softwareplattformen, Versionslisten und Versionsbereiche bleiben ungeklärt.",
    ),
    "certificate_condition_project_firmware_missing": (
        "No firmware version was recorded for this device in the project.",
        "Für dieses Gerät ist im Projekt kein Firmwarestand erfasst.",
    ),
    "certificate_condition_project_firmware_unresolved": (
        "The project firmware entry is not a single version that can be compared literally.",
        "Die Firmwareangabe im Projekt ist keine einzelne Version, die sich wortgetreu abgleichen lässt.",
    ),
    "certificate_condition_literal_firmware_equal": (
        "The project entry and the document’s firmware text are identical. Leading zeros, case and suffixes were retained.",
        "Die Projektangabe stimmt mit der Firmwareangabe der Unterlage überein. Führende Nullen, Groß- und Kleinschreibung sowie Zusätze wurden beibehalten.",
    ),
    "certificate_condition_literal_firmware_different": (
        "The project entry differs from the document’s firmware text. Leading zeros, case and suffixes are part of the comparison.",
        "Die Projektangabe weicht von der Firmwareangabe der Unterlage ab. Führende Nullen, Groß- und Kleinschreibung sowie Zusätze gehören zum Abgleich.",
    ),
    "certificate_condition_not_assessed": ("Not assessed", "Nicht geprüft"),
    "certificate_condition_open_title": (
        "Remaining document and project checks",
        "Offene Prüfungen zu Unterlagen und Projekt",
    ),
    "certificate_condition_document_scope": (
        "Document scope",
        "Geltungsbereich der Unterlage",
    ),
    "certificate_condition_other_pages_and_reports": (
        "Other pages and referenced reports",
        "Weitere Seiten und genannte Berichte",
    ),
    "certificate_condition_annex_conditions": (
        "Annex conditions",
        "Bedingungen der Anhänge",
    ),
    "certificate_condition_hardware_and_configuration": (
        "Hardware and configuration",
        "Hardware und Konfiguration",
    ),
    "certificate_condition_operating_mode": ("Operating mode", "Betriebsart"),
    "certificate_condition_country_and_dso_settings": (
        "Country and grid-operator settings",
        "Länder- und Netzbetreibereinstellungen",
    ),
    "certificate_condition_standard_edition_and_transition": (
        "Standard edition and transition rules",
        "Normausgabe und Übergangsregelungen",
    ),
    "certificate_condition_issuer_current_status": (
        "Current certificate status with the issuer",
        "Aktueller Zertifikatsstatus beim Aussteller",
    ),
    "certificate_condition_project_grid_assessment": (
        "Project grid-connection assessment",
        "Prüfung des projektspezifischen Netzanschlusses",
    ),
    "certificate_condition_dso_permission": (
        "Grid-operator permission",
        "Zustimmung des Netzbetreibers",
    ),
    "certificate_declarations": (
        "Information from the document",
        "Angaben aus der Unterlage",
    ),
    "certificate_models": ("Stated model designations", "Genannte Typenbezeichnungen"),
    "certificate_firmware": (
        "Stated firmware or software",
        "Genannte Firmware bzw. Software",
    ),
    "certificate_standards": (
        "Printed standard references",
        "Abgedruckte Normverweise",
    ),
    "certificate_annex": ("Referenced annex", "Genannter Anhang"),
    "certificate_inspection_scope": (
        "The following information was read from labelled fields on the first page of the retained source document. It does not establish that the equipment or project meets the stated conditions. Other pages, reports and referenced annexes require separate assessment.",
        "Die folgenden Angaben wurden aus beschrifteten Feldern auf der ersten Seite der gespeicherten Originalunterlage ausgelesen. Ob die Geräte oder das Projekt die genannten Bedingungen erfüllen, ist damit nicht nachgewiesen. Weitere Seiten, Berichte und genannte Anhänge müssen gesondert bewertet werden.",
    ),
    "certificate_inspection_unavailable": (
        "The source document’s information could not be read. No applicability conclusion was made.",
        "Die Angaben der Originalunterlage konnten nicht ausgelesen werden. Eine Aussage zur Anwendbarkeit wurde nicht getroffen.",
    ),
    "certificate_inspection_limit": (
        "This file exceeds the automatic reading limit. The source document requires separate review; no applicability conclusion was made.",
        "Diese Datei überschreitet die Grenze für das automatische Auslesen. Die Originalunterlage muss gesondert geprüft werden; eine Aussage zur Anwendbarkeit wurde nicht getroffen.",
    ),
    "certificate_annex_unverified": (
        "The cover refers to {body} certificate page(s) and {annex} annex pages. The retained PDF has {retained} page(s). The referenced annex and its conditions have not been verified.",
        "Das Deckblatt nennt {body} Zertifikatsseite(n) und {annex} Anhangseiten. Die gespeicherte PDF enthält {retained} Seite(n). Der genannte Anhang und seine Bedingungen wurden nicht geprüft.",
    ),
    "certificate_title": (
        "Certificates and related product documents",
        "Zertifikate und zugehörige Produktunterlagen",
    ),
    "certificate_scope": (
        "These documents were linked to the selected products when this result was recorded. Their applicability to this project’s models, firmware, configuration, standard editions and annexes has not been assessed here. Compliance with country-specific requirements, installation approval and grid-operator acceptance require separate evidence.",
        "Diese Unterlagen waren den ausgewählten Produkten zugeordnet, als dieses Ergebnis gespeichert wurde. Ob sie für die Modelle, Firmwarestände und Konfigurationen dieses Projekts gelten und welche Normausgaben und Anhänge maßgeblich sind, wurde hier nicht geprüft. Die Erfüllung landesspezifischer Anforderungen, die Freigabe der Installation und die Zustimmung des Netzbetreibers müssen gesondert nachgewiesen werden.",
    ),
    "certificate_empty": (
        "No certificates or related product documents were recorded for the selected products.",
        "Für die ausgewählten Produkte wurden keine Zertifikate oder zugehörigen Produktunterlagen erfasst.",
    ),
    "certificate_revision": ("Recorded document revision", "Erfasster Dokumentstand"),
    "capacity_reference_title": (
        "Reference scenario using the manufacturer’s usable energy",
        "Referenzszenario mit nutzbarer Energie laut Hersteller",
    ),
    "capacity_reference_published": (
        "Manufacturer’s stated usable energy",
        "Nutzbare Energie laut Hersteller",
    ),
    "capacity_reference_scope": (
        "This reference calculation uses the selected product’s published usable energy as a fixed model window. The manufacturer’s test conditions are shown with the source. Choosing this mode does not establish that they are met. Ageing and changes in usable energy with temperature or charge/discharge rate are not modelled. Conversion and storage losses follow the separate scenario assumptions. Actual deliverable energy is not established.",
        "Diese Referenzberechnung verwendet die vom Hersteller angegebene nutzbare Energie des ausgewählten Produkts als festes Energiefenster im Modell. Die Prüfbedingungen des Herstellers sind beim Quellennachweis angegeben. Die Auswahl dieses Modus bestätigt nicht, dass diese Bedingungen erfüllt sind. Alterung sowie Änderungen der nutzbaren Energie durch Temperatur oder Lade- und Entladerate werden nicht modelliert. Umwandlungs- und Speicherverluste werden nach den gesonderten Szenarioannahmen berechnet. Die tatsächlich abgebbare Energie wird damit nicht nachgewiesen.",
    ),
    "comparison_capacity_basis": (
        "Capacity model differs",
        "Unterschiedliches Kapazitätsmodell",
    ),
    "plant_unit_reserve": (
        "Reserved stored energy",
        "Energiereserve im Speicher",
    ),
    "plant_unit_terminal": (
        "Minimum final stored energy",
        "Gespeicherte Mindestenergie am Ende",
    ),
    "plant_no_terminal_minimum": (
        "No minimum required",
        "Kein Mindestwert erforderlich",
    ),
    "plant_parameter_sources": (
        "Storage assumptions and product data sources",
        "Speicherannahmen und Quellen der Produktdaten",
    ),
    "plant_loss_eta_bus_to_battery": (
        "DC converter: charging efficiency",
        "DC-Wandler: Ladewirkungsgrad",
    ),
    "plant_loss_eta_battery_to_bus": (
        "DC converter: discharging efficiency",
        "DC-Wandler: Entladewirkungsgrad",
    ),
    "plant_loss_eta_store_charge": (
        "Storage: charging efficiency",
        "Speicher: Ladewirkungsgrad",
    ),
    "plant_loss_eta_store_discharge": (
        "Storage: discharging efficiency",
        "Speicher: Entladewirkungsgrad",
    ),
    "plant_loss_eta_inverter_forward": (
        "Inverter: DC to AC efficiency",
        "Wechselrichter: Wirkungsgrad DC zu AC",
    ),
    "plant_loss_eta_inverter_reverse": (
        "Inverter: AC to DC efficiency",
        "Wechselrichter: Wirkungsgrad AC zu DC",
    ),
    "plant_loss_internal_aux_kw": (
        "Internal auxiliary power",
        "Interner Hilfsverbrauch",
    ),
    "plant_loss_standing_loss_rate_per_hour": (
        "Standing-loss coefficient",
        "Koeffizient der zeitabhängigen Speicherverluste",
    ),
    "plant_common_ac_generation": (
        "PV generation at the common AC bus",
        "PV-Erzeugung an der gemeinsamen AC-Sammelschiene",
    ),
    "plant_dc_generation": (
        "DC PV generation after curtailment",
        "DC-PV-Erzeugung nach Abregelung",
    ),
    "plant_dc_stages": (
        "PV generation is shown separately at each DC bus and at the common AC bus. No combined PV self-consumption rate is calculated across these stages.",
        "Die PV-Erzeugung wird für jede DC-Sammelschiene und die gemeinsame AC-Sammelschiene getrennt ausgewiesen. Über diese Stufen hinweg wird keine gemeinsame Eigenverbrauchsquote berechnet.",
    ),
    "scenario_plant_limits": (
        "These results describe the declared scenario. Joint operating capability, continuous equipment performance, backup transfer and country-specific grid compliance are not established by this calculation.",
        "Die Ergebnisse beschreiben das angegebene Szenario. Der gemeinsame Betrieb der Geräte, ihre Dauerleistung, die Notstromumschaltung und die Erfüllung länderspezifischer Netzanforderungen sind durch diese Berechnung nicht nachgewiesen.",
    ),
    "plant_ac_charge_policy": (
        "Charging from the common AC bus",
        "Laden über die gemeinsame AC-Sammelschiene",
    ),
    "plant_ac_charge_on": (
        "Enabled (requires documented AC-to-DC charging)",
        "Aktiviert (AC-Ladung muss dokumentiert sein)",
    ),
    "plant_ac_charge_off": ("Disabled", "Deaktiviert"),
    "plant_pv_group": ("PV conversion group", "PV-Gruppe am Wechselrichter"),
    "plant_pv_unused": ("DC PV inputs unused", "DC-PV-Eingänge ungenutzt"),
    "scenario_dc_plant_scope": (
        "In each interval, each converter supplies its own DC auxiliary demand and its allocated share of AC demand before charging from local DC PV. AC demand is shared in proportion to each unit’s available power. Charging from the AC bus must be enabled and supported by the equipment documentation. It uses remaining AC surplus; grid charging is requested only when separately permitted and within the remaining import limit. This time-step calculation uses no forecast and does not reproduce a manufacturer EMS or an optimal dispatch schedule.",
        "In jedem Zeitintervall versorgt jeder Umrichter zunächst seinen DC-Eigenbedarf und seinen zugeteilten Anteil am AC-Bedarf. Erst danach lädt er den Speicher aus lokaler DC-PV-Erzeugung. Der AC-Bedarf wird im Verhältnis zur verfügbaren Leistung der einzelnen Geräte aufgeteilt. Die AC-Ladung muss aktiviert und durch die Geräteunterlagen belegt sein. Dafür wird der verbleibende AC-Überschuss genutzt. Netzladung wird nur bei gesonderter Freigabe und innerhalb der verbleibenden Netzbezugsgrenze angefordert. Die Berechnung erfolgt schrittweise ohne Prognose und bildet weder ein Hersteller-EMS noch eine optimale Einsatzplanung nach.",
    ),
    "scenario_plant_scope": (
        "This scenario models separate AC PV generation and individual storage units at one shared AC metering point, with the storage converters' DC PV inputs unused. AC PV during outages requires separately established island-operation topology; the availability setting alone is insufficient. Each unit retains its own stored energy by origin, power limits, reserve and loss assumptions; usable storage capacity is held fixed for the stated conditions. Power is allocated proportionally within each unit's power and energy limits for the current interval, without forecasting or optimal dispatch. The calculation does not reproduce a manufacturer EMS or establish joint operating capability, continuous equipment performance, backup transfer or country-specific grid compliance.",
        "Dieses Szenario berechnet die separate AC-PV-Erzeugung und die einzelnen Speichereinheiten an einem gemeinsamen AC-Messpunkt. Die DC-PV-Eingänge der Speicherumrichter sind ungenutzt. AC-PV-Erzeugung bei einem Netzausfall erfordert eine gesondert nachgewiesene Inselbetriebstopologie; die Verfügbarkeitseinstellung allein reicht dafür nicht aus. Für jede Einheit werden gespeicherte Energie nach Herkunft, Leistungsgrenzen, Reserve und Verlustannahmen getrennt geführt; die nutzbare Speicherkapazität wird für die angegebenen Bedingungen als konstant angesetzt. Die Leistung wird für das aktuelle Zeitintervall proportional innerhalb der jeweiligen Leistungs- und Energiegrenzen verteilt, ohne Prognose oder optimale Einsatzplanung. Ein Hersteller-EMS wird damit nicht nachgebildet. Der gemeinsame Betrieb der Geräte, ihre Dauerleistung, die Notstromumschaltung und die Erfüllung länderspezifischer Netzanforderungen sind nicht nachgewiesen.",
    ),
    "plant_unit_window": (
        "Usable storage capacity in this scenario",
        "Nutzbare Speicherkapazität in diesem Szenario",
    ),
    "plant_unit_start": (
        "Initial stored energy",
        "Gespeicherte Energie zu Beginn",
    ),
    "plant_unit_finish": ("Stored energy at end", "Gespeicherte Energie am Ende"),
    "plant_unit_finish_pv_kwh": (
        "Stored PV energy at end",
        "Gespeicherte PV-Energie am Ende",
    ),
    "plant_unit_finish_grid_kwh": (
        "Stored grid energy at end",
        "Gespeicherte Netzenergie am Ende",
    ),
    "plant_unit_finish_initial_unknown_kwh": (
        "Initial energy of unknown origin remaining at end",
        "Am Ende verbleibende Anfangsenergie unbekannter Herkunft",
    ),
    "not_specified": ("Not specified", "Nicht angegeben"),
    "control_network": (
        "Controller communication",
        "Controller-Kommunikation",
    ),
    "controller_network_max": (
        "Maximum supported",
        "Maximal unterstützte Anzahl",
    ),
    "controller_group_size": (
        "Inverters in this group",
        "Wechselrichter in dieser Gruppe",
    ),
    "controller_network_limit_comparison": (
        "The limit applies to the selected controller and network. The operating limits of the inverter group are shown separately.",
        "Die Grenze gilt für den gewählten Controller und seine Netzwerkanbindung. Die Betriebsgrenzen der Wechselrichtergruppe sind separat aufgeführt.",
    ),
    "current_cited_controller_network_limit_required": (
        "The comparison requires a network type and the manufacturer’s inverter limit for that network.",
        "Für den Vergleich sind die Netzwerkanbindung und die dafür vom Hersteller angegebene Höchstzahl der Wechselrichter erforderlich.",
    ),
    "manufacturer_requirement_matches_operating_context": (
        "The documented manufacturer requirement applies to the declared operating mode, topology and communication setup. Firmware, model combination and commissioning still require separate checks.",
        "Die dokumentierte Herstellervorgabe gilt für die angegebene Betriebsart, Topologie und Kommunikationsanbindung. Firmware, Modellkombination und Inbetriebnahme müssen weiterhin gesondert geprüft werden.",
    ),
    "parallel_count_uses_applicable_manufacturer_limit": (
        "Group size is checked only against manufacturer limits documented for the declared operating mode, topology and communication setup. If no applicable limit is documented, it remains unknown.",
        "Die Gerätezahl der Gruppe wird nur mit Herstellergrenzen abgeglichen, die für die angegebene Betriebsart, Topologie und Kommunikationsanbindung dokumentiert sind. Ist keine anwendbare Grenze dokumentiert, bleibt sie unbekannt.",
    ),
    "maximum_grid_output_is_necessary_bound_only": (
        "In grid-connected operation, the requested continuous active power from the battery cannot exceed the applicable documented maximum output of the whole inverter. Where the source gives a maximum apparent power S, |P| ≤ S is a necessary upper bound only; S is not an active-power rating. Passing this check does not establish continuous battery output.",
        "Im Netzparallelbetrieb darf die geforderte dauerhafte Wirkleistungsabgabe der Batterie die dokumentierte maximale Ausgangsleistung des gesamten Wechselrichters nicht überschreiten, sofern diese Angabe für die gewählten Bedingungen gilt. Gibt die Quelle eine maximale Scheinleistung S an, liefert |P| ≤ S lediglich eine notwendige Obergrenze; S darf nicht als Wirkleistungsangabe verwendet werden. Das Einhalten dieser Grenze weist keine Dauerentladeleistung der Batterie nach.",
    ),
    "sales_battery_system": ("Battery system", "Batteriesystem"),
    "sales_battery_module": ("Battery module", "Batteriemodul"),
    "sales_integrated_system": ("Integrated system", "Integriertes System"),
    "plant_scope": (
        "The report presents checks for each recorded system and its coordination group. Shared output, backup transfer and country-specific acceptance remain subject to the open checks.",
        "Der Bericht enthält die Prüfergebnisse für jedes erfasste System und seine Koordinationsgruppe. Die gemeinsame Leistungsabgabe, die Umschaltung auf Notstrombetrieb und die Erfüllung länderspezifischer Anforderungen sind aufgrund der offenen Prüfpunkte noch nicht bestätigt.",
    ),
    "plant_group": ("Coordination group", "Koordinationsgruppe"),
    "grid_connected": ("Grid-connected", "Netzparallelbetrieb"),
    "backup": ("Backup", "Notstrombetrieb"),
    "unit_must_match_plant_connection": (
        "Each system must match the project grid phases and operating mode.",
        "Jedes System muss die im Projekt geforderte Phasenanzahl und Betriebsart unterstützen.",
    ),
    "woo_parallel_count_requires_mode_scope": (
        "The group size is compared with the limit in the product data. Applicability to the declared operating mode and communication setup remains unconfirmed.",
        "Die Anzahl der Geräte in der Gruppe wird mit dem Grenzwert in den Produktdaten verglichen. Ob dieser Wert für die angegebene Betriebsart und Kommunikationsanbindung gilt, ist noch nicht bestätigt.",
    ),
    "mode_model_firmware_and_battery_association_require_scoped_evidence": (
        "Joint operation of this group remains unconfirmed for its operating mode, model combination, firmware versions and battery configuration.",
        "Der gemeinsame Betrieb dieser Gruppe ist hinsichtlich Betriebsart, Modellkombination, Firmwareversionen und Batteriekonfiguration noch nicht bestätigt.",
    ),
    "one_shared_controller_per_declared_group": (
        "The plan specifies one shared controller for the group. Its model and quantity must match the documented manufacturer requirements.",
        "Für die Gruppe ist ein gemeinsamer Controller vorgesehen. Modell und Stückzahl müssen den dokumentierten Herstellervorgaben entsprechen.",
    ),
    "declared_unit_demand_allocation_not_available_plant_output": (
        "These are declared project requirements allocated to individual systems. Available energy and power at the shared connection remain unconfirmed.",
        "Dies sind die den einzelnen Systemen zugewiesenen Projektanforderungen. Die verfügbare Energie und Leistung am gemeinsamen Anschlusspunkt sind noch nicht bestätigt.",
    ),
    "joint_delivery_requires_allocation_and_connection_assessment": (
        "Joint output requires assessment of the individual systems, their allocated requirements and the shared connection.",
        "Die gemeinsame Leistungsabgabe erfordert eine Prüfung der einzelnen Systeme mit ihren zugewiesenen Anforderungen sowie des gemeinsamen Anschlusspunkts.",
    ),
    "pv_fitting_method": ("Fitting method", "Anpassungsmethode"),
    "pv_refinement_method": ("Numerical refinement", "Numerische Verfeinerung"),
    "pv_translation_method": ("Temperature translation", "Temperaturumrechnung"),
    "pv_numerical_tolerance": (
        "Numerical fit tolerance",
        "Numerische Anpassungstoleranz",
    ),
    "pv_noct_irradiance": (
        "NOCT reference irradiance",
        "NOCT-Referenzbestrahlungsstärke",
    ),
    "pv_noct_cell_interval": (
        "NOCT cell-temperature interval",
        "NOCT-Zelltemperaturintervall",
    ),
    "pv_operating_title": (
        "Modeled electrical operating points",
        "Modellierte elektrische Arbeitspunkte",
    ),
    "pv_operating_scope": (
        "These estimates use a fitted single-diode model at the stated uniform module conditions. They do not include shading or establish manufacturer performance, design extremes, protection ratings or country approval.",
        "Diese Schätzwerte beruhen auf einem angepassten Eindiodenmodell bei den angegebenen einheitlichen Modulbedingungen. Sie berücksichtigen keine Verschattung und belegen weder die Leistungsangaben des Herstellers noch Auslegungsextreme, Schutzbemessungen oder eine Länderfreigabe.",
    ),
    "pv_operating_incomplete": (
        "Operating conditions and their source are incomplete.",
        "Betriebsbedingungen und deren Quelle sind noch unvollständig.",
    ),
    "pv_iv_unavailable": (
        "The maintained module data did not produce an admissible I–V model. The cold-Voc and STC checks remain available.",
        "Aus den gepflegten Moduldaten konnte kein zulässiges I–V-Modell ermittelt werden. Die Prüfungen der Leerlaufspannung bei Kälte und unter STC bleiben verfügbar.",
    ),
    "pv_effective_irradiance": ("Effective irradiance", "Effektive Bestrahlungsstärke"),
    "pv_hot_cell": (
        "Hot operating cell temperature",
        "Zelltemperatur bei heißem Betrieb",
    ),
    "pv_cold_cell": (
        "Cold operating cell temperature",
        "Zelltemperatur bei kaltem Betrieb",
    ),
    "pv_case": ("Case", "Betriebsfall"),
    "pv_hot_case": ("Hot operating case", "Heißer Betriebsfall"),
    "pv_cold_case": ("Cold operating case", "Kalter Betriebsfall"),
    "pv_model_details": (
        "Model, inputs and datasheet comparisons",
        "Modell, Eingaben und Datenblattvergleiche",
    ),
    "pv_model_scope": (
        "Batzelis initialization and De Soto fitting use the saved STC points and temperature coefficients. The fitted compound parameters do not identify the physical cell-series count. Numerical fit precision is separate from physical accuracy.",
        "Die Initialisierung nach Batzelis und die Anpassung nach De Soto verwenden die gespeicherten STC-Punkte und Temperaturkoeffizienten. Aus den angepassten zusammengesetzten Parametern lässt sich die physische Anzahl der in Reihe geschalteten Zellen nicht bestimmen. Die numerische Anpassungsgenauigkeit ist von der physikalischen Genauigkeit zu unterscheiden.",
    ),
    "pv_model_identity": ("Model reference", "Modellreferenz"),
    "pv_fitted_parameters": ("Fitted model parameters", "Angepasste Modellparameter"),
    "pv_value": ("Value", "Wert"),
    "pv_cell_technology": ("Cell technology", "Zelltechnologie"),
    "pv_eg_assumption": (
        "Silicon bandgap assumption",
        "Annahme zur Bandlücke von Silizium",
    ),
    "pv_deg_assumption": (
        "Bandgap temperature assumption",
        "Annahme zur Temperaturabhängigkeit der Bandlücke",
    ),
    "pv_numerical_residual": (
        "Relative numerical residual",
        "Relatives numerisches Residuum",
    ),
    "pv_gamma_declared": (
        "Declared power temperature coefficient",
        "Angegebener Temperaturkoeffizient der Leistung",
    ),
    "pv_gamma_model": (
        "Model power temperature coefficient",
        "Temperaturkoeffizient der Leistung im Modell",
    ),
    "pv_datasheet_comparisons": ("Datasheet comparisons", "Datenblattvergleiche"),
    "pv_diagnostics_scope": (
        "The power coefficient and NOCT values were not fitting targets. These comparisons show differences; they do not certify extrapolation accuracy.",
        "Der Leistungskoeffizient und die NOCT-Werte waren keine Zielgrößen der Anpassung. Die Vergleiche zeigen Abweichungen; sie bestätigen keine Extrapolationsgenauigkeit.",
    ),
    "pv_noct_cell": (
        "Declared NOCT cell temperature",
        "Angegebene NOCT-Zelltemperatur",
    ),
    "pv_noct_declared_power": ("Declared NOCT power", "Angegebene NOCT-Leistung"),
    "pv_noct_model_power": (
        "Model power at nominal NOCT",
        "Modellleistung bei nominaler NOCT",
    ),
    "pv_noct_model_limits": (
        "Model powers at the NOCT temperature limits",
        "Modellleistungen an den NOCT-Temperaturgrenzen",
    ),
    "derived_iv_model_with_numerical_readback": (
        "The fitted parameters reproduce the supplied STC points within the stated numerical tolerance. This is a numerical check, not a manufacturer performance validation.",
        "Die angepassten Parameter reproduzieren die vorgegebenen STC-Punkte innerhalb der angegebenen numerischen Toleranz. Dies ist eine numerische Prüfung und keine Validierung der Leistungsangaben des Herstellers.",
    ),
    "manufacturer_iv_performance_validation_required": (
        "The fit does not establish model accuracy for this exact module over its operating range. Validation against manufacturer performance data remains required.",
        "Die Anpassung belegt nicht, wie genau das Modell diesen Modultyp über seinen Betriebsbereich abbildet. Eine Validierung anhand von Leistungsdaten des Herstellers ist weiterhin erforderlich.",
    ),
    "operating_cell_conditions_required": (
        "Effective irradiance, hot and cold cell temperatures and their project basis are required for the operating-point calculation.",
        "Für die Arbeitspunktberechnung sind die effektive Bestrahlungsstärke, die heißen und kalten Zelltemperaturen und deren Projektgrundlage erforderlich.",
    ),
    "operating_cell_conditions_outside_domain": (
        "The cold cell temperature must not exceed the hot value, and both must lie within the cited module temperature range.",
        "Die kalte Zelltemperatur darf den heißen Wert nicht überschreiten. Beide Werte müssen im belegten Temperaturbereich des Moduls liegen.",
    ),
    "declared_uniform_irradiance_and_cell_conditions": (
        "The calculation applies the stated effective irradiance uniformly to the modules at each declared cell temperature.",
        "Die Berechnung verwendet die angegebene effektive Bestrahlungsstärke einheitlich für die Module bei der jeweils angegebenen Zelltemperatur.",
    ),
    "modeled_mpp_at_declared_cell_condition": (
        "This compares the modeled MPP voltage at the declared case with the documented MPPT window. Other irradiance, temperature and shading conditions require their own assessment.",
        "Verglichen wird die modellierte MPP-Spannung im angegebenen Betriebsfall mit dem dokumentierten MPPT-Bereich. Andere Bestrahlungs-, Temperatur- und Verschattungsbedingungen müssen gesondert geprüft werden.",
    ),
    "modeled_parallel_current_at_declared_conditions": (
        "Parallel currents are modeled at the declared uniform case. These points do not replace design-current or protection-rating checks.",
        "Die Parallelströme werden für den angegebenen einheitlichen Betriebsfall modelliert. Diese Arbeitspunkte ersetzen keine Prüfung des Auslegungsstroms oder der Schutzbemessung.",
    ),
    "parallel_operating_mpp_requires_matching_strings": (
        "Different parallel string lengths or orientations do not establish a common operating MPP. The operating-current sum is therefore unresolved.",
        "Unterschiedliche Längen oder Ausrichtungen paralleler Strings belegen keinen gemeinsamen MPP. Die Summe der Betriebsströme bleibt deshalb ungeklärt.",
    ),
    "module_operating_curve_not_admissible": (
        "The model did not produce a finite, physically admissible operating curve for these conditions.",
        "Das Modell lieferte für diese Bedingungen keine endliche, physikalisch zulässige Betriebskennlinie.",
    ),
    "module_iv_inputs_missing": (
        "The model requires STC Voc, Isc, Vmpp and Impp values, plus the Voc and Isc temperature coefficients, from the maintained module record with source references.",
        "Das Modell benötigt Voc, Isc, Vmpp und Impp unter STC sowie die Temperaturkoeffizienten von Voc und Isc aus dem gepflegten Moduldatensatz, jeweils mit Quellenbeleg.",
    ),
    "crystalline_module_basis_missing": (
        "The cited module record does not establish the crystalline-cell basis required by this model.",
        "Der belegte Moduldatensatz bestätigt nicht die für dieses Modell erforderliche kristalline Zellgrundlage.",
    ),
    "module_iv_points_inconsistent": (
        "The supplied STC current or voltage points are inconsistent with a physical single-diode curve.",
        "Die angegebenen STC-Strom- oder Spannungspunkte sind mit einer physikalischen Eindiodenkennlinie nicht vereinbar.",
    ),
    "module_iv_fit_not_admissible": (
        "The fitting result failed its physical or numerical checks. It is not used for operating estimates.",
        "Das Anpassungsergebnis hat die physikalischen oder numerischen Prüfungen nicht bestanden. Es wird nicht für Betriebsschätzungen verwendet.",
    ),
    "physical_input_map_requires_evidence": (
        "The input number identifies the proposed connection. A cited manufacturer connector map is still required.",
        "Die Eingangsnummer bezeichnet den geplanten Anschluss. Ein belegter Anschlussplan des Herstellers ist noch erforderlich.",
    ),
    "pv_inverter_instance": ("Inverter", "Wechselrichter"),
    "pv_instance_not_recorded": ("Not recorded", "Nicht erfasst"),
    "plant_unit": ("System", "System"),
    "pv_strings_title": ("PV wiring plan", "PV-Verschaltungsplan"),
    "pv_strings_scope": (
        "The wiring plan records the assigned roof modules. Cold open-circuit voltage uses the stated ambient temperature and the module's voltage coefficient. STC operating points do not establish hot or cold MPP performance, design currents or wiring protection.",
        "Der Verschaltungsplan enthält die zugeordneten Dachmodule. Die Leerlaufspannung bei Kälte wird mit der angegebenen Umgebungstemperatur und dem Spannungskoeffizienten des Moduls berechnet. Arbeitspunkte unter STC belegen weder das MPP-Verhalten bei Hitze oder Kälte noch die Auslegungsströme oder den Leitungsschutz.",
    ),
    "pv_string": ("String", "String"),
    "pv_input": ("Input", "Eingang"),
    "pv_count": ("Modules", "Module"),
    "pv_stc_vmpp": ("Vmpp at STC", "Vmpp unter STC"),
    "pv_cold_voc": ("Cold Voc", "Voc bei Kälte"),
    "pv_min_ambient": (
        "Lowest design ambient temperature",
        "Niedrigste Auslegungs-Umgebungstemperatur",
    ),
    "pv_temperature_source": (
        "Temperature source and location",
        "Quelle der Temperaturangabe und Standort",
    ),
    "linear_cold_voc_at_declared_ambient": (
        "Voc = modules per string × module Voc at STC × [1 + βVoc × (lowest design ambient temperature − 25 °C)]. βVoc is the relative Voc temperature coefficient in 1/°C; divide a value in %/°C by 100. The design temperature and its source are required.",
        "Voc = Module je String × Voc des Moduls unter STC × [1 + βVoc × (niedrigste Auslegungs-Umgebungstemperatur − 25 °C)]. βVoc ist der relative Temperaturkoeffizient der Leerlaufspannung in 1/°C; Werte in %/°C werden durch 100 geteilt. Die Auslegungstemperatur und ihre Quelle müssen angegeben werden.",
    ),
    "stc_operating_point_only": (
        "This comparison uses STC values: 1,000 W/m² irradiance, 25 °C cell temperature and the AM1.5 reference spectrum.",
        "Dieser Vergleich verwendet STC-Werte: 1.000 W/m² Bestrahlungsstärke, 25 °C Zelltemperatur und das AM1,5-Referenzspektrum.",
    ),
    "parallel_current_at_stc_only": (
        "Parallel-string currents are added at STC. Design irradiance, temperature and applicable rating factors require separate checks.",
        "Die Ströme paralleler Strings werden unter STC addiert. Die für die Auslegung maßgebliche Bestrahlungsstärke, Temperatur und die geltenden Bemessungsfaktoren sind gesondert zu prüfen.",
    ),
    "hot_and_cold_mpp_model_required": (
        "Hot and cold operating MPP checks require a suitable module I–V model and documented cell temperatures.",
        "Für die MPP-Prüfung bei heißem und kaltem Betrieb sind ein geeignetes I–V-Modell des Moduls und belegte Zelltemperaturen erforderlich.",
    ),
    "design_irradiance_and_rating_rules_required": (
        "Design currents require documented irradiance, temperature and applicable rating rules.",
        "Die Auslegungsströme erfordern belegte Bestrahlungs- und Temperaturbedingungen sowie die geltenden Bemessungsregeln.",
    ),
    "cables_connectors_fuses_and_isolation_require_design": (
        "Cable routes, conductor ratings, connector compatibility, fuses and isolation still require project-specific design.",
        "Leitungswege, Leiterbemessung, Steckverbinder-Kompatibilität, Sicherungen und Trenneinrichtungen müssen noch projektspezifisch ausgelegt werden.",
    ),
    "pv_components_title": (
        "PV modules used in the calculation",
        "PV-Module der Berechnung",
    ),
    "pv_components_scope": (
        "Module counts come from the saved layout of the selected generation result. The listed modules are design references; electrical and mounting suitability require project-specific assessment.",
        "Die Stückzahlen stammen aus der gespeicherten Belegung des ausgewählten Ergebnisses zur PV-Erzeugung. Die aufgeführten Module dienen als Auslegungsreferenz; ihre elektrische Eignung und ihre Eignung für die Montage müssen projektspezifisch geprüft werden.",
    ),
    "pv_components_dc_scope": (
        "This list includes only the PV conversion group used by the selected DC calculation.",
        "Diese Liste enthält nur die PV-Gruppe, die für die ausgewählte DC-Berechnung verwendet wurde.",
    ),
    "pv_components_no_saved_layout": (
        "The selected generation data has no saved layout from which to determine a module count.",
        "Zu den ausgewählten Erzeugungsdaten ist keine Belegung gespeichert, aus der sich eine Modulanzahl ermitteln lässt.",
    ),
    "pv_components_no_woo_module_proof": (
        "The saved module specifications could not be linked to the product record and its source document.",
        "Die gespeicherten Modulangaben konnten dem Produktdatensatz und dem zugehörigen Quelldokument nicht eindeutig zugeordnet werden.",
    ),
    "pv_components_declared_reference_module": (
        "The roof uses a planning reference module: an unverified planning assumption for size and power, not a manufacturer datasheet value. The customer supplies the modules actually installed, so no product record or component list is claimed here.",
        "Für das Dach ist ein Planungs-Referenzmodul angesetzt: eine unbestätigte Planungsannahme zu Größe und Leistung, kein Wert aus einem Herstellerdatenblatt. Die tatsächlich installierten Module stellt der Kunde bereit; ein Produktdatensatz oder eine Stückliste wird hier daher nicht zugesagt.",
    ),
    "pv_components_module_power": ("Module power (STC)", "Modulleistung (STC)"),
    "pv_components_capacity": ("PV nameplate power", "PV-Nennleistung"),
    "comparison_title": (
        "Saved calculation comparison",
        "Vergleich gespeicherter Berechnungen",
    ),
    "comparison_scope": (
        "Matching comparison conditions do not establish manufacturer performance or installation approval.",
        "Übereinstimmende Vergleichsbedingungen belegen weder die Leistungsfähigkeit der Geräte noch eine Freigabe für die Installation.",
    ),
    "comparison_definition": (
        "Difference = comparison minus baseline. Differences in ratios are shown in percentage points. PV differences also require the same AC/DC boundary.",
        "Differenz = Vergleichsberechnung minus Referenzberechnung. Unterschiede bei Anteilen werden in Prozentpunkten angegeben. Bei PV-Werten wird eine Differenz nur angezeigt, wenn beide Werte sich auf dieselbe AC- oder DC-Seite beziehen.",
    ),
    "comparison_blocked": (
        "No differences are shown because the comparison conditions differ or are incomplete.",
        "Es werden keine Differenzen angezeigt, da die Vergleichsbedingungen abweichen oder unvollständig sind.",
    ),
    "comparison_baseline": ("Baseline calculation", "Referenzberechnung"),
    "comparison_candidate": ("Comparison calculation", "Vergleichsberechnung"),
    "comparison_difference": ("Difference", "Differenz"),
    "comparison_basis": ("Comparison basis", "Vergleichsgrundlage"),
    "comparison_changes": (
        "Design and assumption changes",
        "Änderungen an Auslegung und Annahmen",
    ),
    "comparison_changed": ("Changed", "Geändert"),
    "comparison_unchanged": ("Unchanged", "Unverändert"),
    "comparison_site": ("Site and time zone", "Standort und Zeitzone"),
    "comparison_periods": ("Calculated periods", "Berechnungszeiträume"),
    "comparison_demand_sources": (
        "Load and auxiliary sources",
        "Quellen für Last und Hilfsverbrauch",
    ),
    "comparison_pv_weather": (
        "PV weather or identical generation input",
        "PV-Wetterdaten oder identische Erzeugungsdaten",
    ),
    "comparison_time_resolution": ("Time resolution", "Zeitliche Auflösung"),
    "comparison_operating_requirements": (
        "Operating requirements",
        "Betriebsanforderungen",
    ),
    "comparison_starting_inventory": (
        "Starting stored energy",
        "Gespeicherte Energie zu Beginn",
    ),
    "comparison_terminal_requirement": (
        "Required final stored energy",
        "Geforderte Mindestenergie am Ende",
    ),
    "comparison_load_scope": ("Load measurement scope", "Bilanzgrenze der Last"),
    "comparison_calculation_method": ("Calculation method", "Berechnungsmethode"),
    "comparison_scenario_constraints": (
        "Scenario requirements",
        "Szenarioanforderungen",
    ),
    "comparison_battery_temperature": ("Battery temperature", "Batterietemperatur"),
    "comparison_storage_parameters": ("Storage parameters", "Speicherparameter"),
    "comparison_equipment_selection": ("Equipment selection", "Geräteauswahl"),
    "comparison_pv_design": (
        "PV layout and generation settings",
        "PV-Belegung und Erzeugungsparameter",
    ),
    "comparison_dc_auxiliary": ("DC auxiliary demand", "DC-Hilfsverbrauch"),
    "comparison_load_demand": ("Simulated load demand", "Simulierter Strombedarf"),
    "comparison_solar_supply": (
        "Solar supplied to load",
        "Solarenergie zur Lastversorgung",
    ),
    "comparison_grid_import": ("Grid import", "Netzbezug"),
    "comparison_unserved_load": (
        "Unserved simulated load",
        "Ungedeckter simulierter Strombedarf",
    ),
    "comparison_pv_export": ("PV export", "PV-Einspeisung"),
    "comparison_stored_final": ("Stored energy at end", "Gespeicherte Energie am Ende"),
    "comparison_pv_generation": ("PV generation", "PV-Erzeugung"),
    "comparison_solar_share": (
        "Solar share of gross demand",
        "Solarer Deckungsanteil am Gesamtbedarf",
    ),
    "comparison_pv_use": (
        "PV used or stored on site",
        "PV-Energie für Verbrauch und Speicherung vor Ort",
    ),
    "comparison_matched": ("Match", "Übereinstimmend"),
    "comparison_different": ("Differ", "Abweichend"),
    "comparison_unavailable": ("Not established", "Nicht belegt"),
    "comparison_no_minimum": ("No minimum required", "Kein Mindestwert erforderlich"),
    "dc_battery_temperature": (
        "Battery temperature for this scenario",
        "Batterietemperatur im Szenario",
    ),
    "dc_temperature_scope": (
        "Battery temperature is a fixed scenario condition used to check the documented charging and discharging temperature ranges. It is not inferred from outdoor weather. This model uses fixed loss assumptions and does not simulate temperature changes.",
        "Die angegebene Batterietemperatur gilt für das gesamte Szenario als konstant und wird mit den dokumentierten Temperaturbereichen für Laden und Entladen abgeglichen. Sie wird nicht aus Wetterdaten abgeleitet. Das Modell verwendet feste Verlustannahmen und bildet keine Temperaturänderungen ab.",
    ),
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
    "grid_declarations": (
        "Grid connection details entered for this project",
        "Angaben zum Netzanschluss dieses Projekts",
    ),
    "grid_declaration_basis": (
        "These details were entered for this project. Confirm them with the responsible grid operator.",
        "Diese Angaben stammen aus dem Projekt. Bitte bestätigen Sie sie mit dem zuständigen Netzbetreiber.",
    ),
    "grid_dso": ("Grid operator", "Netzbetreiber"),
    "grid_dso_source": ("Grid operator source", "Quelle zum Netzbetreiber"),
    "grid_voltage": (
        "Voltage at the grid connection point",
        "Spannungsebene am Netzanschlusspunkt",
    ),
    "grid_low": ("Low voltage", "Niederspannung"),
    "grid_medium": ("Medium voltage", "Mittelspannung"),
    "grid_high": ("High voltage", "Hochspannung"),
    "grid_tab_title": ("Connection conditions", "Anschlussbedingungen"),
    "grid_tab_source": (
        "Source of the connection conditions",
        "Quelle der Anschlussbedingungen",
    ),
    "grid_edition": ("Document edition", "Dokumentausgabe"),
    "grid_tab_date": ("Document date", "Dokumentdatum"),
    "grid_evidence": ("Grid connection review", "Prüfung des Netzanschlusses"),
    "grid_de_scope": (
        "Check the local connection conditions for the voltage level at the grid connection point. Electrical evidence for a generating unit is a separate part of this review.",
        "Prüfen Sie die örtlichen Anschlussbedingungen für die Spannungsebene am Netzanschlusspunkt. Die elektrischen Nachweise der Erzeugungseinheit sind gesondert zu prüfen.",
    ),
    "grid_no_rule": (
        "This revision has no verified local rule for this site.",
        "Für diesen Standort liegt in dieser Projektversion kein geprüftes örtliches Regelwerk vor.",
    ),
    "grid_to_supply": ("Project details still needed", "Noch benötigte Projektangaben"),
    "grid_missing_country_code": ("site country", "Land des Standorts"),
    "grid_missing_dso_name": ("grid operator", "Netzbetreiber"),
    "grid_missing_dso_source_url": (
        "source for the grid operator",
        "Quelle zum zuständigen Netzbetreiber",
    ),
    "grid_missing_voltage_level": (
        "connection voltage level",
        "Spannungsebene am Netzanschlusspunkt",
    ),
    "grid_missing_tab.source_url": (
        "source of the connection conditions",
        "Quelle der Anschlussbedingungen",
    ),
    "grid_missing_tab.edition_or_date": (
        "document edition or date",
        "Ausgabe oder Datum des Dokuments",
    ),
    "grid_all_entered": (
        "All requested details entered",
        "Alle angeforderten Angaben vorhanden",
    ),
    "grid_territory_tab": (
        "Operator territory and applicable conditions",
        "Netzgebiet und geltende Anschlussbedingungen",
    ),
    "grid_unverified": (
        "Independent verification pending",
        "Unabhängige Prüfung ausstehend",
    ),
    "grid_permission": ("Permission to connect", "Zustimmung zum Netzanschluss"),
    "grid_no_permission": (
        "No approval evidenced in this assessment",
        "In dieser Prüfung ist keine Zustimmung nachgewiesen",
    ),
    "grid_source_read": ("Source reviewed", "Quelle geprüft am"),
    "country_rule_title": (
        "Dated national rule reading",
        "Landesregel zum gewählten Datum",
    ),
    "country_rule_scope": (
        "This is a conditional reference for the selected rule date and declared project scope and values. Verify whether the cited rules apply today and on the project's grid connection date. The grid operator, connection voltage, local requirements, equipment compliance and grid permission need separate verification.",
        "Diese bedingte Orientierung bezieht sich auf das gewählte Regelungsdatum und die angegebenen Projektbedingungen und Werte. Prüfen Sie, ob die zitierten Regeln aktuell und zum Netzanschlussdatum des Projekts gelten. Netzbetreiber, Anschlussspannung, örtliche Anforderungen, Gerätekonformität und Anschlussgenehmigung müssen gesondert geprüft werden.",
    ),
    "country_rule_date": ("Rule date", "Regelungsdatum"),
    "country_rule_basis": ("Power basis", "Leistungsbezug"),
    "country_rule_fr_generation_pmax": (
        "French generation-unit Pmax",
        "Pmax der französischen Erzeugungseinheit",
    ),
    "country_rule_nl_storage_max_active": (
        "Dutch storage-unit maximum deliverable active power",
        "Maximal abgebbare Wirkleistung der niederländischen Speichereinheit",
    ),
    "country_rule_de_pv_installed": (
        "Installed solar power under EEG § 9",
        "Installierte PV-Leistung nach EEG § 9",
    ),
    "country_rule_at_tor_typ_a_max_capacity": (
        "Austrian maximum capacity Pmax under TOR Erzeuger Typ A",
        "Maximalkapazität Pmax nach TOR Erzeuger Typ A (Österreich)",
    ),
    "country_rule_power": ("Declared power", "Angegebene Leistung"),
    "country_rule_voltage": (
        "Connection-point voltage",
        "Spannung am Netzanschlusspunkt",
    ),
    "country_rule_before_test": (
        "Meter or control equipment missing, or first successful control test pending",
        "Messsystem oder Steuerungseinrichtung fehlt oder erste erfolgreiche Ansteuerungsprüfung steht aus",
    ),
    "country_rule_remuneration": ("EEG remuneration", "EEG-Vergütungsform"),
    "country_rule_feed_in_or_tenant": (
        "Feed-in tariff or tenant-electricity supplement",
        "Einspeisevergütung oder Mieterstromzuschlag",
    ),
    "country_rule_other": ("Other or none", "Andere oder keine"),
    "country_rule_plug_in": (
        "Complete plug-in solar exception",
        "Vollständige Steckersolar-Ausnahme",
    ),
    "country_rule_full_self_consumption": (
        "Full self-consumption without public-grid injection",
        "Vollständiger Eigenverbrauch ohne Einspeisung ins öffentliche Netz",
    ),
    "country_rule_yes": ("Yes", "Ja"),
    "country_rule_no": ("No", "Nein"),
    "country_rule_unknown": ("Not stated", "Nicht angegeben"),
    "country_rule_conditional": ("Conditional", "Bedingt"),
    "country_rule_unresolved": ("Unresolved", "Offen"),
    "country_rule_result": ("Result", "Ergebnis"),
    "country_rule_missing": ("Information still missing", "Noch fehlende Angaben"),
    "country_rule_source": ("Source", "Quelle"),
    "country_rule_snapshot": ("Evidence snapshot date", "Stand der Quellenprüfung"),
    "country_rule_hash": ("Source text SHA-256", "SHA-256 des Quellentextes"),
    "country_rule_fr_generation_type": (
        "French generation-unit category",
        "Kategorie der französischen Erzeugungseinheit",
    ),
    "country_rule_nl_storage_type": (
        "Dutch storage-unit corresponding requirements",
        "Entsprechende Anforderungen für die niederländische Speichereinheit",
    ),
    "country_rule_nl_storage_lfsm": (
        "Dutch storage-unit LFSM-U droop",
        "LFSM-U / Statik bei Unterfrequenz der niederländischen Speichereinheit",
    ),
    "country_rule_de_eeg_control": (
        "EEG pre-test remote control",
        "EEG-Fernsteuerung vor erfolgreicher Prüfung",
    ),
    "country_rule_de_eeg_export": (
        "EEG pre-test export limitation",
        "EEG-Einspeisebegrenzung vor erfolgreicher Prüfung",
    ),
    "country_rule_fr_enedis_declaration": (
        "Enedis declaration and agreement",
        "Enedis-Anmeldung und Vereinbarung",
    ),
    "country_rule_fr_enedis_certification": (
        "Enedis supporting documentation",
        "Enedis-Unterlagen",
    ),
    "country_rule_at_tor_scope": (
        "Scope of TOR Erzeuger Typ A",
        "Anwendungsbereich der TOR Erzeuger Typ A",
    ),
    "country_rule_at_kleinsterzeugungsanlage": (
        "Kleinsterzeugungsanlage status",
        "Einstufung als Kleinsterzeugungsanlage",
    ),
    "country_rule_at_network_disconnection_protection": (
        "Network disconnection protection",
        "Netzentkupplungsschutz",
    ),
    "country_rule_at_substantial_change": (
        "Substantial change of an existing installation",
        "Wesentliche Änderung einer bestehenden Anlage",
    ),
    "country_rule_in_scope_below_250_kw_and_110_kv": (
        "Inside this TOR part: maximum capacity below 250 kW and connection voltage below 110 kV",
        "Im Anwendungsbereich dieses TOR-Teils: Maximalkapazität unter 250 kW und Anschlussspannung unter 110 kV",
    ),
    "country_rule_outside_scope": (
        "Outside the scope of this TOR part; the cited provisions give no reading for this project",
        "Außerhalb des Anwendungsbereichs dieses TOR-Teils; die zitierten Bestimmungen ergeben für dieses Projekt keine Aussage",
    ),
    "country_rule_kleinsterzeugungsanlage_two_weeks_notice": (
        "Kleinsterzeugungsanlage at up to 0.8 kW maximum capacity: written notice to the network operator at least two weeks before commissioning, and the residual requirements listed in § 2.1",
        "Kleinsterzeugungsanlage bis 0,8 kW Maximalkapazität: schriftliche Verständigung des Netzbetreibers spätestens zwei Wochen vor Inbetriebnahme und die in § 2.1 genannten Restanforderungen",
    ),
    "country_rule_not_kleinsterzeugungsanlage": (
        "Not a Kleinsterzeugungsanlage: the exemption of § 2.1 does not apply",
        "Keine Kleinsterzeugungsanlage: die Ausnahme nach § 2.1 gilt nicht",
    ),
    "country_rule_external_network_disconnection_protection": (
        "External network disconnection protection required above 30 kVA",
        "Externer Netzentkupplungsschutz über 30 kVA erforderlich",
    ),
    "country_rule_automatic_disconnection_device_r25": (
        "Automatic disconnection device under OVE-Richtlinie R 25 permitted up to 30 kVA",
        "Selbsttätig wirkende Freischaltstelle nach OVE-Richtlinie R 25 bis 30 kVA zulässig",
    ),
    "country_rule_new_installation": (
        "New installation; the substantial-change provisions do not apply",
        "Neuanlage; die Bestimmungen zur wesentlichen Änderung greifen nicht",
    ),
    "country_rule_substantial_change_power_increase_above_15_percent": (
        "Maximum capacity increases by more than 15%: the cited example of a substantial change is met",
        "Die Maximalkapazität steigt um mehr als 15 %: das zitierte Beispiel einer wesentlichen Änderung ist erfüllt",
    ),
    "country_rule_power_criterion_not_exceeded_other_criteria_open": (
        "The 15% example is not met; other substantial-change criteria stay open",
        "Das 15-%-Beispiel ist nicht erfüllt; weitere Kriterien einer wesentlichen Änderung bleiben offen",
    ),
    "country_rule_at_connection_route": (
        "Connection route",
        "Anschlussweg",
    ),
    "country_rule_at_conformity_evidence": (
        "Conformity evidence path",
        "Weg des Konformitätsnachweises",
    ),
    "country_rule_notification_route_up_to_20_kw_net_active_power": (
        "Up to 20 kW net active power: notification to the distribution system operator, connection on confirmation or after four weeks without a decision",
        "Bis 20 kW netzwirksame Leistung: Anzeige an den Verteilernetzbetreiber, Anschluss mit Bestätigung oder nach vier Wochen ohne Entscheidung",
    ),
    "country_rule_network_access_contract_required_above_20_kw": (
        "Above 20 kW net active power: a network access contract with the operator is required",
        "Über 20 kW netzwirksame Leistung: ein Netzzugangsvertrag mit dem Netzbetreiber ist erforderlich",
    ),
    "country_rule_declared_austrian_inverter_list": (
        "Declared: entry in the Austrian inverter list. The listing, device and software version still need verification.",
        "Angegeben: Eintrag in der österreichischen Wechselrichterliste. Listeneintrag, Gerät und Softwarestand sind noch zu prüfen.",
    ),
    "country_rule_declared_accredited_r25_report": (
        "Declared: accredited test report under OVE-Richtlinie R 25 including the Austrian settings. The report scope and device version still need verification.",
        "Angegeben: Prüfbericht einer akkreditierten Stelle nach OVE-Richtlinie R 25 einschließlich der österreichischen Einstellungen. Prüfumfang und Gerätestand sind noch zu prüfen.",
    ),
    "country_rule_declared_vde_4105_with_r25_properties": (
        "Declared: VDE-AR-N 4105 report with the additional R 25 properties and Austrian parameters. The report scope and device version still need verification.",
        "Angegeben: Prüfbericht nach VDE-AR-N 4105 mit den zusätzlichen R-25-Eigenschaften und österreichischen Parametern. Prüfumfang und Gerätestand sind noch zu prüfen.",
    ),
    "country_rule_type_a": ("Type A", "Typ A"),
    "country_rule_type_b": ("Type B", "Typ B"),
    "country_rule_type_c": ("Type C", "Typ C"),
    "country_rule_type_d": ("Type D", "Typ D"),
    "country_rule_below_range": (
        "Below the range covered by this rule reading",
        "Unterhalb des Bereichs dieser Regelbetrachtung",
    ),
    "country_rule_missing_inputs": (
        "More project information is needed",
        "Weitere Projektangaben sind erforderlich",
    ),
    "country_rule_outside_version": (
        "The chosen date is outside the documented version",
        "Das gewählte Datum liegt außerhalb der dokumentierten Fassung",
    ),
    "country_rule_statism_2_percent": (
        "2% in storage and generation modes",
        "2 % im Speicher- und Erzeugungsbetrieb",
    ),
    "country_rule_statism_1_percent": (
        "1% in storage and generation modes",
        "1 % im Speicher- und Erzeugungsbetrieb",
    ),
    "country_rule_boundary_not_established": (
        "The 0.8 kW boundary is not established by this clause",
        "Die Grenze von 0,8 kW ist durch diese Vorschrift nicht geklärt",
    ),
    "country_rule_fetch_and_reduce": (
        "Actual export retrieval and remote reduction",
        "Abruf der Ist-Einspeisung und ferngesteuerte Reduzierung",
    ),
    "country_rule_reduce": ("Remote reduction", "Ferngesteuerte Reduzierung"),
    "country_rule_no_requirement_in_9_2_1_2": (
        "No requirement under § 9(2) sentence 1 nos. 1–2 for this power",
        "Für diese Leistung ergibt sich keine Anforderung aus § 9 Absatz 2 Satz 1 Nummer 1 bis 2",
    ),
    "country_rule_not_this_phase": (
        "The declared project is beyond the pre-test phase; other requirements remain open",
        "Das angegebene Projekt befindet sich nach der Phase vor der Prüfung; weitere Anforderungen bleiben offen",
    ),
    "country_rule_sixty_percent_conditionally": (
        "60% of installed power at the grid connection point, under the stated conditions",
        "60 % der installierten Leistung am Netzverknüpfungspunkt unter den angegebenen Bedingungen",
    ),
    "country_rule_not_in_tariff": (
        "The declared remuneration is outside this 60% provision",
        "Die angegebene Vergütungsform fällt nicht unter diese 60-%-Vorschrift",
    ),
    "country_rule_no_60_percent_in_9_2_2b_3": (
        "No 60% limit from § 9(2) sentence 1 nos. 2(b)–3 for this power",
        "Für diese Leistung ergibt sich keine 60-%-Grenze aus § 9 Absatz 2 Satz 1 Nummer 2 Buchstabe b bis Nummer 3",
    ),
    "country_rule_exempt_plug_in": (
        "The declared plug-in solar exception applies to this provision",
        "Die angegebene Steckersolar-Ausnahme gilt für diese Vorschrift",
    ),
    "country_rule_enedis_declare_cacsi": (
        "Declare the installation through Enedis-Connect and accept the CACSI no-injection agreement",
        "Melden Sie die Anlage über Enedis-Connect an und akzeptieren Sie die CACSI-Vereinbarung ohne Netzeinspeisung",
    ),
    "country_rule_enedis_consuel_or_attestation": (
        "Provide a Consuel certificate or declaration on honour. The source requires Consuel when modifying existing electrical circuits or adding a battery, with a possible plug-and-play exception subject to its stated conditions.",
        "Legen Sie eine Consuel-Bescheinigung oder eine Erklärung auf Ehrenwort vor. Laut Quelle ist bei Änderungen bestehender Stromkreise oder beim Hinzufügen einer Batterie eine Consuel-Bescheinigung erforderlich; für Plug-and-play-Geräte kann unter den dort genannten Bedingungen eine Ausnahme gelten.",
    ),
    "country_rule_input_rule_date": ("rule date", "Regelungsdatum"),
    "country_rule_input_power_kw": ("declared power", "angegebene Leistung"),
    "country_rule_input_connection_voltage_kv": (
        "connection-point voltage",
        "Spannung am Netzanschlusspunkt",
    ),
    "country_rule_input_de_before_control_test": (
        "meter and control-test stage",
        "Stand von Messsystem und Ansteuerungsprüfung",
    ),
    "country_rule_input_de_remuneration": ("EEG remuneration", "EEG-Vergütungsform"),
    "country_rule_input_de_plug_in_exception": (
        "complete plug-in solar exception",
        "vollständige Steckersolar-Ausnahme",
    ),
    "country_rule_input_apparent_power_kva": (
        "apparent power at the connection point",
        "Scheinleistung am Netzanschlusspunkt",
    ),
    "country_rule_input_at_existing_installation_change": (
        "existing installation being changed",
        "Änderung einer bestehenden Anlage",
    ),
    "country_rule_input_at_change_previous_power_kw": (
        "maximum capacity before the change",
        "Maximalkapazität vor der Änderung",
    ),
    "country_rule_input_net_active_power_kw": (
        "agreed net active power",
        "vereinbarte netzwirksame Leistung",
    ),
    "country_rule_input_at_conformity_basis": (
        "declared conformity path",
        "angegebener Konformitätsnachweis",
    ),
    "country_rule_se_rfg_maximum_capacity": (
        "Swedish maximum capacity under RfG Article 5",
        "Schwedische Maximalkapazität nach RfG Artikel 5",
    ),
    "country_rule_se_eifs_2018_2": (
        "EIFS 2018:2",
        "EIFS 2018:2",
    ),
    "country_rule_se_rfg_2016_631": (
        "Commission Regulation (EU) 2016/631 (RfG)",
        "Verordnung (EU) 2016/631 (RfG)",
    ),
    "country_rule_se_ellagen_1997_857": (
        "Ellagen (1997:857)",
        "Ellagen (1997:857)",
    ),
    "country_rule_se_module_type": (
        "RfG module type under the Swedish thresholds",
        "RfG-Modultyp nach den schwedischen Schwellenwerten",
    ),
    "country_rule_se_frequency_range": (
        "Frequency range and operating times",
        "Frequenzbereich und Betriebszeiten",
    ),
    "country_rule_se_lfsm_o": (
        "Overfrequency active-power response",
        "Wirkleistungsreaktion bei Überfrequenz",
    ),
    "country_rule_se_voltage_range": (
        "Active-power output over the voltage range",
        "Wirkleistungsabgabe im Spannungsbereich",
    ),
    "country_rule_se_automatic_reconnection": (
        "Conditions for automatic connection",
        "Bedingungen für die automatische Zuschaltung",
    ),
    "country_rule_se_existing_change": (
        "Change to an existing module",
        "Änderung eines bestehenden Moduls",
    ),
    "country_rule_se_connection_duty": (
        "Connection duty and the 43.5 kW notice rule",
        "Anschlusspflicht und die 43,5-kW-Mitteilungsregel",
    ),
    "country_rule_significant_under_article_5_2": (
        "The declared capacity and voltage put the module in one of the RfG Article 5(2) categories",
        "Leistung und Spannung ordnen das Modul einer Kategorie nach RfG Artikel 5 Absatz 2 zu",
    ),
    "country_rule_four_band_range_47_5_to_51_5_hz": (
        "Four bands: 47.5–48.5 Hz for 30 minutes, 48.5–49.0 Hz for 30 minutes, 49.0–51.0 Hz unlimited, 51.0–51.5 Hz for 30 minutes",
        "Vier Bänder: 47,5–48,5 Hz für 30 Minuten, 48,5–49,0 Hz für 30 Minuten, 49,0–51,0 Hz unbegrenzt, 51,0–51,5 Hz für 30 Minuten",
    ),
    "country_rule_lfsm_o_50_5_hz_droop_8_percent": (
        "Reduce active power from a threshold of 50.5 Hz with a primary droop setting of 8%. Disconnection is not an alternative to that reduction.",
        "Reduzierung der Wirkleistung ab einer Schwelle von 50,5 Hz mit einer primären Statik von 8 %. Die Abschaltung ist keine Alternative zu dieser Reduzierung.",
    ),
    "country_rule_voltage_range_90_to_105_percent": (
        "Maintain active-power output between 90% and 105% of the connection-point voltage",
        "Wirkleistungsabgabe zwischen 90 % und 105 % der Spannung am Netzanschlusspunkt beibehalten",
    ),
    "country_rule_automatic_reconnection_47_5_to_50_1_hz_after_3_minutes": (
        "Automatic connection is permitted only after the frequency stayed within 47.5–50.1 Hz for three consecutive minutes; the power increase stays unconstrained below 49.9 Hz, at most 10% of nominal active power per minute between 49.9 and 50.1 Hz, and is not permitted above 50.1 Hz",
        "Eine automatische Zuschaltung ist erst zulässig, nachdem die Frequenz drei zusammenhängende Minuten innerhalb von 47,5–50,1 Hz lag; unterhalb von 49,9 Hz ist der Leistungsanstieg unbegrenzt, zwischen 49,9 und 50,1 Hz höchstens 10 % der Nennwirkleistung je Minute und oberhalb von 50,1 Hz nicht zulässig",
    ),
    "country_rule_modification_notification_type_c_or_d": (
        "A modified type C or type D module: notify the system operator in advance, and the authority decides whether the connection agreement is revised",
        "Geändertes Modul des Typs C oder D: vorherige Mitteilung an den Netzbetreiber; die Behörde entscheidet über die Anpassung des Netzanschlussvertrags",
    ),
    "country_rule_modification_outside_4_1_a_other_rules_open": (
        "Article 4(1)(a) names type C and type D only; for this type the cited article gives no reading and other rules stay open",
        "Artikel 4 Absatz 1 Buchstabe a nennt nur Typ C und Typ D; für diesen Typ ergibt der zitierte Artikel keine Aussage, weitere Regeln bleiben offen",
    ),
    "country_rule_not_applicable_type_a": (
        "The cited clause names types B, C and D only, so it states nothing for type A",
        "Die zitierte Vorschrift nennt nur Typ B, C und D und sagt daher nichts über Typ A aus",
    ),
    "country_rule_not_applicable_type_d": (
        "The cited clause names types A, B and C only, so it states nothing for type D",
        "Die zitierte Vorschrift nennt nur Typ A, B und C und sagt daher nichts über Typ D aus",
    ),
    "country_rule_deviation_notice_within_one_month_up_to_43_5_kw": (
        "Up to 43.5 kW of possible feed-in power: a distribution system operator may deviate from the connection duty only after notifying the applicant, and that notice must arrive within one month of the request. The connection duty itself continues to apply.",
        "Bis 43,5 kW möglicher Einspeiseleistung: Ein Verteilnetzbetreiber darf von der Anschlusspflicht nur nach Mitteilung an den Antragsteller abweichen, und diese Mitteilung muss innerhalb eines Monats nach dem Antrag erfolgen. Die Anschlusspflicht selbst bleibt bestehen.",
    ),
    "country_rule_deviation_on_general_grounds_above_43_5_kw": (
        "Above 43.5 kW of possible feed-in power: the one-month notice rule does not apply, while the general grounds for a deviation and the connection duty itself are unchanged",
        "Über 43,5 kW möglicher Einspeiseleistung: Die Mitteilungsfrist von einem Monat gilt nicht; die allgemeinen Gründe für eine Abweichung und die Anschlusspflicht selbst bleiben unverändert",
    ),
    "country_rule_input_se_export_power_kw": (
        "possible feed-in power",
        "mögliche Einspeiseleistung",
    ),
    "country_rule_input_se_existing_installation_change": (
        "existing module being changed",
        "Änderung eines bestehenden Moduls",
    ),
    "country_open": (
        "Country requirements are not assessed by the selected calculations.",
        "Landesspezifische Anforderungen werden in den ausgewählten Berechnungen nicht bewertet.",
    ),
    "bom": ("Provisional bill of materials", "Vorläufige Stückliste"),
    "terminal_material_scope": (
        "These entries record the terminals checked on each circuit. They have no purchase quantity.",
        "Diese Einträge zeigen die geprüften Klemmen je Stromkreis. Dafür ist keine Bestellmenge angegeben.",
    ),
    "bom_scope": (
        "This table lists selected equipment, saved roof modules, manufacturer-included components, customer-supplied requirements and site-engineering obligations. Quantities are shown only where established. It is not a complete balance-of-system take-off; mounting, cabling, protection and other installation materials still require project-specific design.",
        "Diese Tabelle führt ausgewählte Geräte, Module der gespeicherten Dachbelegung, herstellerseitig mitgelieferte Komponenten, kundenseitig bereitzustellende Anforderungen und projektseitig zu prüfende Pflichten auf. Mengen werden nur angezeigt, wenn sie feststehen. Die Tabelle ist keine vollständige Materialaufnahme des restlichen Systems; Montagesystem, Leitungen, Schutzmaßnahmen und weitere Installationsmaterialien müssen weiterhin projektspezifisch ausgelegt werden.",
    ),
    "material_handling": ("Supply scope", "Lieferumfang"),
    "material_source": ("Quantity basis and sources", "Mengengrundlage und Quellen"),
    "material_assessment": ("Planning status", "Planungsstand"),
    "material_unit": ("Unit", "Einheit"),
    "material_unit_piece": ("pc", "St."),
    "material_unit_pair": ("pair", "Paar"),
    "material_unit_m": ("m", "m"),
    "material_included_documented": (
        "Included with the equipment",
        "Mit dem Gerät mitgeliefert",
    ),
    "material_package_source": (
        "Manufacturer package contents",
        "Herstellerseitiger Lieferumfang",
    ),
    "material_installation_source": (
        "Installation requirement source",
        "Quelle der Installationsanforderung",
    ),
    "material_installation_requirement": (
        "Installation requirement · specification pending",
        "Installationsbedarf · Spezifikation offen",
    ),
    "material_installation_declared": (
        "Installation requirement · cross-section as declared",
        "Installationsbedarf · Querschnitt gemäß Projektangabe",
    ),
    "installation": ("Installation routing", "Leitungswege der Installation"),
    "installation_scope": (
        "Each listed cable or conductor is one physical run. Lengths use the saved three-dimensional path and explicitly declared extra length. A declared cross-section is the project's own statement about that run; it is not a sizing result. Cable sizing, connector matching, protection, earthing, mounting and country requirements have not been assessed by this route calculation.",
        "Jede Zeile steht für eine einzelne Leitung oder einen separat geführten Leiter. Die Länge ergibt sich aus dem gespeicherten dreidimensionalen Leitungsweg zuzüglich der ausdrücklich angegebenen Zusatzlänge. Ein angegebener Querschnitt ist eine Projektangabe zu dieser Leitung und kein Ergebnis einer Auslegung. Die Auslegung der Leitungen, die Kompatibilität der Steckverbinder, Schutzmaßnahmen, Erdung, Montage und länderspezifische Anforderungen werden durch diese Längenberechnung nicht geprüft.",
    ),
    "installation_instances": (
        "Physical devices and site connections",
        "Geräte und Anschlüsse am Standort",
    ),
    "installation_instance_scope": (
        "Connection point names and positions are project inputs. They do not establish manufacturer terminal ratings or approve the circuit design.",
        "Namen und Positionen der Anschlusspunkte sind Projektangaben. Die Bemessungswerte der Herstelleranschlüsse und die Auslegung des Stromkreises werden damit nicht geprüft.",
    ),
    "installation_instance": (
        "Device or site connection",
        "Gerät oder Anschluss am Standort",
    ),
    "installation_ports": ("Connection points", "Anschlusspunkte"),
    "installation_site_point": ("Site connection", "Anschluss am Standort"),
    "installation_product_unavailable": (
        "Selected product is unavailable",
        "Ausgewähltes Produkt nicht verfügbar",
    ),
    "installation_product_revision_changed": (
        "Selected product revision has changed",
        "Stand des ausgewählten Produkts hat sich geändert",
    ),
    "installation_product_details_unavailable": (
        "Saved product details are unavailable",
        "Angaben zum gespeicherten Produkt nicht verfügbar",
    ),
    "installation_circuit": ("Circuit / route", "Stromkreis / Leitungsweg"),
    "installation_pending": ("Quantity not confirmed", "Menge nicht bestätigt"),
    "installation_conductor": ("Conductor", "Leiter"),
    "installation_conductor_open": (
        "Cross-section not declared",
        "Querschnitt nicht angegeben",
    ),
    "installation_conductor_declared": (
        "One cross-section declared",
        "Ein Querschnitt angegeben",
    ),
    "installation_conductor_unconfirmed": (
        "Cross-section missing for a recorded run",
        "Querschnitt für eine erfasste Leitung fehlt",
    ),
    "installation_conductor_conflicting": (
        "Recorded runs declare different cross-sections",
        "Erfasste Leitungen haben unterschiedliche Querschnitte",
    ),
    "installation_conductor_not_recorded": (
        "No run recorded",
        "Keine Leitung erfasst",
    ),
    "installation_closure": (
        "Conductor and quantities",
        "Leiter und Mengen",
    ),
    "installation_closure_recorded": (
        "Cross-section and all quantities recorded",
        "Querschnitt und alle Mengen erfasst",
    ),
    "installation_closure_open": (
        "Cross-section or quantity still open",
        "Querschnitt oder Menge weiterhin offen",
    ),
    # A report saved before the closure existed keeps the fact it recorded
    # nothing, instead of being read as an open or a recorded closure today.
    "installation_closure_not_recorded": (
        "Not recorded in this saved report",
        "In diesem gespeicherten Bericht nicht erfasst",
    ),
    "installation_string_recorded_count": (
        "Strings with cross-section and quantities recorded",
        "Strings mit erfasstem Querschnitt und erfassten Mengen",
    ),
    "installation_string_open_count": (
        "Strings with an open cross-section or quantity",
        "Strings mit offenem Querschnitt oder offener Menge",
    ),
    "installation_length": (
        "Route length + extra length",
        "Leitungsweglänge + Zusatzlänge",
    ),
    "installation_layout_confirmation_required": (
        "Confirm against the current layout",
        "Mit der aktuellen Planung abgleichen",
    ),
    "installation_source_missing": (
        "Measurement or drawing source missing",
        "Quelle für Messung oder Zeichnung fehlt",
    ),
    "installation_source_export_unconfirmed": (
        "Source export permission unconfirmed",
        "Berechtigung zum Export der Quelldaten nicht bestätigt",
    ),
    "installation_route_endpoints_differ": (
        "Route endpoints differ from the saved connection points",
        "Endpunkte des Leitungswegs weichen von den gespeicherten Anschlusspunkten ab",
    ),
    "installation_height_missing": ("Elevation missing", "Höhenangabe fehlt"),
    "installation_extra_length_unconfirmed": (
        "Extra length or its basis is missing",
        "Zusatzlänge oder deren Grundlage fehlt",
    ),
    "installation_route_length_not_positive": (
        "A positive route length is required",
        "Die Leitungsweglänge muss größer als null sein",
    ),
    "installation_string_links": (
        "PV string and circuit links",
        "Zuordnung von PV-Strings und Stromkreisen",
    ),
    "installation_string_link_scope": (
        "These links record the project's declared string and circuit identities together with the cross-section and measured length of each recorded run. Conductor sizing, voltage drop, connector counts, protection, manufacturer terminal allocation and electrical approval remain unassessed.",
        "Diese Zuordnungen halten die im Projekt angegebenen PV-Strings und Stromkreise zusammen mit dem Querschnitt und der ermittelten Länge jeder erfassten Leitung fest. Leiterauslegung, Spannungsfall, Steckverbinderzahlen, Schutzmaßnahmen, herstellerseitige Anschlussbelegung und elektrische Freigabe bleiben ungeprüft.",
    ),
    "installation_string": ("PV string ID", "PV-String-Kennung"),
    "installation_link_circuit": ("Circuit ID", "Stromkreis-Kennung"),
    "installation_link_cables": (
        "Recorded cable runs",
        "Erfasste Leitungen und Leiter",
    ),
    "installation_string_link_linked": (
        "Project identities linked",
        "Projektangaben zugeordnet",
    ),
    "installation_string_link_unlinked": (
        "No circuit link declared",
        "Keine Stromkreiszuordnung angegeben",
    ),
    "installation_string_link_stale_string": (
        "Referenced PV string is missing",
        "Referenzierter PV-String fehlt",
    ),
    "installation_string_link_stale_circuit": (
        "Referenced circuit is missing",
        "Referenzierter Stromkreis fehlt",
    ),
    "installation_string_link_wrong_circuit_kind": (
        "Referenced circuit is not PV DC",
        "Referenzierter Stromkreis ist kein PV-DC-Stromkreis",
    ),
    "installation_string_link_inverter_endpoint_unresolved": (
        "Exactly one selected-inverter endpoint has not been established",
        "Im Stromkreis ist nicht genau ein Anschlusspunkt des ausgewählten Wechselrichters angegeben.",
    ),
    "installation_string_cable_runs_missing": (
        "No cable runs recorded",
        "Keine Leitungen oder Leiter erfasst",
    ),
    "installation_string_plan_missing": (
        "No saved PV string plan is available for this review.",
        "Für diese Prüfung liegt kein gespeicherter PV-Stringplan vor.",
    ),
    "installation_string_plan_empty": (
        "The saved PV string plan contains no strings.",
        "Der gespeicherte PV-Stringplan enthält keine Strings.",
    ),
    "installation_string_plan_hash": (
        "Saved PV string plan SHA-256",
        "SHA-256 des gespeicherten PV-Stringplans",
    ),
    "installation_input_hash": (
        "Installation input SHA-256",
        "SHA-256 der Installationseingaben",
    ),
    "installation_geometry_hash": (
        "Saved geometry SHA-256",
        "SHA-256 der gespeicherten Geometrie",
    ),
    "installation_string_link_review": (
        "PV string/circuit link review",
        "Prüfung der PV-String-/Stromkreiszuordnung",
    ),
    "installation_string_link_material_scope": (
        "Project identity review · no material quantity",
        "Prüfung der Projektzuordnung · keine Materialmenge",
    ),
    "installation_string_linked_count": (
        "Linked project identities",
        "Zugeordnete Projektangaben",
    ),
    "installation_string_unresolved_count": (
        "Unresolved string or circuit identities",
        "Ungeklärte String- oder Stromkreiszuordnungen",
    ),
    "installation_string_cable_gaps": (
        "Referenced circuits without recorded cable runs",
        "Referenzierte Stromkreise ohne erfasste Leitungen oder Leiter",
    ),
    "pv_components_roof_scope": (
        "Module counts come from the saved roof layout retained for this report. The modules are design references; electrical and mounting suitability require project-specific assessment.",
        "Die Stückzahlen stammen aus der für diesen Bericht gespeicherten Dachbelegung. Die Module dienen als Auslegungsreferenz; ihre elektrische Eignung und ihre Eignung für die Montage müssen projektspezifisch geprüft werden.",
    ),
    "material_snapshot": ("Materials snapshot SHA-256", "SHA-256 des Materialstands"),
    "material_woo_product": ("Selected equipment", "Ausgewählte Geräte"),
    "material_pv_reference": (
        "PV reference module · project quotation",
        "PV-Referenzmodul · Projektangebot",
    ),
    "material_manufacturer_included": (
        "Included according to manufacturer · quantity unconfirmed",
        "Laut Hersteller mitgeliefert · Menge unbestätigt",
    ),
    "material_customer_supplied_required": (
        "Customer supplies after project-specific selection",
        "Kundenseitige Bereitstellung nach projektspezifischer Auswahl",
    ),
    "material_site_engineering_required": (
        "Site engineering assessment required",
        "Projektspezifische Planungsprüfung erforderlich",
    ),
    "material_meter": ("Energy meter", "Energiezähler"),
    "material_backup": ("Backup components", "Notstromkomponenten"),
    "material_parallel_controller": ("Parallel controller", "Parallelsteuerung"),
    "material_installation_open": (
        "Installation materials require project-specific design",
        "Installationsmaterialien müssen projektspezifisch ausgelegt werden",
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
    "generation_dc": ("PV generation (DC)", "PV-Erzeugung (DC)"),
    "curtailed_dc": ("PV curtailment (DC)", "PV-Abregelung (DC)"),
    "scenario_dc_scope": (
        "PV generation and curtailment are calculated at the DC bus; load supply and grid flows are calculated on the AC side. Storage results use the saved loss assumptions.",
        "Die PV-Werte für Erzeugung und Abregelung beziehen sich auf den DC-Zwischenkreis. Die Versorgung der Verbraucher sowie Netzbezug und Einspeisung werden auf der AC-Seite berechnet; die Speicherwerte beruhen auf den gespeicherten Verlustannahmen.",
    ),
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
    "pv_standby_title": (
        "Manufacturer standby interval",
        "Standby-Bereich des Herstellers",
    ),
    "pv_standby_scope": (
        "The manufacturer describes standby in this input-voltage interval. These MPP estimates do not establish actual operation or annual exposure; a single point cannot determine the state or recovery at the lower boundary. The absolute voltage rating and MPPT window are checked separately.",
        "Der Hersteller beschreibt für diesen Eingangsspannungsbereich den Standby-Modus. Die geschätzten MPP-Werte belegen weder den tatsächlichen Betrieb noch die Häufigkeit über das Jahr. Ein einzelner Punkt bestimmt weder den Zustand an der unteren Grenze noch die Rückkehr zum Betrieb. Die absolute Spannungsgrenze und das MPPT-Fenster werden gesondert geprüft.",
    ),
    "pv_standby_case": ("Operating point", "Arbeitspunkt"),
    "pv_standby_case_stc": ("STC", "STC"),
    "pv_standby_case_hot": ("Modeled hot case", "Modellierter warmer Fall"),
    "pv_standby_case_cold": ("Modeled cold case", "Modellierter kalter Fall"),
    "pv_standby_value": ("MPP estimate", "Geschätzter MPP"),
    "pv_standby_observation": ("Observation", "Einordnung"),
    "pv_standby_in_interval": (
        "In standby interval · review",
        "Im Standby-Bereich · prüfen",
    ),
    "pv_standby_boundary": (
        "At the lower boundary · review",
        "An der unteren Grenze · prüfen",
    ),
    "pv_standby_outside_interval": (
        "Outside interval for this point",
        "Für diesen Punkt außerhalb des Bereichs",
    ),
    "pv_standby_unavailable": ("Estimate unavailable", "Kein Schätzwert verfügbar"),
}

CHECKS = {
    "plant_grid_phase": (
        "Plant grid phases",
        "Phasenanzahl am Netzanschluss der Gesamtanlage",
    ),
    "plant_operating_mode": ("Plant operating mode", "Betriebsart der Gesamtanlage"),
    "plant_parallel_count": (
        "Converters in the group",
        "Anzahl der Umrichter in der Gruppe",
    ),
    "plant_joint_operation": ("Joint operation", "Gemeinsamer Betrieb"),
    "plant_operating_scope": (
        "Manufacturer requirement applicability",
        "Anwendbarkeit der Herstellervorgabe",
    ),
    "plant_controller_network_count": (
        "Inverters on the controller network",
        "Wechselrichter am Controller",
    ),
    "plant_controller": ("Shared controller", "Gemeinsamer Controller"),
    "plant_pv_allocation": (
        "Allocated PV nameplate rating",
        "Zugewiesene PV-Nennleistung",
    ),
    "plant_energy_allocation": (
        "Allocated usable energy target",
        "Zugewiesener Zielwert für die nutzbare Energie",
    ),
    "plant_discharge_allocation": (
        "Allocated continuous discharge power target",
        "Zugewiesener Zielwert für die Dauerentladeleistung",
    ),
    "plant_joint_energy": (
        "Usable energy at the shared connection",
        "Nutzbare Energie am gemeinsamen Anschlusspunkt",
    ),
    "plant_joint_discharge": (
        "Continuous discharge power at the shared connection",
        "Dauerentladeleistung am gemeinsamen Anschlusspunkt",
    ),
    "pv_iv_model": ("Single-diode model fit", "Anpassung des Eindiodenmodells"),
    "pv_model_applicability": (
        "Model applicability to this module",
        "Anwendbarkeit des Modells auf dieses Modul",
    ),
    "pv_operating_conditions": (
        "Operating-condition domain",
        "Bereich der Betriebsbedingungen",
    ),
    "pv_operating_curve": ("Operating curve", "Betriebskennlinie"),
    "pv_hot_mppt": (
        "Modeled MPP voltage: hot case",
        "Modellierte MPP-Spannung: heißer Betriebsfall",
    ),
    "pv_cold_mppt": (
        "Modeled MPP voltage: cold case",
        "Modellierte MPP-Spannung: kalter Betriebsfall",
    ),
    "pv_hot_current": (
        "Modeled MPPT current: hot case",
        "Modellierter MPPT-Strom: heißer Betriebsfall",
    ),
    "pv_cold_current": (
        "Modeled MPPT current: cold case",
        "Modellierter MPPT-Strom: kalter Betriebsfall",
    ),
    "pv_hot_isc": (
        "Modeled short-circuit current: hot case",
        "Modellierter Kurzschlussstrom: heißer Betriebsfall",
    ),
    "pv_cold_isc": (
        "Modeled short-circuit current: cold case",
        "Modellierter Kurzschlussstrom: kalter Betriebsfall",
    ),
    "pv_parallel_count": ("Strings per MPPT", "Strings je MPPT"),
    "pv_layout_coverage": ("Roof module assignment", "Zuordnung der Dachmodule"),
    "pv_tracker": ("MPPT assignment", "MPPT-Zuordnung"),
    "pv_input": ("Inverter input assignment", "Zuordnung der Wechselrichtereingänge"),
    "pv_cold_voc": ("Cold open-circuit voltage", "Leerlaufspannung bei Kälte"),
    "pv_module_voltage": (
        "Module system voltage (IEC rating)",
        "Systemspannung des Moduls (IEC-Bemessung)",
    ),
    "pv_stc_mppt": ("MPP voltage at STC", "MPP-Spannung unter STC"),
    "pv_nameplate_layout": ("Wired PV nameplate power", "Verschaltete PV-Nennleistung"),
    "pv_stc_current": ("MPPT operating current at STC", "MPPT-Betriebsstrom unter STC"),
    "pv_stc_isc": (
        "MPPT short-circuit current at STC",
        "MPPT-Kurzschlussstrom unter STC",
    ),
    "pv_parallel_match": (
        "Parallel string lengths and orientations",
        "Länge und Ausrichtung paralleler Strings",
    ),
    "pv_operating_temperatures": (
        "Hot and cold operating MPP",
        "MPP bei heißem und kaltem Betrieb",
    ),
    "pv_design_current": ("Design current", "Auslegungsstrom"),
    "pv_wiring_protection": ("Wiring and protection", "Leitungen und Schutz"),
    "grid_output_ceiling": (
        "Inverter output limit in grid-connected operation",
        "Leistungsgrenze des Wechselrichters im Netzparallelbetrieb",
    ),
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
