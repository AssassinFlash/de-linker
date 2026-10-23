import test from 'node:test';import assert from 'node:assert/strict';import React,{act} from 'react';
import {setupDom} from './dom-fixture.mjs';
import flat from '../../../fixtures/planning/geometry-flat.json' with {type:'json'};
import {panelPoses} from '../src/domain/panelPoses.ts';
import {applyGeometryCommand} from '../src/domain/geometryCommands.ts';
for(const mode of ['normal_finish','escape','blur','pointercancel','lostpointercapture','disabled','geometry_render','geometry_before_render','pan_tool','zoom','fit','unmount'])test('plan preview '+mode,async t=>{
 const fixture=setupDom(),{createRoot}=await import('react-dom/client'),{PlanViewport}=await import('../src/components/design/PlanViewport.tsx');
 const oldPoint=Object.getOwnPropertyDescriptor(globalThis,'DOMPoint');
 globalThis.DOMPoint=class {constructor(x,y){this.x=x;this.y=y;}matrixTransform(){return this;}};
 const captures=new Set();let releases=0,calls=0,accepted=0,current=structuredClone(flat),disabled=false;
 fixture.dom.window.SVGElement.prototype.getScreenCTM=()=>({a:1,d:1,inverse(){return this;}});
 fixture.dom.window.SVGElement.prototype.setPointerCapture=id=>captures.add(id);
 fixture.dom.window.SVGElement.prototype.hasPointerCapture=id=>captures.has(id);
 fixture.dom.window.SVGElement.prototype.releasePointerCapture=id=>{captures.delete(id);releases++;};
 const root=createRoot(fixture.element);
 const draw=()=>React.createElement(React.StrictMode,null,React.createElement(PlanViewport,{document:current,roof:current.roofs[0],poses:panelPoses(current),selected:current.arrays[0].id,select(){},disabled,commit(command){calls++;try{current=applyGeometryCommand(current,command);accepted++;return true;}catch{return false;}}}));
 t.after(async()=>{await fixture.dispose(root);if(oldPoint)Object.defineProperty(globalThis,'DOMPoint',oldPoint);else delete globalThis.DOMPoint;});
 await act(async()=>root.render(draw()));
 const svg=document.querySelector('svg'),polygon=document.querySelector('polygon[data-array]');
 function pointer(target,type,x,y){const event=new window.MouseEvent(type,{clientX:x,clientY:y,button:0,bubbles:true});Object.defineProperty(event,'pointerId',{value:7});target.dispatchEvent(event);}
 await act(async()=>{pointer(polygon,'pointerdown',2,3);pointer(svg,'pointermove',7,3);});
 assert.match(document.querySelector('g[data-array]').getAttribute('transform'),/^translate/);assert.equal(captures.has(7),true);
 await act(async()=>{
  if(mode==='escape')window.dispatchEvent(new window.KeyboardEvent('keydown',{key:'Escape'}));
  else if(mode==='blur')window.dispatchEvent(new Event('blur'));
  else if(mode==='pointercancel')pointer(svg,'pointercancel',7,3);
  else if(mode==='lostpointercapture'){captures.delete(7);pointer(svg,'lostpointercapture',7,3);}
  else if(mode==='disabled'){disabled=true;root.render(draw());}
  else if(mode.startsWith('geometry_')){current={...current,module_specs:current.module_specs.map(m=>({...m,length_m:3}))};if(mode==='geometry_render')root.render(draw());}
  else if(mode==='unmount')root.render(null);
  else if(['pan_tool','zoom','fit'].includes(mode)){
   const label={pan_tool:'Pan view',zoom:'Zoom in',fit:'Fit view'}[mode];
   [...document.querySelectorAll('button')].find(b=>(b.getAttribute('aria-label')??b.textContent.trim())===label).click();
  }
 });
 if(mode!=='unmount')await act(async()=>pointer(svg,'pointerup',7,3));
 assert.equal(accepted,mode==='normal_finish'?1:0);
 assert.equal(calls,mode==='normal_finish'||mode==='geometry_before_render'?1:0);
 // JSDOM has no native capture/disconnection. Do not assert its Map against browser auto-release on unmount.
 if(mode!=='unmount')assert.equal(captures.size,0);
 if(mode!=='unmount')assert.equal(document.querySelector('g[data-array]').getAttribute('transform'),null);
 console.log(JSON.stringify({mode,calls,accepted,releases,remainingCaptures:captures.size}));
});
