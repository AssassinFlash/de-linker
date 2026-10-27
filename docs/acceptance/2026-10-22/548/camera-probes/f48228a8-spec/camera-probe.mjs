import assert from 'node:assert/strict';
import test from 'node:test';
import React,{act}from'react';
import {readFileSync}from'node:fs';
import {PerspectiveCamera,Vector3,WebGPURenderer}from'three/webgpu';
import {setupDom,until,deferred}from'./dom-fixture.mjs';
import SceneViewport from'../src/components/design/SceneViewport.tsx';
import {readGeometry}from'../src/domain/validateGeometry.ts';
import policy from'../src/contracts/geometry-policy.json'with{type:'json'};
import {roofPlane}from'../src/domain/geometryEditing.ts';
import {panelPoses}from'../src/domain/panelPoses.ts';
import {renderBoundsPoints}from'../src/domain/renderGeometry.ts';
import {cross,toRender}from'../src/domain/coordinates.ts';
import {sceneViewDirection}from'../src/domain/sceneCamera.ts';
const flat=JSON.parse(readFileSync(new URL('../../../fixtures/planning/geometry-flat.json',import.meta.url),'utf8'));
const button=label=>[...document.querySelectorAll('button')].find(el=>el.textContent.trim()===label);
async function click(label){assert.ok(button(label),label);assert.equal(button(label).disabled,false);await act(async()=>button(label).click());}
const direction=camera=>camera.getWorldDirection(new Vector3()).negate();
const near=(a,b,tolerance=1e-10)=>assert.ok(a.distanceTo(b)<tolerance,JSON.stringify({actual:a.toArray(),expected:b.toArray()}));
function points(document){return renderBoundsPoints(document,panelPoses(document),document.roofs[0].origin_enu).map(p=>new Vector3(...p));}
function projections(document,camera){camera.updateMatrixWorld(true);return points(document).map(p=>p.project(camera).toArray());}
const inside=ndc=>ndc.every(v=>Number.isFinite(v)&&Math.abs(v)<1);

async function mount(t,{document:initial=flat,width=1440,height=700,selected=null}={}){
  const dom=setupDom(),prior=globalThis.getComputedStyle;globalThis.getComputedStyle=dom.dom.window.getComputedStyle.bind(dom.dom.window);
  const host={width,height,mounts:0,unmounts:0,invalidations:0,props:null,store:null};globalThis.__cameraHost=host;
  const{createRoot}=await import('react-dom/client');const root=createRoot(dom.element);let commits=0,selections=0;
  let props={document:readGeometry(structuredClone(initial),policy),poses:panelPoses(initial),selected,select(){selections++;},commit(){commits++;return false;},disabled:false};
  async function render(changes={}){props={...props,...changes};await act(async()=>root.render(React.createElement(SceneViewport,props)));await until(()=>host.store!==null);}
  t.after(async()=>{await dom.dispose(root);if(prior===undefined)delete globalThis.getComputedStyle;else globalThis.getComputedStyle=prior;delete globalThis.__cameraHost;});
  await render();
  return{host,render,get camera(){return host.store.getState().camera;},get props(){return props;},get commits(){return commits;},get selections(){return selections;},async resize(w,h){await act(async()=>host.store.setState({size:{width:w,height:h}}));}};
}

test('independent: real camera hook preserves orbit on selection and resize; explicit Fit uses the latest selected roof without a new Canvas',async t=>{
  const doc=structuredClone(flat),second={...doc.roofs[0],id:'steep-second',...roofPlane(70,205,[40,0,8])};doc.roofs.push(second);doc.arrays[0].roof_id=second.id;
  const before=JSON.stringify(doc),app=await mount(t,{document:doc}),camera=app.camera;
  camera.position.set(120,95,-40);camera.lookAt(new Vector3(0,0,0));camera.updateMatrixWorld(true);const orbitPosition=camera.position.clone(),orbitDirection=direction(camera);
  await app.render({selected:second.id});near(camera.position,orbitPosition);near(direction(camera),orbitDirection);assert.equal(app.camera,camera);assert.equal(app.host.mounts,1);
  await app.resize(390,700);near(direction(camera),orbitDirection);assert.equal(camera.aspect,390/700);assert.ok(camera.near>0&&camera.far>camera.near);assert.ok(projections(doc,camera).every(inside));
  await click('Fit 3D view');near(direction(camera),new Vector3(...sceneViewDirection(doc,second.id)));assert.equal(app.camera,camera);assert.equal(app.host.mounts,1);assert.ok(projections(doc,camera).every(inside));assert.equal(app.commits,0);assert.equal(app.selections,0);assert.equal(JSON.stringify(doc),before);
});

test('independent: current camera fits supported tiny and large scenes across narrow and wide aspects',async t=>{
  for(const scale of [1e-4,1,1e4])await t.test('scene scale '+scale,async st=>{
    const doc=structuredClone(flat);doc.arrays=[];doc.roofs[0].origin_enu=[0,0,0];doc.roofs[0].boundary_uv=[[0,0],[20*scale,0],[20*scale,10*scale],[0,10*scale]];
    const app=await mount(st,{document:doc});for(const[w,h]of[[140,1200],[390,700],[1440,700],[2400,300]]){await app.resize(w,h);assert.equal(app.camera.aspect,w/h);assert.ok(Number.isFinite(app.camera.near)&&app.camera.near>0);assert.ok(Number.isFinite(app.camera.far)&&app.camera.far>app.camera.near);assert.ok(projections(doc,app.camera).every(inside));}
    assert.equal(app.commits,0);
  });
});

test('independent: Fit during pending renderer init does not invalidate ownership, and failure/retry/backend retain their existing generation guards',async t=>{
  const init=WebGPURenderer.prototype.init,dispose=WebGPURenderer.prototype.dispose,gate=deferred();let starts=0,released=0,backendReleased=0,mode='pending';
  WebGPURenderer.prototype.init=async function(){starts++;this.backend.dispose=()=>{backendReleased++;};if(mode==='pending')await gate.promise;if(mode==='fail')throw new Error('controlled-init-failure');};
  WebGPURenderer.prototype.dispose=function(){released++;};t.after(()=>{WebGPURenderer.prototype.init=init;WebGPURenderer.prototype.dispose=dispose;});
  const app=await mount(t),factory=app.host.props.gl;let result,pending;await act(async()=>{pending=factory({canvas:app.host.store.getState().gl.domElement});});await until(()=>starts===1);
  await click('Fit 3D view');assert.equal(app.host.mounts,1);await act(async()=>{gate.resolve();result=await pending;});assert.ok(result);assert.equal(starts,1);assert.equal(app.host.mounts,1);
  const lateLoss=result.onDeviceLost;
  await act(async()=>document.querySelector('.lp-scene-view input[type=checkbox]').click());assert.equal(app.host.mounts,2);await act(async()=>lateLoss());assert.equal(button('Retry 3D'),undefined,'a former renderer cannot fail the replacement');
  mode='fail';await act(async()=>{await assert.rejects(app.host.props.gl({canvas:app.host.store.getState().gl.domElement}),/controlled-init-failure/);});assert.ok(button('Retry 3D'));assert.ok(released>=1);assert.ok(backendReleased>=1);assert.equal(button('Fit 3D view').disabled,true);
  mode='success';await click('Retry 3D');assert.equal(app.host.mounts,3);await act(async()=>{result=await app.host.props.gl({canvas:app.host.store.getState().gl.domElement});});assert.ok(result.backend.isWebGLBackend);assert.equal(app.commits,0);result.dispose();
});

test('SPEC COUNTEREXAMPLE: selected panel instance must use its owning second roof for explicit Fit',async t=>{
  const doc=structuredClone(flat),second={...doc.roofs[0],id:'second-roof',...roofPlane(89.9,0,[25,0,4])};doc.roofs.push(second);doc.arrays[0].roof_id=second.id;
  const pose=panelPoses(doc)[0];assert.equal(pose.roof_id,second.id);const app=await mount(t,{document:doc});await app.render({selected:pose.id});await click('Fit 3D view');
  const normal=new Vector3(...toRender(cross(second.u_axis_enu,second.v_axis_enu))),view=direction(app.camera);console.log(JSON.stringify({case:'selected-panel-roof',selected:pose.id,roof:pose.roof_id,dot:view.dot(normal),actual:view.toArray(),expected:sceneViewDirection(doc,second.id)}));
  assert.ok(view.dot(normal)>.5,'the selected real panel instance must not fall back to the nearly edge-on first-roof composition');near(view,new Vector3(...sceneViewDirection(doc,second.id)));assert.equal(app.commits,0);
});

test('SPEC COUNTEREXAMPLE: resize must fit current geometry extents after an ordinary document edit without resetting its direction',async t=>{
  const app=await mount(t),camera=app.camera,doc=structuredClone(flat);doc.obstacles.push({id:'new-tower',name:'Synthetic tall object',source_id:'survey',roof_id:doc.roofs[0].id,footprint_uv:[[1,1],[2,1],[2,2],[1,2]],extrusion_axis_enu:[0,0,1],height_m:300});
  const originalPosition=camera.position.clone(),beforeDirection=direction(camera);await app.render({document:readGeometry(doc,policy),poses:panelPoses(doc)});near(camera.position,originalPosition);await app.resize(390,700);near(direction(camera),beforeDirection);const resized=projections(doc,camera),outside=resized.filter(p=>!inside(p));
  await click('Fit 3D view');const fitted=projections(doc,camera);assert.ok(fitted.every(inside),'the same current scene is fully supported when Fit is explicitly requested');assert.equal(app.host.mounts,1);assert.equal(app.commits,0);console.log(JSON.stringify({case:'resize-current-extent',outsideAfterResize:outside.length,examples:outside.slice(0,3),allInsideAfterExplicitFit:fitted.every(inside)}));
  assert.equal(outside.length,0,'resize used stale last-Fit bounds instead of the current scene extent');
});
