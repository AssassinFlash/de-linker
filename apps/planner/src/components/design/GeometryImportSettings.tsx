import type { GeometryImportCommand } from "../../domain/geometryImports.ts";
import { formatDecimal } from "../../domain/decimal.ts";
import { __ } from "../../i18n.ts";

/** Frozen declarations stay inspectable without presenting command JSON as UI. */
export function GeometryImportSettings({
	command,
	locale,
}: {
	command: GeometryImportCommand;
	locale: string;
}) {
	const options = command.options,
		number = (value: number) => formatDecimal(value, locale),
		vector = (value: readonly number[]) => value.map(number).join(" · ");
	return (
		<details className="lp-comparison">
			<summary>{__("Original import settings", "linker-tools")}</summary>
			<p>
				{__(
					"A retry uses this original file and these unchanged settings for the same import.",
					"linker-tools",
				)}
			</p>
			<dl className="lp-field-summary">
				<div>
					<dt>{__("Roof face name", "linker-tools")}</dt>
					<dd>{options.roof_name}</dd>
				</div>
				<div>
					<dt>{__("Feature in original file", "linker-tools")}</dt>
					<dd>{options.feature_index + 1}</dd>
				</div>
				<div>
					<dt>{__("Roof face in feature", "linker-tools")}</dt>
					<dd>{options.polygon_index + 1}</dd>
				</div>
				<div>
					<dt>{__("Project origin longitude", "linker-tools")}</dt>
					<dd>{number(options.reference.longitude_deg)}°</dd>
				</div>
				<div>
					<dt>{__("Project origin latitude", "linker-tools")}</dt>
					<dd>{number(options.reference.latitude_deg)}°</dd>
				</div>
				<div>
					<dt>
						{__(
							"Plane origin: east, north and relative height (m)",
							"linker-tools",
						)}
					</dt>
					<dd>{vector(options.plane.origin_enu)} m</dd>
				</div>
				<div>
					<dt>{__("Plane U unit vector (east, north, up)", "linker-tools")}</dt>
					<dd>{vector(options.plane.u_axis_enu)}</dd>
				</div>
				<div>
					<dt>{__("Plane V unit vector (east, north, up)", "linker-tools")}</dt>
					<dd>{vector(options.plane.v_axis_enu)}</dd>
				</div>
				<div>
					<dt>{__("Roof-plane reference", "linker-tools")}</dt>
					<dd>{options.plane.basis_note}</dd>
				</div>
				<div>
					<dt>{__("Source reference", "linker-tools")}</dt>
					<dd>{options.source.label}</dd>
				</div>
				<div>
					<dt>{__("Declared spatial precision", "linker-tools")}</dt>
					<dd>
						{options.source.spatial_precision_m === null
							? __("Unknown", "linker-tools")
							: number(options.source.spatial_precision_m) + " m"}
					</dd>
				</div>
				<div>
					<dt>{__("Permission or licence basis", "linker-tools")}</dt>
					<dd>{options.source.rights_note}</dd>
				</div>
				<div>
					<dt>{__("Permission to export geometry", "linker-tools")}</dt>
					<dd>
						{options.source.export_permission === "permitted"
							? __("Permitted", "linker-tools")
							: options.source.export_permission === "prohibited"
								? __("Prohibited", "linker-tools")
								: __("Unknown", "linker-tools")}
					</dd>
				</div>
				<div>
					<dt>{__("Conversion method", "linker-tools")}</dt>
					<dd>
						<code>
							{options.plane_intersection_method ??
								__("Unsupported earlier conversion method", "linker-tools")}
						</code>
					</dd>
				</div>
			</dl>
		</details>
	);
}
