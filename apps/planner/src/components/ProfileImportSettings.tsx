import type { ImportCommand } from "../domain/profiles.ts";
import { __ } from "../i18n.ts";
import {
	delimiterLabel,
	measurementLabel,
	originLabel,
	timestampRoleLabel,
	valueKindLabel,
} from "./ProfileLabels.ts";

/** A read-only view of the exact frozen request, never the mutable form state. */
export function ProfileImportSettings({
	command,
	locale,
}: {
	command: ImportCommand;
	locale: string;
}) {
	const mapping = command.mapping;
	const optional = (column: string | null) =>
		column ?? __("Not used", "linker-tools");
	const facts: [string, string][] = [
		[__("Source label", "linker-tools"), command.source_label],
		[__("Timestamp column", "linker-tools"), mapping.timestamp_column],
		[__("Value column", "linker-tools"), mapping.value_column],
		[
			__("Measurement point", "linker-tools"),
			measurementLabel(mapping.measurement),
		],
		[
			__("Value meaning and unit", "linker-tools"),
			valueKindLabel(mapping.value_kind),
		],
		[__("Source type", "linker-tools"), originLabel(mapping.origin)],
		[__("Column delimiter", "linker-tools"), delimiterLabel(mapping.delimiter)],
		[
			__("Decimal separator in the file", "linker-tools"),
			mapping.decimal === "."
				? __("Point · 12.5", "linker-tools")
				: __("Comma · 12,5", "linker-tools"),
		],
		[
			__("Interval boundaries", "linker-tools"),
			mapping.end_timestamp_column === null
				? __("Timestamp and fixed duration", "linker-tools")
				: __("Separate start and end columns", "linker-tools"),
		],
		[
			__("The timestamp identifies…", "linker-tools"),
			timestampRoleLabel(mapping.timestamp_role),
		],
		...(mapping.interval_seconds === null
			? []
			: ([
					[
						__("Interval duration", "linker-tools"),
						new Intl.NumberFormat(locale, {
							maximumSignificantDigits: 17,
						}).format(mapping.interval_seconds / 60) + " min",
					],
				] as [string, string][])),
		[
			__("Interval end column", "linker-tools"),
			optional(mapping.end_timestamp_column),
		],
		[__("Source time zone", "linker-tools"), mapping.timezone],
		[
			__("Repeated-time column · optional", "linker-tools"),
			optional(mapping.fold_column),
		],
		[
			__("End repeated-time column · optional", "linker-tools"),
			optional(mapping.end_fold_column),
		],
		[
			__("Source and permission for permanent private storage", "linker-tools"),
			command.rights_note,
		],
	];
	return (
		<>
			<dl className="lp-profile-facts">
				{facts.map(([label, value]) => (
					<div key={label}>
						<dt>{label}</dt>
						<dd>{value}</dd>
					</div>
				))}
			</dl>
			<p>
				{__(
					"ISO date and time. An explicit UTC offset takes precedence over the selected time zone.",
					"linker-tools",
				)}
			</p>
			<p>
				{__(
					"If the file contains energy per interval, average power is calculated using the interval duration. For this interpretation, average power is treated as constant within each original interval. No additional measurements are created.",
					"linker-tools",
				)}
			</p>
		</>
	);
}
