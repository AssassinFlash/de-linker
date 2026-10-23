import {load as tsxLoad} from "./tsx-loader.mjs";
export async function resolve(specifier,context,nextResolve){if(specifier==="@react-three/fiber")return{url:new URL("./spec-r3f-host.mjs",import.meta.url).href,shortCircuit:true};return nextResolve(specifier,context);}
export const load=tsxLoad;
