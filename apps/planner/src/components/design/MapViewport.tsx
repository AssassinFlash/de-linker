import { onMapConsentChange } from "../../data/roofImageryConsent.ts";
import {
	useEffect,
	useId,
	useLayoutEffect,
	useMemo,
	useRef,
	useState,
} from "react";
import type { RefObject } from "react";
import { Map as MapLibreMap, AttributionControl, Marker } from "maplibre-gl";
import type {
	FilterSpecification,
	GeoJSONSource,
	MapMouseEvent,
	MapSourceDataEvent,
	StyleSpecification,
} from "maplibre-gl";
import type {
	GeometryDocument,
	PanelPose,
	Vec2,
} from "../../domain/geometry.ts";
import { imagerySourceKey } from "../../domain/place.ts";
import type { PlaceImagery } from "../../domain/place.ts";
import { geographicMapGeometry } from "../../domain/mapGeometry.ts";
import { MapRequestScope } from "../../data/mapRequests.ts";
import { MapPickGate } from "../../data/MapPickGate.ts";
import { MapPrefixController } from "../../data/MapPrefixController.ts";
import { createMapDrawingController } from "../../data/MapDrawingController.ts";
import type {
	ArrayPlacement,
	MapInteraction,
} from "../../data/mapInteraction.ts";
import { drawingBridge } from "../../domain/mapDrawingGeometry.ts";
import { geographicOnRoof } from "../../domain/geographic.ts";
import { __ } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";

export interface MapCamera {
	centre: [number, number];
	zoom: number;
	bearing: number;
	pitch: number;
}

const SOURCE = "linker-project-geometry";
const SELECTED = "linker-map-selected";
const KINDS = ["roof", "keepout", "obstacle", "module"] as const;
const LAYERS = KINDS.map((kind) => `linker-map-${kind}`);
// Official public style, checked in the Apify provider dossier. It is never
// requested until the visitor explicitly asks to load this external service.
const STREET_STYLE = "https://tiles.openfreemap.org/styles/liberty";
// The selected aerial mosaic has a separate grant from the street style.
const IMAGERY_SOURCE = "linker-site-imagery";
const IMAGERY_LAYER = "linker-site-imagery";
// The mapped building at the site, drawn dashed until the visitor adopts it.
const SITE_OUTLINE_SOURCE = "linker-site-outline";
const SITE_OUTLINE_LAYER = "linker-site-outline";

function selectedFilter(selected: string | null): FilterSpecification {
	return [
		"any",
		["==", ["get", "object_id"], selected ?? ""],
		["==", ["get", "array_id"], selected ?? ""],
	];
}

function aerialOriginsOf(mosaic: PlaceImagery | null): string[] {
	const tile = mosaic?.tiles[0];
	if (!tile) return [];
	try {
		return [new URL(tile).origin];
	} catch {
		return [];
	}
}

function imageryBeforeLayer(map: MapLibreMap): string | undefined {
	if (map.getLayer(SITE_OUTLINE_LAYER)) return SITE_OUTLINE_LAYER;
	return map.getLayer(`linker-map-${KINDS[0]}`)
		? `linker-map-${KINDS[0]}`
		: undefined;
}

function siteOutlineBeforeLayer(map: MapLibreMap): string | undefined {
	return map.getLayer(`linker-map-${KINDS[0]}`)
		? `linker-map-${KINDS[0]}`
		: undefined;
}

/** Bounded renderer diagnostics exclude message bodies, URL paths/queries,
 * project data and source contents. They identify a failed runtime boundary. */
function failureDiagnostic(stage: string, cause: unknown): string {
	const error = cause instanceof Error ? cause : null;
	const extra = cause as { status?: unknown; url?: unknown } | null;
	let origin: string | null = null;
	try {
		if (typeof extra?.url === "string") origin = new URL(extra.url).origin;
	} catch {
		/* Not a URL. */
	}
	return JSON.stringify({
		stage,
		name: error?.name ?? "unknown",
		http_status: typeof extra?.status === "number" ? extra.status : null,
		origin,
		frames:
			error?.stack
				?.split("\n")
				.filter((line) => /^\s+at /.test(line))
				.slice(0, 5)
				.map((line) => line.replace(/[?#][^:)\s]*/g, "")) ?? [],
	});
}

export default function MapViewport({
	document: geometry,
	poses,
	selected,
	select,
	disabled,
	openReferences,
	camera,
	imagery = null,
	viewOnly = false,
	onAerialReady,
	takeImageryConsent,
	siteCentre = null,
	siteOutline = null,
	interaction: mapInteraction = null,
	placement: arrayPlacement = null,
}: {
	document: GeometryDocument;
	poses: readonly PanelPose[];
	selected: string | null;
	select: (id: string) => void;
	disabled: boolean;
	openReferences: () => void;
	camera: RefObject<MapCamera | null>;
	interaction?: MapInteraction | null;
	placement?: ArrayPlacement | null;
	/** The official aerial mosaic for this site, or null where none exists. */
	imagery?: PlaceImagery | null;
	viewOnly?: boolean;
	onAerialReady?: (source: PlaceImagery | null) => void;
	takeImageryConsent?: ((source: PlaceImagery) => boolean) | undefined;
	/** The declared site position, so the mosaic is visible before geometry exists. */
	siteCentre?: readonly [number, number] | null;
	/** The mapped building outline at the site, drawn as the starting point. */
	siteOutline?: {
		ring: [number, number][];
		source: string;
		licence: string;
		planes?: readonly {
			id: number;
			polygon: readonly [number, number][];
			tilt_deg: number;
			azimuth_deg: number;
			area_m2: number;
		}[];
	} | null;
}) {
	const interaction = viewOnly ? null : mapInteraction;
	const placement = viewOnly ? null : arrayPlacement;
	const host = useRef<HTMLDivElement>(null),
		mapRef = useRef<MapLibreMap | null>(null),
		releaseExternal = useRef<(() => void) | null>(null),
		[grant, setGrant] = useState<string | null>(null),
		[attempt, setAttempt] = useState(0),
		[status, setStatus] = useState<"loading" | "ready" | "failed">("loading"),
		[readyAerialMap, setReadyAerialMap] = useState<MapLibreMap | null>(null),
		[readyMap, setReadyMap] = useState<MapLibreMap | null>(null),
		[resourceFailure, setResourceFailure] = useState(false),
		[aerialFailure, setAerialFailure] = useState(false),
		[failure, setFailure] = useState<string | null>(null),
		label = useId();
	const releaseDrawing = useRef<(() => void) | null>(null),
		prefix = useRef<MapPrefixController | null>(null),
		pickGate = useRef(new MapPickGate());
	const heightMarker = useRef<Marker | null>(null);
	const projection = useMemo(() => {
		try {
			return { view: geographicMapGeometry(geometry, poses), error: null };
		} catch (error) {
			return {
				view: null,
				error: error instanceof Error ? error.message : "map_geometry_invalid",
			};
		}
	}, [geometry, poses]);
	const latest = useRef({
		geometry,
		projection,
		selected,
		select,
		disabled,
		interaction,
		placement,
		imagery,
		siteCentre,
		siteOutline,
	});
	latest.current = {
		geometry,
		projection,
		selected,
		select,
		disabled,
		interaction,
		placement,
		imagery,
		siteCentre,
		siteOutline,
	};
	function placeArray(map: MapLibreMap, point: Vec2) {
		const target = latest.current.placement;
		if (!target) return;
		const hit = map
			.queryRenderedFeatures(map.project({ lng: point[0], lat: point[1] }), {
				layers: ["linker-map-roof"],
			})
			.some((feature) => feature.properties?.object_id === target.roofId);
		if (!hit) return;
		const roof = latest.current.geometry.roofs.find(
			(roof) => roof.id === target.roofId,
		)!;
		target.place(
			geographicOnRoof(drawingBridge(latest.current.geometry), roof, point),
		);
	}

	function fit(map: MapLibreMap) {
		const view = latest.current.projection.view;
		if (!view) {
			if (latest.current.siteCentre)
				map.jumpTo({ center: [...latest.current.siteCentre], zoom: 19 });
			return;
		}
		// View padding/max zoom are display policy, never measurement precision.
		if (view.bounds)
			map.fitBounds([[...view.bounds[0]], [...view.bounds[1]]], {
				padding: 44,
				maxZoom: 21,
				duration: 0,
			});
		else map.jumpTo({ center: [...view.centre], zoom: 17 });
	}
	const offeredSource = imagery?.tiles.length
		? imagerySourceKey(imagery)
		: STREET_STYLE;
	useEffect(() => {
		if (imagery && takeImageryConsent?.(imagery)) setGrant(offeredSource);
	}, [imagery, offeredSource, takeImageryConsent]);
	const external = grant === offeredSource;
	const street = external && offeredSource === STREET_STYLE;
	const aerial = external && !street ? grant : null;
	useLayoutEffect(() => {
		if (grant !== null && grant !== offeredSource) {
			releaseExternal.current?.();
			setGrant(null);
		}
	}, [grant, offeredSource]);
	useEffect(() => {
		const stopExternal = () => {
			releaseExternal.current?.();
			setGrant(null);
		};
		const unsubscribe = onMapConsentChange(stopExternal);
		window.addEventListener("pagehide", stopExternal);
		return () => {
			unsubscribe();
			window.removeEventListener("pagehide", stopExternal);
		};
	}, []);

	// Without a design anchor the geometry cannot be projected, but the site's
	// own position is enough to show the aerial mosaic and let the visitor draw:
	// never infer north, and never present the mosaic as a survey frame.
	const available = projection.view !== null || siteCentre !== null;
	const readyImagery =
		available &&
		aerial &&
		status === "ready" &&
		readyMap &&
		readyMap === readyAerialMap &&
		readyMap === mapRef.current
			? imagery
			: null;
	const editableImagery = viewOnly ? null : readyImagery;
	useLayoutEffect(() => {
		onAerialReady?.(editableImagery);
		return () => onAerialReady?.(null);
	}, [onAerialReady, editableImagery]);
	const drawing =
		interaction?.requiresAerial && !readyImagery ? null : interaction;
	useEffect(() => {
		if (!host.current || !available) return;
		let disposed = false;
		let initialized = false;
		let map: MapLibreMap | null = null;
		let resize: ResizeObserver | null = null;
		const mosaic = aerial ? latest.current.imagery : null;
		const requests = new MapRequestScope(street, aerialOriginsOf(mosaic));
		setReadyAerialMap(null);
		setStatus("loading");
		setResourceFailure(false);
		setAerialFailure(false);
		setFailure(null);
		try {
			const style = getComputedStyle(host.current);
			function token(name: string) {
				const value = style.getPropertyValue(name).trim();
				if (!value) throw new Error("map_design_tokens_missing");
				return value;
			}
			const colours = {
				roof: token("--proto-neutral-300"),
				module: token("--proto-teal-900"),
				obstacle: token("--proto-neutral-600"),
				keepout: token("--proto-teal-700"),
				selected: token("--proto-teal-400"),
				background: token("--proto-neutral-100"),
			};
			const ownStyle: StyleSpecification = {
				version: 8,
				sources: {},
				layers: [
					{
						id: "project-background",
						type: "background",
						paint: { "background-color": colours.background },
					},
				],
			};
			// A site without a design anchor still opens the map: the centre and
			// the mosaic come from the declared position, the overlay stays empty.
			const view = latest.current.projection.view ?? {
				collection: { type: "FeatureCollection", features: [] },
				bounds: null,
				centre: [...(latest.current.siteCentre ?? [0, 0])],
			};
			const saved = camera.current;
			map = new MapLibreMap({
				container: host.current,
				style: street ? STREET_STYLE : ownStyle,
				transformRequest: requests.transform,
				center: saved?.centre ?? [...view.centre],
				zoom: saved?.zoom ?? 19,
				bearing: saved?.bearing ?? 0,
				pitch: saved?.pitch ?? 0,
				attributionControl: false,
				cooperativeGestures: true,
				locale: {
					"Map.Title": __("Project map", "linker-tools"),
					"AttributionControl.ToggleAttribution": __(
						"Map attribution",
						"linker-tools",
					),
					"AttributionControl.MapFeedback": __("Map feedback", "linker-tools"),
					"CooperativeGesturesHandler.WindowsHelpText": __(
						"Use Ctrl + scroll to zoom the map",
						"linker-tools",
					),
					"CooperativeGesturesHandler.MacHelpText": __(
						"Use ⌘ + scroll to zoom the map",
						"linker-tools",
					),
					"CooperativeGesturesHandler.MobileHelpText": __(
						"Use two fingers to move the map",
						"linker-tools",
					),
				},
				// Roof properties need close inspection, independent of tile detail.
				maxZoom: 24,
			});
			const current = map;
			mapRef.current = current;
			current.addControl(
				new AttributionControl({ compact: false }),
				"bottom-right",
			);
			current
				.getCanvas()
				.setAttribute("aria-label", __("Project map", "linker-tools"));
			function updateSiteOutline() {
				const shape = latest.current.siteOutline;
				if (!shape || shape.ring.length < 3) {
					if (current.getLayer(SITE_OUTLINE_LAYER))
						current.removeLayer(SITE_OUTLINE_LAYER);
					if (current.getSource(SITE_OUTLINE_SOURCE))
						current.removeSource(SITE_OUTLINE_SOURCE);
					return;
				}
				const ring = [...shape.ring];
				const first = ring[0];
				const last = ring[ring.length - 1];
				if (first && last && (first[0] !== last[0] || first[1] !== last[1]))
					ring.push(first);
				const data = {
					type: "FeatureCollection" as const,
					features: [
						{
							type: "Feature" as const,
							properties: {},
							geometry: { type: "Polygon" as const, coordinates: [ring] },
						},
					],
				};
				if (current.getSource(SITE_OUTLINE_SOURCE)) {
					(current.getSource(SITE_OUTLINE_SOURCE) as GeoJSONSource).setData(
						data,
					);
					return;
				}
				current.addSource(SITE_OUTLINE_SOURCE, { type: "geojson", data });
				current.addLayer(
					{
						id: SITE_OUTLINE_LAYER,
						type: "line",
						source: SITE_OUTLINE_SOURCE,
						paint: {
							"line-color": colours.selected,
							"line-width": 2.5,
							"line-dasharray": [2, 1.5],
						},
					},
					siteOutlineBeforeLayer(current),
				);
			}
			function installImagery() {
				if (!mosaic) return;
				// Under the site outline and project geometry so both stay legible on top.
				const before = imageryBeforeLayer(current);
				current.addSource(IMAGERY_SOURCE, {
					type: "raster",
					tiles: [...mosaic.tiles],
					tileSize: 256,
					attribution: `${mosaic.credit} — ${mosaic.licence}`,
				});
				current.addLayer(
					{
						id: IMAGERY_LAYER,
						type: "raster",
						source: IMAGERY_SOURCE,
						paint: { "raster-opacity": 1 },
					},
					before,
				);
			}
			function updateOverlay() {
				if (disposed) return;
				const data = latest.current.projection.view?.collection ?? {
					type: "FeatureCollection" as const,
					features: [],
				};
				if (current.getSource(SOURCE))
					(current.getSource(SOURCE) as GeoJSONSource).setData(data);
				else {
					current.addSource(SOURCE, { type: "geojson", data });
					for (const kind of KINDS) {
						current.addLayer({
							id: `linker-map-${kind}`,
							type: "fill",
							source: SOURCE,
							filter: ["==", ["get", "kind"], kind],
							paint: {
								"fill-color": colours[kind],
								"fill-opacity": [
									"case",
									["get", "included"],
									kind === "roof" ? 0.25 : 0.85,
									0.2,
								],
								"fill-outline-color":
									kind === "module" ? colours.background : colours[kind],
							},
						});
					}
					current.addLayer({
						id: SELECTED,
						type: "line",
						source: SOURCE,
						filter: selectedFilter(latest.current.selected),
						paint: { "line-color": colours.selected, "line-width": 3 },
					});
				}
			}
			const ready = () => {
				if (disposed) return;
				try {
					installImagery();
					updateSiteOutline();
					updateOverlay();
					if (!saved) fit(current);
					initialized = true;
					setStatus("ready");
					setReadyMap(current);
				} catch (error) {
					setFailure(failureDiagnostic("overlay", error));
					setStatus("failed");
				}
			};
			const pick = (event: MapMouseEvent) => {
				if (
					disposed ||
					(latest.current.disabled && !latest.current.placement) ||
					latest.current.interaction ||
					pickGate.current.blocked ||
					!current.getSource(SOURCE)
				)
					return;
				if (latest.current.placement) {
					placeArray(current, [event.lngLat.lng, event.lngLat.lat]);
					return;
				}
				const hit = current
					.queryRenderedFeatures(event.point, { layers: LAYERS })
					.find((feature) => typeof feature.properties?.object_id === "string");
				if (hit) latest.current.select(hit.properties!.object_id as string);
			};
			// MapLibre counts errored tiles as settled and silently handles HTTP 404s.
			// Inspect the in-view raster tiles after the renderer paints the frame.
			const aerialTileLoading = ({ sourceId, tile }: MapSourceDataEvent) => {
				if (sourceId === IMAGERY_SOURCE && tile) setReadyAerialMap(null);
			};
			const aerialIdle = () => {
				if (!current.getSource(IMAGERY_SOURCE)) return;
				const manager = current.style.tileManagers[IMAGERY_SOURCE];
				if (!manager?.loaded()) return;
				const tiles = manager.getIds();
				const loaded =
					tiles.length > 0 &&
					tiles.every((id) => manager.getTileByID(id)?.state === "loaded");
				setReadyAerialMap(loaded ? current : null);
				setAerialFailure(!loaded);
			};
			const resourceError = (event: { error: Error }) => {
				if (!disposed) {
					setFailure(failureDiagnostic("resource", event.error));
					setResourceFailure(true);
					if (mosaic) setReadyAerialMap(null);
					if (!initialized) setStatus("failed");
				}
			};
			const contextLost = () => {
				if (!disposed) {
					setReadyMap(null);
					setStatus("failed");
				}
			};
			if (mosaic) {
				current.on("sourcedataloading", aerialTileLoading);
				current.on("idle", aerialIdle);
			}
			current.on("load", ready);
			const beginPointer = (event: PointerEvent) => {
				if (current.getCanvas().contains(event.target as Node))
					pickGate.current.beginPointer();
			};
			window.addEventListener("pointerdown", beginPointer, true);
			current.on("click", pick);
			current.on("error", resourceError);
			current.getCanvas().addEventListener("webglcontextlost", contextLost);
			resize = new ResizeObserver(() => {
				if (!disposed) current.resize();
			});
			resize.observe(host.current);
			const release = () => {
				if (disposed) return;
				disposed = true;
				requests.release();
				// Drawing adapters need their map sources/layers to exist at stop.
				releaseDrawing.current?.();
				heightMarker.current?.remove();
				heightMarker.current = null;
				resize?.disconnect();
				if (initialized) {
					const centre = current.getCenter();
					camera.current = {
						centre: [centre.lng, centre.lat],
						zoom: current.getZoom(),
						bearing: current.getBearing(),
						pitch: current.getPitch(),
					};
				}
				if (mosaic) {
					current.off("sourcedataloading", aerialTileLoading);
					current.off("idle", aerialIdle);
				}
				current.off("load", ready);
				current.off("click", pick);
				current.off("error", resourceError);
				window.removeEventListener("pointerdown", beginPointer, true);
				current
					.getCanvas()
					.removeEventListener("webglcontextlost", contextLost);
				if (mapRef.current === current) mapRef.current = null;
				// remove() cancels outstanding resources and owns worker/GL cleanup.
				current.remove();
			};
			if (street || aerial) releaseExternal.current = release;
			return () => {
				if (releaseExternal.current === release) releaseExternal.current = null;
				release();
			};
		} catch (error) {
			setFailure(failureDiagnostic("initialization", error));
			disposed = true;
			requests.release();
			resize?.disconnect();
			map?.remove();
			mapRef.current = null;
			host.current?.replaceChildren();
			setStatus("failed");
		}
	}, [available, aerial, street, attempt, camera]);
	useEffect(() => {
		// The outline arrives after the map is ready, like the mosaic.
		const map = mapRef.current;
		if (!map || map !== readyMap || status !== "ready") return;
		const shape = siteOutline;
		if (!shape || shape.ring.length < 3) {
			if (map.getLayer(SITE_OUTLINE_LAYER)) map.removeLayer(SITE_OUTLINE_LAYER);
			if (map.getSource(SITE_OUTLINE_SOURCE))
				map.removeSource(SITE_OUTLINE_SOURCE);
			return;
		}
		const ring = [...shape.ring];
		const first = ring[0];
		const last = ring[ring.length - 1];
		if (first && last && (first[0] !== last[0] || first[1] !== last[1]))
			ring.push(first);
		const data = {
			type: "FeatureCollection" as const,
			features: [
				{
					type: "Feature" as const,
					properties: {},
					geometry: { type: "Polygon" as const, coordinates: [ring] },
				},
			],
		};
		if (map.getSource(SITE_OUTLINE_SOURCE)) {
			(map.getSource(SITE_OUTLINE_SOURCE) as GeoJSONSource).setData(data);
			return;
		}
		const lineColour = host.current
			? getComputedStyle(host.current)
					.getPropertyValue("--proto-teal-400")
					.trim() || "#2dd4bf"
			: "#2dd4bf";
		map.addSource(SITE_OUTLINE_SOURCE, { type: "geojson", data });
		map.addLayer(
			{
				id: SITE_OUTLINE_LAYER,
				type: "line",
				source: SITE_OUTLINE_SOURCE,
				paint: {
					"line-color": lineColour,
					"line-width": 2.5,
					"line-dasharray": [2, 1.5],
				},
			},
			siteOutlineBeforeLayer(map),
		);
	}, [readyMap, status, siteOutline]);
	useEffect(() => {
		const map = mapRef.current,
			value = drawing;
		if (!map || map !== readyMap || status !== "ready" || !value || disabled)
			return;
		let stopped = false;
		const blockMapPick = () => pickGate.current.block();
		const failed = () => {
			const current = latest.current.interaction;
			if (current?.key === value.key) current.failed();
			else value.failed();
		};
		let controller: { dispose: () => void };
		try {
			const style = getComputedStyle(host.current!);
			function hex(name: string): `#${string}` {
				const value = style.getPropertyValue(name).trim();
				if (!/^#[a-f0-9]{6}$/i.test(value))
					throw new Error("map_design_tokens_missing");
				return value as `#${string}`;
			}
			const ink = hex("--proto-teal-700"),
				paper = hex("--proto-neutral-100");
			if (value.phase === "collecting") {
				const collector = new MapPrefixController(map, value.vertices, ink, {
					append: (point) => latest.current.interaction?.append(point),
					...(value.trace
						? {
								trace: (corners: readonly Vec2[]) =>
									latest.current.interaction?.trace?.(corners),
							}
						: {}),
					blockMapPick,
					failed,
				});
				prefix.current = collector;
				controller = collector;
			} else {
				controller = createMapDrawingController(
					map,
					{ kind: "edit", ring: value.vertices },
					{
						raw: () => undefined,
						transaction: (change) =>
							latest.current.interaction?.transaction(change),
						interrupted: () => latest.current.interaction?.interrupted(),
						failed,
						blockMapPick,
					},
					{ ink, paper },
				);
			}
		} catch {
			failed();
			return;
		}
		const release = () => {
			if (stopped) return;
			stopped = true;
			prefix.current = null;
			controller.dispose();
			if (releaseDrawing.current === release) releaseDrawing.current = null;
		};
		releaseDrawing.current = release;
		return release;
	}, [
		drawing?.key,
		drawing?.phase,
		Boolean(drawing?.trace),
		readyMap,
		status,
		disabled,
		external,
		attempt,
		available,
	]);
	useEffect(() => {
		if (drawing?.phase === "collecting")
			prefix.current?.update(drawing.vertices);
	}, [drawing?.vertices, drawing?.phase]);
	useEffect(() => {
		const map = mapRef.current,
			point = interaction?.referencePosition;
		if (!map || map !== readyMap || status !== "ready" || !point) return;
		const element = globalThis.document.createElement("span");
		element.className = "sc-map-height-reference";
		element.textContent = __("Height reference", "linker-tools");
		const marker = new Marker({ element, anchor: "bottom", offset: [0, -12] })
			.setLngLat([...point])
			.addTo(map);
		heightMarker.current = marker;
		return () => {
			marker.remove();
			if (heightMarker.current === marker) heightMarker.current = null;
		};
	}, [
		interaction?.key,
		interaction?.referencePosition,
		readyMap,
		status,
		external,
		attempt,
	]);
	useEffect(() => {
		const map = mapRef.current;
		if (!map || !map.getSource(SOURCE)) return;
		(map.getSource(SOURCE) as GeoJSONSource).setData(
			projection.view?.collection ?? {
				type: "FeatureCollection",
				features: [],
			},
		);
		map.setFilter(SELECTED, selectedFilter(selected));
	}, [projection]);
	useEffect(() => {
		const map = mapRef.current;
		if (map?.getLayer(SELECTED))
			map.setFilter(SELECTED, selectedFilter(selected));
	}, [selected]);

	if (!available)
		return (
			<Notice>
				<p>
					{projection.error === "map_geographic_reference_required"
						? __(
								"The map needs a geographic origin and a recorded true-north reference for this design.",
								"linker-tools",
							)
						: __(
								"This geometry cannot be shown on the map. You can still switch views or edit numeric properties.",
								"linker-tools",
							)}
				</p>
				<button
					type="button"
					className="sc-button"
					disabled={disabled}
					onClick={openReferences}
				>
					{__("Coordinate references", "linker-tools")}
				</button>
			</Notice>
		);
	return (
		<section
			className="sc-map-view"
			aria-labelledby={label}
			data-map-status={status}
			data-map-failure={failure}
			data-array-placement={placement ? true : undefined}
		>
			<div className="sc-map-heading">
				<h3 id={label}>{__("Project map", "linker-tools")}</h3>
				<span className="sc-eyebrow">
					{external
						? imagery
							? __("Aerial imagery", "linker-tools")
							: __("Street map", "linker-tools")
						: __("Project geometry", "linker-tools")}
				</span>
			</div>
			{viewOnly && (
				<p className="sc-field-help" id={`${label}-viewing`}>
					{__(
						"This aerial imagery is for viewing only. Showing it sends your IP address and the area shown to the imagery provider.",
						"linker-tools",
					)}
				</p>
			)}
			<div className="sc-map-consent">
				<span>
					{external
						? __("The external map is on.", "linker-tools")
						: __(
								"Map tiles stay off until you allow the provider to load them.",
								"linker-tools",
							)}
				</span>
				<button
					type="button"
					className="sc-button"
					aria-describedby={viewOnly ? `${label}-viewing` : undefined}
					aria-pressed={external}
					onClick={() => {
						if (external) releaseExternal.current?.();
						setGrant(external ? null : offeredSource);
					}}
				>
					{imagery
						? external
							? __("Hide aerial map", "linker-tools")
							: __("Show aerial map", "linker-tools")
						: external
							? __("Hide street map", "linker-tools")
							: __("Load street map", "linker-tools")}
				</button>
			</div>
			<div
				className="sc-map-toolbar"
				role="group"
				aria-label={__("Map controls", "linker-tools")}
			>
				{placement && (
					<>
						<p className="sc-field-help">
							{__(
								"Click inside the roof to position the panels.",
								"linker-tools",
							)}
						</p>
						<button
							type="button"
							className="sc-button sc-primary"
							disabled={status !== "ready"}
							onClick={() => {
								const map = mapRef.current;
								if (map) {
									const centre = map.getCenter();
									placeArray(map, [centre.lng, centre.lat]);
								}
							}}
						>
							{__("Place panels at map centre", "linker-tools")}
						</button>
						<button
							type="button"
							className="sc-button"
							onClick={placement.review}
						>
							{__("Review panel layout", "linker-tools")}
						</button>
					</>
				)}
				<button
					type="button"
					className="sc-button"
					disabled={status !== "ready"}
					onClick={() => {
						if (mapRef.current) fit(mapRef.current);
					}}
				>
					{__("Show full design", "linker-tools")}
				</button>
				<button
					type="button"
					className="sc-icon-button"
					aria-label={__("Zoom in", "linker-tools")}
					disabled={status !== "ready"}
					onClick={() => mapRef.current?.zoomIn({ duration: 0 })}
				>
					+
				</button>
				<button
					type="button"
					className="sc-icon-button"
					aria-label={__("Zoom out", "linker-tools")}
					disabled={status !== "ready"}
					onClick={() => mapRef.current?.zoomOut({ duration: 0 })}
				>
					−
				</button>
				<button
					type="button"
					className="sc-button"
					disabled={status !== "ready"}
					onClick={() => mapRef.current?.jumpTo({ bearing: 0, pitch: 0 })}
				>
					{__("North up", "linker-tools")}
				</button>
			</div>
			{(status === "loading" ||
				(aerial &&
					!readyImagery &&
					!resourceFailure &&
					!aerialFailure &&
					status !== "failed")) && (
				<p role="status">{__("Loading map…", "linker-tools")}</p>
			)}
			{(status === "failed" || resourceFailure || aerialFailure) && (
				<Notice error>
					<p>
						{__(
							"The map could not be fully displayed. Your project geometry is unchanged.",
							"linker-tools",
						)}
					</p>
					<button
						type="button"
						className="sc-button"
						onClick={() => setAttempt((value) => value + 1)}
					>
						{__("Retry loading map", "linker-tools")}
					</button>
				</Notice>
			)}
			<div
				className="sc-map-surface"
				data-collecting={drawing?.phase === "collecting" || undefined}
			>
				<div className="sc-map-host" ref={host} />
				{drawing?.phase === "collecting" && (
					<span className="sc-map-reticle" aria-hidden="true" />
				)}
			</div>
			{drawing?.phase === "collecting" && (
				<button
					type="button"
					className="sc-button"
					disabled={status !== "ready"}
					onClick={() => {
						const centre = mapRef.current?.getCenter();
						if (centre) drawing.append([centre.lng, centre.lat]);
					}}
				>
					{__("Add corner at map centre", "linker-tools")}
				</button>
			)}
			<div className="sc-map-provider">
				<p className="sc-field-help">
					{imagery
						? `${imagery.credit} — ${imagery.licence}`
						: __(
								"Loading the street map sends your IP address and the area shown to OpenFreeMap and its delivery network. The street map is for orientation.",
								"linker-tools",
							)}
				</p>
				<div className="sc-actions">
					{imagery ? (
						<a
							href={imagery.licence_url}
							target="_blank"
							rel="noopener noreferrer"
						>
							{__("Map attribution", "linker-tools")}
						</a>
					) : (
						<a
							href="https://openfreemap.org/privacy/"
							target="_blank"
							rel="noopener noreferrer"
						>
							{__("OpenFreeMap privacy policy", "linker-tools")}
						</a>
					)}
					{!imagery && (
						<p className="sc-field-help">
							{__(
								"Aerial imagery is not available. You can upload a roof plan or retry loading the map.",
								"linker-tools",
							)}
						</p>
					)}
				</div>
			</div>
		</section>
	);
}
