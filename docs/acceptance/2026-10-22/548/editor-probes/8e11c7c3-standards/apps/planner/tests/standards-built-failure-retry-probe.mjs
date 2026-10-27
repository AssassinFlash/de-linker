import test from 'node:test';import assert from 'node:assert/strict';import {readFile} from 'node:fs/promises';import {JSDOM} from 'jsdom';
test('failed original emitted scene recovers through a fresh identity and the same queried-entry/shared-core graph',async t=>{
 const dom=new JSDOM('<!doctype html><body></body>',{url:'https://fixture.invalid/workspace/'}),previous=new Map();
 for(const name of ['window','document','navigator','location','MutationObserver']){previous.set(name,Object.getOwnPropertyDescriptor(globalThis,name));Object.defineProperty(globalThis,name,{value:dom.window[name],configurable:true});}
 t.after(()=>{dom.window.close();for(const[name,value]of previous){if(value)Object.defineProperty(globalThis,name,value);else delete globalThis[name];}});
 let starts=0;const query=document.querySelectorAll.bind(document);document.querySelectorAll=selector=>{if(selector==='[data-linker-planner]')starts++;return query(selector);};
 const directory=new URL('../../../plugins/linker-tools/build/planner/',import.meta.url),manifest=JSON.parse(await readFile(new URL('vite-manifest.json',directory),'utf8'));
 await import(new URL(manifest['src/main.tsx'].file+'?ver=review-fixed',directory));
 const scene=manifest['src/components/design/SceneViewport.tsx'];
 await assert.rejects(import(new URL(scene.file,directory)),/synthetic_original_scene_download_failed/);
 const retryUrl=new URL(scene.file+'?planner_retry=1',directory);
 const retry=await import(retryUrl);assert.equal(typeof retry.default,'function');assert.equal(await import(retryUrl),retry);assert.equal(starts,1);
 console.log(JSON.stringify({starts,originalFailed:true,freshRetrySucceeded:true,actualBuiltGraph:true,gpu:false}));
});
