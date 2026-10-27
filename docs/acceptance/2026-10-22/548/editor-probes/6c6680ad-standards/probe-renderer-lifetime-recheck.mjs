import fs from 'node:fs';
import assert from 'node:assert/strict';
import ts from './apps/planner/node_modules/typescript/lib/typescript.js';
import {releaseBackend,releaseUnownedRenderer}from'./apps/planner/src/domain/renderLifetime.ts';
const file='./apps/planner/src/components/design/SceneViewport.tsx';
const source=ts.createSourceFile(file,fs.readFileSync(file,'utf8'),ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);let factory;
function visit(n){if(ts.isJsxAttribute(n)&&n.name.getText(source)==='gl')factory=n.initializer.expression.getText(source);ts.forEachChild(n,visit);}visit(source);
const js=ts.transpileModule(`const callback=${factory};return callback;`,{compilerOptions:{target:ts.ScriptTarget.ES2024,module:ts.ModuleKind.None}}).outputText;
const outputs=[];
for(const mode of ['failed','fallback_failed','fallback_success','late_generation','cleanup_errors']){
 const calls=[],generation={current:0};let failed=0;
 const initial={async dispose(){calls.push('initial');if(mode==='cleanup_errors')throw Error('cleanup_backend_failure');}};
 const current={isWebGLBackend:true,async dispose(){calls.push('fallback');}};
 class Renderer{constructor(){this.backend=initial;this.initialized=false;}async init(){if(mode.startsWith('fallback'))this.backend=current;if(mode==='failed'||mode==='fallback_failed'||mode==='cleanup_errors')throw Error('synthetic_gpu_init_failure');this.initialized=true;if(mode==='late_generation')generation.current++;}async dispose(){calls.push('renderer');if(this.initialized)await this.backend.dispose();if(mode==='cleanup_errors')throw Error('cleanup_renderer_failure');}}
 const fn=new Function('generation','WebGPURenderer','forceWebGL','alive','setFailed','setBackend','releaseBackend','releaseUnownedRenderer',js)(generation,Renderer,false,{current:true},()=>failed++,()=>{},releaseBackend,releaseUnownedRenderer);
 let error=null,result;try{result=await fn({canvas:{}});}catch(e){error=e.message;}
 if(mode==='fallback_success'){assert.ok(result);assert.deepEqual(calls,['initial']);assert.equal(failed,0);}else{assert.equal(error,mode==='late_generation'?'scene_unmounted':'synthetic_gpu_init_failure');assert.ok(calls.includes('renderer'));assert.equal(calls.filter(x=>x==='initial').length,1);if(mode==='fallback_failed')assert.ok(calls.includes('fallback'));}
 outputs.push({mode,calls,failed,error,returnedRenderer:!!result});
}
console.log(JSON.stringify(outputs,null,2));
