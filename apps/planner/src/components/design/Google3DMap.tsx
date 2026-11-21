import { useEffect, useMemo, useRef, useState } from "react";
import type {
	GeometryDocument,
	PanelPose,
	Vec3,
} from "../../domain/geometry.ts";
import { GeographicBridge } from "../../domain/geographic.ts";
import { add, vectorFromRoof } from "../../domain/coordinates.ts";
import { panelCornersUVN } from "../../domain/panelPoses.ts";
import {
	loadGoogleMaps,
	type LatLngAltitudeLiteral,
	type Map3DElementInstance,
	type Maps3DLibrary,
} from "../../data/googleMaps.ts";
import { __ } from "../../i18n.ts";
import { Notice } from "../Notice.tsx";

export interface SiteOutline3D {
	readonly ring: readonly [number, number][];
	readonly source: string;
	readonly licence: string;
	readonly planes?: readonly {
		readonly id: number;
		readonly polygon: readonly [number, number][];
		readonly tilt_deg: number;
		readonly azimuth_deg: number;
		readonly area_m2: number;
	}[];
}

function closeRing(
	points: readonly LatLngAltitudeLiteral[],
): LatLngAltitudeLiteral[] {
	if (points.length === 0) return [];
	const first = points[0]!;
	const last = points[points.length - 1]!;
	if (first.lat === last.lat && first.lng === last.lng) return [...points];
	return [...points, { ...first }];
}

function toLatLngRing(
	ring: readonly (readonly [number, number])[],
	altitude = 0.15,
): LatLngAltitudeLiteral[] {
	return closeRing(
		ring.map(([lng, lat]) => ({
			lat,
			lng,
			altitude,
		})),
	);
}

interface OverlayShape {
	readonly id: string | null;
	readonly kind: "roof" | "keepout" | "obstacle" | "module" | "outline";
	readonly selected: boolean;
	readonly included: boolean;
	readonly path: readonly LatLngAltitudeLiteral[];
	readonly innerPaths: readonly (readonly LatLngAltitudeLiteral[])[];
	readonly heightM?: number;
}

function buildOverlays(
	document: GeometryDocument | undefined,
	poses: readonly PanelPose[],
	siteOutline: SiteOutline3D | null | undefined,
	selected: string | null | undefined,
): OverlayShape[] {
	const shapes: OverlayShape[] = [];
	const anchor = document?.coordinate_system.anchor;
	const hasGeoDocument =
		document &&
		document.roofs.length > 0 &&
		anchor !== null &&
		anchor !== undefined &&
		document.coordinate_system.north_reference === "true_north";

	if (hasGeoDocument && anchor) {
		const bridge = new GeographicBridge({
			schema_version: 1,
			method: "wgs84_cart_topocentric_v1",
			longitude_deg: anchor.longitude_deg,
			latitude_deg: anchor.latitude_deg,
			ellipsoid_height_m: 0,
			height_basis: "zero_height_horizontal_convention",
		});
		const project = (enu: Vec3, altitude: number): LatLngAltitudeLiteral => {
			const [lng, lat] = bridge.inverse(enu);
			return { lat, lng, altitude };
		};
		const roofs = new Map(document.roofs.map((roof) => [roof.id, roof]));
		for (const roof of document.roofs) {
			const onRoof = (uv: readonly [number, number], altitude: number) =>
				project(
					add(roof.origin_enu, vectorFromRoof(roof, [...uv, 0])),
					altitude,
				);
			const outer = closeRing(roof.boundary_uv.map((uv) => onRoof(uv, 0.12)));
			const holes = roof.holes_uv.map((hole) =>
				closeRing(hole.map((uv) => onRoof(uv, 0.12))),
			);
			if (outer.length >= 4)
				shapes.push({
					id: roof.id,
					kind: "roof",
					selected: selected === roof.id,
					included: true,
					path: outer,
					innerPaths: holes.filter((hole) => hole.length >= 4),
				});
		}
		for (const keepout of document.keepouts) {
			const roof = roofs.get(keepout.roof_id);
			if (!roof) continue;
			const path = closeRing(
				keepout.footprint_uv.map((uv) =>
					project(add(roof.origin_enu, vectorFromRoof(roof, [...uv, 0])), 0.22),
				),
			);
			if (path.length >= 4)
				shapes.push({
					id: keepout.id,
					kind: "keepout",
					selected: selected === keepout.id,
					included: true,
					path,
					innerPaths: [],
				});
		}
		for (const obstacle of document.obstacles) {
			const roof = roofs.get(obstacle.roof_id);
			if (!roof) continue;
			const altitude = Math.max(0.3, obstacle.height_m);
			const path = closeRing(
				obstacle.footprint_uv.map((uv) =>
					project(
						add(roof.origin_enu, vectorFromRoof(roof, [...uv, 0])),
						altitude,
					),
				),
			);
			if (path.length >= 4)
				shapes.push({
					id: obstacle.id,
					kind: "obstacle",
					selected: selected === obstacle.id,
					included: true,
					path,
					innerPaths: [],
					heightM: obstacle.height_m,
				});
		}
		for (const pose of poses) {
			const roof = roofs.get(pose.roof_id);
			if (!roof) continue;
			const corners = panelCornersUVN(pose).map((pt) =>
				add(roof.origin_enu, vectorFromRoof(roof, pt)),
			);
			const topIndices = [1, 3, 7, 5];
			const path = closeRing(
				topIndices.map((index) => project(corners[index]!, 0.36)),
			);
			if (path.length >= 4)
				shapes.push({
					id: pose.id,
					kind: "module",
					selected: selected === pose.id || selected === pose.array_id,
					included: pose.included,
					path,
					innerPaths: [],
				});
		}
		return shapes;
	}

	if (siteOutline) {
		if (siteOutline.planes && siteOutline.planes.length > 0) {
			for (const plane of siteOutline.planes) {
				const path = toLatLngRing(plane.polygon, 0.15);
				if (path.length >= 4)
					shapes.push({
						id: null,
						kind: "outline",
						selected: false,
						included: true,
						path,
						innerPaths: [],
					});
			}
		} else if (siteOutline.ring.length >= 3) {
			const path = toLatLngRing(siteOutline.ring, 0.15);
			if (path.length >= 4)
				shapes.push({
					id: null,
					kind: "outline",
					selected: false,
					included: true,
					path,
					innerPaths: [],
				});
		}
	}
	return shapes;
}

export function Google3DMap({
	apiKey,
	center,
	document: geometry,
	poses = [],
	siteOutline = null,
	selected = null,
	select,
	range = 125,
	tilt = 55,
	heading = 0,
	compact = false,
	onSwitchToMap,
	onSwitchToCad,
	onFallback,
}: {
	apiKey: string;
	center: readonly [number, number];
	document?: GeometryDocument | undefined;
	poses?: readonly PanelPose[] | undefined;
	siteOutline?: SiteOutline3D | null | undefined;
	selected?: string | null | undefined;
	select?: ((id: string) => void) | undefined;
	range?: number | undefined;
	tilt?: number | undefined;
	heading?: number | undefined;
	compact?: boolean | undefined;
	onSwitchToMap?: (() => void) | undefined;
	onSwitchToCad?: (() => void) | undefined;
	onFallback?: (() => void) | undefined;
}) {
	const hostRef = useRef<HTMLDivElement>(null);
	const mapRef = useRef<Map3DElementInstance | null>(null);
	const libRef = useRef<Maps3DLibrary | null>(null);
	const [status, setStatus] = useState<"loading" | "ready" | "failed">(
		"loading",
	);
	const [mapMode, setMapMode] = useState<"SATELLITE" | "HYBRID">("SATELLITE");
	const [topDown, setTopDown] = useState(false);
	const [attempt, setAttempt] = useState(0);
	const selectRef = useRef(select);
	selectRef.current = select;

	const effectiveCenter = useMemo<readonly [number, number]>(() => {
		const anchor = geometry?.coordinate_system.anchor;
		if (
			anchor &&
			geometry?.coordinate_system.north_reference === "true_north" &&
			geometry.roofs.length > 0
		) {
			return [anchor.longitude_deg, anchor.latitude_deg];
		}
		return center;
	}, [
		center,
		geometry?.coordinate_system.anchor,
		geometry?.coordinate_system.north_reference,
		geometry?.roofs.length,
	]);

	const overlays = useMemo(
		() => buildOverlays(geometry, poses, siteOutline, selected),
		[geometry, poses, siteOutline, selected],
	);

	useEffect(() => {
		const host = hostRef.current;
		if (!host) return;
		let disposed = false;
		setStatus("loading");
		void (async () => {
			try {
				const maps = await loadGoogleMaps(apiKey);
				if (disposed) return;
				const lib = await maps.importLibrary("maps3d");
				if (disposed) return;
				libRef.current = lib;
				const map = new lib.Map3DElement({
					center: {
						lat: effectiveCenter[1],
						lng: effectiveCenter[0],
						altitude: 0,
					},
					range,
					tilt: topDown ? 0 : tilt,
					heading,
					mode: mapMode,
					gestureHandling: "COOPERATIVE",
				});
				map.style.width = "100%";
				map.style.height = "100%";
				map.style.display = "block";
				const onSteady = (event: Event) => {
					const steady = event as Event & { isSteady?: boolean };
					if (!disposed && steady.isSteady !== false) setStatus("ready");
				};
				const onError = () => {
					if (disposed) return;
					setStatus("failed");
					onFallback?.();
				};
				map.addEventListener("gmp-steadychange", onSteady);
				map.addEventListener("gmp-error", onError);
				map.addEventListener("error", onError);
				host.replaceChildren(map);
				mapRef.current = map;
				setStatus("ready");
			} catch {
				if (!disposed) {
					setStatus("failed");
					onFallback?.();
				}
			}
		})();
		return () => {
			disposed = true;
			mapRef.current = null;
			libRef.current = null;
			host.replaceChildren();
		};
	}, [apiKey, attempt]);

	useEffect(() => {
		const map = mapRef.current;
		if (!map) return;
		map.mode = mapMode;
	}, [mapMode]);

	useEffect(() => {
		const map = mapRef.current;
		if (!map) return;
		map.tilt = topDown ? 0 : tilt;
	}, [topDown, tilt]);

	useEffect(() => {
		const map = mapRef.current;
		if (!map) return;
		map.center = {
			lat: effectiveCenter[1],
			lng: effectiveCenter[0],
			altitude: 0,
		};
		map.range = range;
	}, [effectiveCenter[0], effectiveCenter[1], range]);

	useEffect(() => {
		const map = mapRef.current;
		const lib = libRef.current;
		if (!map || !lib) return;
		const nodes: HTMLElement[] = [];
		const cleanups: (() => void)[] = [];
		if (overlays.length === 0) {
			const marker = new lib.Marker3DElement({
				position: {
					lat: effectiveCenter[1],
					lng: effectiveCenter[0],
					altitude: 2,
				},
				altitudeMode: "RELATIVE_TO_MESH",
			});
			nodes.push(marker);
		} else {
			for (const shape of overlays) {
				const interactive = Boolean(shape.id && selectRef.current);
				const style =
					shape.kind === "module"
						? {
								fillColor: shape.selected
									? "#2dd4bfcc"
									: shape.included
										? "#0d4a43e0"
										: "#94a3b855",
								strokeColor: shape.selected ? "#ffffffef" : "#cbd5e1cc",
								strokeWidth: shape.selected ? 2 : 1.2,
								zIndex: 4,
							}
						: shape.kind === "obstacle"
							? {
									fillColor: shape.selected ? "#f9731699" : "#64748b88",
									strokeColor: "#334155dd",
									strokeWidth: 2,
									zIndex: 3,
								}
							: shape.kind === "keepout"
								? {
										fillColor: shape.selected ? "#f59e0b66" : "#f59e0b38",
										strokeColor: "#d97706dd",
										strokeWidth: 2,
										zIndex: 2,
									}
								: shape.kind === "outline"
									? {
											fillColor: "#0f766e33",
											strokeColor: "#2dd4bfee",
											strokeWidth: 3,
											zIndex: 1,
										}
									: {
											fillColor: shape.selected ? "#14b8a64d" : "#0f766e2e",
											strokeColor: shape.selected ? "#2dd4bfee" : "#14b8a6cc",
											strokeWidth: shape.selected ? 3.5 : 2.5,
											zIndex: 1,
										};
				const polygon = interactive
					? new lib.Polygon3DInteractiveElement({
							altitudeMode: "RELATIVE_TO_MESH",
							extruded: shape.kind === "obstacle",
							drawsOccludedSegments: false,
							...style,
						})
					: new lib.Polygon3DElement({
							altitudeMode: "RELATIVE_TO_MESH",
							extruded: shape.kind === "obstacle",
							drawsOccludedSegments: false,
							...style,
						});
				polygon.path = [...shape.path];
				if (shape.innerPaths.length > 0) {
					polygon.innerPaths = shape.innerPaths.map((ring) => [...ring]);
				}
				if (interactive && shape.id) {
					const targetId = shape.id;
					const onClick = (event: Event) => {
						event.stopPropagation();
						selectRef.current?.(targetId);
					};
					polygon.addEventListener("gmp-click", onClick);
					cleanups.push(() =>
						polygon.removeEventListener("gmp-click", onClick),
					);
				}
				nodes.push(polygon);
			}
		}
		map.replaceChildren(...nodes);
		return () => {
			for (const cleanup of cleanups) cleanup();
			map.replaceChildren();
		};
	}, [overlays, effectiveCenter[0], effectiveCenter[1], status]);

	function resetCamera() {
		const map = mapRef.current;
		if (!map) return;
		const nextTilt = topDown ? 0 : tilt;
		if (typeof map.flyCameraTo === "function") {
			map.flyCameraTo({
				endCamera: {
					center: {
						lat: effectiveCenter[1],
						lng: effectiveCenter[0],
						altitude: 0,
					},
					range,
					tilt: nextTilt,
					heading,
				},
				durationMillis: 450,
			});
		} else {
			map.center = {
				lat: effectiveCenter[1],
				lng: effectiveCenter[0],
				altitude: 0,
			};
			map.range = range;
			map.tilt = nextTilt;
			map.heading = heading;
		}
	}

	if (status === "failed") {
		return (
			<Notice error>
				<p>
					{__(
						"Photorealistic 3D imagery could not be loaded here. You can retry or use the aerial map.",
						"linker-tools",
					)}
				</p>
				<div className="sc-actions">
					<button
						type="button"
						className="sc-button"
						onClick={() => {
							// The failed state above unmounts the host div, so the
							// reload effect would find no host and return early.
							// Restore the mounted layout before the attempt re-runs it.
							setStatus("loading");
							setAttempt((value) => value + 1);
						}}
					>
						{__("Retry 3D", "linker-tools")}
					</button>
					{onSwitchToMap && (
						<button type="button" className="sc-button" onClick={onSwitchToMap}>
							{__("Open aerial map", "linker-tools")}
						</button>
					)}
				</div>
			</Notice>
		);
	}

	return (
		<div
			className={
				compact ? "sc-google3d-view sc-google3d-compact" : "sc-google3d-view"
			}
			data-google3d-status={status}
		>
			<div
				className="sc-map-toolbar"
				role="group"
				aria-label={__("3D satellite controls", "linker-tools")}
			>
				<button type="button" className="sc-button" onClick={resetCamera}>
					{__("Reset 3D view", "linker-tools")}
				</button>
				<button
					type="button"
					className="sc-button"
					aria-pressed={topDown}
					onClick={() => setTopDown((value) => !value)}
				>
					{topDown
						? __("3D oblique view", "linker-tools")
						: __("Top-down view", "linker-tools")}
				</button>
				<button
					type="button"
					className="sc-button"
					aria-pressed={mapMode === "HYBRID"}
					onClick={() =>
						setMapMode((mode) =>
							mode === "SATELLITE" ? "HYBRID" : "SATELLITE",
						)
					}
				>
					{mapMode === "HYBRID"
						? __("Hide street labels", "linker-tools")
						: __("Show street labels", "linker-tools")}
				</button>
				{onSwitchToMap && (
					<button type="button" className="sc-button" onClick={onSwitchToMap}>
						{__("Draw or adopt on aerial map", "linker-tools")}
					</button>
				)}
				{onSwitchToCad && (
					<button type="button" className="sc-button" onClick={onSwitchToCad}>
						{__("CAD 3D (Edit panels)", "linker-tools")}
					</button>
				)}
			</div>
			{status === "loading" && (
				<p role="status">
					{__("Loading 3D satellite imagery…", "linker-tools")}
				</p>
			)}
			<div
				className="sc-google3d-host"
				ref={hostRef}
				role="img"
				aria-label={__("3D satellite view of the site", "linker-tools")}
			/>
		</div>
	);
}

export default Google3DMap;
