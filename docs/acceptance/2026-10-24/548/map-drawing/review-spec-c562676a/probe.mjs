// Real installed Terra Draw 1.35.0 and MapLibre adapter 1.4.1 with a narrow
// JSDOM/Map API port. No replacement mode/store, WebGL, network or stack.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {execFileSync} from "node:child_process";
import {createHash} from "node:crypto";
import {fileURLToPath} from "node:url";
const rootUrl=new URL("../../../../../../",import.meta.url),root=fileURLToPath(rootUrl);
const pin="c562676a2af2a73864d75c34b79d7b8db357ed63";
const git=(...args)=>execFileSync("git",args,{cwd:root,maxBuffer:8*1024*1024});
const read=(path)=>readFileSync(new URL(path,rootUrl));
const sha=(bytes)=>createHash("sha256").update(bytes).digest("hex");
const manifest=JSON.parse(read("plugins/linker-tools/build/planner/source-manifest.json"));
for(const [path,hash] of Object.entries(manifest.sources)){
	assert.equal(sha(read("apps/planner/"+path)),hash,path);
	assert.deepEqual(read("apps/planner/"+path),git("show",pin+":apps/planner/"+path),path);
}
const {JSDOM}=await import(new URL("apps/planner/node_modules/jsdom/lib/api.js",rootUrl));
const {createMapDrawingController}=await import(new URL("apps/planner/src/data/MapDrawingController.ts",rootUrl));
const previousRaf=globalThis.requestAnimationFrame,previousCancel=globalThis.cancelAnimationFrame;
const records=[];
function fixture(){
	const dom=new JSDOM("<!doctype html><div><canvas></canvas></div>",{pretendToBeVisual:true}),canvas=dom.window.document.querySelector("canvas"),container=canvas.parentElement;
	globalThis.requestAnimationFrame=dom.window.requestAnimationFrame.bind(dom.window);
	globalThis.cancelAnimationFrame=dom.window.cancelAnimationFrame.bind(dom.window);
	const errors=[],transactions=[],raw=[],failures=[];let interruptions=0,refuseRemoval=false,ownerRemoved=false;
	dom.window.addEventListener("error",event=>{errors.push(event.error?.message??event.message);event.preventDefault();});
	const toggle=(initial)=>({enabled:initial,isEnabled(){return this.enabled;},enable(){this.enabled=true;},disable(){this.enabled=false;}});
	const sources=new Map(),layers=new Map();
	const map={version:"5.24.0",getCanvas:()=>canvas,getContainer:()=>container,dragPan:toggle(true),dragRotate:toggle(false),doubleClickZoom:toggle(true),project:({lng,lat})=>({x:lng*1e5,y:-lat*1e5}),unproject:({x,y})=>({lng:x/1e5,lat:-y/1e5}),
		addSource(id,value){sources.set(id,{...value,setData(data){this.data=data;}});},getSource(id){return sources.get(id);},removeSource(id){sources.delete(id);},addLayer(value){layers.set(value.id,value);},getLayer(id){return layers.get(id);},removeLayer(id){if(refuseRemoval)throw new Error("synthetic_remove_layer_refusal");layers.delete(id);},remove(){ownerRemoved=true;}};
	canvas.style.cursor="crosshair";
	const controller=createMapDrawingController(map,{kind:"edit",ring:[[0,0],[.002,0],[.002,-.002]]},{raw:value=>raw.push(value),transaction:value=>transactions.push(value),interrupted(){interruptions++;},failed:error=>failures.push(error.message),blockMapPick(){}});
	function event(type,x,y){const e=new dom.window.Event(type,{bubbles:true,cancelable:true});Object.assign(e,{pointerId:1,isPrimary:true,clientX:x,clientY:y,button:0});canvas.dispatchEvent(e);}
	return {dom,canvas,controller,map,sources,layers,errors,transactions,raw,failures,event,refuse(){refuseRemoval=true;},get interruptions(){return interruptions;},get ownerRemoved(){return ownerRemoved;},cleanup(){refuseRemoval=false;try{controller.dispose();}catch{}dom.window.close();}};
}
try{
	// Positive control: actual adapter DOM drag honours release != last move.
	const good=fixture();good.event("pointerdown",0,0);good.event("pointermove",-20,0);good.event("pointermove",-40,0);good.event("pointerup",-75.1234,12.1234);await Promise.resolve();
	assert.equal(good.transactions.length,1);assert.equal(good.failures.length,0);assert.equal(good.errors.length,0);
	assert.ok(good.transactions[0].steps[0].geometry.coordinates[0].some(p=>p[0]===-.000751234&&p[1]===-.000121234));good.controller.dispose();assert.equal(good.sources.size,0);assert.equal(good.layers.size,0);
	records.push({case:"actual-adapter positive endpoint control",transactions:good.transactions,remaining_sources:good.sources.size,remaining_layers:good.layers.size,errors:good.errors});good.cleanup();
	for(const reason of ["blur interruption","invalid endpoint failure","public owner disposal"]){
		const f=fixture();f.event("pointerdown",0,0);f.event("pointermove",-20,0);f.event("pointermove",-40,0);assert.ok(f.raw.length);const retained=JSON.stringify(f.raw.at(-1));f.refuse();let thrown=null;
		if(reason==="blur interruption")f.dom.window.dispatchEvent(new f.dom.window.Event("blur"));
		if(reason==="invalid endpoint failure")f.event("pointerup",NaN,0);
		if(reason==="public owner disposal")try{f.controller.dispose();f.map.remove();}catch(error){thrown=error.message;}
		await Promise.resolve();
		assert.equal(f.transactions.length,0);assert.equal(f.interruptions,0);assert.equal(f.failures.length,0);
		assert.equal(JSON.stringify(f.raw.at(-1)),retained);assert.equal(f.map.dragPan.isEnabled(),true);assert.equal(f.map.dragRotate.isEnabled(),false);assert.equal(f.map.doubleClickZoom.isEnabled(),true);assert.equal(f.canvas.style.cursor,"crosshair");
		assert.ok(f.errors.includes("synthetic_remove_layer_refusal")||thrown==="synthetic_remove_layer_refusal");
		records.push({case:reason,terminal_failed_callbacks:f.failures,terminal_interrupted_callbacks:f.interruptions,uncaught_dom_errors:f.errors,escaped_dispose_error:thrown,transactions:f.transactions.length,raw_preserved:true,handlers_and_cursor_restored:true,remaining_sources:f.sources.size,remaining_layers:f.layers.size,owner_remove_reached:f.ownerRemoved});f.cleanup();
	}
}finally{if(previousRaf)globalThis.requestAnimationFrame=previousRaf;else delete globalThis.requestAnimationFrame;if(previousCancel)globalThis.cancelAnimationFrame=previousCancel;else delete globalThis.cancelAnimationFrame;}
const packages={};for(const name of ["terra-draw","terra-draw-maplibre-gl-adapter"]){const p=JSON.parse(read(`apps/planner/node_modules/${name}/package.json`));packages[name]={version:p.version};}
process.stdout.write(JSON.stringify({pin,base:"66324a39fb449425dd1144b46b4d3abc21dc52d0",diff:`git diff 66324a39...${pin}`,commits:git("log",`66324a39..${pin}`,"--oneline").toString().trim().split("\n"),source_hashes_checked:Object.keys(manifest.sources).length,controller_sha256:sha(read("apps/planner/src/data/MapDrawingController.ts")),packages,records,evidence_limit:"Real library and actual adapter with DOM/Map port plus injected removeLayer failure. Not native WebGL/touch/provider/full drawing acceptance; owner cleanup sequence is an illustrative consumer, not a mounted application path."},null,2)+"\n");
