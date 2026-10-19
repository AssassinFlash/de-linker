#365 rounds 2 and 3 — configurator prefill regressions, registered for #339

The campaign fixture ticket (#339) should keep these sentences. Until that suite
exists they run in `services/genie/tests/test_prefill.py` and
`services/genie/tests/test_route.py`.

- Negated backup is `backup=none`, never `needed`: "ohne Notstrom", "kein Notstrom nötig", "no backup needed", "kein Ersatzstrom".
- A question does not prefill phase or backup: "Ist einphasig möglich?", "can it do backup?", "unterstützt das Drehstrom?".
- Stated figures the first reader dropped: "annual consumption 6000 kWh", "6000 kWh Jahresverbrauch", "12 kW peak", "400 V Drehstrom", "12 000 kWh pro Jahr" (not 0).
- A postcode next to PLZ / Postleitzahl / postcode / ZIP is `plz`.
- An earlier user message in the same conversation still prefills: "12 kWp, dreiphasig" then "und die Speichergröße?".
- "Drehstrom" and "three-phase" are both phase 3.
- A later denial overrides the field: "12 kWp, dreiphasig" then "kein Drehstrom" leaves phase out; the same for "Ich habe keinen Drehstrom"; "mit Notstrom" then "kein Notstrom" is backup none.
- A comma is its own clause: "Ich habe Drehstrom, ist das möglich?" and "I have three-phase, is that supported?" keep phase 3.
- A wh-word that introduces a statement still counts: "Was ich brauche: 12 kWp, Drehstrom", "What I need is three-phase", "Wie gesagt, der Anschluss ist dreiphasig".
- An indirect or verb-first question does not prefill: "ob Notstrom möglich ist", "whether backup is possible", "if backup is possible", "geht das mit Drehstrom", "und kann es Notstrom".
- "Mein Haus ist dreiphasig, kann es auch Notstrom?" keeps phase and does not set backup.
- "ohne Netz und mit Notstrom" is backup needed. "nicht nur Notstrom, sondern auch Eigenverbrauch" and "kein Problem ich brauche Notstrom" leave backup out.
- Year words: "Jahresstromverbrauch 6000 kWh", "Stromverbrauch 6000 kWh", "annual consumption of about 6000 kWh", "6000 kWh p.a.", "Unser Jahresverbrauch liegt bei 6000 kWh", "Our annual consumption is 6000 kWh".
- "PLZ 01067" keeps the leading zero.

Design (dossier §1.12, deterministic read §1.1): only user messages; a later message overrides the same field; the model passes `{}`; all five spec fields (`pv_kwp`, `annual_load_kwh`, `phase`, `backup`, `plz`) are filled by the service. The URL mapping is the committed fixture `services/genie/tests/fixtures/size-hint-urls.json`, checked by `SizeHintTest`.
