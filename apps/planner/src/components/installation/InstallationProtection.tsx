import { useEffect, useState } from "react";
import type {
	InstallationInputs,
	InstallationCircuit,
} from "../../domain/installation.ts";
import { installationId } from "../../domain/installation.ts";
import { formatComputedDecimal } from "../../domain/decimal.ts";
import type {
	ProtectionAssessment,
	ProtectionComparison,
	ProtectionReview,
} from "../../domain/installationProtection.ts";
import {
	GeometryForm,
	GeometryNumber,
	GeometryText,
} from "../design/GeometryForm.tsx";
import type { GeometryValues } from "../design/GeometryForm.tsx";
import { electricalText } from "./ElectricalConditionFields.tsx";
import { Notice } from "../Notice.tsx";

type Section =
	"context" | "fault_range" | "breaking" | "disconnection" | "thermal";
type Edit = { id: string | null; section: Section; core: string | null };
type Thermal = ProtectionAssessment["thermal"][number];
const coreKey = (core: Pick<Thermal, "run_id" | "core_role">) =>
	JSON.stringify([core.run_id, core.core_role]);

/** Reuse recorded circuit/run/core identities, including a separate PE between the same devices. */
function protectedCores(
	plan: InstallationInputs,
	circuit: InstallationCircuit | undefined,
) {
	if (!circuit) return [];
	const related = plan.circuits.filter(
		(other) =>
			other.id === circuit.id ||
			(other.kind === "protective_earth" &&
				((other.start.instance_id === circuit.start.instance_id &&
					other.end.instance_id === circuit.end.instance_id) ||
					(other.start.instance_id === circuit.end.instance_id &&
						other.end.instance_id === circuit.start.instance_id))),
	);
	return plan.cable_runs.flatMap((run) => {
		const owner = related.find((item) => item.id === run.circuit_id);
		if (!owner || !run.conductor || run.conductor.cross_section_mm2 <= 0)
			return [];
		return (run.core_roles ?? []).flatMap((role) =>
			role === "unused" || (owner.id !== circuit.id && role !== "pe")
				? []
				: [
						{
							key: coreKey({ run_id: run.id, core_role: role }),
							run,
							role,
							owner,
						},
					],
		);
	});
}

type Field = readonly [string, string, string, string?];
const fields: Record<Exclude<Section, "context">, readonly Field[]> = {
	fault_range: [
		[
			"minimum_fault_a",
			"Minimum prospective fault current",
			"Minimaler zu erwartender Fehlerstrom",
			"A",
		],
		[
			"maximum_fault_a",
			"Maximum prospective fault current",
			"Maximaler zu erwartender Fehlerstrom",
			"A",
		],
		[
			"source_note",
			"Where does this fault-current range come from?",
			"Woher stammt dieser Fehlerstrombereich?",
		],
	],
	breaking: [
		[
			"capacity_a",
			"Declared breaking capacity",
			"Erklärtes Ausschaltvermögen",
			"A",
		],
		[
			"rated_voltage_v",
			"Voltage at which that capacity applies",
			"Spannung, für die das Ausschaltvermögen gilt",
			"V",
		],
		[
			"source_note",
			"Device data and applicability",
			"Gerätedaten und Geltungsbereich",
		],
	],
	disconnection: [
		[
			"device_worst_case_clear_s",
			"Device's worst-case clearing time",
			"Ungünstigste Abschaltzeit des Schutzgeräts",
			"s",
		],
		[
			"required_clear_s",
			"Required maximum disconnection time",
			"Geforderte maximale Abschaltzeit",
			"s",
		],
		[
			"device_source_note",
			"Source of the device clearing time",
			"Quelle der Abschaltzeit des Schutzgeräts",
		],
		[
			"limit_source_note",
			"Source and applicability of the required time",
			"Quelle und Geltungsbereich der geforderten Zeit",
		],
	],
	thermal: [
		[
			"maximum_let_through_a2s",
			"Maximum let-through energy for this core",
			"Maximales Durchlassintegral für diese Ader",
			"A²s",
		],
		[
			"coverage_min_fault_a",
			"Lowest fault current covered by this evidence",
			"Niedrigster durch diesen Nachweis abgedeckter Fehlerstrom",
			"A",
		],
		[
			"coverage_max_fault_a",
			"Highest fault current covered by this evidence",
			"Höchster durch diesen Nachweis abgedeckter Fehlerstrom",
			"A",
		],
		[
			"maximum_clear_s",
			"Maximum clearing time covered by this evidence",
			"Maximale durch diesen Nachweis abgedeckte Abschaltzeit",
			"s",
		],
		[
			"k_a_sqrt_s_per_mm2",
			"Declared conductor k factor",
			"Erklärter k-Faktor des Leiters",
			"A√s/mm²",
		],
		[
			"k_source_note",
			"Source of k for this conductor and temperature range",
			"Quelle des k-Faktors für diesen Leiter und Temperaturbereich",
		],
		[
			"let_through_source_note",
			"Source and applicability of the let-through evidence",
			"Quelle und Geltungsbereich des Durchlassnachweises",
		],
	],
};

export function InstallationProtection({
	plan,
	review,
	locale,
	disabled,
	change,
	onValidity,
}: {
	plan: InstallationInputs;
	review: ProtectionReview | undefined;
	locale: string;
	disabled: boolean;
	change: (plan: InstallationInputs) => boolean;
	onValidity: (valid: boolean) => void;
}) {
	const t = (en: string, de: string) => electricalText(locale, en, de);
	const [editing, setEditing] = useState<Edit | null>(null);
	const [context, setContext] = useState({
		circuit: "",
		material: "",
		condition: "",
	});
	const [error, setError] = useState("");
	const items = plan.protection_assessments ?? [];
	const before = items.find((item) => item.id === editing?.id);
	const circuit = plan.circuits.find((item) => item.id === context.circuit);
	const coreCircuit = plan.circuits.find(
		(item) => item.id === before?.circuit_id,
	);
	const cores = protectedCores(plan, coreCircuit);
	const blocked = disabled || editing !== null;
	useEffect(() => {
		onValidity(editing === null);
		return () => onValidity(true);
	}, [editing, onValidity]);
	const heading = (section: Section) =>
		({
			context: t(
				"Circuit, device and condition",
				"Stromkreis, Schutzgerät und Betriebszustand",
			),
			fault_range: t("Fault-current range", "Fehlerstrombereich"),
			breaking: t("Breaking capacity", "Ausschaltvermögen"),
			disconnection: t("Disconnection time", "Abschaltzeit"),
			thermal: t(
				"Conductor short-circuit withstand",
				"Thermische Kurzschlussfestigkeit der Ader",
			),
		})[section];
	const n = (value: number | null | undefined) =>
		value == null ? "—" : formatComputedDecimal(value, locale);
	const displayValue = (value: unknown) =>
		typeof value === "number" ? n(value) : String(value ?? "—");
	const circuitLabel = (item: InstallationCircuit) =>
		`${item.name} · ${plan.instances.find((i) => i.id === item.start.instance_id)?.name ?? "?"} → ${plan.instances.find((i) => i.id === item.end.instance_id)?.name ?? "?"}`;
	const coreLabel = (core: (typeof cores)[number]) =>
		`${core.run.name} · ${{ dc_positive: "DC +", dc_negative: "DC −", line: t("Line", "Außenleiter"), neutral: "N", l1: "L1", l2: "L2", l3: "L3", pe: "PE" }[core.role]} · ${n(core.run.conductor?.cross_section_mm2)} mm²${core.owner.kind === "protective_earth" ? ` · ${t("Protective earth", "Schutzleiter")}: ${core.owner.name}` : ""}`;
	function open(
		section: Section,
		item?: ProtectionAssessment,
		core: string | null = null,
	) {
		setContext({
			circuit: item?.circuit_id ?? "",
			material: item?.protection_material_id ?? "",
			condition: item?.operating_condition_id ?? "",
		});
		setError("");
		setEditing({ id: item?.id ?? null, section, core });
	}
	function update(
		id: string,
		edit: (item: ProtectionAssessment) => ProtectionAssessment,
		confirm = false,
	) {
		return change({
			...plan,
			protection_assessments: items.map((item) =>
				item.id === id
					? {
							...edit(item),
							...(!confirm ? { confirmed_context_sha256: null } : {}),
						}
					: item,
			),
		});
	}
	function submit(v: GeometryValues): boolean {
		if (!editing) return false;
		if (editing.section === "context") {
			const material = (plan.materials ?? []).find(
				(m) =>
					m.id === context.material &&
					m.kind === "protection" &&
					m.circuit_id === context.circuit &&
					m.unit === "piece" &&
					m.quantity === 1,
			);
			const condition = circuit?.operating_conditions?.find(
				(c) => c.id === context.condition,
			);
			if (
				!circuit ||
				(context.material && !material) ||
				(context.condition && !condition)
			) {
				setError(
					t(
						"Select a current circuit, protection item and operating condition. Unavailable selections cannot be reused.",
						"Wählen Sie einen vorhandenen Stromkreis, Schutzartikel und Betriebszustand. Nicht mehr verfügbare Auswahlen können nicht übernommen werden.",
					),
				);
				return false;
			}
			if (before && before.circuit_id !== circuit.id && before.thermal.length) {
				setError(
					t(
						"Remove this condition's core declarations before changing its circuit, or add a separate condition.",
						"Entfernen Sie vor einem Stromkreiswechsel die Adernachweise dieses Betriebszustands oder legen Sie einen eigenen Betriebszustand an.",
					),
				);
				return false;
			}
			const item: ProtectionAssessment = {
				...(before ?? {
					id: installationId("protection"),
					fault_range: null,
					breaking: null,
					disconnection: null,
					thermal: [],
				}),
				circuit_id: circuit.id,
				protection_material_id: material?.id ?? null,
				operating_condition_id: condition?.id ?? null,
				scenario: v.text("scenario"),
				confirmed_context_sha256: null,
			};
			return change({
				...plan,
				protection_assessments: before
					? items.map((old) => (old.id === before.id ? item : old))
					: [...items, item],
			});
		}
		if (!before) return false;
		if (editing.section === "fault_range") {
			const minimum_fault_a = v.metric("minimum_fault_a", { min: 0 }),
				maximum_fault_a = v.metric("maximum_fault_a", { positive: true });
			if (minimum_fault_a > maximum_fault_a) {
				setError(
					t(
						"The minimum fault current must not exceed the maximum.",
						"Der minimale Fehlerstrom darf den maximalen nicht überschreiten.",
					),
				);
				return false;
			}
			return update(before.id, (item) => ({
				...item,
				fault_range: {
					minimum_fault_a,
					maximum_fault_a,
					source_note: v.text("source_note"),
				},
			}));
		}
		if (editing.section === "breaking") {
			const kind = v.text("current_kind");
			if (kind !== "ac" && kind !== "dc") return false;
			return update(before.id, (item) => ({
				...item,
				breaking: {
					capacity_a: v.metric("capacity_a", { positive: true }),
					rated_voltage_v: v.metric("rated_voltage_v", { positive: true }),
					current_kind: kind,
					source_note: v.text("source_note"),
				},
			}));
		}
		if (editing.section === "disconnection")
			return update(before.id, (item) => ({
				...item,
				disconnection: {
					device_worst_case_clear_s: v.metric("device_worst_case_clear_s", {
						positive: true,
					}),
					required_clear_s: v.metric("required_clear_s", { positive: true }),
					device_source_note: v.text("device_source_note"),
					limit_source_note: v.text("limit_source_note"),
				},
			}));
		const selected = cores.find((core) => core.key === v.text("core"));
		if (
			!selected ||
			before.thermal.some(
				(core) =>
					coreKey(core) === selected.key && coreKey(core) !== editing.core,
			)
		) {
			setError(
				t(
					"Select an available recorded core. Each core has one declaration in this condition.",
					"Wählen Sie eine vorhandene verfügbare Ader. Jede Ader hat je Betriebszustand einen Nachweis.",
				),
			);
			return false;
		}
		const coverage_min_fault_a = v.metric("coverage_min_fault_a", { min: 0 }),
			coverage_max_fault_a = v.metric("coverage_max_fault_a", {
				positive: true,
			});
		if (coverage_min_fault_a > coverage_max_fault_a) {
			setError(
				t(
					"The evidence's lower fault-current limit must not exceed its upper limit.",
					"Die untere Fehlerstromgrenze des Nachweises darf die obere nicht überschreiten.",
				),
			);
			return false;
		}
		const thermal: Thermal = {
			run_id: selected.run.id,
			core_role: selected.role,
			maximum_let_through_a2s: v.metric("maximum_let_through_a2s", {
				positive: true,
			}),
			coverage_min_fault_a,
			coverage_max_fault_a,
			maximum_clear_s: v.metric("maximum_clear_s", { positive: true }),
			k_a_sqrt_s_per_mm2: v.metric("k_a_sqrt_s_per_mm2", { positive: true }),
			k_source_note: v.text("k_source_note"),
			let_through_source_note: v.text("let_through_source_note"),
		};
		return update(before.id, (item) => ({
			...item,
			thermal: editing.core
				? item.thermal.map((old) =>
						coreKey(old) === editing.core ? thermal : old,
					)
				: [...item.thermal, thermal],
		}));
	}
	function result(value: ProtectionComparison | undefined, unit: string) {
		if (!value || value.status === "not_assessed")
			return (
				<p>
					{t(
						"Not assessed. Record the applicable evidence, review the saved installation and confirm this condition.",
						"Nicht bewertet. Erfassen Sie die anwendbaren Nachweise, prüfen Sie die gespeicherte Installation und bestätigen Sie diesen Betriebszustand.",
					)}
				</p>
			);
		return (
			<p>
				<strong>
					{value.status === "within_declared_values"
						? t("Within declared values", "Innerhalb der erklärten Werte")
						: t("Outside declared values", "Außerhalb der erklärten Werte")}
				</strong>
				{" · "}
				{n(value.measured)} {unit}{" "}
				{value.status === "within_declared_values" ? "≤" : ">"}{" "}
				{n(value.maximum)} {unit}
			</p>
		);
	}
	const thermalBefore = before?.thermal.find(
		(core) => coreKey(core) === editing?.core,
	);
	const saved =
		editing?.section === "context"
			? null
			: editing?.section === "thermal"
				? thermalBefore
				: editing
					? before?.[editing.section]
					: null;
	return (
		<section
			className="lp-profile-panel"
			aria-label={t("Protection evidence", "Schutznachweise")}
		>
			<h3>
				{t(
					"Protection for each operating condition",
					"Schutz je Betriebszustand",
				)}
			</h3>
			<p className="lp-profile-help">
				{t(
					"Start with a circuit and condition. Add fault currents, device data and core evidence as they become available. The comparison uses your declared evidence; it does not approve the complete installation.",
					"Beginnen Sie mit Stromkreis und Betriebszustand. Ergänzen Sie Fehlerströme, Gerätedaten und Adernachweise, sobald sie vorliegen. Der Vergleich verwendet Ihre erklärten Nachweise; er erteilt keine Freigabe für die gesamte Installation.",
				)}
			</p>
			<button
				type="button"
				className="lp-button lp-button-secondary"
				disabled={blocked || !plan.circuits.length}
				onClick={() => open("context")}
			>
				{t("Add protection condition", "Schutz-Betriebszustand hinzufügen")}
			</button>
			{!plan.circuits.length && (
				<p>
					{t(
						"Record a circuit under Installation first.",
						"Erfassen Sie zuerst einen Stromkreis unter Installation.",
					)}
				</p>
			)}
			{items.map((item) => {
				const selectedCircuit = plan.circuits.find(
						(c) => c.id === item.circuit_id,
					),
					material = plan.materials?.find(
						(m) => m.id === item.protection_material_id,
					),
					condition = selectedCircuit?.operating_conditions?.find(
						(c) => c.id === item.operating_condition_id,
					),
					assessed = review?.assessments.find((row) => row.id === item.id);
				return (
					<article key={item.id} className="lp-profile-panel">
						<h4>{item.scenario}</h4>
						<p>
							{selectedCircuit
								? circuitLabel(selectedCircuit)
								: t("Circuit unavailable", "Stromkreis nicht verfügbar")}
						</p>
						<p>
							{t("Protection item", "Schutzartikel")}:{" "}
							{material?.name ?? t("Not selected", "Nicht ausgewählt")} ·{" "}
							{t("Operating condition", "Betriebszustand")}:{" "}
							{condition?.name ?? t("Not selected", "Nicht ausgewählt")}
						</p>
						<div className="lp-inline-actions">
							<button
								type="button"
								className="lp-button lp-button-secondary"
								disabled={blocked}
								onClick={() => open("context", item)}
							>
								{t("Edit condition", "Betriebszustand bearbeiten")}
							</button>
							<button
								type="button"
								className="lp-button lp-button-secondary"
								disabled={blocked}
								onClick={() =>
									change({
										...plan,
										protection_assessments: items.filter(
											(old) => old.id !== item.id,
										),
									})
								}
							>
								{t("Remove condition", "Betriebszustand entfernen")}
							</button>
						</div>
						{(["fault_range", "breaking", "disconnection"] as const).map(
							(part) => (
								<div key={part}>
									<h5>{heading(part)}</h5>
									{item[part] ? (
										<details>
											<summary>
												{t("Recorded evidence", "Erfasste Nachweise")}
											</summary>
											<dl>
												{fields[part].map(([key, en, de, unit]) => (
													<div key={key}>
														<dt>{t(en, de)}</dt>
														<dd>
															{displayValue(
																item[part]?.[
																	key as keyof NonNullable<
																		(typeof item)[typeof part]
																	>
																] ?? "—",
															)}{" "}
															{unit}
														</dd>
													</div>
												))}
											</dl>
										</details>
									) : (
										<p>{t("Not recorded", "Nicht erfasst")}</p>
									)}
									{part === "breaking" && item.breaking && (
										<p>
											{t("Declared current kind", "Erklärte Stromart")}:{" "}
											{item.breaking.current_kind.toUpperCase()}
										</p>
									)}
									{part !== "fault_range" &&
										result(assessed?.[part], part === "breaking" ? "A" : "s")}
									<div className="lp-inline-actions">
										<button
											type="button"
											className="lp-button lp-button-secondary"
											disabled={blocked}
											onClick={() => open(part, item)}
										>
											{item[part]
												? t("Edit evidence", "Nachweis bearbeiten")
												: t("Add evidence", "Nachweis hinzufügen")}
										</button>
										{item[part] && (
											<button
												type="button"
												className="lp-button lp-button-secondary"
												disabled={blocked}
												onClick={() =>
													update(item.id, (old) => ({ ...old, [part]: null }))
												}
											>
												{t("Remove evidence", "Nachweis entfernen")}
											</button>
										)}
									</div>
								</div>
							),
						)}
						<h5>{heading("thermal")}</h5>
						{item.thermal.map((core) => {
							const existing = protectedCores(plan, selectedCircuit).find(
									(candidate) => candidate.key === coreKey(core),
								),
								checked = assessed?.thermal.find(
									(row) => coreKey(row) === coreKey(core),
								);
							return (
								<div key={coreKey(core)}>
									<p>
										<strong>
											{existing
												? coreLabel(existing)
												: t(
														"Recorded core no longer available",
														"Erfasste Ader nicht mehr verfügbar",
													)}
										</strong>
									</p>
									{result(checked, "A²s")}
									<details>
										<summary>
											{t("Recorded evidence", "Erfasste Nachweise")}
										</summary>
										<dl>
											{fields.thermal.map(([key, en, de, unit]) => (
												<div key={key}>
													<dt>{t(en, de)}</dt>
													<dd>
														{displayValue(core[key as keyof Thermal])} {unit}
													</dd>
												</div>
											))}
										</dl>
									</details>
									<div className="lp-inline-actions">
										<button
											type="button"
											className="lp-button lp-button-secondary"
											disabled={blocked}
											onClick={() => open("thermal", item, coreKey(core))}
										>
											{t("Edit core evidence", "Adernachweis bearbeiten")}
										</button>
										<button
											type="button"
											className="lp-button lp-button-secondary"
											disabled={blocked}
											onClick={() =>
												update(item.id, (old) => ({
													...old,
													thermal: old.thermal.filter(
														(row) => coreKey(row) !== coreKey(core),
													),
												}))
											}
										>
											{t("Remove core evidence", "Adernachweis entfernen")}
										</button>
									</div>
								</div>
							);
						})}
						<button
							type="button"
							className="lp-button lp-button-secondary"
							disabled={
								blocked ||
								!protectedCores(plan, selectedCircuit).some(
									(candidate) =>
										!item.thermal.some(
											(core) => coreKey(core) === candidate.key,
										),
								)
							}
							onClick={() => open("thermal", item)}
						>
							{t("Add core evidence", "Adernachweis hinzufügen")}
						</button>
						{!protectedCores(plan, selectedCircuit).length && (
							<p className="lp-profile-help">
								{t(
									"Record core roles and conductor cross-sections on this circuit's cable runs first. A separate PE run must connect the same two devices and declare a PE core.",
									"Erfassen Sie zuerst Aderfunktionen und Leiterquerschnitte an den Kabelstrecken dieses Stromkreises. Eine separate PE-Strecke muss dieselben beiden Geräte verbinden und eine PE-Ader enthalten.",
								)}
							</p>
						)}
						<p>
							{assessed?.confirmation_status === "confirmed"
								? t(
										"This condition and its recorded sources are confirmed.",
										"Dieser Betriebszustand und seine erfassten Quellen sind bestätigt.",
									)
								: assessed?.confirmation_status === "context_changed"
									? t(
											"The context changed. Check the current evidence and confirm this condition again.",
											"Der Zusammenhang hat sich geändert. Prüfen Sie die aktuellen Nachweise und bestätigen Sie diesen Betriebszustand erneut.",
										)
									: t(
											"Review the saved installation to obtain the current context, then confirm the evidence for this condition.",
											"Prüfen Sie die gespeicherte Installation, um den aktuellen Zusammenhang zu erhalten. Bestätigen Sie anschließend die Nachweise für diesen Betriebszustand.",
										)}
						</p>
						<button
							type="button"
							className="lp-button lp-button-secondary"
							disabled={
								blocked ||
								!assessed?.confirmation_context_sha256 ||
								assessed.confirmation_status === "confirmed"
							}
							onClick={() => {
								if (assessed?.confirmation_context_sha256)
									update(
										item.id,
										(old) => ({
											...old,
											confirmed_context_sha256:
												assessed.confirmation_context_sha256,
										}),
										true,
									);
							}}
						>
							{t(
								"Confirm this condition and these sources",
								"Diesen Betriebszustand und diese Quellen bestätigen",
							)}
						</button>
					</article>
				);
			})}
			{editing && (
				<GeometryForm
					key={JSON.stringify(editing)}
					title={heading(editing.section)}
					locale={locale}
					measurementHelp={false}
					onValidity={() => {}}
					submitDisabled={disabled}
					cancel={() => {
						setEditing(null);
						setError("");
					}}
					submit={submit}
				>
					<fieldset disabled={disabled} onInput={() => setError("")}>
						{editing.section === "context" ? (
							<>
								<label className="lp-field">
									<span>{t("Which circuit?", "Welcher Stromkreis?")}</span>
									<select
										name="circuit"
										value={context.circuit}
										required
										onChange={(e) =>
											setContext({
												circuit: e.currentTarget.value,
												material: "",
												condition: "",
											})
										}
									>
										<option value="">—</option>
										{plan.circuits.map((c) => (
											<option key={c.id} value={c.id}>
												{circuitLabel(c)}
											</option>
										))}
									</select>
								</label>
								<label className="lp-field">
									<span>
										{t(
											"Which recorded protection item?",
											"Welcher erfasste Schutzartikel?",
										)}
									</span>
									<select
										name="material"
										value={context.material}
										onChange={(e) =>
											setContext({
												...context,
												material: e.currentTarget.value,
											})
										}
									>
										<option value="">
											{t("Not selected yet", "Noch nicht ausgewählt")}
										</option>
										{(plan.materials ?? [])
											.filter(
												(m) =>
													m.kind === "protection" &&
													m.circuit_id === context.circuit &&
													m.unit === "piece" &&
													m.quantity === 1,
											)
											.map((m) => (
												<option key={m.id} value={m.id}>
													{m.name} · {m.specification}
												</option>
											))}
									</select>
								</label>
								<label className="lp-field">
									<span>
										{t(
											"Which recorded operating condition?",
											"Welcher erfasste Betriebszustand?",
										)}
									</span>
									<select
										name="condition"
										value={context.condition}
										onChange={(e) =>
											setContext({
												...context,
												condition: e.currentTarget.value,
											})
										}
									>
										<option value="">
											{t("Not selected yet", "Noch nicht ausgewählt")}
										</option>
										{(circuit?.operating_conditions ?? []).map((c) => (
											<option key={c.id} value={c.id}>
												{c.name} · {n(c.reference_voltage_v)} V ·{" "}
												{n(c.current_a)} A
											</option>
										))}
									</select>
								</label>
								{circuit &&
									!(plan.materials ?? []).some(
										(m) =>
											m.kind === "protection" &&
											m.circuit_id === circuit.id &&
											m.unit === "piece" &&
											m.quantity === 1,
									) && (
										<p className="lp-profile-help">
											{t(
												"First record one protection item for this circuit under Materials: unit piece, quantity 1.",
												"Erfassen Sie zuerst unter Materialien einen Schutzartikel für diesen Stromkreis: Einheit Stück, Menge 1.",
											)}
										</p>
									)}
								<p className="lp-profile-help">
									{t(
										"Protection items and operating conditions come from your existing materials and circuit properties. You can add this condition now and complete its evidence later.",
										"Schutzartikel und Betriebszustände stammen aus Ihren vorhandenen Materialien und Stromkreiseigenschaften. Sie können diesen Betriebszustand jetzt anlegen und die Nachweise später ergänzen.",
									)}
								</p>
								<GeometryText
									name="scenario"
									label={t(
										"What situation does this evidence cover?",
										"Für welche Situation gelten diese Nachweise?",
									)}
									value={before?.scenario ?? ""}
								/>
							</>
						) : (
							<>
								{editing.section === "thermal" && (
									<label className="lp-field">
										<span>
											{t(
												"Which recorded cable run and core?",
												"Welche erfasste Kabelstrecke und Ader?",
											)}
										</span>
										<select
											name="core"
											defaultValue={editing.core ?? ""}
											required
										>
											<option value="">—</option>
											{cores
												.filter(
													(candidate) =>
														candidate.key === editing.core ||
														!before?.thermal.some(
															(core) => coreKey(core) === candidate.key,
														),
												)
												.map((core) => (
													<option key={core.key} value={core.key}>
														{coreLabel(core)}
													</option>
												))}
										</select>
									</label>
								)}
								{fields[editing.section].map(([key, en, de, unit]) => {
									const value = saved?.[key as keyof typeof saved];
									return unit ? (
										<GeometryNumber
											key={key}
											name={key}
											label={t(en, de)}
											locale={locale}
											unit={unit}
											value={typeof value === "number" ? value : null}
										/>
									) : (
										<GeometryText
											key={key}
											name={key}
											label={t(en, de)}
											value={typeof value === "string" ? value : ""}
											multiline
										/>
									);
								})}
								{editing.section === "breaking" && (
									<label className="lp-field">
										<span>
											{t(
												"Current kind for the declared capacity",
												"Stromart des erklärten Ausschaltvermögens",
											)}
										</span>
										<select
											name="current_kind"
											required
											defaultValue={before?.breaking?.current_kind ?? ""}
										>
											<option value="">—</option>
											<option value="ac">AC</option>
											<option value="dc">DC</option>
										</select>
									</label>
								)}
							</>
						)}
					</fieldset>
					{error && <Notice error>{error}</Notice>}
				</GeometryForm>
			)}
		</section>
	);
}
