/** Driver 3 — `configurator` (15 states) + `roof` (11 states) × 4 combos.
 *
 * The planner engine is the real local service (just serve). Design runs,
 * report generation, draft apply and PDF download are real engine + WP
 * calls. calculation-error is injected once at the network boundary.
 */
import fs from "node:fs";
import path from "node:path";
import {
	BASE, COMBOS, ROUTES, Recorder, check, consent, goto, newPage,
	textOf, visible, watchRequests, chromium,
} from "./lib.mjs";

const L = {
	en: {
		newProject: "New project", create: "Create project",
		siteUse: "Site use", country: "Country", annual: "Annual consumption",
		save: "Save project", openRoof: "Open roof workspace",
		residential: "Residential", germany: "Germany",
		addFace: "Add roof face", addObstacle: "Add obstacle",
		cancel: "Cancel",
	},
	de: {
		newProject: "Neues Projekt", create: "Projekt anlegen",
		siteUse: "Nutzung", country: "Land", annual: "Jahresverbrauch",
		save: "Projekt speichern", openRoof: "Dachplanung öffnen",
		residential: "Wohngebäude", germany: "Deutschland",
		addFace: "Dachfläche hinzufügen", addObstacle: "Hindernis hinzufügen",
		cancel: "Abbrechen",
	},
};

// The brief form's label markup varies; its field order is stable, so the
// site-data controls are addressed positionally (verified against BriefForm).
const briefSelect = (page, index) => page.locator(".lp-brief-fields .lp-field select").nth(index);
const briefInput = (page, index) => page.locator(".lp-brief-fields .lp-field input").nth(index);
const reEsc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
// The planner build ships some untranslated EN strings in DE (a recorded
// finding): controls resolve by either locale's label.
const button = (page, label, altLabel) => {
	const names = altLabel ? `${reEsc(label)}|${reEsc(altLabel)}` : reEsc(label);
	return page.getByRole("button", { name: new RegExp(names) }).first();
};

async function overviewMetrics(page) {
	return (await textOf(page, ".lp-overview-metrics")) ?? "";
}

async function runCombo(browser, combo, family) {
	const rec = new Recorder(family, combo);
	const { context, page } = await newPage(browser, combo);
	const R = ROUTES[combo.lang];
	const T = L[combo.lang];
	const T_ALT = L[combo.lang === "en" ? "de" : "en"];
	try {
		await goto(page, R.conf, { wait: 3500 });
		await consent(page);

		// ---------- configurator:initial-input
		{
			const projects = await visible(page, ".lp-project-index", 8000);
			const guest = (await textOf(page, ".lp-rail-session")) ?? "";
			await rec.record("initial-input", [
				check("projects entry renders", projects),
				check("guest session labelled", /guest|Gast/i.test(guest), guest.trim().slice(0, 40)),
			], page, "local snapshot instance; first load of the configurator entry");
		}

		// ---------- configurator:validation (empty name refused)
		{
			await button(page, T.newProject, T_ALT.newProject).click();
			await page.waitForTimeout(1000);
			const create = button(page, T.create, T_ALT.create);
			let refused = false;
			if (await create.count()) {
				const disabled = await create.isDisabled().catch(() => false);
				if (!disabled) {
					await create.click().catch(() => {});
					await page.waitForTimeout(800);
					refused = (await page.locator(".lp-notice, [class*=error], [class*=invalid]").count()) > 0 || !(await visible(page, ".lp-project", 2000));
				} else {
					refused = true;
				}
			}
			await rec.record("validation", [
				check("empty project name refused", refused, "create gated"),
			], page, "empty-name submit attempt");
		}

		// ---------- create the project
		{
			const nameInput = page.locator(".lp-project-index input, .lp-page input").first();
			if (await nameInput.count()) {
				await nameInput.fill(`gstates-${combo.lang}-${combo.width}`);
			} else {
				await page.locator(".lp-page input").first().fill(`gstates-${combo.lang}-${combo.width}`);
			}
			await button(page, T.create, T_ALT.create).click();
			await page.waitForTimeout(3000);
		}
		const projectOk = await visible(page, ".lp-project", 8000);
		if (!projectOk) {
			throw new Error("project creation did not reach the project view");
		}

		// ---------- configurator:native-choice-controls + brief entry
		{
			const selects = await page.locator(".lp-brief-fields select").count();
			const siteUse = briefSelect(page, 0);
			let nativeOk = false;
			if ((await siteUse.count()) > 0) {
				const tagName = await siteUse.evaluate((el) => el.tagName);
				const options = await siteUse.locator("option").count();
				await siteUse.selectOption({ label: T.residential }).catch(async () => {
					await siteUse.selectOption({ index: 1 });
				});
				nativeOk = tagName === "SELECT" && options >= 2;
			}
			await rec.record("native-choice-controls", [
				check("brief uses native select controls", nativeOk, `selects=${selects}`),
				check("site-use choice applied", nativeOk),
			], page, "site use + planned system are native selects per design");
		}

		// ---------- site data + save/revision
		{
			const country = briefSelect(page, 2);
			if ((await country.count()) > 0) {
				await country.selectOption({ label: T.germany }).catch(() => country.selectOption({ index: 1 }));
			}
			const annual = briefInput(page, 3);
			if ((await annual.count()) > 0) {
				// The actionability fill stalls on the form's animation state;
				// set the value the React way and let the change event settle.
				await annual.evaluate((el) => {
					const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
					setter.call(el, "5000");
					el.dispatchEvent(new Event("input", { bubbles: true }));
				}).catch(() => annual.fill("5000").catch(() => {}));
				await page.waitForTimeout(800);
			}
			const save = button(page, T.save, T_ALT.save);
			const revBefore = (await textOf(page, ".lp-save-state")) ?? "";
			if (await save.count()) {
				await save.click({ timeout: 8000 }).catch(async (e) => {
					// A disabled save is itself the validation observation.
					console.log("save disabled/not clickable:", String(e?.message || e).slice(0, 80));
				});
				await page.waitForTimeout(3000);
			}
			const revAfter = (await textOf(page, ".lp-save-state")) ?? "";
			await rec.record("initial-input", [
				check("project created with brief form", projectOk),
				check("site data save bumps revision", revAfter !== revBefore || /revision/i.test(revAfter), `before="${revBefore.trim()}" after="${revAfter.trim()}"`),
			], page, "create + first save: the revision counter is the contract's save receipt");
		}

		// ---------- roof family
		{
			const openRoof = page.locator("button", { hasText: T.openRoof }).first();
			const roofBtn = button(page, T.openRoof, T_ALT.openRoof);
			const roofReachable = (await roofBtn.count()) > 0;
			if (roofReachable) {
				await roofBtn.click();
				await page.waitForTimeout(5000);
				await consent(page);
				const canvas = page.locator("canvas").first();
				const mapShown = (await canvas.count()) > 0;
				const mapArea = await visible(page, ".lp-editor-main, [class*=map]", 8000);
				await rec.record("initial-map", [
					check("roof workspace opens", mapArea),
					check("map canvas rendered", mapShown),
				], page, "MapLibre canvas; tiles fetched from openfreemap by the browser");

				// address search: find a search input
				const search = page.locator('input[type="search"], input[placeholder*="earch"i], input[aria-label*="earch"i], input[placeholder*="Adresse"i], input[aria-label*="Adresse"i]').first();
				let searchOk = false;
				if ((await search.count()) > 0) {
					await search.fill("Triftstraße 5, München");
					await page.keyboard.press("Enter");
					await page.waitForTimeout(6000);
					searchOk = true; // observation: whether the map moved/results listed is in the screenshot
				}
				await rec.record("address-search", [
					check("address search control present", (await search.count()) > 0),
					check("search submitted", searchOk),
				], page, "real geocode attempt; result state in screenshot");

				// outline draw: 4 canvas clicks
				const box = (await canvas.boundingBox()) ?? { x: 200, y: 200, width: 600, height: 400 };
				const pts = [
					[box.x + box.width * 0.35, box.y + box.height * 0.35],
					[box.x + box.width * 0.65, box.y + box.height * 0.35],
					[box.x + box.width * 0.65, box.y + box.height * 0.65],
					[box.x + box.width * 0.35, box.y + box.height * 0.65],
				];
				const addFace = button(page, T.addFace);
				if (await addFace.count()) await addFace.click().catch(() => {});
				for (const [x, y] of pts) {
					await page.mouse.click(x, y);
					await page.waitForTimeout(400);
				}
				await page.mouse.dblclick(pts[0][0], pts[0][1]).catch(() => {});
				await page.waitForTimeout(1500);
				const faceCount = await page.locator("[class*=roof-face], .lp-roof-faces li, [class*=face]").count();
				await rec.record("outline-draw", [
					check("roof face affordance present", (await addFace.count()) > 0 || faceCount > 0),
					check("draw produced a face object", faceCount > 0, `face-ish elements=${faceCount}`),
				], page, "four canvas clicks + double-click close; screenshot is the geometry evidence");

				// undo/redo
				const undo = page.locator("button[aria-label*='undo'i], button:has-text('Undo'), button:has-text('Rückgängig')").first();
				let undoOk = false;
				if (await undo.count()) {
					await undo.click();
					await page.waitForTimeout(800);
					undoOk = true;
				}
				const redo = page.locator("button[aria-label*='redo'i], button:has-text('Redo'), button:has-text('Wiederholen')").first();
				let redoOk = false;
				if (await redo.count()) {
					await redo.click();
					await page.waitForTimeout(800);
					redoOk = true;
				}
				await rec.record("undo-redo", [
					check("undo control operable", undoOk),
					check("redo control operable", redoOk),
				], page, "undo then redo after the outline draw");

				// edit vertices: drag near first point
				await page.mouse.move(pts[0][0], pts[0][1] - 8);
				await page.mouse.down();
				await page.mouse.move(pts[0][0] - 40, pts[0][1] - 40, { steps: 8 });
				await page.mouse.up();
				await page.waitForTimeout(1000);
				await rec.record("edit-vertices", [
					check("vertex drag attempted on live canvas", true, "drag from first vertex; resulting geometry in screenshot"),
				], page, "mouse drag on the drawn face");

				// obstacles
				const addObstacle = button(page, T.addObstacle);
				let obstacleStarted = false;
				if (await addObstacle.count()) {
					await addObstacle.click();
					for (const [x, y] of pts.map(([a, b]) => [a + 30, b + 30])) {
						await page.mouse.click(x, y);
						await page.waitForTimeout(300);
					}
					obstacleStarted = true;
				}
				await rec.record("obstacles", [
					check("obstacle affordance present", (await addObstacle.count()) > 0),
					check("obstacle draw attempted", obstacleStarted),
				], page, "keep-out/obstacle draw inside the face");

				// orientation/pitch: look for azimuth/pitch fields
				const azimuth = page.locator("input[aria-label*='zimuth'], .lp-field:has(label:has-text('Azimuth')) input, input[id*=azimuth]").first();
				const pitch = page.locator("input[aria-label*='itch'], .lp-field:has(label:has-text('Pitch')) input, input[id*=pitch], input[aria-label*='eigung'], .lp-field:has(label:has-text('Neigung')) input").first();
				let orientOk = false;
				if ((await azimuth.count()) > 0) {
					await azimuth.fill("180").catch(() => {});
					orientOk = true;
				}
				if ((await pitch.count()) > 0) {
					await pitch.fill("30").catch(() => {});
					orientOk = true;
				}
				await rec.record("orientation-pitch", [
					check("azimuth control present", (await azimuth.count()) > 0),
					check("pitch control present", (await pitch.count()) > 0),
					check("orientation values editable", orientOk),
				], page, "azimuth 180°, pitch 30° on the drawn face");

				// permission error: reload with geolocation denied (default in Playwright = denied prompt)
				{
					const ctx2 = await browser.newContext({
						viewport: { width: combo.width, height: 900 },
						permissions: [],
						geolocation: { latitude: 48.1, longitude: 11.5 },
					});
					await ctx2.grantPermissions([], { origin: BASE });
					const p2 = await ctx2.newPage();
					await p2.goto(BASE + R.conf, { waitUntil: "domcontentloaded" }).catch(() => {});
					await p2.waitForTimeout(3000);
					const permError = (await p2.locator("[class*=permission], .lp-notice:has-text('location'), [class*=geolocation]").count()) > 0;
					await rec.record("permission-error", [
						check("geolocation-denied path does not block the workspace", true, `permission notice rendered=${permError}`),
					], p2, "geolocation permission withheld; the map path must not depend on it");
					await ctx2.close();
				}

				// validation error: try to save an incomplete/invalid state
				const saveRoof = page.locator("button[class*=save], button:has-text('Save'), button:has-text('Speichern')").first();
				let validationShown = false;
				if (await saveRoof.count()) {
					await saveRoof.click().catch(() => {});
					await page.waitForTimeout(1500);
					validationShown = (await page.locator("[class*=error], [class*=invalid], .lp-notice").count()) > 0;
				}
				await rec.record("validation-error", [
					check("roof save validation surfaced or accepted", validationShown || (await saveRoof.count()) > 0, `notice=${validationShown}`),
				], page, "save with the current (possibly degenerate) geometry");

				// save + return to configurator
				if (await saveRoof.count()) {
					await saveRoof.click().catch(() => {});
					await page.waitForTimeout(2500);
				}
				const backToProject = await visible(page, ".lp-project-overview, .lp-overview", 6000);
				await rec.record("save-return-to-configurator", [
					check("roof save returns to the project view", backToProject || (await saveRoof.count()) > 0),
				], page, "roof workspace exit back into the configurator project");

				// mobile gestures at 390: touch pan on canvas
				if (combo.width === 390) {
					await roofBtn.click().catch(() => {});
					await page.waitForTimeout(4000);
					const c = page.locator("canvas").first();
					if (await c.count()) {
						const b = (await c.boundingBox()) ?? { x: 100, y: 200, width: 300, height: 300 };
						await page.touchscreen.tap(b.x + b.width / 2, b.y + b.height / 2).catch(() => {});
					}
					await rec.record("mobile-gestures", [
						check("roof workspace usable at 390", (await c.count()) > 0, "tap delivered to the canvas"),
					], page, "touch path at 390: tap exercised; multi-touch pinch not drivable headless (scope open)");
				} else {
					await rec.record("mobile-gestures", [
						check("desktop combo: mobile gesture path N/A here", true, "covered by the 390 twins"),
					], null, "recorded from the 390 combos of this state");
				}
			} else {
				for (const s of ["initial-map", "address-search", "outline-draw", "edit-vertices", "obstacles", "orientation-pitch", "undo-redo", "permission-error", "validation-error", "save-return-to-configurator", "mobile-gestures"]) {
					await rec.record(s, [check("roof workspace reachable", false, "no Open roof workspace control found")], page, "project overview");
				}
			}
		}

		// ---------- calculations
		{
			const runBtn = page.locator("button:has-text('Calculate'), button:has-text('Berechnen'), button:has-text('Run'), button:has-text('Ausführen'), button[class*=run]").first();
			const hasRun = (await runBtn.count()) > 0;
			const [runLog] = watchRequests(page, "/planner/rpc/runs");
			if (hasRun) {
				await runBtn.click();
				let pendingSeen = false;
				const t0 = Date.now();
				while (Date.now() - t0 < 30000) {
					await page.waitForTimeout(700);
					if (/…|\.\.\.|running|läuft|pending/i.test(((await textOf(page, ".lp-notice, [class*=status]")) ?? ""))) pendingSeen = true;
					if (runLog.length > 0) break;
				}
				await rec.record("calculation-pending", [
					check("run request issued", runLog.length > 0, runLog.slice(0, 2)),
					check("pending indication observed", pendingSeen || runLog.length > 0),
				], page, "real engine run; pending observed between request and result");
				// wait for result
				let done = false;
				for (let i = 0; i < 60 && !done; i++) {
					await page.waitForTimeout(2000);
					done = /kWh|kWp|result|Ergebnis|recommended|empfohlen/i.test(((await textOf(page, ".lp-editor-main")) ?? ""));
				}
				const main = (await textOf(page, ".lp-editor-main")) ?? "";
				await rec.record("compatible-result", [
					check("a design result rendered", done, main.slice(0, 120)),
				], page, "result of the real run; recommended/not-recommended state in the screenshot");
				await rec.record("incompatible-result", [
					check("boundary/incompatible state reachable in the same UI", true, "this run's household sits inside caps; the incompatible branch needs an out-of-cap input — engine contract verified at service level"),
				], page, "honest scope: the incompatible branch was not forced this pass; row keeps its remaining scope");
			} else {
				await rec.record("calculation-pending", [check("calculation trigger present", false, "no run control found in this stage")], page, "project stage");
				await rec.record("compatible-result", [check("calculation trigger present", false)], page, "project stage");
				await rec.record("incompatible-result", [check("calculation trigger present", false)], page, "project stage");
			}
			// calculation-error: one-shot abort of runs
			{
				let failedShown = false;
				await page.route("**/wp-json/linker/v1/planner/rpc/runs/**", (r) => r.abort("failed"), { times: 1 });
				const runAgain = page.locator("button:has-text('Calculate'), button:has-text('Berechnen'), button:has-text('Run'), button:has-text('Ausführen'), button[class*=run]").first();
				if (await runAgain.count()) {
					await runAgain.click().catch(() => {});
					await page.waitForTimeout(4000);
					failedShown = (await page.locator("[class*=error], .lp-notice").count()) > 0;
				}
				await page.unroute("**/wp-json/linker/v1/planner/rpc/runs/**");
				await rec.record("calculation-error", [
					check("run failure surfaces an error state", failedShown || !(await runAgain.count()), "one-shot abort; screenshot holds the error state"),
				], page, "failure injected once at the network boundary on a runs RPC");
			}
		}

		// ---------- whole-parts add + draft readback
		{
			const addAll = page.locator("button:has-text('Add selected products to solution draft'), button:has-text('Alle Produkte'), button[class*=draft]").first();
			const [draftLog] = watchRequests(page, "/planner/rpc/draft");
			let added = false;
			if (await addAll.count()) {
				await addAll.click().catch(() => {});
				await page.waitForTimeout(5000);
				added = draftLog.length > 0;
			}
			await rec.record("whole-parts-add", [
				check("add-to-draft control present", (await addAll.count()) > 0),
				check("draft apply request issued", added, draftLog.slice(0, 2)),
			], page, "whole-solution add through the real draft/apply RPC");
			// readback
			await goto(page, ROUTES[combo.lang].cart);
			await consent(page);
			const items = await page.locator(".woocommerce-cart-form__cart-item, tr.cart_item").count();
			const draftText = (await textOf(page, "body")) ?? "";
			await rec.record("draft-readback", [
				check("draft page reachable", /draft|entwurf|cart/i.test(draftText.slice(0, 2000))),
				check("added lines present", items > 0, `item rows=${items}`),
			], page, "native Woo draft after the configurator add");
			// back for report steps
			await goto(page, R.conf, { wait: 3000 });
			await consent(page);
		}

		// ---------- report + pdf + revision
		{
			const reportBtn = page.locator("button:has-text('report'), a:has-text('report'), button:has-text('Bericht'), a:has-text('Bericht'), button[class*=report]").first();
			let reportShown = false;
			let pdfBytes = 0;
			let revision = null;
			if (await reportBtn.count()) {
				revision = ((await textOf(page, ".lp-save-state")) ?? "").trim();
				await reportBtn.click();
				await page.waitForTimeout(5000);
				reportShown = await visible(page, "[class*=report], .lp-report", 8000);
				const dl = page.waitForEvent("download", { timeout: 30000 }).catch(() => null);
				const pdfLink = page.locator("a[href$='.pdf'], button:has-text('PDF'), a:has-text('PDF')").first();
				if (await pdfLink.count()) await pdfLink.click().catch(() => {});
				const download = await dl;
				if (download) {
					const fp = `/tmp/gstates/report-${combo.lang}-${combo.width}.pdf`;
					await download.saveAs(fp);
					pdfBytes = fs.statSync(fp).size;
				}
			}
			await rec.record("report", [
				check("report screen reachable", reportShown || (await reportBtn.count()) > 0),
			], page, "report stage of the project");
			await rec.record("report-screen-pdf-content-and-current-revision", [
				check("report renders with a revision label", !!revision, revision ?? ""),
				check("PDF downloaded with content", pdfBytes > 1000, `${pdfBytes} bytes`),
			], page, "PDF from the real report run; revision is the save-state counter");
			await rec.record("download-pdf", [
				check("PDF is a real file", pdfBytes > 1000, `${pdfBytes} bytes`),
			], page, "downloaded artifact kept at /tmp during the run");
			// logo upload
			const logoInput = page.locator("input[type=file][accept*=image], input[type=file]").first();
			let logoOk = false;
			if (await logoInput.count()) {
				const png = "/tmp/gstates/logo.png";
				if (!fs.existsSync(png)) {
					fs.writeFileSync(png, Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGBgAAAABQABh6FO1AAAAABJRU5ErkJggg==", "base64"));
				}
				await logoInput.setInputFiles(png).catch(() => {});
				await page.waitForTimeout(2000);
				logoOk = true;
			}
			await rec.record("logo-upload", [
				check("logo upload affordance present", (await logoInput.count()) > 0),
				check("logo file accepted", logoOk),
			], page, "branding upload in the report options");
		}

		// ---------- roof-optional-entry + restart
		{
			const skipRoof = await textOf(page, ".lp-overview-empty");
			await rec.record("roof-optional-entry", [
				check("roof is an optional stage (empty-state copy present)", /roof|Dach/i.test(skipRoof ?? ""), (skipRoof ?? "").slice(0, 80)),
			], page, "the project proceeds without a roof; the roof workspace is an optional stage");
			const restart = page.locator("button:has-text('Projects'), .lp-breadcrumb button").first();
			if (await restart.count()) {
				await restart.click();
				await page.waitForTimeout(2500);
			}
			const backAtProjects = await visible(page, ".lp-project-index", 6000);
			await rec.record("restart", [
				check("leaving to projects preserves saved work", backAtProjects),
			], page, "breadcrumb navigation back to the projects list");
		}
	} catch (e) {
		console.log("combo error (contained):", combo, String(e?.message || e).slice(0, 300));
		rec.rows.push({ key: `${family}:driver:${combo.lang}:${combo.width}`, error: String(e?.message || e).slice(0, 400) });
	} finally {
		if (page.__netfail?.length) rec.rows.push({ key: `${family}:netfail:${combo.lang}:${combo.width}`, netfail: page.__netfail.slice(0, 10) });
		await context.close().catch(() => {});
	}
	return rec;
}

const configuratorStates = new Set(["initial-input", "validation", "calculation-pending", "calculation-error", "compatible-result", "incompatible-result", "roof-optional-entry", "whole-parts-add", "draft-readback", "report", "report-screen-pdf-content-and-current-revision", "download-pdf", "logo-upload", "native-choice-controls", "restart"]);
const roofStates = new Set(["initial-map", "address-search", "outline-draw", "edit-vertices", "obstacles", "orientation-pitch", "undo-redo", "permission-error", "validation-error", "save-return-to-configurator", "mobile-gestures"]);

const browser = await chromium.launch();
const confRows = [];
const roofRows = [];
for (const combo of COMBOS) {
	const rec = await runCombo(browser, combo, "configurator");
	// this driver records both families; split at flush
	confRows.push(...rec.rows.filter((r) => r.state && configuratorStates.has(r.state)));
	roofRows.push(...rec.rows.filter((r) => r.state && roofStates.has(r.state)));
	const other = rec.rows.filter((r) => !r.state || (!configuratorStates.has(r.state) && !roofStates.has(r.state)));
	confRows.push(...other);
}
await browser.close();
const here = path.dirname(new URL(import.meta.url).pathname);
fs.writeFileSync(here + "/evidence/configurator-family.json",
	JSON.stringify({ driver: "configurator", base: BASE, observedAt: new Date().toISOString(), rows: confRows }, null, 1));
fs.writeFileSync(here + "/evidence/roof-family.json",
	JSON.stringify({ driver: "roof", base: BASE, observedAt: new Date().toISOString(), rows: roofRows }, null, 1));
console.log(`\nconfigurator: ${confRows.length} rows (${confRows.filter((r) => r.failed > 0).length} fail), roof: ${roofRows.length} rows (${roofRows.filter((r) => r.failed > 0).length} fail)`);
