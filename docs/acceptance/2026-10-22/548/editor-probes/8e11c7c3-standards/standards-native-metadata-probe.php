<?php
declare(strict_types=1);
$root=__DIR__.'/native-metadata-case/';
@mkdir($root.'build/planner/assets',0777,true);
file_put_contents($root.'build/planner/assets/planner.js','// synthetic entry bytes');
function plugin_dir_path($p){return $GLOBALS['root'];}
function plugin_dir_url($p){return 'https://fixture.invalid/wp-content/plugins/linker-tools/';}
function wp_register_script_module(...$args){$GLOBALS['registered']=$args;}
function wp_set_script_module_translations(...$args){}
function is_admin(){return false;}
function wp_enqueue_script(...$args){}
function wp_enqueue_script_module(...$args){}
function rest_url($p){return 'https://fixture.invalid/wp-json/'.$p;}
function admin_url($p){return 'https://fixture.invalid/wp-admin/'.$p;}
function add_query_arg($k,$v,$p){return $p.'?'.$k.'='.$v;}
function determine_locale(){return 'en_GB';}
function wp_json_encode($v){return json_encode($v);}
function esc_attr($v){return htmlspecialchars($v,ENT_QUOTES);}
function esc_html__($v,$domain){return $v;}
require __DIR__.'/plugins/linker-tools/includes/Planner/Gateway.php';
require __DIR__.'/plugins/linker-tools/includes/Planner/Application.php';
$good='assets/SceneViewport-ab_CD-12.js';
$cases=[$good,null,17,'assets/SceneViewport-hash.js?x=1','assets/SceneViewport-hash.js#fragment','assets/../SceneViewport-hash.js','assets/SceneViewport-%2f.js','https://foreign.invalid/SceneViewport-hash.js','assets/SceneViewport-hash.mjs','assets/SceneViewport-.js'];
foreach($cases as $case){
 $manifest=['src/main.tsx'=>['file'=>'assets/planner.js'],'src/components/design/SceneViewport.tsx'=>['file'=>$case]];
 file_put_contents($root.'build/planner/vite-manifest.json',json_encode($manifest));
 $GLOBALS['registered']=null;$app=new Linker\Tools\Planner\Application($root.'plugin.php');$app->assets();$html=$app->mount();
 if(!preg_match('/data-planner-config="([^"]+)"/',$html,$m))throw new RuntimeException('missing configuration');
 $config=json_decode(html_entity_decode($m[1],ENT_QUOTES),true);$expected=$case===$good?'https://fixture.invalid/wp-content/plugins/linker-tools/build/planner/'.$case:null;
 if($config['scene_module_url']!==$expected)throw new RuntimeException('unsafe scene accepted');
 if($GLOBALS['registered'][2]!==[])throw new RuntimeException('site React dependency introduced');
 echo json_encode(['input'=>$case,'scene'=>$config['scene_module_url'],'accepted'=>$expected!==null]).PHP_EOL;
}
unlink($root.'build/planner/vite-manifest.json');unlink($root.'build/planner/assets/planner.js');rmdir($root.'build/planner/assets');rmdir($root.'build/planner');rmdir($root.'build');rmdir($root);
