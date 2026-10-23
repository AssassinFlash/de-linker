/** Pinned Terra Draw interaction buffer. The caller owns source/plane review,
 * raw recovery and the single GeometryCommand writer; this class owns no
 * project, input history or network request. */
import {
	TerraDraw,
	TerraDrawPolygonMode,
	TerraDrawSelectMode,
} from "terra-draw";
import type { TerraDrawEventListeners } from "terra-draw";
import { TerraDrawMapLibreGLAdapter } from "terra-draw-maplibre-gl-adapter";
import type { Map as MapLibreMap } from "maplibre-gl";
import type { Vec2 } from "../domain/geometry.ts";
import type { MapVertexAction } from "../domain/mapRingEdit.ts";
import { reconcileMapVertex } from "../domain/mapRingEdit.ts";
import {
	MAP_HANDLE_DECIMALS,
	mapPolygon,
	quantizeMapPosition,
	readMapPolygon,
} from "../domain/mapDrawingGeometry.ts";
import policy from "../contracts/geometry-policy.json" with { type: "json" };

type Polygon = ReturnType<typeof mapPolygon>;
type DrawAdapter = ConstructorParameters<typeof TerraDraw>[0]["adapter"];
type MapPort = Pick<
	MapLibreMap,
	"getCanvas" | "dragPan" | "dragRotate" | "doubleClickZoom"
>;
export interface RawMapDrawing {
	readonly geometry: Polygon;
	readonly committed_coordinate_count: number | null;
	readonly complete: boolean;
}
export interface MapDrawingStep {
	readonly action: MapVertexAction | "draw";
	readonly geometry: Polygon;
}
export interface MapDrawingTransaction {
	/** A midpoint drag may contain insert + drag, but remains one transaction. */
	readonly steps: readonly MapDrawingStep[];
}
export interface MapDrawingCallbacks {
	readonly raw: (value: RawMapDrawing | null) => void;
	readonly transaction: (value: MapDrawingTransaction) => void;
	readonly interrupted: () => void;
	readonly failed: (cause: unknown) => void;
	/** Keep MapViewport's pick suppressed for the completion click even if its
	 * transaction callback disposes the controller during that pointerup. */
	readonly blockMapPick: () => void;
}
type Start =
	| { readonly kind: "draw" }
	| { readonly kind: "edit"; readonly ring: readonly Vec2[] };

/** A map handler gate stays blocked until a later physical pointerdown. That
 * reset belongs to the viewport, which outlives the drawing controller. */
export class MapPickGate {
	blocked = false;
	beginPointer = () => {
		this.blocked = false;
	};
	block = () => {
		this.blocked = true;
	};
}

export function createMapDrawingController(
	map: MapLibreMap,
	start: Start,
	callbacks: MapDrawingCallbacks,
): MapDrawingController {
	return new MapDrawingController(
		map,
		new TerraDrawMapLibreGLAdapter({
			map,
			prefixId: "linker-draw-" + crypto.randomUUID(),
			coordinatePrecision: MAP_HANDLE_DECIMALS,
			ignoreMismatchedPointerEvents: true,
		}),
		start,
		callbacks,
	);
}

/** Adapter injection permits real pinned-library tests without pretending a
 * fake projection/DOM is a native map or touch-device acceptance. */
export class MapDrawingController {
	private readonly draw: TerraDraw;
	private readonly adapter: DrawAdapter;
	private readonly callbacks: MapDrawingCallbacks;
	private readonly canvas: HTMLCanvasElement;
	private readonly owner: Document;
	private readonly window: Window;
	private readonly restore: () => void;
	private featureId: string | null = null;
	private disposed = false;
	private applying = false;
	private pointer: number | null = null;
	private pointerBefore: Polygon | null = null;
	private pointerEnd: Vec2 | null = null;
	private queued = false;
	private steps: MapDrawingStep[] = [];
	private raw: RawMapDrawing | null = null;

	constructor(
		map: MapPort,
		adapter: DrawAdapter,
		start: Start,
		callbacks: MapDrawingCallbacks,
	) {
		this.canvas = map.getCanvas();
		this.adapter = adapter;
		this.owner = this.canvas.ownerDocument;
		if (!this.owner.defaultView) throw new Error("map_drawing_window_missing");
		this.window = this.owner.defaultView;
		this.callbacks = callbacks;
		const toggles = [map.dragPan, map.dragRotate, map.doubleClickZoom].map(
			(handler) => ({ handler, enabled: handler.isEnabled() }),
		);
		const cursor = this.canvas.style.cursor;
		this.restore = () => {
			const failures: unknown[] = [];
			for (const { handler, enabled } of toggles) {
				try {
					if (enabled) handler.enable();
					else handler.disable();
				} catch (error) {
					failures.push(error);
				}
			}
			try {
				this.canvas.style.cursor = cursor;
			} catch (error) {
				failures.push(error);
			}
			if (failures.length)
				throw new AggregateError(failures, "map_drawing_restore_failed");
		};
		this.draw = new TerraDraw({
			adapter,
			idStrategy: {
				getId: () => crypto.randomUUID(),
				isValidId: (id) => typeof id === "string" && id.length > 0,
			},
			modes: [
				new TerraDrawPolygonMode({
					editable: false,
					showCoordinatePoints: false,
					keyEvents: { cancel: "Escape", finish: "Enter" },
				}),
				new TerraDrawSelectMode({
					// Pinned source accepts finite non-negative values. Zero
					// disables its modulo skip (n % 0 is NaN); unlike 1, it does
					// not discard every movement. Library fixture checks event 5.
					dragEventThrottle: 0,
					keyEvents: {
						deselect: "Escape",
						delete: null,
						rotate: null,
						scale: null,
					},
					flags: {
						polygon: {
							feature: {
								// Geographic feature translation/rotation is not a rigid
								// metric operation; domain controls own those transforms.
								draggable: false,
								rotateable: false,
								scaleable: false,
								coordinates: {
									draggable: true,
									deletable: true,
									midpoints: { draggable: true },
								},
							},
						},
					},
				}),
			],
		});
		// Capture before Terra's handlers so midpoint insertion belongs to the
		// same transaction as its subsequent drag. No SDK history is configured.
		this.canvas.addEventListener("pointerdown", this.pointerDown, true);
		this.window.addEventListener("pointerup", this.pointerUp, true);
		this.window.addEventListener("pointercancel", this.pointerCancel, true);
		this.canvas.addEventListener("lostpointercapture", this.pointerCancel);
		this.window.addEventListener("blur", this.interrupt);
		this.window.addEventListener("pagehide", this.interrupt);
		this.owner.addEventListener("visibilitychange", this.visibility);
		this.draw.on("change", this.changed);
		this.draw.on("finish", this.finished);
		try {
			this.applying = true;
			this.draw.start();
			if (start.kind === "edit") {
				this.featureId = crypto.randomUUID();
				const geometry = mapPolygon(start.ring);
				readMapPolygon(geometry);
				this.addAndSelect(geometry);
			} else this.draw.setMode("polygon");
		} catch (error) {
			const cleanup = this.release();
			if (cleanup)
				throw new AggregateError(
					[error, cleanup],
					"map_drawing_initialization_failed",
				);
			throw error;
		} finally {
			this.applying = false;
		}
	}

	private addAndSelect(geometry: Polygon) {
		if (!this.featureId) throw new Error("map_drawing_binding_missing");
		const results = this.draw.addFeatures([
			{
				type: "Feature",
				id: this.featureId,
				properties: { mode: "polygon" },
				geometry,
			},
		]);
		if (results.length !== 1 || !results[0]?.valid)
			throw new Error("map_drawing_projection_rejected");
		this.draw.selectFeature(this.featureId);
	}

	private fail(cause: unknown) {
		if (this.disposed) return;
		const cleanup = this.release();
		this.callbacks.failed(
			cleanup
				? new AggregateError([cause, cleanup], "map_drawing_failed")
				: cause,
		);
	}
	private changed: TerraDrawEventListeners["change"] = (ids, _, context) => {
		if (
			this.disposed ||
			this.applying ||
			(context && "origin" in context && context.origin === "api")
		)
			return;
		try {
			if (!this.featureId)
				for (const id of ids) {
					const feature = this.draw.getSnapshotFeature(id);
					if (
						typeof id === "string" &&
						feature?.geometry.type === "Polygon" &&
						feature.properties.mode === "polygon" &&
						feature.properties.currentlyDrawing === true
					) {
						this.featureId = id;
						break;
					}
				}
			if (!this.featureId || !ids.includes(this.featureId)) return;
			const feature = this.draw.getSnapshotFeature(this.featureId);
			if (!feature) {
				// Esc removes unfinished library geometry; retain the prior raw
				// input for the caller's explicit recovery/discard decision.
				this.interrupt();
				return;
			}
			if (
				feature.geometry.type !== "Polygon" ||
				feature.geometry.coordinates.length !== 1 ||
				feature.geometry.coordinates[0]!.length > policy.max_vertices + 2
			)
				throw new Error("map_drawing_raw_limit");
			const count = feature.properties.committedCoordinateCount;
			if (
				count !== undefined &&
				(typeof count !== "number" ||
					!Number.isSafeInteger(count) ||
					count < 1 ||
					count > policy.max_vertices)
			)
				throw new Error("map_drawing_raw_invalid");
			this.raw = {
				geometry: structuredClone(feature.geometry),
				committed_coordinate_count: typeof count === "number" ? count : null,
				complete: feature.properties.currentlyDrawing !== true,
			};
			this.callbacks.raw(this.raw);
		} catch (error) {
			this.fail(error);
		}
	};

	private finished: TerraDrawEventListeners["finish"] = (id, context) => {
		if (this.disposed || this.applying || id !== this.featureId) return;
		try {
			if (
				context.action !== "draw" &&
				context.action !== "dragCoordinate" &&
				context.action !== "insertMidpoint" &&
				context.action !== "deleteCoordinate"
			)
				throw new Error("map_drawing_action_unsupported");
			const feature = this.draw.getSnapshotFeature(id);
			if (!feature) throw new Error("map_drawing_binding_missing");
			const geometry = mapPolygon(readMapPolygon(feature.geometry));
			// Snapshot now: a later drag in the same pointer transaction changes
			// this object before a queued midpoint insertion can be reconciled.
			this.steps.push({ action: context.action, geometry });
			if (this.pointer === null) this.enqueue();
		} catch (error) {
			this.fail(error);
		}
	};

	private pointerDown = (event: PointerEvent) => {
		if (this.disposed) return;
		this.callbacks.blockMapPick();
		if (!event.isPrimary || this.pointer !== null) {
			this.interrupt();
			return;
		}
		this.pointer = event.pointerId;
		this.pointerBefore = null;
		this.pointerEnd = null;
		if (this.featureId) {
			const feature = this.draw.getSnapshotFeature(this.featureId);
			if (
				feature?.geometry.type === "Polygon" &&
				feature.properties.currentlyDrawing !== true
			)
				this.pointerBefore = structuredClone(feature.geometry);
		}
	};
	private pointerUp = (event: PointerEvent) => {
		if (this.disposed || this.pointer !== event.pointerId) return;
		if (event.target !== this.canvas) {
			this.interrupt();
			return;
		}
		try {
			const endpoint = this.adapter.getLngLatFromEvent(event);
			if (endpoint)
				this.pointerEnd = quantizeMapPosition([endpoint.lng, endpoint.lat]);
		} catch (error) {
			this.fail(error);
			return;
		}
		// Queued work runs after Terra's pointerup regardless of registration
		// order. Keep pointer non-null until then to coalesce both finishes.
		queueMicrotask(() => {
			if (this.disposed) return;
			this.pointer = null;
			this.flush();
		});
	};
	private pointerCancel = (event: PointerEvent) => {
		if (this.pointer === event.pointerId) this.interrupt();
	};
	private visibility = () => {
		if (this.owner.visibilityState === "hidden") this.interrupt();
	};
	private interrupt = () => {
		if (this.disposed) return;
		const cleanup = this.release();
		if (cleanup) this.callbacks.failed(cleanup);
		else this.callbacks.interrupted();
	};
	private enqueue() {
		if (this.queued) return;
		this.queued = true;
		queueMicrotask(() => {
			this.queued = false;
			if (!this.disposed && this.pointer === null) this.flush();
		});
	}
	private flush() {
		if (this.disposed) return;
		const steps = this.steps;
		this.steps = [];
		try {
			if (
				steps.length > 2 ||
				(steps.length === 2 &&
					(steps[0]!.action !== "insertMidpoint" ||
						steps[1]!.action !== "dragCoordinate"))
			)
				throw new Error("map_drawing_transaction_invalid");
			const last = steps.at(-1),
				previous =
					steps.length > 1 ? steps.at(-2)!.geometry : this.pointerBefore;
			let inserted: Vec2 | null = null;
			if (steps.length === 2 && this.pointerBefore) {
				const geographic = readMapPolygon(this.pointerBefore);
				reconcileMapVertex(
					{ metric: geographic, geographic },
					readMapPolygon(steps[0]!.geometry),
					"insertMidpoint",
					(point) => {
						inserted = point;
						return point;
					},
				);
			}
			if (last?.action === "dragCoordinate" && previous) {
				const geographic = readMapPolygon(previous),
					before = { metric: geographic, geographic };
				// Terra's drag-end does not reapply the release coordinate. Infer
				// the one actually changed raw vertex from its completed action,
				// then set only that display point to the captured endpoint. Never
				// assume a pointerdown helper index survived winding/target choice.
				const corrected = reconcileMapVertex(
					before,
					readMapPolygon(last.geometry),
					"dragCoordinate",
					(point, old) => {
						if (
							inserted &&
							(!old || old[0] !== inserted[0] || old[1] !== inserted[1])
						)
							throw new Error("map_drawing_midpoint_target_changed");
						return this.pointerEnd ?? point;
					},
				);
				if (corrected === before && this.pointerEnd)
					throw new Error("map_drawing_endpoint_unresolved");
				if (this.pointerEnd) {
					const geometry = mapPolygon(corrected.metric);
					readMapPolygon(geometry);
					this.applying = true;
					this.draw.updateFeatureGeometry(this.featureId!, geometry);
					this.applying = false;
					steps[steps.length - 1] = { action: "dragCoordinate", geometry };
					this.raw = {
						geometry,
						complete: true,
						committed_coordinate_count: null,
					};
					this.callbacks.raw(this.raw);
				}
			}
			this.pointerBefore = null;
			this.pointerEnd = null;
			if (!steps.length) return;
			if (steps.some((step) => step.action === "draw")) {
				this.applying = true;
				this.draw.selectFeature(this.featureId!);
				this.applying = false;
			}
			this.callbacks.transaction({ steps });
		} catch (error) {
			this.applying = false;
			this.fail(error);
		}
	}

	/** Application-owned toolbar completion, using the pinned raw coordinate
	 * count. Terra has no public finishDrawing API. Missing vertices remain raw. */
	finishCandidate(): boolean {
		if (this.disposed || this.pointer !== null || !this.featureId) return false;
		const feature = this.draw.getSnapshotFeature(this.featureId),
			count = feature?.properties.committedCoordinateCount;
		if (
			feature?.geometry.type !== "Polygon" ||
			feature.properties.currentlyDrawing !== true ||
			typeof count !== "number" ||
			!Number.isSafeInteger(count) ||
			count < 3 ||
			count > policy.max_vertices
		)
			return false;
		try {
			const ring = feature.geometry.coordinates[0]!.slice(0, count),
				geometry = mapPolygon(
					readMapPolygon({
						type: "Polygon",
						coordinates: [[...ring, ring[0]]],
					}),
				);
			this.applying = true;
			this.draw.setMode("static");
			this.addAndSelect(geometry);
			this.applying = false;
			this.raw = { geometry, committed_coordinate_count: null, complete: true };
			this.callbacks.raw(this.raw);
			this.steps.push({ action: "draw", geometry });
			this.enqueue();
			return true;
		} catch (error) {
			this.applying = false;
			this.fail(error);
			return false;
		}
	}

	/** Call while the old map/style/layers still exist, before MapLibre.remove or
	 * provider replacement. A library cleanup refusal is reported, without
	 * aborting the owner's subsequent map cleanup. Late work cannot commit. */
	dispose(): void {
		const cleanup = this.release();
		if (cleanup) this.callbacks.failed(cleanup);
	}
	private release(): Error | null {
		if (this.disposed) return null;
		this.disposed = true;
		this.steps = [];
		this.canvas.removeEventListener("pointerdown", this.pointerDown, true);
		this.window.removeEventListener("pointerup", this.pointerUp, true);
		this.window.removeEventListener("pointercancel", this.pointerCancel, true);
		this.canvas.removeEventListener("lostpointercapture", this.pointerCancel);
		this.window.removeEventListener("blur", this.interrupt);
		this.window.removeEventListener("pagehide", this.interrupt);
		this.owner.removeEventListener("visibilitychange", this.visibility);
		this.draw.off("change", this.changed);
		this.draw.off("finish", this.finished);
		const failures: unknown[] = [];
		try {
			this.draw.stop();
		} catch (error) {
			failures.push(error);
		}
		try {
			this.restore();
		} catch (error) {
			failures.push(error);
		}
		return failures.length
			? new AggregateError(failures, "map_drawing_cleanup_failed")
			: null;
	}
}
