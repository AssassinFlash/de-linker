import { useId } from "react";
import type { PeriodDraft } from "../../domain/energyScenario.ts";
import { __, sprintf } from "../../i18n.ts";
import { ScenarioNumber } from "./ScenarioNumber.tsx";

export function OperatingPeriodForm({
	period,
	index,
	locale,
	onChange,
	remove,
	report,
	perUnitReserve = false,
	hasStorage = true,
	inputPath = "energy_scenario.schedule",
	inputErrors = [],
}: {
	period: PeriodDraft;
	index: number;
	locale: string;
	onChange: (next: PeriodDraft) => void;
	remove: (() => void) | undefined;
	report: (field: string, valid: boolean) => void;
	perUnitReserve?: boolean;
	hasStorage?: boolean;
	inputPath?: string | undefined;
	inputErrors?: readonly string[] | undefined;
}) {
	const errorId = useId(),
		startPath = `${inputPath}[${index}].start_utc`,
		endPath = `${inputPath}[${index}].end_utc`,
		startError = inputErrors.includes(startPath),
		endError = inputErrors.includes(endPath),
		dateError = __(
			"Enter a date and time with Z or a UTC offset. The end must be after the start.",
			"linker-tools",
		);
	const field = "period-" + period.id;
	function patch(
		values: Partial<
			Pick<
				PeriodDraft,
				| "start_utc"
				| "end_utc"
				| "mode"
				| "reserve_kwh"
				| "import_policy"
				| "import_cap_kw"
				| "export_policy"
				| "export_cap_kw"
				| "pv_enabled"
				| "allow_grid_charge"
			>
		>,
	) {
		onChange({ ...period, ...values });
	}
	return (
		<fieldset className="sc-scenario-period">
			<legend>
				{sprintf(__("Operating period %d", "linker-tools"), index + 1)}
			</legend>
			<div className="sc-geometry-fields">
				<label className="sc-field">
					<span>{__("Start with UTC or offset", "linker-tools")}</span>
					<input
						type="text"
						value={period.start_utc}
						name={startPath}
						aria-invalid={startError}
						aria-describedby={startError ? errorId + "-start" : undefined}
						placeholder="2024-03-30T23:00:00Z"
						onChange={(e) => patch({ start_utc: e.currentTarget.value })}
					/>
					{startError && (
						<small className="sc-field-error" id={errorId + "-start"}>
							{dateError}
						</small>
					)}
				</label>
				<label className="sc-field">
					<span>{__("End with UTC or offset", "linker-tools")}</span>
					<input
						type="text"
						value={period.end_utc}
						name={endPath}
						aria-invalid={endError}
						aria-describedby={endError ? errorId + "-end" : undefined}
						placeholder="2024-03-31T01:00:00Z"
						onChange={(e) => patch({ end_utc: e.currentTarget.value })}
					/>
					{endError && (
						<small className="sc-field-error" id={errorId + "-end"}>
							{dateError}
						</small>
					)}
				</label>
				<label className="sc-field">
					<span>{__("Grid condition", "linker-tools")}</span>
					<select
						value={period.mode ?? ""}
						onChange={(e) => {
							const mode = e.currentTarget.value as PeriodDraft["mode"] | "";
							patch({
								mode: mode || null,
								...(mode === "outage" ? { allow_grid_charge: false } : {}),
							});
						}}
					>
						<option value="">{__("Choose an option", "linker-tools")}</option>
						<option value="connected">
							{__("Grid connected", "linker-tools")}
						</option>
						<option value="outage">{__("Grid outage", "linker-tools")}</option>
					</select>
				</label>
				{hasStorage && !perUnitReserve && (
					<ScenarioNumber
						field={field + "-reserve"}
						label={__("Reserved stored energy", "linker-tools")}
						value={period.reserve_kwh}
						unit="kWh"
						locale={locale}
						report={report}
						onChange={(value) => patch({ reserve_kwh: value })}
					/>
				)}
				<label className="sc-field">
					<span>{__("PV available in this period", "linker-tools")}</span>
					<select
						value={period.pv_enabled === null ? "" : String(period.pv_enabled)}
						onChange={(e) =>
							patch({
								pv_enabled:
									e.currentTarget.value === ""
										? null
										: e.currentTarget.value === "true",
							})
						}
					>
						<option value="">{__("Choose an option", "linker-tools")}</option>
						<option value="true">{__("Available", "linker-tools")}</option>
						<option value="false">{__("Unavailable", "linker-tools")}</option>
					</select>
				</label>
				{hasStorage && period.mode !== "outage" && (
					<label className="sc-field">
						<span>{__("Grid charging allowed", "linker-tools")}</span>
						<select
							value={
								period.allow_grid_charge === null
									? ""
									: String(period.allow_grid_charge)
							}
							onChange={(e) =>
								patch({
									allow_grid_charge:
										e.currentTarget.value === ""
											? null
											: e.currentTarget.value === "true",
								})
							}
						>
							<option value="">{__("Choose an option", "linker-tools")}</option>
							<option value="true">{__("Allowed", "linker-tools")}</option>
							<option value="false">{__("Not allowed", "linker-tools")}</option>
						</select>
					</label>
				)}
				{period.mode !== "outage" && (
					<>
						<label className="sc-field">
							<span>{__("Grid import limit", "linker-tools")}</span>
							<select
								value={period.import_policy ?? ""}
								onChange={(e) =>
									patch({
										import_policy: (e.currentTarget.value ||
											null) as PeriodDraft["import_policy"],
									})
								}
							>
								<option value="">
									{__("Choose an option", "linker-tools")}
								</option>
								<option value="unlimited">
									{__("No cap in this scenario", "linker-tools")}
								</option>
								<option value="limited">
									{__("Specified cap", "linker-tools")}
								</option>
							</select>
						</label>
						{period.import_policy === "limited" && (
							<ScenarioNumber
								field={field + "-import"}
								label={__("Import cap", "linker-tools")}
								unit="kW"
								locale={locale}
								value={period.import_cap_kw}
								report={report}
								onChange={(value) => patch({ import_cap_kw: value })}
							/>
						)}
						<label className="sc-field">
							<span>{__("Grid export limit", "linker-tools")}</span>
							<select
								value={period.export_policy ?? ""}
								onChange={(e) =>
									patch({
										export_policy: (e.currentTarget.value ||
											null) as PeriodDraft["export_policy"],
									})
								}
							>
								<option value="">
									{__("Choose an option", "linker-tools")}
								</option>
								<option value="unlimited">
									{__("No cap in this scenario", "linker-tools")}
								</option>
								<option value="limited">
									{__("Specified cap", "linker-tools")}
								</option>
							</select>
						</label>
						{period.export_policy === "limited" && (
							<ScenarioNumber
								field={field + "-export"}
								label={__("Export cap", "linker-tools")}
								unit="kW"
								locale={locale}
								value={period.export_cap_kw}
								report={report}
								onChange={(value) => patch({ export_cap_kw: value })}
							/>
						)}
					</>
				)}
			</div>
			{period.mode === "outage" && (
				<p className="sc-field-help">
					{__(
						"During an outage, grid import, export and charging are zero. A critical-load profile and an explicit PV availability choice are required.",
						"linker-tools",
					)}
				</p>
			)}
			{remove && (
				<button type="button" className="sc-text-button" onClick={remove}>
					{__("Remove operating period", "linker-tools")}
				</button>
			)}
		</fieldset>
	);
}
