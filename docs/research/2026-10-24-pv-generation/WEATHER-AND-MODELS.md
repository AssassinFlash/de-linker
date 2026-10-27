# PVGIS weather and pinned models for the detailed PV chain

2026-10-24. **Use the frozen PVGIS 5.3 TMY response for an explicitly typical-year scenario.** It supplies actual provider GHI, DNI, DHI, temperature and wind fields needed by pvlib 0.16.1. It does not establish a historical-weather-year route, measured generation, manufacturer suitability or engineering accuracy. JRC distinguishes hourly plane irradiance from TMY's horizontal/global, normal/direct and horizontal/diffuse variables; hourly horizontal `Gb(i)` must not be renamed DNI. [JRC manual §§9–10](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/pvgis-5-user-manual_en), [pinned pvlib variable map](../2026-10-23-pv-inputs/raw/pvlib-pvgis.py).

The one new complete weather asset is [the original JSON](raw/berlin-2005-2023-nohorizon.tmy.json): **1,268,118 bytes**, SHA-256 `5406a027f131e780d2a7a79a98d1f79b9e62c6ab7fe4b2f212a1829553321110`. Apify run `YgxlVDzJ8c1fh03tT` downloaded the official HTTP 200/application-json response; bytes were saved without reserialization. Full request, response inputs/meta, exact acquisition record and statistics are in [weather-provenance.json](raw/weather-provenance.json) and [validation](raw/weather-validation.json).

```text
https://re.jrc.ec.europa.eu/api/v5_3/tmy?lat=52.52&lon=13.405&startyear=2005&endyear=2023&usehorizon=0&outputformat=json
```

Actual echoes: Berlin `52.52/13.405`, elevation **37 m**, radiation **PVGIS-SARAH3**, meteorology **ERA5**, selection period **2005–2023**, horizon **false**, and `location.irradiance_time_offset=0.1838` hours. The documented TMY route chooses the location's default radiation database; neither its API table nor pvlib's TMY getter exposes an explicit radiation-database selector. This request therefore does **not** claim to select ERA5 radiation. Admit this asset against its actual expected SARAH3/ERA5 echoes and freeze them; a changed database is a changed input. The older coverage-year text on the format page is not evidence about this v5_3 response's available years. No independent backend build identifier is supplied. [JRC TMY generator](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/pvgis-5-tools/pvgis-typical-meteorological-year-tmy-generator_en), [API §2.6](../2026-10-23-pv-inputs/raw/official-api-doc.md).

All **8,760** rows have finite required values:

| Provider field → model field | Meaning/unit | Observed range |
| --- | --- | --- |
| `G(h)` → `ghi` | Global horizontal, W/m² | 0–911 |
| `Gb(n)` → `dni` | Beam on a plane normal to solar rays, W/m² | 0–934.67 |
| `Gd(h)` → `dhi` | Diffuse horizontal, W/m² | 0–434 |
| `T2m` → `temp_air` | Air at 2 m, °C | −14.87–36 |
| `WS10m` → `wind_speed` | Wind at 10 m, m/s | 0–8.41 |
| `SP` → `pressure` | Surface air pressure, Pa | 98,360–104,020 |

These meanings/heights/units come from the response metadata, not column-name inference. Temperature has 8,753 nonzero rows; wind has 8,759. Legitimate individual zero values remain zero. The existing Unknown-technology/all-zero-meteorology response is excluded, not repaired or reused. [Earlier anomaly evidence](../2026-10-23-pv-inputs/raw/unknown-output-capability.json).

**Keep the two time axes separate.** JRC says TMY selects representative months from different years. All actual source labels here are HH:00 UTC, unique but globally non-monotonic; no February 29 occurs. Preserve every original string and all twelve `months_selected` entries. JRC specifically directs applying the irradiance offset when calculating sun height: use the original selected-year label **plus exactly 661.68 seconds**, without rounding to 11 minutes or applying ERA5's generic 30-minute offset. Meteorological variables remain their hourly source conditions. [Freshly acquired official explanation](raw/official-tmy-format.md), [public primary page](https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/pvgis-5-tools/pvgis-typical-meteorological-year-tmy-generator_en).

The proposed declared reconstruction is consistent with those facts: evaluate solar geometry at those original radiation instants, then place the modelled AC value over the corresponding `[hour, hour+1h)` of an explicitly chosen non-leap synthetic UTC year. Preserve the source→synthetic mapping and both axis hashes. This interval-constant AC reconstruction is **our modelling policy**, not provider-measured interval-average AC or a historical-year forecast. pvlib's getter defaults to coercing years to 1990; use `coerce_year=None` when acquiring/parsing source identity, or the raw reader, before any explicit synthetic-axis mapping. [pvlib 0.16.1 parser/getter](https://github.com/pvlib/pvlib-python/blob/v0.16.1/pvlib/iotools/pvgis.py#L435).

A read-only diagnostic supports using the supplied offset: on rows with DNI >50 W/m², `GHI−DNI×cos(apparent_zenith)−DHI` RMS is 0.678 W/m² at that offset, versus 8.777 at HH:00 and 14.973 at +30 minutes. This is a clock-consistency diagnostic, not an accuracy tolerance or release criterion. Its inputs/policy are retained in the validation JSON.

The six installed pvlib modules match the previously Apify-acquired **v0.16.1 tag tree** byte-for-byte by Git blob hash; signatures and SHA-256 values are retained in [source verification](raw/pvlib-source-verification.json). Relevant contracts:

- Explicit `get_total_irradiance(..., model='perez', model_perez='allsitescomposite1990', dni_extra=..., airmass=..., albedo=...)`; default transposition is isotropic. Perez needs apparent zenith and relative, uncorrected-for-pressure airmass. [Source](https://github.com/pvlib/pvlib-python/blob/v0.16.1/pvlib/irradiance.py#L278).
- `sapm_cell(poa_global,temp_air,wind_speed,a,b,deltaT,irrad_ref=1000)` expects **10 m** wind. No height conversion is needed for this input/model pairing. Its thermal coefficients still require declared construction/mounting sources. [Source](https://github.com/pvlib/pvlib-python/blob/v0.16.1/pvlib/temperature.py#L57).
- `pvwatts_dc(effective_irradiance,temp_cell,pdc0,gamma_pdc,temp_ref=25,k=None,cap_adjustment=False)` returns W. Effective irradiance needs the declared optical/IAM treatment. [Source](https://github.com/pvlib/pvlib-python/blob/v0.16.1/pvlib/pvsystem.py#L3052).
- `inverter.pvwatts` uses inverter DC input limit `pdc0=Pac0/eta_inv_nom`, distinct from module reference DC nameplate. `pvwatts_multi` sums DC before one conversion curve; do not sum separately clipped outputs for a shared inverter. [Source](https://github.com/pvlib/pvlib-python/blob/v0.16.1/pvlib/inverter.py#L336).

JRC's retained usage conditions permit use without restrictions and retain their responsibility disclaimer; preserve PVGIS/database attribution and the actual acquisition provenance. [Primary terms](../2026-10-23-pv-inputs/raw/official-pvgis-usage-conditions.md). No accuracy or near-shading/electrical/manufacturer/country release follows from obtaining weather. A historical meteorological-year route still needs independent source evidence. Only one new full-year raw body is retained; previous hourly/manual/license evidence is reused by reference. The extra pinned tutorial probe used TMY3, so its different timing convention was excluded and only acquisition metadata retained. No application, dependency, build, service, database or browser was changed.
