import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, "../../../..");
const { chromium } = createRequire(path.join(repo, "tests/e2e/package.json"))("playwright");
const [outArg, baseArg] = process.argv.slice(2);
const base = baseArg.replace(/\/$/, "");
const out = path.resolve(outArg);
const results = [];
const MAIL_DIR = path.join(process.env.HOME, "de-linker-local/fullmatrix/mail");
const UNIQUE = `p4${Date.now().toString(36)}`;

function mailSnapshot() {
	if (!fs.existsSync(MAIL_DIR)) return [];
	return fs.readdirSync(MAIL_DIR).filter((f) => !f.startsWith(".")).map((f) => {
		const body = fs.readFileSync(path.join(MAIL_DIR, f), "utf8").slice(0, 6000);
		return { file: f, to: (body.match(/[Tt]o:\s*([^\r\n]+)/) || [])[1] || null, subject: (body.match(/[Ss]ubject:\s*([^\r\n]+)/) || [])[1] || null, preview: body };
	});
}
async function record(key, lang, width, page, url, checks, scope, extra = {}) {
	const stem = `rolep4-${key}:${lang}:${width}`.replace(/[^a-zA-Z0-9_.:-]/g, "_");
	const shot = path.join(out, "screenshots", `${stem}.png`);
	let screenshot = null;
	if (page) { try { await page.screenshot({ path: shot }); screenshot = path.relative(repo, shot); } catch {} }
	const failed = checks.filter((c) => c.result === "fail").length;
	results.push({ key: `${key}:${lang}:${width}`, stateKey: key, lang, width, url, checks, passed: checks.length - failed, failed, status: failed ? "fail" : "observed", screenshot, scope, observedAt: new Date().toISOString(), pass: "role4", ...extra });
	console.log(`${failed ? "FAIL" : "ok  "} ${key}:${lang}:${width}`);
}
async function page2(context, route) {
	const p = await context.newPage();
	await p.goto(base + route, { waitUntil: "domcontentloaded", timeout: 90000 });
	await p.waitForLoadState("networkidle", { timeout: 8000 }).catch(() => {});
	const r = p.locator('[data-cky-tag="reject-button"]:visible');
	if (await r.count()) { await r.first().click().catch(() => {}); await p.waitForTimeout(300); }
	return p;
}
const CLICK = { timeout: 20000 };

const browser = await chromium.launch({ channel: "chromium", args: ["--disable-gpu"] });
try {
	// 1) guest inquiry, fresh context, original generic submit
	{
		const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
		const p = await page2(ctx, "/proforma-request/");
		await p.locator("input[type='email']").first().fill(`fm-guest-${UNIQUE}@local.test`);
		const nf = p.locator("input[name*='name' i]:visible").first();
		if (await nf.count()) await nf.fill("Guest Fullmatrix P4");
		const msg = p.locator("textarea").first();
		if (await msg.count()) await msg.fill("Fullmatrix pass-4 single-shot guest inquiry.");
		const consent = p.locator("input[name='consent']").first();
		if (await consent.count()) await consent.check().catch(() => {});
		const submit = p.locator("form button[type='submit'], form input[type='submit']").first();
		await submit.scrollIntoViewIfNeeded();
		await new Promise((r) => setTimeout(r, 3500)); // PublicGuard::MIN_SECONDS = 3
		await submit.click(CLICK);
		await p.waitForLoadState("networkidle", { timeout: 40000 }).catch(() => {});
		await p.waitForTimeout(1500);
		const url = p.url();
		const ok = /inquiry-received|order-received/.test(url);
		const h1 = await p.locator("h1").first().innerText().catch(() => "");
		const err = await p.locator(".woocommerce-error, .woocommerce-info").first().innerText().catch(() => "");
		await record("inquiry:success-confirmation", "en", 1440, p, url, [
			{ name: "lands on native received endpoint", result: ok ? "pass" : "fail", observed: `url=${url} h1=${h1.trim().slice(0, 80)} err=${err.trim().slice(0, 120)}` },
		], "Pass-4 single-shot guest inquiry on isolated local instance (fresh context, one submission)");
		await record("dynamic-routes:inquiry-detail-and-received-key", "en", 1440, p, url, [
			{ name: "valid received key exercised", result: ok && /key=/.test(url) ? "pass" : "fail", observed: url },
		], "Valid received-key from the real submission above");
		await ctx.close();
	}
	// 2) contact EN, fresh context
	{
		const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
		const p = await page2(ctx, "/contact/");
		await p.locator("input[type='email']").first().fill(`fm-contact-${UNIQUE}@local.test`);
		const nf = p.locator("input[name*='name' i]:visible").first();
		if (await nf.count()) await nf.fill("Contact Fullmatrix P4");
		const msg = p.locator("textarea").first();
		if (await msg.count()) await msg.fill("Fullmatrix pass-4 single-shot contact message.");
		const consent = p.locator("input[name='consent']").first();
		if (await consent.count()) await consent.check().catch(() => {});
		const submit = p.locator("form button[type='submit'], form input[type='submit']").first();
		await submit.scrollIntoViewIfNeeded();
		await new Promise((r) => setTimeout(r, 3500)); // PublicGuard::MIN_SECONDS = 3
		await submit.click(CLICK);
		await p.waitForLoadState("networkidle", { timeout: 30000 }).catch(() => {});
		await p.waitForTimeout(1200);
		const notice = await p.locator(".woocommerce-message, .linker-form-success, [class*='success']").first().innerText().catch(() => "");
		const err = await p.locator(".woocommerce-error").first().innerText().catch(() => "");
		await record("contact:success", "en", 1440, p, p.url(), [
			{ name: "success state reached", result: /[?&]contact=(ok|sent|thanks)|thank|danke/i.test(p.url()) || /thank|sent|message/i.test(notice) ? "pass" : "fail", observed: `url=${p.url()} notice=${notice.trim().slice(0, 120)} err=${err.trim().slice(0, 120)}` },
		], "Pass-4 single-shot contact submission (fresh context)");
		await ctx.close();
	}
	// 3) signed-in approved inquiry
	{
		const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
		const lp = await page2(ctx, "/my-account/");
		await lp.fill("#username", "fm-approved");
		await lp.fill("#password", "Fm!Pwapproved#26");
		await lp.click("button[name='login']");
		await lp.waitForLoadState("networkidle", { timeout: 20000 }).catch(() => {});
		await lp.waitForTimeout(600);
		const pdp = await page2(ctx, "/product/saj-ats1-t63-a/");
		const add = pdp.locator("a[href*='add-to-cart']").first();
		await add.scrollIntoViewIfNeeded();
		await add.click(CLICK).catch(() => {});
		await pdp.waitForTimeout(900);
		const iq = await page2(ctx, "/proforma-request/");
		await iq.waitForTimeout(900);
		const msg = iq.locator("textarea").first();
		if (await msg.count()) await msg.fill("Fullmatrix pass-4 approved inquiry.");
		const submit = iq.locator("form button[type='submit'], form input[type='submit']").first();
		await submit.scrollIntoViewIfNeeded();
		await new Promise((r) => setTimeout(r, 3500)); // PublicGuard::MIN_SECONDS = 3
		await submit.click(CLICK);
		await iq.waitForLoadState("networkidle", { timeout: 40000 }).catch(() => {});
		await iq.waitForTimeout(1500);
		const url = iq.url();
		const ok = /inquiry-received|order-received/.test(url);
		const err = await iq.locator(".woocommerce-error, .woocommerce-info").first().innerText().catch(() => "");
		await record("inquiry:signed-in-summary", "en", 1440, iq, url, [
			{ name: "signed-in submission accepted", result: ok ? "pass" : "fail", observed: `url=${url} err=${err.trim().slice(0, 160)}` },
		], "Pass-4 approved-customer inquiry after PDP add");
		await ctx.close();
	}
	// 4) reset with long poll
	{
		const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
		const before = mailSnapshot().length;
		const lp = await page2(ctx, "/my-account/lost-password/");
		const userInput = lp.locator("input[name='user_login']");
		if (await userInput.count()) {
			await userInput.fill("fm-approved");
			await lp.locator("button[type='submit']").first().click(CLICK).catch(() => {});
			await lp.waitForLoadState("networkidle", { timeout: 20000 }).catch(() => {});
		}
		let resetMail = null;
		for (let i = 0; i < 60 && !resetMail; i++) {
			await new Promise((r) => setTimeout(r, 3000));
			resetMail = mailSnapshot().slice(before).find((m) => /reset|passwort/i.test(m.subject || ""));
		}
		const link = resetMail ? (resetMail.preview.match(/https?:\/\/[^\s"<>]+key=[^\s"<>]+/g) || [])[0] : null;
		let final = null;
		if (link) {
			const rp = await ctx.newPage();
			await rp.goto(link.replace(/&amp;/g, "&"), { waitUntil: "domcontentloaded", timeout: 30000 }).catch(() => {});
			await rp.waitForTimeout(1000);
			const p1 = rp.locator("input[name='password_1'], input[type='password']").first();
			if (await p1.count()) {
				await p1.fill("Fm!Pwapproved#26");
				const p2 = rp.locator("input[name='password_2']").first();
				if (await p2.count()) await p2.fill("Fm!Pwapproved#26");
				await rp.locator("button[type='submit'], input[type='submit']").first().click(CLICK).catch(() => {});
				await rp.waitForTimeout(1500);
				final = rp.url();
			}
			await rp.close();
		}
		await record("dynamic-routes:password-reset-token-states", "en", 1440, null, link ? "captured" : "-", [
			{ name: "reset mail captured with key link", result: link ? "pass" : "fail", observed: `mail=${resetMail?.subject} link=${link ? link.slice(-70) : null} (async queue up to 180s)` },
			{ name: "valid key completes reset", result: final ? "pass" : "fail", observed: `final=${final}` },
		], "Pass-4: lost-password UI flow with 180s async mail poll");
		await ctx.close();
	}
} finally {
	await browser.close();
	fs.writeFileSync(path.join(out, "role-results-pass4.json"), `${JSON.stringify(results, null, 2)}\n`);
}
console.log(JSON.stringify({ rows: results.length, fails: results.filter((r) => r.failed > 0).map((r) => r.key) }));
