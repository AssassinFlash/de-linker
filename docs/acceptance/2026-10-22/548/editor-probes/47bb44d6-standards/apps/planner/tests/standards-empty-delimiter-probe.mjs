import {JSDOM} from 'jsdom';import {readConfiguration} from '../src/data/config.ts';
const dom=new JSDOM('<section></section>',{url:'https://fixture.invalid/workspace/'}),element=dom.window.document.querySelector('section');
const directory='https://fixture.invalid/assets/',entry=directory+'planner.js?ver=fixed';
try{for(const suffix of ['?','#','?#']){
 element.dataset.plannerConfig=JSON.stringify({base_url:'/api/',nonce_url:'/nonce/',locale:'en_GB',countries:{FR:'France'},scene_module_url:directory+'SceneViewport-hash.js'+suffix});
 let accepted=false,result=null;try{result=readConfiguration(element,entry).sceneModuleUrl;accepted=true;}catch{}
 console.log(JSON.stringify({suffix,accepted,result,contractExpected:'reject',severity:'known Spec P3; no executable directory/origin bypass'}));
}}finally{dom.window.close();}
