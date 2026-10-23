// Independent analytic review probe. Uses the existing checkout/dependencies;
// no browser, provider request, service, copy, or build mutation is performed.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const rootUrl = new URL("../../../../../../", import.meta.url);
const root = fileURLToPath(rootUrl);
const pinned = "f40db1d6e22f4b7511ddc658024ff2cf8f91f507";
const git = (...args) => execFileSync("git", args, {
	cwd: root,
	stdio: ["ignore", "pipe", "pipe"],
});
const sha = (bytes) => createHash("sha256").update(bytes).digest("hex");
const changed = git("diff", "--name-only", `be5711bf...${pinned}`)
	.toString()
	.trim()
	.split("\n");
const checked = [];
for (const path of changed.filter((path) =>
	path.startsWith("apps/planner/") ||
	path.startsWith("plugins/linker-tools/") ||
	path.startsWith("plugins/linker-commerce/content/windpress/") ||
	path.startsWith("tools/local/"),
)) {
	let expected;
	try {
		expected = git("show", `${pinned}:${path}`);
	} catch {
		continue; // A deleted former generated chunk is not a runnable input.
	}
	const actual = readFileSync(new URL(path, rootUrl));
	assert.deepEqual(actual, expected, `${path} differs from pinned source`);
	checked.push({ path, sha256: sha(actual) });
}
const domain = (name) => import(new URL(`apps/planner/src/domain/${name}.ts`, rootUrl));
const { readGeometry } = await domain("validateGeometry");
const { geographicMapGeometry } = await domain("mapGeometry");
const { geometryUvResolution, requireUvResolution } = await domain("geometryNumerics");
const { pointOnRoof } = await domain("coordinates");
const document = JSON.parse(readFileSync(new URL("fixtures/planning/geometry-flat.json", rootUrl)));
const policy = JSON.parse(readFileSync(new URL("apps/planner/src/contracts/geometry-policy.json", rootUrl)));

// A declared analytic 20 m square. Its large UV chart is legal wire data but
// exceeds the existing render arithmetic domain. The cancelling origin keeps
// the geographic display at an ordinary supported Cologne latitude.
const offset = 1e14;
const diagonal = Math.SQRT1_2;
document.coordinate_system.north_reference = "true_north";
document.coordinate_system.north_source_id = "survey";
document.coordinate_system.anchor = {
	latitude_deg: 50.94,
	longitude_deg: 6.96,
	source_id: "survey",
	datum: "EPSG:4326",
};
document.arrays = [];
Object.assign(document.roofs[0], {
	origin_enu: [0, -2 * diagonal * offset, 4],
	u_axis_enu: [diagonal, diagonal, 0],
	v_axis_enu: [-diagonal, diagonal, 0],
	boundary_uv: [
		[offset, offset],
		[offset + 20, offset],
		[offset + 20, offset + 20],
		[offset, offset + 20],
	],
});
const geometry = readGeometry(document, policy);
const before = JSON.stringify(geometry);
let existingGuard;
try {
	requireUvResolution(geometry.roofs[0].boundary_uv.flat());
	existingGuard = "accepted";
} catch (error) {
	existingGuard = error.message;
}
const view = geographicMapGeometry(geometry);
assert.equal(JSON.stringify(geometry), before);
const enu = geometry.roofs[0].boundary_uv.map((uv) => pointOnRoof(geometry.roofs[0], uv));
const edges = enu.map((point, index) => Math.hypot(...point.map((value, axis) => enu[(index + 1) % enu.length][axis] - value)));
assert.equal(existingGuard, "geometry_numeric_resolution_unsupported");
assert.equal(view.collection.features.length, 1);
assert.ok(edges.every((length) => Math.abs(length - 20) > 0.019));
const report = {
	pinned,
	commands: {
		diff: `git diff be5711bf...${pinned}`,
		log: `git log be5711bf..${pinned} --oneline`,
		reproduce: `node ${fileURLToPath(import.meta.url)}`,
	},
	commits: git("log", `be5711bf..${pinned}`, "--oneline").toString().trim().split("\n"),
	pinned_current_files: checked,
	numerical_support: {
		wire_validation: "accepted",
		fixture: document,
		uv_resolution_m: geometryUvResolution(geometry),
		policy_max_uv_resolution_m: JSON.parse(readFileSync(new URL("apps/planner/src/contracts/geometry-numerics.json", rootUrl))).max_uv_resolution_m,
		existing_renderer_guard: existingGuard,
		map_result: "accepted",
		metric_points_used: enu,
		map_projected_ring: view.collection.features[0].geometry.coordinates[0],
		edge_lengths_m: edges,
		expected_analytic_edge_m: 20,
		unchanged_input: JSON.stringify(geometry) === before,
	},
};
process.stdout.write(JSON.stringify(report, null, 2) + "\n");
