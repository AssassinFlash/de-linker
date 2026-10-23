/** Public MapLibre events and GeoJSON only. An open committed prefix can be
 * restored without fabricating clicks or importing private drawing state. */
import type {
	Map as MapLibreMap,
	MapMouseEvent,
	GeoJSONSource,
} from "maplibre-gl";
import type { Vec2 } from "../domain/geometry.ts";

export interface PrefixCallbacks {
	readonly append: (position: Vec2) => void;
	readonly blockMapPick: () => void;
	readonly failed: (cause: unknown) => void;
}
type MapPort = Pick<
	MapLibreMap,
	| "getCanvas"
	| "on"
	| "off"
	| "addSource"
	| "getSource"
	| "removeSource"
	| "addLayer"
	| "getLayer"
	| "removeLayer"
	| "doubleClickZoom"
>;
export class MapPrefixController {
	private readonly map: MapPort;
	private readonly callbacks: PrefixCallbacks;
	private readonly canvas: HTMLCanvasElement;
	private readonly owner: Window;
	private readonly id = "linker-draw-prefix-" + crypto.randomUUID();
	private readonly layers: string[];
	private readonly zoomEnabled: boolean;
	private readonly cursor: string;
	private readonly pointers = new Set<number>();
	private gesture: { id: number; x: number; y: number; valid: boolean } | null =
		null;
	private completed = false;
	private disposed = false;
	constructor(
		map: MapPort,
		vertices: readonly Vec2[],
		colour: string,
		callbacks: PrefixCallbacks,
	) {
		this.map = map;
		this.callbacks = callbacks;
		this.canvas = map.getCanvas();
		const owner = this.canvas.ownerDocument.defaultView;
		if (!owner) throw new Error("map_drawing_window_missing");
		this.owner = owner;
		this.layers = [this.id + "-line", this.id + "-point"];
		this.zoomEnabled = map.doubleClickZoom.isEnabled();
		this.cursor = this.canvas.style.cursor;
		try {
			map.doubleClickZoom.disable();
			this.canvas.style.cursor = "crosshair";
			map.addSource(this.id, {
				type: "geojson",
				data: { type: "FeatureCollection", features: [] },
			});
			map.addLayer({
				id: this.layers[0]!,
				type: "line",
				source: this.id,
				filter: ["==", ["geometry-type"], "LineString"],
				paint: { "line-color": colour, "line-width": 2 },
			});
			map.addLayer({
				id: this.layers[1]!,
				type: "circle",
				source: this.id,
				filter: ["==", ["geometry-type"], "Point"],
				paint: {
					"circle-color": colour,
					"circle-radius": 5,
					"circle-stroke-color": colour,
					"circle-stroke-width": 2,
				},
			});
			this.update(vertices);
			this.owner.addEventListener("pointerdown", this.down, true);
			this.owner.addEventListener("pointermove", this.move, true);
			this.owner.addEventListener("pointerup", this.up, true);
			this.owner.addEventListener("pointercancel", this.cancel, true);
			this.owner.addEventListener("blur", this.reset);
			this.canvas.addEventListener("lostpointercapture", this.lost);
			map.on("click", this.click);
		} catch (cause) {
			this.dispose();
			throw cause;
		}
	}
	update(vertices: readonly Vec2[]) {
		if (this.disposed) return;
		const features: GeoJSON.Feature[] = vertices.map((point) => ({
			type: "Feature",
			properties: {},
			geometry: { type: "Point", coordinates: [...point] },
		}));
		if (vertices.length >= 2)
			features.unshift({
				type: "Feature",
				properties: {},
				geometry: {
					type: "LineString",
					coordinates: vertices.map((point) => [...point]),
				},
			});
		(this.map.getSource(this.id) as GeoJSONSource).setData({
			type: "FeatureCollection",
			features,
		});
	}
	private down = (event: PointerEvent) => {
		if (this.disposed) return;
		this.completed = false;
		if (this.pointers.size || this.canvas.contains(event.target as Node))
			this.pointers.add(event.pointerId);
		if (!this.canvas.contains(event.target as Node)) {
			if (this.gesture) this.gesture.valid = false;
			return;
		}
		this.callbacks.blockMapPick();
		if (this.pointers.size !== 1 || event.button !== 0 || !event.isPrimary) {
			if (this.gesture) this.gesture.valid = false;
			return;
		}
		this.gesture = {
			id: event.pointerId,
			x: event.clientX,
			y: event.clientY,
			valid: true,
		};
	};
	private move = (event: PointerEvent) => {
		const gesture = this.gesture;
		// Match the pinned MapLibre default click tolerance, in display pixels;
		// this threshold is never a metre/survey/numerical tolerance.
		if (
			gesture?.id === event.pointerId &&
			Math.hypot(event.clientX - gesture.x, event.clientY - gesture.y) >= 3
		)
			gesture.valid = false;
	};
	private up = (event: PointerEvent) => {
		this.move(event);
		const gesture = this.gesture;
		this.completed =
			!!gesture &&
			gesture.id === event.pointerId &&
			gesture.valid &&
			this.pointers.size === 1 &&
			this.canvas.contains(event.target as Node);
		this.pointers.delete(event.pointerId);
		this.gesture = null;
	};
	private cancel = (event: PointerEvent) => {
		this.pointers.delete(event.pointerId);
		this.gesture = null;
		this.completed = false;
	};
	private lost = () => {
		if (this.gesture) this.reset();
	};
	private reset = () => {
		this.pointers.clear();
		this.gesture = null;
		this.completed = false;
	};
	private click = (event: MapMouseEvent) => {
		if (this.disposed || !this.completed) return;
		this.completed = false;
		// One physical release can produce at most one point. A second click
		// never both adds a duplicate and finishes a polygon.
		if (event.originalEvent.detail > 1) return;
		this.callbacks.blockMapPick();
		this.callbacks.append([event.lngLat.lng, event.lngLat.lat]);
	};
	dispose() {
		if (this.disposed) return;
		this.disposed = true;
		this.reset();
		this.owner.removeEventListener("pointerdown", this.down, true);
		this.owner.removeEventListener("pointermove", this.move, true);
		this.owner.removeEventListener("pointerup", this.up, true);
		this.owner.removeEventListener("pointercancel", this.cancel, true);
		this.owner.removeEventListener("blur", this.reset);
		this.canvas.removeEventListener("lostpointercapture", this.lost);
		const failures: unknown[] = [];
		const attempt = (operation: () => void) => {
			try {
				operation();
			} catch (error) {
				failures.push(error);
			}
		};
		attempt(() => {
			this.map.off("click", this.click);
		});
		for (const layer of [...this.layers].reverse())
			attempt(() => {
				if (this.map.getLayer(layer)) this.map.removeLayer(layer);
			});
		attempt(() => {
			if (this.map.getSource(this.id)) this.map.removeSource(this.id);
		});
		attempt(() => {
			if (this.zoomEnabled) this.map.doubleClickZoom.enable();
			else this.map.doubleClickZoom.disable();
		});
		attempt(() => {
			this.canvas.style.cursor = this.cursor;
		});
		if (failures.length)
			this.callbacks.failed(
				new AggregateError(failures, "map_drawing_cleanup_failed"),
			);
	}
}
