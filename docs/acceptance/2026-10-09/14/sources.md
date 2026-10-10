# #14 Solution Configurator: sources of the engine's rules

Every number the engine decides with lives in `services/engine/src/linker_engine/rules.py`.
This file is the evidence record that rules.py points to (`SOURCES`): for each rule, the
source, the Apify run that read it on 2026-10-09, and where the statement stands. Statements
are paraphrased; page numbers refer to the PDF as fetched. Run IDs are runs of the project's
Apify account (`api.apify.com/v2/actor-runs/<id>`); their datasets and key-value stores hold
the fetched text or file.

Rules marked **unverified planning assumption** have no published source. They are
`verified=False` in rules.py, the design report lists them under "Assumptions and limits",
and the PR names them.

## Storage sizing (HTW Berlin)

| Rule (rules.py) | Value | Source | Apify run | What it says, where |
|---|---|---|---|---|
| `HTW_MIN_KWP_PER_MWH` | 0.5 kWp per MWh/a | Orth, Weniger, Meissner: Empfehlungen zur Auslegung von Solarstromspeichern (2022), `ORTH-2022-Empfehlungen-zur-Auslegung-von-Solarstromspeichern.pdf` | `vHhj67xHo315AkvuL` (store `bwEGK7v0WQTz5AsNb`) | p. 1, rule 1: a battery only where the PV power is at least 0.5 kW per 1000 kWh/a of consumption |
| `HTW_MAX_KWH_PER_KWP` | 1.5 kWh per kWp | same | same | p. 1, rule 2: usable capacity at most 1.5 kWh per kW of PV |
| `HTW_MAX_KWH_PER_MWH` | 1.5 kWh per MWh/a | same | same | p. 1, rule 3: usable capacity at most 1.5 kWh per 1000 kWh/a, about the night-time consumption |
| `HTW_DISCHARGE_EFFICIENCY` | 0.94 | HTW FAQ Unabhängigkeitsrechner, https://solar.htw-berlin.de/faq-unabhaengigkeitsrechner/ | `WOAJD3CFcs6CfuCJA`, `UScs0Pf8pb4tbnCma` | battery inverter modelled with a constant 94 % efficiency for charging and for discharging |
| `HTW_REFERENCE_YIELD` | 1024 kWh per kWp | same | `WOAJD3CFcs6CfuCJA` | with the calculator's inputs (35° south roof, AC power = DC power) the PV yield is 1024 kWh/kW a year |
| `HTW_TABLE_MIN_KWH`, `HTW_TABLE_MAX_KWH` | 2000, 10 000 kWh/a | same | `WOAJD3CFcs6CfuCJA` | the calculator accepts annual consumption between 2000 and 10 000 kWh (size of its result table) |
| `DEFAULT_TILT_DEG`, `DEFAULT_AZIMUTH_DEG` | 35°, 180° | same | `WOAJD3CFcs6CfuCJA` | the simulated PV system sits on a 35° south-facing roof |
| `HTW_HOUSEHOLD_SPREAD_PP` | 5 percentage points | HTW Berlin, Studie Dezentrale Solarstromspeicher (2015), `HTW-Studie-Dezentrale-Solarstromspeicher.pdf` | `TQzdygoq4Pu2qSSBA` (store `GAs2BCJbePvdfR5di`) | p. 34: of 74 households simulated with 1 kWp/MWh and 1 kWh/MWh, most deviate by less than 5 percentage points from the mean self-sufficiency |
| `HEAT_PUMP_KWH_LOW`, `HEAT_PUMP_KWH_HIGH` | 2664, 4011 kWh/a | HTW Berlin, Stromspeicher-Inspektion 2021 | `TQzdygoq4Pu2qSSBA` | p. 24: the four heat pumps of the reference data used between 2664 and 4011 kWh/a for hot water and space heating |
| `EV_KWH_LOW`, `EV_KWH_HIGH` | 1551, 3097 kWh/a | HTW Berlin, Solares Laden von Elektrofahrzeugen (2025) | `TQzdygoq4Pu2qSSBA` | p. 33: half of the 730 households charge between 1551 and 3097 kWh/a at their own wallbox (median 2228) |

The lookup tables (`services/engine/data/htw/tabelleAutarkie.json`, `tabelleEigenverbrauch.json`)
were read byte for byte by runs `PDwkAtxn2VEMg6Wq3` and `DzDiCEbTQb4QgEh6M` (and together with
`config.json` by `XNBE9GWmP7lZZ3k69`); their sha256 are in `data/htw/source.json`. The bilinear
interpolation follows the calculator's own `js/unabhaengig.js` (run `zH9d2xlHVeRGC2dOj`; the
calculator's network traffic in `GEFXmU6AgcPuQtsgV`). HTW Berlin states no licence for the
tables (imprint, run `uXO2gxODb6sUm6kIQ`); the report credits HTW Berlin wherever a value from
them appears.

**Open item (tracked, does not block this delivery):** whether the byte-exact lookup tables may
ship in our engine, or must be re-derived into our own numbers, is not settled by anything HTW
publishes. Action: ask HTW Berlin through the contact on the calculator page for written
permission, or verify a licence statement through Apify before the cutover (#17); until then
the tables stay in `data/htw/` with this record. The delivery of #14 is not blocked: the tables
are cited with their origin in every report.

## Grid code (VDE-AR-N 4105)

| Rule | Value | Source | Apify run | What it says |
|---|---|---|---|---|
| `SINGLE_PHASE_MAX_KVA` | 4.6 kVA | energie-experten.org, VDE-AR-N 4105, https://www.energie-experten.org/erneuerbare-energien/photovoltaik/planung/vde-ar-n-4105 | `bnZxTl1v2GWjSM7HO` (dataset `6f0TXWiItSP9WbajX`); search `FYjEnJr8QxvcwoCu1` | unbalance limit of 4.6 kVA per phase (chapter 5.5), so single-phase feed-in stays at or below 4.6 kVA |
| `NA_PROTECTION_KVA` | 30 kVA | same | `bnZxTl1v2GWjSM7HO` | up to 30 kVA the inverter's integrated protection suffices; above 30 kVA a central NA protection at the meter is required |
| `VDE_4110_KW` | 135 kW | same | `bnZxTl1v2GWjSM7HO` | VDE-AR-N 4105 covers systems up to a total active power of 135 kW; above that the medium-voltage rule VDE-AR-N 4110 applies |

## Yield (PVGIS)

| Rule | Value | Source | Apify run | What it says |
|---|---|---|---|---|
| `PVGIS_SYSTEM_LOSS_PCT` | 14 % | PVGIS 5 user manual, https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/pvgis-5-user-manual_en | `z8dqy97enkbhPhktQ` | default value of 14 % for the overall system losses |
| `PVGIS_GRID_DEG` | 0.05° | docs/specs/14-solution-configurator.md | – | cache cell of the PVGIS requests, as the ticket specifies |
| `PVGIS_TIMEOUT_S` | 120 s | **unverified planning assumption** | – | a full 2005–2023 hourly request took 19 s on 2026-10-09 (engine call, not a fact source) |

## String layout and string fuses

| Rule | Value | Source | Apify run | What it says |
|---|---|---|---|---|
| `STRING_FUSE_ISC_FACTOR` | 1.25 × Isc STC | IEC 60364-7-712:2017 as applied in the ElectricalOM "Section 712 – Solar Photovoltaic Systems" calculation sheet (2025-01-23), https://electricalom.com/site/dl/other/Section%20712%20-%20PVs%20Calculations.pdf | `U0rFetot8n3pAno1h` (dataset `Mg9aW1nwNbsI5Ta43`) | Reg. 712.433.101.1: I_SC_MAX = 1.25 × I_SC_STC |
| `STRING_FUSE_OCPR_FACTOR` | 1.35 × I_MOD_MAX_OCPR | same; Mitolo 2025, https://journals.riverpublishers.com/index.php/DGAEJ/article/view/30737/22485 | `U0rFetot8n3pAno1h`; `96LY20aLxSBbZl4Xo` | Reg. 712.431.101/102: string protection is needed when 1.35 × I_MOD_MAX_OCPR < (Ns − 1) × I_SC_MAX; Mitolo: protection is required once the reverse current through a module exceeds its maximum overcurrent protection rating |
| `STRING_FUSE_RATING_MIN`, `STRING_FUSE_RATING_MAX` | 1.5 and 2.4 × Isc STC | ElectricalOM sheet, IEC 62548 check | `U0rFetot8n3pAno1h` | 1.5 × I_SC_STC < In < 2.4 × I_SC_STC. Fronius' operating instructions in the same run ask 1.8 to 2.4 × Isc for its inverters: a manufacturer may narrow the window |
| `STRING_FUSE_POLES` | 2 per string | Mitolo 2025; Eaton Bussmann photovoltaic application guide | `96LY20aLxSBbZl4Xo`; `U0rFetot8n3pAno1h` | in floating (unearthed) arrays both conductors carry fault current, so both are protected; Eaton recommends fuse links in the positive and the negative cable |
| `STRING_FUSE_GROUP` | per MPPT | SMA SMC_RUECK-11; Eaton guide; IEC 62548:2016 (sample) | `U0rFetot8n3pAno1h` | SMA: with at most two strings in parallel the reverse current never exceeds one string's short-circuit current; Eaton: three or more parallel strings need each string protected, fewer do not; IEC 62548 Figure 5 draws a PCE with multiple MPPT inputs as separate arrays. Strings on different MPPT inputs are not in parallel |
| `STRING_T_MIN_C` | −10 °C | **unverified planning assumption** | – | lowest cell temperature for the open-circuit voltage check |
| `STRING_T_CELL_MAX_C` | 70 °C | **unverified planning assumption** | – | highest cell temperature for the MPP voltage check |

## Installer's scope and roof step

| Rule | Value | Status |
|---|---|---|
| `DC_CABLE_M_PER_STRING` | 15 m per pole and string | **unverified planning assumption** (placeholder route; the installer measures it) |
| `CONNECTOR_PAIRS_PER_STRING` | 2 | **unverified planning assumption** (one mating pair at each end of a string) |
| `ROOF_FLAT_TILT_DEG` | 10° | **unverified planning assumption** |
| `ROOF_MAX_TILT_DEG` | 60° | **unverified planning assumption** |
| `ROOF_NORTH_EXCLUSION_DEG` | 45° either side of north | **unverified planning assumption** |
| `ROOF_EDGE_INSET_M` | 0.3 m | **unverified planning assumption** |
| `MODULE_GAP_M` | 0.02 m | **unverified planning assumption** |

## Commercial and industrial

| Rule | Value | Source | Apify run | What it says |
|---|---|---|---|---|
| `LOAD_INTERVAL_H` | 0.25 h | docs/specs/14-solution-configurator.md; MsbG § 55 | `4mBQDAUC1coJgjjZx` | load profiles in quarter-hour values |
| `RLM_THRESHOLD_KWH` | 100 000 kWh/a | Messstellenbetriebsgesetz § 55 (1) Nr. 1, https://www.gesetze-im-internet.de/messbg/__55.html | `4mBQDAUC1coJgjjZx` (dataset `EG83EWwPNpQALx4Ox`) | consumers above 100 000 kWh a year are metered with a meter-reading profile or, where needed, a quarter-hourly registering load profile |
| `CI_HOURS_PEAK` | 1 h (about 1C) | Intilion, https://intilion.com/blog/stromspeicher-fur-gewerbe-und-industrie/ | `qWmgLbKa9QiodeAe1` | for peak shaving a 1C system is often recommended |
| `CI_HOURS_SELF_CONSUMPTION` | 2 h (about 0.5C) | same | `qWmgLbKa9QiodeAe1` | for self-consumption a 0.5C rate is usually enough (target above 200 full cycles a year) |
| `CI_KWH_PER_KWP` | 1 kWh per kWp | Voltfang (2026-02-18), https://voltfang.de/2026/02/18/wie-gross-muss-eine-pv-anlage-fuer-einen-gewerbespeicher-sein/ | `qWmgLbKa9QiodeAe1` | rule of thumb: per 1 kWp of PV about 1 kWh of usable storage |
| `CI_KWP_PER_MWH_LOW`, `CI_KWP_PER_MWH_HIGH` | 0.8, 1.0 kWp per MWh/a | same | `qWmgLbKa9QiodeAe1` | guide value of about 0.8 to 1.0 kWp of PV per MWh of annual consumption |

## Data the engine reads (not rules)

- Postcode positions: GeoNames `DE.zip` (CC BY 4.0), downloaded by run `8C6KD3QLOZSUixFz5`;
  `services/engine/scripts/build_plz.py` writes `data/plz_de.csv.gz`.
- Aerial images: `data/imagery.json`, the 16 states' DOP WMS with credit and licence. These are
  the services the page loads its tiles from at runtime; each answered a GetMap request on
  2026-10-09.
- LoD2 building models: `data/lod2-sources.json`, the states' download patterns and licences
  as the old repository's research recorded them after real downloads on 2026-07-18 (facts
  only; no code was taken). The Munich fixture is a cut of the Bavarian tile 692/5334 fetched
  by the engine on 2026-10-09 (`services/engine/tests/fixtures/lod2/source.json`).
- Products and their figures: the live site's Store API and WC REST API, read-only (GET), on
  2026-10-09; `services/engine/scripts/build_fixtures.py` builds the fixture feed from them.
