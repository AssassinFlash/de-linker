import type { PlannerClient } from "../../data/PlannerClient.ts";
import { useCallback, useRef } from "react";
import type { ScenarioDraft } from "../../domain/energyScenario.ts";
import { BATTERY_FIELDS, emptyPeriod } from "../../domain/energyScenario.ts";
import { __ } from "../../i18n.ts";
import { ScenarioNumber } from "./ScenarioNumber.tsx";
import { toPercent, fromPercent } from "../../domain/decimal.ts";
import { OperatingPeriodForm } from "./OperatingPeriodForm.tsx";
import { batteryPresentation } from "./batteryPresentation.ts";
import { DcStorageForm } from "./DcStorageForm.tsx";
import { emptyDcScenario } from "../../domain/dcEnergy.ts";
import type { JsonObject } from "../../data/protocol.ts";

export function ScenarioForm({
	value,
	locale,
	disabled,
	onChange,
	onValidity,
	useProfileRange,
	rangeBusy,
	section,
	equipmentSelection,
	converters,
	openEquipment,
	client,
	scope,
	active,
}: {
	value: ScenarioDraft;
	locale: string;
	disabled: boolean;
	onChange: (next: ScenarioDraft) => void;
	onValidity: (valid: boolean) => void;
	useProfileRange: () => void;
	rangeBusy: boolean;
	section: "storage" | "initial" | "operation";
	equipmentSelection: JsonObject | null;
	converters: readonly string[];
	openEquipment: () => void;
	client: PlannerClient;
	scope: string;
	active: boolean;
}) {
	const validity = useRef(new Map<string, boolean>());
	const report = useCallback(
		(field: string, valid: boolean) => {
			if (validity.current.get(field) === valid) return;
			validity.current.set(field, valid);
			onValidity([...validity.current.values()].every(Boolean));
		},
		[onValidity],
	);
	const inventory = value.initial_inventory;
	const dc = value.coupling === "shared_dc";
	return (
		<fieldset className="lp-scenario-fields" disabled={disabled}>
			<div hidden={section !== "storage"}>
				<label className="lp-field">
					<span>{__("System connection", "linker-tools")}</span>
					<select
						value={value.coupling ?? "independent_ac"}
						onChange={(e) =>
							onChange({
								...value,
								coupling: e.currentTarget.value as
									"shared_dc" | "independent_ac",
								dc: value.dc ?? emptyDcScenario(),
								battery_binding: null,
							})
						}
					>
						<option value="independent_ac">
							{__("Separate AC connections", "linker-tools")}
						</option>
						<option value="shared_dc">
							{__("PV and battery share an inverter", "linker-tools")}
						</option>
					</select>
				</label>
				{dc && (
					<DcStorageForm
						client={client}
						scope={scope}
						active={active && section === "storage"}
						inverterId={
							typeof equipmentSelection?.inverter_product_id === "number"
								? equipmentSelection.inverter_product_id
								: null
						}
						value={value}
						locale={locale}
						onChange={onChange}
						report={report}
						equipmentSelected={equipmentSelection !== null}
						converters={converters}
						openEquipment={openEquipment}
					/>
				)}
			</div>
			<section
				className="lp-scenario-block"
				hidden={section !== "storage" || dc}
			>
				<h3>{__("Storage parameters", "linker-tools")}</h3>
				<p className="lp-profile-help">
					{__(
						"These values define a storage scenario at one AC connection. This calculation does not assess product suitability.",
						"linker-tools",
					)}
				</p>
				<div className="lp-geometry-fields">
					{BATTERY_FIELDS.map((field) => {
						const presentation = batteryPresentation(field),
							number = value.battery[field];
						return (
							<ScenarioNumber
								key={field}
								field={field}
								label={presentation.label}
								unit={presentation.unit}
								locale={locale}
								value={presentation.scale === 100 ? toPercent(number) : number}
								{...(presentation.max === undefined
									? {}
									: { max: presentation.max })}
								report={report}
								onChange={(number) =>
									onChange({
										...value,
										battery: {
											...value.battery,
											[field]:
												presentation.scale === 100
													? fromPercent(number)
													: number,
										},
										battery_binding: null,
									})
								}
							/>
						);
					})}
				</div>
				<label className="lp-field">
					<span>
						{__("Source or assumption for storage parameters", "linker-tools")}
					</span>
					<textarea
						value={value.source_note}
						rows={2}
						onChange={(e) =>
							onChange({
								...value,
								source_note: e.currentTarget.value,
								battery_binding: null,
							})
						}
					/>
				</label>
				<details className="lp-comparison">
					<summary>{__("Storage model and units", "linker-tools")}</summary>
					<p>
						{__(
							"Usable stored energy is the model's internal energy window. Charging and discharging power are measured at the AC connection. The two efficiencies describe their separate conversion directions.",
							"linker-tools",
						)}
					</p>
					<p>
						{__(
							"Internal auxiliary power is drawn from stored energy. Separate AC auxiliary demand comes from its interval profile. Standing loss uses E × (1 − exp(−r × hours)), with r in 1/h. Zero losses are explicit scenario assumptions.",
							"linker-tools",
						)}
					</p>
					<p>
						{__(
							"This model uses fixed capacity, power and efficiency. Temperature effects, ageing, shared DC ports, phase limits and switching behaviour require their own assessment.",
							"linker-tools",
						)}
					</p>
				</details>
			</section>
			<section className="lp-scenario-block" hidden={section !== "initial"}>
				<h3>{__("Initial stored energy", "linker-tools")}</h3>
				<p className="lp-profile-help">
					{__(
						"Stored energy keeps its origin throughout the calculation. Energy from the grid or an unknown source is excluded from the solar-supplied total.",
						"linker-tools",
					)}
				</p>
				<div className="lp-geometry-fields">
					{(["pv_kwh", "grid_kwh", "initial_unknown_kwh"] as const).map(
						(field) => (
							<ScenarioNumber
								key={field}
								field={"initial-" + field}
								label={
									field === "pv_kwh"
										? __("From PV", "linker-tools")
										: field === "grid_kwh"
											? __("From the grid", "linker-tools")
											: __("Origin unknown", "linker-tools")
								}
								value={inventory[field]}
								unit="kWh"
								locale={locale}
								report={report}
								onChange={(number) =>
									onChange({
										...value,
										initial_inventory: { ...inventory, [field]: number },
									})
								}
							/>
						),
					)}
				</div>
				<button
					type="button"
					className="lp-text-button"
					onClick={() =>
						onChange({
							...value,
							initial_inventory: {
								pv_kwh: 0,
								grid_kwh: 0,
								initial_unknown_kwh: 0,
								source_note: __(
									"Empty stored-energy inventory selected for the start of this scenario.",
									"linker-tools",
								),
							},
						})
					}
				>
					{__("Start with an empty battery", "linker-tools")}
				</button>
				<label className="lp-field">
					<span>{__("Basis for the initial state", "linker-tools")}</span>
					<textarea
						rows={2}
						value={inventory.source_note}
						onChange={(e) =>
							onChange({
								...value,
								initial_inventory: {
									...inventory,
									source_note: e.currentTarget.value,
								},
							})
						}
					/>
				</label>
			</section>
			<section className="lp-scenario-block" hidden={section !== "operation"}>
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
				{value.schedule.map((period, index) => (
					<OperatingPeriodForm
						key={period.id}
						period={period}
						index={index}
						locale={locale}
						report={report}
						onChange={(next) =>
							onChange({
								...value,
								schedule: value.schedule.map((item) =>
									item.id === period.id ? next : item,
								),
							})
						}
						remove={
							value.schedule.length > 1
								? () =>
										onChange({
											...value,
											schedule: value.schedule.filter(
												(item) => item.id !== period.id,
											),
										})
								: undefined
						}
					/>
				))}
				<button
					type="button"
					className="lp-text-button"
					onClick={() =>
						onChange({
							...value,
							schedule: [
								...value.schedule,
								{
									...emptyPeriod(),
									start_utc: value.schedule.at(-1)?.end_utc ?? "",
								},
							],
						})
					}
				>
					{__("Add operating period", "linker-tools")}
				</button>
				<label className="lp-field">
					<span>
						{__("Stored energy at the end of the calculation", "linker-tools")}
					</span>
					<select
						value={value.terminal_policy ?? ""}
						onChange={(e) =>
							onChange({
								...value,
								terminal_policy: (e.currentTarget.value ||
									null) as ScenarioDraft["terminal_policy"],
							})
						}
					>
						<option value="">{__("Choose an option", "linker-tools")}</option>
						<option value="none">
							{__("No minimum required", "linker-tools")}
						</option>
						<option value="minimum">
							{__("Specify a minimum", "linker-tools")}
						</option>
					</select>
				</label>
				{value.terminal_policy === "minimum" && (
					<ScenarioNumber
						field="terminal"
						label={__("Minimum final stored energy", "linker-tools")}
						value={value.terminal_min_kwh}
						unit="kWh"
						locale={locale}
						report={report}
						onChange={(number) =>
							onChange({ ...value, terminal_min_kwh: number })
						}
					/>
				)}
				<details className="lp-comparison">
					<summary>{__("How storage is operated", "linker-tools")}</summary>
					<p>
						{dc
							? __(
									"The DC bus supplies auxiliary demand first. PV and battery share the inverter power limit when serving AC demand. Surplus PV can charge the battery before inverter clipping; remaining PV is exported within the grid limit, then curtailed. Grid charging requires documented equipment support and a separate reverse-efficiency assumption.",
									"linker-tools",
								)
							: __(
									"PV supplies the simulated load and AC auxiliary demand first. Surplus PV charges the battery within the specified power and energy limits. The battery supplies remaining demand using stored energy above the reserve. When connected, the grid supplies any remaining demand within the import limit. This controller does not request grid charging. Remaining PV is exported within the export limit, then curtailed.",
									"linker-tools",
								)}
					</p>
					<p>
						{__(
							"Stored energy continues across every period. The model excludes battery export and does not reset the battery at midnight or at the start of an outage.",
							"linker-tools",
						)}
					</p>
				</details>
			</section>
		</fieldset>
	);
}
