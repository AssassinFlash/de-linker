import assert from 'node:assert/strict';
import test from 'node:test';
import React,{act} from 'react';
import {create} from 'zustand';
import {context} from '@react-three/fiber';
import {PerspectiveCamera,Vector3} from 'three/webgpu';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {setupDom} from './dom-fixture.mjs';
import {SceneCamera} from '../src/components/design/SceneCamera.tsx';

const near=(a,b)=>assert.ok(a.distanceTo(b)<1e-9,JSON.stringify({actual:a.toArray(),expected:b.toArray()}));
const facing=camera=>camera.getWorldDirection(new Vector3()).negate();
const extent=(x=0,size=20)=>({centre:new Vector3(x,4,-3),size,direction:[.3,.9,.3].map(n=>n/Math.sqrt(.99))});

async function rig(t,{strict=false}={}){
 const dom=setupDom(),{createRoot}=await import('react-dom/client'),camera=new PerspectiveCamera(75,1,.1,2000),canvas=document.createElement('canvas');
 Object.defineProperties(canvas,{clientWidth:{get:()=>store.getState().size.width},clientHeight:{get:()=>store.getState().size.height}});
 let invalidations=0,instances=[],disposed=[],done=false;
 const connect=OrbitControls.prototype.connect,dispose=OrbitControls.prototype.dispose;
 OrbitControls.prototype.connect=function(...args){instances.push(this);return connect.apply(this,args);};
 OrbitControls.prototype.dispose=function(...args){disposed.push(this);return dispose.apply(this,args);};
 const store=create(()=>({camera,gl:{domElement:canvas},size:{width:1440,height:700},invalidate(){invalidations++;}}));
 const root=createRoot(dom.element);let props={extent:extent(),request:0};
 async function render(changes={}){props={...props,...changes};let node=React.createElement(context.Provider,{value:store},React.createElement(SceneCamera,props));if(strict)node=React.createElement(React.StrictMode,null,node);await act(async()=>root.render(node));}
 async function finish(){if(done)return;done=true;await dom.dispose(root);OrbitControls.prototype.connect=connect;OrbitControls.prototype.dispose=dispose;}
 t.after(finish);await render();
 return{camera,canvas,store,instances,disposed,render,finish,get invalidations(){return invalidations;},get controls(){return instances.at(-1);},async resize(width,height){await act(async()=>store.setState({size:{width,height}}));}};
}

test('independent actual OrbitControls: current target, pan/orbit preservation and latest extent agree after Fit/resize',async t=>{
 const app=await rig(t),controls=app.controls;near(controls.target,extent().centre);
 const shift=new Vector3(17,2,-9);controls.target.add(shift);app.camera.position.add(shift);controls.update();
 const oldPosition=app.camera.position.clone(),oldTarget=controls.target.clone(),oldDirection=facing(app.camera);
 await app.render({extent:extent(80,500)});near(app.camera.position,oldPosition);near(controls.target,oldTarget);near(facing(app.camera),oldDirection);assert.equal(app.instances.length,1);
 await app.resize(390,700);near(controls.target,extent(80,500).centre);near(facing(app.camera),oldDirection);assert.equal(app.instances.length,1);
 const afterResize=app.camera.position.clone();controls.update();near(app.camera.position,afterResize);near(facing(app.camera),oldDirection);
 await app.render({extent:{...extent(-150,60),direction:[0,Math.SQRT1_2,Math.SQRT1_2]},request:1});near(controls.target,extent(-150,60).centre);near(facing(app.camera),new Vector3(0,Math.SQRT1_2,Math.SQRT1_2));
 const beforeWheel=app.camera.position.clone();await act(async()=>app.canvas.dispatchEvent(new window.WheelEvent('wheel',{deltaY:100,cancelable:true})));assert.ok(app.camera.position.distanceTo(beforeWheel)>0);near(controls.target,extent(-150,60).centre);
 const valid=app.camera.position.clone();await app.resize(0,700);near(app.camera.position,valid);await app.render({extent:extent(900,70)});near(app.camera.position,valid);const direction=facing(app.camera);await app.resize(390,700);near(controls.target,extent(900,70).centre);near(facing(app.camera),direction);assert.ok(app.camera.near>0&&app.camera.far>app.camera.near);
 console.log(JSON.stringify({case:'orbit-target-synchronization',controllers:app.instances.length,currentTarget:controls.target.toArray(),finiteClipping:[app.camera.near,app.camera.far]}));
});

test('independent actual OrbitControls: StrictMode disposes old listeners, transform pauses/resumes and final unmount is inert',async t=>{
 const app=await rig(t,{strict:true});assert.equal(app.instances.length,2);assert.equal(app.disposed.length,1);assert.equal(app.disposed[0],app.instances[0]);
 const [old,active]=app.instances;assert.equal(old.enabled,true);assert.equal(active.enabled,true);
 app.canvas.dispatchEvent(new window.Event('planner-transform-start'));assert.equal(active.enabled,false);assert.equal(old.enabled,true);
 const paused=app.camera.position.clone();await act(async()=>app.canvas.dispatchEvent(new window.WheelEvent('wheel',{deltaY:100,cancelable:true})));near(app.camera.position,paused);
 app.canvas.dispatchEvent(new window.Event('planner-transform-end'));assert.equal(active.enabled,true);await act(async()=>app.canvas.dispatchEvent(new window.WheelEvent('wheel',{deltaY:100,cancelable:true})));assert.ok(app.camera.position.distanceTo(paused)>0);
 const before=app.invalidations;old.dispatchEvent({type:'change'});assert.equal(app.invalidations,before);active.dispatchEvent({type:'change'});assert.equal(app.invalidations,before+1);
 await app.finish();assert.equal(app.disposed.length,2);assert.equal(new Set(app.disposed).size,2);active.enabled=true;app.canvas.dispatchEvent(new window.Event('planner-transform-start'));assert.equal(active.enabled,true);const ended=app.invalidations;active.dispatchEvent({type:'change'});assert.equal(app.invalidations,ended);
 console.log(JSON.stringify({case:'actual-orbit-strict-cleanup',constructed:app.instances.length,disposed:app.disposed.length,pauseResumeWheelVerified:true,oldAndUnmountedListenersInert:true}));
});
