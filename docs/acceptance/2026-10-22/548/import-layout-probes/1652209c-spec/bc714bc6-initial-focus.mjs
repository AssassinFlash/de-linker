import assert from "node:assert/strict";
const app=process.env.PLANNER_SPEC_SNAPSHOT+"/apps/planner";
const {default: React,act}=await import(app+"/node_modules/react/index.js");
const {setupDom}=await import(app+"/tests/dom-fixture.mjs");
const fixture=setupDom(), {createRoot}=await import(app+"/node_modules/react-dom/client.js");
const {GeometryForm,GeometryNumber}=await import(app+"/src/components/design/GeometryForm.tsx");
const root=createRoot(fixture.element), calls=[];
window.HTMLElement.prototype.scrollIntoView=function(options){calls.push({node:this,options});};
try{await act(async()=>root.render(React.createElement(React.StrictMode,null,React.createElement(GeometryForm,{title:"Synthetic focus check",locale:"en-GB",submit:()=>true,cancel:()=>{},onValidity:()=>{}},React.createElement(GeometryNumber,{name:"width",label:"Width",locale:"en-GB",value:12,help:"Synthetic correction context"}),React.createElement(GeometryNumber,{name:"length",label:"Length",locale:"en-GB",value:8})))));
const input=document.querySelector('[name="width"]');assert.equal(document.activeElement,input);assert.ok(calls.length>0);assert.ok(calls.every(call=>call.node===input.closest("label")));assert.ok(calls.every(call=>call.options.block==="start"&&call.options.behavior==="instant"));assert.equal(input.value,"12");console.log(JSON.stringify({snapshot:"1652209cb0deef904adc70baba9770c8f8ed61b7",appliesToTarget:"bc714bc628f1555d2ddcbface216dabc7b9371d5",initialFocusedField:input.name,revealedLabel:input.closest("label").textContent,revealCalls:calls.length,strictMode:true,nativeBrowser:false},null,2));}finally{await fixture.dispose(root);}
