import type { JsonObject } from "../../data/protocol.ts";
import { readObject } from "../../data/readProtocol.ts";
import { __ } from "../../i18n.ts";

export function PlantStorageSummary({
	result,
	locale,
}: {
	result: JsonObject;
	locale: string;
}) {
	const plant = readObject(readObject(result.equipment_binding).plant),
		units = plant.units as readonly JsonObject[];
	const metrics = readObject(result.metrics);
	const format = (v: unknown) =>
		typeof v === "number"
			? new Intl.NumberFormat(locale, { maximumFractionDigits: 3 }).format(v)
			: "—";
	const total = (v: JsonObject) =>
		[v.pv_kwh, v.grid_kwh, v.initial_unknown_kwh].reduce<number>(
			(a, n) => a + Number(n),
			0,
		);
	return (
		<section className="lp-scenario-block">
			<h4>{__("Stored energy by unit", "linker-tools")}</h4>
			<div className="lp-table-scroll" tabIndex={0}>
				<table>
					<caption>
						{__(
							"Initial and final stored energy (kWh), with final energy shown by origin",
							"linker-tools",
						)}
					</caption>
					<thead>
						<tr>
							<th>{__("Storage unit", "linker-tools")}</th>
							<th>{__("Starting state", "linker-tools")}</th>
							<th>{__("Stored energy at end", "linker-tools")}</th>
							<th>{__("From PV", "linker-tools")}</th>
							<th>{__("From the grid", "linker-tools")}</th>
							<th>{__("Origin unknown", "linker-tools")}</th>
						</tr>
					</thead>
					<tbody>
						{(metrics.units as readonly JsonObject[]).map((u) => {
							const finish = readObject(u.stored_final);
							return (
								<tr key={String(u.unit_id)}>
									<th scope="row">
										{String(units.find((x) => x.id === u.unit_id)!.name)}
									</th>
									<td>{format(total(readObject(u.stored_initial)))}</td>
									<td>{format(total(finish))}</td>
									<td>{format(finish.pv_kwh)}</td>
									<td>{format(finish.grid_kwh)}</td>
									<td>{format(finish.initial_unknown_kwh)}</td>
								</tr>
							);
						})}
					</tbody>
				</table>
			</div>
		</section>
	);
}
