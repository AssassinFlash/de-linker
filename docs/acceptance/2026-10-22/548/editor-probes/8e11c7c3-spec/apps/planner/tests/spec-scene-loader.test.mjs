import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
import {loadSceneModule} from '../src/data/sceneModule.ts';
const records=[];function record(x){records.push(x);fs.writeFileSync(new URL('../../../probe_loader.results.json',import.meta.url),JSON.stringify(records,null,2)+'\n')}
const wait=async p=>{for(let i=0;i<200&&!p();i++)await new Promise(r=>setTimeout(r,5));assert.ok(p())};
test('independent: concurrent failures retry fresh URLs, successful and in-flight imports are reused',async()=>{
 const native=new URL('../src/components/design/SceneViewport.tsx',import.meta.url).href;
 const urls=[],resolvers=[];const gates=Array.from({length:3},()=>new Promise(r=>resolvers.push(r)));
 globalThis.__specSceneEvaluate=async url=>{urls.push(url);const index=Number(new URL(url).searchParams.get('planner_retry')??0);await gates[index];if(index<2)throw Object.assign(new Error('controlled-module-failure'),{moduleUrl:url})};
 const first=loadSceneModule(native),sameFirst=loadSceneModule(native);assert.equal(first,sameFirst);const failure1=assert.rejects(first,/controlled-module-failure/);await wait(()=>urls.length===1);resolvers[0]();await failure1;
 const second=loadSceneModule(native),sameSecond=loadSceneModule(native);assert.equal(second,sameSecond);const failure2=assert.rejects(second,/controlled-module-failure/);await wait(()=>urls.length===2);resolvers[1]();await failure2;
 const third=loadSceneModule(native),sameThird=loadSceneModule(native);assert.equal(third,sameThird);await wait(()=>urls.length===3);resolvers[2]();const recovered=await third;assert.equal(typeof recovered.default,'function');assert.equal(loadSceneModule(native),third);assert.equal(await loadSceneModule(native),recovered);
 assert.deepEqual(urls.map(u=>new URL(u).search),['','?planner_retry=1','?planner_retry=2']);record({case:'concurrency_failures_success',requests:urls,firstShared:first===sameFirst,retryShared:second===sameSecond,successPromiseReused:loadSceneModule(native)===third});
});
test('independent: absent native metadata never invents a retry URL',async()=>{
 const before=[];globalThis.__specSceneEvaluate=async url=>{before.push(url);throw new Error('module-fail')};
 // The literal URL is already a cached failed ESM module from the preceding case.
 await assert.rejects(loadSceneModule(null),/controlled-module-failure/);await assert.rejects(loadSceneModule(null),/scene_module_url_missing/);await assert.rejects(loadSceneModule(null),/scene_module_url_missing/);assert.deepEqual(before,[]);record({case:'missing_native_metadata',newModuleEvaluations:0,refusal:'scene_module_url_missing'});
});
