// Final bounded read-only equivalence/counterexample probe. No source copy,
// install, build, browser action, service, or network is performed.
import assert from "node:assert/strict";
import {readFileSync,statfsSync} from "node:fs";
import {execFileSync} from "node:child_process";
import {createHash} from "node:crypto";
import {fileURLToPath} from "node:url";
const rootUrl=new URL("../../../../../../",import.meta.url),root=fileURLToPath(rootUrl);
const prior="81cd1c5b1a7d5ff5592131602c12d642d13c162b",pin="5c693115d345a676d7a737bdfb886597b74fbe80";
const git=(...args)=>execFileSync("git",args,{cwd:root,stdio:["ignore","pipe","pipe"],maxBuffer:8*1024*1024});
const sha=(bytes)=>createHash("sha256").update(bytes).digest("hex");
const read=(path)=>readFileSync(new URL(path,rootUrl));
const json=(path)=>JSON.parse(read(path));
const object=(ref,path)=>git("show",`${ref}:${path}`);
const file="plugins/linker-tools/build/planner/source-manifest.json";
const oldManifest=JSON.parse(object(prior,file)),manifest=JSON.parse(object(pin,file));
assert.deepEqual(read(file),object(pin,file));
const sourceRows=[];
for(const [path,hash] of Object.entries(manifest.sources)){
	const bytes=read(`apps/planner/${path}`);
	assert.equal(sha(bytes),hash,path);
	assert.deepEqual(bytes,object(pin,`apps/planner/${path}`),path);
	if(path.startsWith("src/"))assert.deepEqual(bytes,object(prior,`apps/planner/${path}`),path);
	sourceRows.push({path,sha256:hash,unchanged_runtime:path.startsWith("src/")});
}
const tracked=git("ls-tree","-r","--name-only",pin,"apps/planner/src/").toString().trim().split("\n");
for(const path of tracked)assert.deepEqual(object(pin,path),object(prior,path),path);
const builds=[];
assert.deepEqual(manifest.build,oldManifest.build);
for(const [path,hash] of Object.entries(manifest.build)){
	const full=`plugins/linker-tools/build/planner/${path}`,bytes=read(full);
	assert.equal(sha(bytes),hash,path);
	assert.deepEqual(bytes,object(pin,full),path);
	assert.deepEqual(bytes,object(prior,full),path);
	builds.push({path,sha256:hash,unchanged:true});
}
const before=JSON.parse(object(prior,"apps/planner/package-lock.json")),after=json("apps/planner/package-lock.json");
assert.deepEqual(read("apps/planner/package-lock.json"),object(pin,"apps/planner/package-lock.json"));
const changedUrls=[];
function lockCompare(a,b,path=[]){
	if(a&&typeof a==="object"){
		assert.deepEqual(Object.keys(a),Object.keys(b),path.join("/"));
		for(const key of Object.keys(a))lockCompare(a[key],b[key],[...path,key]);
	}else if(a!==b){
		assert.equal(path.at(-1),"resolved",path.join("/"));
		const oldUrl=new URL(a),newUrl=new URL(b);
		assert.equal(oldUrl.hostname,"registry.npmmirror.com");
		assert.equal(newUrl.hostname,"registry.npmjs.org");
		oldUrl.hostname=newUrl.hostname;
		assert.equal(oldUrl.href,newUrl.href);
		changedUrls.push(path.join("/"));
	}
}
lockCompare(before,after);assert.equal(changedUrls.length,189);
assert.equal(read("apps/planner/.npmrc").toString().trim().split("\n").at(-1),"replace-registry-host=always");
assert.equal(sha(read("apps/planner/.npmrc")),manifest.sources[".npmrc"]);
const specs=["548-map-display.md","548-design-geometry.md","548-product-identity.md","548-workbench-application.md"];
for(const spec of specs)assert.deepEqual(object(pin,`docs/specs/${spec}`),object(prior,`docs/specs/${spec}`));
const {readGeometry}=await import(new URL("apps/planner/src/domain/validateGeometry.ts",rootUrl));
const {geographicMapGeometry}=await import(new URL("apps/planner/src/domain/mapGeometry.ts",rootUrl));
const original=json("docs/acceptance/2026-10-22/548/map-display/review-spec-f40db1d6/probe.json").numerical_support.fixture;
const checked=readGeometry(original,json("apps/planner/src/contracts/geometry-policy.json")),input=JSON.stringify(checked);
assert.throws(()=>geographicMapGeometry(checked),/geometry_numeric_resolution_unsupported/);
assert.equal(JSON.stringify(checked),input);
const base="docs/acceptance/2026-10-22/548/map-display/system-identity/native/",entry=manifest.build["assets/planner.js"],native=[];
for(const name of ["de-desktop-system-about-open","en-desktop-system-about-framed","de-phone-system-about-framed","en-phone-system-about-framed","en-desktop-list-system-about-framed"]){
	const path=base+name,record=json(path+".json"),png=read(path+".png"),state=record.after;
	const dimensions=[png.readUInt32BE(16),png.readUInt32BE(20)];
	assert.deepEqual(dimensions,state.viewport);
	assert.deepEqual(state.widths,[state.viewport[0],state.viewport[0]]);
	assert.deepEqual(record.before.fields,state.fields);
	assert.deepEqual(record.before.scroll,state.scroll);
	assert.equal(state.fonts,"loaded");assert.equal(state.details,true);
	assert.equal(state.links.length,10);
	assert.ok(state.entry[0].endsWith(`?ver=${entry}`));
	assert.ok(state.identityBox.top>=0&&state.identityBox.bottom<=state.viewport[1]);
	native.push({name,dimensions,fields:state.fields.length,revision:state.revision??null,fonts:state.fonts,credit_links:state.links.length,entry_sha256:entry,fully_framed:true,json_sha256:sha(read(path+".json")),png_sha256:sha(png)});
}
const keyboard=json(base+"de-desktop-keyboard-toggle.json"),workspaces=json(base+"native-all-workspaces.json"),reopen=json(base+"native-project-reopen.json");
assert.ok(keyboard.fieldsUnchanged&&keyboard.keyboardReopened&&keyboard.requests.length===0);
assert.equal(keyboard.beforeRevision,keyboard.afterRevision);
assert.deepEqual(workspaces.states.map(s=>s.workspace),["site","energy","design","overview"]);
assert.ok(workspaces.states.every(s=>s.identityCount===1&&s.revision==="Gespeichert · Version 3"));
assert.equal(reopen.identityCount,1);assert.equal(reopen.fields.length,11);assert.equal(reopen.revision,"Saved · revision 3");
const research="docs/research/2026-10-23-map-workbench-integration/registry-canonicalization/";
const run=json(research+"run.json"),verification=json(research+"verification.json"),rawRecords=json(research+"apify-results.json");
assert.equal(run.status,"SUCCEEDED");
for(const name of ["maplibre-gl","terra-draw","terra-draw-maplibre-gl-adapter"]){
	const metadata=json(research+name+".json"),locked=after.packages["node_modules/"+name],v=verification.packages.find(p=>p.name===name);
	assert.equal(v.http_status,200);assert.equal(v.sha256,sha(read(research+name+".json")));
	const raw=rawRecords.find(record=>record.url===v.url);
	assert.equal(raw.crawl.httpStatusCode,200);assert.equal(raw.crawl.contentType,"application/json");assert.ok(raw.fileUrl);
	assert.equal(metadata.version,locked.version);assert.equal(metadata.dist.integrity,locked.integrity);assert.equal(metadata.dist.tarball,locked.resolved);
}
const disk=statfsSync(root);
process.stdout.write(JSON.stringify({pin,prior,head:git("rev-parse","HEAD").toString().trim(),diff:`git diff be5711bf...${pin}`,commits:git("log",`be5711bf..${pin}`,"--oneline").toString().trim().split("\n"),source_count:sourceRows.length,runtime_source_count:sourceRows.filter(s=>s.unchanged_runtime).length,tracked_src_including_tests_unchanged:tracked.length,source_hashes:sourceRows,unchanged_builds:builds,lock_urls_changed:changedUrls.length,lock_changes_only_canonical_host:true,specs_unchanged:specs,original_counterexample:{wire:"accepted",map:"geometry_numeric_resolution_unsupported",input_unchanged:true},inspected_native_pairs:native,keyboard_record:keyboard,workspace_record:workspaces,reopen:{url:reopen.url,fields:reopen.fields.length,revision:reopen.revision},npm_acquisition:{terminal_status:run.status,status_message:run.statusMessage,record_http_statuses:verification.packages.map(p=>p.http_status),evidence_limit:"HTTP200 downloaded JSON records; terminal crawl counter reports 0 successes and 3 failures, not an error-free crawl."},native_evidence_limit:"Stored JSON/PNG inspection only. No fresh browser acceptance; worker packet trace, complete map matrix, withdrawal/failure/gestures and full-goal/release gates remain open.",resources_created:{source_copy:0,dependency_copy:0,worktree:0,instance:0,backup:0,network_request:0},disk_free_bytes:disk.bavail*disk.bsize},null,2)+"\n");
