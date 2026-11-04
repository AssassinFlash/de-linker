import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, "../../../..");
const [matrixArg, outArg, baseArg] = process.argv.slice(2);
if (!matrixArg || !outArg || !baseArg) {
	throw new Error("usage: node template-binding.mjs <template-matrix.json> <outdir> <local-base>");
}
const base = baseArg.replace(/\/$/, "");
const templates = JSON.parse(fs.readFileSync(path.resolve(matrixArg), "utf8"));
const out = path.resolve(outArg);
fs.mkdirSync(out, { recursive: true });

function wpContent(id) {
	return execFileSync(
		"just",
		["wp", "fullmatrix", "post", "get", String(id), "--field=post_content"],
		{ cwd: repo, encoding: "utf8", maxBuffer: 20 * 1024 * 1024 },
	);
}

function markerFor(id, content) {
	if (!content.trim()) return { kind: "empty", value: null };
	const ids = [...content.matchAll(/\bid="([a-zA-Z0-9_-]{4,})"/g)].map((m) => m[1]);
	const preferred = ids.find((x) => /^(tv-|lc-)/.test(x)) || ids[0];
	if (preferred) return { kind: "id", value: preferred };
	const classes = [...content.matchAll(/class="([^"]{6,120})"/g)].map((m) => m[1].split(/\s+/)[0]);
	if (classes[0]) return { kind: "class", value: classes[0] };
	return { kind: "content-hash-prefix", value: content.replace(/\s+/g, " ").trim().slice(0, 80) };
}

const rows = [];
for (const template of templates) {
	const content = wpContent(template.id);
	const marker = markerFor(template.id, content);
	const candidates = (template.route_candidates || []).map((c) => ({
		url: c.url,
		path: new URL(c.url).pathname + new URL(c.url).search,
		lang: c.lang,
	}));
	const rendered = [];
	for (const candidate of candidates) {
		const expectedStatus = /_coverage-review-missing-route/.test(candidate.path) ? 404 : null;
		const started = new Date().toISOString();
		let status = null;
		let html = "";
		let found = false;
		let error = null;
		try {
			const response = await fetch(base + candidate.path, { redirect: "follow" });
			status = response.status;
			html = await response.text();
			found = marker.kind === "id"
				? new RegExp(`id="${marker.value}"`).test(html)
				: marker.kind === "class"
					? new RegExp(`class="[^"]*\\b${marker.value}\\b`).test(html)
					: html.replace(/\s+/g, " ").includes(marker.value);
		} catch (e) {
			error = String(e?.message || e).slice(0, 300);
		}
		rendered.push({
			url: candidate.url,
			localUrl: base + candidate.path,
			lang: candidate.lang,
			httpStatus: status,
			expectedStatus,
			marker,
			markerFound: found,
			error,
			observedAt: started,
		});
	}
	const emptyContent = marker.kind === "empty";
	const bound = rendered.length
		&& rendered.every((r) => r.httpStatus !== null)
		&& rendered.some((r) => (emptyContent ? r.httpStatus === 200 : (r.markerFound && (r.expectedStatus ? r.httpStatus === r.expectedStatus : r.httpStatus < 400))));
	const rowsItem = {
		id: template.id,
		kind: template.kind,
		slug: template.slug,
		title: template.title,
		lang: template.lang,
		marker,
		rendered_routes: rendered,
		binding: emptyContent ? "empty-content-local-and-production" : bound ? "bound-local-snapshot" : "not-confirmed",
		evidenceScope: emptyContent
			? "Template post_content is empty (len=0) on the local snapshot AND on production (read-only wp db query 2026-11-04). No code or markup renders from it; 'binding' here records the empty fact, not a render proof. Execution/behavior contract unsatisfiable while content is empty."
			: "Local production-snapshot instance request. Marker proves this LC template/partial content renders on the route; not a pixel-parity or production-identity claim.",
	};
	rows.push(rowsItem);
	console.log(`${emptyContent ? "EMPTY" : bound ? "bound" : "UNBOUND"} ${template.id} ${template.slug} (${rendered.map((r) => r.httpStatus + (r.markerFound ? "+marker" : "-marker")).join(",")})`);
}
fs.writeFileSync(path.join(out, "template-bindings.json"), `${JSON.stringify(rows, null, 2)}\n`);
const summary = {
	templates: rows.length,
	bound: rows.filter((r) => r.binding === "bound-local-snapshot").length,
	emptyContent: rows.filter((r) => r.binding === "empty-content-local-and-production").map((r) => r.id + ":" + r.slug),
	unbound: rows.filter((r) => r.binding === "not-confirmed").map((r) => r.id + ":" + r.slug),
};
fs.writeFileSync(path.join(out, "summary.json"), `${JSON.stringify(summary, null, 2)}\n`);
console.log(JSON.stringify(summary));
