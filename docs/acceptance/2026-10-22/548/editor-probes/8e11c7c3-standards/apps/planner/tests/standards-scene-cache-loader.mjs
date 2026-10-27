export async function load(url,context,nextLoad){
 const parsed=new URL(url);
 if(parsed.pathname.endsWith('/components/design/SceneViewport.tsx')||/\/SceneViewport-[\w-]+\.js$/.test(parsed.pathname))return {format:'module',shortCircuit:true,source:`
 globalThis.__standardsSceneEvaluations.push(import.meta.url);
 if(!new URL(import.meta.url).searchParams.has('planner_retry'))throw new Error('synthetic_cached_module_failure');
 await globalThis.__standardsSceneGate;
 export default function Scene(){return null;}
 `};
 return nextLoad(url,context);
}
