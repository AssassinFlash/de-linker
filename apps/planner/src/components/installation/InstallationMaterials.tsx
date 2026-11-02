import { useEffect, useState } from "react";
import type {
	InstallationInputs,
	InstallationMaterial,
	InstallationReview,
} from "../../domain/installation.ts";
import type { EquipmentProduct } from "../../data/equipmentProducts.ts";
import type { GeometryDocument } from "../../domain/geometry.ts";
import { readObject } from "../../data/readProtocol.ts";
import { installationId, readInstallation } from "../../domain/installation.ts";
import {
	GeometryForm,
	GeometryNumber,
	GeometryText,
} from "../design/GeometryForm.tsx";
import { electricalText } from "./ElectricalConditionFields.tsx";

export function InstallationMaterials({
	plan,
	geometry,
	products,
	review,
	showReviewSummary = true,
	locale,
	disabled,
	change,
	onValidity,
}: {
	plan: InstallationInputs;
	geometry: GeometryDocument;
	products: readonly EquipmentProduct[];
	review: InstallationReview["material_review"];
	showReviewSummary?: boolean;
	locale: string;
	disabled: boolean;
	change: (plan: InstallationInputs) => boolean;
	onValidity: (valid: boolean) => void;
}) {
	const [editing, setEditing] = useState<InstallationMaterial | "new" | null>(
		null,
	);
	const [showComparison, setShowComparison] = useState(false);
	const [comparisonChoice, setComparisonChoice] = useState("");
	const [comparisonConfirmed, setComparisonConfirmed] = useState(false);
	const [showMountingRule, setShowMountingRule] = useState(false);
	const [mountingError, setMountingError] = useState("");
	const t = (en: string, de: string) => electricalText(locale, en, de);
	useEffect(() => {
		onValidity(editing === null);
		return () => onValidity(true);
	}, [editing, onValidity]);
	const before = editing === "new" ? null : editing;
	const candidates = plan.instances.flatMap((instance) => {
		const product = products.find(
			(p) =>
				p.id === instance.product_id &&
				p.product_revision === instance.product_revision,
		);
		if (!product) return [];
		try {
			const facts = readObject(product.installation_facts);
			if (facts.status !== "documented" || !Array.isArray(facts.items))
				return [];
			return facts.items.flatMap((raw) => {
				try {
					const fact = readObject(raw),
						source = readObject(fact.source),
						spec = readObject(fact.specification);
					if (
						!Array.isArray(fact.conditions) ||
						fact.conditions.length ||
						!(
							(fact.basis === "manufacturer_recommended_pe_conductor" &&
								spec.terminal_domain === "pe") ||
							(fact.basis === "manufacturer_minimum_rating" &&
								spec.terminal_domain === "ac")
						) ||
						typeof fact.id !== "string" ||
						typeof source.document_id !== "string" ||
						typeof source.document_revision !== "string" ||
						typeof source.page !== "number"
					)
						return [];
					return [{ instance, product, fact, source }];
				} catch {
					return [];
				}
			});
		} catch {
			return [];
		}
	});
	const identity = (
		instance: unknown,
		product: unknown,
		revision: unknown,
		fact: unknown,
		document: unknown,
		documentRevision: unknown,
	) =>
		JSON.stringify([
			instance,
			product,
			revision,
			fact,
			document,
			documentRevision,
		]);
	const candidateKey = (c: (typeof candidates)[number]) =>
		identity(
			c.instance.id,
			c.product.id,
			c.product.product_revision,
			c.fact.id,
			c.source.document_id,
			c.source.document_revision,
		);
	const activeCandidate = candidates.find(
		(c) => candidateKey(c) === comparisonChoice,
	);
	useEffect(() => {
		if (comparisonChoice && !activeCandidate) setComparisonConfirmed(false);
	}, [comparisonChoice, Boolean(activeCandidate)]);
	const kinds: [InstallationMaterial["kind"], string][] = [
		["connector", t("Connector or terminal", "Steckverbinder oder Klemme")],
		["protection", t("Protection device", "Schutzeinrichtung")],
		["earthing", t("Protective earthing", "Schutzerdung")],
		["mounting", t("Mounting material", "Montagematerial")],
		[
			"other",
			t("Other installation material", "Weiteres Installationsmaterial"),
		],
	];
	return (
		<section className="lp-scenario-block">
			<h3>{t("Installation materials", "Installationsmaterialien")}</h3>
			<p>
				{t(
					"Record physical items and their quantities. Project declarations do not verify connector fit, protective coordination, earthing or a complete bill of materials.",
					"Erfassen Sie die benötigten Bauteile und Mengen. Projektangaben prüfen weder die Eignung von Steckverbindern, die Schutzkoordination oder Erdung noch die Vollständigkeit der Stückliste.",
				)}
			</p>
			{review && showReviewSummary && (
				<p role="status">
					{t(
						"Material entries reviewed. Technical suitability and completeness remain open.",
						"Materialangaben geprüft. Technische Eignung und Vollständigkeit bleiben offen.",
					)}
				</p>
			)}
			{(plan.materials ?? []).map((item) => (
				<div className="lp-selected-profile" key={item.id}>
					<strong>{item.name}</strong>
					{" · "}
					{item.mounting_quantity_basis
						? t("Quantity rule", "Mengenregel")
						: item.quantity === null
							? t("Quantity open", "Menge offen")
							: `${item.quantity} ${item.unit === "piece" ? t("pcs", "Stk.") : "m"}`}
					{item.mounting_quantity_basis && (
						<p>
							{(() => {
								const result = review?.rows.find(
									(row) => row.id === item.id,
								)?.mounting_quantity_result;
								return !result
									? t(
											"Review the installation to calculate the quantity.",
											"Prüfen Sie die Installation, um die Menge zu berechnen.",
										)
									: result.status === "calculated"
										? t(
												`Declared rule: ${result.modules} modules × ${result.per_module} + ${result.segments} occupied row segments × ${result.per_segment} + ${result.adjacencies} neighboring slot pairs × ${result.per_adjacency} = ${result.quantity} pieces`,
												`Angegebene Mengenregel: ${result.modules} Module × ${result.per_module} + ${result.segments} belegte Reihenabschnitte × ${result.per_segment} + ${result.adjacencies} Paare benachbarter Modulplätze × ${result.per_adjacency} = ${result.quantity} Stück`,
											)
										: t(
												"Review the current roof layout and confirm the quantity rule again.",
												"Prüfen Sie die aktuelle Dachplanung und bestätigen Sie die Mengenregel erneut.",
											);
							})()}
						</p>
					)}
					{item.circuit_id !== null &&
						!plan.circuits.some((c) => c.id === item.circuit_id) && (
							<p>
								{t(
									"The linked circuit is no longer available.",
									"Der zugeordnete Stromkreis ist nicht mehr verfügbar.",
								)}
							</p>
						)}
					{review?.rows.find((row) => row.id === item.id)
						?.comparison_result && (
						<p>
							{t("Manufacturer comparison", "Herstellervergleich")}:{" "}
							{(() => {
								const status = review.rows.find((row) => row.id === item.id)!
									.comparison_result!.status;
								const labels: Record<string, [string, string]> = {
									within_recommendation: [
										"Within the recommended cross-section range",
										"Innerhalb des empfohlenen Querschnittsbereichs",
									],
									outside_recommendation: [
										"Outside the recommended cross-section range",
										"Außerhalb des empfohlenen Querschnittsbereichs",
									],
									meets_minimum_values: [
										"Both minimum ratings met",
										"Beide Mindestwerte erfüllt",
									],
									below_minimum_values: [
										"At least one minimum rating not met",
										"Mindestens ein Mindestwert nicht erfüllt",
									],
								};
								return labels[status]
									? t(...labels[status])
									: t(
											"Unavailable: check the circuit, device and current source",
											"Nicht verfügbar: Stromkreis, Gerät und aktuelle Quelle prüfen",
										);
							})()}
						</p>
					)}
					<div className="lp-inline-actions">
						<button
							className="lp-text-button"
							disabled={disabled || editing !== null}
							onClick={() => {
								setShowComparison(Boolean(item.comparison));
								setComparisonChoice(
									item.comparison
										? identity(
												item.comparison.instance_id,
												item.comparison.product_id,
												item.comparison.product_revision,
												item.comparison.fact_id,
												item.comparison.document_id,
												item.comparison.document_revision,
											)
										: "",
								);
								setComparisonConfirmed(false);
								setShowMountingRule(Boolean(item.mounting_quantity_basis));
								setMountingError("");
								setEditing(item);
							}}
						>
							{t("Edit", "Bearbeiten")}
						</button>
						<button
							className="lp-text-button"
							disabled={disabled || editing !== null}
							onClick={() =>
								change(
									readInstallation({
										...plan,
										materials: plan.materials!.filter(
											(row) => row.id !== item.id,
										),
									}),
								)
							}
						>
							{t("Remove", "Entfernen")}
						</button>
					</div>
				</div>
			))}
			{editing === null ? (
				<button
					className="lp-button lp-button-secondary"
					disabled={disabled}
					onClick={() => {
						setShowComparison(false);
						setComparisonChoice("");
						setComparisonConfirmed(false);
						setShowMountingRule(false);
						setMountingError("");
						setEditing("new");
					}}
				>
					{t("Add installation material", "Installationsmaterial hinzufügen")}
				</button>
			) : (
				<GeometryForm
					title={t("Installation material", "Installationsmaterial")}
					locale={locale}
					measurementHelp={false}
					cancel={() => setEditing(null)}
					onValidity={() => {}}
					submit={(v) => {
						setMountingError("");
						const unit = v.text("unit") as InstallationMaterial["unit"];
						const item: InstallationMaterial = {
							id: before?.id ?? installationId("material"),
							name: v.text("name"),
							kind: v.text("kind") as InstallationMaterial["kind"],
							circuit_id: v.text("circuit") || null,
							quantity: v.number("quantity", {
								optional: true,
								positive: true,
								integer: unit === "piece",
							}),
							unit,
							specification: v.text("specification"),
							source_note: v.text("source"),
						};
						const choice = comparisonChoice;
						if (v.text("mounting_array")) {
							const array = geometry.arrays.find(
								(a) => a.id === v.text("mounting_array"),
							);
							const roof = geometry.roofs.find((r) => r.id === array?.roof_id);
							const module = geometry.module_specs.find(
								(m) => m.id === array?.module_spec_id,
							);
							if (
								!array ||
								!roof ||
								!module ||
								!v.checked("mounting_confirmed") ||
								item.kind !== "mounting" ||
								item.unit !== "piece" ||
								item.quantity !== null ||
								choice !== ""
							) {
								setMountingError(
									t(
										"Select a current array, choose mounting material and pieces, leave the fixed quantity and manufacturer comparison empty, and confirm the rule.",
										"Wählen Sie ein aktuelles Modulfeld, Montagematerial und Stück. Lassen Sie die feste Menge und den Herstellervergleich leer und bestätigen Sie die Mengenregel.",
									),
								);
								return false;
							}
							item.mounting_quantity_basis = {
								array,
								roof,
								module,
								conditions_confirmed: true,
								per_module: v.number("per_module", {
									min: 0,
									max: 10000,
									integer: true,
								})!,
								per_segment: v.number("per_segment", {
									min: 0,
									max: 10000,
									integer: true,
								})!,
								per_adjacency: v.number("per_adjacency", {
									min: 0,
									max: 10000,
									integer: true,
								})!,
							};
							if (
								!item.mounting_quantity_basis.per_module &&
								!item.mounting_quantity_basis.per_segment &&
								!item.mounting_quantity_basis.per_adjacency
							) {
								setMountingError(
									t(
										"Enter at least one non-zero count.",
										"Geben Sie mindestens eine Menge größer als null ein.",
									),
								);
								return false;
							}
						}
						if (choice !== "") {
							const selected = activeCandidate;
							if (!selected) throw new Error("source unavailable");
							const circuit = plan.circuits.find(
								(row) => row.id === item.circuit_id,
							);
							if (!circuit) throw new Error("circuit unavailable");
							const pe =
								selected.fact.basis === "manufacturer_recommended_pe_conductor";
							item.comparison = {
								instance_id: selected.instance.id,
								product_id: selected.product.id,
								product_revision: selected.product.product_revision,
								fact_id: String(selected.fact.id),
								document_id: String(selected.source.document_id),
								document_revision: String(selected.source.document_revision),
								cross_section_mm2: pe
									? v.number("cross_section", { positive: true })
									: null,
								rated_current_a: pe
									? null
									: v.number("rated_current", { positive: true }),
								rated_voltage_v: pe
									? null
									: v.number("rated_voltage", { positive: true }),
								conditions_confirmed: comparisonConfirmed,
								circuit_context: {
									id: circuit.id,
									kind: circuit.kind,
									start: circuit.start,
									end: circuit.end,
								},
							};
						}
						return change(
							readInstallation({
								...plan,
								materials: before
									? plan.materials!.map((row) =>
											row.id === before.id ? item : row,
										)
									: [...(plan.materials ?? []), item],
							}),
						);
					}}
				>
					<GeometryText
						name="name"
						label={t("Item name", "Bezeichnung")}
						value={before?.name ?? ""}
					/>
					<label className="lp-field">
						<span>{t("Material type", "Materialart")}</span>
						<select name="kind" required defaultValue={before?.kind ?? ""}>
							<option value="">{t("Choose a type", "Art auswählen")}</option>
							{kinds.map(([value, label]) => (
								<option value={value} key={value}>
									{label}
								</option>
							))}
						</select>
					</label>
					<label className="lp-field">
						<span>
							{t(
								"Linked circuit (optional)",
								"Zugeordneter Stromkreis (optional)",
							)}
						</span>
						<select name="circuit" defaultValue={before?.circuit_id ?? ""}>
							<option value="">
								{t("No circuit linked", "Kein Stromkreis zugeordnet")}
							</option>
							{before?.circuit_id &&
								!plan.circuits.some((c) => c.id === before.circuit_id) && (
									<option value={before.circuit_id}>
										{t(
											"Circuit no longer available",
											"Stromkreis nicht mehr verfügbar",
										)}
									</option>
								)}
							{plan.circuits.map((c) => (
								<option key={c.id} value={c.id}>
									{c.name}
								</option>
							))}
						</select>
					</label>
					<label className="lp-field">
						<span>{t("Unit", "Einheit")}</span>
						<select name="unit" required defaultValue={before?.unit ?? "piece"}>
							<option value="piece">{t("Pieces", "Stück")}</option>
							<option value="m">{t("Metres", "Meter")}</option>
						</select>
					</label>
					<GeometryNumber
						name="quantity"
						label={t("Quantity (optional)", "Menge (optional)")}
						value={before?.quantity}
						locale={locale}
						unit=""
						optional
					/>
					<GeometryText
						name="specification"
						label={t(
							"Declared specification and application",
							"Angegebene Spezifikation und Verwendung",
						)}
						value={before?.specification ?? ""}
						multiline
					/>
					<GeometryText
						name="source"
						label={t(
							"Source of this project declaration",
							"Quelle dieser Projektangabe",
						)}
						value={before?.source_note ?? ""}
						multiline
					/>
					<label className="lp-field">
						<span>
							{t(
								"Calculate mounting pieces from an array (optional)",
								"Montageteile aus einem Modulfeld berechnen (optional)",
							)}
						</span>
						<select
							name="mounting_array"
							defaultValue={before?.mounting_quantity_basis?.array.id ?? ""}
							onChange={(event) =>
								setShowMountingRule(event.currentTarget.value !== "")
							}
						>
							<option value="">
								{t("Enter a quantity manually", "Menge selbst eingeben")}
							</option>
							{before?.mounting_quantity_basis &&
								!geometry.arrays.some(
									(a) => a.id === before.mounting_quantity_basis?.array.id,
								) && (
									<option value={before.mounting_quantity_basis.array.id}>
										{t(
											"Previous array unavailable",
											"Bisheriges Modulfeld nicht verfügbar",
										)}
									</option>
								)}
							{geometry.arrays.map((a) => (
								<option value={a.id} key={a.id}>
									{a.name} ·{" "}
									{geometry.roofs.find((r) => r.id === a.roof_id)?.name}
								</option>
							))}
						</select>
					</label>
					{showMountingRule && (
						<>
							{mountingError && <p role="alert">{mountingError}</p>}
							<p>
								{t(
									"Enter your mounting design's counts for each module, each occupied row segment, and each pair of neighboring occupied slots. Removed slots split segments. If a joint or gap breaks a mounting run, use separate arrays or enter the project quantity manually. Use pieces and leave the fixed quantity empty. The calculation does not check the system, rails, anchors, structural loads or roof suitability.",
									"Geben Sie die Mengen Ihrer Montageplanung je Modul, je belegtem Reihenabschnitt und je Paar benachbarter belegter Modulplätze ein. Entfernte Plätze teilen einen Abschnitt. Unterbricht eine Fuge oder ein Abstand den Montagestrang, verwenden Sie getrennte Modulfelder oder geben Sie die Projektmenge selbst ein. Wählen Sie Stück und lassen Sie die feste Menge leer. Die Berechnung prüft weder System, Schienen, Befestigung, statische Lasten noch die Eignung des Dachs.",
								)}
							</p>
							<GeometryNumber
								name="per_module"
								label={t("Pieces per module", "Stück je Modul")}
								value={before?.mounting_quantity_basis?.per_module ?? 0}
								locale={locale}
								unit=""
							/>
							<GeometryNumber
								name="per_segment"
								label={t(
									"Pieces per continuous row segment",
									"Stück je zusammenhängendem Reihenabschnitt",
								)}
								value={before?.mounting_quantity_basis?.per_segment ?? 0}
								locale={locale}
								unit=""
							/>
							<GeometryNumber
								name="per_adjacency"
								label={t(
									"Pieces per neighboring slot pair",
									"Stück je Paar benachbarter Modulplätze",
								)}
								value={before?.mounting_quantity_basis?.per_adjacency ?? 0}
								locale={locale}
								unit=""
							/>
							<label>
								<input type="checkbox" name="mounting_confirmed" />{" "}
								{t(
									"I confirm these counts and the source above apply to this mounting design and array.",
									"Ich bestätige, dass diese Mengen und die oben genannte Quelle für dieses Montagesystem und Modulfeld gelten.",
								)}
							</label>
						</>
					)}
					<label className="lp-field">
						<span>
							{t(
								"Compare with a manufacturer fact (optional)",
								"Mit Herstellerangabe vergleichen (optional)",
							)}
						</span>
						<select
							name="comparison"
							value={comparisonChoice}
							onChange={(event) => {
								setComparisonChoice(event.currentTarget.value);
								setComparisonConfirmed(false);
								setShowComparison(event.currentTarget.value !== "");
							}}
						>
							<option value="">{t("No comparison", "Kein Vergleich")}</option>
							{comparisonChoice && !activeCandidate && (
								<option value={comparisonChoice}>
									{t(
										"Previously selected source unavailable; select a current source or remove the comparison",
										"Zuvor gewählte Quelle nicht verfügbar; aktuelle Quelle wählen oder Vergleich entfernen",
									)}
								</option>
							)}
							{candidates.map((c) => (
								<option value={candidateKey(c)} key={candidateKey(c)}>
									{c.instance.name} · {c.product.model} · {String(c.fact.id)} ·
									p. {String(c.source.page)}
								</option>
							))}
						</select>
					</label>
					{candidates.map((c) => (
						<p key={`${c.instance.id}-${String(c.fact.id)}-source`}>
							{c.instance.name} · {c.product.model} · {String(c.fact.id)} · p.{" "}
							{String(c.source.page)}: {String(c.source.quote ?? "")}{" "}
							{typeof c.source.url === "string" &&
								c.source.url.startsWith(
									"https://de-linker.com/wp-content/uploads/",
								) && (
									<a href={c.source.url} target="_blank" rel="noreferrer">
										{t("Manufacturer document", "Herstellerdokument")}
									</a>
								)}
						</p>
					))}
					{showComparison && (
						<>
							<p>
								{t(
									"For the selected fact, enter the project's cross-section or both device ratings below. The circuit must connect to the selected device. Other manufacturer conditions and installation approval remain open.",
									"Für die gewählte Herstellerangabe unten den Projektquerschnitt oder beide Gerätenennwerte eingeben. Der Stromkreis muss mit dem gewählten Gerät verbunden sein. Weitere Herstellerbedingungen und die Freigabe der Installation bleiben offen.",
								)}
							</p>
							<label>
								<input
									type="checkbox"
									name="comparison_confirmed"
									checked={comparisonConfirmed}
									disabled={!activeCandidate}
									onChange={(event) =>
										setComparisonConfirmed(event.currentTarget.checked)
									}
								/>{" "}
								{t(
									"I confirm this manufacturer instruction applies to the selected device and circuit.",
									"Ich bestätige, dass diese Herstellerangabe für das gewählte Gerät und den Stromkreis gilt.",
								)}
							</label>
							<GeometryNumber
								name="cross_section"
								label={t(
									"Declared PE cross-section",
									"Angegebener PE-Querschnitt",
								)}
								value={before?.comparison?.cross_section_mm2}
								locale={locale}
								unit="mm²"
								optional
							/>
							<GeometryNumber
								name="rated_current"
								label={t(
									"Declared device rated current",
									"Angegebener Gerätenennstrom",
								)}
								value={before?.comparison?.rated_current_a}
								locale={locale}
								unit="A"
								optional
							/>
							<GeometryNumber
								name="rated_voltage"
								label={t(
									"Declared device rated voltage",
									"Angegebene Gerätenennspannung",
								)}
								value={before?.comparison?.rated_voltage_v}
								locale={locale}
								unit="V"
								optional
							/>
						</>
					)}
				</GeometryForm>
			)}
		</section>
	);
}
