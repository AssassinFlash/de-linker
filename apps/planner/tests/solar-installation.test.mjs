import test from "node:test";
import assert from "node:assert/strict";
import { register } from "node:module";
import React, { act, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import flat from "../../../fixtures/planning/geometry-flat.json" with { type: "json" };
import { setupDom, enter, until } from "./dom-fixture.mjs";
import { emptyBrief } from "../src/domain/brief.ts";
register("./map-library-loader.mjs", import.meta.url);

const aerial = {
	tiles: ["https://tile.example.test/{z}/{x}/{y}.png"],
	credit: "Fixture imagery",
	licence: "Fixture drawing licence",
	licence_url: "https://tile.example.test/licence",
};

async function mount(
	t,
	initial = { brief: emptyBrief(), geometry: structuredClone(flat) },
) {
	const dom = setupDom();
	const previousStyle = Object.getOwnPropertyDescriptor(
		globalThis,
		"getComputedStyle",
	);
	globalThis.getComputedStyle = window.getComputedStyle.bind(window);
	const style = document.createElement("style");
	style.textContent =
		".lp-map-host{--proto-neutral-300:#cccccc;--proto-teal-900:#112233;--proto-neutral-600:#445566;--proto-teal-700:#007777;--proto-teal-400:#44bbbb;--proto-neutral-100:#eeeeee;}";
	document.head.append(style);
	const { createRoot } = await import("react-dom/client");
	const { SolarInstallation } =
		await import("../src/components/configurator/SolarInstallation.tsx");
	const root = createRoot(dom.element);
	let current = initial,
		next = 0;
	const query = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	function Harness() {
		const [inputs, setInputs] = useState(current);
		return React.createElement(SolarInstallation, {
			inputs,
			config: { locale: "en", mapModuleUrl: null },
			session: { query_scope: "test" },
			client: {
				isCurrentScope: () => true,
				query: async (path) => {
					if (path === "places/lookup") return { imagery: aerial };
					if (path === "places/outline") return { found: false };
					return { schema_version: 1, provider: "woocommerce", pv_modules: [] };
				},
			},
			disabled: false,
			edit: (op) => {
				current = op(current);
				setInputs(current);
				return true;
			},
			next: () => next++,
		});
	}
	await act(async () =>
		root.render(
			React.createElement(
				QueryClientProvider,
				{ client: query },
				React.createElement(Harness),
			),
		),
	);
	t.after(async () => {
		query.clear();
		await dom.dispose(root);
		if (previousStyle)
			Object.defineProperty(globalThis, "getComputedStyle", previousStyle);
		else delete globalThis.getComputedStyle;
	});
	return {
		get inputs() {
			return current;
		},
		get next() {
			return next;
		},
	};
}
function button(text) {
	const el = [...document.querySelectorAll("button")].find(
		(e) => e.textContent.trim() === text,
	);
	assert.ok(el, `Missing ${text}`);
	return el;
}
async function click(text) {
	await act(async () => button(text).click());
}
function input(label) {
	const el = [...document.querySelectorAll("label")].find((e) =>
		e.querySelector("span")?.textContent.startsWith(label),
	);
	assert.ok(el, `Missing ${label}`);
	return el.querySelector("input");
}
test("new solar module details persist known capacity and source without requiring a roof", async (t) => {
	const app = await mount(t);
	await click("Use module details");
	await enter(input("Number of modules"), "12");
	await enter(input("Roof pitch"), "25");
	await enter(input("Azimuth (north = 0°)"), "180");
	await enter(input("Source of module details"), "Installer's module list");
	const known = app.inputs.pvgis_reference_setup;
	assert.equal(known.model, "pvgis_5_3_known_ac_reference_v1");
	assert.equal(
		known.arrays[0].peak_power_kwp,
		(12 * flat.module_specs[0].stc_power_w) / 1000,
	);
	assert.equal(known.arrays[0].tilt_deg, 25);
	assert.equal(known.arrays[0].source_note, "Installer's module list");
	assert.equal(app.inputs.pvgis_reference, undefined);
	await enter(input("Latitude"), "52.12567");
	await enter(input("Longitude"), "5.12567");
	await enter(input("Calendar year"), "2020");
	await enter(input("System loss"), "14");
	await enter(input("Source of the model settings"), "Commissioning report");
	for (const [label, value] of [
		["Radiation database", "PVGIS-ERA5"],
		["PV reference technology", "crystSi"],
		["Mounting place", "free"],
		["Terrain horizon", "true"],
	]) {
		const select = [...document.querySelectorAll("label")]
			.find((field) => field.querySelector("span")?.textContent === label)
			.querySelector("select");
		await act(async () => {
			select.value = value;
			select.dispatchEvent(new window.Event("change", { bubbles: true }));
		});
	}
	assert.equal(app.inputs.brief.site.latitude, 52.12567);
	assert.equal(app.inputs.brief.site.coordinate_basis, "user_entered");
	assert.deepEqual(
		app.inputs.pvgis_reference,
		app.inputs.pvgis_reference_setup,
	);
	await click("Continue with energy use");
	assert.equal(app.next, 1);
});
test("a project with a located building starts on the aerial map without creating a measurement origin", async (t) => {
	const brief = emptyBrief();
	const app = await mount(t, {
		brief: {
			...brief,
			site: {
				...brief.site,
				country_code: "DE",
				location_label: "Karlstraße 1, 80333 München",
				postal_code: "80333",
				latitude: 48.145,
				longitude: 11.566,
				coordinate_basis: "user_entered",
			},
		},
	});
	assert.equal(
		button("Place modules on the roof").getAttribute("aria-pressed"),
		"true",
	);
	assert.equal(button("Aerial map").getAttribute("aria-pressed"), "true");
	await until(
		() =>
			document.querySelector('[data-map-status="ready"]') &&
			button("Show aerial map"),
	);
	assert.equal(app.inputs.geometry, undefined);
});

test("the first aerial roof uses the selected roof corner as its confirmed origin", async (t) => {
	const brief = emptyBrief();
	const app = await mount(t, {
		brief: {
			...brief,
			site: {
				...brief.site,
				country_code: "DE",
				location_label: "Karlstraße 1, 80333 München",
				postal_code: "80333",
				latitude: 48.145,
				longitude: 11.566,
				coordinate_basis: "user_entered",
			},
		},
		geometry: {
			...flat,
			roofs: [],
			arrays: [],
			obstacles: [],
			keepouts: [],
			layout_rules: [],
		},
	});
	const { maps } = await import("./map-library-fixture.mjs");
	const map = () => maps.findLast((value) => !value.removed);
	await until(
		() =>
			button("Show aerial map") &&
			document.querySelector('[data-map-status="ready"]'),
	);
	await click("Draw roof");
	assert.equal(document.querySelector('[data-collecting="true"]'), null);
	await click("Show aerial map");
	await until(() => map().getSource("linker-site-imagery"));
	async function point(lng, lat) {
		await act(async () => {
			for (const type of ["pointerdown", "pointerup"]) {
				const event = new window.Event(type, { bubbles: true });
				Object.assign(event, {
					pointerId: 1,
					isPrimary: true,
					button: 0,
					clientX: 20,
					clientY: 20,
				});
				map().getCanvas().dispatchEvent(event);
			}
			map().emit("click", {
				point: { x: 20, y: 20 },
				originalEvent: { detail: 1 },
				lngLat: { lng, lat },
			});
		});
	}
	for (const [lng, lat] of [
		[11.56605, 48.14505],
		[11.5662, 48.14505],
		[11.5662, 48.14515],
		[11.56605, 48.14515],
	])
		await point(lng, lat);
	assert.deepEqual(app.inputs.geometry.roofs, []);
	assert.equal(app.inputs.geometry.coordinate_system.anchor, null);
	for (const [label, value] of [
		["Pitch", "0"],
		["Azimuth", "180"],
		["Relative roof height", "0"],
		["Drawing source", "Licensed aerial drawing and installer roof dimensions"],
	])
		await enter(input(label), value);
	await act(async () => document.querySelector(".sc-check input").click());
	await click("Confirm roof and map origin");
	const { coordinate_system: frame, roofs, sources } = app.inputs.geometry;
	assert.equal(roofs.length, 1);
	assert.equal(frame.anchor.longitude_deg, 11.56605);
	assert.equal(frame.anchor.latitude_deg, 48.14505);
	assert.equal(frame.north_reference, "true_north");
	assert.equal(frame.north_source_id, roofs[0].source_id);
	assert.equal(
		sources.find((source) => source.id === frame.north_source_id).permissions
			.export,
		"unknown",
	);
	await click("Place modules");
	await click("Review panel layout");
	assert.ok(
		document.activeElement === input("Rows"),
		"panel review should focus the row count",
	);
	await enter(input("Rows"), "1");
	await enter(input("Columns"), "2");
	await enter(input("Module gap"), "0.05");
	map().hits = [{ properties: { object_id: roofs[0].id } }];
	await point(11.56608, 48.14512);
	assert.equal(app.inputs.geometry.arrays.length, 1);
	assert.equal(app.inputs.geometry.arrays[0].columns, 2);
});

test("the solar page records a named map origin only after confirmation", async (t) => {
	const brief = emptyBrief();
	const app = await mount(t, {
		brief,
	});
	await click("Place modules on the roof");
	assert.equal(app.inputs.geometry, undefined);
	await enter(input("Drawing source"), "Installer site plan");
	await act(async () => document.querySelector(".sc-check input").click());
	for (const [label, value] of [
		["Width", "8"],
		["Depth", "5"],
		["Pitch", "25"],
		["Azimuth", "180"],
		["Relative roof height", "3"],
		["Origin east / U", "0"],
		["Origin north / V", "0"],
	])
		await enter(input(label), value);
	await click("Add rectangular roof");
	assert.equal(app.inputs.geometry.roofs.length, 1);
	const permission = document.querySelector('select[name="export"]');
	assert.ok(permission, "the drawing's report permission can be set on Solar");
	assert.equal(permission.value, "unknown");
	await act(async () => {
		permission.value = "permitted";
		permission.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
	assert.equal(app.inputs.geometry.sources[0].permissions.export, "permitted");
	assert.equal(app.inputs.geometry.coordinate_system.anchor, null);
	await enter(input("Latitude"), "52.09");
	assert.equal(app.inputs.geometry.coordinate_system.anchor, null);
	await enter(input("Longitude"), "5.12");
	assert.equal(app.inputs.geometry.coordinate_system.anchor, null);
	await click("Confirm site coordinates as map origin and use true north");
	const { anchor, north_reference, north_source_id } =
		app.inputs.geometry.coordinate_system;
	assert.deepEqual(anchor, {
		latitude_deg: 52.09,
		longitude_deg: 5.12,
		datum: "EPSG:4326",
		source_id: north_source_id,
	});
	assert.equal(north_reference, "true_north");
	assert.equal(
		app.inputs.geometry.sources.find((source) => source.id === north_source_id)
			.note,
		"Installer site plan",
	);
	assert.deepEqual(app.inputs.geometry.coordinate_system.anchor, anchor);
	await enter(input("Width"), "1");
	await enter(input("Depth"), "1");
	await enter(input("Origin east / U"), "2");
	await enter(input("Origin north / V"), "2");
	await enter(input("Obstacle height above roof"), "0.5");
	await click("Add obstacle");
	assert.equal(
		app.inputs.geometry.obstacles[0].roof_id,
		app.inputs.geometry.roofs[0].id,
	);
	assert.equal(app.inputs.geometry.obstacles[0].height_m, 0.5);
});

test("new roof interaction places moves rotates removes and undoes an actual module group", async (t) => {
	const app = await mount(t);
	await click("Place modules on the roof");
	await enter(input("Rows"), "1");
	await enter(input("Columns"), "2");
	await enter(input("Module gap"), "0.05");
	await enter(input("Origin east / U"), "1");
	await enter(input("Origin north / V"), "1");
	const before = app.inputs.geometry.arrays.length;
	await click("Place module group");
	assert.equal(app.inputs.geometry.arrays.length, before + 1);
	const added = app.inputs.geometry.arrays.at(-1);
	await click("→");
	assert.deepEqual(app.inputs.geometry.arrays.at(-1).origin_uv, [1.1, 1]);
	await click("Rotate selected");
	assert.equal(app.inputs.geometry.arrays.at(-1).rotation_deg, 90);
	await click("Remove selected");
	assert.equal(app.inputs.geometry.arrays.length, before);
	await click("Undo");
	assert.equal(app.inputs.geometry.arrays.at(-1).id, added.id);
	const layout = app.inputs.geometry;
	const { register } = await import("node:module");
	register("./scene-renderer-loader.mjs", import.meta.url);
	const { behavior } = await import("./scene-renderer-three.mjs");
	behavior.mode = "ready";
	globalThis.getComputedStyle = window.getComputedStyle.bind(window);
	t.after(() => delete globalThis.getComputedStyle);
	await click("3D view");
	await until(() => document.querySelector('[data-renderer="WebGL 2"]'));
	assert.equal(document.querySelector(".sc-roof-board"), null);
	await click("Plan view");
	assert.ok(document.querySelector(".sc-roof-board"));
	assert.equal(app.inputs.geometry, layout);
	assert.deepEqual(
		app.inputs.geometry.coordinate_system,
		flat.coordinate_system,
	);
});
