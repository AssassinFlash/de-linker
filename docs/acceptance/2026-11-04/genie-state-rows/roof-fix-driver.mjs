/** Roof-family driver (2026-11-04 second round, corrected harness).
 *
 * The first fix round asserted that a control existed and that a click was
 * delivered; that proves navigation, not the customer's roof. Every state
 * here is read back from what the app shows after the operation:
 *
 * - the workspace is entered through the rail link the customer uses
 *   (`a[href="#lp-design"]`), which works from any workspace;
 * - the location lives in the brief's own fields ("Address or location
 *   reference", Latitude, Longitude) — the roof step has no separate address
 *   search, so the state is verified through those fields and their saved
 *   read-back, never through an invented control;
 * - roof faces, obstacles, pitch/bearing and the boundary ring are read back
 *   from the reopened properties form and from the object tree;
 * - undo/redo are read back from the value they restore;
 * - Save is verified by the revision the app reports and by a reload that
 *   still shows the face and the overview's "Current layout".
 *
 * Multi-touch pinch is not drivable in headless Chromium: the touch row keeps
 * that half as an explicit scope note instead of a pass.
 */
import fs from "node:fs";
import {
	BASE, COMBOS, ROUTES, Recorder, check, consent, evidenceFile, goto,
	newPage, textOf, visible, chromium,
} from "./lib.mjs";

const L = {
	en: {
		newProject: "New project", create: "Create project", save: "Save project",
		addFace: "Add roof face", apply: "Apply properties", cancel: "Cancel properties",
		editProps: "Edit numeric properties", addObstacle: "Add obstacle",
		undo: "Undo", redo: "Redo", roofFaces: "Roof faces",
		address: "Address or location reference",
	},
	de: {
		newProject: "Neues Projekt", create: "Projekt anlegen", save: "Projekt speichern",
		addFace: "Dachfläche hinzufügen", apply: "Eigenschaften übernehmen", cancel: "Eigenschaften abbrechen",
		editProps: "Numerische Eigenschaften bearbeiten", addObstacle: "Hindernis hinzufügen",
		undo: "Rückgängig", redo: "Wiederholen", roofFaces: "Dachflächen",
		address: "Adresse oder Ortsangabe",
	},
};
/** Both locales stay acceptable on labels the planner shell translates late
 * (see D1 in RESULTS.md); the state is read from values, not from the label. */
const BOTH = Object.fromEntries(
	Object.keys(L.en).map((k) => [k, [L.en[k], L.de[k]]])
);
const btn = (page, key) => {
	const names = BOTH[key];
	return page.getByRole("button", { name: new RegExp(`^(${names.map((n) => n.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})$`) }).first();
};
const reEsc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/** Numbers are typed the way this planner parses them: the interface's own
 * decimal separator (comma on de_DE_formal). "0.8" is refused in German with
 * "A valid number is required", and latitude "48.14" would never be stored. */
const num = (lang, value) => String(value).replace(".", lang === "de" ? "," : ".");

/** Move to a project section the way the layout offers it at this width.
 *
 * Desktop has the rail (`a[href="#lp-<section>"]`); the 390 layout replaces the
 * rail with the `lp-mobile-workspace` select ("Project sections"). Clicking the
 * rail at 390 times out because it is not rendered there, which is a layout
 * fact, not a missing workspace. */
async function openSection(page, section) {
	const select = page.locator("select.lp-mobile-workspace").first();
	if (await select.isVisible().catch(() => false)) {
		await select.selectOption(section).catch(() => {});
		await page.waitForTimeout(2200);
		return true;
	}
	const rail = page.locator(`a[href="#lp-${section}"]`).first();
	if ((await rail.count()) === 0) return false;
	await rail.click().catch(() => {});
	await page.waitForTimeout(2200);
	return true;
}

const openDesign = async (page) => {
	await openSection(page, "design");
	return (await page.locator("#lp-design").count()) > 0;
};

async function openFaceForm(page) {
	await btn(page, "addFace").click({ timeout: 15000 }).catch(() => {});
	await page.waitForTimeout(1000);
	return page.locator("form.lp-geometry-form").first();
}

/** Read every named field of the open properties form. */
async function formValues(form) {
	return form
		.locator("[name]")
		.evaluateAll((els) =>
			Object.fromEntries(
				els
					.filter((el) => el.name)
					.map((el) => [el.name, el.type === "checkbox" ? el.checked : el.value])
			)
		)
		.catch(() => ({}));
}

async function fillField(form, name, value) {
	const field = form.locator(`[name="${name}"]`).first();
	if ((await field.count()) === 0) return false;
	await field.fill(String(value)).catch(() => {});
	return true;
}

async function selectObject(page, name) {
	const item = page.locator(".lp-object-tree button").filter({ hasText: name }).first();
	if ((await item.count()) === 0) return false;
	await item.click().catch(() => {});
	await page.waitForTimeout(1200);
	return true;
}

async function openNumericProperties(page) {
	const b = page.getByRole("button", { name: new RegExp(`^(${BOTH.editProps.map(reEsc).join("|")})$`) }).first();
	if ((await b.count()) === 0) return null;
	await b.click().catch(() => {});
	await page.waitForTimeout(1400);
	const form = page.locator("form.lp-geometry-form").first();
	return (await form.count()) ? form : null;
}

async function runCombo(browser, combo) {
	const rec = new Recorder("roof", combo);
	const { context, page } = await newPage(browser, combo);
	const out = {};
	try {
		await goto(page, ROUTES[combo.lang].conf, { wait: 3500 });
		await consent(page);
		await btn(page, "newProject").click({ timeout: 20000 }).catch(() => {});
		await page.waitForTimeout(1000);
		await page.locator(".lp-page input").first().fill(`roof-${combo.lang}-${combo.width}-${Date.now() % 100000}`);
		await btn(page, "create").click({ timeout: 20000 }).catch(() => {});
		await page.waitForTimeout(4000);
		const created = (await page.locator(".lp-project").count()) > 0;
		if (!created) throw new Error("project not created");

		// ---- address-search: the brief's own location fields, saved and read back
		await openSection(page, "site");
		const site = page.locator("#lp-site");
		const addressInput = site.locator('input[autocomplete="off"]').first();
		const addressPresent = (await addressInput.count()) > 0;
		if (addressPresent) {
			await addressInput.fill("Triftstraße 5, 80538 München");
			await addressInput.blur().catch(() => {});
		}
		const siteInputs = site.locator("input");
		const numericCount = await siteInputs.count();
		// Latitude/Longitude are the two decimal inputs in this fieldset.
		const lat = site.locator('input').nth(numericCount - 2);
		const lon = site.locator('input').nth(numericCount - 1);
		const geoSet = numericCount >= 2;
		if (geoSet) {
			await lat.fill(num(combo.lang, "48.140278")).catch(() => {});
			await lon.fill(num(combo.lang, "11.588411")).catch(() => {});
			await lon.blur().catch(() => {});
		}
		await btn(page, "save").click({ timeout: 20000 }).catch(() => {});
		await page.waitForTimeout(4000);
		const savedState = (await textOf(page, ".lp-save-state", 8000)) ?? "";
		const revision1 = Number(savedState.match(/revision\s*(\d+)/i)?.[1] ?? 0);
		await page.reload({ waitUntil: "domcontentloaded" });
		await page.waitForTimeout(4500);
		await consent(page);
		const siteAfter = page.locator("#lp-site");
		if ((await siteAfter.count()) === 0) await openSection(page, "site");
		const addressAfter = await siteAfter.locator('input[autocomplete="off"]').first().inputValue().catch(() => "");
		const latAfter = await siteAfter.locator("input").nth(numericCount - 2).inputValue().catch(() => "");
		const lonAfter = await siteAfter.locator("input").nth(numericCount - 1).inputValue().catch(() => "");
		await rec.record("address-search", [
			check("the brief carries the location fields (address, latitude, longitude)",
				addressPresent && geoSet, `address field=${addressPresent}, numeric fields=${numericCount}`),
			check("address and coordinates are accepted", addressPresent ? addressAfter.includes("München") : false,
				`address read-back=${JSON.stringify(addressAfter.slice(0, 40))}`),
			check("coordinates are saved and read back after a reload",
				latAfter.replace(",", ".").startsWith("48.14") && lonAfter.replace(",", ".").startsWith("11.58"),
				`latitude=${latAfter}, longitude=${lonAfter}`),
		], page, "the roof step has no separate address search: the location is the brief's own address + latitude/longitude, verified by saving and re-reading after a reload");

		// ---- initial-map: the design workspace and its plan surface
		const entered = await openDesign(page);
		const planSwitch = page.getByRole("button", { name: /^(Plan|Draufsicht|Map|Karte|3D)$/ });
		const viewCount = await planSwitch.count();
		const quantities = (await textOf(page, "#lp-design", 6000)) ?? "";
		const facesEmpty = /Roof faces\s*\n?\s*0|Dachflächen\s*\n?\s*0/.test(quantities);
		await rec.record("initial-map", [
			check("design workspace reached through the rail link", entered),
			check("plan/map/3D view switch rendered", viewCount >= 2, `${viewCount} view controls`),
			check("the empty design states its own state (0 roof faces)", facesEmpty,
				quantities.replace(/\n+/g, " · ").slice(0, 120)),
		], page, "a fresh project's design workspace; the map tab's tiles come from an external origin and are recorded as an environment fact");

		// ---- outline-draw: a measured roof face through the real form
		let form = await openFaceForm(page);
		const formOpen = (await form.count()) > 0;
		const faceFormFields = formOpen ? await formValues(form) : {};
		if (formOpen) {
			await fillField(form, "name", "North roof");
			await fillField(form, "width", num(combo.lang, 10));
			await fillField(form, "length", num(combo.lang, 8));
			await fillField(form, "pitch", num(combo.lang, 30));
			await fillField(form, "bearing", num(combo.lang, 180));
			await fillField(form, "east", "0");
			await fillField(form, "north", "0");
			await fillField(form, "up", "0");
			await fillField(form, "source", "Measured on site");
			await fillField(form, "rights_note", "Own site measurements");
			await form.locator('[name="rights"]').check({ force: true }).catch(() => {});
			await btn(page, "apply").click({ timeout: 15000 }).catch(() => {});
			await page.waitForTimeout(2500);
		}
		const formStillOpen = (await page.locator("form.lp-geometry-form").count()) > 0;
		const blocked = formStillOpen
			? await form
					.locator("[required]")
					.evaluateAll((els) =>
						els
							.filter((el) =>
								el.type === "checkbox" ? !el.checked : !String(el.value ?? "").trim()
							)
							.map((el) => el.name || el.type)
					)
					.catch(() => [])
			: [];
		const designText = (await textOf(page, "#lp-design", 8000)) ?? "";
		const treeItems = await page.locator(".lp-object-tree button").allInnerTexts().catch(() => []);
		const faceDrawn = treeItems.some((t) => t.includes("North roof")) && /Roof faces\s*\n?\s*1|Dachflächen\s*\n?\s*1/.test(designText);
		await rec.record("outline-draw", [
			check("the measured-roof-face form opens with its fields",
				formOpen && Object.keys(faceFormFields).length >= 8,
				`form open=${formOpen} · fields=${JSON.stringify(Object.keys(faceFormFields))}`),
			check("applying the form adds the face to the design", faceDrawn,
				`object tree=${JSON.stringify(treeItems.slice(0, 4))}${formStillOpen ? ` · form still open, empty required fields=${JSON.stringify(blocked)}` : ""}`),
		], page, "the real measured-roof form (name, width, length, pitch, bearing, origin, source, permissions) rather than canvas click points");

		// ---- orientation-pitch: read the face's own values back
		await selectObject(page, "North roof");
		let props = await openNumericProperties(page);
		const propsValues = props ? await formValues(props) : {};
		const pitchRead = String(propsValues.pitch ?? "");
		const bearingRead = String(propsValues.bearing ?? "");
		if (props) {
			await fillField(props, "pitch", num(combo.lang, 45));
			await btn(page, "apply").click({ timeout: 15000 }).catch(() => {});
			await page.waitForTimeout(2000);
			await selectObject(page, "North roof");
			props = await openNumericProperties(page);
		}
		const pitchAfter = props ? String((await formValues(props)).pitch ?? "") : "";
		await rec.record("orientation-pitch", [
			check("pitch and bearing are stored on the face", pitchRead === "30" && bearingRead === "180",
				`pitch=${pitchRead}, bearing=${bearingRead}`),
			check("a new pitch (45) is accepted and read back", pitchAfter.replace(",", ".").startsWith("45"), `pitch=${pitchAfter}`),
		], page, "pitch/bearing read from the face's reopened numeric properties, not from a label's presence");

		// ---- validation-error: an out-of-range pitch is refused, value not stored
		let invalidSeen = false;
		let invalidValue = "";
		if (props) {
			await fillField(props, "pitch", num(combo.lang, 999));
			await btn(page, "apply").click({ timeout: 15000 }).catch(() => {});
			await page.waitForTimeout(1500);
			invalidSeen =
				(await props.locator('[aria-invalid="true"]').count()) > 0 ||
				(await props.locator("[role=alert], .lp-notice, [class*=notice]").count()) > 0;
			invalidValue = String((await formValues(props)).pitch ?? "");
			await btn(page, "cancel").click().catch(() => {});
			await page.waitForTimeout(1000);
		}
		await rec.record("validation-error", [
			check("pitch 999 is refused with a visible validation state", invalidSeen, `form open=${!!props}`),
			check("the refused value is kept in the field for correction", invalidValue === num(combo.lang, 999), `field still shows ${invalidValue}`),
		], page, "the stated bounds (0 ≤ pitch < 90) are enforced on submit; the form keeps the refused value for correction");

		// ---- edit-vertices: the boundary ring is the vertex editing surface
		await selectObject(page, "North roof");
		props = await openNumericProperties(page);
		const boundaryBefore = props ? String((await formValues(props)).boundary ?? "") : "";
		let boundaryAfter = "";
		if (props) {
			// The ring is written in the interface's own decimal format, so the
			// edit is made on its own text: the vertex that reads 10 ; 8 becomes
			// 12 ; 8, which is one moved corner of the same quadrilateral.
			const edited = boundaryBefore.replace(
				new RegExp(`(^|\\n)\\s*10(\\s*;\\s*)8`, "m"),
				`$1 12$28`
			);
			await fillField(props, "boundary", edited);
			await btn(page, "apply").click({ timeout: 15000 }).catch(() => {});
			await page.waitForTimeout(2000);
			await selectObject(page, "North roof");
			props = await openNumericProperties(page);
			boundaryAfter = props ? String((await formValues(props)).boundary ?? "") : "";
		}
		await rec.record("edit-vertices", [
			check("the face exposes its boundary ring for editing", boundaryBefore.length > 0,
				JSON.stringify(boundaryBefore.slice(0, 60))),
			check("a moved vertex is stored and read back",
				new RegExp(`(^|\\n)\\s*12(\\s*;\\s*)8`, "m").test(boundaryAfter),
				JSON.stringify(boundaryAfter.slice(0, 60))),
		], page, "roof vertices are edited through the face's boundary ring (the plan canvas moves arrays, not roof vertices)");

		// ---- obstacles
		if (props) {
			await btn(page, "cancel").click().catch(() => {});
			await page.waitForTimeout(800);
		}
		await btn(page, "addObstacle").click({ timeout: 15000 }).catch(() => {});
		await page.waitForTimeout(1200);
		const obstacleForm = page.locator("form.lp-geometry-form").first();
		const obstacleOpen = (await obstacleForm.count()) > 0;
		if (obstacleOpen) {
			await fillField(obstacleForm, "name", "Chimney");
			await fillField(obstacleForm, "u", num(combo.lang, 3));
			await fillField(obstacleForm, "v", num(combo.lang, 3));
			await fillField(obstacleForm, "width", num(combo.lang, 1));
			await fillField(obstacleForm, "length", num(combo.lang, 1));
			await fillField(obstacleForm, "height", num(combo.lang, 0.8));
			await obstacleForm.locator('select[name="axis"]').selectOption("normal").catch(() => {});
			await btn(page, "apply").click({ timeout: 15000 }).catch(() => {});
			await page.waitForTimeout(2000);
		}
		const obstacleStillOpen = (await page.locator("form.lp-geometry-form").count()) > 0;
		const obstacleBlocked = obstacleStillOpen
			? await page
					.locator("form.lp-geometry-form [required]")
					.evaluateAll((els) =>
						els
							.filter((el) =>
								el.type === "checkbox" ? !el.checked : !String(el.value ?? "").trim()
							)
							.map((el) => el.name || el.type)
					)
					.catch(() => [])
			: [];
		const treeAfterObstacle = await page.locator(".lp-object-tree button").allInnerTexts().catch(() => []);
		await rec.record("obstacles", [
			check("the obstacle form opens inside the face", obstacleOpen),
			check("the obstacle is added under its roof face",
				treeAfterObstacle.some((t) => t.includes("Chimney")),
				`object tree=${JSON.stringify(treeAfterObstacle.slice(0, 6))}${obstacleStillOpen ? ` · form still open, empty required fields=${JSON.stringify(obstacleBlocked)}` : ""}`),
		], page, "a real obstacle (footprint + height) added through its own form and read back from the object tree");

		// ---- undo / redo: read back the value they restore
		const undo = page.locator('button[aria-label="Undo"], button[aria-label="Rückgängig"]').first();
		const redo = page.locator('button[aria-label="Redo"], button[aria-label="Wiederholen"]').first();
		const undoAvailable = (await undo.count()) > 0 && !(await undo.isDisabled().catch(() => true));
		const treeBeforeUndo = await page.locator(".lp-object-tree button").allInnerTexts().catch(() => []);
		if (undoAvailable) {
			await undo.click().catch(() => {});
			await page.waitForTimeout(1500);
		}
		const treeAfterUndo = await page.locator(".lp-object-tree button").allInnerTexts().catch(() => []);
		const redoAvailable = (await redo.count()) > 0 && !(await redo.isDisabled().catch(() => true));
		if (redoAvailable) {
			await redo.click().catch(() => {});
			await page.waitForTimeout(1500);
		}
		const treeAfterRedo = await page.locator(".lp-object-tree button").allInnerTexts().catch(() => []);
		await rec.record("undo-redo", [
			check("undo is offered after an edit", undoAvailable),
			check("undo removed the obstacle from the design",
				treeBeforeUndo.some((t) => t.includes("Chimney")) && !treeAfterUndo.some((t) => t.includes("Chimney")),
				`before=${JSON.stringify(treeBeforeUndo.slice(0, 5))} after=${JSON.stringify(treeAfterUndo.slice(0, 5))}`),
			check("redo put it back", redoAvailable && treeAfterRedo.some((t) => t.includes("Chimney")),
				`after redo=${JSON.stringify(treeAfterRedo.slice(0, 5))}`),
		], page, "the project editor's own history buttons, verified by the object tree they restore");

		// ---- save-return-to-configurator: revision, reload, overview
		const saveBtn = btn(page, "save");
		await saveBtn.click({ timeout: 20000 }).catch(() => {});
		await page.waitForTimeout(4500);
		const stateAfterSave = (await textOf(page, ".lp-save-state", 8000)) ?? "";
		const revision2 = Number(stateAfterSave.match(/revision\s*(\d+)/i)?.[1] ?? 0);
		await openSection(page, "overview");
		await page.waitForTimeout(1500);
		const overview = (await textOf(page, ".lp-overview-work", 8000)) ?? "";
		await page.reload({ waitUntil: "domcontentloaded" });
		await page.waitForTimeout(5000);
		await consent(page);
		await openDesign(page);
		const afterReload = (await textOf(page, "#lp-design", 8000)) ?? "";
		await rec.record("save-return-to-configurator", [
			check("save records a new revision", revision2 > revision1, `${JSON.stringify(stateAfterSave)} (before=${revision1})`),
			check("the overview shows the saved roof as the current layout",
				/Current layout|Aktuelle Dachfläche|Aktuelles Layout/i.test(overview) && /North roof/.test(overview),
				overview.replace(/\n+/g, " · ").slice(0, 100)),
			check("the face and the obstacle survive a reload", /North roof/.test(afterReload) && /Chimney/.test(afterReload),
				`roof=${/North roof/.test(afterReload)} obstacle=${/Chimney/.test(afterReload)}`),
		], page, "revision from the app's own save state, the overview's current-layout block, and a reload read-back — not a click");

		// ---- permission-error: no location permission is required
		const permScript = await page
			.evaluate(() => navigator.permissions?.query?.({ name: "geolocation" }).then((s) => s.state).catch(() => "unavailable"))
			.catch(() => "unavailable");
		const designStillUsable = (await page.locator("#lp-design").count()) > 0;
		await rec.record("permission-error", [
			check("geolocation permission is not granted (denied/default)", permScript !== "granted", `state=${permScript}`),
			check("the design workspace works without any location permission", designStillUsable),
		], page, "the roof path runs from the brief's coordinates; no permission gate is on it");

		// ---- mobile-gestures: the touch branch, with its real limit recorded
		if (combo.width === 390) {
			const canvas = page.locator("#lp-design canvas, #lp-design svg").first();
			const visibleCanvas = (await canvas.count()) > 0;
			let tapOk = false;
			if (visibleCanvas) {
				const box = await canvas.boundingBox().catch(() => null);
				if (box) {
					await page.touchscreen.tap(box.x + box.width / 2, box.y + box.height / 2).catch(() => {});
					await page.waitForTimeout(1200);
					tapOk = (await page.locator("#lp-design").count()) > 0;
				}
			}
			await rec.record("mobile-gestures", [
				check("the design surface renders at 390 with touch input", visibleCanvas && tapOk),
				check(
					"multi-touch pinch/rotate has no headless synthesis",
					false,
					"not exercised: Chromium's headless CDP cannot produce a two-finger gesture, so the pinch/rotate half of this state has no browser evidence",
					{
						scope:
							"pinch/rotate cannot be synthesized in headless Chromium; the tap path above is the covered half, and the gesture half stays open",
					}
				),
			], page, "390 touch branch; the pinch half is recorded as an open scope, not as a pass");
		} else {
			await rec.record("mobile-gestures", [
				check("desktop combo: the touch branch is covered by the 390 twins", true),
			], null, "recorded from the 390 combos of this state");
		}
	} catch (e) {
		console.log("combo error (contained):", combo, String(e?.message || e).slice(0, 250));
		rec.rows.push({ key: `roof:fixdriver:${combo.lang}:${combo.width}`, error: String(e?.message || e).slice(0, 350) });
	} finally {
		if (page.__netfail?.length) rec.rows.push({ key: `roof:netfail:${combo.lang}:${combo.width}`, netfail: page.__netfail.slice(0, 8) });
		await context.close().catch(() => {});
	}
	return rec;
}

// This host is under memory pressure (free pages in the low hundreds of MB,
// swap mostly used), and Chromium gets reclaimed mid-run when several pages
// and a hero cinematic are alive at once. One browser, one argument set, and
// a fresh page per phase keep the run inside that budget.
const browser = await chromium.launch({
	args: ["--disable-gpu", "--disable-dev-shm-usage", "--renderer-process-limit=1"],
});
const all = [];
for (const combo of COMBOS) all.push(await runCombo(browser, combo));
await browser.close();
const rows = all.flatMap((r) => r.rows);
fs.writeFileSync(await evidenceFile("roof-family"), JSON.stringify({
	driver: "roof", fixRound: 3, base: BASE, observedAt: new Date().toISOString(),
	rows,
	modelBudget: "none: deterministic planner behaviour against the real local engine",
}, null, 1));
console.log("roof fix driver done:", rows.length, "records,", rows.filter((r) => r.status === "fail").length, "failed");
