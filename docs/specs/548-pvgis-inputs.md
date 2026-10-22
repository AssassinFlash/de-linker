# PVGIS input assets for the unified planning project

This is one implementation contract within the full delivery objective in map
548. The product scope remains residential and commercial, throughout Europe,
with the same project, revision and frozen run consumed by every screen,
report and commerce handoff. This batch does not establish hardware release,
site shading, country compliance, a public API or UI acceptance.

## Source and model

The source contract is [the primary-source dossier](../research/2026-10-23-pv-inputs/PVGIS-SERIES.md)
and the existing [numerical model contract](../research/2026-10-22-planning-implementation/NUMERICAL-MODELS.md),
sections 3–4. Research acquisition used Apify and preserved actual responses.
The pure adapter reads frozen bytes, without network or provider defaults.

Every request explicitly fixes API 5.3, database, complete year range, exact
latitude/longitude, peak kWp, system loss %, technology, mounting ventilation
class, actual tilt, true-north clockwise azimuth and terrain-horizon choice.
The request does not round the location or angles, optimize the roof posture,
select a German postcode or silently replace an unavailable database/year.
The direct REST aspect conversion is north-clockwise azimuth minus 180°.

The capture fixes requested/effective official URL, HTTP status, MIME type,
UTC retrieval instant, acquisition basis and source identifiers. The parser
requires the same explicit request at the official versioned endpoint,
compares provider input echoes and units, and rejects duplicate JSON fields,
nonfinite values, missing/negative power, invalid quality flags and any
missing, duplicated, out-of-order or wrong-year hour. Operational byte/row
limits are explicit, strict positive integers. Full coverage comes from
calendar timestamps, including leap years, rather than a constant 8760.

The exact raw provider body is retained, with SHA-256, source/rights metadata
and attribution. This permanent asset path is suitable for these licensed
public PVGIS results. It must not be applied to finite-retention imagery or
Solar data. The trusted intake receives retention evidence from the server;
a future browser route must not accept a browser's claim of provider rights
or official acquisition as proof.

## Temporal meaning and output boundary

- ERA5 `HH:30` output is interpreted using the named centered-hour mean model:
  `[timestamp−30min,timestamp+30min)`. Native UTC is retained; no site-local DST
  interpretation is applied to the provider timestamp.
- SARAH observations retain their native instantaneous timestamps even when
  the provider's generic JSON template says `hourly averages`. Using them as
  an energy input requires explicit `sample_value_over_containing_utc_hour_v1`.
  That reconstruction assigns a constant estimate to the containing UTC hour;
  its interval assignment is our declared modelling policy, not an official
  universal interval definition. It never claims measured hourly means,
  energy-preserving conversion of point samples or recovered subhourly detail.
- The provider's `Int` radiation-reconstruction flags are retained independently
  from our temporal reconstruction. A source `Int=0` does not cancel the latter.
- PVGIS `P` in W is converted once to kW at the modelled AC-scenario boundary.
  The explicit system loss has already been applied. This output is not raw DC
  and must not pass through a second complete module/inverter/loss chain.
- A PVGIS system estimate cannot release a specific inverter, shared hybrid
  port, MPPT, battery or grid connection. Near-field and inter-row shading,
  actual electrical capability and site export/storage control remain separate
  assessments. These limits travel with the source in the actual run result.

Two actual provider anomalies are acceptance requirements. `Unknown` technology
can return a normal 200 response, module input echoes and radiation rows while
omitting **all** PV power values and their unit. It must fail intake, never
produce zero PV. The actual north-facing request `aspect=-180` returned `-179`;
this one-degree change must be rejected, never normalized as an equivalent
north label or concealed by tolerance. A different model can support the actual
geometry; changing the customer's roof posture is not the remedy.

## Project and execution integration

The imported asset is private to its project and immutable. The intake checks
write ownership before parsing or writing auxiliary bytes. Its idempotent
receipt preserves the first accepted capture, interpretation and operational
parse limits; later deployment ceilings do not rewrite that receipt.

The server resolves selected asset IDs to exact raw/metadata hashes when
enqueueing the energy run. CSV profiles retain their original pinned TZif;
PVGIS profiles are native UTC and require no OS timezone lookup. A PVGIS asset
is accepted only for the solar-input role, not as load or auxiliary demand.
The worker binds all dependency roles back to the frozen revision's selected
project assets, then reconstructs the same provider input from pinned bytes.
It neither fetches current weather nor chooses a new database, year or model.

The same continuous energy replay and independent conservation/source checks
apply to the provider profile. Results retain project/revision/run identity,
source details, model roles, resolution and reconstruction history. Equipment
and country assessments remain explicitly unassessed in this component; a
successful energy task cannot turn those into a release.

## Independent evidence required for this batch

- Exact ERA5/SARAH3 original hashes, complete 2020 leap-year axis and source
  metadata, plus all actual technology/mounting mapping probe metadata.
- ERA5 original-file Decimal integral **946.43692 kWh** for the fixed 1 kWp
  scenario; no second 14% loss. SARAH produces **979.72921 kWh** only under the
  explicitly selected reconstruction, preserving its instantaneous origin.
- Rejection of wrong identities, MIME/status, malformed JSON/rows/quality,
  wrong units, duplicate fields, incomplete years and the two actual provider
  anomalies above.
- Actual owned asset → immutable project run → registered Worker → continuous
  result using the full 8784-hour provider original and a separately labelled
  synthetic constant 1 kW gross load, zero auxiliary load and no battery.
  Since original max PV is below 1 kW, independent totals are load 8784 kWh,
  solar to load 946.43692 kWh and grid import **7837.56308 kWh**.
- Frozen execution after the project is edited, no PV timezone dependency,
  private ownership, stable import retry and both independent review axes.

These are computational and persistence checks. They do not validate an actual
customer installation or give a field-accuracy percentage to this weather model.
