#!/usr/bin/env node
/*
 * Turn a measured layout into one sizes rule per image file.
 *
 * Usage: node sizes-from-measurement.mjs <measurement.json> <out.json>
 *
 * The measurement JSON comes from a browser pass that records, per published
 * page and per viewport width, every <img> that renders with a real box and
 * still has no srcset (tools/perf/measure-image-boxes.mjs measures the box).
 *
 * Why a generated table rather than a hand-written one: 20 published pages
 * carry hand-authored <img> markup inside post_content, so there is no source
 * file to derive from and no template to fix once. A hand table only ever
 * catches the images someone remembered; this one states every box that was
 * actually measured.
 *
 * Rule for a file that appears in more than one box at the same viewport: the
 * widest box wins. A sizes rule that understates the box makes the browser pick
 * a variant smaller than the space it fills, which shows as a soft image; a
 * rule that overstates it costs bytes but never quality. Overstating is bounded
 * because the widest measured box is still a fraction of the original file.
 */
import fs from "node:fs";

const [, , measurePath, outPath] = process.argv;
if (!measurePath || !outPath) {
	console.error(
		"usage: node sizes-from-measurement.mjs <measurement.json> <out.json>",
	);
	process.exit(2);
}

const measurement = JSON.parse(fs.readFileSync(measurePath, "utf8"));
const byStem = new Map();

/** Strip the size suffix and extension so one rule covers every variant URL. */
const stemOf = (file) =>
	file.replace(/-\d+x\d+(?=\.[a-z0-9]+$)/i, "").replace(/\.[a-z0-9]+$/i, "");

for (const [, perWidth] of Object.entries(measurement)) {
	for (const [width, rows] of Object.entries(perWidth)) {
		if (!Array.isArray(rows)) continue;
		const viewport = Number(width);
		for (const row of rows) {
			if (!row || !row.f || row.dw < 1) continue;
			const stem = stemOf(row.f);
			if (!byStem.has(stem)) byStem.set(stem, new Map());
			const boxes = byStem.get(stem);
			boxes.set(viewport, Math.max(boxes.get(viewport) ?? 0, row.dw));
		}
	}
}

// Two viewports are measured: a phone (390) and a desktop (1440). The rule
// switches at 768 px, the child theme's own phone/desktop boundary.
const PHONE = 390;
const DESKTOP = 1440;
const SWITCH = 768;
const HEADROOM = 8;

const table = {};
for (const [stem, boxes] of [...byStem.entries()].sort((a, b) =>
	a[0].localeCompare(b[0]),
)) {
	const phone = boxes.get(PHONE);
	const desktop = boxes.get(DESKTOP);
	if (phone === undefined && desktop === undefined) continue;
	// A file seen at one viewport only: state the box it has there and reuse it.
	const phoneBox = Math.ceil((phone ?? desktop) + HEADROOM);
	const desktopBox = Math.ceil((desktop ?? phone) + HEADROOM);
	// A full-bleed band is as wide as the viewport at both measured widths.
	if (phoneBox >= PHONE && desktopBox >= DESKTOP) {
		table[stem] = "100vw";
		continue;
	}
	table[stem] = `(max-width: ${SWITCH}px) ${phoneBox}px, ${desktopBox}px`;
}

fs.writeFileSync(outPath, `${JSON.stringify(table, null, "\t")}\n`);
console.log(`wrote ${outPath}: ${Object.keys(table).length} files`);
