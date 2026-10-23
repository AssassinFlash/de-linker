import assert from 'node:assert/strict';
import test from 'node:test';
import React,{act} from 'react';
import {setupDom,until,deferred} from './dom-fixture.mjs';

test('review: recovery authentication refusal offers a working native retry',async(t)=>{
 const dom=setupDom();history.replaceState(null,'','/workspace/');
 const {createRoot}=await import('react-dom/client');
 const {SessionBoundary}=await import('../src/components/SessionBoundary.tsx');
 const {Workspace}=await import('../src/components/Workspace.tsx');
 const {PlannerClient}=await import('../src/data/PlannerClient.ts');
 const session={schema_version:1,kind:'user',cookie_confirmed:true,expires_at:2000000000,query_scope:'3'.repeat(64),nonce:'abcdefghij',claim_pending:false,runtime:{schema_version:1,runtime_sha256:'4'.repeat(64),models:{},limits:{max_body_bytes:1000000,max_csv_bytes:100000,max_page_size:30,max_json_depth:32}}};
 const json=(body,status=200)=>new Response(JSON.stringify(body),{status,headers:{'Content-Type':'application/json'}});
 const gate=deferred();let bootstraps=0,discoveryCalls=0;
 const client=new PlannerClient({origin:location.origin,baseUrl:location.origin+'/api/',nonceUrl:location.origin+'/nonce',fetch:async(url)=>{
   const path=new URL(url).pathname;
   if(path==='/nonce')return new Response('abcdefghij');
   if(path.endsWith('/bootstrap')){bootstraps++;return json(session)}
   if(path.endsWith('/projects/list'))return json({items:[],next:null});
   if(path.endsWith('/recovery/scopes')){discoveryCalls++;if(discoveryCalls===1){await gate.promise;return json({error:{code:'identity_refused'}},401)}return json({schema_version:1,scopes:[session.query_scope],next:null})}
   assert.fail(path);
 }});
 const store={async readCreations(){return []}};
 const root=createRoot(dom.element);t.after(()=>dom.dispose(root));
 await act(async()=>root.render(React.createElement(SessionBoundary,{client},(confirmed,recheck)=>React.createElement(Workspace,{key:confirmed.query_scope,session:confirmed,client,store,config:{locale:'en-GB',countries:{NO:'Norway'}},recheck}))));
 await until(()=>document.body.textContent.includes('Project workspace'));
 await act(async()=>gate.resolve());
 await until(()=>document.body.textContent.includes('earlier sessions could not be checked'));
 const retry=[...document.querySelectorAll('button')].find(x=>x.textContent==='Try again');assert.ok(retry);
 await act(async()=>retry.click());
 await act(async()=>{await Promise.resolve();await Promise.resolve()});
 console.log(JSON.stringify({bootstraps,discoveryCalls,currentNativeAdmission:client.isCurrentScope(session.query_scope),newProjectDisabled:[...document.querySelectorAll('button')].find(x=>x.textContent==='New project')?.disabled,errorRemains:document.body.textContent.includes('earlier sessions could not be checked')}));
 assert.ok(bootstraps>1,'the native identity must be rechecked after an authentication refusal; refetch cannot use revoked admission');
});
