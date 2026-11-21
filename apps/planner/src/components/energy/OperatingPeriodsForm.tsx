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
	hasStorage = true,
	inputPath,
	inputErrors,
}: {
	periods: readonly PeriodDraft[];
	onChange: (next: readonly PeriodDraft[]) => void;
	locale: string;
	report: (field: string, valid: boolean) => void;
	useProfileRange: () => void;
	rangeBusy: boolean;
	perUnitReserve?: boolean;
	hasStorage?: boolean;
	inputPath?: string | undefined;
	inputErrors?: readonly string[] | undefined;
}) {
	return (
		<section className="sc-work-panel">
			<div className="sc-work-panel-heading">
				<h3>{__("Operating periods", "linker-tools")}</h3>
				<p className="sc-field-help">
					{__(
						"Periods must join without gaps or overlaps and stay within the source data. Timestamps include Z for UTC or an explicit offset, such as +01:00.",
						"linker-tools",
					)}
				</p>
				<button
					type="button"
					className="sc-button"
					disabled={rangeBusy}
					onClick={useProfileRange}
				>
					{rangeBusy
						? __("Checking profile coverage…", "linker-tools")
						: __("Use the shared profile range", "linker-tools")}
				</button>
			</div>
			{periods.map((period, index) => (
				<OperatingPeriodForm
					key={period.id}
					period={period}
					inputPath={inputPath}
					inputErrors={inputErrors}
					perUnitReserve={perUnitReserve}
					hasStorage={hasStorage}
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
				className="sc-text-button"
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
		</section>
	);
}
