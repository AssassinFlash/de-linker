import test from 'node:test';import assert from 'node:assert/strict';import {JSDOM} from 'jsdom';import {readConfiguration} from '../src/data/config.ts';
test('entry origin/directory controls executable metadata despite hostile document base and encoded traversal',()=>{
 const dom=new JSDOM('<base href="https://foreign.invalid/"><section></section>',{url:'https://fixture.invalid/workspace/'});
 try{const element=dom.window.document.querySelector('section'),entry='https://fixture.invalid/wp-content/plugins/linker-tools/build/planner/assets/planner.js?ver=current';
 const prefix='https://fixture.invalid/wp-content/plugins/linker-tools/build/planner/assets/';
 const configure=scene=>{element.dataset.plannerConfig=JSON.stringify({base_url:'/api/',nonce_url:'/nonce/',locale:'de_DE_formal',countries:{DE:'Deutschland'},scene_module_url:scene});return readConfiguration(element,entry);};
 assert.equal(configure(prefix+'SceneViewport-ab_CD-12.js').sceneModuleUrl,prefix+'SceneViewport-ab_CD-12.js');
 for(const value of [
  'SceneViewport-ab_CD-12.js',
  prefix.replace('https://','https://user:pass@')+'SceneViewport-ab_CD-12.js',
  prefix+'../SceneViewport-ab_CD-12.js',
  prefix+'%2e%2e/SceneViewport-ab_CD-12.js',
  prefix+'nested/SceneViewport-ab_CD-12.js',
  prefix+'SceneViewport-ab_CD-12.js?planner_retry=77',
  prefix+'SceneViewport-ab_CD-12.js#fragment',
  prefix+'SceneViewport-ab_CD-12%2ejs',
  prefix+'SceneViewport-ab_CD-12.js/extra',
  prefix+'other.js',
  'data:text/javascript,export default function(){}',
  'javascript:alert(1)',
  'blob:https://fixture.invalid/SceneViewport-hash.js',
  'http://['
 ])assert.throws(()=>configure(value),'unsafe candidate: '+value);
 console.log(JSON.stringify({additionalRejectedCandidates:14,documentBaseCannotChangeTrustOrigin:true}));
 }finally{dom.window.close();}
});
