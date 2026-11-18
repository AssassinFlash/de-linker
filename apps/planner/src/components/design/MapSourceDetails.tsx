import type { Source } from "../../domain/geometry.ts";
import { formatComputedDecimal, formatDecimal } from "../../domain/decimal.ts";
import { __, sprintf } from "../../i18n.ts";

type SourceDetailsProps = { source: Source; locale: string };

export function SourceMeasurements({ source, locale }: SourceDetailsProps) {
	return (
		<>
			<dt>{__("Declared spatial precision (m)", "linker-tools")}</dt>
			<dd>
				{source.spatial_precision_m === null
					? __("Unknown", "linker-tools")
					: formatDecimal(source.spatial_precision_m, locale)}
			</dd>
			<dt>{__("Calibration and measurement conditions", "linker-tools")}</dt>
			<dd>{source.calibration_note}</dd>
			{source.calibration && (
				<>
					<dt>{__("Recorded scale", "linker-tools")}</dt>
					<dd>
						{sprintf(
							__("%s m per pixel", "linker-tools"),
							formatComputedDecimal(source.calibration.m_per_pixel, locale),
						)}
					</dd>
				</>
			)}
		</>
	);
}

/** A source declaration remains a fact record, never a claim by the renderer. */
export function MapSourceDetails({ source, locale }: SourceDetailsProps) {
	return (
		<dl className="lp-drawing-source">
			<dt>{__("Measurement or drawing reference", "linker-tools")}</dt>
			<dd>{source.note}</dd>
			<SourceMeasurements source={source} locale={locale} />
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
