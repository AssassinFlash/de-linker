import { useCallback, useRef } from "react";
import type {
	ScenarioDraft,
	PeriodDraft,
} from "../../domain/energyScenario.ts";
import { __ } from "../../i18n.ts";
import { ScenarioNumber } from "./ScenarioNumber.tsx";
import { batteryPresentation } from "./batteryPresentation.ts";
import { fromPercent, toPercent } from "../../domain/decimal.ts";

/** A short editor over the same physical scenario used by the advanced form. */
export function SimpleEnergySetup({
	value,
	storageOnly,
	hasAuxiliaryProfile,
	locale,
	disabled,
	onChange,
	onValidity,
	useProfileRange,
	rangeBusy,
}: {
	value: ScenarioDraft;
	storageOnly: boolean;
	hasAuxiliaryProfile: boolean;
	locale: string;
	disabled: boolean;
	onChange: (value: ScenarioDraft) => void;
	onValidity: (valid: boolean) => void;
	useProfileRange: () => void;
	rangeBusy: boolean;
}) {
	const validity = useRef(new Map<string, boolean>());
	const report = useCallback(
		(key: string, valid: boolean) => {
			validity.current.set(key, valid);
			onValidity([...validity.current.values()].every(Boolean));
		},
		[onValidity],
	);
	const period = value.schedule[0]!;
	const purpose =
		period.mode === "outage"
			? "backup"
			: value.controller === "peak_shaving_with_reserve_v1"
				? "peak"
				: period.mode === "connected"
					? "self"
					: "";
	const patchPeriod = (
		patch: Partial<
			Pick<
				PeriodDraft,
				"start_utc" | "end_utc" | "import_cap_kw" | "allow_grid_charge"
			>
		>,
	) => onChange({ ...value, schedule: [{ ...period, ...patch }] });
	function choosePurpose(purpose: string) {
		if (!purpose) return;
		onChange({
			...value,
			controller:
				purpose === "peak"
					? "peak_shaving_with_reserve_v1"
					: "self_consumption_with_reserve_v1",
			aux_ac_kw: value.aux_ac_kw ?? (hasAuxiliaryProfile ? null : 0),
			battery: {
				...value.battery,
				internal_aux_kw: value.battery.internal_aux_kw ?? 0,
				standing_loss_rate_per_hour:
					value.battery.standing_loss_rate_per_hour ?? 0,
			},
			source_note:
				value.source_note ||
				__(
					"User-declared constant AC storage scenario; auxiliary and standing losses explicitly set to zero unless edited.",
					"linker-tools",
				),
			initial_inventory: {
				pv_kwh: value.initial_inventory.pv_kwh ?? 0,
				grid_kwh: value.initial_inventory.grid_kwh ?? 0,
				initial_unknown_kwh: value.initial_inventory.initial_unknown_kwh ?? 0,
				source_note:
					value.initial_inventory.source_note ||
					__("User-declared starting charge; source unknown.", "linker-tools"),
			},
			terminal_policy: value.terminal_policy ?? "none",
			schedule: [
				{
					...period,
					mode: purpose === "backup" ? "outage" : "connected",
					reserve_kwh: period.reserve_kwh ?? 0,
					import_policy:
						purpose === "peak"
							? "limited"
							: (period.import_policy ?? "unlimited"),
					export_policy: period.export_policy ?? "limited",
					export_cap_kw: period.export_cap_kw ?? 0,
					pv_enabled: !storageOnly && purpose !== "backup",
					allow_grid_charge:
						purpose === "backup" ? false : (period.allow_grid_charge ?? false),
				},
			],
		});
	}
	return (
		<fieldset disabled={disabled} className="lp-brief-fields">
			<h3>{__("Energy use and storage", "linker-tools")}</h3>
			{storageOnly && (
				<p>
					{__(
						"Storage-only project · no PV generation or roof required.",
						"linker-tools",
					)}
				</p>
			)}
			<label className="lp-field">
				<span>{__("Operating goal", "linker-tools")}</span>
				<select
					value={purpose}
					onChange={(e) => choosePurpose(e.currentTarget.value)}
				>
					<option value="">{__("Choose an option", "linker-tools")}</option>
					<option value="self">{__("Self-consumption", "linker-tools")}</option>
					<option value="backup">
						{__("Backup during an outage", "linker-tools")}
					</option>
					<option value="peak">
						{__("Peak shaving · separate AC storage", "linker-tools")}
					</option>
				</select>
			</label>
			<p>
				{__(
					"Enter known storage capacity, power and efficiencies. Annual consumption shapes the load profile; it does not determine battery size.",
					"linker-tools",
				)}
			</p>
			<div className="grid gap-5 md:grid-cols-2">
				{(
					[
						"usable_window_kwh",
						"charge_ac_kw",
						"discharge_ac_kw",
						"eta_charge",
						"eta_discharge",
					] as const
				).map((field) => {
					const p = batteryPresentation(field);
					return (
						<ScenarioNumber
							key={field}
							field={field}
							label={p.label}
							unit={p.unit}
							locale={locale}
							value={
								p.scale === 100
									? toPercent(value.battery[field])
									: value.battery[field]
							}
							{...(p.max === undefined ? {} : { max: p.max })}
							report={report}
							onChange={(number) =>
								onChange({
									...value,
									battery: {
										...value.battery,
										[field]: p.scale === 100 ? fromPercent(number) : number,
									},
									battery_binding: null,
								})
							}
						/>
					);
				})}
				<ScenarioNumber
					field="start"
					label={__("Starting stored energy", "linker-tools")}
					value={
						value.initial_inventory.initial_unknown_kwh === null
							? null
							: value.initial_inventory.initial_unknown_kwh +
								(value.initial_inventory.pv_kwh ?? 0) +
								(value.initial_inventory.grid_kwh ?? 0)
					}
					unit="kWh"
					locale={locale}
					report={report}
					onChange={(number) =>
						onChange({
							...value,
							initial_inventory: {
								pv_kwh: 0,
								grid_kwh: 0,
								initial_unknown_kwh: number,
								source_note: __(
									"User-declared starting charge; source unknown.",
									"linker-tools",
								),
							},
						})
					}
				/>
				{(!hasAuxiliaryProfile || value.aux_ac_kw != null) && (
					<ScenarioNumber
						field="aux"
						label={__("Constant AC auxiliary demand", "linker-tools")}
						value={value.aux_ac_kw ?? null}
						unit="kW"
						locale={locale}
						report={report}
						onChange={(aux_ac_kw) => onChange({ ...value, aux_ac_kw })}
					/>
				)}
				{purpose === "peak" && (
					<ScenarioNumber
						field="cap"
						label={__("Grid import cap", "linker-tools")}
						value={period.import_cap_kw}
						unit="kW"
						locale={locale}
						report={report}
						onChange={(import_cap_kw) => patchPeriod({ import_cap_kw })}
					/>
				)}
			</div>
			{purpose === "peak" && (
				<label className="lp-field">
					<span>
						<input
							type="checkbox"
							checked={period.allow_grid_charge === true}
							onChange={(e) =>
								patchPeriod({ allow_grid_charge: e.currentTarget.checked })
							}
						/>{" "}
						{__("Allow grid charging below this cap", "linker-tools")}
					</span>
				</label>
			)}
			{purpose === "backup" && (
				<p>
					{__(
						"Select a critical-load profile in Energy use, then set the outage start and end below. PV is off in this backup setup; advanced settings can enable a documented backup PV supply. The calculation reports any unmet demand.",
						"linker-tools",
					)}
				</p>
			)}
			{storageOnly && purpose === "self" && (
				<p>
					{__(
						"Without PV, this mode uses only the starting charge. Choose peak shaving to recharge from the grid below a defined cap.",
						"linker-tools",
					)}
				</p>
			)}
			<div className="grid gap-5 md:grid-cols-2">
				<label className="lp-field">
					<span>{__("Calculation start · UTC or offset", "linker-tools")}</span>
					<input
						value={period.start_utc}
						onChange={(e) => patchPeriod({ start_utc: e.currentTarget.value })}
					/>
				</label>
				<label className="lp-field">
					<span>{__("Calculation end · UTC or offset", "linker-tools")}</span>
					<input
						value={period.end_utc}
						onChange={(e) => patchPeriod({ end_utc: e.currentTarget.value })}
					/>
				</label>
			</div>
			<button
				type="button"
				className="lp-text-button"
				disabled={rangeBusy}
				onClick={useProfileRange}
			>
				{__("Use selected profile dates", "linker-tools")}
			</button>
			<p>
				{__(
					"The simple setup starts with no reserve, no grid export and no auxiliary or standing losses unless entered. Review starting charge, source notes and loss assumptions in advanced settings.",
					"linker-tools",
				)}
			</p>
		</fieldset>
	);
}
