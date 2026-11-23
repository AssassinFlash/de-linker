import { decimalSeparator } from "../domain/decimal.ts";
import type { PanelElectrical } from "../domain/geometry.ts";
import type { PanelFields } from "../domain/panelParameters.ts";
import { __ } from "../i18n.ts";

export function PanelMeasurementFields({
	locale,
	fields,
	change,
}: {
	locale: string;
	fields: PanelFields;
	change: (next: PanelFields) => void;
}) {
	const separator = decimalSeparator(locale);
	function field(
		key: Exclude<keyof PanelFields, "electrical">,
		name: string,
		label: string,
		unit: string,
	) {
		return (
			<label className="sc-field">
				<span>
					{label} ({unit})
				</span>
				<input
					type="text"
					inputMode="decimal"
					name={name}
					value={fields[key].replace(".", separator)}
					onChange={(e) =>
						change({
							...fields,
							[key]: e.currentTarget.value.replace(separator, "."),
						})
					}
				/>
			</label>
		);
	}
	function electrical(
		key: Exclude<keyof PanelElectrical, "cell_technology">,
		label: string,
		unit = "",
	) {
		return (
			<label className="sc-field">
				<span>
					{label}
					{unit && " (" + unit + ")"}
				</span>
				<input
					type="text"
					inputMode="decimal"
					name={"panel_" + key}
					value={(fields.electrical?.[key] ?? "").replace(".", separator)}
					onChange={(e) =>
						change({
							...fields,
							electrical: {
								...fields.electrical,
								[key]: e.currentTarget.value.replace(separator, "."),
							},
						})
					}
				/>
			</label>
		);
	}
	return (
		<div className="sc-panel-measurements">
			<p className="sc-muted">
				{__(
					"Use the dimensions and rated power on your panel data sheet. Thickness is used for the 3D layout.",
					"linker-tools",
				)}
			</p>
			<div className="sc-fields">
				{field(
					"length",
					"panel_length_mm",
					__("Panel length", "linker-tools"),
					"mm",
				)}
				{field(
					"width",
					"panel_width_mm",
					__("Panel width", "linker-tools"),
					"mm",
				)}
				{field(
					"thickness",
					"panel_thickness_mm",
					__("Panel thickness", "linker-tools"),
					"mm",
				)}
				{field(
					"power",
					"panel_power_w",
					__("Power per panel", "linker-tools"),
					"Wp",
				)}
			</div>
			<details>
				<summary>
					{__(
						"Panel data for electrical and energy checks (optional)",
						"linker-tools",
					)}
				</summary>
				{field(
					"coefficient",
					"panel_temperature_coefficient",
					__("Temperature coefficient of maximum power", "linker-tools"),
					"%/°C",
				)}
				{electrical(
					"voc_v",
					__("Open-circuit voltage at STC", "linker-tools"),
					"V",
				)}
				{electrical("vmpp_v", __("MPP voltage at STC", "linker-tools"), "V")}
				{electrical(
					"isc_a",
					__("Short-circuit current at STC", "linker-tools"),
					"A",
				)}
				{electrical("impp_a", __("MPP current at STC", "linker-tools"), "A")}
				{electrical(
					"max_system_voltage_v",
					__("Maximum system voltage", "linker-tools"),
					"V",
				)}
				{electrical(
					"alpha_isc_pct_per_c",
					__(
						"Temperature coefficient of short-circuit current",
						"linker-tools",
					),
					"%/°C",
				)}
				{electrical(
					"beta_voc_pct_per_c",
					__("Temperature coefficient of open-circuit voltage", "linker-tools"),
					"%/°C",
				)}
				<label className="sc-field">
					<span>{__("Cell technology", "linker-tools")}</span>
					<select
						name="panel_cell_technology"
						value={fields.electrical?.cell_technology ?? ""}
						onChange={(event) =>
							change({
								...fields,
								electrical: {
									...fields.electrical,
									cell_technology: event.currentTarget.value,
								},
							})
						}
					>
						<option value="">{__("Unknown", "linker-tools")}</option>
						<option value="monocrystalline">
							{__("Monocrystalline silicon", "linker-tools")}
						</option>
						<option value="polycrystalline">
							{__("Polycrystalline silicon", "linker-tools")}
						</option>
					</select>
				</label>
			</details>
		</div>
	);
}
