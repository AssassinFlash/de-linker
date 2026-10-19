#365 round 2 — configurator prefill regressions, registered for #339

The campaign fixture ticket (#339) should keep these sentences. Until that suite
exists they run in `services/genie/tests/test_prefill.py` and
`services/genie/tests/test_route.py`.

- Negated backup is `backup=none`, never `needed`: "ohne Notstrom", "kein Notstrom nötig", "no backup needed", "kein Ersatzstrom".
- A question does not prefill phase or backup: "Ist einphasig möglich?", "can it do backup?", "unterstützt das Drehstrom?".
- Stated figures the first reader dropped: "annual consumption 6000 kWh", "6000 kWh Jahresverbrauch", "12 kW peak", "400 V Drehstrom", "12 000 kWh pro Jahr" (not 0).
- A postcode next to PLZ / Postleitzahl / postcode / ZIP is `plz`.
- An earlier user message in the same conversation still prefills: "12 kWp, dreiphasig" then "und die Speichergröße?".
- "Drehstrom" and "three-phase" are both phase 3.

Design (dossier §1.12, deterministic read §1.1): only user messages; a later message overrides the same field; the model passes `{}`; all five spec fields (`pv_kwp`, `annual_load_kwh`, `phase`, `backup`, `plz`) are filled by the service. The URL mapping is the committed fixture `services/genie/tests/fixtures/size-hint-urls.json`, checked by `SizeHintTest`.
