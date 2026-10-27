// ECharts 6.1.0 bundles indexed optional property types incompatible with
// exactOptionalPropertyTypes. Widen only their three base declarations to
// the undefined value already admitted by the derived indexed types.
// Compiler evidence: Path/Displayable plus Graph/Chord ExtraEmphasisState.
// Runtime files and project-wide strict checking remain unchanged.
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
const path = new URL(
	"../node_modules/echarts/types/dist/shared.d.ts",
	import.meta.url,
);
const original = readFileSync(path, "utf8");
const replacements = [
	[
		"hoverLayer?: boolean | number;",
		"hoverLayer?: boolean | number | undefined;",
		1,
	],
	[
		"focus?: DefaultEmphasisFocus | 'adjacency';",
		"focus?: DefaultEmphasisFocus | 'adjacency' | undefined;",
		2,
	],
];
if (
	replacements.every(
		([, next, count]) => original.split(next).length - 1 === count,
	)
)
	process.exit(0);
if (
	createHash("sha256").update(original).digest("hex") !==
	"b81977145fc9eec07bbfd9380228d5c11e8a6dfe42f9af1fedf48da1451c49e0"
)
	throw new Error(
		"Unexpected ECharts declaration bytes; review the pinned compatibility patch",
	);
let corrected = original;
for (const [before, after, count] of replacements) {
	if (corrected.split(before).length - 1 !== count)
		throw new Error("ECharts declaration shape changed");
	corrected = corrected.replaceAll(before, after);
}
writeFileSync(path, corrected);
