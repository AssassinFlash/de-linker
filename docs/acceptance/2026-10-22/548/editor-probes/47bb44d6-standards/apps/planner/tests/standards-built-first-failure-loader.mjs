export async function load(url,context,nextLoad){
 const parsed=new URL(url);
 if(/\/SceneViewport-[\w-]+\.js$/.test(parsed.pathname)&&!parsed.search)return {format:'module',shortCircuit:true,source:"throw new Error('synthetic_original_scene_download_failed');"};
 return nextLoad(url,context);
}
