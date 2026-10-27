import fs from 'node:fs';
import ts from './apps/planner/node_modules/typescript/lib/typescript.js';
const path='./apps/planner/src/components/design/SceneViewport.tsx';
const source=ts.createSourceFile(path,fs.readFileSync(path,'utf8'),ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
let callback;
function visit(n){if(ts.isJsxAttribute(n)&&n.name.getText(source)==='gl')callback=n.initializer.expression.getText(source);ts.forEachChild(n,visit);}visit(source);
let created=0,disposed=0,failed=0;
class Renderer{constructor(){created++;}async init(){throw new Error('synthetic_gpu_init_failure');}async dispose(){disposed++;}}
const js=ts.transpileModule(`const callback=${callback}; return callback;`,{compilerOptions:{target:ts.ScriptTarget.ES2024,module:ts.ModuleKind.None}}).outputText;
const fn=new Function('generation','WebGPURenderer','forceWebGL','alive','setFailed','setBackend',js)({current:0},Renderer,false,{current:true},()=>failed++,()=>{});
let error;try{await fn({canvas:{}});}catch(e){error=e.message;}
console.log(JSON.stringify({case:'extracted_original_renderer_factory_rejection',created,disposed,failed,error}));
if(created!==1||disposed!==0||failed!==1)throw new Error('unexpected probe result');
