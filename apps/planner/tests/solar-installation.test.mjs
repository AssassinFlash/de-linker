import test from "node:test";
import assert from "node:assert/strict";
import { register } from "node:module";
import React, { act, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import flat from "../../../fixtures/planning/geometry-flat.json" with { type: "json" };
import plannerGerman from "../../../plugins/linker-tools/languages/linker-tools-de_DE_formal-cf89287c9001d7518d0d20e58c3eb721.json" with { type: "json" };
import { setupDom, enter, until } from "./dom-fixture.mjs";
import { emptyBrief } from "../src/domain/brief.ts";
import { buildCalibration } from "../src/domain/imageCalibration.ts";
register("./map-library-loader.mjs", import.meta.url);

const aerial = {
	tiles: ["https://tile.example.test/{z}/{x}/{y}.png"],
	credit: "Fixture imagery",
	licence: "Fixture drawing licence",
	licence_url: "https://tile.example.test/licence",
};
const viewing = {
	tiles: ["https://image.discomap.eea.europa.eu/image?bbox={bbox-epsg-3857}"],
	credit: "European Union, Copernicus Land Monitoring Service (EEA)",
	licence: "Copernicus VHR Image Mosaic viewing service",
	licence_url:
		"https://land.copernicus.eu/en/products/european-image-mosaic/very-high-resolution-image-mosaic-2021-true-colour-2m",
};

async function mount(
	t,
	initial = { brief: emptyBrief(), geometry: structuredClone(flat) },
	placeImagery = aerial,
	viewingImagery = null,
	locale = "en",
) {
	const dom = setupDom();

	if (locale === "de") {
		window.wp.i18n.__ = (message) =>
			plannerGerman.locale_data.messages[message]?.[0] ?? message;
	}
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
			config: { locale, mapModuleUrl: null },
			session: { query_scope: "test" },
			client: {
				isCurrentScope: () => true,
				query: async (path) => {
					if (path === "places/lookup")
						return { imagery: placeImagery, viewing_imagery: viewingImagery };
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
		(e) =>
			e.getAttribute("aria-label") === text || e.textContent.trim() === text,
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
test("reopened roof source shows its declared precision, measurement note and recorded image scale", async (t) => {
	const geometry = structuredClone(flat);
	Object.assign(geometry.sources[0], {
		kind: "user_drawing",
		rights_basis: "user_attestation",
		note: "roof-plan.png",
		spatial_precision_m: 0.05,
		calibration_note: "Installer checked the second span.",
		calibration: buildCalibration({
			view: "horizontal_plan",
			image: { media_type: "image/png", pixel_width: 800, pixel_height: 800 },
			controlPoints: { first: [100, 100], second: [400, 100] },
			knownLength: 6,
			downslopeBearingDeg: 0,
			checkPoints: { first: [100, 200], second: [700, 200] },
			checkLength: 12,
			checkToleranceRatio: 0.01,
			pitchDeg: 0,
			note: "Drawing scale verified.",
		}),
	});
	await mount(t, { brief: emptyBrief(), geometry }, aerial, null, "de");
	const properties = [...document.querySelectorAll("fieldset")].find(
		(field) =>
			field.querySelector(":scope > legend")?.textContent === "roof-plan.png",
	);
	assert.ok(properties);
	assert.match(properties.textContent, /0,05/);
	assert.match(properties.textContent, /Installer checked the second span\./);
	assert.match(properties.textContent, /0,02 m je Pixel/);
});
test("a saved roof opening remains visible when switching between the overview and editable plan", async (t) => {
	const geometry = structuredClone(flat);
	geometry.roofs[0].holes_uv = [
		[
			[9, 9],
			[11, 9],
			[11, 11],
			[9, 11],
		],
	];
	const app = await mount(t, { brief: emptyBrief(), geometry });
	function assertOpening(svg) {
		const shape = svg?.querySelector(".lp-roof-shape");
		assert.equal(shape?.getAttribute("fill-rule"), "evenodd");
		assert.equal(
			shape?.getAttribute("d"),
			"M0,0 L20,0 L20,20 L0,20Z M9,9 L11,9 L11,11 L9,11Z",
		);
	}
	assertOpening(document.querySelector('svg[aria-label="Fixture roof"]'));
	assert.equal(document.querySelector("dialog[open]"), null);
	await click("Open roof layout");
	assertOpening(
		document.querySelector('dialog[open] svg[aria-label="Editable roof plan"]'),
	);
	await click("Draw roof");
	assert.equal(button("Close").disabled, true);
	await click("Select / move");
	await click("Close");
	assert.equal(document.querySelector("dialog[open]"), null);
	assertOpening(document.querySelector('svg[aria-label="Fixture roof"]'));
	assert.deepEqual(app.inputs.geometry, geometry);
});
test("site coordinates keep pasted notation and leave mixed or out-of-range values available for correction", async (t) => {
	const app = await mount(t, { geometry: structuredClone(flat) });
	assert.equal(app.inputs.brief, undefined);
	const latitude = input("Latitude"),
		longitude = input("Longitude");
	await enter(latitude, "48.1689");
	await enter(longitude, "11,5844");
	assert.equal(app.inputs.brief.site.longitude, 11.5844);
	await enter(latitude, "1.234,5");
	assert.equal(latitude.value, "1.234,5");
	assert.equal(latitude.getAttribute("aria-invalid"), "true");
	assert.equal(app.inputs.brief.site.latitude, 48.1689);
	await enter(longitude, "181");
	await enter(latitude, "48,17");
	assert.equal(button("Continue with energy use").disabled, true);
	assert.equal(longitude.value, "181");
	await enter(longitude, "");
	assert.equal(button("Continue with energy use").disabled, false);
	assert.equal(app.inputs.brief.site.latitude, 48.17);
	assert.equal(app.inputs.brief.site.longitude, null);
});
test("an anchored roof keeps unfinished site coordinates available across roof modes", async (t) => {
	const geometry = structuredClone(flat);
	geometry.coordinate_system.anchor = {
		datum: "EPSG:4326",
		latitude_deg: 51.5,
		longitude_deg: -0.12,
		source_id: geometry.sources[0].id,
	};
	await mount(t, { brief: emptyBrief(), geometry });
	await click("Use module details");
	await enter(input("Latitude"), "1.234,5");
	await click("Place modules on the roof");
	assert.equal(button("Continue with energy use").disabled, true);
	assert.equal(input("Latitude").value, "1.234,5");
	await click("Use module details");
	assert.equal(input("Latitude").value, "1.234,5");
	await click("Place modules on the roof");
	for (const raw of ["5", "51", "51,", "51,5"])
		await enter(input("Latitude"), raw);
	assert.equal(button("Continue with energy use").disabled, false);
	await click("Use module details");
	await click("Place modules on the roof");
	assert.equal(document.querySelector('input[aria-invalid="true"]'), null);
	await click("Use module details");
	assert.equal(input("Latitude").value, "51.5");
});
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
	await click("Open roof layout");
	assert.equal(button("Aerial map").getAttribute("aria-pressed"), "true");
	await until(
		() =>
			document.querySelector('[data-map-status="ready"]') &&
			button("Show aerial map"),
	);
	assert.equal(app.inputs.geometry, undefined);
});

test("a site without licensed aerial imagery can open the roof image wizard while the draw tool is selected", async (t) => {
	const brief = emptyBrief();
	const app = await mount(
		t,
		{
			brief: {
				...brief,
				site: {
					...brief.site,
					country_code: "GB",
					location_label: "London",
					latitude: 51.5,
					longitude: -0.12,
				},
			},
		},
		null,
	);
	await click("Open roof layout");
	await until(() => button("Load street map"));
	await click("Draw roof");
	assert.equal(button("Calibrate a roof image").disabled, false);
	const form = await traceRoofImage(t, "roof-plan.png");
	form.elements.namedItem("source").value = "roof-plan.png";
	form.elements.namedItem("rights").value =
		"Owner drawing with permission to retain and derive";
	await click("Add roof to current design");
	assert.equal(
		app.inputs.geometry,
		undefined,
		"permission must be confirmed before adding geometry",
	);
	await act(async () => form.elements.namedItem("retention").click());
	await click("Add roof to current design");
	assert.ok(
		app.inputs.geometry,
		document.querySelector(".lp-import-panel [role=alert]")?.textContent,
	);
	const { roofs, sources, coordinate_system: frame } = app.inputs.geometry;
	assert.equal(roofs.length, 1);
	assert.equal(frame.anchor, null);
	assert.equal(sources[0].calibration.m_per_pixel, 0.02);
	assert.equal(
		sources[0].rights_note,
		"Owner drawing with permission to retain and derive",
	);
	assert.equal(sources[0].rights_basis, "user_attestation");
	assert.equal(button("Plan view").getAttribute("aria-pressed"), "true");
	assert.equal(button("Select / move").getAttribute("aria-pressed"), "true");
});

async function traceRoofImage(t, image, roofId, length = "12") {
	await click("Calibrate a roof image");
	const form = document.querySelector(".lp-import-panel form");
	if (roofId) {
		const target = form.elements.namedItem("target");
		await act(async () => {
			target.value = roofId;
			target.dispatchEvent(new window.Event("change", { bubbles: true }));
		});
	}
	const fileInput = form.querySelector(
		'input[type="file"][accept*="image/png"]',
	);
	assert.ok(fileInput);
	const originalCreate = globalThis.createImageBitmap;
	globalThis.createImageBitmap = async () => ({
		width: 800,
		height: 600,
		close() {},
	});
	t.after(() => {
		globalThis.createImageBitmap = originalCreate;
	});
	const file = new Blob([new Uint8Array([137, 80, 78, 71])], {
		type: "image/png",
	});
	Object.defineProperty(file, "name", { value: image });
	Object.defineProperty(fileInput, "files", { value: [file] });
	await act(async () =>
		fileInput.dispatchEvent(new window.Event("change", { bubbles: true })),
	);
	assert.equal(form.querySelector(".lp-file-name").textContent, image);
	const mark = async (x, y) => {
		const svg = form.querySelector(".lp-plan-svg");
		svg.getBoundingClientRect = () => ({
			left: 0,
			top: 0,
			width: 800,
			height: 600,
		});
		await act(async () =>
			svg.dispatchEvent(
				new window.MouseEvent("click", {
					bubbles: true,
					clientX: x,
					clientY: y,
				}),
			),
		);
	};
	await click("Continue");
	await mark(100, 500);
	await mark(700, 500);
	await enter(form.elements.namedItem("length"), length);
	await click("Check span (0 of 2)");
	await mark(100, 100);
	await mark(700, 100);
	await enter(form.elements.namedItem("check_length"), length);
	await click("Continue");
	await click("Roof outline (0 points)");
	for (const point of [
		[100, 100],
		[700, 100],
		[700, 500],
		[100, 500],
	])
		await mark(...point);
	return form;
}

async function declareDrawing(form, image, rights, exportPermission) {
	form.elements.namedItem("source").value = image;
	form.elements.namedItem("rights").value = rights;
	form.elements.namedItem("export").value = exportPermission;
}

test("replacing and recalibrating a roof requires permission for the selected drawing and preserves shared sources", async (t) => {
	const original = structuredClone(flat);
	original.sources[0] = {
		...original.sources[0],
		kind: "user_drawing",
		note: "Provider aerial imagery",
		rights_note: "Provider licence",
		rights_basis: "referenced_licence",
		reference_url: "https://example.com/licence",
	};
	original.coordinate_system = {
		...original.coordinate_system,
		north_reference: "true_north",
		north_source_id: "survey",
		anchor: {
			latitude_deg: 51.5,
			longitude_deg: -0.12,
			source_id: "survey",
			datum: "EPSG:4326",
		},
	};
	original.roofs.push({
		...original.roofs[0],
		id: "other_roof",
		origin_enu: [30, -20, 4],
	});
	const app = await mount(t, { brief: emptyBrief(), geometry: original });
	await click("Open roof layout");
	let form = await traceRoofImage(t, "owner-plan.png", "roof");
	await click("Add roof to current design");
	assert.deepEqual(
		app.inputs.geometry,
		original,
		"replacement needs fresh permission",
	);
	await declareDrawing(
		form,
		"Owner plan",
		"Owner permits derivation and retention",
		"prohibited",
	);
	await act(async () => form.elements.namedItem("retention").click());
	await click("Add roof to current design");
	const replaced = app.inputs.geometry;
	const roof = replaced.roofs.find(({ id }) => id === "roof");
	const source = replaced.sources.find(({ id }) => id === roof.source_id);
	assert.equal(source.rights_basis, "user_attestation");
	assert.equal(source.reference_url, null);
	assert.equal(source.permissions.export, "prohibited");
	assert.deepEqual(
		replaced.sources.find(({ id }) => id === "survey"),
		original.sources[0],
	);
	assert.deepEqual(
		replaced.roofs.find(({ id }) => id === "other_roof"),
		original.roofs[1],
	);
	assert.deepEqual(roof.origin_enu, original.roofs[0].origin_enu);
	assert.deepEqual(replaced.coordinate_system, original.coordinate_system);
	assert.deepEqual(replaced.arrays, original.arrays);

	form = await traceRoofImage(t, "owner-plan.png", "roof", "15");
	await click("Add roof to current design");
	assert.deepEqual(
		app.inputs.geometry,
		replaced,
		"reselected image needs fresh permission",
	);
	await declareDrawing(form, "Owner plan", source.rights_note, "prohibited");
	await act(async () => form.elements.namedItem("retention").click());
	await click("Add roof to current design");
	const recalibrated = app.inputs.geometry;
	const recalibratedRoof = recalibrated.roofs.find(({ id }) => id === "roof");
	assert.equal(
		recalibrated.sources.find(({ id }) => id === recalibratedRoof.source_id)
			.calibration.m_per_pixel,
		0.025,
	);
	assert.equal(recalibratedRoof.id, roof.id);
	assert.deepEqual(
		recalibrated.roofs.find(({ id }) => id === "other_roof"),
		original.roofs[1],
	);
});

test("undoing image calibration restores known PV inputs and keeps later project and PV settings edits", async (t) => {
	const known = {
		schema_version: 1,
		model: "pvgis_5_3_known_ac_reference_v1",
		radiation_database: "PVGIS-ERA5",
		year: 2020,
		pv_technology: "crystSi",
		mounting_place: "free",
		system_loss_percent: 14,
		use_terrain_horizon: true,
		source_note: "Commissioning report",
		arrays: [
			{
				id: "original_array",
				peak_power_kwp: 6,
				tilt_deg: 25,
				azimuth_north_clockwise_deg: 180,
				source_note: "Installer's module list",
			},
		],
	};
	const app = await mount(t, {
		brief: emptyBrief(),
		pvgis_reference_setup: known,
		pvgis_reference: known,
	});
	const form = await traceRoofImage(t, "roof-plan.png");
	declareDrawing(form, "Roof plan", "Use permitted", "unknown");
	await act(async () => form.elements.namedItem("retention").click());
	await click("Add roof to current design");
	assert.equal(app.inputs.geometry.roofs.length, 1);
	assert.equal(
		app.inputs.pvgis_reference_setup.model,
		"pvgis_5_3_roof_ac_reference_v1",
	);
	await click("Close");
	await enter(input("Latitude"), "52.12567");
	await enter(input("System loss"), "12");
	await click("Open roof layout");
	await click("Undo");
	assert.deepEqual(app.inputs.pvgis_reference_setup, {
		...known,
		system_loss_percent: 12,
	});
	assert.equal(app.inputs.geometry, undefined);
	assert.deepEqual(
		app.inputs.pvgis_reference,
		app.inputs.pvgis_reference_setup,
	);
	assert.equal(app.inputs.inactive_known_pv_arrays, undefined);
	assert.equal(app.inputs.brief.site.latitude, 52.12567);
	assert.equal(
		button("Use module details").getAttribute("aria-pressed"),
		"true",
	);
});

test("Solar can show and withdraw a viewing mosaic without acquiring geometry", async (t) => {
	const brief = emptyBrief();
	const otherOrigin = "https://other.example.test/19/1/2.png";
	const official = { ...viewing, tiles: [...viewing.tiles, otherOrigin] };
	const geometry = structuredClone(flat);
	const sourceId = geometry.sources[0].id;
	Object.assign(geometry.coordinate_system, {
		anchor: {
			datum: "EPSG:4326",
			longitude_deg: -0.12,
			latitude_deg: 51.5,
			source_id: sourceId,
		},
		north_reference: "true_north",
		north_source_id: sourceId,
	});
	const app = await mount(
		t,
		{
			brief: {
				...brief,
				site: {
					...brief.site,
					country_code: "GB",
					location_label: "London",
					latitude: 51.5,
					longitude: -0.12,
				},
			},
			geometry,
		},
		null,
		official,
	);
	const { maps } = await import("./map-library-fixture.mjs");
	const map = () => maps.findLast((value) => !value.removed);
	await click("Open roof layout");
	const tileUrl = official.tiles[0].replace("{bbox-epsg-3857}", "1,2,3,4");
	await until(() => document.querySelector('[data-map-status="ready"]'));
	assert.throws(
		() => map().options.transformRequest(tileUrl),
		/not_authorized/,
	);
	assert.equal(map().getSource("linker-site-imagery"), undefined);
	await click("Show aerial map");
	await until(() => map().getSource("linker-site-imagery"));
	const viewer = map();
	assert.equal(viewer.options.transformRequest(tileUrl).url, tileUrl);
	for (const other of [
		otherOrigin,
		"https://tiles.openfreemap.org/styles/liberty",
		tileUrl.replace(".europa.eu/", ".europa.eu.other.test/"),
		tileUrl.replace(".europa.eu/", ".europa.eu:8443/"),
	])
		assert.throws(
			() => viewer.options.transformRequest(other),
			/not_authorized/,
		);
	assert.match(
		document.querySelector(".lp-map-provider").textContent,
		/Copernicus Land Monitoring Service/,
	);
	assert.equal(
		document.querySelector(".lp-map-provider a").href,
		official.licence_url,
	);
	await act(async () => {
		const tile = { state: "loading" };
		viewer.emit("sourcedataloading", { sourceId: "linker-site-imagery", tile });
		tile.state = "loaded";
		viewer.emit("idle");
	});
	for (const tool of ["Draw roof", "Obstacle", "Place modules"]) {
		await click(tool);
		assert.equal(document.querySelector('[data-collecting="true"]'), null);
		assert.equal(document.querySelector('[data-array-placement="true"]'), null);
		assert.doesNotMatch(
			document.body.textContent,
			/Add corner at map centre|Place panels at map centre|Finish outline/,
		);
		await act(async () => {
			viewer
				.getCanvas()
				.dispatchEvent(
					new window.KeyboardEvent("keydown", { key: "Enter", bubbles: true }),
				);
			for (const type of ["pointerdown", "pointerup"]) {
				const event = new window.Event(type, { bubbles: true });
				Object.assign(event, {
					pointerId: 1,
					isPrimary: true,
					button: 0,
					clientX: 20,
					clientY: 20,
				});
				viewer.getCanvas().dispatchEvent(event);
			}
			viewer.hits = [{ properties: { object_id: geometry.roofs[0].id } }];
			viewer.emit("click", {
				point: { x: 20, y: 20 },
				originalEvent: { detail: 1 },
				lngLat: { lng: -0.12, lat: 51.5 },
			});
		});
		assert.deepEqual(app.inputs.geometry, geometry);
	}
	assert.equal(button("Calibrate a roof image").disabled, false);
	await act(async () =>
		document.dispatchEvent(new window.Event("cookieyes_consent_update")),
	);
	assert.equal(viewer.removed, true);
	assert.throws(
		() => viewer.options.transformRequest(tileUrl),
		/not_authorized/,
	);
	await until(() => document.querySelector('[data-map-status="ready"]'));
	assert.equal(button("Show aerial map").getAttribute("aria-pressed"), "false");
	await click("Show aerial map");
	await until(() => map().getSource("linker-site-imagery"));
	const shownAgain = map();
	await click("Hide aerial map");
	assert.equal(shownAgain.removed, true);
	assert.throws(
		() => shownAgain.options.transformRequest(tileUrl),
		/not_authorized/,
	);
});

test("German Solar explains viewing consent and the customer drawing path", async (t) => {
	const brief = emptyBrief();
	await mount(
		t,
		{
			brief: {
				...brief,
				site: {
					...brief.site,
					country_code: "NO",
					location_label: "Oslo",
					latitude: 59.9139,
					longitude: 10.7522,
				},
			},
		},
		null,
		viewing,
		"de",
	);
	await click(window.wp.i18n.__("Open roof layout"));
	await until(() => document.querySelector('[data-map-status="ready"]'));
	assert.match(
		document.body.textContent,
		/Dieses Luftbild dient nur zur Ansicht\./,
	);
	assert.match(
		document.body.textContent,
		/Nutzen Sie die Planansicht oder ein Dachbild/,
	);
	await click("Luftbildkarte anzeigen");
	assert.equal(
		button("Luftbildkarte ausblenden").getAttribute("aria-pressed"),
		"true",
	);
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
	await click("Open roof layout");
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
	assert.equal(
		Boolean(document.querySelector('[data-collecting="true"]')),
		false,
	);
	await point(11.566, 48.145);
	await act(async () => {
		const current = map();
		const good = { state: "loading" },
			bad = { state: "loading" };
		for (const tile of [good, bad])
			current.emit("sourcedataloading", {
				sourceId: "linker-site-imagery",
				tile,
			});
		good.state = "loaded";
		bad.state = "errored";
		current.emit("idle");
	});
	assert.equal(document.querySelector('[data-collecting="true"]'), null);
	assert.ok(button("Retry loading map"));
	await click("Retry loading map");
	const finishAerial = async () => {
		await until(() => map().getSource("linker-site-imagery"));
		await act(async () => {
			const current = map();
			const tile = { state: "loading" };
			current.emit("sourcedataloading", {
				sourceId: "linker-site-imagery",
				tile,
			});
			tile.state = "loaded";
			current.emit("idle");
		});
	};
	await finishAerial();
	assert.ok(document.querySelector('[data-collecting="true"]'));
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
	])
		await enter(input(label), value);
	await act(async () => document.querySelector(".sc-check input").click());
	await act(async () =>
		document.dispatchEvent(new window.Event("cookieyes_consent_update")),
	);
	assert.equal(button("Confirm roof and map origin").disabled, true);
	await click("Confirm roof and map origin");
	assert.deepEqual(app.inputs.geometry.roofs, []);
	await click("Show aerial map");
	await finishAerial();
	await click("Confirm roof and map origin");
	const { coordinate_system: frame, roofs, sources } = app.inputs.geometry;
	assert.equal(roofs.length, 1);
	assert.equal(frame.anchor.longitude_deg, 11.56605);
	assert.equal(frame.anchor.latitude_deg, 48.14505);
	assert.equal(frame.north_reference, "true_north");
	assert.equal(frame.north_source_id, roofs[0].source_id);
	const source = sources.find((source) => source.id === frame.north_source_id);
	assert.equal(source.note, aerial.credit);
	assert.equal(source.rights_note, `${aerial.licence} (${aerial.licence_url})`);
	assert.equal(source.reference_url, aerial.licence_url);
	assert.deepEqual(source.permissions, {
		derive: "permitted",
		retain: "permitted",
		export: "unknown",
	});
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
	await click("Open roof layout");
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
	await click("Open roof layout");
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
