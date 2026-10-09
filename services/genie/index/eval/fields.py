"""The question each fact-card field becomes, in English and German.

Keys are the field codes of the fact-cards spec (old repository,
knowledge/fact-cards/README.md §4). A field becomes a question only when it is one an
installer asks about a model: identity, regional, lifecycle and free-form "other fact"
rows, and rows numbered 90 and up (labels as each document prints them), are left out.
`{model}` is the model designation as the card prints it; CP-01 also names `{partner}`.
German follows the formal register of the site (de_DE_formal).
"""

# Fields whose evidence is a drawing rather than text: clearance and dimension drawings
# (IN-03, ME-05), layouts (IN-04), wiring and earthing diagrams (IN-05, IN-07, IN-08),
# torque labels (IN-06), pin-outs (CO-03) and compatibility matrices (CP-01). A row of
# these fields that the card read off the rendered page is a figure question.
FIGURE_FIELDS = frozenset(
    {"IN-03", "IN-04", "IN-05", "IN-06", "IN-07", "IN-08", "ME-05", "CO-03", "CP-01"}
)

QUESTIONS: dict[str, tuple[str, str]] = {
    # EL · electrical
    "EL-01": (
        "What is the nominal voltage of the {model}?",
        "Wie hoch ist die Nennspannung beim {model}?",
    ),
    "EL-02": (
        "What is the operating voltage range of the {model}?",
        "Welchen Betriebsspannungsbereich hat der {model}?",
    ),
    "EL-03": (
        "What is the rated or maximum current of the {model}?",
        "Wie hoch ist der Nenn- bzw. Maximalstrom beim {model}?",
    ),
    "EL-04": (
        "What is the rated power of the {model}?",
        "Wie hoch ist die Nennleistung beim {model}?",
    ),
    "EL-05": (
        "What peak power can the {model} deliver, and for how long?",
        "Welche Spitzenleistung liefert der {model} und wie lange?",
    ),
    "EL-06": (
        "What grid frequency does the {model} support?",
        "Welche Netzfrequenz unterstützt der {model}?",
    ),
    "EL-07": (
        "Which grid types or phases does the {model} support?",
        "Welche Netzformen bzw. Phasen unterstützt der {model}?",
    ),
    "EL-08": (
        "What is the standby or self-consumption of the {model}?",
        "Wie hoch ist der Eigenverbrauch im Standby beim {model}?",
    ),
    "EL-10": (
        "What is the maximum PV input power of the {model}?",
        "Wie hoch ist die maximale PV-Eingangsleistung beim {model}?",
    ),
    "EL-11": (
        "What is the maximum DC input voltage of the {model}?",
        "Wie hoch ist die maximale DC-Eingangsspannung beim {model}?",
    ),
    "EL-12": (
        "What is the MPPT voltage range of the {model}?",
        "Welchen MPPT-Spannungsbereich hat der {model}?",
    ),
    "EL-13": (
        "What is the start-up voltage of the {model}?",
        "Wie hoch ist die Startspannung beim {model}?",
    ),
    "EL-14": (
        "How many MPPTs and strings per MPPT does the {model} have?",
        "Wie viele MPPTs und Strings pro MPPT hat der {model}?",
    ),
    "EL-15": (
        "What is the maximum input current per MPPT of the {model}?",
        "Wie hoch ist der maximale Eingangsstrom pro MPPT beim {model}?",
    ),
    "EL-16": (
        "What is the maximum short-circuit current per MPPT of the {model}?",
        "Wie hoch ist der maximale Kurzschlussstrom pro MPPT beim {model}?",
    ),
    "EL-20": (
        "What battery voltage range does the {model} accept?",
        "Welchen Batteriespannungsbereich akzeptiert der {model}?",
    ),
    "EL-21": (
        "What is the maximum charge and discharge current of the {model}?",
        "Wie hoch ist der maximale Lade- und Entladestrom beim {model}?",
    ),
    "EL-22": (
        "What is the maximum charge and discharge power of the {model}?",
        "Wie hoch ist die maximale Lade- und Entladeleistung beim {model}?",
    ),
    "EL-23": (
        "How many battery ports does the {model} have?",
        "Wie viele Batterieanschlüsse hat der {model}?",
    ),
    "EL-30": (
        "What is the rated AC output power of the {model}?",
        "Wie hoch ist die AC-Nennausgangsleistung beim {model}?",
    ),
    "EL-31": (
        "What is the maximum apparent power of the {model}?",
        "Wie hoch ist die maximale Scheinleistung beim {model}?",
    ),
    "EL-32": (
        "What is the maximum AC output current of the {model}?",
        "Wie hoch ist der maximale AC-Ausgangsstrom beim {model}?",
    ),
    "EL-33": (
        "What power factor range does the {model} support?",
        "Welchen Leistungsfaktorbereich unterstützt der {model}?",
    ),
    "EL-34": (
        "What is the THDi of the {model}?",
        "Wie hoch ist der THDi beim {model}?",
    ),
    "EL-40": (
        "What is the rated backup output power of the {model}?",
        "Wie hoch ist die Nennleistung des Backup-Ausgangs beim {model}?",
    ),
    "EL-41": (
        "What peak power does the backup output of the {model} deliver?",
        "Welche Spitzenleistung liefert der Backup-Ausgang beim {model}?",
    ),
    "EL-42": (
        "What is the backup switchover time of the {model}?",
        "Wie lang ist die Umschaltzeit auf Backup beim {model}?",
    ),
    "EL-50": (
        "How does the {model} measure current, directly or through CTs?",
        "Wie misst der {model} den Strom, direkt oder über Stromwandler?",
    ),
    "EL-51": (
        "What CT ratio does the {model} use?",
        "Welches Stromwandlerverhältnis verwendet der {model}?",
    ),
    "EL-52": (
        "What is the measurement accuracy class of the {model}?",
        "Welche Genauigkeitsklasse hat der {model}?",
    ),
    # ME · mechanical
    "ME-01": (
        "What are the dimensions of the {model}?",
        "Welche Abmessungen hat der {model}?",
    ),
    "ME-02": ("How much does the {model} weigh?", "Wie schwer ist der {model}?"),
    "ME-03": ("How is the {model} mounted?", "Wie wird der {model} montiert?"),
    "ME-04": (
        "What housing or form factor does the {model} have?",
        "Welche Bauform hat der {model}?",
    ),
    "ME-05": (
        "What are the assembled dimensions of the {model} per configuration?",
        "Welche Abmessungen hat der {model} im aufgebauten Zustand je Konfiguration?",
    ),
    "ME-08": (
        "What user interface does the {model} have?",
        "Welche Bedienschnittstelle hat der {model}?",
    ),
    # CO · communication
    "CO-01": (
        "Which communication interfaces does the {model} have?",
        "Welche Kommunikationsschnittstellen hat der {model}?",
    ),
    "CO-02": (
        "Which communication protocols does the {model} use?",
        "Welche Kommunikationsprotokolle verwendet der {model}?",
    ),
    "CO-03": (
        "What is the pin assignment of the communication ports of the {model}?",
        "Wie ist die Pinbelegung der Kommunikationsanschlüsse beim {model}?",
    ),
    "CO-04": (
        "What is the maximum communication cable length of the {model}?",
        "Wie lang darf das Kommunikationskabel beim {model} maximal sein?",
    ),
    "CO-05": (
        "How are termination and addressing set on the {model}?",
        "Wie werden Abschlusswiderstand und Adresse beim {model} eingestellt?",
    ),
    "CO-06": (
        "Which monitoring platform or app works with the {model}?",
        "Mit welcher Monitoring-Plattform oder App wird der {model} überwacht?",
    ),
    # CP · compatible devices
    "CP-01": (
        "Is the {partner} listed as compatible with the {model}?",
        "Ist {partner} als kompatibel mit dem {model} gelistet?",
    ),
    "CP-03": (
        "What pairing limits apply to the {model}?",
        "Welche Kombinationsgrenzen gelten für den {model}?",
    ),
    # CE · certification
    "CE-01": (
        "Which safety standards does the {model} meet?",
        "Welche Sicherheitsnormen erfüllt der {model}?",
    ),
    "CE-02": (
        "Which EMC standards does the {model} meet?",
        "Welche EMV-Normen erfüllt der {model}?",
    ),
    "CE-03": (
        "Is the {model} certified to UN38.3 for transport?",
        "Ist der {model} nach UN38.3 für den Transport zertifiziert?",
    ),
    "CE-04": (
        "Which certification marks does the {model} carry?",
        "Welche Prüfzeichen trägt der {model}?",
    ),
    "CE-05": (
        "Which directives does the declaration of conformity of the {model} list?",
        "Welche Richtlinien nennt die Konformitätserklärung des {model}?",
    ),
    "CE-08": (
        "Which certificate has been issued for the {model}?",
        "Welches Zertifikat wurde für den {model} ausgestellt?",
    ),
    # WA · warranty
    "WA-01": (
        "How long is the product warranty of the {model}?",
        "Wie lange gilt die Produktgarantie beim {model}?",
    ),
    "WA-02": (
        "What performance or capacity warranty does the {model} have?",
        "Welche Leistungs- bzw. Kapazitätsgarantie hat der {model}?",
    ),
    "WA-03": (
        "Under which conditions does the warranty of the {model} apply?",
        "Unter welchen Bedingungen gilt die Garantie des {model}?",
    ),
    "WA-05": (
        "What does the warranty of the {model} exclude?",
        "Was ist von der Garantie des {model} ausgeschlossen?",
    ),
    # PK · package contents
    "PK-01": (
        "What is included in the delivery of the {model}?",
        "Was gehört beim {model} zum Lieferumfang?",
    ),
    "PK-02": (
        "What does the installer have to provide for the {model}?",
        "Was muss der Installateur beim {model} selbst bereitstellen?",
    ),
    "PK-03": (
        "Which optional accessories are available for the {model}?",
        "Welches optionale Zubehör gibt es für den {model}?",
    ),
    # FW · firmware
    "FW-02": (
        "How is the firmware of the {model} updated?",
        "Wie wird die Firmware des {model} aktualisiert?",
    ),
    "FW-03": (
        "Which firmware version does the {model} need on the partner device?",
        "Welche Firmwareversion braucht der {model} auf dem Partnergerät?",
    ),
    # IN · installation
    "IN-01": (
        "Where may the {model} be installed?",
        "Wo darf der {model} installiert werden?",
    ),
    "IN-02": (
        "How is the {model} mounted during installation?",
        "Wie wird der {model} bei der Installation befestigt?",
    ),
    "IN-03": (
        "What clearances does the {model} need?",
        "Welche Mindestabstände braucht der {model}?",
    ),
    "IN-04": (
        "What system limits and layouts apply to the {model}?",
        "Welche Systemgrenzen und Aufbauvarianten gelten für den {model}?",
    ),
    "IN-05": (
        "Which cables does the {model} need?",
        "Welche Kabel braucht der {model}?",
    ),
    "IN-06": (
        "What tightening torques apply to the {model}?",
        "Welche Anzugsdrehmomente gelten beim {model}?",
    ),
    "IN-07": (
        "Which protective devices does the {model} require?",
        "Welche Schutzeinrichtungen braucht der {model}?",
    ),
    "IN-08": ("How is the {model} earthed?", "Wie wird der {model} geerdet?"),
    "IN-09": (
        "How is the {model} commissioned?",
        "Wie wird der {model} in Betrieb genommen?",
    ),
    "IN-10": (
        "Which other site restrictions apply to the {model}?",
        "Welche weiteren Einschränkungen am Aufstellort gelten für den {model}?",
    ),
    # EN · environment
    "EN-01": (
        "What is the operating temperature range of the {model}?",
        "Welchen Betriebstemperaturbereich hat der {model}?",
    ),
    "EN-02": (
        "What is the storage temperature of the {model}?",
        "Bei welcher Temperatur darf der {model} gelagert werden?",
    ),
    "EN-03": (
        "What relative humidity does the {model} tolerate?",
        "Welche relative Luftfeuchtigkeit verträgt der {model}?",
    ),
    "EN-04": (
        "Up to what altitude can the {model} operate?",
        "Bis zu welcher Höhe kann der {model} betrieben werden?",
    ),
    "EN-05": (
        "What is the ingress protection rating of the {model}?",
        "Welche Schutzart hat der {model}?",
    ),
    "EN-06": ("How loud is the {model}?", "Wie laut ist der {model}?"),
    "EN-07": ("How is the {model} cooled?", "Wie wird der {model} gekühlt?"),
    "EN-08": (
        "Which other environmental limits apply to the {model}?",
        "Welche weiteren Umgebungsgrenzen gelten für den {model}?",
    ),
    # EF · efficiency
    "EF-01": (
        "What is the maximum efficiency of the {model}?",
        "Wie hoch ist der maximale Wirkungsgrad beim {model}?",
    ),
    "EF-02": (
        "What is the European efficiency of the {model}?",
        "Wie hoch ist der europäische Wirkungsgrad beim {model}?",
    ),
    "EF-03": (
        "What is the MPPT efficiency of the {model}?",
        "Wie hoch ist der MPPT-Wirkungsgrad beim {model}?",
    ),
    "EF-04": (
        "What is the round-trip or battery-to-AC efficiency of the {model}?",
        "Wie hoch ist der Batterie-zu-AC-Wirkungsgrad beim {model}?",
    ),
    # BA · battery
    "BA-01": (
        "What cell chemistry does the {model} use?",
        "Welche Zellchemie verwendet der {model}?",
    ),
    "BA-02": (
        "What is the usable energy of the {model}?",
        "Wie viel nutzbare Energie hat der {model}?",
    ),
    "BA-03": (
        "What is the nominal energy of the {model}?",
        "Wie hoch ist die Nennenergie beim {model}?",
    ),
    "BA-04": (
        "What is the capacity in Ah of the {model}?",
        "Welche Kapazität in Ah hat der {model}?",
    ),
    "BA-05": (
        "What is the cell configuration of the {model}?",
        "Wie sind die Zellen beim {model} verschaltet?",
    ),
    "BA-06": (
        "What depth of discharge does the {model} allow?",
        "Welche Entladetiefe erlaubt der {model}?",
    ),
    "BA-07": (
        "What cycle life does the {model} have?",
        "Wie viele Zyklen erreicht der {model}?",
    ),
    "BA-08": (
        "What is the recommended C-rate of the {model}?",
        "Welche C-Rate wird für den {model} empfohlen?",
    ),
    "BA-09": ("What BMS does the {model} use?", "Welches BMS verwendet der {model}?"),
    "BA-10": (
        "How far can the {model} be scaled?",
        "Wie weit lässt sich der {model} erweitern?",
    ),
    "BA-11": (
        "What rules apply to mixing and expanding the {model}?",
        "Welche Regeln gelten für das Mischen und Erweitern beim {model}?",
    ),
}
