// Independent review probe; reads the existing checkout and original counterexample.
// No source/dependency copy, service, external request, or build write is used.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
const rootUrl = new URL("../../../../../../", import.meta.url);
const root = fileURLToPath(rootUrl);
const pin = "81cd1c5b1a7d5ff5592131602c12d642d13c162b";
const git = (...args) => execFileSync("git", args, {cwd:root,stdio:["ignore","pipe","pipe"],maxBuffer:8*1024*1024});
const sha = (data) => createHash("sha256").update(data).digest("hex");
const relevant = git("ls-files").toString().split("\n").filter((path) => /^(apps\/planner\/|plugins\/linker-tools\/(build\/planner\/|includes\/Planner\/|languages\/)|plugins\/linker-commerce\/content\/windpress\/|tools\/local\/)/.test(path));
const hashes = [];
for (const path of relevant) {
	const bytes = readFileSync(new URL(path, rootUrl));
	assert.deepEqual(bytes, git("show",`${pin}:${path}`), path);
	hashes.push({path,sha256:sha(bytes)});
}
const domain = (name) => import(new URL(`apps/planner/src/domain/${name}.ts`, rootUrl));
const {readGeometry} = await domain("validateGeometry");
const {geographicMapGeometry} = await domain("mapGeometry");
const {GeographicBridge} = await domain("geographic");
const {numberResolution} = await domain("geometryNumerics");
const policy = JSON.parse(readFileSync(new URL("apps/planner/src/contracts/geometry-policy.json",rootUrl)));
const numeric = JSON.parse(readFileSync(new URL("apps/planner/src/contracts/geometry-numerics.json",rootUrl)));
const original = JSON.parse(readFileSync(new URL("../review-spec-f40db1d6/probe.json", import.meta.url))).numerical_support.fixture;
const flat = JSON.parse(readFileSync(new URL("fixtures/planning/geometry-flat.json",rootUrl)));
const base = {...flat,arrays:[],coordinate_system:structuredClone(original.coordinate_system)};
const far = original.roofs[0].boundary_uv;
const object = {id:"review-opaque-object",name:"Synthetic numerical probe",roof_id:"roof",source_id:"survey",footprint_uv:far};
const cases = {
	"original cancelling-origin roof":original,
	"unsupported opening":{...base,roofs:[{...base.roofs[0],holes_uv:[far]}]},
	"obstacle chart":{...base,obstacles:[{...object,extrusion_axis_enu:[0,0,1],height_m:2}]},
	"keepout chart":{...base,keepouts:[{...object,reason:"Synthetic numerical boundary"}]},
	"module UV chart":{...base,arrays:[{...flat.arrays[0],origin_uv:[1e14,1e14]}]},
	"module normal coordinate":{...base,arrays:[{...flat.arrays[0],lower_edge_clearance_m:1e14}]},
	"ENU before inverse":{...base,roofs:[{...base.roofs[0],origin_enu:[1e14,0,4]}]},
	"obstacle top":{...base,obstacles:[{...object,footprint_uv:base.roofs[0].boundary_uv,extrusion_axis_enu:[0,0,1],height_m:1e14}]},
};
const outcomes = [];
const inverse = GeographicBridge.prototype.inverse;
let visits = [];
GeographicBridge.prototype.inverse = function(point) {
	visits.push([...point]);
	assert.ok(point.every((v) => numberResolution(v) <= numeric.max_uv_resolution_m),"unsupported ENU reached inverse");
	return inverse.call(this,point);
};
try {
	for (const [name,value] of Object.entries(cases)) {
		const input = readGeometry(structuredClone(value),policy),before=JSON.stringify(input);
		visits=[];
		let refusal=null;
		try {geographicMapGeometry(input);} catch(error) {refusal=error.message;}
		assert.equal(refusal,"geometry_numeric_resolution_unsupported",name);
		assert.equal(JSON.stringify(input),before,name);
		if (name === "original cancelling-origin roof" || name === "ENU before inverse") assert.equal(visits.length,0,name);
		outcomes.push({name,wire:"accepted",map:refusal,unchanged:true,inverse_calls_before_refusal:visits.length,unsupported_enu_reached_inverse:false});
	}
	const offset=1e6, d=Math.SQRT1_2;
	const supported=structuredClone(original);
	Object.assign(supported.roofs[0],{origin_enu:[0,-2*d*offset,4],boundary_uv:[[offset,offset],[offset+20,offset],[offset+20,offset+20],[offset,offset+20]]});
	const accepted=readGeometry(supported,policy),before=JSON.stringify(accepted);
	visits=[];
	const view=geographicMapGeometry(accepted);
	assert.equal(view.collection.features.length,1);
	assert.equal(JSON.stringify(accepted),before);
	outcomes.push({name:"supported 1e6 chart with cancelling origin",wire:"accepted",map:"accepted",unchanged:true,inverse_calls:visits.length,bounds:view.bounds});
} finally {GeographicBridge.prototype.inverse=inverse;}
const manifest=JSON.parse(readFileSync(new URL("plugins/linker-tools/build/planner/source-manifest.json",rootUrl)));
process.stdout.write(JSON.stringify({pin,head:git("rev-parse","HEAD").toString().trim(),diff:`git diff be5711bf...${pin}`,commits:git("log",`be5711bf..${pin}`,"--oneline").toString().trim().split("\n"),verified_files:hashes,build_hashes:manifest.build,numeric_budget_m:numeric.max_uv_resolution_m,outcomes},null,2)+"\n");
