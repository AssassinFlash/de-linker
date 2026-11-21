import { panelLabel } from "../../domain/panelParameters.ts";
import type { GeometryDocument } from "../../domain/geometry.ts";
import { panelPoses } from "../../domain/panelPoses.ts";
import { __ } from "../../i18n.ts";

/** Display the saved ENU geometry and Woo facts; no electrical model. */
export function PvgisRoofFacts({
	geometry,
	locale,
}: {
	geometry: GeometryDocument;
	locale: string;
}) {
	const poses = panelPoses(geometry).filter((p) => p.included),
		n = (v: number) =>
			new Intl.NumberFormat(locale, { maximumFractionDigits: 3 }).format(v);
	return (
		<div className="sc-scenario-sources">
			<h4>{__("Inputs from the roof design", "linker-tools")}</h4>
			<dl className="sc-run-facts">
				<dt>{__("Included modules", "linker-tools")}</dt>
				<dd>{n(poses.length)}</dd>
				<dt>{__("Module nameplate power", "linker-tools")}</dt>
				<dd>
					{n(poses.reduce((sum, p) => sum + p.stc_power_w, 0) / 1000)} kWp
				</dd>
				<dt>{__("Location", "linker-tools")}</dt>
				<dd>
					{geometry.coordinate_system.anchor!.latitude_deg}°,{" "}
					{geometry.coordinate_system.anchor!.longitude_deg}°
				</dd>
			</dl>
			<div className="sc-table-scroll">
				<table className="sc-data-table">
					<thead>
						<tr>
							{[
								__("Array", "linker-tools"),
								__("Panel dimensions", "linker-tools"),
								__("Included modules", "linker-tools"),
								__("Nameplate power (kWp)", "linker-tools"),
								__("Tilt (°)", "linker-tools"),
								__("Azimuth from north, clockwise (°)", "linker-tools"),
							].map((label) => (
								<th key={label} scope="col">
									{label}
								</th>
							))}
						</tr>
					</thead>
					<tbody>
						{geometry.arrays.map((array) => {
							const included = poses.filter((p) => p.array_id === array.id),
								first = included[0];
							if (!first) return null;
							const normal = first.normal_enu,
								horizontal = Math.hypot(normal[0], normal[1]);
							return (
								<tr key={array.id}>
									<th scope="row">{array.name}</th>
									<td>
										{panelLabel(
											geometry.module_specs.find(
												(m) => m.id === array.module_spec_id,
											)!,
											locale,
										)}
									</td>
									<td>{n(included.length)}</td>
									<td>
										{n(
											included.reduce((sum, p) => sum + p.stc_power_w, 0) /
												1000,
										)}
									</td>
									<td>
										{n((Math.atan2(horizontal, normal[2]) * 180) / Math.PI)}
									</td>
									<td>
										{horizontal
											? n(
													((Math.atan2(normal[0], normal[1]) * 180) / Math.PI +
														360) %
														360,
												)
											: "—"}
									</td>
								</tr>
							);
						})}
					</tbody>
				</table>
			</div>
		</div>
	);
}
