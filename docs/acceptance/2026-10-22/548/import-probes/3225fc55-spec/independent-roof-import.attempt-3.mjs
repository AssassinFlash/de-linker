import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import React, { act } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { IDBFactory } from 'fake-indexeddb';
import { setupDom, until, deferred, enter } from './dom-fixture.mjs';
import { PlannerClient } from '../src/data/PlannerClient.ts';
import { GeometryImportStore, geometryImportStore } from '../src/data/GeometryImportStore.ts';
import { DraftStore } from '../src/data/DraftStore.ts';
import { useGeometryImport } from '../src/data/useGeometryImport.ts';
import { GeometryIntake } from '../src/components/design/GeometryIntake.tsx';
import { ProfileIntake } from '../src/components/ProfileIntake.tsx';
import { ProjectEditor } from '../src/components/ProjectEditor.tsx';
import { emptyGeometry } from '../src/domain/geometryCommands.ts';
import { emptyBrief } from '../src/domain/brief.ts';

const fixture = name => readFileSync(new URL('../../../fixtures/planning/' + name, import.meta.url));
const raw = fixture('source-roof-wgs84.geojson');
const accepted = JSON.parse(fixture('geometry-import-asset.json'));
const options = accepted.metadata.geometry_import_options;
const scope = 'a'.repeat(64), former = 'b'.repeat(64), foreign = 'c'.repeat(64), pid = accepted.project_id;
const session = {
  schema_version: 1, kind: 'guest', cookie_confirmed: true, expires_at: 2000000000,
  query_scope: scope, nonce: 'abcdefghij', claim_pending: false,
  runtime: {schema_version: 1, runtime_sha256: 'd'.repeat(64), models: {}, limits: {
    max_body_bytes: 16777216, max_csv_bytes: 4194304, max_page_size: 20, max_json_depth: 32,
  }},
};
const response = (value, status = 200) => new Response(JSON.stringify(value), {status, headers: {'Content-Type': 'application/json'}});
const refused = (code, status = 422) => response({error: {code}}, status);
const request = (changes = {}) => ({schema_version: 1, project_id: pid, key: crypto.randomUUID(), content_base64: raw.toString('base64'), options: structuredClone(options), ...changes});
const button = text => [...document.querySelectorAll('button')].find(el => (el.getAttribute('aria-label') ?? el.textContent.trim()) === text);
const field = name => document.querySelector(`[name="${name}"]`);
async function click(text) {const el = button(text); assert.ok(el, text); assert.equal(el.disabled, false, text + ' enabled'); await act(async () => el.click());}
async function select(el, value) {await act(async () => {el.value = value; el.dispatchEvent(new window.Event('input', {bubbles: true})); el.dispatchEvent(new window.Event('change', {bubbles: true}));});}
async function readDB(store, method, ...args) {let value; await act(async()=>{value=await store[method](...args);}); return value;}
async function tick() {await act(async () => new Promise(resolve => setTimeout(resolve, 0)));}

// A new isolated IDBFactory exercises actual transactions. The real client,
// hooks, controls, Query cache and both recovery stores remain in this path.
// Only native HTTP replies are controlled; fixture coordinates are synthetic.
async function mount(t, {mode = 'hook', locale = 'en-GB', geometry = emptyGeometry(), recoveryScopes = [scope], writeGate = null, onReply = () => response(accepted), inputs, seed} = {}) {
  const dom = setupDom(), descriptor = Object.getOwnPropertyDescriptor(globalThis, 'indexedDB');
  Object.defineProperty(globalThis, 'indexedDB', {value: new IDBFactory(), configurable: true});
  const {createRoot} = await import('react-dom/client');
  const journal = mode === 'project' ? geometryImportStore : new GeometryImportStore(), drafts = new DraftStore();
  if (seed) await seed(journal, drafts);
  const cache = new QueryClient(), root = createRoot(dom.element), uploads = [], revisions = [], csv = [], events = [];
  let owner = session, reply = onReply, flow, closes = 0, activity = false, writeStarted = false;
  const client = new PlannerClient({origin: location.origin, baseUrl: location.origin + '/api/', nonceUrl: location.origin + '/nonce', fetch: async (url, init) => {
    const path = new URL(url).pathname;
    if (path === '/nonce') return new Response('abcdefghij');
    if (path.endsWith('/bootstrap')) return response(owner);
    if (path.endsWith('/geometry/import')) {
      const stored = await new GeometryImportStore().list(recoveryScopes, pid);
      assert.ok(stored.some(item => item.body === init.body), 'a new database connection sees the exact committed original before fetch');
      events.push('fetch'); uploads.push({body: init.body, signal: init.signal});
      return reply(init, 'geometry');
    }
    if (path.endsWith('/projects/revise')) {
      const stored = await drafts.read(scope, pid);
      assert.equal(stored.pending.body, init.body, 'real project IDB contains the exact revision intent before dispatch');
      revisions.push(init.body); return reply(init, 'revision');
    }
    if (path.endsWith('/profiles/csv')) {csv.push(init.body); return reply(init, 'csv');}
    throw new Error('Unexpected review transport ' + path);
  }});
  await client.bootstrap();
  const protectedJournal = {
    list: journal.list.bind(journal), clear: journal.clear.bind(journal), acknowledge: journal.acknowledge.bind(journal),
    async write(origin, body) {writeStarted = true; if (writeGate) await writeGate.promise; await journal.write(origin, body); events.push('committed');},
  };
  const project = {id: pid, title: 'Independent roof import review', revision: 7, input_sha256: 'e'.repeat(64), inputs: inputs ?? {brief: emptyBrief()}};
  let props = {projectId: pid, session, client, recheck() {events.push('recheck');}, recoveryScopes, confirmedAssetIds: [], store: protectedJournal};
  function App() {
    if (mode === 'hook') {flow = useGeometryImport(props); return null;}
    if (mode === 'intake') return React.createElement(GeometryIntake, {...props, geometry, locale, disabled: false, currentAssetIds: [], onActivity(value) {activity = value;}, attach() {assert.fail('Unexpected attachment');}});
    if (mode === 'csv') return React.createElement(ProfileIntake, {...props, store: drafts, locale, timezone: 'Europe/Oslo', attach: async () => {assert.fail('Unexpected CSV attach');}, registerGuard() {}, currentAssetIds: []});
    return React.createElement(ProjectEditor, {project, session, client, store: drafts, recheck: props.recheck, recoveryScopes, config: {locale, countries: {DE: 'Germany'}}, close() {closes++; return true;}});
  }
  async function render(changes = {}) {props = {...props, ...changes}; await act(async () => root.render(React.createElement(QueryClientProvider, {client: cache}, React.createElement(App))));}
  t.after(async () => {for(let i=0;i<3;i++) await tick(); await dom.dispose(root); cache.clear(); if (descriptor) Object.defineProperty(globalThis, 'indexedDB', descriptor); else delete globalThis.indexedDB;});
  if (mode === 'project') location.hash = '#lp-design';
  await render();
  if (mode === 'hook') await until(() => !flow.checking);
  if (mode === 'intake' || mode === 'project') await until(() => button('Import roof geometry') && !button('Import roof geometry').disabled);
  return {client, journal, drafts, uploads, revisions, csv, events, project, render, get flow() {return flow;}, get activity() {return activity;}, get closes() {return closes;}, get writeStarted() {return writeStarted;}, reply(value) {reply = value;}, async revoke() {owner = {...session, query_scope: foreign}; await act(async () => client.bootstrap());}};
}

async function upload(bytes = raw, name = 'original-survey.geojson') {
  const input = document.querySelector('.lp-geometry-intake input[type=file]');
  await act(async () => {
    Object.defineProperty(input, 'files', {value: [{name, size: bytes.length, arrayBuffer: async () => Uint8Array.from(bytes).buffer}], configurable: true});
    input.dispatchEvent(new window.Event('change', {bubbles: true}));
  });
  await until(() => !button('Close import').disabled);
}
async function fillPlane({pitch = '30,5', bearing = '90', height = '-5,125'} = {}) {
  await enter(field('pitch'), pitch); await enter(field('bearing'), bearing); await enter(field('height'), height); await enter(field('basis'), '  Survey A / original basis  '); await click('Continue');
}
async function fillSource() {
  await enter(field('source'), '  Original measurement A  '); await enter(field('rights'), '  Own file: retain and derive.  '); await enter(field('precision'), '0,15'); await select(field('export'), 'prohibited'); await act(async () => field('retention').click());
}

test('independent: all raw controls and original bytes survive Back, unidentified 422, and later typed correction', async t => {
  const app = await mount(t, {mode: 'intake', locale: 'de-DE', onReply: () => refused('unidentified_proxy_failure')});
  await click('Import roof geometry'); await upload();
  assert.equal(app.activity, true); assert.equal(field('selection').value, '0:0');
  for (const name of ['pitch', 'bearing', 'height', 'precision']) assert.equal(field(name).value, '', name + ' has no measured default');
  assert.equal(field('retention').checked, false); assert.equal(field('export').value, 'unknown');
  const zero = document.querySelector('[data-import-step="1"] input[type=checkbox]'); assert.equal(zero.checked, false);
  await enter(field('roof'), '  My exact raw roof  '); await click('Continue'); await fillPlane(); await fillSource();
  const nodes = Object.fromEntries(['roof','pitch','bearing','height','basis','source','rights','precision','export','retention'].map(name => [name, field(name)]));
  const values = Object.fromEntries(Object.entries(nodes).map(([name,node]) => [name, node.type === 'checkbox' ? node.checked : node.value]));
  await click('Back'); await click('Back'); await click('Continue'); await click('Continue');
  await click('Prepare roof preview'); await until(() => app.uploads.length === 1 && !button('Check or retry this upload').disabled);
  const stored = (await readDB(app.journal,'list',[scope], pid))[0]; assert.equal(stored.body, app.uploads[0].body);
  assert.equal(JSON.parse(stored.body).content_base64, raw.toString('base64'));
  assert.equal(JSON.parse(stored.body).options.source.export_permission, 'prohibited');
  assert.equal(JSON.parse(stored.body).options.source.spatial_precision_m, 0.15);
  assert.equal(JSON.parse(stored.body).options.plane.origin_enu[2], -5.125);
  assert.equal(document.querySelector('.lp-geometry-intake form').hidden, true);
  app.reply(() => refused('invalid_input')); await click('Check or retry this upload'); await until(() => !button('Prepare roof preview').disabled);
  assert.equal(app.uploads[1].body, stored.body); assert.deepEqual(await readDB(app.journal,'list',[scope], pid), []);
  for (const [name,node] of Object.entries(nodes)) {assert.equal(field(name), node, name + ' node retained'); assert.equal(node.type === 'checkbox' ? node.checked : node.value, values[name], name + ' raw value retained');}
  await click('Close import'); await until(() => document.activeElement === button('Import roof geometry'));
});

test('independent: actual MultiPolygon choice is explicit and sends its original rings and nonzero part indices', async t => {
  const input = JSON.parse(raw), rings = input.geometry.coordinates;
  const second = rings.map(ring => ring.map(([x,y]) => [x + 0.002,y + 0.003]));
  const bytes = Buffer.from(JSON.stringify({type: 'FeatureCollection', features: [{type: 'Feature', geometry: {type: 'Point', coordinates: [0,0]}}, {type: 'Feature', properties: {name: 'Warehouse roof'}, geometry: {type: 'MultiPolygon', coordinates: [rings,second]}}]}, null, 3));
  const app = await mount(t, {mode: 'intake', locale: 'de-DE', onReply: () => refused('invalid_input')});
  await click('Import roof geometry'); await upload(bytes); assert.equal(field('selection').value, '');
  assert.deepEqual([...field('selection').options].slice(1).map(el => el.textContent), ['Warehouse roof · face 1','Warehouse roof · face 2']);
  await click('Continue'); assert.equal(document.querySelector('[data-import-step="0"]').hidden, false);
  await select(field('selection'), '1:1'); await click('Continue'); await fillPlane(); await fillSource(); await click('Prepare roof preview'); await until(() => app.uploads.length === 1 && !button('Prepare roof preview').disabled);
  const command = JSON.parse(app.uploads[0].body); assert.equal(command.options.feature_index, 1); assert.equal(command.options.polygon_index, 1); assert.equal(command.content_base64, bytes.toString('base64'));
  assert.equal(command.options.reference.longitude_deg, second[0][0][0]); assert.equal(command.options.reference.latitude_deg, second[0][0][1]);
  assert.ok(document.body.textContent.includes('Openings in source: 1'));
});

test('independent: existing origin stays fixed and declared negative Up follows the selected vertex geodetic vertical', async t => {
  const geometry = structuredClone(accepted.metadata.geometry_import.geometry);
  const point = JSON.parse(fixture('geographic-proj-reference.json')).cases[0].points[1];
  const bytes = JSON.parse(raw), dx = point.geodetic[0] - bytes.geometry.coordinates[0][0][0], dy = point.geodetic[1] - bytes.geometry.coordinates[0][0][1];
  bytes.geometry.coordinates = bytes.geometry.coordinates.map(ring => ring.map(([x,y]) => [x+dx,y+dy]));
  const app = await mount(t, {mode:'intake',locale:'de-DE',geometry,onReply:()=>refused('invalid_input')});
  await click('Import roof geometry'); await upload(Buffer.from(JSON.stringify(bytes))); await click('Continue'); await fillPlane(); await fillSource(); await click('Prepare roof preview'); await until(()=>app.uploads.length===1 && !button('Prepare roof preview').disabled);
  const command=JSON.parse(app.uploads[0].body), p=command.options.plane, ref=command.options.reference;
  assert.equal(ref.longitude_deg,options.reference.longitude_deg); assert.equal(ref.latitude_deg,options.reference.latitude_deg); assert.equal(p.origin_enu[2],-5.125);
  // Frozen independently generated PROJ base + analytic geodetic unit direction.
  const rad=Math.PI/180, phi=point.geodetic[1]*rad, phi0=ref.latitude_deg*rad, dl=(point.geodetic[0]-ref.longitude_deg)*rad;
  const direction=[Math.cos(phi)*Math.sin(dl),Math.sin(phi)*Math.cos(phi0)-Math.cos(phi)*Math.sin(phi0)*Math.cos(dl),Math.sin(phi)*Math.sin(phi0)+Math.cos(phi)*Math.cos(phi0)*Math.cos(dl)];
  const distance=(-5.125-point.enu[2])/direction[2];
  for(let axis=0;axis<2;axis++) assert.ok(Math.abs(p.origin_enu[axis]-(point.enu[axis]+distance*direction[axis]))<5e-8,'preserve complete geodetic vertical, axis '+axis);
  assert.ok(p.v_axis_enu[0]>0.8 && p.v_axis_enu[2]<-0.5); assert.ok(Math.abs(p.v_axis_enu[1])<1e-14,'90 degrees is downslope east');
  assert.deepEqual(geometry,accepted.metadata.geometry_import.geometry,'import does not move existing geometry');
});

test('independent: nonempty unaligned geometry cannot supply implicit origin or dispatch', async t => {
  const geometry=JSON.parse(fixture('geometry-flat.json')), original=structuredClone(geometry);
  const app=await mount(t,{mode:'intake',geometry}); await click('Import roof geometry');
  assert.ok(document.body.textContent.includes('existing design needs a geographic origin'));
  assert.equal(document.querySelector('.lp-geometry-intake fieldset').disabled,true); assert.equal(app.uploads.length,0); assert.deepEqual(geometry,original);
});

test('independent: malformed 3D, CRS and unclosed originals never reach mutation', async t => {
  const app=await mount(t,{mode:'intake'}); await click('Import roof geometry');
  for(const kind of ['3D','CRS','unclosed']) {
    const input=JSON.parse(raw); if(kind==='3D') input.geometry.coordinates[0][0].push(20); if(kind==='CRS') input.crs={type:'name',properties:{name:'EPSG:3857'}}; if(kind==='unclosed') input.geometry.coordinates[0].pop();
    await upload(Buffer.from(JSON.stringify(input)),kind+'.geojson'); assert.equal(button('Continue').disabled,true); assert.equal(field('selection').options.length,1); assert.equal(app.uploads.length,0);
  }
});

test('independent: real IDB quota across other project intents refuses dispatch without evicting originals', async t => {
  const app=await mount(t), protectedBodies=[];
  for(let i=0;i<32;i++){const body=JSON.stringify(request({project_id:'f'.repeat(32)}));protectedBodies.push(body);await app.journal.write(scope,body);}
  await act(async()=>app.flow.prepare(request())); assert.equal(app.uploads.length,0); assert.equal(app.flow.storageFailed,true); assert.equal(app.flow.durable,false);
  assert.deepEqual((await readDB(app.journal,'list',[scope],'f'.repeat(32))).map(item=>item.body).sort(),protectedBodies.sort());
  assert.deepEqual(await readDB(app.journal,'list',[scope],pid),[]);
});

test('independent: incomplete local commit and later native withdrawal cannot dispatch a roof request', async t => {
  const gate=deferred(),app=await mount(t,{writeGate:gate}); let pending;
  await act(async()=>{pending=app.flow.prepare(request());}); await until(()=>app.writeStarted); assert.equal(app.uploads.length,0); assert.deepEqual(await readDB(app.journal,'list',[scope],pid),[]);
  await app.revoke(); await act(async()=>{gate.resolve();await pending;}); assert.equal(app.uploads.length,0); assert.equal((await readDB(app.journal,'list',[scope],pid)).length,1); assert.equal(app.flow.asset,null);
});

test('independent: dismiss aborts a dispatched request, preserves its durable intent, and fences an ignored late response', async t => {
  const gate=deferred(),app=await mount(t,{onReply:async()=>{await gate.promise;return response(accepted);}});let pending;
  await act(async()=>{pending=app.flow.prepare(request());});await until(()=>app.uploads.length===1);
  await act(async()=>app.flow.dismiss());await until(()=>!app.flow.checking);assert.equal(app.uploads[0].signal.aborted,true);
  await act(async()=>{gate.resolve();await pending;});assert.equal(app.flow.asset,null);assert.equal((await readDB(app.journal,'list',[scope],pid)).length,1);
});

test('independent: current native admission, without dismissal, fences a late successful response', async t => {
  const gate=deferred(),app=await mount(t,{onReply:async()=>{await gate.promise;return response(accepted);}});let pending;
  await act(async()=>{pending=app.flow.prepare(request());});await until(()=>app.uploads.length===1);await app.revoke();
  await act(async()=>{gate.resolve();await pending;});assert.equal(app.flow.asset,null);assert.equal((await readDB(app.journal,'list',[scope],pid))[0].assetId,null);
});

test('independent: only a native-granted former namespace can be explicitly retried with the same original body/key', async t => {
  const body=JSON.stringify(request()),app=await mount(t,{recoveryScopes:[scope,former]});await app.journal.write(former,body);await app.journal.write(foreign,JSON.stringify(request()));
  await act(async()=>app.flow.refresh());await until(()=>app.flow.records.length===1);assert.equal(app.uploads.length,0);assert.equal(app.flow.records[0].scope,former);
  await act(async()=>app.flow.retry(app.flow.records[0]));await until(()=>app.flow.asset!==null&&!app.flow.busy);assert.equal(app.uploads[0].body,body);assert.equal((await readDB(app.journal,'list',[former],pid))[0].assetId,accepted.id);
  const ungranted=(await readDB(app.journal,'list',[foreign],pid))[0];await assert.rejects(app.flow.retry(ungranted),/geometry_recovery_invalid/);assert.equal(app.uploads.length,1);
  await app.render({confirmedAssetIds:[accepted.id]});await until(()=>!app.flow.checking);assert.deepEqual(await readDB(app.journal,'list',[former],pid),[]);assert.equal((await readDB(app.journal,'list',[foreign],pid)).length,1);
});

test('independent: unidentified status/code combinations retain retry bytes; only identified pre-mutation pairs release them', async t => {
  const app=await mount(t);
  for(const [status,code,release] of [[400,'request_failed',false],[413,'proxy_failure',false],[415,'invalid_input',false],[422,'invalid_json_object',true],[503,'invalid_input',false],[400,'invalid_input',true]]) {
    app.reply(()=>refused(code,status));const cmd=request();await act(async()=>app.flow.prepare(cmd));
    assert.equal(app.flow.intent===null,release,status+'/'+code);const rows=await readDB(app.journal,'list',[scope],pid);assert.equal(rows.some(row=>row.key===cmd.key),!release);
    if(!release){const original=app.flow.intent;await act(async()=>app.flow.retry(original));assert.equal(app.uploads.at(-1).body,original.body);await act(async()=>app.flow.dismiss());await until(()=>!app.flow.checking);}
  }
});

test('independent: changed server options or content hash never produce an attachable prepared roof', async t => {
  const app=await mount(t);
  for(const kind of ['options','hash']) {
    const reply=structuredClone(accepted);if(kind==='options') reply.metadata.geometry_import_options.source.label='Different original';else {reply.content_sha256='0'.repeat(64);reply.metadata.geometry_import.content_sha256='0'.repeat(64);}
    app.reply(()=>response(reply));const cmd=request();await act(async()=>app.flow.prepare(cmd));assert.equal(app.flow.asset,null);assert.ok(app.flow.intent);assert.equal((await readDB(app.journal,'list',[scope],pid)).some(row=>row.key===cmd.key),true);await act(async()=>app.flow.dismiss());
  }
});

test('independent: CSV identified refusal correction also uses the real client and real IndexedDB original', async t => {
  const mapping={timestamp_column:'time',value_column:'power',measurement:'net_import',value_kind:'interval_average_kw',timestamp_role:'start',timezone:'Europe/Oslo',origin:'synthetic',interval_seconds:900,delimiter:';',decimal:'.',end_timestamp_column:null,fold_column:null,end_fold_column:null,offset_rule:'explicit_offset_precedes_naive_timezone',within_interval_assumption:'constant_mean_no_new_observations'};
  const body=JSON.stringify({schema_version:1,project_id:pid,content_base64:btoa('time;power\n2024-01-01T00:00Z;1\n'),mapping,source_label:'Independent retained CSV',rights_note:'Own test original',key:crypto.randomUUID()});
  const app=await mount(t,{mode:'csv',seed:async(_journal,store)=>store.writeProfileImport(scope,body),onReply:()=>refused('request_failed')});
  await until(()=>button('Check or retry this import'));await click('Check or retry this import');await until(()=>app.csv.length===1&&!button('Check or retry this import').disabled);
  assert.equal(app.csv[0],body);assert.equal((await readDB(app.drafts,'readProfileImports',scope,pid))[0].body,body);
  app.reply(()=>refused('invalid_input'));await click('Check or retry this import');await until(()=>!button('Check or retry this import'));assert.equal(app.csv[1],body);assert.deepEqual(await readDB(app.drafts,'readProfileImports',scope,pid),[]);assert.ok(document.querySelector('input[type=file]'));
});

test('independent: commercial project preview adds exactly one shared history step; unknown revision retry preserves body; confirmed save clears only that original', async t => {
  const original=JSON.stringify(request()),unrelated=JSON.stringify(request({options:{...structuredClone(options),source:{...options.source,label:'Another unfinished import'}}}));
  const otherProject='f'.repeat(32),other=JSON.stringify(request({project_id:otherProject}));
  const brief=emptyBrief();brief.project_use='commercial';brief.annual_load={kwh:31415.9,basis:'bill_total',source_note:'Independent existing bill'};
  const initial={brief,unrelated_fact:{preserve:'Every history command'}};
  let revisionAttempt=0;
  const app=await mount(t,{mode:'project',inputs:initial,seed:async journal=>{await journal.write(scope,original);await journal.write(scope,unrelated);await journal.write(scope,other);await journal.acknowledge(scope,other,accepted.id);},onReply:(init,kind)=>{
    if(kind==='geometry')return response(accepted);assert.equal(kind,'revision');revisionAttempt++;if(revisionAttempt===1)return refused('request_failed');const command=JSON.parse(init.body);return response({id:pid,title:'Independent roof import review',revision:8,input_sha256:'9'.repeat(64),inputs:command.inputs});
  }});
  await until(()=>button(options.source.label));await click(options.source.label);assert.equal(app.uploads.length,0);assert.equal(button('Save project').disabled,true);
  const beforeEvent=new window.Event('beforeunload',{cancelable:true});window.dispatchEvent(beforeEvent);assert.equal(beforeEvent.defaultPrevented,true);
  await act(async()=>document.querySelector('nav a[href="#lp-overview"]').click());assert.equal(document.querySelector('.lp-project').dataset.workspace,'design');await click('Projects');assert.equal(app.closes,0);
  await click('Check or retry this upload');await until(()=>button('Add roof to current design')&&!button('Add roof to current design').disabled);
  assert.equal((await readDB(app.drafts,'read',scope,pid))?.history.current.geometry,undefined,'preview alone does not enter history');assert.equal((await readDB(app.journal,'list',[scope],pid)).length,2,'preview alone does not clear original');
  assert.equal(document.querySelector('.lp-import-review svg').getAttribute('aria-label').includes(options.roof_name),true);assert.ok(document.querySelector('.lp-import-review svg path[fill-rule="evenodd"]'));
  await click('Add roof to current design');
  let local;for(let i=0;i<100;i++){local=await readDB(app.drafts,'read',scope,pid);if(local?.history.current.geometry?.roofs.length===1)break;await tick();}
  assert.equal(local.history.past.length,1);assert.deepEqual(local.history.current.brief,brief);assert.deepEqual(local.history.current.unrelated_fact,initial.unrelated_fact);assert.equal(local.history.current.geometry.roofs[0].holes_uv.length,1);
  const added=structuredClone(local.history.current);await click('Undo');for(let i=0;i<100;i++){local=await readDB(app.drafts,'read',scope,pid);if(local?.history.current.geometry===undefined)break;await tick();}assert.deepEqual(local.history.current,initial);
  await click('Redo');for(let i=0;i<100;i++){local=await readDB(app.drafts,'read',scope,pid);if(local?.history.current.geometry)break;await tick();}assert.deepEqual(local.history.current,added);
  await click('Save project');await until(()=>button('Retry save'));local=await readDB(app.drafts,'read',scope,pid);assert.equal(local.pending.body,app.revisions[0]);assert.equal((await readDB(app.journal,'list',[scope],pid)).length,2);
  await click('Retry save');await until(()=>document.body.textContent.includes('Saved · revision 8'));assert.equal(app.revisions[1],app.revisions[0]);
  for(let i=0;i<100;i++){if((await readDB(app.journal,'list',[scope],pid)).length===1)break;await tick();}
  assert.deepEqual((await readDB(app.journal,'list',[scope],pid)).map(row=>row.body),[unrelated]);assert.equal((await readDB(app.journal,'list',[scope],otherProject))[0].body,other);
  local=await readDB(app.drafts,'read',scope,pid);assert.deepEqual(local.baseline.inputs,added);assert.equal(local.pending,null);assert.equal(local.history.past.length,1);assert.ok(document.body.textContent.includes('roof import is included in the saved project'));
});
