/**
 * Deterministic layout/visual defect self-check over real pages. See README.md.
 *
 * Reads every page read-only (navigation only), evaluates layout-probes.js in
 * the page, and writes one JSON plus a Markdown table. No form is submitted,
 * nothing is added to a cart, no order is created.
 *
 * Exit status: 0 when no `defect`-severity issue is found (review-severity
 * entries do not fail), 1 otherwise, so it can be a gate.
 */
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";

const here = path.dirname(fileURLToPath(import.meta.url));
const { chromium } = createRequire(path.join(here, "../e2e/package.json"))(
	"playwright",
);

const { values } = parseArgs({
	options: {
		base: { type: "string", default: "https://de-linker.com" },
		out: { type: "string" },
		widths: { type: "string", default: "1440,390" },
		heights: { type: "string", default: "900,844" },
		only: { type: "string" },
		selftest: { type: "boolean", default: false },
		fixture: { type: "string" },
		quiet: { type: "boolean", default: false },
	},
});

const probeSource = fs
	.readFileSync(path.join(here, "layout-probes.js"), "utf8")
	.replace(/;\s*$/, "");
const probe = new Function(`return (${probeSource});`)();

/** Layered UI whose overlap is its purpose; excluded from the overlap rule. */
const OVERLAY_SELECTORS = [
	".cky-consent-bar",
	".cky-consent-container",
	"#cookie-law-info-bar",
	"#linker-genie-mount",
	".linker-genie",
	".linker-genie-panel",
	".linker-genie-peek",
	".woocommerce-store-notice",
	"[class*='skip-link']",
];

const widths = values.widths.split(",").map(Number);
const heights = values.heights.split(",").map(Number);
if (widths.length !== heights.length) {
	throw new Error("--widths and --heights must have the same length");
}

const SETTLE = async (page) => {
	await page.addStyleTag({
		content:
			"*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}",
	});
	await page.evaluate(async () => {
		for (const image of document.images) image.loading = "eager";
		await document.fonts.ready;
	});
	await page.waitForLoadState("networkidle");
	// The probe measures real boxes, so lazy images below the fold must have
	// been laid out with their final intrinsic sizes.
	await page.evaluate(() => {
		for (const image of document.images) {
			if (image.srcset) image.srcset = image.srcset;
		}
	});
	await page.waitForLoadState("networkidle");
	await page.waitForTimeout(400);
};

const PRODUCTION_PAGES = [
	{ name: "home", en: "/" },
	{ name: "products", en: "/products/" },
	{ name: "proforma-request", en: "/proforma-request/" },
	{ name: "cart", en: "/cart/" },
	{ name: "faq-download", en: "/faq-download/" },
	{
		name: "inquiry-received",
		en: "/proforma-request/inquiry-received/8457/?key=wc_order_xi62caTdhUWuM",
		// The guest confirmation gate (Woo's verify-email form) replaces the
		// success card for an anonymous browser; see the report's limitations.
		note: "existing historical order 8457, guest verification gate",
	},
];

const check = async ({ browser, base, page: spec, width, height, index }) => {
	const context = await browser.newContext({
		viewport: { width, height },
		reducedMotion: "reduce",
		deviceScaleFactor: 1,
		userAgent: undefined,
	});
	await context.addInitScript(() => {
		// Put the Genie preview card to rest without touching the server.
		localStorage.setItem(
			"linker-genie-peek-dismissed-until",
			String(Date.now() + 30 * 86400000),
		);
	});
	const tab = await context.newPage();
	const consoleErrors = [];
	tab.on("console", (message) => {
		if (message.type() === "error") consoleErrors.push(message.text().slice(0, 200));
	});
	try {
		const response = await tab.goto(base + spec.path, {
			waitUntil: "networkidle",
			timeout: 120000,
		});
		await SETTLE(tab);
		const result = await tab.evaluate(probe, {
			overlaySelectors: OVERLAY_SELECTORS,
			tapTarget: 24,
		});
		return {
			name: spec.name,
			lang: spec.lang,
			path: spec.path,
			url: result.url,
			title: result.title,
			documentLang: result.lang,
			status: response?.status() ?? 0,
			viewport: `${width}x${height}`,
			document: result.document,
			counts: result.counts,
			issues: result.issues,
			consoleErrors: [...new Set(consoleErrors)].slice(0, 5),
			note: spec.note,
		};
	} catch (error) {
		return {
			name: spec.name,
			lang: spec.lang,
			path: spec.path,
			viewport: `${width}x${height}`,
			failed: String(error.message ?? error).slice(0, 400),
			issues: [],
			counts: {},
		};
	} finally {
		await context.close();
	}
};

/** Opens the fixture from disk at every viewport and checks the verdict. */
const runSelftest = async (browser) => {
	const fileUrl = "file://" + (values.fixture ?? path.join(here, "layout-fixture.html"));
	const results = [];
	for (const [index, width] of widths.entries()) {
		const context = await browser.newContext({
			viewport: { width, height: heights[index] },
			reducedMotion: "reduce",
		});
		const tab = await context.newPage();
		await tab.goto(fileUrl, { waitUntil: "load" });
		const result = await tab.evaluate(probe, { overlaySelectors: OVERLAY_SELECTORS });
		results.push({ viewport: `${width}x${heights[index]}`, ...result });
		await context.close();
	}
	const found = new Set(results.flatMap((row) => row.issues.map((i) => i.type)));
	const selectors = new Set(
		results.flatMap((row) => row.issues.map((i) => i.selector)),
	);
	const expectedTypes = [
		"overflow-x-visible",
		"clipped-by-ancestor",
		"opt-out-of-centering",
		"text-clipped",
		"focusable-invisible",
		"small-target",
		"image-broken",
		"overlap",
		"horizontal-scroll",
	];
	const expectHit = [
		"#planted-overflow",
		"#planted-clipped",
		"#planted-cta",
		"#planted-clipped-text",
		"#planted-hidden-link",
		"#planted-tiny",
		"#planted-broken-img",
		"#planted-overlap-a",
	];
	const expectMiss = [
		"#control-overflow-clipped",
		"#control-scroller",
		"#control-grid-fill",
		"#control-flex",
		"#control-wrapping",
		"#control-hidden-visibility",
		"#control-sr-only",
		"#control-inline-link",
		"#control-big",
		"#control-inline-svg",
	];
	const problems = [];
	for (const type of expectedTypes)
		if (!found.has(type)) problems.push(`missed defect type: ${type}`);
	for (const selector of expectHit)
		if (!selectors.has(selector)) problems.push(`missed planted defect: ${selector}`);
	for (const selector of expectMiss)
		if (selectors.has(selector)) problems.push(`reported a control: ${selector}`);
	return { results, problems };
};

const main = async () => {
	const browser = await chromium.launch({
		channel: "chromium",
		args: [
			"--disable-gpu",
			"--force-color-profile=srgb",
			"--disable-partial-raster",
			"--disable-gpu-rasterization",
		],
	});
	try {
		if (values.selftest) {
			const { results, problems } = await runSelftest(browser);
			const out = values.out ?? path.join(here, "../../.scratch/visual-selfcheck/selftest");
			fs.mkdirSync(out, { recursive: true });
			fs.writeFileSync(
				path.join(out, "selftest.json"),
				JSON.stringify({ results, problems }, null, 2) + "\n",
			);
			if (problems.length) {
				console.error("self-test FAILED\n" + problems.map((p) => "  - " + p).join("\n"));
				if (!values.quiet)
					for (const row of results)
						console.error(row.viewport, JSON.stringify(row.counts));
				process.exitCode = 1;
				return;
			}
			if (!values.quiet)
				console.log(
					`self-test ok: every planted defect reported, no control reported (${results.length} viewports)`,
				);
			return;
		}

		const out =
			values.out ?? path.join(here, "../../.scratch/visual-selfcheck/run");
		fs.mkdirSync(out, { recursive: true });

		// Resolve the German twin of each page from the page's own hreflang
		// alternates, so a changed permalink does not silently test English
		// twice.
		const pages = [];
		for (const spec of PRODUCTION_PAGES) {
			if (values.only && !spec.name.includes(values.only)) continue;
			pages.push({ ...spec, lang: "en", path: spec.en });
			const context = await browser.newContext();
			const tab = await context.newPage();
			let german = null;
			try {
				await tab.goto(values.base + spec.en, {
					waitUntil: "domcontentloaded",
					timeout: 120000,
				});
				german = await tab.evaluate(() => {
					const link = document.querySelector('link[hreflang="de"]');
					if (!link) return null;
					const url = new URL(link.href);
					return url.pathname + url.search;
				});
			} catch {
				german = null;
			} finally {
				await context.close();
			}
			if (!german) throw new Error(`no German alternate on ${spec.en}`);
			pages.push({ ...spec, name: `${spec.name}`, lang: "de", path: german });
		}

		const rows = [];
		for (const [index, width] of widths.entries()) {
			for (const spec of pages) {
				const row = await check({
					browser,
					base: values.base,
					page: spec,
					width,
					height: heights[index],
				});
				rows.push(row);
				if (!values.quiet) {
					const total = row.issues?.length ?? 0;
					console.log(
						`${row.viewport} ${row.lang} ${row.name} ${row.path} -> ${total} (${row.failed ? "FAILED " + row.failed : Object.keys(row.counts ?? {}).map((k) => `${k}:${row.counts[k]}`).join(" ")})`,
					);
				}
			}
		}

		const defects = rows.flatMap((row) =>
			(row.issues ?? [])
				.filter((issue) => issue.severity === "defect")
				.map((issue) => ({ ...issue, name: row.name, lang: row.lang, viewport: row.viewport, path: row.path })),
		);
		const reviews = rows.flatMap((row) =>
			(row.issues ?? [])
				.filter((issue) => issue.severity !== "defect")
				.map((issue) => ({ ...issue, name: row.name, lang: row.lang, viewport: row.viewport, path: row.path })),
		);
		fs.writeFileSync(
			path.join(out, "layout-selfcheck.json"),
			JSON.stringify(
				{
					base: values.base,
					generatedAt: new Date().toISOString(),
					widths,
					heights,
					pages,
					rows,
					summary: {
						pagesChecked: rows.length,
						defects: defects.length,
						reviews: reviews.length,
						failedLoads: rows.filter((row) => row.failed).length,
					},
				},
				null,
				2,
			) + "\n",
		);
		if (!values.quiet) {
			console.log(
				`\n${rows.length} page/viewports, ${defects.length} defect-severity, ${reviews.length} review-severity, ${rows.filter((r) => r.failed).length} failed loads`,
			);
			console.log(`written: ${out}/layout-selfcheck.json`);
		}
		if (defects.length || rows.some((row) => row.failed)) process.exitCode = 1;
	} finally {
		await browser.close();
	}
};

await main();
