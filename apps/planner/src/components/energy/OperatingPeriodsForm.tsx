import { __ } from "../../i18n.ts";
import { emptyPeriod, type PeriodDraft } from "../../domain/energyScenario.ts";
import { OperatingPeriodForm } from "./OperatingPeriodForm.tsx";
export function OperatingPeriodsForm({
	periods,
	onChange,
	locale,
	report,
	useProfileRange,
	rangeBusy,
	perUnitReserve = false,
}: {
	periods: readonly PeriodDraft[];
	onChange: (next: readonly PeriodDraft[]) => void;
	locale: string;
	report: (field: string, valid: boolean) => void;
	useProfileRange: () => void;
	rangeBusy: boolean;
	perUnitReserve?: boolean;
}) {
	return (
		<>
			<h3>{__("Operating periods", "linker-tools")}</h3>
			<p className="lp-profile-help">
				{__(
					"Periods must join without gaps or overlaps and stay within the source data. Timestamps include Z for UTC or an explicit offset, such as +01:00.",
					"linker-tools",
				)}
			</p>
			<button
				type="button"
				className="lp-button lp-button-secondary"
				disabled={rangeBusy}
				onClick={useProfileRange}
			>
				{rangeBusy
					? __("Checking profile coverage…", "linker-tools")
					: __("Use the shared profile range", "linker-tools")}
			</button>
			{periods.map((period, index) => (
				<OperatingPeriodForm
					key={period.id}
					period={period}
					perUnitReserve={perUnitReserve}
					index={index}
					locale={locale}
					report={report}
					onChange={(next) =>
						onChange(
							periods.map((item) => (item.id === period.id ? next : item)),
						)
					}
					remove={
						periods.length > 1
							? () => onChange(periods.filter((item) => item.id !== period.id))
							: undefined
					}
				/>
			))}
			<button
				type="button"
				className="lp-text-button"
				onClick={() =>
					onChange([
						...periods,
						{
							...emptyPeriod(),
							reserve_kwh: perUnitReserve ? 0 : null,
							start_utc: periods.at(-1)?.end_utc ?? "",
						},
					])
				}
			>
				{__("Add operating period", "linker-tools")}
			</button>
		</>
	);
}
