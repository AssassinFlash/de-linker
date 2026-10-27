import {load}from'./tsx-loader.mjs';export{load};
export async function resolve(specifier,context,nextResolve){if(specifier==='@react-three/fiber')return{url:new URL('./standards-r3f-host.mjs',import.meta.url).href,shortCircuit:true};return nextResolve(specifier,context);}
