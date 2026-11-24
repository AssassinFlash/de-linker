"""Monthly energy series shared by the project view and its printed proposal."""

from linker_engine.models import ReportMonthlyChart


def monthly_chart(
    locale: str, pv: list[float], load: list[float] | None, source: str
) -> ReportMonthlyChart | None:
    if len(pv) != 12 or not any(pv):
        return None
    de = locale == "de"
    return ReportMonthlyChart(
        title="Monatliche Energiebilanz" if de else "Monthly energy profile",
        unit="kWh",
        months=(
            "Jan Feb Mär Apr Mai Jun Jul Aug Sep Okt Nov Dez"
            if de
            else "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec"
        ).split(),
        pv_kwh=pv,
        load_kwh=load,
        source_note=source,
    )
