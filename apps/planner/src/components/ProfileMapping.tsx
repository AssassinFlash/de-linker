import { useId, useMemo } from "react";
import type { ReactNode } from "react";
import { MEASUREMENTS } from "../domain/profiles.ts";
import type { CsvMapping } from "../domain/profiles.ts";
import { __ } from "../i18n.ts";
import {
	measurementLabel,
	originLabel,
	timestampRoleLabel,
	valueKindLabel,
} from "./ProfileLabels.ts";
import { NumberField } from "./NumberField.tsx";

export interface MappingFields {
	readonly timestamp: string;
	readonly value: string;
	readonly measurement: string;
	readonly unit: string;
	readonly timeRole: string;
	readonly timezone: string;
	readonly origin: string;
	readonly durationMode: string;
	readonly minutes: number | null;
	readonly end: string;
	readonly fold: string;
	readonly endFold: string;
	readonly decimal: string;
}
export function emptyMapping(timezone: string | null): MappingFields {
	return {
		timestamp: "",
		value: "",
		measurement: "",
		unit: "",
		timeRole: "",
		timezone: timezone ?? "",
		origin: "",
		durationMode: "",
		minutes: null,
		end: "",
		fold: "",
		endFold: "",
		decimal: "",
	};
}
export function mappedProfile(
	fields: MappingFields,
	delimiter: string,
): CsvMapping | null {
	if (
		!fields.timestamp ||
		!fields.value ||
		!fields.measurement ||
		!fields.unit ||
		!fields.timezone ||
		!fields.origin ||
		!fields.decimal ||
		(fields.durationMode !== "ends" &&
			(fields.durationMode !== "fixed" ||
				!fields.timeRole ||
				fields.minutes === null ||
				fields.minutes <= 0)) ||
		(fields.durationMode === "ends" && !fields.end)
	)
		return null;
	const columns = [
		fields.timestamp,
		fields.value,
		...(fields.durationMode === "ends" ? [fields.end] : []),
		...[
			fields.fold,
			fields.durationMode === "ends" ? fields.endFold : "",
		].filter(Boolean),
	];
	if (new Set(columns).size !== columns.length) return null;
	return {
		timestamp_column: fields.timestamp,
		value_column: fields.value,
		measurement: fields.measurement as CsvMapping["measurement"],
		value_kind: fields.unit as CsvMapping["value_kind"],
		timestamp_role:
			fields.durationMode === "ends"
				? "start"
				: (fields.timeRole as CsvMapping["timestamp_role"]),
		timezone: fields.timezone,
		origin: fields.origin as CsvMapping["origin"],
		interval_seconds:
			fields.durationMode === "fixed" ? fields.minutes! * 60 : null,
		delimiter,
		decimal: fields.decimal as CsvMapping["decimal"],
		end_timestamp_column: fields.durationMode === "ends" ? fields.end : null,
		fold_column: fields.fold || null,
		end_fold_column:
			fields.durationMode === "ends" ? fields.endFold || null : null,
		offset_rule: "explicit_offset_precedes_naive_timezone",
		within_interval_assumption: "constant_mean_no_new_observations",
	};
}
function Choice({
	label,
	value,
	onChange,
	children,
	help,
	optional = false,
}: {
	label: string;
	value: string;
	onChange: (value: string) => void;
	children: ReactNode;
	help?: string;
	optional?: boolean;
}) {
	const id = useId();
	return (
		<label className="lp-field">
			<span id={id + "-label"}>{label}</span>
			<select
				value={value}
				required={!optional}
				onChange={(event) => onChange(event.currentTarget.value)}
				aria-describedby={help ? id : undefined}
				aria-labelledby={id + "-label"}
			>
				<option value="">
					{optional
						? __("Not used", "linker-tools")
						: __("Select…", "linker-tools")}
				</option>
				{children}
			</select>
			{help && <small id={id}>{help}</small>}
		</label>
	);
}
export function ProfileMapping({
	columns,
	fields,
	locale,
	onChange,
	onValidity,
}: {
	columns: readonly string[];
	fields: MappingFields;
	locale: string;
	onChange: (next: MappingFields) => void;
	onValidity: (valid: boolean) => void;
}) {
	const zones = useMemo(
		() => ["UTC", ...Intl.supportedValuesOf("timeZone")],
		[],
	);
	const set = (key: keyof MappingFields, value: string | number | null) =>
		onChange({ ...fields, [key]: value });
	const options = () =>
		columns.filter(Boolean).map((column) => (
			<option key={column} value={column}>
				{column}
			</option>
		));
	return (
		<div className="lp-profile-mapping grid gap-5 md:grid-cols-2">
			<Choice
				label={__("Timestamp column", "linker-tools")}
				value={fields.timestamp}
				onChange={(value) => set("timestamp", value)}
				help={__(
					"ISO date and time. An explicit UTC offset takes precedence over the selected time zone.",
					"linker-tools",
				)}
			>
				{options()}
			</Choice>
			<Choice
				label={__("Value column", "linker-tools")}
				value={fields.value}
				onChange={(value) => set("value", value)}
			>
				{options()}
			</Choice>
			<Choice
				label={__("Measurement point", "linker-tools")}
				value={fields.measurement}
				onChange={(value) => set("measurement", value)}
				help={__(
					"What these values represent. Net grid import can include the effect of on-site generation and storage and cannot replace total site load.",
					"linker-tools",
				)}
			>
				{MEASUREMENTS.map((role) => (
					<option key={role} value={role}>
						{measurementLabel(role)}
					</option>
				))}
			</Choice>
			<Choice
				label={__("Value meaning and unit", "linker-tools")}
				value={fields.unit}
				onChange={(value) => set("unit", value)}
				help={__(
					"Supported values are average power over an interval or energy within an interval. Instantaneous power samples need a separate interpretation.",
					"linker-tools",
				)}
			>
				<option value="interval_average_kw">
					{valueKindLabel("interval_average_kw")}
				</option>
				<option value="interval_energy_kwh">
					{valueKindLabel("interval_energy_kwh")}
				</option>
			</Choice>
			<Choice
				label={__("Decimal separator in the file", "linker-tools")}
				value={fields.decimal}
				onChange={(value) => set("decimal", value)}
			>
				<option value=".">{__("Point · 12.5", "linker-tools")}</option>
				<option value=",">{__("Comma · 12,5", "linker-tools")}</option>
			</Choice>
			<Choice
				label={__("Source type", "linker-tools")}
				value={fields.origin}
				onChange={(value) => set("origin", value)}
				help={__(
					"This declaration is saved with the file. It describes the source you selected and does not verify the accuracy of a meter or model.",
					"linker-tools",
				)}
			>
				{["measured", "modelled", "template", "synthetic"].map((origin) => (
					<option key={origin} value={origin}>
						{originLabel(origin)}
					</option>
				))}
			</Choice>
			<Choice
				label={__("Interval boundaries", "linker-tools")}
				value={fields.durationMode}
				onChange={(value) => set("durationMode", value)}
			>
				<option value="fixed">
					{__("Timestamp and fixed duration", "linker-tools")}
				</option>
				<option value="ends">
					{__("Separate start and end columns", "linker-tools")}
				</option>
			</Choice>
			{fields.durationMode === "fixed" && (
				<>
					<Choice
						label={__("The timestamp identifies…", "linker-tools")}
						value={fields.timeRole}
						onChange={(value) => set("timeRole", value)}
					>
						<option value="start">{timestampRoleLabel("start")}</option>
						<option value="end">{timestampRoleLabel("end")}</option>
					</Choice>
					<NumberField
						label={__("Interval duration", "linker-tools")}
						unit="min"
						locale={locale}
						value={fields.minutes}
						min={0}
						onChange={(value) => set("minutes", value)}
						onValidity={onValidity}
					/>
				</>
			)}
			{fields.durationMode === "ends" && (
				<Choice
					label={__("Interval end column", "linker-tools")}
					value={fields.end}
					onChange={(value) => set("end", value)}
				>
					{options()}
				</Choice>
			)}
			<Choice
				label={__("Source time zone", "linker-tools")}
				value={fields.timezone}
				onChange={(value) => set("timezone", value)}
				help={__(
					"The source time zone applies to timestamps without a UTC offset and may differ from the project location.",
					"linker-tools",
				)}
			>
				{[
					...new Set([...(fields.timezone ? [fields.timezone] : []), ...zones]),
				].map((zone) => (
					<option key={zone} value={zone}>
						{zone}
					</option>
				))}
			</Choice>
			<Choice
				label={__("Repeated-time column · optional", "linker-tools")}
				value={fields.fold}
				onChange={(value) => set("fold", value)}
				optional
				help={__(
					"For repeated local times: 0 identifies the first occurrence, 1 the second. Timestamps with UTC offsets do not use this column.",
					"linker-tools",
				)}
			>
				{options()}
			</Choice>
			{fields.durationMode === "ends" && (
				<Choice
					label={__("End repeated-time column · optional", "linker-tools")}
					value={fields.endFold}
					onChange={(value) => set("endFold", value)}
					optional
					help={__(
						"For this column, 0 identifies the first occurrence of a repeated local end time and 1 the second.",
						"linker-tools",
					)}
				>
					{options()}
				</Choice>
			)}
		</div>
	);
}
