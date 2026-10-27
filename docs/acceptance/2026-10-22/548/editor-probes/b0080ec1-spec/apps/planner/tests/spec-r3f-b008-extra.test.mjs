import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import React,{act} from 'react';
import * as THREE from 'three/webgpu';
import {createRoot,extend} from '@react-three/fiber';
import {TransformControls} from 'three/addons/controls/TransformControls.js';
import {setupDom} from './dom-fixture.mjs';
import flat from '../../../fixtures/planning/geometry-flat.json' with {type:'json'};
import {panelPoses} from '../src/domain/panelPoses.ts';
import {applyGeometryCommand} from '../src/domain/geometryCommands.ts';
const results=[];
function record(value){results.push(value);fs.writeFileSync(new URL('../../../probe_r3f_extra.results.json',import.meta.url),JSON.stringify(results,null,2)+'\n');}
async function fixture(t){
 const dom=setupDom(); const {Panels}=await import('../src/components/design/SceneViewport.tsx');extend(THREE);
 const canvas=document.createElement('canvas');canvas.setPointerCapture=()=>{};canvas.releasePointerCapture=()=>{};canvas.hasPointerCapture=()=>false;
 const gl={domElement:canvas,render(){},setPixelRatio(){},setSize(){},getPixelRatio(){return 1},xr:{enabled:false,isPresenting:false,addEventListener(){},removeEventListener(){},setAnimationLoop(){}},shadowMap:{enabled:false,type:0}};
 const root=createRoot(canvas);let controls=[];let disposed=0;const attach=TransformControls.prototype.attach,dispose=TransformControls.prototype.dispose;
 TransformControls.prototype.attach=function(...args){controls.push(this);return attach.apply(this,args)};
 TransformControls.prototype.dispose=function(...args){disposed++;return dispose.apply(this,args)};
 let doc=structuredClone(flat),attempts=0,commits=0,lastCommand=null;doc.roofs.push({...doc.roofs[0],id:'secondroof',origin_enu:[30,-20,4]});
 doc.arrays[0]={...doc.arrays[0],roof_id:'secondroof',rows:1,columns:1,excluded_slots:[]};
 doc.arrays.push({...doc.arrays[0],id:'otherarray',origin_uv:[8,9]});let selected=doc.arrays[0].id,disabled=false,shown=true;
 await root.configure({gl,frameloop:'never',dpr:1,size:{width:200,height:200,top:0,left:0},camera:{position:[30,30,30]}});
 async function render(){await act(async()=>root.render(React.createElement(React.StrictMode,null,shown&&React.createElement(Panels,{document:doc,frame:JSON.stringify(doc),poses:panelPoses(doc).filter(p=>p.array_id==='array'),array:doc.arrays[0],roof:doc.roofs[1],reference:doc.roofs[0].origin_enu,palette:{roof:'#aaa',module:'#123456',selected:'#0f0',obstacle:'#777',keepout:'#666',background:'#fff'},selected,select(){},disabled,commit(command){attempts++;lastCommand=command;try{doc=applyGeometryCommand(doc,command);commits++;return true;}catch{return false}}}))));}
 t.after(async()=>{await act(async()=>root.unmount());await new Promise(r=>setTimeout(r,600));TransformControls.prototype.attach=attach;TransformControls.prototype.dispose=dispose;await dom.dispose({unmount(){}})});
 await render();return{get doc(){return doc},set doc(v){doc=v},get control(){return controls.at(-1)},get attempts(){return attempts},get commits(){return commits},get lastCommand(){return lastCommand},get disposed(){return disposed},set selected(v){selected=v},set disabled(v){disabled=v},set shown(v){shown=v},render};
}
function begin(f){const c=f.control;assert.ok(c.object);c.dragging=true;c.axis='X';c.dispatchEvent({type:'mouseDown',mode:'translate'});c.object.position.x+=2;return c;}
test('independent: a valid unchanged-frame finish commits exactly one full-document group',async t=>{const f=await fixture(t),before=structuredClone(f.doc);begin(f).pointerUp(null);record({case:'normal_finish',attempts:f.attempts,commits:f.commits,origin:f.doc.arrays[0].origin_uv,groupBeforeMatches:JSON.stringify(f.lastCommand.before)===JSON.stringify(before)});assert.equal(f.commits,1);assert.equal(f.lastCommand.type,'group');assert.deepEqual(f.lastCommand.before,before);assert.deepEqual(f.doc.arrays[0].origin_uv,[3,2]);assert.deepEqual(f.doc.arrays[1],before.arrays[1]);});
const changes={module:d=>({...d,module_specs:d.module_specs.map(m=>({...m,width_m:1.1}))}),other_array:d=>({...d,arrays:d.arrays.map(a=>a.id==='otherarray'?{...a,origin_uv:[10,10]}:a)}),north:d=>({...d,coordinate_system:{...d.coordinate_system,north_reference:'true_north',north_source_id:'survey'}})};
for(const [name,change]of Object.entries(changes))test('independent: '+name+' mutation aborts preview and permits a fresh gesture',async t=>{const f=await fixture(t),c=begin(f);f.doc=change(f.doc);const expected=structuredClone(f.doc);await f.render();assert.equal(c.dragging,false);c.dispatchEvent({type:'mouseUp',mode:'translate'});assert.equal(f.attempts,0);assert.deepEqual(f.doc,expected);begin(f).pointerUp(null);record({case:name+'_changed',oldAttempts:0,commits:f.commits,origin:f.doc.arrays[0].origin_uv});assert.equal(f.commits,1);assert.deepEqual(f.doc.arrays[0].origin_uv,[3,2]);});
for(const [name,change]of Object.entries({roof:d=>({...d,roofs:d.roofs.map(r=>r.id==='secondroof'?{...r,origin_enu:[40,-20,4]}:r)}),reference:d=>({...d,roofs:d.roofs.map(r=>r.id==='roof'?{...r,origin_enu:[20,-20,4]}:r)}),...changes}))test('independent: '+name+' parent mutation before child render cannot commit stale displacement',async t=>{const f=await fixture(t),c=begin(f);f.doc=change(f.doc);const expected=structuredClone(f.doc);c.pointerUp(null);record({case:name+'_parent_before_child',attempts:f.attempts,commits:f.commits,origin:f.doc.arrays[0].origin_uv});assert.equal(f.attempts,1);assert.equal(f.commits,0);assert.deepEqual(f.doc,expected);});
for(const mode of ['deselect','disable','unmount'])test('independent: '+mode+' during manipulation cancels without leaving preview or command',async t=>{const f=await fixture(t),c=begin(f),group=c.object;const expected=[21,0.0,-2];if(mode==='deselect')f.selected='otherarray';if(mode==='disable')f.disabled=true;if(mode==='unmount')f.shown=false;await f.render();record({case:mode,attempts:f.attempts,commits:f.commits,dragging:c.dragging,group:group.position.toArray(),disposed:f.disposed});assert.equal(c.dragging,false);assert.equal(f.commits,0);assert.equal(f.attempts,0);if(mode!=='unmount')assert.deepEqual(group.position.toArray(),expected);else assert.equal(group.parent,null);assert.equal(c.object,undefined);});
