/**
 * #351 acceptance captures: the register card's business-type radios, EN/DE,
 * 1440/390 — the resting pills (unchanged design) and the keyboard-focused
 * pill with its focus ring.
 *
 * Evidence tooling only. Nothing is submitted; the walk never leaves step 1
 * and creates no account and no mail. Run after `just present c351` and
 * `just windpress-compile c351` from the repository root:
 *   node docs/acceptance/2026-10-19/351/capture.mjs
 */
import { createRequire } from "node:module";
import { mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const { chromium } = createRequire(
	path.join(here, "../../../../plugins/linker-tools/package.json"),
)("playwright");
const base = process.env.LINKER_CAPTURE_BASE || "http://127.0.0.1:9153";
const out = path.join(here, "screens");
mkdirSync(out, { recursive: true });

const languages = [
	{ code: "en", url: "/my-account/register/" },
	{ code: "de", url: "/de/mein-konto/register/" },
];

async function settle(page) {
	await page.waitForLoadState("networkidle");
	await page.addStyleTag({
		content:
			"*,*::before,*::after{animation:none!important;transition:none!important;}",
	});
	await page.waitForTimeout(250);
}

async function shot(page, name) {
	await page.evaluate(() => window.scrollTo(0, 0));
	await page.waitForTimeout(120);
	await page.screenshot({ path: path.join(out, name), fullPage: true });
	console.log("captured", name);
}

const browser = await chromium.launch();
for (const language of languages) {
	for (const [width, height] of [
		[1440, 900],
		[390, 844],
	]) {
		const page = await browser.newPage({
			viewport: { width, height },
		});
		await page.goto(base + language.url);
		await settle(page);
		await shot(page, `${language.code}-${width}-step-1-resting.png`);

		// The ticket's acceptance state: the radio itself checked and focused.
		// A click on the input selects it (and proves the input is the hit
		// target), then Tab from the company name moves keyboard focus onto
		// the checked input — the browser's tab stop of a radio group — so the
		// focused pill carries the chain's focus ring.
		const installer = page.locator("#linker_customer_role_installer");
		await installer.check();
		await page.locator('[name="billing_company"]').focus();
		await page.keyboard.press("Tab");
		if ((await page.evaluate(() => document.activeElement?.id)) !== "linker_customer_role_installer") {
			throw new Error(
				`Tab did not reach the checked radio on ${language.code} ${width}`
			);
		}
		await shot(page, `${language.code}-${width}-step-1-focus-ring.png`);
		await page.close();
	}
}
await browser.close();
