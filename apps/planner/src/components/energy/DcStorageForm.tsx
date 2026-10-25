import type { PlannerClient } from "../../data/PlannerClient.ts";
import { useEquipmentProducts } from "../../data/equipmentProducts.ts";
import type { ScenarioDraft } from "../../domain/energyScenario.ts";
import { DC_LOSS_FIELDS, emptyDcScenario } from "../../domain/dcEnergy.ts";
import type { DcLossField } from "../../domain/dcEnergy.ts";
import { __ } from "../../i18n.ts";
import { toPercent, fromPercent } from "../../domain/decimal.ts";
import { ScenarioNumber } from "./ScenarioNumber.tsx";
import { Notice } from "../Notice.tsx";

export function dcLossLabel(field: DcLossField): string {
	switch (field) {
		case "eta_bus_to_battery":
			return __("DC converter: charging efficiency", "linker-tools");
		case "eta_battery_to_bus":
			return __("DC converter: discharging efficiency", "linker-tools");
		case "eta_store_charge":
			return __("Storage: charging efficiency", "linker-tools");
		case "eta_store_discharge":
			return __("Storage: discharging efficiency", "linker-tools");
		case "eta_inverter_forward":
			return __("Inverter: DC to AC efficiency", "linker-tools");
		case "eta_inverter_reverse":
			return __("Inverter: AC to DC efficiency", "linker-tools");
		case "internal_aux_kw":
			return __("Internal auxiliary power", "linker-tools");
		case "standing_loss_rate_per_hour":
			return __("Standing-loss coefficient", "linker-tools");
	}
}

export function DcStorageForm({
	value,
	locale,
	onChange,
	report,
	converters,
	equipmentSelected,
	openEquipment,
	client,
	scope,
	active,
	inverterId,
}: {
	value: ScenarioDraft;
	locale: string;
	onChange: (next: ScenarioDraft) => void;
	report: (field: string, valid: boolean) => void;
	converters: readonly string[];
	equipmentSelected: boolean;
	openEquipment: () => void;
	client: PlannerClient;
	scope: string;
	active: boolean;
	inverterId: number | null;
}) {
	const dc = value.dc ?? emptyDcScenario();
	const catalog = useEquipmentProducts(client, scope, active);
	const ports =
		inverterId === null ? undefined : catalog.data?.dcPorts[String(inverterId)];
	const portsReady =
		inverterId !== null &&
		!!catalog.data?.prepared &&
		!catalog.error &&
		!catalog.isFetching;
	const change = (
		patch: Partial<
			Pick<
				typeof dc,
				| "source_note"
				| "pv_converter_id"
				| "battery_port_id"
				| "battery_temperature_c"
				| "aux_dc_kw"
				| "losses"
			>
		>,
	) => onChange({ ...value, dc: { ...dc, ...patch }, battery_binding: null });
	return (
		<section className="lp-scenario-block">
			<h3>{__("Shared inverter and battery", "linker-tools")}</h3>
			<p className="lp-profile-help">
				{__(
					"The saved product selection supplies battery capacity, voltage, current and equipment power limits where documented. Losses and auxiliary consumption remain separate calculation assumptions.",
					"linker-tools",
				)}
			</p>
			<button type="button" className="lp-text-button" onClick={openEquipment}>
				{equipmentSelected
					? __("Review equipment selection", "linker-tools")
					: __("Select equipment", "linker-tools")}
			</button>
			{catalog.error && (
				<Notice error>
					{__("Product data could not be loaded.", "linker-tools")}
				</Notice>
			)}
			{(catalog.isFetching || !catalog.data?.prepared) && (
				<p role="status">
					{__("Current product data is being prepared.", "linker-tools")}
				</p>
			)}
			<div className="lp-geometry-fields">
				<label className="lp-field">
					<span>{__("PV conversion group", "linker-tools")}</span>
					<input
						value={dc.pv_converter_id}
						list="lp-dc-converters"
						onChange={(e) => change({ pv_converter_id: e.currentTarget.value })}
					/>
					<datalist id="lp-dc-converters">
						{converters.map((id) => (
							<option key={id} value={id} />
						))}
					</datalist>
				</label>
				{ports !== undefined ? (
					<label className="lp-field">
						<span>{__("Connected battery port", "linker-tools")}</span>
						<select
							value={dc.battery_port_id}
							onChange={(e) =>
								change({ battery_port_id: e.currentTarget.value })
							}
							disabled={!portsReady}
						>
							<option value="">{__("Choose an option", "linker-tools")}</option>
							{dc.battery_port_id && !ports.includes(dc.battery_port_id) && (
								<option value={dc.battery_port_id} disabled>
									{dc.battery_port_id}
								</option>
							)}
							{ports.map((id) => (
								<option key={id} value={id}>
									{id}
								</option>
							))}
						</select>
					</label>
				) : portsReady ? (
					<ScenarioNumber
						field="dc-port"
						label={__("Connected battery port", "linker-tools")}
						value={
							/^battery-[1-9][0-9]*$/.test(dc.battery_port_id)
								? Number(dc.battery_port_id.slice(8))
								: null
						}
						unit=""
						locale={locale}
						report={report}
						min={1}
						integer
						onChange={(n) =>
							change({ battery_port_id: n === null ? "" : `battery-${n}` })
						}
					/>
				) : (
					<label className="lp-field">
						<span>{__("Connected battery port", "linker-tools")}</span>
						<input disabled readOnly value="" />
					</label>
				)}
				<ScenarioNumber
					field="dc-temperature"
					label={__("Battery temperature for this scenario", "linker-tools")}
					value={dc.battery_temperature_c ?? null}
					unit="°C"
					locale={locale}
					report={report}
					min={null}
					onChange={(n) => change({ battery_temperature_c: n })}
				/>

				<ScenarioNumber
					field="dc-aux"
					label={__("Auxiliary demand on the DC bus", "linker-tools")}
					value={dc.aux_dc_kw}
					unit="kW"
					locale={locale}
					report={report}
					onChange={(n) => change({ aux_dc_kw: n })}
				/>
			</div>
			<p className="lp-profile-help">
				{__(
					"The selected PV source must retain DC power for this conversion group. A CSV containing AC generation cannot supply this input. The battery port is checked against the selected inverter.",
					"linker-tools",
				)}
			</p>
			<p className="lp-profile-help">
				{__(
					"Battery temperature is a fixed scenario condition used to check the documented charging and discharging temperature ranges. It is not inferred from outdoor weather. This model uses fixed loss assumptions and does not simulate temperature changes.",
					"linker-tools",
				)}
			</p>

			<h4>{__("Loss assumptions", "linker-tools")}</h4>
			<p className="lp-profile-help">
				{__(
					"Efficiencies apply separately to the DC converter, stored energy and inverter. A reverse-efficiency assumption is required to calculate grid charging. Zero auxiliary demand or standing loss is an explicit assumption.",
					"linker-tools",
				)}
			</p>
			<div className="lp-geometry-fields">
				{DC_LOSS_FIELDS.map((field) => {
					const efficiency = field.startsWith("eta_");
					return (
						<ScenarioNumber
							key={field}
							field={`dc-${field}`}
							label={dcLossLabel(field)}
							value={
								efficiency ? toPercent(dc.losses[field]) : dc.losses[field]
							}
							unit={
								efficiency ? "%" : field === "internal_aux_kw" ? "kW" : "1/h"
							}
							{...(efficiency ? { max: 100 } : {})}
							locale={locale}
							report={report}
							onChange={(n) =>
								change({
									losses: {
										...dc.losses,
										[field]: efficiency ? fromPercent(n) : n,
									},
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
					rows={2}
					value={dc.source_note}
					onChange={(e) => change({ source_note: e.currentTarget.value })}
				/>
			</label>
		</section>
	);
}
