import { createRequire } from "node:module";
import { createHash } from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, "../../../..");
const { chromium } = createRequire(path.join(repo, "tests/e2e/package.json"))("playwright");
const [matrixArg, outArg, baseArg] = process.argv.slice(2);
if (!matrixArg || !outArg || !baseArg) {
	throw new Error("usage: node local-page-sweep.mjs <page-matrix.json> <outdir> <local-base>");
}
const matrixPath = path.resolve(matrixArg);
const out = path.resolve(outArg);
const base = baseArg.replace(/\/$/, "");
const matrixBytes = fs.readFileSync(matrixPath);
const matrixSha256 = createHash("sha256").update(matrixBytes).digest("hex");
const matrix = JSON.parse(matrixBytes.toString("utf8"));
const selected = matrix.filter(
	(row) =>
		row.render === "pending" ||
		row.interaction === "pending" ||
		row.visual_review === "pending",
);
fs.mkdirSync(path.join(out, "screenshots"), { recursive: true });
const resultPath = path.join(out, "results.json");
const resumePath = path.join(out, "resume.json");
let prior = [];
if (fs.existsSync(resultPath) && fs.existsSync(resumePath)) {
	const resume = JSON.parse(fs.readFileSync(resumePath, "utf8"));
	if (resume.matrixSha256 !== matrixSha256 || resume.base !== base) {
		throw new Error("existing results belong to a different matrix or local base");
	}
	prior = JSON.parse(fs.readFileSync(resultPath, "utf8"));
}
const completed = new Map(prior.map((row) => [row.key, row]));
const results = [];
let failures = 0;

function persist() {
	const ordered = selected.map((row) => completed.get(row.key)).filter(Boolean);
	fs.writeFileSync(resultPath, `${JSON.stringify(ordered, null, 2)}\n`);
	fs.writeFileSync(
		resumePath,
		`${JSON.stringify({ matrixSha256, base, selected: selected.length, completed: ordered.length }, null, 2)}\n`,
	);
}

function routeFor(url) {
	const parsed = new URL(url);
	return `${parsed.pathname}${parsed.search}${parsed.hash}`;
}

function safeError(error) {
	return String(error?.message || error).replace(/[\r\n]+/g, " ").slice(0, 1000);
}

async function dismissConsent(page) {
	const reject = page.locator('[data-cky-tag="reject-button"]:visible');
	if (await reject.count()) {
		await reject.first().click();
		return "rejected-in-disposable-local-context";
	}
	return "not-shown";
}

async function readRuntime(page) {
	return page.evaluate(() => {
		const root = document.documentElement;
		const main = document.querySelector("main") || document.querySelector("#main") || document.body;
		const visible = (element) => {
			const style = getComputedStyle(element);
			const box = element.getBoundingClientRect();
			return style.display !== "none" && style.visibility !== "hidden" && box.width > 0 && box.height > 0;
		};
		const controls = [...main.querySelectorAll("a,button,input,select,textarea,summary,[role=tab],[tabindex]")]
			.filter(visible)
			.map((element) => ({
				tag: element.tagName.toLowerCase(),
				id: element.id || null,
				role: element.getAttribute("role"),
				type: element.getAttribute("type"),
				text: (element.innerText || element.getAttribute("aria-label") || element.getAttribute("value") || "").trim().replace(/\s+/g, " ").slice(0, 240),
				href: element.href || null,
				disabled: Boolean(element.disabled) || element.getAttribute("aria-disabled") === "true",
			}));
		const links = [...main.querySelectorAll("a[href]")]
			.filter(visible)
			.map((element) => ({
				href: element.href,
				text: (element.innerText || element.getAttribute("aria-label") || "").trim().replace(/\s+/g, " ").slice(0, 240),
			}));
		const overflow = [...main.querySelectorAll("body *")]
			.filter(visible)
			.map((element) => {
				const box = element.getBoundingClientRect();
				return { element, left: box.left + scrollX, right: box.right + scrollX, width: box.width };
			})
			.filter((box) => box.width > 0 && (box.left < -1 || box.right > innerWidth + 1))
			.slice(0, 30)
			.map((box) => ({
				tag: box.element.tagName.toLowerCase(),
				id: box.element.id || null,
				class: typeof box.element.className === "string" ? box.element.className.slice(0, 240) : null,
				left: Math.round(box.left * 100) / 100,
				right: Math.round(box.right * 100) / 100,
			}));
		return {
			title: document.title,
			language: root.lang,
			h1: [...document.querySelectorAll("h1")].filter(visible).map((node) => node.innerText.trim()),
			textLength: (main.innerText || "").trim().length,
			mainText: (main.innerText || "").trim().slice(0, 20000),
			viewport: { innerWidth, innerHeight, clientWidth: root.clientWidth, scrollWidth: root.scrollWidth, scrollHeight: root.scrollHeight },
			controls,
			links,
			overflow,
			mojibake: /[\uFFFD]|Ã.|â€/.test(document.body.innerText),
			images: [...document.images].filter(visible).map((image) => ({
				src: image.currentSrc || image.src,
				complete: image.complete,
				naturalWidth: image.naturalWidth,
				naturalHeight: image.naturalHeight,
			})),
		};
	});
}

async function captureAtRest(page, screenshot) {
	await page.addStyleTag({ content: "*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}" });
	await page.evaluate(async () => {
		for (let y = 0; y < document.body.scrollHeight; y += 600) {
			window.scrollTo(0, y);
			await new Promise((resolve) => setTimeout(resolve, 80));
		}
		window.scrollTo(0, 0);
		await document.fonts.ready;
	});
	await page.waitForTimeout(250);
	await page.screenshot({ path: screenshot, fullPage: true });
}

async function clickTarget(page, target) {
	const box = target.box;
	const text = target.text || target.id || target.href || "unnamed";
	if (box) await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
	return { label: text, type: "button", clicked: true, url: page.url() };
}

async function exerciseInteractions(page, context, row, runtime) {
	const baseOrigin = new URL(base).origin;
	const interactions = [];
	const errors = [];
	if (runtime.controls.length === 0) {
		interactions.push({ type: "page-controls", result: "no main-region controls; shared chrome is evaluated separately" });
		return { interactions, errors };
	}
	for (const target of runtime.controls.filter((item) => ["button", "summary"].includes(item.tag) || item.role === "tab").slice(0, 30)) {
		try {
			const locator = target.id
				? page.locator(`#${target.id.replace(/([^a-zA-Z0-9_-])/g, "\\$1")}`).first()
				: page.getByRole(target.tag === "summary" ? "group" : target.role === "tab" ? "tab" : "button", { name: target.text, exact: true }).first();
			if (!(await locator.count()) || !(await locator.isVisible())) continue;
			const before = await page.evaluate(() => ({ url: location.href, hash: location.hash }));
			await locator.click({ timeout: 5000 });
			await page.waitForTimeout(100);
			const after = await page.evaluate(() => ({ url: location.href, hash: location.hash }));
			interactions.push({ type: target.role === "tab" ? "tab" : "disclosure", label: target.text || target.id, before, after, clicked: true });
		} catch (error) {
			errors.push({ type: "interaction", label: target.text || target.id, error: safeError(error) });
		}
	}
	const hashes = [];
	const seenHash = new Set();
	for (const link of runtime.links) {
		try {
			const parsed = new URL(link.href);
			if (parsed.origin !== baseOrigin || !parsed.hash || parsed.pathname + parsed.search !== new URL(page.url()).pathname + new URL(page.url()).search || seenHash.has(parsed.hash)) continue;
			seenHash.add(parsed.hash);
			const locator = page.locator(`a[href="${parsed.hash}"]`).first();
			if (!(await locator.count()) || !(await locator.isVisible())) continue;
			await locator.click({ timeout: 5000 });
			await page.waitForTimeout(100);
			const state = await page.evaluate(() => ({ url: location.href, hash: location.hash, scrollY }));
			const targetExists = await page.locator(parsed.hash).count();
			const item = { type: "same-page-anchor", href: link.href, state, targetExists: targetExists > 0 };
			interactions.push(item);
			hashes.push(item);
		} catch (error) {
			errors.push({ type: "same-page-anchor", label: link.href, error: safeError(error) });
		}
	}
	const candidate = runtime.links.find((link) => {
		try {
			const parsed = new URL(link.href);
			return parsed.origin === baseOrigin && !parsed.hash && !/[?&](add-to-cart|remove_item)=/.test(parsed.search) && !/\/(cart|proforma-request|my-account)(\/|$)/.test(parsed.pathname) && !/\/(loesungsentwurf|proforma-anfrage|mein-konto)(\/|$)/.test(parsed.pathname);
		} catch {
			return false;
		}
	});
	if (candidate) {
		const destination = await context.newPage();
		try {
			const response = await destination.goto(candidate.href, { waitUntil: "domcontentloaded", timeout: 30000 });
			const readback = await destination.evaluate(() => ({ url: location.href, lang: document.documentElement.lang, h1: [...document.querySelectorAll("h1")].map((node) => node.innerText.trim()) }));
			interactions.push({ type: "internal-link-consumer", source: candidate.text, destinationStatus: response?.status() ?? null, ...readback });
		} catch (error) {
			errors.push({ type: "internal-link-consumer", label: candidate.href, error: safeError(error) });
		} finally {
			await destination.close();
		}
	}
	return { interactions, errors };
}

const browser = await chromium.launch({
	channel: "chromium",
	args: ["--disable-gpu", "--force-color-profile=srgb", "--disable-partial-raster", "--disable-gpu-rasterization"],
});
try {
	for (const [index, row] of selected.entries()) {
		const existing = completed.get(row.key);
		if (existing) {
			results.push(existing);
			console.log(`reuse ${index + 1}/${selected.length} ${row.key}`);
			continue;
		}
		const startedAt = new Date().toISOString();
		const context = await browser.newContext({ viewport: { width: row.width, height: 900 }, reducedMotion: "reduce", deviceScaleFactor: 1 });
		await context.addInitScript(() => localStorage.setItem("linker-genie-peek-dismissed-until", String(Date.now() + 2592000000)));
		const page = await context.newPage();
		const consoleErrors = [];
		const pageErrors = [];
		const requestFailures = [];
		page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text().slice(0, 1000)); });
		page.on("pageerror", (error) => pageErrors.push(safeError(error)));
		page.on("requestfailed", (request) => requestFailures.push({ url: request.url(), error: request.failure()?.errorText || "unknown" }));
		const stem = `${row.kind}-${row.id}-${row.lang || "unknown"}-${row.width}`.replace(/[^a-zA-Z0-9_.-]/g, "_");
		const screenshot = path.join(out, "screenshots", `${stem}.png`);
		let result;
		try {
			const response = await page.goto(base + routeFor(row.url), { waitUntil: "domcontentloaded", timeout: 45000 });
			await page.waitForLoadState("networkidle", { timeout: 10000 }).catch(() => {});
			const consent = await dismissConsent(page);
			const runtime = await readRuntime(page);
			await captureAtRest(page, screenshot);
			const afterMedia = await readRuntime(page);
			const interactionResult = await exerciseInteractions(page, context, row, afterMedia);
			const failedImages = afterMedia.images.filter((image) => image.complete && image.naturalWidth === 0);
			const basicPass = Boolean(response && response.status() < 400 && afterMedia.h1.length && (!row.lang || afterMedia.language.toLowerCase().startsWith(row.lang)));
			result = {
				key: row.key,
				kind: row.kind,
				id: row.id,
				lang: row.lang,
				width: row.width,
				requestedUrl: row.url,
				localUrl: base + routeFor(row.url),
				finalUrl: page.url(),
				httpStatus: response?.status() ?? null,
				startedAt,
				completedAt: new Date().toISOString(),
				consent,
				basicPass,
				language: afterMedia.language,
				h1: afterMedia.h1,
				title: afterMedia.title,
				textLength: afterMedia.textLength,
				mainTextSha256: createHash("sha256").update(afterMedia.mainText).digest("hex"),
				viewport: afterMedia.viewport,
				overflow: afterMedia.overflow,
				mojibake: afterMedia.mojibake,
				failedImages,
				controls: afterMedia.controls,
				interactions: interactionResult.interactions,
				interactionErrors: interactionResult.errors,
				consoleErrors,
				pageErrors,
				requestFailures,
				screenshot: path.relative(repo, screenshot),
				evidenceScope: "Anonymous local production-snapshot row at rest; safe main-region disclosures/tabs, same-page anchors and one eligible internal-link consumer. No form submission, draft mutation, mail or model call. Automated capture/geometry is not live/local pixel parity or full manual visual approval.",
			};
			if (!basicPass) failures += 1;
		} catch (error) {
			failures += 1;
			result = { key: row.key, kind: row.kind, id: row.id, lang: row.lang, width: row.width, requestedUrl: row.url, localUrl: base + routeFor(row.url), startedAt, completedAt: new Date().toISOString(), basicPass: false, fatalError: safeError(error), consoleErrors, pageErrors, requestFailures };
		} finally {
			await context.close();
		}
		completed.set(row.key, result);
		results.push(result);
		persist();
		console.log(`${result.basicPass ? "ok" : "FAIL"} ${index + 1}/${selected.length} ${row.key}`);
	}
} finally {
	await browser.close();
	persist();
}
const summary = {
	matrixSha256,
	base,
	selected: selected.length,
	completed: completed.size,
	basicPass: [...completed.values()].filter((row) => row.basicPass).length,
	basicFailures: [...completed.values()].filter((row) => !row.basicPass).length,
	overflowRows: [...completed.values()].filter((row) => row.viewport && row.viewport.scrollWidth > row.viewport.innerWidth + 1).length,
	failedImageRows: [...completed.values()].filter((row) => row.failedImages?.length).length,
	consoleErrorRows: [...completed.values()].filter((row) => row.consoleErrors?.length).length,
	pageErrorRows: [...completed.values()].filter((row) => row.pageErrors?.length).length,
	interactionErrorRows: [...completed.values()].filter((row) => row.interactionErrors?.length).length,
};
fs.writeFileSync(path.join(out, "summary.json"), `${JSON.stringify(summary, null, 2)}\n`);
console.log(JSON.stringify(summary, null, 2));
if (completed.size !== selected.length || failures) process.exitCode = 1;
