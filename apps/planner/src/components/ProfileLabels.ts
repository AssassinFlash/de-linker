import type { Measurement } from "../domain/profiles.ts";
import type { ProfileIssue } from "../data/profileIssue.ts";
import { __ } from "../i18n.ts";

export function valueKindLabel(kind: unknown): string {
	return kind === "interval_average_kw"
		? __("Average power over each interval · kW", "linker-tools")
		: kind === "interval_energy_kwh"
			? __("Energy within each interval · kWh", "linker-tools")
			: __("Not specified", "linker-tools");
}
export function timestampRoleLabel(role: unknown): string {
	return role === "start"
		? __("The start of the interval", "linker-tools")
		: role === "end"
			? __("The end of the interval", "linker-tools")
			: __("Not specified", "linker-tools");
}
export function delimiterLabel(delimiter: string): string {
	const labels: Record<string, string> = {
		";": __("Semicolon", "linker-tools"),
		",": __("Comma", "linker-tools"),
		"\t": __("Tab", "linker-tools"),
		"|": __("Vertical bar", "linker-tools"),
	};
	return labels[delimiter] ?? delimiter;
}

export function measurementLabel(role: Measurement): string {
	const labels = {
		gross_load: __("Total site load", "linker-tools"),
		critical_load: __("Critical load", "linker-tools"),
		net_import: __(
			"Net grid import · negative values mean export",
			"linker-tools",
		),
		pv_available_ac: __("Available PV output · AC", "linker-tools"),
		pv_generation_ac: __("PV generation · AC", "linker-tools"),
		aux_ac: __("External auxiliary load · AC", "linker-tools"),
	};
	return labels[role];
}
export function originLabel(origin: string): string {
	const labels: Record<string, string> = {
		measured: __("Measured", "linker-tools"),
		modelled: __("Modelled", "linker-tools"),
		template: __("Template", "linker-tools"),
		synthetic: __("Synthetic test data", "linker-tools"),
	};
	return labels[origin] ?? __("Source not identified", "linker-tools");
}
export function issueLabel(issue: ProfileIssue["issue"]): string {
	const labels = {
		timestamp_format: __(
			"Use ISO dates and times, for example 2024-01-01T00:00+01:00.",
			"linker-tools",
		),
		timestamp_range: __(
			"A timestamp is outside the supported date range.",
			"linker-tools",
		),
		fold_value: __(
			"The repeated-time column must contain 0 for the first occurrence or 1 for the second.",
			"linker-tools",
		),
		offset_and_fold: __(
			"A timestamp uses either a UTC offset or a repeated-time column. Both cannot apply together.",
			"linker-tools",
		),
		local_time_range: __(
			"A local timestamp cannot be converted within the supported date range.",
			"linker-tools",
		),
		local_time_nonexistent: __(
			"This local time does not exist because of a clock change. The source time convention needs to be checked.",
			"linker-tools",
		),
		fold_mismatch: __(
			"The occurrence value does not match this local timestamp.",
			"linker-tools",
		),
		local_time_ambiguous: __(
			"This local time occurs twice. Its UTC offset or a column identifying the occurrence is required.",
			"linker-tools",
		),
		number_format: __(
			"Numbers must match the selected decimal separator. Thousands separators and blank numeric values are not accepted.",
			"linker-tools",
		),
		number_nonfinite: __(
			"A numeric value is outside the finite supported range.",
			"linker-tools",
		),
		encoding: __("Save the source file with UTF-8 encoding.", "linker-tools"),
		headers: __(
			"The first record must contain unique column names, including every mapped column.",
			"linker-tools",
		),
		row_width: __(
			"This record has a different number of cells from the header. Check the delimiter and quotation marks.",
			"linker-tools",
		),
		interval_duration: __(
			"An interval needs a positive duration within the supported date range.",
			"linker-tools",
		),
		interval_order: __(
			"Intervals must be in time order and must not overlap. Correct the source rather than sorting it here.",
			"linker-tools",
		),
		value_sign: __(
			"Values must be finite and match the selected measurement point. Negative values are accepted only for net grid import.",
			"linker-tools",
		),
		energy_range: __(
			"Integrated energy is outside the supported numeric range. The source units and values need to be checked.",
			"linker-tools",
		),
		csv_syntax: __(
			"The CSV quotation or record structure is invalid.",
			"linker-tools",
		),
		empty: __("The file contains no data records.", "linker-tools"),
	};
	return labels[issue];
}
