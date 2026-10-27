// Final independent actual-adapter regression probe. Reuses the previous owned
// Map/JSDOM fixture in memory; preserves historical failing evidence verbatim.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {execFileSync} from "node:child_process";
import {createHash} from "node:crypto";
import {fileURLToPath} from "node:url";
const rootUrl=new URL("../../../../../../",import.meta.url),root=fileURLToPath(rootUrl);
const pin="71cd719aa67021aee6398ae58f359738005d1f57",base="66324a39fb449425dd1144b46b4d3abc21dc52d0";
const git=(...args)=>execFileSync("git",args,{cwd:root,maxBuffer:8*1024*1024});
const read=path=>readFileSync(new URL(path,rootUrl));
const sha=bytes=>createHash("sha256").update(bytes).digest("hex");
const manifest=JSON.parse(read("plugins/linker-tools/build/planner/source-manifest.json"));
for(const [path,hash]of Object.entries(manifest.sources)){assert.equal(sha(read("apps/planner/"+path)),hash,path);assert.deepEqual(read("apps/planner/"+path),git("show",pin+":apps/planner/"+path),path);}
assert.equal(git("diff","--name-only",pin,"--","apps/planner").toString(),"");
const oldManifest=JSON.parse(git("show",base+":plugins/linker-tools/build/planner/source-manifest.json"));
assert.deepEqual(manifest.build,oldManifest.build);
for(const[path,hash]of Object.entries(manifest.build))assert.equal(sha(read("plugins/linker-tools/build/planner/"+path)),hash,path);
const {JSDOM}=await import(new URL("apps/planner/node_modules/jsdom/lib/api.js",rootUrl));
const {createMapDrawingController}=await import(new URL("apps/planner/src/data/MapDrawingController.ts",rootUrl));
const oldPath="docs/acceptance/2026-10-24/548/map-drawing/review-spec-c562676a/probe.mjs",old=read(oldPath).toString();
const start=old.indexOf("function fixture(){"),end=old.indexOf("\ntry{",start);
assert.ok(start>=0&&end>start);
const fixture=new Function("JSDOM","createMapDrawingController",old.slice(start,end)+"\nreturn fixture;")(JSDOM,createMapDrawingController);
const previousRaf=globalThis.requestAnimationFrame,previousCancel=globalThis.cancelAnimationFrame;
const records=[];
const messages=error=>[error.message,...(error.errors??[]).flatMap(messages)];
function drag(f){f.event("pointerdown",0,0);f.event("pointermove",-20,0);f.event("pointermove",-40,0);}
try{
	const good=fixture();drag(good);good.event("pointerup",-75.1234,12.1234);await Promise.resolve();
	assert.equal(good.transactions.length,1);assert.equal(good.errors.length,0);assert.equal(good.failures.length,0);
	const ring=good.transactions[0].steps[0].geometry.coordinates[0];assert.deepEqual(ring,[[ -.000751234,-.000121234],[.002,0],[.002,-.002],[-.000751234,-.000121234]]);
	good.controller.dispose();assert.equal(good.layers.size,0);assert.equal(good.sources.size,0);
	records.push({case:"actual-adapter endpoint/closure positive",transactions:good.transactions,unchanged_other_vertices:true,removed_sources:3,removed_layers:5,uncaught_errors:good.errors});good.cleanup();
	for(const reason of["blur interruption","invalid endpoint failure","public owner disposal"]){
		const f=fixture();drag(f);const raw=JSON.stringify(f.raw.at(-1));assert.ok(raw);f.refuse();
		if(reason==="blur interruption")f.dom.window.dispatchEvent(new f.dom.window.Event("blur"));
		if(reason==="invalid endpoint failure")f.event("pointerup",NaN,0);
		if(reason==="public owner disposal")f.controller.dispose();
		f.map.remove();await Promise.resolve();
		assert.equal(f.ownerRemoved,true);assert.equal(f.transactions.length,0);assert.equal(f.interruptions,0);assert.equal(f.failures.length,1);assert.equal(f.errors.length,0);
		assert.equal(JSON.stringify(f.raw.at(-1)),raw);assert.equal(f.map.dragPan.isEnabled(),true);assert.equal(f.map.dragRotate.isEnabled(),false);assert.equal(f.map.doubleClickZoom.isEnabled(),true);assert.equal(f.canvas.style.cursor,"crosshair");
		f.controller.dispose();f.dom.window.dispatchEvent(new f.dom.window.Event("blur"));await Promise.resolve();assert.equal(f.failures.length,1);
		records.push({case:reason,failed_callbacks:f.failures,interrupted_callbacks:f.interruptions,uncaught_errors:f.errors,owner_remove_reached:f.ownerRemoved,transactions:f.transactions.length,prior_raw_unchanged:true,handlers_and_cursor_restored:true,late_callbacks_duplicated:false});f.cleanup();
	}
	const normal=fixture();drag(normal);const saved=JSON.stringify(normal.raw.at(-1));normal.dom.window.dispatchEvent(new normal.dom.window.Event("blur"));await Promise.resolve();assert.equal(normal.interruptions,1);assert.equal(normal.failures.length,0);assert.equal(normal.errors.length,0);assert.equal(JSON.stringify(normal.raw.at(-1)),saved);records.push({case:"normal cancellation",interrupted_callbacks:normal.interruptions,failed_callbacks:normal.failures,prior_raw_unchanged:true,transactions:normal.transactions.length});normal.cleanup();
	const partial=fixture();partial.map.dragPan.disable();partial.map.dragPan.enable=()=>{throw new Error("synthetic_pan_restore_refusal");};partial.map.dragRotate.enable();partial.map.doubleClickZoom.disable();partial.canvas.style.cursor="move";partial.controller.dispose();partial.map.remove();assert.equal(partial.failures.length,1);assert.equal(partial.errors.length,0);assert.equal(partial.ownerRemoved,true);assert.equal(partial.map.dragRotate.isEnabled(),false);assert.equal(partial.map.doubleClickZoom.isEnabled(),true);assert.equal(partial.canvas.style.cursor,"crosshair");records.push({case:"one handler refuses",failed_callbacks:partial.failures,other_handlers_and_cursor_restored:true,owner_remove_reached:true,uncaught_errors:partial.errors});partial.cleanup();
	const init=fixture();init.controller.dispose();init.refuse();const shape={kind:"edit",ring:[[0,0],[0,0],[1,1]]},snapshot=JSON.stringify(shape);let causes=[];
	try{createMapDrawingController(init.map,shape,{raw(){},transaction(){throw new Error("No commit");},interrupted(){throw new Error("No asynchronous terminal");},failed(){throw new Error("No asynchronous terminal");},blockMapPick(){}});assert.fail("Expected construction refusal");}catch(error){causes=messages(error);assert.ok(causes.includes("map_drawing_initialization_failed"));assert.ok(causes.includes("map_vertex_identity_ambiguous"));assert.ok(causes.includes("synthetic_remove_layer_refusal"));}
	assert.equal(JSON.stringify(shape),snapshot);init.map.remove();assert.equal(init.ownerRemoved,true);records.push({case:"construction and cleanup both fail",causes,original_shape_unchanged:true,owner_remove_reached:true});init.cleanup();
}finally{if(previousRaf)globalThis.requestAnimationFrame=previousRaf;else delete globalThis.requestAnimationFrame;if(previousCancel)globalThis.cancelAnimationFrame=previousCancel;else delete globalThis.cancelAnimationFrame;}
process.stdout.write(JSON.stringify({pin,base,diff:`git diff ${base}...${pin}`,commits:git("log",`${base}..${pin}`,"--oneline").toString().trim().split("\n"),source_hashes_checked:Object.keys(manifest.sources).length,unchanged_emitted_artifacts:Object.keys(manifest.build).length,controller_sha256:sha(read("apps/planner/src/data/MapDrawingController.ts")),reused_fixture_path:oldPath,reused_fixture_sha256:sha(read(oldPath)),packages:{"terra-draw":JSON.parse(read("apps/planner/node_modules/terra-draw/package.json")).version,"terra-draw-maplibre-gl-adapter":JSON.parse(read("apps/planner/node_modules/terra-draw-maplibre-gl-adapter/package.json")).version},records,evidence_limit:"Actual installed library/adapter through DOM and a narrow Map port. No native WebGL, provider, browser recovery, complete drawing UI, touch or production acceptance."},null,2)+"\n");
