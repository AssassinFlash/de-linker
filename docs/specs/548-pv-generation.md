# Explicit roof-to-PV generation

This is part of the complete unified-planner goal, not a replacement for its
equipment, shading, qualification, reporting or site-delivery requirements.
It implements the explicit pvlib route in
`research/2026-10-22-planning-implementation/NUMERICAL-MODELS.md` section 4.2.
The existing PVGIS system-output route remains a different named model: its
already converted/loss-adjusted `P` must never enter this DC/converter chain.

## Model and inputs

The initial model is a **uniform, unshaded array reference scenario**. It gives
the comparison baseline required by later geometric and electrical shading
models; it does not calculate site shading or release a real inverter. This
distinction travels with every produced profile and detailed result.

- Read the same validated metric geometry used by plan/map/3D. Derive each
  actual included module ID, count and STC rating from its real panel poses;
  excluded slots contribute nothing. Combine roof slope and mounting tilt
  through the actual ENU normal, not by adding tilt numbers or imposing south.
- A geographic anchor and declared north reference are required. Weather must
  match the exact anchor; interface language, postcode and project type cannot
  replace it. Horizontal surfaces use an explicit orientation-invariant
  convention, not a claim of measured azimuth.
- Weather supplies explicit UTC source/evaluation instants and separate
  energy intervals, GHI/DNI/DHI in W/m², 2m air temperature in °C, 10m wind in
  m/s, surface pressure in Pa, altitude and immutable source details. Missing,
  negative irradiance/wind, nonfinite or physically invalid values are errors.
- Every module's PVWatts temperature coefficient and every array's SAPM
  coefficients, albedo, beam-IAM parameter, diffuse/spectral/soiling factors
  and DC wiring/mismatch factors are explicit sourced scenario parameters.
  No manufacturer approval is inferred from these values. There is no hidden
  global 14% loss, fixed German location or nominal capacity substitution.
- Each actual array belongs to exactly one named conversion group. Its
  independent-MPPT MPP-sum assumption is explicit. DC is combined before one
  shared PVWatts conversion curve and AC cap per group. Independent already
  clipped array AC outputs cannot be added to imitate a shared inverter.

## Reproducible computation

Pin pvlib 0.16.1 and explicitly select the SPA solar-position method, its
year/month delta-T calculation, refraction convention, irradiance transposition
model and extra-terrestrial-radiation/airmass conventions. Weather pressure,
temperature, altitude and native evaluation dates are actual model inputs.

Expose plane irradiance components, incidence angle, optical transfer, cell
temperature, array DC, conversion-group DC/AC and conversion/clipping reduction
in the witness. SAPM uses incident POA and the matching 10m wind; PVWatts DC
uses the explicitly transferred effective irradiance. Preserve units and apply
each declared loss once. Unsupported/nonphysical model results are errors;
never silently repair NaN, negative DC or energy gain into a plausible number.
When GHI, DNI and DHI are all exactly zero, incident POA is physically zero;
resolve this explicit branch before the Perez clearness division. It must not
be implemented as a general NaN-to-zero replacement for nonzero weather.

Output is the named model's estimated AC potential before site export/storage
control. The existing continuous-energy kernel applies those later controls.
Retain geometry/weather/parameter hashes, source/model versions, input/output
time semantics, source accuracy and unassessed requirements. A point/typical
weather reconstruction is not an energy-preserving observation conversion or
a subhourly peak guarantee. Resource ceilings are caller-supplied operational
limits, never engineering bounds or a successful truncated calculation.

## PVGIS TMY weather adapter

The primary acquisition and temporal evidence are in
`research/2026-10-24-pv-generation/WEATHER-AND-MODELS.md`. The actual Berlin
sample contains GHI, DNI, DHI and healthy temperature, 10m wind and pressure;
hourly `seriescalc` plane beam must not be relabelled DNI.

The adapter verifies the official versioned request/capture, exact location,
requested year range/horizon, actual provider-selected databases, units, all
twelve selected month-years and each of the 8760 original hourly labels.
Duplicate fields, missing/extra/duplicated hours, altered source years,
unreported irradiance timing and wrong metadata fail intake.

A TMY is a stitched typical scenario, not one observed historical year. A named
non-leap synthetic energy axis is explicitly selected. Preserve the original
selected-year labels for solar geometry, adding the provider's exact reported
irradiance-time offset; do not substitute 1990, HH:00 or a universal 30 minutes.
Hold the representative modelled AC value over the corresponding synthetic
hour with an explicit reconstruction record and no energy-preservation claim.
No leap day, missing interval, wind-height conversion or alternate radiation
database is invented.

## Required evidence

Independently check actual-pose orientation/count, excluded slots, analytic
horizontal POA, SAPM's documented numeric example, PVWatts DC and inverter
examples, shared-converter clipping, loss accounting, source mismatch and
strict rejection. Use the newly acquired complete TMY to execute the complete
pure generation chain without live weather reads. Then connect its immutable
inputs/output to owned assets and the managed worker; UI/native delivery and
complete near-shading/electrical methods remain required by the full goal.

## Owned profile and durable energy integration

The trusted importer reads geometry and `pv_generation` parameters from one
explicit saved project revision. It checks ownership before parsing, computing
or publishing source/model bytes. Retain the original weather response, the
canonical complete model input and the detailed witness as permanent owned
dependencies; a browser cannot attest provider capture or model provenance.
An identical command retries against the first receipt even if the operational
resource policy changes. A new command must satisfy the current policy.

Selecting the derived profile is permitted only for `pv_available_ac`.
Preview exposes its modelled origin, reconstruction and exact interval/source
records. Neither selection nor preview grants equipment or country release.

At enqueue, compare the selected reference's geometry and parameter binding
against the exact saved inputs. Inspect the actual pinned input bundle too:
metadata hashes alone must not allow a different roof/model to be substituted.
A geometry or parameter edit makes that reference stale for a new calculation;
editing and saving must still work so the customer can update the design.
Changing load inputs alone does not invalidate the roof's available-AC model.

Pin raw weather, metadata, model input and witness hashes into the durable run.
The worker independently verifies those roles against the owned assets and
frozen revision, rebuilds the profile from the retained original and reproduces
the input/witness hashes before energy dispatch. It must not consult the latest
project, weather, product data or provider. A run queued before a roof edit
continues against its original snapshot; it becomes historical, not current.
Missing/tampered dependencies and unsupported model versions fail explicitly.

The profile-model identity advances to
`csv_pvgis_and_geometry_bound_pv_reference_v2`; an older worker cannot claim
to execute that identity. This backend increment adds no public intake route,
customer-visible source control or live runtime acceptance claim. Those native
workflow and managed-intake steps remain part of this same complete delivery.
