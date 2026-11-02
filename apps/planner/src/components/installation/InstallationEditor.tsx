import { ElectricalResults } from "./ElectricalResults.tsx";
import { ConductorManufacturerResults } from "./ConductorManufacturerResults.tsx";
import { ReferenceCurrentResults } from "./ReferenceCurrentResults.tsx";
import { electricalText } from "./ElectricalConditionFields.tsx";
import { useEffect, useRef, useState } from "react";
import type { GeometryDocument, Vec3 } from "../../domain/geometry.ts";
import type { GeometryCommand } from "../../domain/geometryCommands.ts";
import type {
	InstallationInputs,
	InstallationReview,
} from "../../domain/installation.ts";
import {
	readInstallation,
	readInstallationReview,
} from "../../domain/installation.ts";
import { sameJson } from "../../domain/draft.ts";
import { formatDecimal } from "../../domain/decimal.ts";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import type { JsonObject, Session } from "../../data/protocol.ts";
import { ApiError } from "../../data/protocol.ts";
import { readObject } from "../../data/readProtocol.ts";
import { useEquipmentProducts } from "../../data/equipmentProducts.ts";
import { panelPoses } from "../../domain/panelPoses.ts";
import { __ } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";
import { NetworkViewport } from "./NetworkViewport.tsx";
import {
	InstanceForm,
	CircuitForm,
	RouteForm,
	CableForm,
} from "./NetworkForms.tsx";
import { LazySceneViewport } from "../design/LazySceneViewport.tsx";
import {
	GeometryForm,
	GeometryText,
	GeometryNumber,
} from "../design/GeometryForm.tsx";
import { manualSource } from "../../domain/geometryEditing.ts";
import { installationId } from "../../domain/installation.ts";
import { readPvStringPlan } from "../../domain/pvStrings.ts";
import { readPvPlantStringPlan } from "../../domain/pvPlantStrings.ts";
import type { PvPlantStringPlan } from "../../domain/pvPlantStrings.ts";
import { readEquipmentPlant } from "../../domain/equipmentPlant.ts";
import type { PvStringPlan } from "../../domain/pvStrings.ts";
import { PvStringLinks } from "./PvStringLinks.tsx";
import { conductorLabel } from "./installationLabels.ts";
import { TerminalResults } from "./TerminalResults.tsx";
import { InstallationMaterials } from "./InstallationMaterials.tsx";
import { hasTerminalFeature } from "../../domain/installationTerminals.ts";

type Kind = "instances" | "circuits" | "routes" | "cable_runs";
const reason = (code: string) =>
	(
		({
			layout_confirmation_required: __(
				"Confirm against the current layout",
				"linker-tools",
			),
			source_missing: __(
				"Measurement or drawing source missing",
				"linker-tools",
			),
			source_export_unconfirmed: __(
				"Source export permission unconfirmed",
				"linker-tools",
			),
			route_endpoints_differ: __(
				"Route endpoints differ from the saved connection points",
				"linker-tools",
			),
			height_missing: __("Elevation missing", "linker-tools"),
			extra_length_unconfirmed: __(
				"Extra length or its basis is missing",
				"linker-tools",
			),
			route_length_not_positive: __(
				"A positive route length is required",
				"linker-tools",
			),
		}) as Record<string, string>
	)[code] ?? __("Input needs attention", "linker-tools");
export function InstallationEditor({
	inputs,
	savedInputs,
	savedRevision,
	geometry,
	client,
	session,
	projectId,
	locale,
	sceneModuleUrl,
	change,
	onValidity,
	editGeometry,
}: {
	inputs: JsonObject;
	savedInputs: JsonObject;
	savedRevision: number;
	geometry: GeometryDocument;
	client: PlannerClient;
	session: Session;
	projectId: string;
	locale: string;
	sceneModuleUrl: string | null;
	change: (value: InstallationInputs) => boolean;
	onValidity: (valid: boolean) => void;
	editGeometry: (command: GeometryCommand) => boolean;
}) {
	const plan = readInstallation(inputs.installation);
	const savedInstallation = readInstallation(savedInputs.installation);
	const savedStringInput =
		savedInputs.pv_plant_string_plan === undefined
			? savedInputs.pv_string_plan
			: {
					plan: savedInputs.pv_plant_string_plan,
					plant: savedInputs.equipment_plant,
				};
	const currentStringInput =
		inputs.pv_plant_string_plan === undefined
			? inputs.pv_string_plan
			: { plan: inputs.pv_plant_string_plan, plant: inputs.equipment_plant };
	let savedStrings: PvStringPlan | PvPlantStringPlan | null = null;
	try {
		if (savedInputs.pv_plant_string_plan !== undefined)
			savedStrings = readPvPlantStringPlan(savedInputs.pv_plant_string_plan);
		else if (savedInputs.pv_string_plan !== undefined)
			savedStrings = readPvStringPlan(savedInputs.pv_string_plan);
	} catch {
		// Preserve the declaration; it must be corrected in the string editor.
	}
	const stringPlanChanged = !sameJson(currentStringInput, savedStringInput);
	const products = useEquipmentProducts(client, session.query_scope, true);
	const [form, setForm] = useState<{ kind: Kind; id: string | null } | null>(
			null,
		),
		[view, setView] = useState<"plan" | "3d">("plan"),
		[newSource, setNewSource] = useState(false);
	const [review, setReview] = useState<InstallationReview | null>(null),
		[reviewGeometry, setReviewGeometry] = useState<GeometryDocument | null>(
			null,
		),
		[busy, setBusy] = useState(false),
		[failed, setFailed] = useState(false),
		[conflicted, setConflicted] = useState(false),
		[linksValid, setLinksValid] = useState(true),
		[materialsValid, setMaterialsValid] = useState(true),
		[reviewStrings, setReviewStrings] = useState<unknown>(null),
		[reviewContext, setReviewContext] = useState<{
			projectId: string;
			queryScope: string;
			revision: number;
		} | null>(null);
	const latest = useRef({
		projectId,
		queryScope: session.query_scope,
		savedRevision,
		plan,
		geometry,
		strings: savedStringInput,
		draftStrings: currentStringInput,
	});
	latest.current = {
		projectId,
		queryScope: session.query_scope,
		savedRevision,
		plan,
		geometry,
		strings: savedStringInput,
		draftStrings: currentStringInput,
	};
	const active = useRef(true);
	useEffect(() => {
		active.current = true;
		return () => {
			active.current = false;
		};
	}, []);
	useEffect(() => {
		onValidity(form === null && !newSource && linksValid && materialsValid);
		return () => onValidity(true);
	}, [form, newSource, linksValid, materialsValid, onValidity]);
	// Saving the prepared inputs advances the revision without changing the
	// accepted review basis. Pending replies still require the exact revision.
	const shown =
		review &&
		reviewContext &&
		reviewContext.projectId === projectId &&
		reviewContext.queryScope === session.query_scope &&
		client.isCurrentScope(reviewContext.queryScope) &&
		reviewContext.revision <= savedRevision &&
		sameJson(plan, review.prepared_inputs) &&
		sameJson(geometry, reviewGeometry) &&
		((plan.pv_string_links === undefined &&
			savedInputs.pv_plant_string_plan === undefined) ||
			(!stringPlanChanged && sameJson(reviewStrings, savedStringInput)))
			? review
			: null;
	function edit(kind: Kind, row: unknown): boolean {
		try {
			const id = readObject(row).id;
			const existing = plan[kind].some((old) => old.id === id);
			const next = readInstallation({
				...plan,

				[kind]: existing
					? plan[kind].map((old) => (old.id === id ? row : old))
					: [...plan[kind], row],
			});
			const ok = change(next);
			if (ok) {
				setForm(null);
				setFailed(false);
			}
			return ok;
		} catch {
			setFailed(true);
			return false;
		}
	}
	function remove(kind: Kind, id: string) {
		try {
			change(
				readInstallation({
					...plan,

					[kind]: plan[kind].filter((p) => p.id !== id),
				}),
			);
		} catch {
			setFailed(true);
		}
	}
	async function check() {
		if (busy) return;
		const before = {
			projectId,
			queryScope: session.query_scope,
			savedRevision,
			plan,
			geometry,
			strings: savedStringInput,
			draftStrings: currentStringInput,
		};
		setBusy(true);
		setFailed(false);
		setConflicted(false);
		try {
			const raw = await client.query(
				"installation/review",
				{
					schema_version: 1,
					project_id: projectId,
					expected_revision: savedRevision,
					geometry: readObject(geometry),
					installation: readObject(plan),
					bind_geometry: true,
				},
				session.query_scope,
			);
			if (
				!active.current ||
				!client.isCurrentScope(session.query_scope) ||
				!sameJson(before, latest.current)
			)
				return;
			const result = readInstallationReview(
				raw,
				plan,
				projectId,
				savedStrings,
				savedRevision,
				savedInputs.equipment_plant === undefined
					? null
					: readEquipmentPlant(savedInputs.equipment_plant),
			);
			if (!change(result.prepared_inputs)) throw new Error("not_applied");
			setReview(result);
			setReviewGeometry(geometry);
			setReviewStrings(savedStringInput);
			setReviewContext({
				projectId,
				queryScope: session.query_scope,
				revision: savedRevision,
			});
		} catch (error) {
			if (
				active.current &&
				client.isCurrentScope(session.query_scope) &&
				sameJson(before, latest.current)
			) {
				if (
					error instanceof ApiError &&
					error.status === 409 &&
					error.code === "conflict"
				)
					setConflicted(true);
				else setFailed(true);
			}
		} finally {
			if (active.current) setBusy(false);
		}
	}
	const headings: Record<Kind, string> = {
		instances: __("Physical devices and site connections", "linker-tools"),
		circuits: __("Circuits", "linker-tools"),
		routes: __("Recorded routes", "linker-tools"),
		cable_runs: __("Physical cables and conductors", "linker-tools"),
	};
	const addLabels: Record<Kind, string> = {
		instances: __("Add device or site connection", "linker-tools"),
		circuits: __("Add circuit", "linker-tools"),
		routes: __("Add route", "linker-tools"),
		cable_runs: __("Add cable or conductor", "linker-tools"),
	};
	const common = {
		locale,
		geometry,
		plan,
		cancel: () => setForm(null),
		onValidity: () => {},
	};
	const paths = plan.routes
		.filter((r) => r.points.every((p) => p.height_m !== null))
		.map((r) =>
			r.points.map((p) => [p.east_m, p.north_m, p.height_m!] as Vec3),
		);
	return (
		<section
			className="lp-focus-target"
			id="lp-installation"
			tabIndex={-1}
			aria-labelledby="lp-installation-title"
		>
			<header className="lp-section-title">
				<span className="lp-index">09</span>
				<div>
					<h2 id="lp-installation-title">
						{__("Installation routing", "linker-tools")}
					</h2>
					<p>
						{__(
							"Place the devices and connection points, record the routes, then calculate cable and conductor lengths. Save the project to include these inputs in a planning report.",
							"linker-tools",
						)}
					</p>
				</div>
			</header>
			<Notice>
				{__(
					"This step calculates lengths from the positions and routes you record. Cable sizing, protection, earthing, mounting, connector matching and country requirements remain separate engineering checks.",
					"linker-tools",
				)}
			</Notice>
			{!geometry.sources.length && (
				<Notice>
					{__(
						"Add the source of your site measurements or drawing before recording positions. A roof layout is optional.",
						"linker-tools",
					)}
				</Notice>
			)}
			{failed && (
				<Notice error>
					{__(
						"Installation quantities could not be confirmed. Check the device data, sources and route inputs; your recorded work remains available.",
						"linker-tools",
					)}
				</Notice>
			)}
			{conflicted && (
				<Notice error>
					{__(
						"The saved project changed. Your edits remain open. Reopen the project before reviewing routes or string links.",
						"linker-tools",
					)}
				</Notice>
			)}
			{(products.isError || products.isFetching) && (
				<Notice error={products.isError}>
					{electricalText(
						locale,
						products.isFetching
							? "Loading current product and cable data…"
							: "Current product and cable data are unavailable. Saved declarations remain available; reload before choosing new references.",
						products.isFetching
							? "Aktuelle Produkt- und Kabeldaten werden geladen…"
							: "Aktuelle Produkt- und Kabeldaten sind nicht verfügbar. Gespeicherte Angaben bleiben erhalten; laden Sie die Daten vor der Auswahl neuer Referenzen erneut.",
					)}
				</Notice>
			)}
			{products.error && (
				<button
					className="lp-text-button"
					onClick={() => void products.refetch()}
				>
					{__("Reload product data", "linker-tools")}
				</button>
			)}

			{newSource ? (
				<GeometryForm
					title={__("Measurement or drawing source", "linker-tools")}
					locale={locale}
					cancel={() => setNewSource(false)}
					onValidity={() => {}}
					submit={(v) => {
						if (!v.checked("rights")) return false;
						const source = {
							...manualSource(
								installationId("source"),
								v.text("note"),
								v.text("rights_note"),
							),
							kind: v.text("kind") as "user_measurement" | "user_drawing",
							spatial_precision_m: v.number("precision", {
								optional: true,
								min: 0,
							}),
							calibration_note:
								v.text("conditions") || __("Not recorded.", "linker-tools"),
							permissions: {
								derive: "permitted" as const,
								retain: "permitted" as const,
								export: "permitted" as const,
							},
						};
						if (
							!editGeometry({ type: "put_source", before: null, value: source })
						)
							return false;
						setNewSource(false);
						return true;
					}}
				>
					<GeometryText
						name="note"
						label={__("Source reference", "linker-tools")}
						value=""
						multiline
					/>
					<label className="lp-field">
						<span>{__("Source type", "linker-tools")}</span>
						<select name="kind" required defaultValue="">
							<option value="">
								{__("Choose a source type", "linker-tools")}
							</option>
							<option value="user_measurement">
								{__("Site measurement", "linker-tools")}
							</option>
							<option value="user_drawing">
								{__("Project drawing", "linker-tools")}
							</option>
						</select>
					</label>
					<GeometryNumber
						name="precision"
						label={__("Declared spatial precision", "linker-tools")}
						locale={locale}
						optional
					/>
					<GeometryText
						name="conditions"
						label={__("Calibration and measurement conditions", "linker-tools")}
						value=""
						optional
						multiline
					/>
					<GeometryText
						name="rights_note"
						label={__("Permission or licence basis", "linker-tools")}
						value=""
						multiline
					/>
					<label className="lp-check">
						<input name="rights" type="checkbox" required />
						{__(
							"I may save, use and export these project measurements or drawing data.",
							"linker-tools",
						)}
					</label>
				</GeometryForm>
			) : form ? (
				form.kind === "instances" ? (
					<InstanceForm
						{...common}
						instance={plan.instances.find((d) => d.id === form.id) ?? null}
						products={
							products.isError || products.isFetching
								? []
								: (products.data?.products ?? [])
						}
						submit={(v) => edit("instances", v)}
					/>
				) : form.kind === "circuits" ? (
					<CircuitForm
						{...common}
						circuit={plan.circuits.find((d) => d.id === form.id) ?? null}
						submit={(v) => edit("circuits", v)}
					/>
				) : form.kind === "routes" ? (
					<RouteForm
						{...common}
						route={plan.routes.find((d) => d.id === form.id) ?? null}
						submit={(v) => edit("routes", v)}
					/>
				) : (
					<CableForm
						{...common}
						cable={plan.cable_runs.find((d) => d.id === form.id) ?? null}
						products={
							products.isError || products.isFetching
								? []
								: (products.data?.products ?? [])
						}
						cableReferences={
							products.isError || products.isFetching
								? []
								: (products.data?.cableReferences ?? [])
						}
						submit={(v) => edit("cable_runs", v)}
					/>
				)
			) : (
				<>
					<button
						type="button"
						className="lp-text-button"
						disabled={!linksValid || !materialsValid}
						onClick={() => setNewSource(true)}
					>
						{__("Add measurement or drawing source", "linker-tools")}
					</button>
					<div className="lp-inline-actions">
						<button
							className="lp-text-button"
							aria-pressed={view === "plan"}
							onClick={() => setView("plan")}
						>
							{__("Plan view", "linker-tools")}
						</button>
						<button
							className="lp-text-button"
							aria-pressed={view === "3d"}
							onClick={() => setView("3d")}
						>
							{__("3D view", "linker-tools")}
						</button>
					</div>
					{view === "plan" ? (
						<NetworkViewport geometry={geometry} plan={plan} />
					) : (
						<LazySceneViewport
							sceneModuleUrl={sceneModuleUrl}
							document={geometry}
							poses={panelPoses(geometry)}
							routes={paths}
							selected={null}
							select={() => {}}
							commit={() => false}
							disabled
						/>
					)}
					{(Object.keys(headings) as Kind[]).map((kind) => (
						<section className="lp-scenario-block" key={kind}>
							<h3>{headings[kind]}</h3>
							{plan[kind].map((row) => {
								const dependent =
									kind === "instances"
										? plan.circuits.some((c) =>
												[c.start.instance_id, c.end.instance_id].includes(
													row.id,
												),
											)
										: kind === "circuits"
											? plan.cable_runs.some((c) => c.circuit_id === row.id)
											: kind === "routes"
												? plan.cable_runs.some((c) => c.route_id === row.id)
												: false;
								return (
									<div className="lp-selected-profile" key={row.id}>
										<strong>{row.name}</strong>
										<div className="lp-inline-actions">
											<button
												className="lp-text-button"
												disabled={!linksValid || !materialsValid}
												onClick={() => setForm({ kind, id: row.id })}
											>
												{__("Edit", "linker-tools")}
											</button>
											<button
												className="lp-text-button"
												disabled={dependent || !linksValid || !materialsValid}
												title={
													dependent
														? __(
																"Remove linked connections first",
																"linker-tools",
															)
														: undefined
												}
												onClick={() => remove(kind, row.id)}
											>
												{__("Remove", "linker-tools")}
											</button>
											{kind === "instances" &&
												"product_id" in row &&
												row.product_id !== null &&
												products.data?.products.some(
													(p) =>
														p.id === row.product_id &&
														p.product_revision !== row.product_revision,
												) && (
													<button
														className="lp-text-button"
														disabled={!linksValid || !materialsValid}
														onClick={() => {
															const p = products.data!.products.find(
																(p) => p.id === row.product_id,
															)!;
															edit("instances", {
																...row,
																product_revision: p.product_revision,
															});
														}}
													>
														{__("Use current product data", "linker-tools")}
													</button>
												)}
										</div>
									</div>
								);
							})}
							<button
								className="lp-button lp-button-secondary"
								disabled={
									!linksValid ||
									!materialsValid ||
									!geometry.sources.length ||
									(kind === "instances"
										? products.isFetching || !products.data?.prepared
										: kind === "circuits"
											? plan.instances.length === 0
											: kind === "routes"
												? plan.circuits.length === 0
												: !plan.circuits.length || !plan.routes.length)
								}
								onClick={() => setForm({ kind, id: null })}
							>
								{addLabels[kind]}
							</button>
						</section>
					))}
					<InstallationMaterials
						plan={plan}
						products={products.data?.products ?? []}
						review={shown?.material_review}
						locale={locale}
						disabled={busy || !linksValid}
						change={change}
						onValidity={setMaterialsValid}
					/>
					<PvStringLinks
						plan={plan}
						savedInstallation={savedInstallation}
						savedStrings={savedStrings}
						stringPlanChanged={stringPlanChanged}
						review={shown?.pv_string_reconciliation ?? null}
						locale={locale}
						disabled={busy || !materialsValid}
						change={change}
						onValidity={setLinksValid}
					/>
					<button
						className="lp-button"
						disabled={
							busy ||
							!linksValid ||
							!materialsValid ||
							(!plan.cable_runs.length &&
								!plan.circuits.some((c) => c.operating_conditions?.length) &&
								!hasTerminalFeature(plan) &&
								!plan.materials?.length &&
								plan.pv_string_links === undefined &&
								savedInputs.pv_plant_string_plan === undefined) ||
							((plan.pv_string_links !== undefined ||
								savedInputs.pv_plant_string_plan !== undefined) &&
								stringPlanChanged)
						}
						onClick={() => void check()}
					>
						{busy
							? __("Checking…", "linker-tools")
							: hasTerminalFeature(plan)
								? electricalText(
										locale,
										"Review installation",
										"Installation prüfen",
									)
								: plan.pv_string_links !== undefined
									? __("Review routes and string links", "linker-tools")
									: electricalText(
											locale,
											"Review routes and circuit conditions",
											"Strecken und Betriebsbedingungen prüfen",
										)}
					</button>
					{shown?.terminal_assessment && (
						<TerminalResults
							review={shown.terminal_assessment}
							plan={plan}
							locale={locale}
						/>
					)}
					{shown?.electrical && (
						<>
							<ElectricalResults review={shown.electrical} locale={locale} />
							<ReferenceCurrentResults
								review={shown.electrical}
								cables={shown.cables}
								locale={locale}
							/>
						</>
					)}
					{shown && (
						<ConductorManufacturerResults
							cables={shown.cables}
							locale={locale}
						/>
					)}
					{shown && shown.cables.length > 0 && (
						<div className="lp-table-scroll" tabIndex={0}>
							<table className="lp-data-table">
								<thead>
									<tr>
										<th>{__("Name", "linker-tools")}</th>
										<th>{__("Calculated length (m)", "linker-tools")}</th>
										<th>{__("Quantity basis", "linker-tools")}</th>
										<th>{__("Conductor", "linker-tools")}</th>
									</tr>
								</thead>
								<tbody>
									{shown.cables.map((c) => (
										<tr key={c.id}>
											<td>{c.name}</td>
											<td>
												{c.quantity === null
													? "—"
													: formatDecimal(c.quantity, locale)}
											</td>
											<td>
												{c.reasons.length
													? c.reasons.map(reason).join("; ")
													: `${formatDecimal(c.route_length_m, locale)} + ${formatDecimal(c.extra_length_m, locale)}`}
											</td>
											<td>{conductorLabel(c.conductor, locale)}</td>
										</tr>
									))}
								</tbody>
							</table>
						</div>
					)}
				</>
			)}
		</section>
	);
}
