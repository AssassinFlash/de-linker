/**
 * Shared full-page capture + exact RGB comparison. See README.md for usage.
 * Capture conditions preserve the measured repeatable setup in the site's
 * acceptance records: software raster, sRGB, decoded images/fonts, no motion.
 */
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";
import { execFileSync } from "node:child_process";

const here = path.dirname(fileURLToPath(import.meta.url));
const { chromium } = createRequire(path.join(here, "../e2e/package.json"))(
	"playwright",
);
const { values, positionals } = parseArgs({
	allowPositionals: true,
	options: {
		widths: { type: "string" },
		paths: { type: "string" },
		"allow-header": { type: "string", multiple: true, default: [] },
		scenarios: { type: "string" },
		baseline: { type: "boolean", default: false },
		direct: { type: "boolean", default: false },
	},
});
const [out, liveBase, localBase] = positionals;
if (
	!out ||
	!liveBase ||
	!localBase ||
	!values.widths ||
	(!values.paths && !values.scenarios)
) {
	throw new Error(
		"usage: node tests/visual/pixel-parity.mjs <outdir> <live-base> <local-base> --widths <comma-list> --paths <comma-list> [--allow-header <path>:<widths>:<height>]",
	);
}
const widths = values.widths.split(",").map(Number);
const scenarios = values.scenarios
	? JSON.parse(fs.readFileSync(values.scenarios, "utf8"))
	: values.paths.split(",").map((route) => ({ path: route }));
const allowedHeaderChanges = values["allow-header"].map((rule) => {
	const [route, widthList, height] = rule.split(":");
	return {
		path: route,
		widths: widthList.split(",").map(Number),
		height: Number(height),
	};
});
fs.mkdirSync(out, { recursive: true });
const cases = [];
for (const width of widths) {
	for (const scenario of scenarios) {
		if (scenario.widths && !scenario.widths.includes(width)) continue;
		const route = scenario.path;
		const stem =
			scenario.name ||
			route.replace(/[^a-z0-9]+/gi, "_").replace(/^_|_$/g, "") ||
			"home";
		if (
			values.baseline &&
			fs.existsSync(path.join(out, `${stem}-${width}-before.png`))
		)
			continue;
		let language;
		let headerHeight;
		const ruledRegions = new Map();
		const imageSources = {};
		const sortRecords = {};
		for (const [base, label] of values.baseline
			? [[localBase, "before"]]
			: [
					[liveBase, "live"],
					[localBase, "local"],
				]) {
			// GPU dithering produced 24,117 differing pixels on identical pages;
			// software raster + sRGB eliminated it. One browser per capture.
			const browser = await chromium.launch({
				channel: "chromium",
				args: [
					...(values.direct ? ["--no-proxy-server"] : []),
					"--disable-gpu",
					"--force-color-profile=srgb",
					"--disable-partial-raster",
					"--disable-gpu-rasterization",
				],
			});
			let page;
			try {
				// 900px is the established desktop/mobile acceptance viewport height.
				const context = await browser.newContext({
					viewport: { width, height: 900 },
					reducedMotion: "reduce",
					deviceScaleFactor: 1,
				});
				await context.addInitScript(() => {
					// Exercise the page at rest during the full-page scroll, without
					// the preview card's 8s dwell. Only this disposable browser stores it.
					localStorage.setItem(
						"linker-genie-peek-dismissed-until",
						String(Date.now() + 30 * 86400000),
					);
				});
				page = await context.newPage();
				// The existing snapshot capture budget also covers live lazy media.
				await page.goto(base + route, {
					waitUntil: "networkidle",
					timeout: 120000,
				});
				for (const action of scenario.actions ?? []) {
					// Only relative visits: filled-draft evidence uses a disposable
					// anonymous Woo session, never an order or inquiry submission.
					if (action.visit) {
						if (!action.visit.startsWith("/") || action.visit.startsWith("//"))
							throw new Error("scenario visits must be site-relative");
						await page.goto(base + action.visit, { waitUntil: "networkidle" });
					}
					if (action.fill)
						await page.locator(action.fill[0]).fill(action.fill[1]);
					if (action.click) await page.locator(action.click).click();
					if (action.press)
						await page.locator(action.press[0]).press(action.press[1]);
				}
				await page.addStyleTag({
					content:
						"*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}",
				});
				// The layout viewport stays at the requested width and the
				// established 900px height for the whole capture; the full page
				// is taken with a CDP clip below. Growing the viewport instead
				// re-lays-out the document, and images whose decode started at the
				// shorter height are re-rasterized for the taller one, which made
				// the same page produce different pixels per host even with
				// identical image bytes and identical canvas hashes at natural and
				// at box size.
				//
				// The sweep must be instant. The site sets scroll-behavior: smooth
				// on the root element, so a plain scrollTo starts an animation that
				// the next call interrupts; the sweep then never reaches the lower
				// sections, their native lazy images keep an empty currentSrc, and
				// img.decode() on them never settles (measured: five images still
				// without a source after a smooth sweep, and the capture hung).
				const sweep = async (step, pause) =>
					page.evaluate(
						async ([stepSize, wait]) => {
							for (
								let y = 0;
								y < document.documentElement.scrollHeight;
								y += stepSize
							) {
								window.scrollTo({ top: y, behavior: "instant" });
								await new Promise((resolve) => setTimeout(resolve, wait));
							}
							window.scrollTo({ top: 0, behavior: "instant" });
						},
						[step, pause],
					);
				const decodeImages = () =>
					page.evaluate(async () => {
						await Promise.all(
							[...document.images]
								.filter(
									(img) =>
										img.getClientRects().length > 0 &&
										getComputedStyle(img).visibility !== "hidden" &&
										img.currentSrc,
								)
								.map((img) => img.decode().catch(() => {})),
						);
					});
				await sweep(600, 120);
				await decodeImages();
				await page.waitForLoadState("networkidle");
				// Loading the lazy images above can make the document taller;
				// sweep again so the new bottom is observed too. The viewport
				// is still not resized.
				await sweep(600, 60);
				await decodeImages();
				await page.evaluate(async () => {
					await document.fonts.ready;
				});
				// Existing capture setup settles fonts/layout for 800ms after decode.
				await page.waitForTimeout(800);
				// Woo shuffles related products on every request
				// (wc_get_related_products() runs shuffle() behind the filterable
				// woocommerce_product_related_posts_shuffle, default true), so two
				// captures of the same page differ in card order on the live host
				// itself. Sorting the rendered cards is a declared normalization of
				// an input that is random by design, not a mask: every pixel is
				// still compared, and both sides must render the same card set.
				const sorted = {};
				for (const rule of scenario.sortChildren ?? []) {
					const record = await page.evaluate((spec) => {
						const containers = [...document.querySelectorAll(spec.selector)];
						if (!containers.length) return null;
						return containers.map((container) => {
							const key = (element) =>
								(element.querySelector(spec.key)?.textContent ?? "").trim();
							const observed = [...container.children].map(key);
							[...container.children]
								.sort((a, b) => key(a).localeCompare(key(b), "en"))
								.forEach((child) => container.appendChild(child));
							return {
								observed,
								sorted: [...container.children].map(key),
							};
						});
					}, rule);
					if (!record)
						throw new Error(`missing sort container: ${rule.selector}`);
					sorted[rule.selector] = record;
				}
				if (Object.keys(sorted).length) await page.waitForTimeout(200);
				sortRecords[label] = sorted;
				imageSources[label] = await page
					.locator(".woocommerce-cart-form img")
					.evaluateAll((images) =>
						images.map((img) => ({
							source: new URL(img.currentSrc).pathname,
							loading: img.loading,
							natural: [img.naturalWidth, img.naturalHeight],
						})),
					);
				const metadata = await page.evaluate(() => ({
					language: document.documentElement.lang.split(/[-_]/)[0],
					headerHeight: Math.ceil(
						document.querySelector("#lc-header")?.getBoundingClientRect()
							.height ?? 0,
					),
				}));
				if (label !== "local") ({ language, headerHeight } = metadata);
				for (const region of scenario.ruledRegions ?? []) {
					const boxes = await page
						.locator(region.selector)
						.evaluateAll((elements) =>
							elements
								.map((element) => {
									const box = element.getBoundingClientRect();
									return {
										x: box.x + scrollX,
										y: box.y + scrollY,
										width: box.width,
										height: box.height,
									};
								})
								.filter((box) => box.width > 0 && box.height > 0),
						);
					if (!boxes.length && label !== "live")
						throw new Error(`missing ruled region: ${region.selector}`);
					const size = await page.evaluate(() => ({
						width: document.documentElement.scrollWidth,
						height: document.documentElement.scrollHeight,
					}));
					for (const [index, box] of boxes.entries()) {
						const padding = region.padding ?? 0;
						const name = `${region.name}:${index}`;
						const bounds = [
							Math.max(0, Math.floor(box.x - padding)),
							Math.max(0, Math.floor(box.y - padding)),
							Math.min(size.width, Math.ceil(box.x + box.width + padding)),
							Math.min(size.height, Math.ceil(box.y + box.height + padding)),
						];
						const previous = ruledRegions.get(name);
						if (previous)
							previous.bounds = [
								Math.min(previous.bounds[0], bounds[0]),
								Math.min(previous.bounds[1], bounds[1]),
								Math.max(previous.bounds[2], bounds[2]),
								Math.max(previous.bounds[3], bounds[3]),
							];
						else ruledRegions.set(name, { ...region, name, bounds });
					}
				}
				const name = `${stem}-${width}-${label}.png`;
				// CDP paints the whole document without resizing the layout
				// viewport, so every element keeps the size it had while the page
				// was laid out. fullPage:true is deliberately not used: Playwright
				// implements it by resizing the viewport, which is the re-layout
				// this capture must avoid.
				const shotSize = await page.evaluate(() => ({
					width: document.documentElement.scrollWidth,
					height: document.documentElement.scrollHeight,
				}));
				const session = await page.context().newCDPSession(page);
				try {
					const shot = await session.send("Page.captureScreenshot", {
						format: "png",
						fromSurface: true,
						captureBeyondViewport: true,
						clip: {
							x: 0,
							y: 0,
							width: shotSize.width,
							height: shotSize.height,
							scale: 1,
						},
					});
					fs.writeFileSync(
						path.join(out, name),
						Buffer.from(shot.data, "base64"),
					);
				} finally {
					await session.detach();
				}
				console.log(name);
			} finally {
				try {
					if (scenario.emptyDraftAfter && page) {
						// Use Woo's own nonce-bearing remove links from this new session.
						const remove = await page
							.locator(".woocommerce-cart-form a.remove")
							.evaluateAll((elements) =>
								elements.map((element) => element.href),
							);
						for (const url of remove)
							await page.goto(url, { waitUntil: "networkidle" });
						if (await page.locator(".woocommerce-cart-form a.remove").count())
							throw new Error(
								"disposable draft cleanup did not empty the session",
							);
					}
				} finally {
					await browser.close();
				}
			}
		}
		cases.push({
			path: route,
			stem,
			width,
			language,
			headerHeight,
			ruledRegions: [...ruledRegions.values()],
			imageSources,
			sortRecords,
		});
	}
}
fs.writeFileSync(
	path.join(out, "capture.json"),
	JSON.stringify(
		{
			cases,
			allowedHeaderChanges,
			networkRoute: values.direct
				? "direct browser connection"
				: "system default",
		},
		null,
		2,
	) + "\n",
);
if (!values.baseline)
	execFileSync("python3", [path.join(here, "compare.py"), out], {
		stdio: "inherit",
	});
