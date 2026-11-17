import { useQuery } from "@tanstack/react-query";
import { readPlaceImagery } from "../../domain/place.ts";
import type { PointerEvent as ReactPointerEvent } from "react";
import { useEffect, useRef, useState } from "react";
import type { JsonObject, Session } from "../../data/protocol.ts";
import type { Configuration } from "../../data/config.ts";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import { useModuleTemplates } from "../../data/useModuleTemplates.ts";
import type {
	GeometryDocument,
	ModuleSpec,
	Vec2,
} from "../../domain/geometry.ts";
import {
	applyGeometryCommand,
	emptyGeometry,
	roofDependents,
} from "../../domain/geometryCommands.ts";
import type { GeometryCommand } from "../../domain/geometryCommands.ts";
import { manualSource, rectangularRoof } from "../../domain/geometryEditing.ts";
import { readGeometry } from "../../domain/validateGeometry.ts";
import {
	attachGeometryImport,
	readGeometryImports,
} from "../../domain/geometryImports.ts";
import { GeometryIntake } from "../design/GeometryIntake.tsx";
import policy from "../../contracts/geometry-policy.json" with { type: "json" };
import { moduleSummary, panelPoses } from "../../domain/panelPoses.ts";
import { readObject } from "../../data/readProtocol.ts";
import {
	referenceDraft,
	referenceInputs,
	KNOWN_PV_MODEL,
	REFERENCE_DATABASES,
	REFERENCE_TECHNOLOGIES,
	type PvgisReferenceDraft,
} from "../../domain/pvgisReference.ts";
import { invalidateEnergyReplay } from "../../domain/energyScenario.ts";
import { readBrief } from "../../domain/brief.ts";
import { LazySceneViewport } from "../design/LazySceneViewport.tsx";
import { LazyMapViewport } from "../design/LazyMapViewport.tsx";
import type { MapCamera } from "../design/MapViewport.tsx";
import {
	mapPolygon,
	newMapShapeCommand,
	readMapPolygon,
} from "../../domain/mapDrawingGeometry.ts";
import type { MapInteraction } from "../../data/mapInteraction.ts";
import { __ } from "../../i18n.ts";

export interface SolarInstallationProps {
	inputs: JsonObject;
	config: Configuration;
	client: PlannerClient;
	session: Session;
	disabled: boolean;
	edit: (op: (inputs: JsonObject) => JsonObject) => boolean;
	next: () => void;
	initialMap?: boolean;
	onEditing?: (editing: boolean) => void;
	geometryImport?: {
		projectId: string;
		recheck: () => void;
		confirmedInputs: JsonObject;
		onActivity: (open: boolean) => void;
		recoveryScopes?: readonly string[] | undefined;
		recoveryChecking?: boolean | undefined;
	};
}
const id = () => "solar_" + crypto.randomUUID();
export function SolarInstallation({
	inputs,
	config,
	client,
	session,
	disabled,
	edit,
	next,
	initialMap = false,
	onEditing,
	geometryImport,
}: SolarInstallationProps) {
	const geometry =
		inputs.geometry === undefined
			? emptyGeometry()
			: readGeometry(inputs.geometry, policy);
	const reference = referenceDraft(inputs);
	const [mode, setMode] = useState<"known" | "roof">(
		initialMap || (reference.model !== KNOWN_PV_MODEL && geometry.roofs.length)
			? "roof"
			: "known",
	);
	const templates = useModuleTemplates(client, session.query_scope, !disabled);
	const [moduleId, setModuleId] = useState(geometry.module_specs[0]?.id ?? "");
	const module =
		geometry.module_specs.find((m) => m.id === moduleId) ??
		templates.data?.find((t) => t.specification.id === moduleId)?.specification;
	const known =
		reference.model === KNOWN_PV_MODEL ? reference.arrays?.[0] : undefined;
	const [count, setCount] = useState("");
	const [selected, select] = useState<string | null>(
		geometry.roofs[0]?.id ?? null,
	);
	const [tool, setTool] = useState<"select" | "roof" | "obstacle" | "modules">(
		"select",
	);
	const [error, setError] = useState("");
	const [view, setView] = useState<"plan" | "map" | "scene">(
		initialMap ? "map" : "plan",
	);
	const map = view === "map";
	useEffect(
		() => onEditing?.(mode === "roof" && tool !== "select"),
		[mode, tool, onEditing],
	);
	const camera = useRef<MapCamera | null>(null);
	const [vertices, setVertices] = useState<readonly Vec2[]>([]);
	const [drawingKey, setDrawingKey] = useState(() => crypto.randomUUID());
	const [undo, setUndo] = useState<readonly GeometryDocument[]>([]);
	const [fields, setFields] = useState({
		width: "",
		depth: "",
		pitch: "",
		azimuth: "",
		height: "",
		source: "",
		rows: "",
		columns: "",
		gap: "",
		obstacleHeight: "",
		originU: "",
		originV: "",
	});
	const [confirmed, setConfirmed] = useState(false);
	const roof =
		geometry.roofs.find((r) => r.id === selected) ??
		geometry.roofs.find(
			(r) =>
				geometry.arrays.some((a) => a.id === selected && a.roof_id === r.id) ||
				geometry.obstacles.some((o) => o.id === selected && o.roof_id === r.id),
		) ??
		geometry.roofs[0];
	const poses = panelPoses(geometry);
	const summary = moduleSummary(geometry);
	const blocked = disabled || !client.isCurrentScope(session.query_scope);
	const mapReferenced =
		geometry.coordinate_system.anchor !== null &&
		geometry.coordinate_system.north_reference === "true_north";
	const numeric = (key: keyof typeof fields) => {
		const value = fields[key].trim() ? Number(fields[key]) : NaN;
		if (!Number.isFinite(value))
			throw new Error(
				__(
					"Enter the dimensions, orientation and source for this drawing.",
					"linker-tools",
				),
			);
		return value;
	};
	function commit(command: GeometryCommand) {
		if (blocked) return false;
		try {
			const ok = edit((current) => {
				const before =
					current.geometry === undefined
						? emptyGeometry()
						: readGeometry(current.geometry, policy);
				return {
					...invalidateEnergyReplay(current),
					geometry: readObject(applyGeometryCommand(before, command)),
				};
			});
			if (ok) {
				setUndo((previous) => [...previous, geometry]);
				setError("");
			}
			return ok;
		} catch {
			setError(
				__(
					"This edit could not be applied. Check the selected roof and dimensions.",
					"linker-tools",
				),
			);
			return false;
		}
	}
	function chooseModule(spec: ModuleSpec) {
		const existing = geometry.module_specs.find((m) => m.id === spec.id);
		if (!existing && !commit({ type: "put_module", before: null, value: spec }))
			return;
		setModuleId(spec.id);
		if (
			mode === "known" &&
			Number.isSafeInteger(Number(count)) &&
			Number(count) > 0
		) {
			knownChange({
				peak_power_kwp: (Number(count) * (existing ?? spec).stc_power_w) / 1000,
			});
		}
	}
	function knownChange(patch: JsonObject) {
		if (blocked) return;
		edit((current) => {
			const draft = referenceDraft(current);
			const existing =
				draft.model === KNOWN_PV_MODEL ? (draft.arrays ?? []) : [];
			const first = existing[0] ?? {
				id: id(),
				peak_power_kwp: null,
				tilt_deg: null,
				azimuth_north_clockwise_deg: null,
				source_note: "",
			};
			return referenceInputs(current, {
				...draft,
				model: KNOWN_PV_MODEL,
				arrays: [{ ...first, ...patch }, ...existing.slice(1)],
			});
		});
	}
	function roofReferenceInputs(
		current: JsonObject,
		patch: Partial<PvgisReferenceDraft> = {},
	) {
		const { arrays: _known, ...settings } = referenceDraft(current);
		return referenceInputs(current, {
			...settings,
			...patch,
			model: "pvgis_5_3_roof_ac_reference_v1",
		});
	}
	function referenceChange(patch: Partial<PvgisReferenceDraft>, method = mode) {
		if (blocked) return;
		edit((current) => {
			if (method === "roof") return roofReferenceInputs(current, patch);
			const { arrays, ...settings } = referenceDraft(current);
			return referenceInputs(current, {
				...settings,
				...patch,
				model: KNOWN_PV_MODEL,
				arrays: arrays?.length
					? arrays
					: [
							{
								id: id(),
								peak_power_kwp: null,
								tilt_deg: null,
								azimuth_north_clockwise_deg: null,
								source_note: "",
							},
						],
			});
		});
	}
	function coordinateChange(
		key: "latitude" | "longitude",
		value: number | null,
	) {
		if (blocked) return;
		edit((current) => {
			const brief = readBrief(current.brief);
			const site = { ...brief.site, [key]: value };
			return {
				...invalidateEnergyReplay(current),
				brief: {
					...brief,
					site: {
						...site,
						coordinate_basis:
							site.latitude === null || site.longitude === null
								? "not_provided"
								: "user_entered",
					},
				},
			};
		});
	}
	function confirmMapReference() {
		try {
			const site = readBrief(inputs.brief).site;
			if (
				site.coordinate_basis !== "user_entered" ||
				site.latitude === null ||
				site.longitude === null ||
				geometry.coordinate_system.anchor
			)
				return;
			if (!confirmed || !fields.source.trim())
				throw new Error(
					__(
						"Confirm the drawing source before setting the map reference.",
						"linker-tools",
					),
				);
			const source = manualSource(
				id(),
				fields.source.trim(),
				fields.source.trim(),
			);
			commit({
				type: "group",
				before: geometry,
				edits: [
					{ type: "put_source", before: null, value: source },
					{
						type: "set_coordinate_system",
						before: geometry.coordinate_system,
						value: {
							...geometry.coordinate_system,
							anchor: {
								latitude_deg: site.latitude,
								longitude_deg: site.longitude,
								source_id: source.id,
								datum: "EPSG:4326",
							},
							north_reference: "true_north",
							north_source_id: source.id,
						},
					},
				],
			});
		} catch (cause) {
			setError(
				cause instanceof Error
					? cause.message
					: __("Check the project coordinates.", "linker-tools"),
			);
		}
	}
	function addRoof(points?: readonly Vec2[]) {
		try {
			if (!confirmed || !fields.source.trim())
				throw new Error(
					__(
						"Confirm the drawing source before adding a roof.",
						"linker-tools",
					),
				);
			const source = manualSource(
				id(),
				fields.source.trim(),
				fields.source.trim(),
			);
			const identity = {
				id: id(),
				name: `${__("Roof", "linker-tools")} ${geometry.roofs.length + 1}`,
				source_id: source.id,
			};
			const withSource = applyGeometryCommand(geometry, {
				type: "put_source",
				before: null,
				value: source,
			});
			const command: GeometryCommand = points
				? newMapShapeCommand(
						withSource,
						{
							kind: "roof",
							identity,
							pitch_deg: numeric("pitch"),
							bearing_deg: numeric("azimuth"),
							height_reference_position: points[0]!,
							reference_height_m: numeric("height"),
						},
						mapPolygon(points),
					)
				: {
						type: "put_roof",
						before: null,
						value: rectangularRoof(identity, {
							width: numeric("width"),
							slopeLength: numeric("depth"),
							pitch: numeric("pitch"),
							bearing: numeric("azimuth"),
							origin: [
								numeric("originU"),
								numeric("originV"),
								numeric("height"),
							],
						}),
					};
			const edits = command.type === "group" ? command.edits : [command];
			if (
				commit({
					type: "group",
					before: geometry,
					edits: [
						{ type: "put_source", before: null, value: source },
						...edits,
					],
				})
			) {
				select(identity.id);
				setVertices([]);
				setTool("select");
			}
		} catch (cause) {
			setError(
				cause instanceof Error
					? cause.message
					: __("Check the roof inputs.", "linker-tools"),
			);
		}
	}
	function addObstacle(points?: readonly Vec2[]) {
		try {
			if (!roof) return;
			const u = points ? 0 : numeric("originU"),
				v = points ? 0 : numeric("originV"),
				width = points ? 0 : numeric("width"),
				depth = points ? 0 : numeric("depth");
			const value = {
				id: id(),
				name: __("Obstacle", "linker-tools"),
				roof_id: roof.id,
				source_id: roof.source_id,
				height_m: numeric("obstacleHeight"),
				extrusion_axis_enu: [0, 0, 1] as const,
			};
			const command: GeometryCommand = points
				? newMapShapeCommand(
						geometry,
						{ kind: "obstacle", value },
						mapPolygon(points),
					)
				: {
						type: "put_obstacle",
						before: null,
						value: {
							...value,
							footprint_uv: [
								[u, v],
								[u + width, v],
								[u + width, v + depth],
								[u, v + depth],
							],
						},
					};
			if (commit(command)) {
				select(value.id);
				setTool("select");
				setVertices([]);
			}
		} catch (cause) {
			setError(
				cause instanceof Error
					? cause.message
					: __("Check the obstacle inputs.", "linker-tools"),
			);
		}
	}
	function placeModules(point?: Vec2) {
		try {
			if (!roof || !module) return;
			const value = {
				id: id(),
				name: __("Module group", "linker-tools"),
				source_id: roof.source_id,
				roof_id: roof.id,
				module_spec_id: module.id,
				origin_uv: point ?? ([numeric("originU"), numeric("originV")] as Vec2),
				rotation_deg: 0,
				mount_tilt_deg: 0,
				lower_edge_clearance_m: 0,
				rows: numeric("rows"),
				columns: numeric("columns"),
				column_gap_m: numeric("gap"),
				row_gap_m: numeric("gap"),
				excluded_slots: [],
				mounting_note: __(
					"Modules follow the roof plane at the declared spacing.",
					"linker-tools",
				),
			};
			if (commit({ type: "put_array", before: null, value })) {
				select(value.id);
				setTool("select");
			}
		} catch (cause) {
			setError(
				cause instanceof Error
					? cause.message
					: __("Check the module group inputs.", "linker-tools"),
			);
		}
	}
	function removeSelected() {
		if (!selected) return;
		commit(
			geometry.roofs.some((r) => r.id === selected)
				? {
						type: "delete_roof",
						id: selected,
						expected_dependents: roofDependents(geometry, selected),
					}
				: { type: "delete_object", id: selected },
		);
		select(null);
	}
	const interaction: MapInteraction | null =
		map && mapReferenced && (tool === "roof" || (tool === "obstacle" && roof))
			? {
					key: drawingKey,
					phase: "collecting",
					vertices,
					referencePosition: vertices[0] ?? null,
					append: (point) =>
						setVertices((previous) => {
							if (
								previous.length >= policy.max_vertices ||
								previous.some(
									([lng, lat]) => lng === point[0] && lat === point[1],
								)
							)
								return previous;
							return [...previous, point];
						}),
					transaction: (change) => {
						try {
							const last = change.steps.at(-1);
							if (last) setVertices(readMapPolygon(last.geometry));
						} catch {
							setError(__("Check the drawn outline.", "linker-tools"));
						}
					},
					failed: () =>
						setError(__("The drawing could not be updated.", "linker-tools")),
					interrupted: () => setTool("select"),
				}
			: null;
	function startTool(value: typeof tool) {
		setTool(value);
		setVertices([]);
		setDrawingKey(crypto.randomUUID());
		setError("");
		if ((value === "roof" || value === "obstacle") && mapReferenced)
			setView("map");
		else if (view === "scene" && value !== "select") setView("plan");
	}
	const field = (key: keyof typeof fields, label: string, unit = "m") => (
		<label className="sc-field">
			<span>
				{label}
				{unit ? ` (${unit})` : ""}
			</span>
			<input
				type="number"
				step="any"
				value={fields[key]}
				onChange={(e) => {
					const value = e.currentTarget.value;
					setFields((previous) => ({ ...previous, [key]: value }));
				}}
			/>
		</label>
	);
	const drag = useRef<{
		point: Vec2;
		id: string;
		kind: "array" | "obstacle" | "vertex";
		vertex: number | undefined;
	} | null>(null);
	function planPoint(
		svg: SVGSVGElement,
		clientX: number,
		clientY: number,
	): Vec2 | null {
		const transform = svg.getScreenCTM();
		if (!transform) return null;
		const point = svg.createSVGPoint();
		point.x = clientX;
		point.y = clientY;
		const local = point.matrixTransform(transform.inverse());
		return [local.x, local.y];
	}
	function startDrag(
		event: ReactPointerEvent<SVGPolygonElement | SVGCircleElement>,
		objectId: string,
		kind: "array" | "obstacle" | "vertex",
		vertex?: number,
	) {
		if (blocked || tool !== "select") return;
		event.stopPropagation();
		select(objectId);
		const svg = event.currentTarget.ownerSVGElement!;
		const point = planPoint(svg, event.clientX, event.clientY);
		if (!point) return;
		drag.current = {
			point,
			id: objectId,
			kind,
			vertex,
		};
		svg.setPointerCapture?.(event.pointerId);
	}
	function endDrag(event: ReactPointerEvent<SVGSVGElement>) {
		const active = drag.current;
		drag.current = null;
		if (!active || blocked) return;
		const point = planPoint(event.currentTarget, event.clientX, event.clientY);
		if (!point) return;
		const delta: Vec2 = [
			point[0] - active.point[0],
			point[1] - active.point[1],
		];
		if (!delta[0] && !delta[1]) return;
		if (active.kind === "array")
			commit({ type: "move_arrays", ids: [active.id], delta_uv: delta });
		else if (active.kind === "obstacle") {
			const old = geometry.obstacles.find((o) => o.id === active.id);
			if (old)
				commit({
					type: "put_obstacle",
					before: old,
					value: {
						...old,
						footprint_uv: old.footprint_uv.map(([u, v]) => [
							u + delta[0],
							v + delta[1],
						]),
					},
				});
		} else {
			const old = geometry.roofs.find((r) => r.id === active.id);
			if (old)
				commit({
					type: "put_roof",
					before: old,
					value: {
						...old,
						boundary_uv: old.boundary_uv.map((p, i) =>
							i === active.vertex ? point : p,
						),
					},
				});
		}
	}
	const allPoints = roof?.boundary_uv ?? [];
	const minU = allPoints.length ? Math.min(...allPoints.map((p) => p[0])) : 0,
		minV = allPoints.length ? Math.min(...allPoints.map((p) => p[1])) : 0;
	const width = allPoints.length
			? Math.max(...allPoints.map((p) => p[0])) - minU
			: 1,
		depth = allPoints.length
			? Math.max(...allPoints.map((p) => p[1])) - minV
			: 1;
	const site = readBrief(inputs.brief).site;
	const imagery = useQuery({
		queryKey: [
			session.query_scope,
			"sc-solar-imagery",
			site.country_code,
			site.postal_code,
			site.location_label,
		],
		enabled:
			map && !blocked && Boolean(site.postal_code || site.location_label),
		retry: false,
		queryFn: async ({ signal }) => {
			const reply = readObject(
				await client.query(
					"places/lookup",
					{
						schema_version: 1,
						query: site.postal_code || site.location_label,
						...(site.country_code ? { country: site.country_code } : {}),
					},
					session.query_scope,
					signal,
				),
			);
			return {
				imagery: readPlaceImagery(reply.imagery),
				latitude: reply.latitude,
				longitude: reply.longitude,
				country: reply.country_code,
			};
		},
		refetchOnReconnect: false,
		refetchOnWindowFocus: false,
	});
	const latitude = site.latitude ?? imagery.data?.latitude,
		longitude = site.longitude ?? imagery.data?.longitude,
		country = site.country_code ?? imagery.data?.country;
	const outline = useQuery({
		queryKey: [
			session.query_scope,
			"sc-solar-outline",
			site.location_label,
			country,
			latitude,
			longitude,
		],
		enabled:
			map && !blocked && imagery.isSuccess && Boolean(site.location_label),
		retry: false,
		queryFn: async ({ signal }) => {
			if (
				typeof latitude !== "number" ||
				typeof longitude !== "number" ||
				typeof country !== "string"
			)
				return null;
			const found = readObject(
				await client.query(
					"places/outline",
					{
						schema_version: 1,
						query: site.location_label,
						country,
						latitude,
						longitude,
					},
					session.query_scope,
					signal,
				),
			);
			if (
				found.found !== true ||
				!Array.isArray(found.outline) ||
				found.outline.length < 3 ||
				typeof found.source !== "string" ||
				typeof found.licence !== "string"
			)
				return null;
			return {
				ring: found.outline as [number, number][],
				source: found.source,
				licence: found.licence,
			};
		},
	});
	return (
		<section className="sc-solar">
			<header className="sc-section-head">
				<h1>{__("Define the solar installation", "linker-tools")}</h1>
				<p>
					{__(
						"A roof layout or the module details can provide the starting point.",
						"linker-tools",
					)}
				</p>
			</header>
			<fieldset disabled={blocked}>
				<div className="sc-option-row">
					{(["known", "roof"] as const).map((value) => (
						<button
							type="button"
							className={`sc-option-card${mode === value ? " active" : ""}`}
							aria-pressed={mode === value}
							key={value}
							onClick={() => {
								if (
									value !== mode &&
									(value === "known" || reference.model === KNOWN_PV_MODEL)
								)
									referenceChange({}, value);
								setMode(value);
							}}
						>
							{value === "known"
								? __("Use module details", "linker-tools")
								: __("Place modules on the roof", "linker-tools")}
						</button>
					))}
				</div>
				<div className="sc-card">
					<label className="sc-field">
						<span>{__("PV module", "linker-tools")}</span>
						<select
							value={module?.id ?? ""}
							onChange={(e) => {
								const spec =
									templates.data?.find(
										(t) => t.specification.id === e.currentTarget.value,
									)?.specification ??
									geometry.module_specs.find(
										(m) => m.id === e.currentTarget.value,
									);
								if (spec) chooseModule(spec);
							}}
						>
							<option value="">{__("Choose a module", "linker-tools")}</option>
							{[
								...geometry.module_specs,
								...(templates.data ?? [])
									.map((t) => t.specification)
									.filter(
										(m) =>
											!geometry.module_specs.some((old) => old.id === m.id),
									),
							].map((m) => (
								<option key={m.id} value={m.id}>
									{m.model} · {m.stc_power_w} Wp
								</option>
							))}
						</select>
					</label>
					{templates.isError && (
						<p role="alert">
							{__("Module data could not be loaded.", "linker-tools")}
						</p>
					)}
					{mode === "known" ? (
						<>
							<div className="sc-fields">
								<label className="sc-field">
									<span>{__("Number of modules", "linker-tools")}</span>
									<input
										type="number"
										min="1"
										step="1"
										value={
											count ||
											(module && known?.peak_power_kwp != null
												? String(
														(known.peak_power_kwp * 1000) / module.stc_power_w,
													)
												: "")
										}
										onChange={(e) => {
											const text = e.currentTarget.value;
											setCount(text);
											if (module)
												knownChange({
													peak_power_kwp:
														text &&
														Number(text) > 0 &&
														Number.isInteger(Number(text))
															? (Number(text) * module.stc_power_w) / 1000
															: null,
												});
										}}
									/>
								</label>
								<label className="sc-field">
									<span>{__("Solar capacity", "linker-tools")} (kWp)</span>
									<input
										type="number"
										min="0"
										step="any"
										value={known?.peak_power_kwp ?? ""}
										onChange={(e) => {
											setCount("");
											knownChange({
												peak_power_kwp: e.currentTarget.value
													? Number(e.currentTarget.value)
													: null,
											});
										}}
									/>
								</label>
								{(["tilt_deg", "azimuth_north_clockwise_deg"] as const).map(
									(key) => (
										<label className="sc-field" key={key}>
											<span>
												{key === "tilt_deg"
													? __("Roof pitch", "linker-tools")
													: __("Azimuth (north = 0°)", "linker-tools")}{" "}
												(°)
											</span>
											<input
												type="number"
												step="any"
												value={known?.[key] ?? ""}
												onChange={(e) =>
													knownChange({
														[key]: e.currentTarget.value
															? Number(e.currentTarget.value)
															: null,
													})
												}
											/>
										</label>
									),
								)}
								<label className="sc-field">
									<span>{__("Source of module details", "linker-tools")}</span>
									<input
										value={known?.source_note ?? ""}
										onChange={(e) =>
											knownChange({ source_note: e.currentTarget.value })
										}
									/>
								</label>
							</div>
						</>
					) : (
						<div className="sc-roof-layout">
							<div>
								<div className="sc-roof-tools">
									{(["select", "roof", "modules", "obstacle"] as const).map(
										(value) => (
											<button
												type="button"
												key={value}
												aria-pressed={tool === value}
												onClick={() => startTool(value)}
											>
												{
													{
														select: __("Select / move", "linker-tools"),
														roof: __("Draw roof", "linker-tools"),
														modules: __("Place modules", "linker-tools"),
														obstacle: __("Obstacle", "linker-tools"),
													}[value]
												}
											</button>
										),
									)}
									<button
										type="button"
										disabled={!undo.length}
										onClick={() => {
											const previous = undo.at(-1);
											if (
												previous &&
												edit((current) => ({
													...invalidateEnergyReplay(current),
													geometry: readObject(previous),
												}))
											)
												setUndo(undo.slice(0, -1));
										}}
									>
										{__("Undo", "linker-tools")}
									</button>
								</div>
								<div
									className="sc-roof-tools"
									role="group"
									aria-label={__("Plan view controls", "linker-tools")}
								>
									{(
										[
											["plan", __("Plan view", "linker-tools")],
											["scene", __("3D view", "linker-tools")],
											["map", __("Aerial map", "linker-tools")],
										] as const
									).map(([value, label]) => (
										<button
											type="button"
											key={value}
											aria-pressed={view === value}
											disabled={
												(value === "scene" && !roof) || vertices.length > 0
											}
											onClick={() => {
												setView(value);
												if (value === "scene") setTool("select");
											}}
										>
											{label}
										</button>
									))}
								</div>
								{map && imagery.isError && (
									<div role="alert">
										<p>
											{__(
												"Aerial imagery is not available. You can upload a roof plan or retry loading the map.",
												"linker-tools",
											)}
										</p>
										<button
											type="button"
											onClick={() => void imagery.refetch()}
										>
											{__("Try again", "linker-tools")}
										</button>
									</div>
								)}
								{map ? (
									<LazyMapViewport
										mapModuleUrl={config.mapModuleUrl ?? null}
										imagery={imagery.data?.imagery ?? null}
										siteOutline={outline.data ?? null}
										document={geometry}
										poses={poses}
										selected={selected}
										select={select}
										disabled={blocked}
										openReferences={() =>
											setError(
												__(
													"Confirm the geographic origin and true-north basis in the project before drawing on the map.",
													"linker-tools",
												),
											)
										}
										camera={camera}
										siteCentre={
											site.latitude !== null && site.longitude !== null
												? [site.longitude, site.latitude]
												: null
										}
										interaction={interaction}
										placement={
											tool === "modules" && roof && module && mapReferenced
												? { roofId: roof.id, place: placeModules }
												: null
										}
									/>
								) : view === "scene" && roof ? (
									<LazySceneViewport
										sceneModuleUrl={config.sceneModuleUrl ?? null}
										document={geometry}
										poses={poses}
										selected={selected}
										select={select}
										commit={commit}
										disabled={blocked}
									/>
								) : (
									<svg
										className="sc-roof-board"
										viewBox={`${minU - 1} ${minV - 1} ${width + 2} ${depth + 2}`}
										aria-label={__("Editable roof plan", "linker-tools")}
										role="img"
										onPointerUp={endDrag}
										onPointerCancel={() => {
											drag.current = null;
										}}
										onClick={(e) => {
											if (blocked || tool !== "modules" || !roof) return;
											const point = planPoint(
												e.currentTarget,
												e.clientX,
												e.clientY,
											);
											if (point) placeModules(point);
										}}
									>
										{roof && (
											<polygon
												points={roof.boundary_uv
													.map((p) => p.join(","))
													.join(" ")}
												className="lp-roof-shape"
												onClick={() => select(roof.id)}
											/>
										)}
										{geometry.obstacles
											.filter((o) => o.roof_id === roof?.id)
											.map((o) => (
												<polygon
													key={o.id}
													onPointerDown={(e) => startDrag(e, o.id, "obstacle")}
													points={o.footprint_uv
														.map((p) => p.join(","))
														.join(" ")}
													className="lp-obstacle-shape"
													onClick={(e) => {
														e.stopPropagation();
														select(o.id);
													}}
												/>
											))}
										{poses
											.filter((p) => p.roof_id === roof?.id && p.included)
											.map((p) => (
												<polygon
													key={p.id}
													onPointerDown={(e) =>
														startDrag(e, p.array_id, "array")
													}
													points={p.footprint_uv
														.map((v) => v.join(","))
														.join(" ")}
													className="lp-panel-shape"
													data-selected={selected === p.array_id || undefined}
													onClick={(e) => {
														e.stopPropagation();
														select(p.array_id);
													}}
												/>
											))}
										{tool === "select" &&
											roof?.boundary_uv.map(([u, v], index) => (
												<circle
													key={`corner-${index}`}
													cx={u}
													cy={v}
													r={Math.max(width, depth) * 0.012}
													className="sc-roof-vertex"
													onPointerDown={(e) =>
														startDrag(e, roof.id, "vertex", index)
													}
												/>
											))}
									</svg>
								)}
								{interaction && vertices.length >= 3 && (
									<button
										type="button"
										onClick={() =>
											tool === "roof"
												? addRoof(vertices)
												: addObstacle(vertices)
										}
									>
										{__("Finish outline", "linker-tools")}
									</button>
								)}
								<p className="sc-hint">
									{interaction
										? __(
												"Click each corner on the map, then finish the outline.",
												"linker-tools",
											)
										: tool === "roof" && !mapReferenced
											? __(
													"Enter the roof dimensions or confirm the map origin to draw on the map.",
													"linker-tools",
												)
											: __(
													"The plan uses metres in the recorded roof plane.",
													"linker-tools",
												)}
								</p>
							</div>
							<aside className="sc-roof-props">
								<label className="sc-field">
									<span>{__("Selected roof", "linker-tools")}</span>
									<select
										value={roof?.id ?? ""}
										onChange={(e) => select(e.currentTarget.value)}
									>
										<option value="">
											{__("Choose a roof", "linker-tools")}
										</option>
										{geometry.roofs.map((r) => (
											<option key={r.id} value={r.id}>
												{r.name}
											</option>
										))}
									</select>
								</label>
								{field("width", __("Width", "linker-tools"))}
								{field("depth", __("Depth", "linker-tools"))}
								{field("pitch", __("Pitch", "linker-tools"), "°")}
								{field("azimuth", __("Azimuth", "linker-tools"), "°")}
								{field("height", __("Relative roof height", "linker-tools"))}
								{field("originU", __("Origin east / U", "linker-tools"))}
								{field("originV", __("Origin north / V", "linker-tools"))}
								<label className="sc-field">
									<span>{__("Drawing source", "linker-tools")}</span>
									<input
										value={fields.source}
										onChange={(e) => {
											const value = e.currentTarget.value;
											setFields((previous) => ({ ...previous, source: value }));
										}}
									/>
								</label>
								<label className="sc-check">
									<input
										type="checkbox"
										checked={confirmed}
										onChange={(e) => setConfirmed(e.currentTarget.checked)}
									/>
									{__(
										"I confirm these dimensions and permission to use this drawing.",
										"linker-tools",
									)}
								</label>
								{!geometry.coordinate_system.anchor &&
									site.coordinate_basis === "user_entered" &&
									site.latitude !== null &&
									site.longitude !== null && (
										<button
											type="button"
											disabled={!confirmed || !fields.source.trim()}
											onClick={confirmMapReference}
										>
											{__(
												"Confirm site coordinates as map origin and use true north",
												"linker-tools",
											)}
										</button>
									)}
								<button
									type="button"
									disabled={!confirmed || !fields.source.trim()}
									onClick={() => addRoof()}
								>
									{__("Add rectangular roof", "linker-tools")}
								</button>
								{field(
									"obstacleHeight",
									__("Obstacle height above roof", "linker-tools"),
								)}
								<button
									type="button"
									disabled={!roof}
									onClick={() => addObstacle()}
								>
									{__("Add obstacle", "linker-tools")}
								</button>
								{field("rows", __("Rows", "linker-tools"), "")}
								{field("columns", __("Columns", "linker-tools"), "")}
								{field("gap", __("Module gap", "linker-tools"))}
								<button
									type="button"
									disabled={!module || !roof}
									onClick={() => placeModules()}
								>
									{__("Place module group", "linker-tools")}
								</button>
								<button
									type="button"
									disabled={!selected}
									onClick={removeSelected}
								>
									{__("Remove selected", "linker-tools")}
								</button>
								{geometry.arrays.some((a) => a.id === selected) && (
									<div className="sc-actions">
										{(
											[
												[-0.1, 0, "←"],
												[0, -0.1, "↑"],
												[0, 0.1, "↓"],
												[0.1, 0, "→"],
											] as const
										).map(([u, v, label]) => (
											<button
												type="button"
												key={label}
												aria-label={`${__("Move selected", "linker-tools")} ${label}`}
												onClick={() =>
													commit({
														type: "move_arrays",
														ids: [selected!],
														delta_uv: [u, v],
													})
												}
											>
												{label}
											</button>
										))}
										<button
											type="button"
											onClick={() =>
												commit({
													type: "rotate_arrays",
													ids: [selected!],
													delta_deg: 90,
												})
											}
										>
											{__("Rotate selected", "linker-tools")}
										</button>
									</div>
								)}
							</aside>
						</div>
					)}
					<h3>{__("Solar generation estimate", "linker-tools")}</h3>
					<p className="sc-muted">
						{__(
							"Compare systems uses JRC PVGIS to estimate AC generation from the location, array details and settings below. Energy comparisons use the period covered by both the solar and energy use profiles.",
							"linker-tools",
						)}
					</p>
					<div className="sc-fields">
						{(mode === "known" || !geometry.coordinate_system.anchor) &&
							(["latitude", "longitude"] as const).map((key) => {
								const bound = key === "latitude" ? 90 : 180;
								return (
									<label className="sc-field" key={key}>
										<span>
											{key === "latitude"
												? __("Latitude", "linker-tools")
												: __("Longitude", "linker-tools")}
										</span>
										<input
											type="number"
											step="any"
											min={-bound}
											max={bound}
											value={site[key] ?? ""}
											onChange={(e) =>
												coordinateChange(
													key,
													e.currentTarget.validity.valid &&
														e.currentTarget.value
														? e.currentTarget.valueAsNumber
														: null,
												)
											}
										/>
									</label>
								);
							})}
						<label className="sc-field">
							<span>{__("Calendar year", "linker-tools")}</span>
							<input
								type="number"
								min="1"
								max="9998"
								step="1"
								value={reference.year ?? ""}
								onChange={(e) =>
									referenceChange({
										year:
											e.currentTarget.validity.valid && e.currentTarget.value
												? e.currentTarget.valueAsNumber
												: null,
									})
								}
							/>
						</label>
						<label className="sc-field">
							<span>{__("Radiation database", "linker-tools")}</span>
							<select
								value={reference.radiation_database ?? ""}
								onChange={(e) =>
									referenceChange({
										radiation_database: (e.currentTarget.value ||
											null) as PvgisReferenceDraft["radiation_database"],
									})
								}
							>
								<option value="">
									{__("Choose a radiation database", "linker-tools")}
								</option>
								{REFERENCE_DATABASES.map((database) => (
									<option key={database}>{database}</option>
								))}
							</select>
						</label>
						<label className="sc-field">
							<span>{__("PV reference technology", "linker-tools")}</span>
							<select
								value={reference.pv_technology ?? ""}
								onChange={(e) =>
									referenceChange({
										pv_technology: (e.currentTarget.value ||
											null) as PvgisReferenceDraft["pv_technology"],
									})
								}
							>
								<option value="">
									{__("Choose a reference technology", "linker-tools")}
								</option>
								{REFERENCE_TECHNOLOGIES.map((technology) => (
									<option key={technology}>{technology}</option>
								))}
							</select>
						</label>
						<label className="sc-field">
							<span>{__("Mounting place", "linker-tools")}</span>
							<select
								value={reference.mounting_place ?? ""}
								onChange={(e) =>
									referenceChange({
										mounting_place: (e.currentTarget.value ||
											null) as PvgisReferenceDraft["mounting_place"],
									})
								}
							>
								<option value="">
									{__("Choose the mounting place", "linker-tools")}
								</option>
								<option value="free">
									{__("Freestanding or ventilated", "linker-tools")}
								</option>
								<option value="building">
									{__("Building-integrated", "linker-tools")}
								</option>
							</select>
						</label>
						<label className="sc-field">
							<span>{__("System loss (%)", "linker-tools")}</span>
							<input
								type="number"
								step="any"
								min="0"
								max="100"
								value={reference.system_loss_percent ?? ""}
								onChange={(e) =>
									referenceChange({
										system_loss_percent:
											e.currentTarget.validity.valid && e.currentTarget.value
												? e.currentTarget.valueAsNumber
												: null,
									})
								}
							/>
						</label>
						<label className="sc-field">
							<span>{__("Terrain horizon", "linker-tools")}</span>
							<select
								value={
									reference.use_terrain_horizon === null
										? ""
										: String(reference.use_terrain_horizon)
								}
								onChange={(e) =>
									referenceChange({
										use_terrain_horizon: e.currentTarget.value
											? e.currentTarget.value === "true"
											: null,
									})
								}
							>
								<option value="">
									{__("Choose a horizon setting", "linker-tools")}
								</option>
								<option value="true">
									{__("Include PVGIS terrain horizon", "linker-tools")}
								</option>
								<option value="false">
									{__("Omit terrain horizon", "linker-tools")}
								</option>
							</select>
						</label>
						<label className="sc-field">
							<span>{__("Source of the model settings", "linker-tools")}</span>
							<input
								maxLength={4096}
								value={reference.source_note ?? ""}
								onChange={(e) =>
									referenceChange({ source_note: e.currentTarget.value })
								}
							/>
						</label>
					</div>
					<p className="sc-solar-total">
						{mode === "roof"
							? `${summary.count} ${__("placed modules", "linker-tools")} · ${summary.stc_kwp} kWp`
							: known?.peak_power_kwp != null
								? `${known.peak_power_kwp} kWp`
								: __("Solar capacity not entered", "linker-tools")}
					</p>
				</div>
				{geometryImport && (
					<GeometryIntake
						geometry={geometry}
						projectId={geometryImport.projectId}
						session={session}
						client={client}
						locale={config.locale}
						recheck={geometryImport.recheck}
						disabled={blocked || tool !== "select"}
						onActivity={geometryImport.onActivity}
						attach={(before, asset) => {
							try {
								if (
									!edit((current) => {
										const attached = attachGeometryImport(
											invalidateEnergyReplay(current),
											before,
											asset,
										);
										return referenceDraft(current).model === KNOWN_PV_MODEL
											? roofReferenceInputs(attached)
											: attached;
									})
								)
									return false;
							} catch {
								return false;
							}
							setMode("roof");
							select(asset.geometry.roofs[0]!.id);
							return true;
						}}
						currentAssetIds={Object.values(
							readGeometryImports(inputs.geometry_imports).selected,
						)}
						confirmedAssetIds={Object.values(
							readGeometryImports(
								geometryImport.confirmedInputs.geometry_imports,
							).selected,
						)}
						recoveryScopes={geometryImport.recoveryScopes}
						recoveryChecking={geometryImport.recoveryChecking}
					/>
				)}
				{error && <p role="alert">{error}</p>}
				<footer className="sc-next">
					<button type="button" onClick={next}>
						{__("Continue with energy use", "linker-tools")}
					</button>
				</footer>
			</fieldset>
		</section>
	);
}
