import {load as transpile} from './tsx-loader.mjs';
export async function load(url,context,nextLoad){
 if(new URL(url).pathname.endsWith('/components/design/SceneViewport.tsx'))return{format:'module',shortCircuit:true,source:`import React from 'react'; await globalThis.__specSceneEvaluate(import.meta.url); export default function ControlledScene(){return React.createElement('p',{'data-spec-recovered-scene':'true'},'Controlled transport fixture; no GPU');}`};
 return transpile(url,context,nextLoad);
}
