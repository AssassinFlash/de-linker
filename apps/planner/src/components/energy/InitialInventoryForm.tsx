import type { ScenarioDraft } from "../../domain/energyScenario.ts";
import { __ } from "../../i18n.ts";
import { ScenarioNumber } from "./ScenarioNumber.tsx";

export function InitialInventoryForm({
	value: inventory,
	onChange,
	locale,
	report,
}: {
	value: ScenarioDraft["initial_inventory"];
	onChange: (next: ScenarioDraft["initial_inventory"]) => void;
	locale: string;
	report: (field: string, valid: boolean) => void;
}) {
	return (
		<section className="lp-scenario-block">
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
							onChange={(number) => onChange({ ...inventory, [field]: number })}
						/>
					),
				)}
			</div>
			<button
				type="button"
				className="lp-text-button"
				onClick={() =>
					onChange({
						pv_kwh: 0,
						grid_kwh: 0,
						initial_unknown_kwh: 0,
						source_note: __(
							"Empty stored-energy inventory selected for the start of this scenario.",
							"linker-tools",
						),
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
						onChange({ ...inventory, source_note: e.currentTarget.value })
					}
				/>
			</label>
		</section>
	);
}
