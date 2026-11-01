import type { CircuitOperatingCondition } from "../../domain/installationElectrical.ts";
import { GeometryNumber, GeometryText } from "../design/GeometryForm.tsx";
import type { GeometryValues } from "../design/GeometryForm.tsx";
export const electricalText = (locale: string, en: string, de: string) =>
	locale.startsWith("de") ? de : en;
export function ElectricalChoice({
	name,
	label,
	value,
	options,
	optional = false,
	onChange,
}: {
	name: string;
	label: string;
	value?: string | undefined;
	options: readonly (readonly [string, string])[];
	optional?: boolean;
	onChange?: () => void;
}) {
	return (
		<label className="lp-field">
			<span>{label}</span>
			<select
				name={name}
				defaultValue={value ?? ""}
				required={!optional}
				onChange={onChange}
			>
				<option value="">—</option>
				{options.map(([v, text]) => (
					<option key={v} value={v}>
						{text}
					</option>
				))}
			</select>
		</label>
	);
}
export function ElectricalConditionFields({
	id,
	before,
	locale,
}: {
	id: string;
	before: CircuitOperatingCondition | null;
	locale: string;
}) {
	const t = (en: string, de: string) => electricalText(locale, en, de),
		p = id + "_";
	const number = (
		key: string,
		label: string,
		unit: string,
		value: number | null | undefined,
		optional = false,
	) => (
		<GeometryNumber
			name={p + key}
			label={label}
			unit={unit}
			locale={locale}
			value={value}
			optional={optional}
		/>
	);
	const boolOptions = [
		["true", t("Yes", "Ja")],
		["false", t("No", "Nein")],
	] as const;
	return (
		<fieldset>
			<legend>
				{t("Declared operating condition", "Erklärter Betriebszustand")}
			</legend>
			<GeometryText
				name={p + "name"}
				label={t("Condition name", "Bezeichnung des Betriebszustands")}
				value={before?.name ?? ""}
			/>
			<ElectricalChoice
				name={p + "method"}
				label={t("Calculation method", "Berechnungsverfahren")}
				value={before?.method}
				options={[
					["dc_resistive", t("DC resistive loop", "DC-Widerstandsschleife")],
					["ac_two_wire", t("AC two-wire", "AC-Zweileiter")],
					[
						"ac_balanced_three_phase",
						t("AC balanced three-phase", "AC symmetrisch dreiphasig"),
					],
				]}
			/>
			{number(
				"current",
				t("Steady current", "Stationärer Strom"),
				"A",
				before?.current_a,
			)}
			{number(
				"voltage",
				t("Reference voltage", "Bezugsspannung"),
				"V",
				before?.reference_voltage_v,
			)}
			<ElectricalChoice
				name={p + "direction"}
				label={t("Current direction", "Stromrichtung")}
				value={before?.direction}
				options={[
					["start_to_end", t("From → To", "Von → Nach")],
					["end_to_start", t("To → From", "Nach → Von")],
				]}
			/>
			{number(
				"temperature",
				t("Conductor temperature", "Leitertemperatur"),
				"°C",
				before?.conductor_temperature_c,
			)}
			{number(
				"frequency",
				t("AC frequency", "AC-Frequenz"),
				"Hz",
				before?.frequency_hz,
				true,
			)}
			{number(
				"pf",
				t("AC power factor", "AC-Leistungsfaktor"),
				"cos φ",
				before?.power_factor,
				true,
			)}
			<ElectricalChoice
				name={p + "reactive"}
				label={t("AC reactive current", "AC-Blindstrom")}
				value={before?.reactive_direction ?? ""}
				optional
				options={[
					["lagging", t("Lagging", "Nacheilend")],
					["leading", t("Leading", "Voreilend")],
				]}
			/>
			<ElectricalChoice
				name={p + "balanced"}
				label={t("Balanced phases", "Symmetrische Phasen")}
				value={before?.balanced == null ? "" : String(before.balanced)}
				optional
				options={boolOptions}
			/>
			<ElectricalChoice
				name={p + "sinusoidal"}
				label={t("Sinusoidal current", "Sinusförmiger Strom")}
				value={before ? String(before.sinusoidal) : ""}
				options={boolOptions}
			/>
			<GeometryText
				name={p + "arrangement"}
				label={t(
					"Conductor arrangement (exact manufacturer condition)",
					"Leiteranordnung (genaue Herstellerbedingung)",
				)}
				value={before?.arrangement ?? ""}
				optional
			/>
			<GeometryText
				name={p + "note"}
				label={t(
					"Source of these operating conditions",
					"Quelle dieser Betriebsbedingungen",
				)}
				value={before?.source_note ?? ""}
				multiline
			/>
			{number(
				"limit",
				t(
					"Project voltage-drop limit (optional)",
					"Projektgrenzwert für den Spannungsfall (optional)",
				),
				"%",
				before?.voltage_limit?.maximum_percent,
				true,
			)}
			<GeometryText
				name={p + "limit_note"}
				label={t(
					"Source and applicability of the project limit",
					"Quelle und Geltungsbereich des Projektgrenzwerts",
				)}
				value={before?.voltage_limit?.source_note ?? ""}
				optional
				multiline
			/>
		</fieldset>
	);
}
export function operatingCondition(
	v: GeometryValues,
	id: string,
): CircuitOperatingCondition {
	const p = id + "_",
		limit = v.number(p + "limit", { optional: true, min: 0 }),
		note = v.text(p + "limit_note");
	if ((limit === null) !== (note === ""))
		throw new Error("voltage_limit_requires_basis");
	const balanced = v.text(p + "balanced"),
		sinusoidal = v.text(p + "sinusoidal");
	if (!["true", "false"].includes(sinusoidal))
		throw new Error("sinusoidal_declaration_required");
	return {
		id,
		name: v.text(p + "name"),
		method: v.text(p + "method") as CircuitOperatingCondition["method"],
		current_a: v.metric(p + "current", { min: 0 }),
		reference_voltage_v: v.metric(p + "voltage", { positive: true }),
		direction: v.text(
			p + "direction",
		) as CircuitOperatingCondition["direction"],
		conductor_temperature_c: v.metric(p + "temperature"),
		frequency_hz: v.number(p + "frequency", { optional: true, positive: true }),
		power_factor: v.number(p + "pf", { optional: true, min: 0, max: 1 }),
		reactive_direction: (v.text(p + "reactive") ||
			null) as CircuitOperatingCondition["reactive_direction"],
		balanced: balanced === "" ? null : balanced === "true",
		sinusoidal: sinusoidal === "true",
		arrangement: v.text(p + "arrangement") || null,
		source_note: v.text(p + "note"),
		voltage_limit:
			limit === null ? null : { maximum_percent: limit, source_note: note },
	};
}
