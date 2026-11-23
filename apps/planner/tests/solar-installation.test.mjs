import test from "node:test";
import assert from "node:assert/strict";
import { register } from "node:module";
import React, { act, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import flat from "../../../fixtures/planning/geometry-flat.json" with { type: "json" };
import plannerGerman from "../../../plugins/linker-tools/languages/linker-tools-de_DE_formal-cf89287c9001d7518d0d20e58c3eb721.json" with { type: "json" };
import { setupDom, enter, until } from "./dom-fixture.mjs";
import { buildCalibration } from "../src/domain/imageCalibration.ts";
import { emptyBrief } from "../src/domain/brief.ts";
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
	lookupCoordinates = {},
	mapEntry = {},
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
		".sc-map-host{--proto-neutral-300:#cccccc;--proto-teal-900:#112233;--proto-neutral-600:#445566;--proto-teal-700:#007777;--proto-teal-400:#44bbbb;--proto-neutral-100:#eeeeee;}";
	document.head.append(style);
	const { createRoot } = await import("react-dom/client");
	const { SolarInstallation } =
		await import("../src/components/configurator/SolarInstallation.tsx");
	const root = createRoot(dom.element);
	let current = initial,
		next = 0;
	const placeQueries = [];
	const query = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	function Harness() {
		const [inputs, setInputs] = useState(current);
		return React.createElement(SolarInstallation, {
			...mapEntry,
			inputs,
			config: { locale, mapModuleUrl: null, ...mapEntry.config },
			session: { query_scope: "test" },
			client: {
				isCurrentScope: () => true,
				query: async (path) => {
					if (path === "places/lookup") {
						placeQueries.push(path);
						return {
							imagery: placeImagery,
							viewing_imagery: viewingImagery,
							...lookupCoordinates,
						};
					}
					if (path === "places/outline") return { found: false };
					return { schema_version: 1, provider: "woocommerce", products: [] };
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
		placeQueries,
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
	const named = [...document.querySelectorAll("input[aria-label]")].find(
		(el) => el.getAttribute("aria-label") === label,
	);
	if (named) return named;
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
test("saved roof openings survive preview, editing and reopening the same layout", async (t) => {
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
	function checkOpening(label) {
		const outline = document.querySelector(
			`svg[aria-label="${label}"] path[fill-rule="evenodd"]`,
		);
		assert.ok(outline, label);
		assert.equal(
			outline.getAttribute("d"),
			"M0,0 L20,0 L20,20 L0,20Z M9,9 L11,9 L11,11 L9,11Z",
		);
	}
	checkOpening("Roof layout preview");
	await click("Open roof layout");
	checkOpening("Editable roof plan");
	await click("Use this layout");
	checkOpening("Roof layout preview");
	assert.deepEqual(app.inputs.geometry, geometry);
});
test("site coordinates retain an invalid edit and accept a corrected decimal comma", async (t) => {
	const validation = [];
	const app = await mount(
		t,
		{ brief: emptyBrief(), geometry: structuredClone(flat) },
		aerial,
		null,
		"en",
		{},
		{ onCoordinateValidity: (valid) => validation.push(valid) },
	);
	await click("Use module details");
	await enter(input("Latitude"), "91,7");
	assert.equal(input("Latitude").value, "91,7");
	assert.equal(input("Latitude").getAttribute("aria-invalid"), "true");
	assert.equal(validation.at(-1), false);
	await enter(input("Latitude"), "51,72");
	await enter(input("Longitude"), "9.17");
	assert.equal(validation.at(-1), true);
	assert.equal(app.inputs.brief.site.latitude, 51.72);
	assert.equal(app.inputs.brief.site.longitude, 9.17);
});
test("German panel choices save the cell technology expected by the electrical calculation", async (t) => {
	const inputs = { brief: emptyBrief(), geometry: structuredClone(flat) };
	const app = await mount(t, inputs, aerial, null, "de");
	await click("Moduldaten bearbeiten");
	const field = document.querySelector("select[name=panel_cell_technology]");
	assert.deepEqual(
		[...field.options].map((o) => [o.label, o.value]),
		[
			["Unbekannt", ""],
			["Monokristallines Silizium", "monocrystalline"],
			["Polykristallines Silizium", "polycrystalline"],
		],
	);
	await act(async () => {
		field.value = "polycrystalline";
		field.dispatchEvent(new window.Event("change", { bubbles: true }));
	});
	await click("Weiter zum Energiebedarf");
	assert.equal(
		app.inputs.geometry.module_specs[0].electrical.cell_technology,
		"polycrystalline",
	);
});
test("continuing with edited panel settings preserves roof ownership and group quantities", async (t) => {
	const app = await mount(t);
	const geometry = app.inputs.geometry;
	await click("Edit panel parameters");
	await enter(input("Power per panel"), "497");
	await click("Continue with energy use");
	assert.equal(app.next, 1);
	assert.equal(app.inputs.geometry.module_specs[0].stc_power_w, 497);
	assert.equal(
		app.inputs.geometry.module_specs[0].id,
		geometry.module_specs[0].id,
	);
	assert.deepEqual(app.inputs.geometry.arrays, geometry.arrays);
	assert.deepEqual(app.inputs.geometry.roofs, geometry.roofs);
});
test("a known system capacity and a partial panel count survive edits independently", async (t) => {
	const app = await mount(t);
	await click("Use module details");
	await enter(input("Solar capacity"), "8");
	await enter(input("Number of modules"), "16");
	assert.equal(app.inputs.pvgis_reference_setup.arrays[0].peak_power_kwp, 8);
	await enter(input("Power per panel"), "430");
	assert.equal(app.inputs.pvgis_reference_setup.arrays[0].peak_power_kwp, 8);
	await enter(input("Solar capacity"), "");
	assert.equal(app.inputs.pvgis_reference_setup.arrays[0].peak_power_kwp, 6.88);
	assert.equal(input("Number of modules").value, "16");
});
test("new solar module details persist known capacity and source without requiring a roof", async (t) => {
	const app = await mount(t);
	await click("Use module details");
	await enter(
		input("Power per panel"),
		String(flat.module_specs[0].stc_power_w),
	);
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
	document.querySelector("summary").click();
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
test("a located project keeps the known-capacity path and opens the map only on request", async (t) => {
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
		button("Use module details").getAttribute("aria-pressed"),
		"true",
	);
	await enter(input("Solar capacity"), "5.5");
	assert.equal(app.inputs.pvgis_reference_setup.arrays[0].peak_power_kwp, 5.5);
	assert.deepEqual(app.placeQueries, []);
	await click("Continue with energy use");
	assert.equal(app.next, 1);
	await click("Place modules on the roof");
	assert.equal(document.querySelector('[data-map-status="ready"]'), null);
	await click("Open roof layout");
	assert.equal(button("Aerial map").getAttribute("aria-pressed"), "true");
	await until(
		() =>
			document.querySelector('[data-map-status="ready"]') &&
			button("Show aerial map"),
	);
	assert.equal(app.inputs.geometry, undefined);
	await click("Back");
	assert.equal(document.querySelector('[data-map-status="ready"]'), null);
	await click("Use module details");
	assert.equal(input("Solar capacity").value, "5.5");
});

test("a country and postcode center the aerial view without assigning a measurement origin", async (t) => {
	const brief = emptyBrief();
	const app = await mount(
		t,
		{
			brief: {
				...brief,
				site: {
					...brief.site,
					country_code: "NL",
					location_label: "9401 AB",
				},
			},
		},
		aerial,
		null,
		"en",
		{ latitude: 52.995, longitude: 6.562 },
	);
	await openRoof();
	await until(() => document.querySelector('[data-map-status="ready"]'));
	const { maps } = await import("./map-library-fixture.mjs");
	assert.deepEqual(
		maps.findLast((map) => !map.removed).options.center,
		[6.562, 52.995],
	);
	assert.equal(app.inputs.brief.site.latitude, null);
	assert.equal(app.inputs.geometry, undefined);
});

test("a roof address opens its consented aerial map ready to draw and honours withdrawal", async (t) => {
	const brief = emptyBrief();
	let consent = true;
	await mount(
		t,
		{
			brief: {
				...brief,
				site: {
					...brief.site,
					country_code: "NL",
					location_label: "Amsterdam",
				},
			},
		},
		aerial,
		null,
		"en",
		{ latitude: 52.37, longitude: 4.9 },
		{
			initialMap: true,
			takeImageryConsent: (source) => {
				assert.deepEqual(source, aerial);
				const granted = consent;
				consent = false;
				return granted;
			},
		},
	);
	await until(
		() =>
			document.querySelector('[data-map-status="ready"]') &&
			[...document.querySelectorAll("button")].some(
				(b) => b.textContent === "Hide aerial map",
			),
	);
	assert.equal(button("Draw polygon").getAttribute("aria-pressed"), "true");
	await act(async () =>
		document.dispatchEvent(new window.Event("cookieyes_consent_update")),
	);
	await until(() => document.querySelector('[data-map-status="ready"]'));
	assert.equal(button("Show aerial map").getAttribute("aria-pressed"), "false");
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
	await openRoof();
	await until(() => button("Load street map"));
	assert.equal(button("Draw polygon").disabled, true);
	assert.doesNotMatch(
		document.body.textContent,
		/Mark each roof corner on the aerial map/,
	);
	assert.match(
		document.body.textContent,
		/No aerial image is available for this location/,
	);
	await click("Enter roof measurements");
	await until(() => document.activeElement === input("Width"));
	assert.equal(button("Plan view").getAttribute("aria-pressed"), "true");
	await click("Aerial map");
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
		document.querySelector(".sc-import-panel [role=alert]")?.textContent,
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
	assert.equal(button("Select plane").getAttribute("aria-pressed"), "true");
});

async function openRoof(locale = "en") {
	await click(
		locale === "de"
			? "Module auf dem Dach platzieren"
			: "Place modules on the roof",
	);
	await act(async () =>
		document.querySelector(".sc-solar button.sc-primary").click(),
	);
}

async function traceRoofImage(t, image, roofId, length = "12") {
	if (!document.querySelector(".sc-roof-editor")) await openRoof();
	await click("Calibrate a roof image");
	const form = document.querySelector(".sc-import-panel form");
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
	assert.equal(form.querySelector(".sc-file-name").textContent, image);
	const mark = async (x, y) => {
		const svg = form.querySelector(".sc-plan-svg");
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
	await enter(input("Latitude"), "52.12567");
	await enter(input("System loss"), "12");
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
	const tileUrl = official.tiles[0].replace("{bbox-epsg-3857}", "1,2,3,4");
	await openRoof();
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
		document.querySelector(".sc-map-provider").textContent,
		/Copernicus Land Monitoring Service/,
	);
	assert.equal(
		document.querySelector(".sc-map-provider a").href,
		official.licence_url,
	);
	await act(async () => {
		const tile = { state: "loading" };
		viewer.emit("sourcedataloading", { sourceId: "linker-site-imagery", tile });
		tile.state = "loaded";
		viewer.emit("idle");
	});
	for (const tool of ["Draw polygon", "Obstacle", "Place modules"]) {
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
	await openRoof("de");
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
	await openRoof();
	await until(
		() =>
			button("Show aerial map") &&
			document.querySelector('[data-map-status="ready"]'),
	);
	await click("Draw polygon");
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
	assert.ok(
		!input("Pitch").closest("details"),
		"map measurements are beside the traced outline",
	);
	await act(async () =>
		document.dispatchEvent(new window.Event("cookieyes_consent_update")),
	);
	assert.equal(button("Finish outline").disabled, true);
	await click("Finish outline");
	assert.deepEqual(app.inputs.geometry.roofs, []);
	await click("Show aerial map");
	await finishAerial();
	await click("Finish outline");
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
	assert.equal(button("Place modules").getAttribute("aria-pressed"), "true");
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
	await click("Draw polygon");
	await until(() => document.querySelector('[data-collecting="true"]'));
	const canvas = map().getCanvas();
	map().unproject = ([x, y]) => ({
		lng: 11.567 + x / 100000,
		lat: 48.1455 - y / 100000,
	});
	await act(async () => {
		for (const [type, x, y] of [
			["pointerdown", 10, 10],
			["pointermove", 35, 10],
			["pointermove", 35, 30],
			["pointermove", 10, 30],
			["pointerup", 10, 10],
		]) {
			const event = new window.Event(type, { bubbles: true });
			Object.assign(event, {
				pointerId: 1,
				isPrimary: true,
				button: 0,
				clientX: x,
				clientY: y,
			});
			canvas.dispatchEvent(event);
		}
	});
	assert.equal(
		app.inputs.geometry.roofs.length,
		2,
		"releasing the traced outline applies the second roof",
	);
	const second = app.inputs.geometry.roofs[1];
	assert.equal(second.boundary_uv.length, 4);
	assert.equal(
		app.inputs.geometry.sources.find((s) => s.id === second.source_id)
			.reference_url,
		aerial.licence_url,
	);
	assert.deepEqual(app.inputs.geometry.coordinate_system, frame);
});

test("the solar page records a named map origin only after confirmation", async (t) => {
	const brief = emptyBrief();
	const app = await mount(t, {
		brief,
	});
	await openRoof();
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

test("choosing module details on a saved roof changes the project basis on Continue", async (t) => {
	const app = await mount(t);
	assert.equal(
		button("Place modules on the roof").getAttribute("aria-pressed"),
		"true",
	);
	await click("Use module details");
	await click("Continue with energy use");
	assert.equal(app.next, 1);
	assert.equal(
		app.inputs.pvgis_reference_setup.model,
		"pvgis_5_3_known_ac_reference_v1",
	);
	assert.equal(app.inputs.pvgis_reference_setup.arrays[0].peak_power_kwp, null);
	assert.deepEqual(app.inputs.geometry, flat);
});

test("drawing the first roof replaces the known calculation basis and Undo restores it", async (t) => {
	const app = await mount(t, { brief: emptyBrief() });
	await enter(input("Solar capacity"), "5.5");
	const known = app.inputs.pvgis_reference_setup;
	await openRoof();
	assert.deepEqual(app.inputs.pvgis_reference_setup, known);
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
	assert.equal(
		app.inputs.pvgis_reference_setup.model,
		"pvgis_5_3_roof_ac_reference_v1",
	);
	await click("Undo");
	assert.equal(app.inputs.geometry, undefined);
	assert.deepEqual(app.inputs.pvgis_reference_setup, known);
	assert.equal(input("Solar capacity").value, "5.5");
});

test("selected measured roof properties apply to that roof and Undo restores its previous plane", async (t) => {
	const geometry = structuredClone(flat);
	geometry.sources[0].kind = "user_measurement";
	geometry.sources[0].rights_basis = "user_attestation";
	const app = await mount(t, { brief: emptyBrief(), geometry });
	await openRoof();
	const pitch = input("Selected roof pitch");
	const direction = input("Selected roof azimuth");
	const height = input("Selected roof height");
	assert.equal(pitch.value, "0");
	assert.equal(direction.value, "0");
	assert.equal(height.value, "4");

	async function change(field, value) {
		await enter(field, value);
		await act(async () =>
			field.dispatchEvent(new window.FocusEvent("focusout", { bubbles: true })),
		);
	}
	await change(pitch, "90");
	assert.equal(pitch.getAttribute("aria-invalid"), "true");
	await click("Use this layout");
	assert.equal(input("Selected roof pitch"), pitch);
	await click("Continue with energy use");
	assert.equal(app.next, 0);
	await change(pitch, "30");
	await change(direction, "180");
	await change(height, "6");
	const saved = app.inputs.geometry.roofs[0];
	assert.deepEqual(saved.origin_enu, [10, -20, 6]);
	assert.ok(
		saved.u_axis_enu.every((coordinate, i) => coordinate === [-1, 0, 0][i]),
	);
	assert.ok(Math.abs(saved.v_axis_enu[2] + 0.5) < 1e-12);
	assert.deepEqual(saved.boundary_uv, geometry.roofs[0].boundary_uv);
	assert.deepEqual(app.inputs.geometry.arrays, geometry.arrays);

	await click("Use this layout");
	await click("Open roof layout");
	assert.equal(input("Selected roof height").value, "6");
	await click("Undo");
	assert.equal(input("Selected roof height").value, "4");
	assert.deepEqual(app.inputs.geometry.roofs[0].u_axis_enu, saved.u_axis_enu);
	await change(input("Selected roof pitch"), "90");
	await click("Remove selected");
	assert.equal(app.inputs.geometry.roofs.length, 0);
	await click("Continue with energy use");
	assert.equal(app.next, 1);
});

test("new roof interaction places moves rotates removes and undoes an actual module group", async (t) => {
	const app = await mount(t);
	await openRoof();
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

test("roof studio presents the current layout, editable geometry, modules and summary", async (t) => {
	const geometry = structuredClone(flat);
	geometry.roofs[0].holes_uv = [
		[
			[6, 6],
			[8, 6],
			[8, 8],
			[6, 8],
		],
	];
	const app = await mount(
		t,
		{ brief: emptyBrief(), geometry },
		null,
		null,
		"en",
		{},
		{ initialPlan: true },
	);
	const inspector = document.querySelector(
		'[role="tablist"][aria-label="Roof inspector"]',
	);
	assert.ok(inspector, "the inspector has one set of tabs");
	assert.deepEqual(
		[...inspector.querySelectorAll('[role="tab"]')].map(
			(tab) => tab.textContent,
		),
		["Geometry", "Modules", "Summary"],
	);
	assert.match(
		document.querySelector(".sc-roof-metrics").textContent,
		/396\s*m²/,
	);
	await click("Modules");
	assert.equal(button("Modules").getAttribute("aria-selected"), "true");
	assert.ok(document.querySelector('[role="tabpanel"]:not([hidden]) select'));
	await click("Summary");
	assert.match(
		document.querySelector('[role="tabpanel"]:not([hidden])').textContent,
		/Fixture roof396/,
	);
	assert.deepEqual(app.inputs.geometry, geometry);
});

test("measure the plan without changing the roof, then save and reopen an exclusion", async (t) => {
	const geometry = structuredClone(flat);
	const editing = [];
	const app = await mount(
		t,
		{ brief: emptyBrief(), geometry },
		null,
		null,
		"en",
		{},
		{ initialPlan: true, onEditing: (value) => editing.push(value) },
	);
	const svg = document.querySelector('svg[aria-label="Editable roof plan"]');
	svg.getScreenCTM = () => ({ inverse: () => ({}) });
	svg.createSVGPoint = () => ({
		x: 0,
		y: 0,
		matrixTransform() {
			return this;
		},
	});
	const corner = (x, y) =>
		act(async () =>
			svg.dispatchEvent(
				new window.MouseEvent("click", {
					bubbles: true,
					clientX: x,
					clientY: y,
				}),
			),
		);
	await click("Measure");
	await corner(1, 2);
	await corner(4, 6);
	assert.match(
		document.querySelector(".sc-studio-measurement").textContent,
		/5\s*m/,
	);
	assert.deepEqual(app.inputs.geometry, geometry);
	assert.equal(editing.at(-1), false);
	await click("Keep-out");
	for (const [x, y] of [
		[1, 1],
		[3, 1],
		[3, 3],
		[1, 3],
	])
		await corner(x, y);
	await click("Finish outline");
	assert.deepEqual(app.inputs.geometry.keepouts.at(-1).footprint_uv, [
		[1, 1],
		[3, 1],
		[3, 3],
		[1, 3],
	]);
	assert.equal(
		app.inputs.geometry.keepouts.at(-1).roof_id,
		geometry.roofs[0].id,
	);
	await click("Use this layout");
	await click("Open roof layout");
	assert.ok(document.querySelector(".sc-keepout-shape"));
});

test("the plan offers only the located aerial source and retains the drawn roof when the visitor withdraws", async (t) => {
	const inputs = {
		brief: {
			...emptyBrief(),
			site: {
				...emptyBrief().site,
				country_code: "NL",
				location_label: "Amsterdam",
				latitude: 52.36,
				longitude: 4.88,
			},
		},
		geometry: structuredClone(flat),
	};
	const app = await mount(
		t,
		inputs,
		aerial,
		null,
		"en",
		{ latitude: 52.36, longitude: 4.88 },
		{ initialPlan: true },
	);
	await until(() =>
		[...document.querySelectorAll("button")].some(
			(el) => el.textContent.trim() === "Allow aerial map",
		),
	);
	assert.equal(document.querySelector("[data-map-status]"), null);
	await click("Allow aerial map");
	await until(() =>
		[...document.querySelectorAll("button")].some(
			(el) =>
				el.textContent.trim() === "Hide aerial map" &&
				el.getAttribute("aria-pressed") === "true",
		),
	);
	await click("Hide aerial map");
	assert.equal(button("Show aerial map").getAttribute("aria-pressed"), "false");
	assert.deepEqual(app.inputs.geometry, inputs.geometry);
});

test("a measured roof without a map position can supply coordinates without changing its survey origin", async (t) => {
	const brief = emptyBrief();
	brief.site = {
		...brief.site,
		country_code: "NL",
		location_label: "Amsterdam",
	};
	const inputs = { brief, geometry: structuredClone(flat) };
	const app = await mount(
		t,
		inputs,
		aerial,
		null,
		"en",
		{ latitude: null, longitude: null },
		{ initialPlan: true },
	);
	await until(() => document.querySelector(".sc-studio-location"));
	await click("Enter map coordinates");
	const form = document.querySelector(".sc-studio-location");
	await enter(form.querySelector('input[name="latitude"]'), "52.36");
	await enter(form.querySelector('input[name="longitude"]'), "4.88");
	await until(() =>
		[...document.querySelectorAll("button")].some(
			(el) => el.textContent.trim() === "Allow aerial map",
		),
	);
	assert.equal(app.inputs.geometry.coordinate_system.anchor, null);
	assert.equal(app.inputs.brief.site.latitude, 52.36);
	assert.equal(app.inputs.brief.site.longitude, 4.88);
	assert.equal(document.querySelector("[data-map-status]"), null);
});

test("an installer can locate the project address explicitly and retry a failed lookup with the measured roof intact", async (t) => {
	const brief = emptyBrief();
	brief.site = {
		...brief.site,
		country_code: "NL",
		location_label: "Museumstraat 1, Amsterdam",
	};
	const original = structuredClone(flat);
	const app = await mount(
		t,
		{ brief, geometry: original },
		aerial,
		null,
		"en",
		{},
		{ initialPlan: true, config: { googleMapsApiKey: "fixture" } },
	);
	let searches = 0;
	t.mock.method(globalThis, "fetch", async (url, options) => {
		assert.equal(url, "https://places.googleapis.com/v1/places:searchText");
		assert.equal(
			JSON.parse(options.body).textQuery,
			"Museumstraat 1, Amsterdam",
		);
		searches++;
		if (searches === 1) return new Response(null, { status: 503 });
		return Response.json({
			places: [
				{
					formattedAddress: "Museumstraat 1, 1071 XX Amsterdam",
					location: { latitude: 52.36, longitude: 4.88 },
					addressComponents: [{ types: ["country"], shortText: "NL" }],
				},
			],
		});
	});
	await until(() => document.querySelector(".sc-studio-location"));
	assert.equal(searches, 0);
	await click("Find this address with Google Maps");
	assert.equal(searches, 1);
	assert.ok(
		document.querySelector('.sc-studio-location input[name="latitude"]'),
	);
	assert.equal(app.inputs.brief.site.latitude, null);
	await click("Find this address with Google Maps");
	assert.equal(searches, 2);
	assert.equal(app.inputs.brief.site.longitude, 4.88);
	assert.equal(app.inputs.brief.site.latitude, 52.36);
	assert.deepEqual(app.inputs.geometry, original);
	assert.equal(document.querySelector("[data-map-status]"), null);
});

test("the German roof inspector displays and saves fractional survey heights with decimal commas", async (t) => {
	const geometry = structuredClone(flat);
	geometry.sources[0].kind = "user_measurement";
	geometry.sources[0].rights_basis = "user_attestation";
	geometry.roofs[0].origin_enu[2] = 3.5;
	const app = await mount(
		t,
		{ brief: emptyBrief(), geometry },
		null,
		null,
		"de",
		{},
		{ initialPlan: true },
	);
	const height = document.querySelectorAll(
		".sc-selected-roof-properties input",
	)[2];
	assert.equal(height.value, "3,5");
	await enter(height, "4,25");
	await act(async () =>
		height.dispatchEvent(new window.FocusEvent("focusout", { bubbles: true })),
	);
	assert.equal(app.inputs.geometry.roofs[0].origin_enu[2], 4.25);
	assert.equal(
		document.querySelectorAll(".sc-selected-roof-properties input")[2].value,
		"4,25",
	);
});
