import { useEffect, useId, useMemo, useRef, useState } from "react";
import type { RefObject } from "react";
import { Map as MapLibreMap, AttributionControl, Marker } from "maplibre-gl";
import type {
	GeoJSONSource,
	MapMouseEvent,
	StyleSpecification,
} from "maplibre-gl";
import type { GeometryDocument, PanelPose } from "../../domain/geometry.ts";
import { geographicMapGeometry } from "../../domain/mapGeometry.ts";
import { MapRequestScope } from "../../data/mapRequests.ts";
import { MapPickGate } from "../../data/MapPickGate.ts";
import { MapPrefixController } from "../../data/MapPrefixController.ts";
import { createMapDrawingController } from "../../data/MapDrawingController.ts";
import type { MapInteraction } from "../../data/mapInteraction.ts";
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
	interaction = null,
}: {
	document: GeometryDocument;
	poses: readonly PanelPose[];
	selected: string | null;
	select: (id: string) => void;
	disabled: boolean;
	openReferences: () => void;
	camera: RefObject<MapCamera | null>;
	interaction?: MapInteraction | null;
}) {
	const host = useRef<HTMLDivElement>(null),
		mapRef = useRef<MapLibreMap | null>(null),
		releaseExternal = useRef<(() => void) | null>(null),
		[external, setExternal] = useState(false),
		[attempt, setAttempt] = useState(0),
		[status, setStatus] = useState<"loading" | "ready" | "failed">("loading"),
		[readyMap, setReadyMap] = useState<MapLibreMap | null>(null),
		[resourceFailure, setResourceFailure] = useState(false),
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
		projection,
		selected,
		select,
		disabled,
		interaction,
	});
	latest.current = { projection, selected, select, disabled, interaction };

	function fit(map: MapLibreMap) {
		const view = latest.current.projection.view;
		if (!view) return;
		// View padding/max zoom are display policy, never measurement precision.
		if (view.bounds)
			map.fitBounds([[...view.bounds[0]], [...view.bounds[1]]], {
				padding: 44,
				maxZoom: 21,
				duration: 0,
			});
		else map.jumpTo({ center: [...view.centre], zoom: 17 });
	}
	useEffect(() => {
		// This transient request never changes a persisted CMP category grant.
		const stopExternal = () => {
			releaseExternal.current?.();
			setExternal(false);
		};
		const visibility = () => {
			if (globalThis.document.visibilityState === "hidden") stopExternal();
		};
		const hidden = () => {
			if (host.current?.closest("[hidden], [inert]")) stopExternal();
		};
		const observer = new MutationObserver(hidden);
		for (
			let parent = host.current?.parentElement;
			parent;
			parent = parent.parentElement
		) {
			observer.observe(parent, {
				attributes: true,
				attributeFilter: ["hidden", "inert"],
			});
			if (parent.hasAttribute("data-linker-planner")) break;
		}
		globalThis.document.addEventListener(
			"cookieyes_consent_update",
			stopExternal,
		);
		globalThis.document.addEventListener(
			"wp_listen_for_consent_change",
			stopExternal,
		);
		globalThis.document.addEventListener("visibilitychange", visibility);
		window.addEventListener("pagehide", stopExternal);
		return () => {
			observer.disconnect();
			globalThis.document.removeEventListener(
				"cookieyes_consent_update",
				stopExternal,
			);
			globalThis.document.removeEventListener(
				"wp_listen_for_consent_change",
				stopExternal,
			);
			globalThis.document.removeEventListener("visibilitychange", visibility);
			window.removeEventListener("pagehide", stopExternal);
		};
	}, [projection.view !== null]);

	const available = projection.view !== null;
	useEffect(() => {
		if (!host.current || !available) return;
		let disposed = false;
		let initialized = false;
		let map: MapLibreMap | null = null;
		let resize: ResizeObserver | null = null;
		const requests = new MapRequestScope(external);
		setStatus("loading");
		setResourceFailure(false);
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
			const view = latest.current.projection.view!;
			const saved = camera.current;
			map = new MapLibreMap({
				container: host.current,
				style: external ? STREET_STYLE : ownStyle,
				transformRequest: requests.transform,
				center: saved?.centre ?? [...view.centre],
				zoom: saved?.zoom ?? 17,
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
			function updateOverlay() {
				if (disposed || !latest.current.projection.view) return;
				const data = latest.current.projection.view.collection;
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
									kind === "roof" ? 0.65 : 0.85,
									0.2,
								],
								"fill-outline-color": colours[kind],
							},
						});
					}
					current.addLayer({
						id: SELECTED,
						type: "line",
						source: SOURCE,
						filter: ["==", ["get", "object_id"], latest.current.selected ?? ""],
						paint: { "line-color": colours.selected, "line-width": 3 },
					});
				}
			}
			const ready = () => {
				if (disposed) return;
				try {
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
					latest.current.disabled ||
					latest.current.interaction ||
					pickGate.current.blocked ||
					!current.getSource(SOURCE)
				)
					return;
				const hit = current
					.queryRenderedFeatures(event.point, { layers: LAYERS })
					.find((feature) => typeof feature.properties?.object_id === "string");
				if (hit) latest.current.select(hit.properties!.object_id as string);
			};
			const resourceError = (event: { error: Error }) => {
				if (!disposed) {
					setFailure(failureDiagnostic("resource", event.error));
					setResourceFailure(true);
					if (!initialized) setStatus("failed");
				}
			};
			const contextLost = () => {
				if (!disposed) {
					setReadyMap(null);
					setStatus("failed");
				}
			};
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
				// Drawing adapters need their map sources/layers to exist at stop.
				// Their public disposal reports failures without preventing remove.
				releaseDrawing.current?.();
				heightMarker.current?.remove();
				heightMarker.current = null;
				requests.release();
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
			if (external) releaseExternal.current = release;
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
	}, [available, external, attempt, camera]);
	useEffect(() => {
		const map = mapRef.current,
			value = latest.current.interaction;
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
		interaction?.key,
		interaction?.phase,
		readyMap,
		status,
		disabled,
		external,
		attempt,
		available,
	]);
	useEffect(() => {
		if (interaction?.phase === "collecting")
			prefix.current?.update(interaction.vertices);
	}, [interaction?.vertices, interaction?.phase]);
	useEffect(() => {
		const map = mapRef.current,
			point = interaction?.referencePosition;
		if (!map || map !== readyMap || status !== "ready" || !point) return;
		const element = globalThis.document.createElement("span");
		element.className = "lp-map-height-reference";
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
		if (!map || !map.getSource(SOURCE) || !projection.view) return;
		(map.getSource(SOURCE) as GeoJSONSource).setData(
			projection.view.collection,
		);
		map.setFilter(SELECTED, ["==", ["get", "object_id"], selected ?? ""]);
	}, [projection]);
	useEffect(() => {
		const map = mapRef.current;
		if (map?.getLayer(SELECTED))
			map.setFilter(SELECTED, ["==", ["get", "object_id"], selected ?? ""]);
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
					className="lp-button lp-button-secondary"
					disabled={disabled}
					onClick={openReferences}
				>
					{__("Coordinate references", "linker-tools")}
				</button>
			</Notice>
		);
	return (
		<section
			className="lp-map-view"
			aria-labelledby={label}
			data-map-status={status}
			data-map-failure={failure}
		>
			<div className="lp-map-heading">
				<h3 id={label}>{__("Project map", "linker-tools")}</h3>
				<span className="lp-eyebrow">
					{external
						? __("Street map", "linker-tools")
						: __("Project geometry", "linker-tools")}
				</span>
			</div>
			<p className="lp-profile-help">
				{__(
					"The map displays your recorded geometry using the project's geographic reference. Roof dimensions and declared source accuracy remain unchanged.",
					"linker-tools",
				)}
			</p>
			<div
				className="lp-map-toolbar"
				role="group"
				aria-label={__("Map controls", "linker-tools")}
			>
				<button
					type="button"
					className="lp-button lp-button-secondary"
					disabled={status !== "ready"}
					onClick={() => {
						if (mapRef.current) fit(mapRef.current);
					}}
				>
					{__("Show full design", "linker-tools")}
				</button>
				<button
					type="button"
					className="lp-icon-button"
					aria-label={__("Zoom in", "linker-tools")}
					disabled={status !== "ready"}
					onClick={() => mapRef.current?.zoomIn({ duration: 0 })}
				>
					+
				</button>
				<button
					type="button"
					className="lp-icon-button"
					aria-label={__("Zoom out", "linker-tools")}
					disabled={status !== "ready"}
					onClick={() => mapRef.current?.zoomOut({ duration: 0 })}
				>
					−
				</button>
				<button
					type="button"
					className="lp-button lp-button-secondary"
					disabled={status !== "ready"}
					onClick={() => mapRef.current?.jumpTo({ bearing: 0, pitch: 0 })}
				>
					{__("North up", "linker-tools")}
				</button>
			</div>
			{status === "loading" && (
				<p role="status">{__("Loading map…", "linker-tools")}</p>
			)}
			{(status === "failed" || resourceFailure) && (
				<Notice error>
					<p>
						{__(
							"The map could not be fully displayed. Your project geometry is unchanged.",
							"linker-tools",
						)}
					</p>
					<button
						type="button"
						className="lp-button lp-button-secondary"
						onClick={() => setAttempt((value) => value + 1)}
					>
						{__("Retry loading map", "linker-tools")}
					</button>
				</Notice>
			)}
			<div
				className="lp-map-surface"
				data-collecting={interaction?.phase === "collecting" || undefined}
			>
				<div className="lp-map-host" ref={host} />
				{interaction?.phase === "collecting" && (
					<span className="lp-map-reticle" aria-hidden="true" />
				)}
			</div>
			{interaction?.phase === "collecting" && (
				<button
					type="button"
					className="lp-button lp-button-secondary"
					disabled={status !== "ready"}
					onClick={() => {
						const centre = mapRef.current?.getCenter();
						if (centre) interaction.append([centre.lng, centre.lat]);
					}}
				>
					{__("Add corner at map centre", "linker-tools")}
				</button>
			)}
			<div className="lp-map-provider">
				<p className="lp-profile-help">
					{__(
						"Loading the street map sends your IP address and the area shown to OpenFreeMap and its delivery network. The street map is for orientation.",
						"linker-tools",
					)}
				</p>
				<div className="lp-inline-actions">
					<button
						type="button"
						className="lp-button lp-button-secondary"
						onClick={() => {
							if (external) releaseExternal.current?.();
							setExternal(!external);
						}}
					>
						{external
							? __("Hide street map", "linker-tools")
							: __("Load street map", "linker-tools")}
					</button>
					<a
						href="https://openfreemap.org/privacy/"
						target="_blank"
						rel="noopener noreferrer"
					>
						{__("OpenFreeMap privacy policy", "linker-tools")}
					</a>
				</div>
			</div>
		</section>
	);
}
