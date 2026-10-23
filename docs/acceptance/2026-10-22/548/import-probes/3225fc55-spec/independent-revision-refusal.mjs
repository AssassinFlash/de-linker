import assert from 'node:assert/strict';
import test from 'node:test';
import React, {act} from 'react';
import {IDBFactory} from 'fake-indexeddb';
import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {setupDom, until} from './dom-fixture.mjs';
import {PlannerClient} from '../src/data/PlannerClient.ts';
import {DraftStore} from '../src/data/DraftStore.ts';
import {useProjectDraft} from '../src/data/useProjectDraft.ts';
import {editDraft} from '../src/domain/draft.ts';

test('independent: real revision transport keeps unknown or wrong-pair intents, releases typed refusal, then saves newer input under a new key', async t => {
  const dom=setupDom(), prior=Object.getOwnPropertyDescriptor(globalThis,'indexedDB');
  Object.defineProperty(globalThis,'indexedDB',{value:new IDBFactory(),configurable:true});
  const {createRoot}=await import('react-dom/client'),root=createRoot(dom.element),cache=new QueryClient(),store=new DraftStore();
  const project={id:'1'.repeat(32),title:'Independent revision refusal',revision:7,input_sha256:'2'.repeat(64),inputs:{note:'Original'}};
  const session={schema_version:1,kind:'guest',cookie_confirmed:true,expires_at:2000000000,query_scope:'3'.repeat(64),nonce:'abcdefghij',claim_pending:false,runtime:{schema_version:1,runtime_sha256:'4'.repeat(64),models:{},limits:{max_body_bytes:16777216,max_csv_bytes:4194304,max_page_size:20,max_json_depth:32}}};
  let failure={status:400,code:'request_failed'},flow;const sent=[];
  const json=(value,status=200)=>new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json'}});
  const client=new PlannerClient({origin:location.origin,baseUrl:location.origin+'/api/',nonceUrl:location.origin+'/nonce',fetch:async(url,init)=>{
    const path=new URL(url).pathname;if(path==='/nonce')return new Response('abcdefghij');if(path.endsWith('/bootstrap'))return json(session);
    assert.ok(path.endsWith('/projects/revise'));const local=await new DraftStore().read(session.query_scope,project.id);assert.equal(local.pending.body,init.body,'an independent IDB connection sees the exact committed save intent');sent.push(init.body);
    if(failure)return json({error:{code:failure.code}},failure.status);
    const command=JSON.parse(init.body);return json({...project,revision:8,input_sha256:'5'.repeat(64),inputs:command.inputs});
  }});
  await client.bootstrap();
  function App(){flow=useProjectDraft(project,session,client,store,()=>assert.fail('Unexpected native identity error'));return null;}
  t.after(async()=>{await dom.dispose(root);cache.clear();if(prior)Object.defineProperty(globalThis,'indexedDB',prior);else delete globalThis.indexedDB;});
  await act(async()=>root.render(React.createElement(QueryClientProvider,{client:cache},React.createElement(App))));await until(()=>flow.draft!==null);
  await act(async()=>flow.update(old=>editDraft(old,{note:'Uncertain snapshot'})));await act(async()=>flow.save());
  assert.ok(flow.draft.pending);const original=flow.draft.pending.body;assert.equal(sent[0],original);
  await act(async()=>flow.update(old=>editDraft(old,{note:'Newer input must survive'})));
  failure={status:415,code:'invalid_input'};await act(async()=>flow.save());assert.equal(sent[1],original);assert.equal(flow.draft.pending.body,original,'a recognized code with an unsupported status is still unknown');assert.equal(flow.draft.history.current.note,'Newer input must survive');
  failure={status:400,code:'invalid_input'};await act(async()=>flow.save());assert.equal(sent[2],original);assert.equal(flow.draft.pending,null);assert.equal(flow.draft.history.current.note,'Newer input must survive');
  failure=null;await act(async()=>flow.save());await until(()=>flow.draft.baseline.revision===8);
  const next=JSON.parse(sent[3]);assert.notEqual(next.key,JSON.parse(original).key);assert.deepEqual(next.inputs,{note:'Newer input must survive'});assert.equal(flow.draft.pending,null);assert.deepEqual(flow.draft.baseline.inputs,next.inputs);
});
