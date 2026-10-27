import{load as tsxLoad}from"./tsx-loader.mjs";
export async function load(url,context,nextLoad){if(url.endsWith("/SceneViewport.tsx"))throw new Error("synthetic_3d_chunk_load_failure");return tsxLoad(url,context,nextLoad);}
