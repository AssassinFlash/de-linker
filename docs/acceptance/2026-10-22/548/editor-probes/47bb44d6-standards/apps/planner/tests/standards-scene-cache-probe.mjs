import test from 'node:test';import assert from 'node:assert/strict';import {readFile} from 'node:fs/promises';
import {loadSceneModule} from '../src/data/sceneModule.ts';
test('rejected module evicts pending, explicit retry changes identity, inflight and success are reused',async()=>{
 globalThis.__standardsSceneEvaluations=[];let release;globalThis.__standardsSceneGate=new Promise(r=>release=r);
 const directory=new URL('../../../plugins/linker-tools/build/planner/',import.meta.url);
 const manifest=JSON.parse(await readFile(new URL('vite-manifest.json',directory),'utf8'));
 const nativeUrl=new URL(manifest['src/components/design/SceneViewport.tsx'].file,directory).href;
 const first=loadSceneModule(nativeUrl),parallel=loadSceneModule(nativeUrl);assert.equal(first,parallel);
 await assert.rejects(first,/synthetic_cached_module_failure/);
 const retry=loadSceneModule(nativeUrl);assert.notEqual(first,retry);assert.equal(loadSceneModule(nativeUrl),retry);
 release();const value=await retry;assert.equal(typeof value.default,'function');assert.equal(loadSceneModule(nativeUrl),retry);
 assert.equal(globalThis.__standardsSceneEvaluations.length,2);assert.equal(new URL(globalThis.__standardsSceneEvaluations[0]).search,'');
 assert.equal(globalThis.__standardsSceneEvaluations[1],nativeUrl+'?planner_retry=1');
 const missing=loadSceneModule(null);await assert.rejects(missing,/synthetic_cached_module_failure/);await assert.rejects(loadSceneModule(null),/scene_module_url_missing/);
 assert.equal(globalThis.__standardsSceneEvaluations.length,2);
 console.log(JSON.stringify({evaluated:globalThis.__standardsSceneEvaluations,pendingIdentityReused:true,successfulPromiseReused:true,missingMetadataInventedNoURL:true}));
 delete globalThis.__standardsSceneGate;delete globalThis.__standardsSceneEvaluations;
});
