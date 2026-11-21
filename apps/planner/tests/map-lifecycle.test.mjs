import assert from "node:assert/strict";
import test from "node:test";
import { register } from "node:module";
import React, { act } from "react";
import imported from "../../../fixtures/planning/geometry-import-asset.json" with { type: "json" };
import { setupDom, until } from "./dom-fixture.mjs";
register("./map-library-loader.mjs", import.meta.url);

const activeMap = (maps) => maps.findLast((map) => !map.removed);
const button = (text) =>
	[...document.querySelectorAll("button")].find(
		(node) => node.textContent.trim() === text,
	);

test("map view requires consent, releases provider requests on withdrawal, and preserves geometry through retry", async (t) => {
	const fixture = setupDom();
	const previous = new globalThis.Map();
	for (const name of ["MutationObserver", "getComputedStyle"]) {
		previous.set(name, Object.getOwnPropertyDescriptor(globalThis, name));
		Object.defineProperty(globalThis, name, {
			value: window[name].bind(window),
			configurable: true,
		});
	}
	const css = document.createElement("style");
	css.textContent =
		".sc-map-host{--proto-neutral-300:#ccc;--proto-teal-900:#123;--proto-neutral-600:#456;--proto-teal-700:#278;--proto-teal-400:#4bc;--proto-neutral-100:#eee;}";
	document.head.append(css);
	const { createRoot } = await import("react-dom/client");
	const { default: MapViewport } =
		await import("../src/components/design/MapViewport.tsx");
	const { maps, behavior } = await import("./map-library-fixture.mjs");
	const root = createRoot(fixture.element);
	t.after(async () => {
		await fixture.dispose(root);
		for (const [name, descriptor] of previous) {
			if (descriptor) Object.defineProperty(globalThis, name, descriptor);
			else delete globalThis[name];
		}
	});
	const geometry = structuredClone(imported.metadata.geometry_import.geometry),
		before = JSON.stringify(geometry),
		camera = { current: null },
		picked = [];
	const props = {
		document: geometry,
		poses: [],
		selected: null,
		select: (id) => picked.push(id),
		disabled: false,
		openReferences() {},
		camera,
	};
	const render = async () =>
		act(async () =>
			root.render(
				React.createElement(
					React.StrictMode,
					null,
					React.createElement(MapViewport, props),
				),
			),
		);
	await render();
	await until(() => document.querySelector('[data-map-status="ready"]'));
	assert.ok(maps.length >= 2, "StrictMode should release the first setup");
	assert.equal(maps[0].removals, 1);
	assert.equal(typeof activeMap(maps).options.style, "object");
	assert.throws(
		() =>
			activeMap(maps).options.transformRequest(
				"https://tiles.openfreemap.org/styles/liberty",
			),
		/not_authorized/,
	);
	await act(async () => button("Load street map").click());
	await until(() => document.querySelector('[data-map-status="ready"]'));
	assert.equal(
		activeMap(maps).options.style,
		"https://tiles.openfreemap.org/styles/liberty",
	);
	assert.ok(
		maps.some((map) => map.fitted),
		"the first ready view must fit the actual geometry",
	);
	assert.equal(
		activeMap(maps).getSource("linker-project-geometry").data.features[0]
			.geometry.coordinates.length,
		2,
	);
	activeMap(maps).hits = [{ properties: { object_id: geometry.roofs[0].id } }];
	await act(async () =>
		activeMap(maps).emit("click", { point: { x: 1, y: 1 } }),
	);
	assert.deepEqual(picked, [geometry.roofs[0].id]);
	const hiddenByButton = activeMap(maps);
	await act(async () => {
		button("Hide street map").click();
		assert.equal(hiddenByButton.removals, 1);
	});
	await until(() => typeof activeMap(maps)?.options.style === "object");
	assert.deepEqual(activeMap(maps).options.style.sources, {});
	behavior.autoLoad = false;
	await act(async () => button("Load street map").click());
	const unavailable = activeMap(maps);
	await act(async () =>
		unavailable.emit("error", { error: new Error("synthetic offline") }),
	);
	assert.equal(
		document.querySelector(".sc-map-view").dataset.mapStatus,
		"failed",
	);
	assert.equal(
		document.querySelector('.sc-map-view [role="status"]'),
		null,
		"a terminal provider refusal must not keep announcing loading",
	);
	assert.equal(
		JSON.parse(document.querySelector(".sc-map-view").dataset.mapFailure).stage,
		"resource",
	);
	behavior.autoLoad = true;
	await act(async () => button("Retry loading map").click());
	await until(() => document.querySelector('[data-map-status="ready"]'));
	assert.equal(unavailable.removals, 1);
	const withdrawn = activeMap(maps);
	window.getCkyConsent = () => ({ isUserActionCompleted: false });
	await act(async () =>
		document.dispatchEvent(new window.Event("cookieyes_consent_update")),
	);
	assert.equal(activeMap(maps), withdrawn);
	window.getCkyConsent = () => ({ isUserActionCompleted: true });
	await act(async () =>
		document.dispatchEvent(new window.Event("cookieyes_consent_update")),
	);
	await until(() => typeof activeMap(maps)?.options.style === "object");
	assert.equal(withdrawn.removals, 1);
	assert.throws(
		() =>
			withdrawn.options.transformRequest(
				"https://tiles.openfreemap.org/styles/liberty",
			),
		/not_authorized/,
	);
	activeMap(maps).jumpTo({
		center: [6.9601, 50.9401],
		zoom: 19,
		bearing: 35,
		pitch: 10,
	});
	await act(async () =>
		root.render(React.createElement("p", null, "Other editor view")),
	);
	assert.equal(activeMap(maps), undefined);
	await render();
	await until(() => document.querySelector('[data-map-status="ready"]'));
	assert.deepEqual(activeMap(maps).options.center, [6.9601, 50.9401]);
	assert.equal(activeMap(maps).options.bearing, 35);
	assert.equal(
		typeof activeMap(maps).options.style,
		"object",
		"reopening the map does not silently renew withdrawn consent",
	);
	assert.equal(JSON.stringify(geometry), before);
	assert.ok(
		maps.filter((map) => map.removed).every((map) => map.removals === 1),
	);
});

test("late imagery needs its own grant and changing providers revokes it", async (t) => {
	const fixture = setupDom();
	const previous = new globalThis.Map();
	for (const name of ["MutationObserver", "getComputedStyle"]) {
		previous.set(name, Object.getOwnPropertyDescriptor(globalThis, name));
		Object.defineProperty(globalThis, name, {
			value: window[name].bind(window),
			configurable: true,
		});
	}
	const css = document.createElement("style");
	css.textContent =
		".sc-map-host{--proto-neutral-300:#ccc;--proto-teal-900:#123;--proto-neutral-600:#456;--proto-teal-700:#278;--proto-teal-400:#4bc;--proto-neutral-100:#eee;}";
	document.head.append(css);
	const { createRoot } = await import("react-dom/client");
	const { default: MapViewport } =
		await import("../src/components/design/MapViewport.tsx");
	const { emptyGeometry } = await import("../src/domain/geometryCommands.ts");
	const { maps, behavior } = await import("./map-library-fixture.mjs");
	const root = createRoot(fixture.element);
	t.after(async () => {
		await fixture.dispose(root);
		for (const [name, descriptor] of previous) {
			if (descriptor) Object.defineProperty(globalThis, name, descriptor);
			else delete globalThis[name];
		}
	});
	const camera = { current: null };
	const outline = {
		ring: [
			[-0.1419, 51.501],
			[-0.1415, 51.501],
			[-0.1415, 51.5013],
			[-0.1419, 51.5013],
		],
		source: "Microsoft building footprints",
		licence: "ODbL-1.0",
	};
	const renderWith = async (imagery) =>
		act(async () =>
			root.render(
				React.createElement(MapViewport, {
					document: emptyGeometry(),
					poses: [],
					selected: null,
					select() {},
					disabled: false,
					openReferences() {},
					camera,
					siteCentre: [-0.1417, 51.5011],
					siteOutline: outline,
					imagery,
				}),
			),
		);
	await renderWith(null);
	await until(() => document.querySelector('[data-map-status="ready"]'));
	await act(async () => button("Load street map").click());
	await until(() => document.querySelector('[data-map-status="ready"]'));
	const live = activeMap(maps);
	assert.ok(live.getLayer("linker-site-outline"));
	const first = {
		tiles: [
			"https://image.discomap.eea.europa.eu/arcgis/rest/services/GioLand/VHR2021_WM/ImageServer/exportImage?bbox={bbox-epsg-3857}",
		],
		credit: "European Union, Copernicus Land Monitoring Service (EEA)",
		licence: "Copernicus VHR Image Mosaic viewing service",
		licence_url: "https://land.copernicus.eu/en/products/european-image-mosaic",
	};
	await renderWith(first);
	assert.equal(activeMap(maps).getSource("linker-site-imagery"), undefined);
	assert.throws(
		() => live.options.transformRequest(first.tiles[0]),
		/not_authorized/,
	);
	await act(async () => button("Show aerial map").click());
	await until(() => activeMap(maps)?.getSource("linker-site-imagery"));
	const firstMap = activeMap(maps);
	const order = [...firstMap.layers.keys()];
	assert.deepEqual(order.slice(0, 2), [
		"linker-site-imagery",
		"linker-site-outline",
	]);
	assert.ok(
		order.indexOf("linker-map-roof") > order.indexOf("linker-site-outline"),
	);
	assert.equal(
		firstMap.options.transformRequest(
			"https://image.discomap.eea.europa.eu/arcgis/rest/services/GioLand/VHR2021_WM/ImageServer/exportImage?bbox=0,0,1,1",
		).credentials,
		"same-origin",
	);
	const second = {
		tiles: [
			"https://de-linker.com/wp-json/linker/v1/imagery/it?bbox={bbox-epsg-3857}",
		],
		credit: "Ministero dell'Ambiente e della Sicurezza Energetica (PCN)",
		licence: "Open data, Geoportale Nazionale",
		licence_url: "https://www.pcn.minambiente.it/",
	};
	await renderWith(second);
	assert.equal(firstMap.removals, 1);
	assert.throws(
		() => firstMap.options.transformRequest(first.tiles[0]),
		/not_authorized/,
	);
	assert.equal(activeMap(maps).getSource("linker-site-imagery"), undefined);
	assert.throws(
		() => activeMap(maps).options.transformRequest(second.tiles[0]),
		/not_authorized/,
	);
	await act(async () => button("Show aerial map").click());
	await until(() => activeMap(maps)?.getSource("linker-site-imagery"));
	const secondMap = activeMap(maps);
	assert.throws(
		() =>
			secondMap.options.transformRequest(
				"https://image.discomap.eea.europa.eu/arcgis/rest/services/GioLand/VHR2021_WM/ImageServer/exportImage?bbox=0,0,1,1",
			),
		/not_authorized/,
	);
	assert.equal(
		secondMap.options.transformRequest(
			"https://de-linker.com/wp-json/linker/v1/imagery/it?bbox=1022900,5694800,1023200,5695100",
		).credentials,
		"same-origin",
	);
	assert.match(
		secondMap.getSource("linker-site-imagery").attribution,
		/Ministero dell'Ambiente/,
	);
	await act(async () => button("Hide aerial map").click());
	behavior.autoLoad = false;
	t.after(() => {
		behavior.autoLoad = true;
	});
	await act(async () => button("Show aerial map").click());
	const pending = activeMap(maps);
	await act(async () => {
		document.dispatchEvent(new window.Event("wp_listen_for_consent_change"));
		pending.emit("load");
	});
	assert.equal(pending.removals, 1);
	assert.equal(pending.getSource("linker-site-imagery"), undefined);
	assert.throws(
		() => pending.options.transformRequest(second.tiles[0]),
		/not_authorized/,
	);
});
