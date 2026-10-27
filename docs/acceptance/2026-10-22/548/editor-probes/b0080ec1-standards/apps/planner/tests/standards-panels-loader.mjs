import {load as base} from './tsx-loader.mjs';
export async function resolve(specifier,context,nextResolve){
 if(specifier==='@react-three/fiber')return{url:new URL('./standards-panels-host.mjs',import.meta.url).href,shortCircuit:true};
 return nextResolve(specifier,context);
}
export async function load(url,context,nextLoad){
 const out=await base(url,context,nextLoad);
 if(url.endsWith('/SceneViewport.tsx'))return {...out,source:out.source.replaceAll('"react/jsx-runtime"',JSON.stringify(new URL('./standards-group-jsx.mjs',import.meta.url).href))+'\nexport {Panels as StandardsPanels};'};
 return out;
}
