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


## Managed roof-derived calendar-year AC reference

The project can explicitly select `pvgis_5_3_roof_ac_reference_v1` as a second
PV-generation method inside the same workspace. It never replaces a failed TMY
or detailed PV task automatically. The server derives site coordinates, actual
included module count and STC power, and each array's inclination/azimuth from
the saved georeferenced, conflict-free layout and the current Woo-maintained
module specification. The browser cannot submit a provider URL or an independent
module-power table.

The customer explicitly chooses the calendar year, ERA5 or SARAH3 database,
provider technology model, mounting model, total system-loss percentage and
terrain-horizon policy. A private explanatory note is optional. These are
scenario choices, not device specifications or manufacturer releases. The
versioned request is the documented JRC `seriescalc` interface; it is distinct
from the typical-year weather interface. No database/year or roof-angle change
is made to obtain a successful response.

`runs/pvgis-reference` queues the registered
`prepare_pvgis_roof_ac_reference_v1` worker. HTTP admission, worker execution,
operator identity and readonly idempotency replay use the same executor set.
The native WordPress identity/origin/nonce, source-operation timeout and
calculation-admission policies apply unchanged. The existing configured weather
transfer limits and PV array/hour limits bound this model; no new engineering
or operational default is introduced.

Every included array has a frozen official request and retained original,
capture and source identity. Acquisition is supervised and cancellable. A private lease-fenced journal
retains complete per-array originals and captures immediately, with one saved
operation start/deadline across retries. Completed arrays reuse those bytes;
invalid originals stay quarantined and cannot become a usable profile. The
shared budget counts complete retained originals and supplies the remaining
allowance before each uncaptured response. It does not claim to meter every
byte of an interrupted stream; such transfers remain bounded by the remaining
per-response cap, finite attempts and original deadline. No new table is used,
and journal data never becomes a partial project asset or run result. All arrays must validate and
have exactly matching calendar axes before their AC output is summed. A partial
array response cannot publish a project profile. The resulting
`pvgis_roof_ac_reference_profile_v1` is available only as `pv_available_ac`; it
cannot be selected as DC input or sent through a second complete loss chain.

New energy calculations check the exact selected profile against its frozen
roof/model parameters and current Woo permission/specification proof. Historical
results retain their own originals. Reports and comparison reports identify
this method, each alternative's own roof/module quantities and assumptions,
without summing alternatives into the current bill of materials. Optional
private notes remain in owner-facing reports and are excluded from Genie
summaries. Actual inverter behavior, nearby/inter-row shading, electrical
qualification and country/grid release remain separate assessments.

The production model claim requires a native official request from the real
customer path, profile adoption and downstream energy/report readback. Synthetic
transport fixtures establish boundaries and arithmetic only; they do not prove
that a current Paris response has succeeded or demonstrate installation accuracy.


Native validation of the derived-angle path exposed one floating-point identity
issue: a saved 30-degree mounting angle reconstructed as 29.999999999999996,
while JRC echoed 30. Only derived request angles may use a decimal spelling
based on the platform's `float_info.dig`, and only when it differs by at most
`math.ulp` of the derived binary value. Larger differences remain unchanged.
The equivalent 360/0 azimuth boundary follows that same bound. Saved geometry,
provider originals/capture identity and the global exact parser are unchanged;
the observed one-degree north echo remains a rejection. The original failed
native run stays quarantined, and a corrected executable requires a new owned
request rather than relabelling its receipt.
