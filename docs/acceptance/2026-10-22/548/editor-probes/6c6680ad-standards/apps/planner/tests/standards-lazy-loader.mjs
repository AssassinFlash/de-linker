import { load as originalLoad } from './tsx-loader.mjs';
export async function load(url,context,nextLoad){
 if(url.endsWith('/SceneViewport.tsx'))return{format:'module',shortCircuit:true,source:'throw new Error("synthetic_3d_chunk_unavailable"); export default function SceneViewport(){}'};
 return originalLoad(url,context,nextLoad);
}
