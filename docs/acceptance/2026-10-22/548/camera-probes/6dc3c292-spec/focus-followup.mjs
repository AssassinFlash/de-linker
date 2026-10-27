import assert from 'node:assert/strict';
import test from 'node:test';
import React,{act} from 'react';
import {readFileSync} from 'node:fs';
import {IDBFactory} from 'fake-indexeddb';
import {setupDom,until,deferred,enter} from './dom-fixture.mjs';
import {PlannerClient} from '../src/data/PlannerClient.ts';
import {GeometryImportStore} from '../src/data/GeometryImportStore.ts';
import {GeometryIntake} from '../src/components/design/GeometryIntake.tsx';
import {emptyGeometry} from '../src/domain/geometryCommands.ts';
import {revealActionResult} from '../src/components/revealActionResult.ts';

const asset=JSON.parse(readFileSync(new URL('../../../fixtures/planning/geometry-import-asset.json',import.meta.url),'utf8'));
const source=readFileSync(new URL('../../../fixtures/planning/source-roof-wgs84.geojson',import.meta.url));
const scope='a'.repeat(64),session={schema_version:1,kind:'guest',cookie_confirmed:true,expires_at:2000000000,query_scope:scope,nonce:'abcdefghij',claim_pending:false,runtime:{schema_version:1,runtime_sha256:'4'.repeat(64),models:{},limits:{max_body_bytes:16777216,max_csv_bytes:4194304,max_page_size:20,max_json_depth:32}}};
const button=text=>[...document.querySelectorAll('button')].find(el=>el.textContent.trim()===text);
async function click(text){const b=button(text);assert.ok(b,text);assert.equal(b.disabled,false);await act(async()=>b.click());}
const json=value=>new Response(JSON.stringify(value),{status:200,headers:{'Content-Type':'application/json'}});

async function rig(t){
 const dom=setupDom(),prior=Object.getOwnPropertyDescriptor(globalThis,'indexedDB');Object.defineProperty(globalThis,'indexedDB',{value:new IDBFactory(),configurable:true});
 const journal=new GeometryImportStore();let gate=null,reads=0,completed=0,owner=session;const attachments=[],uploads=[];
 const store={async list(...args){reads++;if(gate)await gate.promise;const rows=await journal.list(...args);completed++;return rows;},write:journal.write.bind(journal),clear:journal.clear.bind(journal),acknowledge:journal.acknowledge.bind(journal)};
 const client=new PlannerClient({baseUrl:location.origin+'/rpc/',nonceUrl:location.origin+'/nonce',origin:location.origin,fetch:async(url,init)=>{const p=new URL(url).pathname;if(p==='/nonce')return new Response('abcdefghij');if(p.endsWith('/bootstrap'))return json(owner);if(p.endsWith('/geometry/import')){uploads.push(init.body);assert.equal((await journal.list([scope],asset.project_id))[0].body,init.body);return json(asset);}throw new Error(p);}});
 await client.bootstrap();const {createRoot}=await import('react-dom/client'),root=createRoot(dom.element);let props={geometry:emptyGeometry(),projectId:asset.project_id,session,client,locale:'de-DE',disabled:false,recheck(){},onActivity(){},currentAssetIds:[],confirmedAssetIds:[],recoveryScopes:[scope],store,attach(before,prepared){attachments.push({before,prepared});return true;}};
 async function render(changes={}){props={...props,...changes};await act(async()=>root.render(React.createElement(GeometryIntake,props)));}
 t.after(async()=>{await dom.dispose(root);if(prior)Object.defineProperty(globalThis,'indexedDB',prior);else delete globalThis.indexedDB;});await render();await until(()=>button('Import roof geometry')?.disabled===false);
 return{dom,journal,client,render,attachments,uploads,get reads(){return reads;},get completed(){return completed;},hold(value){gate=value;},async revoke(){owner={...session,query_scope:'b'.repeat(64)};await client.bootstrap();await render();}};
}

for(const outcome of ['resolved','rejected','revoked'])test('independent actual IDB Close waits for recovery read: '+outcome,async t=>{
 const app=await rig(t);await click('Import roof geometry');await until(()=>app.completed>=2);const gate=deferred();app.hold(gate);button('Close import').focus();await click('Close import');await until(()=>button('Import roof geometry').disabled);assert.notEqual(document.activeElement,button('Import roof geometry'));
 if(outcome==='revoked')await app.revoke();await act(async()=>outcome==='rejected'?gate.reject(new Error('independent read refusal')):gate.resolve());
 if(outcome==='revoked'){await until(()=>button('Import roof geometry')===undefined);assert.equal(document.activeElement,document.body);}else{await until(()=>button('Import roof geometry').disabled===false);assert.equal(document.activeElement,button('Import roof geometry'));if(outcome==='rejected')assert.ok(document.body.textContent.includes('Browser recovery could not be read or updated.'));}
 assert.equal(app.uploads.length,0);assert.equal(app.attachments.length,0);console.log(JSON.stringify({case:'close-focus-recovery',outcome,reads:app.reads,focus:document.activeElement.tagName}));
});

test('independent actual IDB Add waits for recovery completion and never steals focus onto a disabled trigger',async t=>{
 const app=await rig(t),body=JSON.stringify({schema_version:1,project_id:asset.project_id,content_base64:source.toString('base64'),options:asset.metadata.geometry_import_options,key:crypto.randomUUID()});await app.journal.write(scope,body);await app.render({confirmedAssetIds:['f'.repeat(32)]});await until(()=>button(asset.metadata.geometry_import_options.source.label));await click(asset.metadata.geometry_import_options.source.label);await click('Check or retry this upload');await until(()=>button('Add roof to current design')?.disabled===false);const completed=app.completed;await until(()=>app.completed>completed||button('Add roof to current design'));
 const gate=deferred();app.hold(gate);button('Add roof to current design').focus();await click('Add roof to current design');assert.equal(app.attachments.length,1);await until(()=>button('Import roof geometry').disabled);assert.notEqual(document.activeElement,button('Import roof geometry'));assert.deepEqual(app.uploads,[body]);await act(async()=>gate.resolve());await until(()=>button('Import roof geometry').disabled===false);assert.equal(document.activeElement,button('Import roof geometry'));assert.equal(app.attachments[0].prepared.geometry.roofs[0].holes_uv.length,1);
});

test('independent invalid raw locale field retains focus while revealing its semantic label; scope veto stays inert',async t=>{
 const app=await rig(t);await click('Import roof geometry');const file=document.querySelector('input[type=file]');Object.defineProperty(file,'files',{value:[{name:'owned-independent.geojson',size:source.length,arrayBuffer:async()=>Uint8Array.from(source).buffer}]});await act(async()=>file.dispatchEvent(new window.Event('change',{bubbles:true})));await until(()=>!button('Continue').disabled);await click('Continue');for(const[name,value]of[['pitch','1.'],['bearing','180'],['height','5'],['basis','Independent measured plane']])await enter(document.querySelector(`[name=${name}]`),value);
 const scrolled=[],scrollPrototype=window.HTMLElement.prototype,original=scrollPrototype.scrollIntoView;scrollPrototype.scrollIntoView=function(){scrolled.push(this);};t.after(()=>{scrollPrototype.scrollIntoView=original;});await click('Continue');const pitch=document.querySelector('[name=pitch]');await until(()=>document.activeElement===pitch);assert.equal(pitch.value,'1.');assert.equal(scrolled.at(-1),pitch.closest('label'));assert.equal(app.uploads.length,0);
 const focused=document.activeElement,count=scrolled.length;assert.equal(revealActionResult(pitch,()=>false),false);assert.equal(document.activeElement,focused);assert.equal(scrolled.length,count);const detached=document.createElement('input');assert.equal(revealActionResult(detached),false);assert.equal(scrolled.length,count);
 console.log(JSON.stringify({case:'invalid-locale-focus-label',raw:pitch.value,focused:pitch.name,scrolledLabel:scrolled.at(-1).textContent.trim().slice(0,80),nativeStickyClearance:'not claimed'}));
});
