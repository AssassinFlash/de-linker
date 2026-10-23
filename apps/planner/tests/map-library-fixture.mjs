// Test-only library port. It records ownership and public API calls; it is
// never used as evidence of WebGL, map tiles, network privacy or survey accuracy.
export const maps = [];
export const behavior = { autoLoad: true };
export class Map {
	constructor(options) {
		this.options = options;
		this.removed = false;
		this.removals = 0;
		this.events = new globalThis.Map();
		this.sources = new globalThis.Map();
		this.layers = new globalThis.Map();
		this.canvas = document.createElement("canvas");
		options.container.append(this.canvas);
		this.centre = options.center;
		this.zoom = options.zoom;
		this.bearing = options.bearing;
		this.pitch = options.pitch;
		this.hits = [];
		maps.push(this);
		queueMicrotask(() => {
			if (!this.removed && behavior.autoLoad) this.emit("load");
		});
	}
	on(name, callback) {
		const handlers = this.events.get(name) ?? new Set();
		handlers.add(callback);
		this.events.set(name, handlers);
	}
	off(name, callback) {
		this.events.get(name)?.delete(callback);
	}
	emit(name, event) {
		for (const callback of this.events.get(name) ?? []) callback(event);
	}
	addControl() {}
	getCanvas() {
		return this.canvas;
	}
	getSource(id) {
		return this.sources.get(id);
	}
	addSource(id, source) {
		this.sources.set(id, {
			...source,
			setData(data) {
				this.data = data;
			},
		});
	}
	addLayer(layer) {
		this.layers.set(layer.id, layer);
	}
	getLayer(id) {
		return this.layers.get(id);
	}
	setFilter(id, filter) {
		this.layers.get(id).filter = filter;
	}
	queryRenderedFeatures() {
		return this.hits;
	}
	fitBounds(bounds, options) {
		this.fitted = bounds;
		this.centre = [
			(bounds[0][0] + bounds[1][0]) / 2,
			(bounds[0][1] + bounds[1][1]) / 2,
		];
		this.zoom = options.maxZoom;
	}
	jumpTo(value) {
		if (value.center) this.centre = value.center;
		if (value.zoom !== undefined) this.zoom = value.zoom;
		if (value.bearing !== undefined) this.bearing = value.bearing;
		if (value.pitch !== undefined) this.pitch = value.pitch;
	}
	zoomIn() {
		this.zoom++;
	}
	zoomOut() {
		this.zoom--;
	}
	resize() {}
	getCenter() {
		return { lng: this.centre[0], lat: this.centre[1] };
	}
	getZoom() {
		return this.zoom;
	}
	getBearing() {
		return this.bearing;
	}
	getPitch() {
		return this.pitch;
	}
	remove() {
		this.removed = true;
		this.removals++;
		this.canvas.remove();
	}
}
export class AttributionControl {}
