import type { Source } from "../../domain/geometry.ts";
import { formatDecimal } from "../../domain/decimal.ts";
import { __ } from "../../i18n.ts";

/** A source declaration remains a fact record, never a claim by the renderer. */
export function MapSourceDetails({
	source,
	locale,
}: {
	source: Source;
	locale: string;
}) {
	return (
		<dl className="lp-drawing-source">
			<dt>{__("Measurement or drawing reference", "linker-tools")}</dt>
			<dd>{source.note}</dd>
			<dt>{__("Declared spatial precision (m)", "linker-tools")}</dt>
			<dd>
				{source.spatial_precision_m === null
					? __("Unknown", "linker-tools")
					: formatDecimal(source.spatial_precision_m, locale)}
			</dd>
			<dt>{__("Calibration and measurement conditions", "linker-tools")}</dt>
			<dd>{source.calibration_note}</dd>
			<dt>{__("Basis for using these measurements", "linker-tools")}</dt>
			<dd>{source.rights_note}</dd>
			<dt>{__("Permission to export geometry", "linker-tools")}</dt>
			<dd>
				{source.permissions.export === "permitted"
					? __("Permitted", "linker-tools")
					: source.permissions.export === "prohibited"
						? __("Prohibited", "linker-tools")
						: __("Unknown", "linker-tools")}
			</dd>
		</dl>
	);
}
