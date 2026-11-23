import { locateProjectSite } from "../../data/googleMaps.ts";
import { onMapConsentChange } from "../../data/roofImageryConsent.ts";
import { LayoutRulesForm } from "../design/LayoutRulesForm.tsx";
import { RoofInspector, type RoofTab } from "../design/RoofInspector.tsx";
import { useQuery } from "@tanstack/react-query";
import { imagerySourceKey, readPlaceImagery } from "../../domain/place.ts";
import type { PointerEvent as ReactPointerEvent, ReactNode } from "react";
import { useCallback, useEffect, useId, useRef, useState } from "react";
import type { PlaceImagery } from "../../domain/place.ts";
import type { Json, JsonObject, Session } from "../../data/protocol.ts";
import { sameJson } from "../../domain/draft.ts";
import type { Configuration } from "../../data/config.ts";
import type { PlannerClient } from "../../data/PlannerClient.ts";
import {
	emptyPanelFields,
	panelFields,
	panelLabel,
	panelSpecification,
} from "../../domain/panelParameters.ts";
import { Icon } from "../Icon.tsx";
import { SiteCoordinates } from "./SiteCoordinates.tsx";
import { PanelMeasurementFields } from "../PanelMeasurementFields.tsx";
import type {
	GeometryDocument,
	RoofFace,
	Vec2,
} from "../../domain/geometry.ts";
import {
	applyGeometryCommand,
	emptyGeometry,
	roofDependents,
} from "../../domain/geometryCommands.ts";
import type { GeometryCommand } from "../../domain/geometryCommands.ts";
import {
	ringArea,
	manualSource,
	rectangularRoof,
	roofPlane,
} from "../../domain/geometryEditing.ts";
import { cross } from "../../domain/coordinates.ts";
import { readGeometry } from "../../domain/validateGeometry.ts";
import {
	attachGeometryImport,
	readGeometryImports,
} from "../../domain/geometryImports.ts";
import {
	ImageCalibrationWorkspace,
	type CalibrationCommand,
} from "../design/ImageCalibrationWorkspace.tsx";
import { SourceMeasurements } from "../design/MapSourceDetails.tsx";
import { GeometryIntake } from "../design/GeometryIntake.tsx";
import { GeometryExportPermission } from "../design/GeometryForm.tsx";
import policy from "../../contracts/geometry-policy.json" with { type: "json" };
import { moduleSummary, panelPoses } from "../../domain/panelPoses.ts";
import { readObject } from "../../data/readProtocol.ts";
import {
	referenceDraft,
	referenceInputs,
	KNOWN_PV_MODEL,
	knownReferenceArrays,
	REFERENCE_DATABASES,
	REFERENCE_TECHNOLOGIES,
	type PvgisReferenceDraft,
} from "../../domain/pvgisReference.ts";
import { invalidateEnergyReplay } from "../../domain/energyScenario.ts";
import { readBrief } from "../../domain/brief.ts";
import {
	formatComputedDecimal,
	formatDecimal,
	parseDecimal,
} from "../../domain/decimal.ts";
import { LazySceneViewport } from "../design/LazySceneViewport.tsx";
import { LazyMapViewport } from "../design/LazyMapViewport.tsx";
import type { MapCamera } from "../design/MapViewport.tsx";
import {
	mapPolygon,
	newMapShapeCommand,
	readMapPolygon,
} from "../../domain/mapDrawingGeometry.ts";
import { canAnchorFirstMapRoof } from "../../domain/mapDrawingBase.ts";
import type { MapInteraction } from "../../data/mapInteraction.ts";
import { revealActionResult } from "../revealActionResult.ts";
import { __, sprintf } from "../../i18n.ts";

export interface SolarInstallationProps {
	inputs: JsonObject;
	config: Configuration;
	client: PlannerClient;
	session: Session;
	disabled: boolean;
	edit: (op: (inputs: JsonObject) => JsonObject) => boolean;
	next: () => void;
	wiring?: ReactNode;
	initialMap?: boolean;
	initialPlan?: boolean;
	annualGenerationKwh?: number | null;
	takeImageryConsent?: (source: PlaceImagery) => boolean;
	onEditing?: (editing: boolean) => void;
	onLayoutChange?: () => void;
	onCoordinateValidity?: (valid: boolean) => void;
	active?: boolean;
	geometryImport?: {
		projectId: string;
		recheck: () => void;
		confirmedInputs: JsonObject;
		onActivity: (open: boolean) => void;
		recoveryScopes?: readonly string[] | undefined;
		recoveryChecking?: boolean | undefined;
	};
}
interface ReferenceChange {
	before: JsonObject;
	after: PvgisReferenceDraft;
}
type SolarUndo =
	| { geometry: GeometryDocument | null; reference: ReferenceChange | null }
	| {
			calibration: CalibrationCommand;
			hadGeometry: boolean;
			reference: ReferenceChange | null;
	  };
const referenceKeys = [
	"pvgis_reference_setup",
	"pvgis_reference",
	"inactive_known_pv_arrays",
] as const;

function restoreKnownReference(
	current: JsonObject,
	{ before, after }: ReferenceChange,
): JsonObject {
	const active = referenceDraft(current);
	if (active.model !== after.model) throw new Error("solar_reference_changed");
	if (!sameJson(active, after)) {
		// Keep shared settings edited after tracing, and recompile for the known arrays.
		const known = referenceDraft(before);
		return referenceInputs(current, {
			...active,
			model: KNOWN_PV_MODEL,
			...(known.arrays === undefined ? {} : { arrays: known.arrays }),
		});
	}
	const restored: Record<string, Json> = { ...current };
	for (const key of referenceKeys) {
		const value = before[key];
		if (value === undefined) delete restored[key];
		else restored[key] = value;
	}
	return restored;
}

function roofProperties(roof: RoofFace) {
	const [east, north, up] = cross(roof.u_axis_enu, roof.v_axis_enu);
	const horizontal = Math.hypot(east, north);
	const pitch = (Math.atan2(horizontal, up) * 180) / Math.PI;
	const bearing = horizontal
		? Math.atan2(east, north)
		: Math.atan2(-roof.u_axis_enu[1], roof.u_axis_enu[0]);
	return {
		pitch,
		azimuth: ((bearing * 180) / Math.PI + 360) % 360,
		height: roof.origin_enu[2],
	};
}

function measurement(raw: string, locale: string): number {
	try {
		return parseDecimal(raw, locale, "point-or-comma") ?? NaN;
	} catch {
		return NaN;
	}
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
	wiring,
	initialMap = false,
	initialPlan = false,
	annualGenerationKwh = null,
	active = true,
	onCoordinateValidity,
	takeImageryConsent,
	onEditing,
	onLayoutChange,
	geometryImport,
}: SolarInstallationProps) {
	const geometry =
		inputs.geometry === undefined
			? emptyGeometry()
			: readGeometry(inputs.geometry, policy);
	const reference = referenceDraft(inputs);
	const site = readBrief(inputs.brief).site;
	const recordedCentre =
		site.latitude !== null && site.longitude !== null
			? ([site.longitude, site.latitude] as const)
			: null;
	const mapReferenced =
		geometry.coordinate_system.anchor !== null &&
		geometry.coordinate_system.north_reference === "true_north";
	const [mode, setMode] = useState<"known" | "roof">(
		initialMap ||
			initialPlan ||
			(reference.model !== KNOWN_PV_MODEL && geometry.roofs.length > 0)
			? "roof"
			: "known",
	);
	const [layoutOpen, setLayoutOpen] = useState(initialMap || initialPlan);
	const [inspector, setInspector] = useState<RoofTab>("geometry");
	const choicesId = useId();
	const layoutHeading = useRef<HTMLHeadingElement>(null);
	const openLayout = useRef<HTMLButtonElement>(null);
	const [moduleId, setModuleId] = useState(geometry.module_specs[0]?.id ?? "");
	const [newPanelId, setNewPanelId] = useState(id);
	const savedPanel = geometry.module_specs.find((item) => item.id === moduleId);
	const [measurements, setMeasurements] = useState(emptyPanelFields);
	const [editingPanel, setEditingPanel] = useState(false);
	const module =
		savedPanel && !editingPanel
			? savedPanel
			: panelSpecification(savedPanel?.id ?? newPanelId, measurements);
	const known = knownReferenceArrays(inputs)?.[0];
	const knownPanels = inputs.known_panel_details as
		| {
				count: number | null;
				power_w: number | null;
				system_kwp: number | null;
		  }
		| undefined;
	const [selected, select] = useState<string | null>(
		geometry.roofs[0]?.id ?? null,
	);
	const [tool, setTool] = useState<
		"select" | "roof" | "keepout" | "measure" | "obstacle" | "modules"
	>(initialMap && !geometry.roofs.length ? "roof" : "select");
	const [error, setError] = useState("");
	const [roofPropertyInvalid, setRoofPropertyInvalid] = useState(false);
	const roofPropertiesPanel = useRef<HTMLDivElement>(null);
	const [view, setView] = useState<"plan" | "map" | "scene">(
		!initialPlan &&
			(initialMap ||
				recordedCentre !== null ||
				mapReferenced ||
				(site.country_code && site.location_label.trim()))
			? "map"
			: "plan",
	);
	const [coordinatesValid, setCoordinatesValid] = useState(true);
	const [keepCoordinates, setKeepCoordinates] = useState(false);
	useEffect(() => {
		onCoordinateValidity?.(coordinatesValid);
	}, [coordinatesValid, onCoordinateValidity]);
	const showCoordinates =
		mode === "known" ||
		!geometry.coordinate_system.anchor ||
		keepCoordinates ||
		!coordinatesValid;
	const editingLayout = active && mode === "roof" && layoutOpen;
	const map = editingLayout && view === "map";
	const blocked = disabled || !client.isCurrentScope(session.query_scope);
	const placeQuery = site.postal_code || site.location_label;
	const imagery = useQuery({
		queryKey: [
			session.query_scope,
			"sc-solar-imagery",
			site.country_code,
			site.postal_code,
			site.location_label,
		],
		enabled: editingLayout && !blocked && Boolean(placeQuery.trim()),
		retry: false,
		queryFn: async ({ signal }) => {
			const reply = readObject(
				await client.query(
					"places/lookup",
					{
						schema_version: 1,
						query: placeQuery,
						...(site.country_code ? { country: site.country_code } : {}),
					},
					session.query_scope,
					signal,
				),
			);
			return {
				imagery: readPlaceImagery(reply.imagery),
				viewingImagery: readPlaceImagery(reply.viewing_imagery),
				latitude: reply.latitude,
				longitude: reply.longitude,
				country: reply.country_code,
			};
		},
		refetchOnReconnect: false,
		refetchOnWindowFocus: false,
	});
	const viewingImagery = imagery.data?.viewingImagery ?? null;
	const planImagery = imagery.data?.imagery ?? viewingImagery;
	const requestedImagery = useRef<string | null>(null);
	useEffect(() => {
		const clear = () => {
			requestedImagery.current = null;
		};
		const stop = onMapConsentChange(clear);
		window.addEventListener("pagehide", clear);
		return () => {
			stop();
			window.removeEventListener("pagehide", clear);
		};
	}, []);
	const takeMapConsent = useCallback(
		(source: PlaceImagery) => {
			const matches = requestedImagery.current === imagerySourceKey(source);
			requestedImagery.current = null;
			return matches || (takeImageryConsent?.(source) ?? false);
		},
		[takeImageryConsent],
	);
	const viewOnly = !imagery.data?.imagery && viewingImagery !== null;
	const noAerial =
		map && imagery.isSuccess && !imagery.data.imagery && !viewingImagery;
	const mapToolUnavailable = (value: typeof tool) =>
		map && value !== "select" && (viewOnly || (noAerial && value === "roof"));
	const usingTool =
		tool !== "select" && tool !== "measure" && !mapToolUnavailable(tool);
	const lookedUpLatitude = imagery.data?.latitude;
	const lookedUpLongitude = imagery.data?.longitude;
	const siteCentre =
		recordedCentre ??
		(typeof lookedUpLatitude === "number" &&
		typeof lookedUpLongitude === "number"
			? ([lookedUpLongitude, lookedUpLatitude] as const)
			: null);

	const [manualLocation, setManualLocation] = useState(false);
	const [locating, setLocating] = useState(false);
	const [locationError, setLocationError] = useState(false);
	const locationRequest = useRef(0);
	useEffect(() => {
		setLocating(false);
		setLocationError(false);
		return () => {
			locationRequest.current++;
		};
	}, [view, active, session.query_scope, geometryImport?.projectId]);
	const positioned = siteCentre !== null || mapReferenced;
	const showLocation =
		editingLayout &&
		view !== "scene" &&
		(manualLocation || (!positioned && (map || !!planImagery)));
	async function findAddress() {
		const request = ++locationRequest.current;
		setLocating(true);
		setLocationError(false);
		const located = await locateProjectSite(site, config).catch(() => null);
		if (
			request !== locationRequest.current ||
			!client.isCurrentScope(session.query_scope)
		)
			return;
		setLocating(false);
		if (!located) {
			setLocationError(true);
			setManualLocation(true);
			return;
		}
		edit((current) => {
			const brief = readBrief(current.brief);
			if (!sameJson(brief.site, site)) return current;
			return {
				...invalidateEnergyReplay(current),
				brief: { ...brief, site: located },
			};
		});
	}
	const firstMapRoof = siteCentre !== null && canAnchorFirstMapRoof(geometry);
	const [calibrationOpen, setCalibrationOpen] = useState(false);
	const [editingRules, setEditingRules] = useState(false);
	const [importOpen, setImportOpen] = useState(false);
	const reportImportActivity = geometryImport?.onActivity;
	const geometryImportActivity = useCallback(
		(open: boolean) => {
			setImportOpen(open);
			reportImportActivity?.(open);
		},
		[reportImportActivity],
	);
	useEffect(() => {
		onEditing?.(
			editingLayout &&
				(calibrationOpen || editingRules || usingTool || roofPropertyInvalid),
		);
		return () => onEditing?.(false);
	}, [
		calibrationOpen,
		editingLayout,
		editingRules,
		roofPropertyInvalid,
		usingTool,
		onEditing,
	]);
	const camera = useRef<MapCamera | null>(null);
	const moduleRows = useRef<HTMLInputElement>(null);
	const measuredWidth = useRef<HTMLInputElement>(null);
	const [vertices, setVertices] = useState<readonly Vec2[]>([]);
	const [ruler, setRuler] = useState<readonly Vec2[]>([]);
	const [readyAerial, setReadyAerial] = useState<PlaceImagery | null>(null);
	const tracedAerial = useRef<PlaceImagery | null>(null);
	const canConfirmAerial =
		readyAerial &&
		tracedAerial.current &&
		imagerySourceKey(readyAerial) === imagerySourceKey(tracedAerial.current);
	const [drawingKey, setDrawingKey] = useState(() => crypto.randomUUID());
	const [undo, setUndo] = useState<readonly SolarUndo[]>([]);
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
				geometry.obstacles.some(
					(o) => o.id === selected && o.roof_id === r.id,
				) ||
				geometry.keepouts.some((o) => o.id === selected && o.roof_id === r.id),
		) ??
		geometry.roofs[0];
	const selectedProperties = roof ? roofProperties(roof) : null;
	const edgeClearance = geometry.layout_rules.find(
		(rule) => rule.roof_id === roof?.id,
	)?.edge_clearance_m;
	useEffect(() => {
		if (
			roofPropertyInvalid &&
			!roofPropertiesPanel.current?.querySelector('input[aria-invalid="true"]')
		) {
			setRoofPropertyInvalid(false);
			setError("");
		}
	}, [roof, roofPropertyInvalid]);
	const selectedSource = geometry.sources.find(
		(source) => source.id === roof?.source_id,
	);
	const editablePlane =
		roof?.u_axis_enu[2] === 0 &&
		roof.v_axis_enu[2] <= 0 &&
		selectedSource?.kind === "user_measurement" &&
		selectedSource.reference_sha256 === null &&
		selectedSource.permissions.derive === "permitted";
	function selectObject(value: string) {
		select(value);
		setInspector(
			geometry.arrays.some((a) => a.id === value) ? "modules" : "geometry",
		);
	}
	const poses = panelPoses(geometry);
	const summary = moduleSummary(geometry);
	const area = geometry.roofs.reduce(
		(sum, face) =>
			sum +
			ringArea(face.boundary_uv) -
			face.holes_uv.reduce((holes, ring) => holes + ringArea(ring), 0),
		0,
	);
	const format = (value: number) =>
		new Intl.NumberFormat(config.locale, { maximumFractionDigits: 2 }).format(
			value,
		);
	const metrics = [
		[
			__("Roof area", "linker-tools"),
			geometry.roofs.length ? format(area) + " m²" : "—",
		],
		[
			__("Modules", "linker-tools"),
			format(summary.count) + " " + __("pcs", "linker-tools"),
		],
		[__("PV capacity", "linker-tools"), format(summary.stc_kwp) + " kWp"],
		[
			__("Annual yield", "linker-tools"),
			annualGenerationKwh === null
				? "—"
				: format(annualGenerationKwh / 1000) +
					" " +
					__("MWh/yr", "linker-tools"),
		],
	];
	const numeric = (key: keyof typeof fields) => {
		const value = measurement(fields[key], config.locale);
		if (!Number.isFinite(value))
			throw new Error(
				__(
					"Enter the dimensions, orientation and source for this drawing.",
					"linker-tools",
				),
			);
		return value;
	};
	function commit(
		editCommand: GeometryCommand | { calibration: CalibrationCommand },
	) {
		if (blocked) return false;
		const calibration =
			"calibration" in editCommand ? editCommand.calibration : null;
		const command =
			"calibration" in editCommand ? editCommand.calibration : editCommand;
		let entry: SolarUndo | undefined;
		try {
			const ok = edit((current) => {
				const before =
					current.geometry === undefined
						? emptyGeometry()
						: readGeometry(current.geometry, policy);
				const after = applyGeometryCommand(before, command);
				const updated = {
					...invalidateEnergyReplay(current),
					geometry: readObject(after),
				};
				const switchesReference =
					referenceDraft(current).model === KNOWN_PV_MODEL &&
					(calibration !== null ||
						(mode === "roof" &&
							before.roofs.length === 0 &&
							after.roofs.length > 0));
				const nextInputs = switchesReference
					? roofReferenceInputs(updated)
					: updated;
				const reference = switchesReference
					? { before: current, after: referenceDraft(nextInputs) }
					: null;
				entry = calibration
					? {
							calibration,
							hadGeometry: current.geometry !== undefined,
							reference,
						}
					: {
							geometry: current.geometry === undefined ? null : before,
							reference,
						};
				return nextInputs;
			});
			if (ok && entry) {
				if (mode === "roof") onLayoutChange?.();
				const applied = entry;
				setUndo((previous) => [...previous, applied]);
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
	function clearRoofPropertyError(target: HTMLInputElement) {
		target.removeAttribute("aria-invalid");
		const remaining = Boolean(
			roofPropertiesPanel.current?.querySelector('input[aria-invalid="true"]'),
		);
		setRoofPropertyInvalid(remaining);
		if (!remaining) setError("");
	}
	function applyRoofProperty(
		key: keyof ReturnType<typeof roofProperties>,
		target: HTMLInputElement,
	) {
		if (!roof || !selectedProperties || !editablePlane) return;
		const value = measurement(target.value, config.locale);
		const previous = Math.round(selectedProperties[key] * 100) / 100;
		if (value === previous) {
			target.value = formatDecimal(previous, config.locale);
			if (target.hasAttribute("aria-invalid")) clearRoofPropertyError(target);
			return;
		}
		if (
			!Number.isFinite(value) ||
			(key === "pitch" && (value < 0 || value >= 90)) ||
			(key === "azimuth" && (value < 0 || value >= 360))
		) {
			target.setAttribute("aria-invalid", "true");
			setRoofPropertyInvalid(true);
			setError(__("Check the selected roof and dimensions.", "linker-tools"));
			return;
		}
		const { pitch, azimuth } = selectedProperties;
		const next =
			key === "height"
				? {
						...roof,
						origin_enu: [
							roof.origin_enu[0],
							roof.origin_enu[1],
							value,
						] as const,
					}
				: {
						...roof,
						...roofPlane(
							key === "pitch" ? value : pitch,
							key === "azimuth" ? value : azimuth,
							roof.origin_enu,
						),
					};
		if (commit({ type: "put_roof", before: roof, value: next })) {
			clearRoofPropertyError(target);
		} else {
			target.value = formatDecimal(previous, config.locale);
		}
	}

	function undoRoofEdit() {
		const previous = undo.at(-1);
		if (blocked || !previous) return;
		let restoredMode: "known" | null = null;
		try {
			const ok = edit((current) => {
				const next = { ...invalidateEnergyReplay(current) };
				if ("geometry" in previous) {
					if (previous.geometry === null) delete next.geometry;
					else next.geometry = readObject(previous.geometry);
				} else {
					const [source, roof] = previous.calibration.edits;
					const currentGeometry = readGeometry(current.geometry, policy);
					if (
						!sameJson(
							currentGeometry.sources.find(
								(item) => item.id === source.value.id,
							),
							source.value,
						) ||
						!sameJson(
							currentGeometry.roofs.find((item) => item.id === roof.value.id),
							roof.value,
						)
					)
						throw new Error("geometry_object_changed");
					const restored = applyGeometryCommand(currentGeometry, {
						type: "group",
						edits: [
							roof.before
								? { type: "put_roof", before: roof.value, value: roof.before }
								: {
										type: "delete_roof",
										id: roof.value.id,
										expected_dependents: [],
									},
							{ type: "delete_object", id: source.value.id },
						],
					});
					if (!previous.hadGeometry && sameJson(restored, emptyGeometry()))
						delete next.geometry;
					else next.geometry = readObject(restored);
				}
				if (!previous.reference) return next;
				const restoredInputs = restoreKnownReference(next, previous.reference);
				if (referenceDraft(restoredInputs).model === KNOWN_PV_MODEL)
					restoredMode = "known";
				return restoredInputs;
			});
			if (!ok) return;
			onLayoutChange?.();
			setUndo(undo.slice(0, -1));
			setError("");
			if (restoredMode) {
				setMode(restoredMode);
				setLayoutOpen(false);
			}
		} catch {
			setError(
				__(
					"This edit could not be applied. Some values or references may be invalid or may have changed. The current design is unchanged.",
					"linker-tools",
				),
			);
		}
	}
	function knownChange(patch: JsonObject, panels?: JsonObject) {
		if (blocked) return;
		edit((current) => {
			const draft = referenceDraft(current);
			const existing = knownReferenceArrays(current) ?? [];
			const first = existing[0] ?? {
				id: id(),
				peak_power_kwp: null,
				tilt_deg: null,
				azimuth_north_clockwise_deg: null,
				source_note: "",
			};
			const next = referenceInputs(current, {
				...draft,
				model: KNOWN_PV_MODEL,
				arrays: [{ ...first, ...patch }, ...existing.slice(1)],
			});
			if (panels === undefined) return next;
			return { ...next, known_panel_details: panels };
		});
	}
	function panelPowerChange(
		field: "count" | "power_w" | "system_kwp",
		value: number | null,
	) {
		const details = {
			count: knownPanels?.count ?? null,
			power_w: knownPanels?.power_w ?? null,
			system_kwp: knownPanels
				? knownPanels.system_kwp
				: (known?.peak_power_kwp ?? null),
			[field]: value,
		};
		const computed =
			details.count && details.power_w
				? (details.count * details.power_w) / 1000
				: null;
		knownChange({ peak_power_kwp: details.system_kwp ?? computed }, details);
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
	function referenceChange(
		patch: Partial<PvgisReferenceDraft>,
		method = mode === "roof" &&
		!geometry.roofs.length &&
		reference.model === KNOWN_PV_MODEL
			? "known"
			: mode,
	) {
		if (blocked) return;
		edit((current) => {
			if (method === "roof") return roofReferenceInputs(current, patch);
			const { arrays: _active, ...settings } = referenceDraft(current);
			const arrays = knownReferenceArrays(current);
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
	function addRoof(
		points?: readonly Vec2[],
		aerial = map && points ? tracedAerial.current : null,
	) {
		if (
			map &&
			points &&
			(!aerial ||
				!readyAerial ||
				imagerySourceKey(readyAerial) !== imagerySourceKey(aerial))
		)
			return;
		try {
			if (!aerial && (!confirmed || !fields.source.trim()))
				throw new Error(
					__(
						"Confirm the drawing source before adding a roof.",
						"linker-tools",
					),
				);
			const declared = aerial
				? {
						...manualSource(
							id(),
							aerial.credit,
							`${aerial.licence} (${aerial.licence_url})`,
						),
						reference_url: aerial.licence_url,
						rights_basis: "referenced_licence" as const,
					}
				: manualSource(id(), fields.source.trim(), fields.source.trim());
			const source = points
				? { ...declared, kind: "user_drawing" as const }
				: declared;
			const frame = geometry.coordinate_system;
			const coordinateEdit =
				aerial && points && firstMapRoof
					? {
							type: "set_coordinate_system" as const,
							before: frame,
							value: {
								...frame,
								anchor: {
									longitude_deg: points[0]![0],
									latitude_deg: points[0]![1],
									datum: "EPSG:4326" as const,
									source_id: source.id,
								},
								north_reference: "true_north" as const,
								north_source_id: source.id,
							},
						}
					: null;
			const identity = {
				id: id(),
				name: `${__("Roof", "linker-tools")} ${geometry.roofs.length + 1}`,
				source_id: source.id,
			};
			const sourceEdits = [
				{ type: "put_source" as const, before: null, value: source },
				...(coordinateEdit ? [coordinateEdit] : []),
			];
			const withSource = applyGeometryCommand(geometry, {
				type: "group",
				before: geometry,
				edits: sourceEdits,
			});
			const command: GeometryCommand =
				aerial && points
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
							value: points
								? {
										...identity,
										...roofPlane(numeric("pitch"), numeric("azimuth"), [
											numeric("originU"),
											numeric("originV"),
											numeric("height"),
										]),
										boundary_uv: points,
										holes_uv: [],
									}
								: rectangularRoof(identity, {
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
					edits: [...sourceEdits, ...edits],
				})
			) {
				select(identity.id);
				setVertices([]);
				setTool(points ? "modules" : "select");
				if (points) setInspector("modules");
			}
		} catch (cause) {
			setError(
				cause instanceof Error
					? cause.message
					: __("Check the roof inputs.", "linker-tools"),
			);
		}
	}
	function addKeepout() {
		if (!roof || vertices.length < 3) return;
		const value = {
			id: id(),
			roof_id: roof.id,
			name: __("Keep-out", "linker-tools"),
			reason: __("Keep clear of modules", "linker-tools"),
			source_id: roof.source_id,
		};
		try {
			const command: GeometryCommand = map
				? newMapShapeCommand(
						geometry,
						{ kind: "keepout", value },
						mapPolygon(vertices),
					)
				: {
						type: "put_keepout",
						before: null,
						value: { ...value, footprint_uv: vertices },
					};
			if (commit(command)) {
				select(value.id);
				startTool("select");
			}
		} catch {
			setError(__("Check the drawn outline.", "linker-tools"));
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
	function applyPanelChanges() {
		if (!editingPanel && (savedPanel || !module)) return true;
		if (
			!module ||
			!commit({ type: "put_module", before: savedPanel ?? null, value: module })
		)
			return false;
		setModuleId(module.id);
		setEditingPanel(false);
		return true;
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
			const arrayEdit = { type: "put_array" as const, before: null, value };
			if (
				commit(
					savedPanel && !editingPanel
						? arrayEdit
						: {
								type: "group",
								edits: [
									{
										type: "put_module",
										before: savedPanel ?? null,
										value: module,
									},
									arrayEdit,
								],
							},
				)
			) {
				setModuleId(module.id);
				setEditingPanel(false);
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
	const mapDrawing: MapInteraction | null =
		map &&
		((tool === "roof" && (firstMapRoof || mapReferenced)) ||
			((tool === "obstacle" || tool === "keepout") && roof && mapReferenced))
			? {
					key: drawingKey,
					phase: "collecting",
					requiresAerial: tool === "roof",
					...(tool === "roof" &&
					readyAerial &&
					!vertices.length &&
					fields.pitch &&
					fields.azimuth &&
					fields.height
						? {
								trace: (corners: readonly Vec2[]) => {
									tracedAerial.current = readyAerial;
									setVertices(corners);
									addRoof(corners, readyAerial);
								},
							}
						: {}),
					vertices,
					referencePosition: vertices[0] ?? null,
					append: (point) => {
						if (tool === "roof") {
							if (!readyAerial) return;
							const previousSource = tracedAerial.current;
							if (
								previousSource &&
								imagerySourceKey(previousSource) !==
									imagerySourceKey(readyAerial)
							)
								setVertices([]);
							tracedAerial.current = readyAerial;
						}
						setVertices((previous) => {
							if (
								previous.length >= policy.max_vertices ||
								previous.some(
									([lng, lat]) => lng === point[0] && lat === point[1],
								)
							)
								return previous;
							return [...previous, point];
						});
					},
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
		tracedAerial.current = null;
		setRuler([]);
		setTool(value);
		if (value !== "select")
			setInspector(value === "modules" ? "modules" : "geometry");
		setVertices([]);
		setDrawingKey(crypto.randomUUID());
		setError("");
		if (value === "measure") setView("plan");
		else if (
			(value === "roof" || value === "obstacle") &&
			mapReferenced &&
			view !== "plan"
		)
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
				ref={
					key === "rows"
						? moduleRows
						: key === "width"
							? measuredWidth
							: undefined
				}
				type="text"
				inputMode="decimal"
				value={fields[key]}
				onBlur={() => {
					const value = measurement(fields[key], config.locale);
					if (Number.isFinite(value))
						setFields((previous) => ({
							...previous,
							[key]: formatDecimal(value, config.locale),
						}));
				}}
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
	const roofPath = roof
		? [roof.boundary_uv, ...roof.holes_uv]
				.map((ring) => `M${ring.map((point) => point.join(",")).join(" L")}Z`)
				.join(" ")
		: undefined;
	const minU = allPoints.length ? Math.min(...allPoints.map((p) => p[0])) : 0,
		minV = allPoints.length ? Math.min(...allPoints.map((p) => p[1])) : 0;
	const width = allPoints.length
			? Math.max(...allPoints.map((p) => p[0])) - minU
			: 1,
		depth = allPoints.length
			? Math.max(...allPoints.map((p) => p[1])) - minV
			: 1;

	const interaction =
		viewOnly || (mapDrawing?.requiresAerial && !imagery.data?.imagery)
			? null
			: mapDrawing;
	const tracingRoof =
		interaction?.requiresAerial && Boolean(imagery.data?.imagery);
	const placingOnMap = map && tool === "modules" && !viewOnly;
	const latitude = site.latitude ?? imagery.data?.latitude,
		longitude = site.longitude ?? imagery.data?.longitude,
		country = site.country_code ?? imagery.data?.country;
	const outline = useQuery({
		queryKey: [
			session.query_scope,
			"sc-solar-outline",
			placeQuery,
			country,
			latitude,
			longitude,
		],
		enabled: map && !blocked && imagery.isSuccess && Boolean(placeQuery),
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
						query: placeQuery,
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
	const moduleChoice = (
		<>
			{geometry.module_specs.length > 0 && (
				<label className="sc-field">
					<span>{__("Panel dimensions for this layout", "linker-tools")}</span>
					<select
						value={savedPanel?.id ?? ""}
						onChange={(e) => {
							setModuleId(e.currentTarget.value);
							setEditingPanel(false);
							setMeasurements(emptyPanelFields());
							setNewPanelId(id());
						}}
					>
						{geometry.module_specs.map((spec) => (
							<option key={spec.id} value={spec.id}>
								{panelLabel(spec, config.locale)}
							</option>
						))}
						<option value="">
							{__("Enter different panel dimensions", "linker-tools")}
						</option>
					</select>
				</label>
			)}
			{savedPanel?.source.note ===
				"declared_reference — Parameters retained from an earlier design." && (
				<p className="sc-muted">
					{__(
						"These measurements come from the earlier layout. Check them against your panel data sheet.",
						"linker-tools",
					)}
				</p>
			)}
			{savedPanel && !editingPanel && (
				<button
					type="button"
					className="sc-button"
					onClick={() => {
						setMeasurements(panelFields(savedPanel));
						setEditingPanel(true);
					}}
				>
					{__("Edit panel parameters", "linker-tools")}
				</button>
			)}
			{(!savedPanel || editingPanel) && (
				<PanelMeasurementFields
					locale={config.locale}
					fields={measurements}
					change={setMeasurements}
				/>
			)}
			{editingPanel && savedPanel && (
				<div className="sc-actions">
					<button
						type="button"
						className="sc-button"
						disabled={!module}
						onClick={applyPanelChanges}
					>
						{__("Apply panel parameters", "linker-tools")}
					</button>
					<button
						type="button"
						className="sc-button"
						onClick={() => setEditingPanel(false)}
					>
						{__("Cancel", "linker-tools")}
					</button>
				</div>
			)}
		</>
	);
	const roofDimensions = (
		<div className="sc-fields">
			{field("pitch", __("Pitch", "linker-tools"), "°")}
			{field("azimuth", __("Azimuth", "linker-tools"), "°")}
			{field("height", __("Relative roof height", "linker-tools"))}
		</div>
	);
	const moduleLayout = (
		<div className="sc-fields">
			{field("rows", __("Rows", "linker-tools"), "")}
			{field("columns", __("Columns", "linker-tools"), "")}
			{field("gap", __("Module gap", "linker-tools"))}
		</div>
	);
	const continueToEnergy = (
		<footer className="sc-next sc-site-next">
			<button
				type="button"
				disabled={
					!coordinatesValid ||
					blocked ||
					calibrationOpen ||
					editingRules ||
					importOpen ||
					roofPropertyInvalid ||
					(editingPanel && !module) ||
					vertices.length > 0
				}
				onClick={() => {
					if (mode !== "roof" || applyPanelChanges()) next();
				}}
			>
				{__("Continue with energy use", "linker-tools")} <Icon name="arrow" />
			</button>
		</footer>
	);
	return (
		<section className="sc-solar">
			<header className="sc-section-head" hidden={editingLayout}>
				<h1>{__("Define the solar installation", "linker-tools")}</h1>
				<p>
					{__(
						"A roof layout or the module details can provide the starting point.",
						"linker-tools",
					)}
				</p>
			</header>
			<fieldset disabled={blocked || calibrationOpen} hidden={editingLayout}>
				<div className="sc-option-row sc-solar-methods">
					{(
						[
							[
								"known",
								__("Use module details", "linker-tools"),
								__("Quantity, power and orientation", "linker-tools"),
							],
							[
								"roof",
								__("Place modules on the roof", "linker-tools"),
								__("Roof outline, obstacles and layout", "linker-tools"),
							],
						] as const
					).map(([value, label, help]) => (
						<button
							type="button"
							className="sc-option-card"
							aria-label={label}
							aria-describedby={`${choicesId}-${value}-help`}
							aria-pressed={mode === value}
							disabled={
								importOpen || roofPropertyInvalid || vertices.length > 0
							}
							key={value}
							onClick={() => {
								if (value === mode || (mode === "roof" && !applyPanelChanges()))
									return;
								if (
									(value === "known" && reference.model !== KNOWN_PV_MODEL) ||
									(value === "roof" &&
										geometry.roofs.length > 0 &&
										reference.model === KNOWN_PV_MODEL)
								)
									referenceChange({}, value);
								setKeepCoordinates(value === "roof" && !coordinatesValid);
								setMode(value);
								setLayoutOpen(false);
								startTool("select");
							}}
						>
							<Icon
								name={value === "known" ? "solar" : "layers"}
								className="sc-method-icon"
							/>
							<span className="sc-method-label">{label}</span>
							<span aria-hidden="true" className="sc-method-check">
								{mode === value && <Icon name="check" />}
							</span>
							<small
								className="sc-solar-choice-note"
								id={`${choicesId}-${value}-help`}
							>
								{help}
							</small>
						</button>
					))}
				</div>
				<div className="sc-card sc-solar-inputs">
					{mode === "known" ? (
						<>
							<p className="sc-muted">
								{__(
									"Enter the total solar capacity if you know it, or enter the number of panels and their rated power. Leave unknown values blank.",
									"linker-tools",
								)}
							</p>
							<div className="sc-fields">
								<label className="sc-field">
									<span>{__("Solar capacity", "linker-tools")} (kWp)</span>
									<input
										type="number"
										min="0"
										step="any"
										value={
											(knownPanels
												? knownPanels.system_kwp
												: known?.peak_power_kwp) ?? ""
										}
										placeholder={
											knownPanels?.count &&
											knownPanels.power_w &&
											known?.peak_power_kwp
												? String(known.peak_power_kwp)
												: undefined
										}
										onChange={(e) => {
											const power = e.currentTarget.valueAsNumber;
											panelPowerChange(
												"system_kwp",
												Number.isFinite(power) && power > 0 ? power : null,
											);
										}}
									/>
								</label>
								<label className="sc-field">
									<span>{__("Power per panel", "linker-tools")} (Wp)</span>
									<input
										type="number"
										name="known_panel_power_w"
										min="0"
										step="any"
										value={knownPanels?.power_w ?? ""}
										onChange={(e) => {
											const power = e.currentTarget.valueAsNumber;
											const watts =
												Number.isFinite(power) && power > 0 ? power : null;
											panelPowerChange("power_w", watts);
										}}
									/>
								</label>
								<label className="sc-field">
									<span>{__("Number of modules", "linker-tools")}</span>
									<input
										type="number"
										name="known_panel_count"
										min="1"
										step="1"
										value={knownPanels?.count ?? ""}
										onChange={(e) => {
											const n = e.currentTarget.valueAsNumber;
											const number =
												Number.isSafeInteger(n) && n > 0 ? n : null;
											panelPowerChange("count", number);
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
						<>
							{!editingLayout && roof && (
								<svg
									className="sc-roof-board sc-roof-preview"
									viewBox={`${minU - 1} ${minV - 1} ${width + 2} ${depth + 2}`}
									role="img"
									aria-label={__("Roof layout preview", "linker-tools")}
								>
									<path
										className="sc-roof-shape"
										fillRule="evenodd"
										d={roofPath}
									/>
									{geometry.obstacles
										.filter((obstacle) => obstacle.roof_id === roof.id)
										.map((obstacle) => (
											<polygon
												key={obstacle.id}
												className="sc-obstacle-shape"
												points={obstacle.footprint_uv
													.map((point) => point.join(","))
													.join(" ")}
											/>
										))}
									{poses
										.filter((pose) => pose.roof_id === roof.id && pose.included)
										.map((pose) => (
											<polygon
												key={pose.id}
												className="sc-panel-shape"
												points={pose.footprint_uv
													.map((point) => point.join(","))
													.join(" ")}
											/>
										))}
								</svg>
							)}
							{!editingLayout && (
								<button
									type="button"
									className="sc-button sc-primary sc-open-layout"
									ref={openLayout}
									onClick={() => {
										setLayoutOpen(true);
										window.requestAnimationFrame(() =>
											revealActionResult(layoutHeading.current),
										);
									}}
								>
									<Icon name="layers" />
									{__("Open roof layout", "linker-tools")}
								</button>
							)}
						</>
					)}
					{mode === "roof" && !editingLayout && (
						<div className="sc-layout-panels">{moduleChoice}</div>
					)}
					<div className="sc-solar-total">
						<Icon name="solar" />
						<div>
							<span>{__("Solar capacity", "linker-tools")}</span>
							<strong>
								{mode === "roof" && geometry.roofs.length > 0
									? `${summary.count} ${__("placed modules", "linker-tools")} · ${formatComputedDecimal(summary.stc_kwp, config.locale)} kWp`
									: mode === "known" && known?.peak_power_kwp != null
										? `${formatComputedDecimal(known.peak_power_kwp, config.locale)} kWp`
										: __("Not specified", "linker-tools")}
							</strong>
						</div>
					</div>
				</div>
			</fieldset>
			{editingLayout && (
				<section
					className="sc-card sc-roof-editor sc-roof-studio"
					aria-labelledby={`${choicesId}-roof-editor`}
				>
					<header className="sc-section-head sc-solar-layout-header">
						<h2 ref={layoutHeading} id={`${choicesId}-roof-editor`}>
							{__("Roof studio", "linker-tools")}
						</h2>
						<button
							type="button"
							className="sc-button btn-secondary"
							disabled={
								calibrationOpen ||
								importOpen ||
								roofPropertyInvalid ||
								vertices.length > 0
							}
							onClick={() => {
								if (!applyPanelChanges()) return;
								startTool("select");
								setLayoutOpen(false);
								window.requestAnimationFrame(() =>
									revealActionResult(openLayout.current),
								);
							}}
						>
							{geometry.roofs.length
								? __("Use this layout", "linker-tools")
								: __("Back", "linker-tools")}
						</button>
					</header>
					{noAerial && (
						<div>
							<p>
								{__(
									"No aerial image is available for this location. Use your own roof plan or enter the roof measurements.",
									"linker-tools",
								)}
							</p>
							<button
								type="button"
								className="sc-button"
								onClick={() => {
									startTool("roof");
									setView("plan");
									window.requestAnimationFrame(() =>
										revealActionResult(measuredWidth.current),
									);
								}}
							>
								{__("Enter roof measurements", "linker-tools")}
							</button>
						</div>
					)}
					<fieldset
						className="sc-roof-editor-fields"
						disabled={blocked || calibrationOpen}
					>
						<div className="sc-roof-layout">
							<div className="sc-studio-canvas">
								<div
									className="sc-studio-tools"
									role="group"
									aria-label={__("Drawing tools", "linker-tools")}
								>
									{(
										[
											["select", __("Select plane", "linker-tools")],
											["roof", __("Draw polygon", "linker-tools")],
											["keepout", __("Keep-out", "linker-tools")],
											["measure", __("Measure", "linker-tools")],
										] as const
									).map(([value, label]) => (
										<button
											type="button"
											key={value}
											aria-pressed={
												tool === value && !mapToolUnavailable(value)
											}
											disabled={
												((value === "measure" || value === "keepout") &&
													!roof) ||
												(value !== "measure" && mapToolUnavailable(value))
											}
											onClick={() => startTool(value)}
										>
											{label}
										</button>
									))}
								</div>
								{showLocation && (
									<div className="sc-studio-location">
										{!positioned &&
											config.googleMapsApiKey &&
											site.country_code &&
											site.location_label.trim() && (
												<button
													className="sc-button"
													type="button"
													disabled={locating}
													onClick={() => void findAddress()}
												>
													{locating
														? __("Finding the site…", "linker-tools")
														: __(
																"Find this address with Google Maps",
																"linker-tools",
															)}
												</button>
											)}
										{locationError && (
											<p role="alert">
												{__(
													"The address could not be located. Enter the coordinates to position the map.",
													"linker-tools",
												)}
											</p>
										)}
										{manualLocation ? (
											<div className="sc-fields">
												<SiteCoordinates
													site={site}
													locale={config.locale}
													change={coordinateChange}
													onValidity={setCoordinatesValid}
												/>
											</div>
										) : (
											<button
												type="button"
												className="sc-button"
												disabled={locating}
												onClick={() => setManualLocation(true)}
											>
												{__("Enter map coordinates", "linker-tools")}
											</button>
										)}
									</div>
								)}
								{view === "plan" &&
									positioned &&
									coordinatesValid &&
									planImagery && (
										<div className="sc-map-consent">
											<span id={choicesId + "-provider"}>
												{sprintf(
													__(
														"Allow %s to load the map using your IP address and the area shown.",
														"linker-tools",
													),
													planImagery.credit,
												)}
											</span>
											<button
												type="button"
												className="sc-button btn-secondary"
												disabled={vertices.length > 0}
												aria-describedby={choicesId + "-provider"}
												onClick={() => {
													setManualLocation(false);
													requestedImagery.current =
														imagerySourceKey(planImagery);
													startTool("select");
													setView("map");
												}}
											>
												{__("Allow aerial map", "linker-tools")}
											</button>
										</div>
									)}
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
								{map && positioned ? (
									<LazyMapViewport
										mapModuleUrl={config.mapModuleUrl ?? null}
										imagery={imagery.data?.imagery ?? viewingImagery}
										viewOnly={viewOnly}
										onAerialReady={setReadyAerial}
										takeImageryConsent={takeMapConsent}
										siteOutline={outline.data ?? null}
										document={geometry}
										poses={poses}
										selected={selected}
										select={selectObject}
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
										siteCentre={siteCentre}
										interaction={interaction}
										placement={
											placingOnMap && roof && module && mapReferenced
												? {
														roofId: roof.id,
														place: placeModules,
														review: () =>
															revealActionResult(moduleRows.current),
													}
												: null
										}
									/>
								) : view === "scene" && roof ? (
									<LazySceneViewport
										sceneModuleUrl={config.sceneModuleUrl ?? null}
										document={geometry}
										poses={poses}
										selected={selected}
										select={selectObject}
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
											if (
												blocked ||
												!["roof", "keepout", "measure", "modules"].includes(
													tool,
												)
											)
												return;
											const point = planPoint(
												e.currentTarget,
												e.clientX,
												e.clientY,
											);
											if (!point) return;
											if (tool === "modules") {
												if (roof) placeModules(point);
											} else if (tool === "measure")
												setRuler((points) =>
													points.length === 1 ? [...points, point] : [point],
												);
											else if (vertices.length < policy.max_vertices)
												setVertices((points) => [...points, point]);
										}}
									>
										{roof && (
											<path
												className="sc-roof-shape"
												fillRule="evenodd"
												d={roofPath}
												onClick={() => {
													if (tool === "select") selectObject(roof.id);
												}}
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
													className="sc-obstacle-shape"
													onClick={(e) => {
														if (tool !== "select") return;
														e.stopPropagation();
														selectObject(o.id);
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
													className="sc-panel-shape"
													data-selected={selected === p.array_id || undefined}
													onClick={(e) => {
														if (tool !== "select") return;
														e.stopPropagation();
														selectObject(p.array_id);
													}}
												/>
											))}
										{geometry.keepouts
											.filter((zone) => zone.roof_id === roof?.id)
											.map((zone) => (
												<polygon
													key={zone.id}
													className="sc-keepout-shape"
													data-selected={selected === zone.id || undefined}
													points={zone.footprint_uv
														.map((p) => p.join(","))
														.join(" ")}
													onClick={() => {
														if (tool === "select") selectObject(zone.id);
													}}
												/>
											))}
										{(tool === "measure" || vertices.length > 0) && (
											<g className="sc-studio-draft" pointerEvents="none">
												<polyline
													points={(tool === "measure" ? ruler : vertices)
														.map((p) => p.join(","))
														.join(" ")}
												/>
												{(tool === "measure" ? ruler : vertices).map(
													([u, v], index) => (
														<circle
															key={index}
															cx={u}
															cy={v}
															r={Math.max(width, depth) * 0.009}
														/>
													),
												)}
											</g>
										)}
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
								{(interaction ||
									(!map && (tool === "roof" || tool === "keepout"))) &&
									vertices.length >= 3 && (
										<button
											type="button"
											disabled={
												!!interaction?.requiresAerial && !canConfirmAerial
											}
											onClick={() => {
												if (tool === "keepout") addKeepout();
												else if (tool === "roof") addRoof(vertices);
												else addObstacle(vertices);
											}}
										>
											{__("Finish outline", "linker-tools")}
										</button>
									)}
								{tool === "measure" && (
									<p className="sc-studio-measurement" role="status">
										{ruler.length === 2
											? format(
													Math.hypot(
														ruler[1]![0] - ruler[0]![0],
														ruler[1]![1] - ruler[0]![1],
													),
												) + " m"
											: __(
													"Tap two points on the roof plan to measure the distance.",
													"linker-tools",
												)}
									</p>
								)}
								{tool === "keepout" && (
									<p className="sc-hint">
										{__(
											"Mark the corners of the area to leave clear, then finish the outline.",
											"linker-tools",
										)}
									</p>
								)}
								{!noAerial && tool !== "measure" && tool !== "keepout" && (
									<p className="sc-hint">
										{map && viewOnly
											? __(
													"Use the plan view or a roof image you have permission to use to create the layout.",
													"linker-tools",
												)
											: interaction?.requiresAerial && firstMapRoof
												? __(
														"Mark each roof corner on the aerial map. The first corner sets the origin with true north.",
														"linker-tools",
													)
												: interaction
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
								)}
								<div
									className="sc-roof-tools"
									role="group"
									aria-label={__("Plan view controls", "linker-tools")}
								>
									<button
										type="button"
										disabled={!undo.length}
										onClick={undoRoofEdit}
									>
										{__("Undo", "linker-tools")}
									</button>
									<button
										type="button"
										disabled={!selected}
										onClick={removeSelected}
									>
										{__("Remove selected", "linker-tools")}
									</button>
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
												if (value === "scene" || tool === "measure")
													startTool("select");
											}}
										>
											{label}
										</button>
									))}
								</div>
								<dl className="sc-roof-metrics">
									{metrics.map(([label, value]) => (
										<div key={label}>
											<dt>{label}</dt>
											<dd>{value}</dd>
										</div>
									))}
								</dl>
							</div>
							<RoofInspector
								tab={inspector}
								foot={continueToEnergy}
								change={setInspector}
								locked={roofPropertyInvalid || calibrationOpen || editingRules}
								geometry={
									<>
										<label className="sc-field">
											<span>{__("Selected roof", "linker-tools")}</span>
											<select
												value={roof?.id ?? ""}
												disabled={roofPropertyInvalid || editingRules}
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
										{roof && selectedProperties && (
											<div
												className="sc-selected-roof-properties"
												ref={roofPropertiesPanel}
											>
												{(
													[
														[
															"pitch",
															__("Selected roof pitch", "linker-tools"),
															"°",
														],
														[
															"azimuth",
															__("Selected roof azimuth", "linker-tools"),
															"°",
														],
														[
															"height",
															__("Selected roof height", "linker-tools"),
															"m",
														],
													] as const
												).map(([key, label, unit]) => (
													<label
														className="sc-field"
														key={`${roof.id}:${key}:${selectedProperties[key]}`}
													>
														<span>
															{key === "pitch"
																? __("Pitch", "linker-tools")
																: key === "azimuth"
																	? __("Azimuth", "linker-tools")
																	: __("Height", "linker-tools")}{" "}
															({unit})
														</span>
														<input
															type="text"
															inputMode="decimal"
															aria-label={label}
															defaultValue={formatDecimal(
																Math.round(selectedProperties[key] * 100) / 100,
																config.locale,
															)}
															readOnly={!editablePlane}
															onBlur={(event) =>
																applyRoofProperty(key, event.currentTarget)
															}
															onKeyDown={(event) => {
																if (event.key === "Escape") {
																	event.stopPropagation();
																	event.currentTarget.value = formatDecimal(
																		Math.round(selectedProperties[key] * 100) /
																			100,
																		config.locale,
																	);
																	clearRoofPropertyError(event.currentTarget);
																} else if (event.key === "Enter") {
																	event.preventDefault();
																	event.currentTarget.blur();
																}
															}}
														/>
													</label>
												))}
												<div className="sc-field sc-edge-rule">
													<span>{__("Edge clearance", "linker-tools")}</span>
													<button
														type="button"
														aria-expanded={editingRules}
														onClick={() => setEditingRules(!editingRules)}
													>
														{edgeClearance == null
															? __("Set clearance", "linker-tools")
															: format(edgeClearance) + " m"}
													</button>
												</div>
											</div>
										)}
										{editingRules && roof && (
											<LayoutRulesForm
												key={roof.id}
												roofId={roof.id}
												document={geometry}
												locale={config.locale}
												commit={commit}
												cancel={() => setEditingRules(false)}
												onValidity={(valid) => setEditingRules(!valid)}
											/>
										)}
										{tracingRoof && (
											<>
												<p className="sc-field-help">
													{__(
														"Enter your roof measurements, then trace around the roof in one drag. You can also tap each corner and finish the outline.",
														"linker-tools",
													)}
												</p>
												{roofDimensions}
											</>
										)}
										{!tracingRoof && (
											<details
												open={!roof || tool === "roof" || tool === "obstacle"}
											>
												<summary>
													{__("Add a measured roof face", "linker-tools")}
												</summary>
												{field("width", __("Width", "linker-tools"))}
												{field("depth", __("Depth", "linker-tools"))}
												{roofDimensions}
												{field(
													"originU",
													__("Origin east / U", "linker-tools"),
												)}
												{field(
													"originV",
													__("Origin north / V", "linker-tools"),
												)}
												<label className="sc-field">
													<span>{__("Drawing source", "linker-tools")}</span>
													<input
														value={fields.source}
														onChange={(e) => {
															const value = e.currentTarget.value;
															setFields((previous) => ({
																...previous,
																source: value,
															}));
														}}
													/>
												</label>
												<label className="sc-check">
													<input
														type="checkbox"
														checked={confirmed}
														onChange={(e) =>
															setConfirmed(e.currentTarget.checked)
														}
													/>
													{__(
														"I confirm these dimensions and permission to use this drawing.",
														"linker-tools",
													)}
												</label>
												{!(map && firstMapRoof) &&
													!geometry.coordinate_system.anchor &&
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
											</details>
										)}
										<details className="sc-studio-obstacle">
											<summary>{__("Raised obstacle", "linker-tools")}</summary>
											<button
												type="button"
												disabled={!roof || mapToolUnavailable("obstacle")}
												aria-pressed={tool === "obstacle"}
												onClick={() => startTool("obstacle")}
											>
												{__("Obstacle", "linker-tools")}
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
										</details>
									</>
								}
								modules={
									<>
										<p className="sc-field-help">
											{module
												? sprintf(
														__(
															"Generic %s W PV module (reference only — not supplied by Linker)",
															"linker-tools",
														),
														formatComputedDecimal(
															module.stc_power_w,
															config.locale,
														),
													)
												: __(
														"PV modules are design references and are not supplied by Linker.",
														"linker-tools",
													)}
										</p>
										{moduleChoice}
										<button
											type="button"
											disabled={!roof || mapToolUnavailable("modules")}
											aria-pressed={tool === "modules"}
											onClick={() => startTool("modules")}
										>
											{__("Place modules", "linker-tools")}
										</button>
										{moduleLayout}
										{!placingOnMap && (
											<div className="sc-fields">
												{field(
													"originU",
													__("Origin east / U", "linker-tools"),
												)}
												{field(
													"originV",
													__("Origin north / V", "linker-tools"),
												)}
											</div>
										)}

										<button
											type="button"
											disabled={!module || !roof}
											onClick={() => placeModules()}
										>
											{__("Place module group", "linker-tools")}
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
									</>
								}
								summary={
									<>
										<h3>{__("Roof summary", "linker-tools")}</h3>
										{geometry.roofs.map((face) => (
											<div className="sc-roof-face-summary" key={face.id}>
												<strong>{face.name}</strong>
												<span>
													{format(
														ringArea(face.boundary_uv) -
															face.holes_uv.reduce(
																(sum, ring) => sum + ringArea(ring),
																0,
															),
													) + " m²"}
												</span>
											</div>
										))}
										<p>
											{annualGenerationKwh === null
												? __(
														"Calculate annual yield from the roof layout and site in the energy step.",
														"linker-tools",
													)
												: __(
														"Annual yield uses the project’s calculated solar profile.",
														"linker-tools",
													)}
										</p>
									</>
								}
							/>
						</div>
					</fieldset>
					<ImageCalibrationWorkspace
						geometry={geometry}
						roofId={null}
						locale={config.locale}
						disabled={blocked || importOpen || vertices.length > 0}
						onActivity={setCalibrationOpen}
						commit={(command) => {
							if (!commit({ calibration: command })) return false;
							setView("plan");
							startTool("select");
							select(command.edits[1].value.id);
							return true;
						}}
					/>
					{error && <p role="alert">{error}</p>}
				</section>
			)}
			<details className="sc-card sc-product-filter">
				<summary>{__("Solar generation estimate", "linker-tools")}</summary>
				<fieldset disabled={blocked || calibrationOpen}>
					<p className="sc-muted">
						{__(
							"Compare systems uses JRC PVGIS to estimate AC generation from the location, array details and settings below. Energy comparisons use the period covered by both the solar and energy use profiles.",
							"linker-tools",
						)}
					</p>
					<div className="sc-fields">
						{showCoordinates && !(showLocation && manualLocation) && (
							<SiteCoordinates
								site={site}
								locale={config.locale}
								change={coordinateChange}
								onValidity={setCoordinatesValid}
							/>
						)}
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
				</fieldset>
			</details>
			{mode === "roof" && geometry.sources.length > 0 && (
				<details className="sc-card sc-product-filter">
					<summary>{__("Source properties", "linker-tools")}</summary>
					<div className="sc-fields">
						{geometry.sources.map((source) => (
							<fieldset key={source.id}>
								<legend>{source.note}</legend>
								<dl className="sc-source-measurements">
									<SourceMeasurements source={source} locale={config.locale} />
								</dl>
								<GeometryExportPermission
									value={source.permissions.export}
									disabled={
										blocked ||
										Object.hasOwn(
											readGeometryImports(inputs.geometry_imports).selected,
											source.id,
										)
									}
									onChange={(permission) =>
										commit({
											type: "put_source",
											before: source,
											value: {
												...source,
												permissions: {
													...source.permissions,
													export: permission,
												},
											},
										})
									}
								/>
							</fieldset>
						))}
					</div>
				</details>
			)}
			{geometryImport && (
				<div hidden={!editingLayout}>
					<GeometryIntake
						geometry={geometry}
						projectId={geometryImport.projectId}
						session={session}
						client={client}
						locale={config.locale}
						recheck={geometryImport.recheck}
						disabled={blocked || usingTool}
						onActivity={geometryImportActivity}
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
							onLayoutChange?.();
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
				</div>
			)}
			{wiring}
			{!editingLayout && continueToEnergy}
		</section>
	);
}
