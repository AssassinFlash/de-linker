/**
 * #225 acceptance captures: the two-step register card, EN/DE, 1440/390.
 *
 * Evidence tooling only. It never submits a valid registration; the two
 * refused posts create no account and no mail (their errors are the subject).
 * Run from the repository root:
 *   node docs/acceptance/2026-10-19/225/capture.mjs
 */
import { createRequire } from "node:module";
import { execFileSync } from "node:child_process";
import { mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, "../../../..");
const { chromium } = createRequire(
	path.join(here, "../../../../plugins/linker-tools/package.json"),
)("playwright");
const base = process.env.LINKER_CAPTURE_BASE || "http://127.0.0.1:9138";
const out = path.join(here, "screens");
mkdirSync(out, { recursive: true });

// The shared public-connection allowance is three per hour (PublicGuard). Each
// server-refusal case below spends one, so the local instance's limiter is
// cleared between cases, the way IntegrationTestCase isolates it. Local only.
const clearLimits =
	'global $wpdb; $wpdb->query( $wpdb->prepare( "DELETE FROM {$wpdb->options} WHERE option_name LIKE %s", $wpdb->esc_like( "linker_commerce_limit_" ) . "%" ) );';
function resetLimits() {
	execFileSync("just", ["wp", "c225", "eval", clearLimits], { cwd: repo, stdio: "ignore" });
}

const languages = [
	{ code: "en", url: "/my-account/register/", first: "First name", last: "Last name", email: "Email address", password: "Password", company: "Company name" },
	{ code: "de", url: "/de/mein-konto/register/", first: "Vorname", last: "Nachname", email: "E-Mail-Adresse", password: "Passwort", company: "Firmenname" },
];

async function settle(page) {
	await page.waitForLoadState("networkidle");
	await page.addStyleTag({ content: "*,*::before,*::after{animation:none!important;transition:none!important;}" });
	await page.waitForTimeout(250);
}

async function shot(page, name) {
	// A full-page capture paints a position:fixed header where the page is
	// scrolled; the focus jump of a step change can put it mid-card. Start at
	// the document top for every state.
	await page.evaluate(() => window.scrollTo(0, 0));
	await page.waitForTimeout(120);
	await page.screenshot({ path: path.join(out, name), fullPage: true });
	console.log("captured", name);
}

async function panel(page) {
	return page.locator('[data-pane="1"]');
}

async function fillCompany(page, language) {
	await page.locator('[name="billing_company"]').fill("Solarbau Beispiel GmbH");
	await page.locator('label.radio[for="linker_customer_role_installer"]').click();
	await page.locator('[name="linker_company_website"]').fill("example.com");
}

async function serverSubmit(page) {
	await page.evaluate(() => {
		const form = document.querySelector("form[data-linker-register]");
		if (!form) return;
		// A copy of the no-JavaScript submission: every field of both panes
		// posts, exactly as the single form does without account-ui.js.
		form.querySelectorAll(":disabled").forEach((control) => {
			control.disabled = false;
		});
		const register = document.createElement("input");
		register.type = "hidden";
		register.name = "register";
		register.value = "Register";
		form.appendChild(register);
		HTMLFormElement.prototype.submit.call(form);
	});
}

const browser = await chromium.launch({ channel: "chromium", args: ["--disable-gpu", "--force-color-profile=srgb"] });
try {
	for (const language of languages) {
		for (const width of [1440, 390]) {
			const context = await browser.newContext({ viewport: { width, height: 900 }, reducedMotion: "reduce", deviceScaleFactor: 1 });
			await context.addInitScript(() => {
				try {
					localStorage.setItem("linker-genie-peek-dismissed-until", String(Date.now() + 30 * 86400000));
				} catch (e) {}
			});
			const page = await context.newPage();
			page.on("pageerror", (error) => console.log("pageerror", language.code, width, error.message));
			await page.goto(base + language.url, { waitUntil: "networkidle", timeout: 120000 });
			await settle(page);

			// Step 1, fresh.
			await shot(page, `${language.code}-${width}-step-1.png`);

			// The searchable country select, open.
			await page.locator(".select2-selection--single").click();
			await page.waitForTimeout(300);
			await shot(page, `${language.code}-${width}-country-open.png`);
			await page.keyboard.press("Escape");

			// A client-side refusal: nothing filled, Continue.
			await page.locator("[data-next]").click();
			await page.waitForTimeout(150);
			await shot(page, `${language.code}-${width}-step-1-client-errors.png`);

			// Step 2, filled step 1.
			await fillCompany(page, language);
			await page.locator("[data-next]").click();
			await page.waitForTimeout(150);
			await shot(page, `${language.code}-${width}-step-2.png`);
			await context.close();

			// A server-side refusal from step 1 (JS validation bypassed): the
			// server's notice and its step-1 opening.
			resetLimits();
			const step1 = await browser.newContext({ viewport: { width, height: 900 }, reducedMotion: "reduce", deviceScaleFactor: 1 });
			const p1 = await step1.newPage();
			await p1.goto(base + language.url, { waitUntil: "networkidle", timeout: 120000 });
			await settle(p1);
			await p1.waitForTimeout(3200);
			await Promise.all([p1.waitForNavigation({ waitUntil: "networkidle", timeout: 120000 }), serverSubmit(p1)]);
			await settle(p1);
			await shot(p1, `${language.code}-${width}-step-1-server-errors.png`);
			await step1.close();

			// A server-side refusal from step 2: the company is complete, the
			// email is not; the card keeps step 2 open with WooCommerce's notice.
			resetLimits();
			const step2 = await browser.newContext({ viewport: { width, height: 900 }, reducedMotion: "reduce", deviceScaleFactor: 1 });
			const p2 = await step2.newPage();
			await p2.goto(base + language.url, { waitUntil: "networkidle", timeout: 120000 });
			await settle(p2);
			await fillCompany(p2, language);
			await p2.locator("[data-next]").click();
			await p2.locator('[name="email"]').fill("not-an-email");
			await p2.locator('[name="billing_first_name"]').fill("Maria");
			await p2.locator('[name="billing_last_name"]').fill("Beispiel");
			await p2.locator('[name="password"]').fill("Muster-Solar-2026!");
			await p2.waitForTimeout(3200);
			await Promise.all([p2.waitForNavigation({ waitUntil: "networkidle", timeout: 120000 }), serverSubmit(p2)]);
			await settle(p2);
			await shot(p2, `${language.code}-${width}-step-2-server-errors.png`);
			await step2.close();
		}
	}
} finally {
	await browser.close();
}
