"""One immutable set of pinned numerical choices for execution and its witness.

Sources: NUMERICAL-MODELS.md §4.2; pinned pvlib 0.16.1 source fingerprints in
2026-10-24-pv-generation. These are model conventions, not equipment limits.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .canonical import Object


@dataclass(frozen=True)
class PvConventions:
    solar_position: str
    delta_t: str
    atmospheric_refraction_deg: float
    spa_numthreads: int
    extraterrestrial_radiation: str
    solar_constant_w_m2: float
    extraterrestrial_epoch_year: int
    relative_airmass: str
    perez_coefficients: str
    sapm_reference_irradiance_w_m2: float
    pvwatts_dc_reference_temperature_c: float
    pvwatts_dc_k: None
    pvwatts_optional_low_light_adjustment: bool
    zero_irradiance_policy: str

    def document(self) -> Object:
        return {**asdict(self)}


CONVENTIONS = PvConventions(
    solar_position="nrel_numpy",
    delta_t="spa_year_month",
    atmospheric_refraction_deg=0.5667,
    spa_numthreads=1,
    extraterrestrial_radiation="spencer",
    solar_constant_w_m2=1366.1,
    extraterrestrial_epoch_year=2014,
    relative_airmass="kastenyoung1989",
    perez_coefficients="allsitescomposite1990",
    sapm_reference_irradiance_w_m2=1000.0,
    pvwatts_dc_reference_temperature_c=25.0,
    pvwatts_dc_k=None,
    pvwatts_optional_low_light_adjustment=False,
    zero_irradiance_policy="zero_ghi_dni_dhi_implies_zero_poa_before_clearness_model_v1",
)
