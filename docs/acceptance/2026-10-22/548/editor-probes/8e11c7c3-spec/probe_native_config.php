<?php
declare(strict_types=1);
namespace Linker\Tools\Planner { final class Gateway { public const NAMESPACE='linker/v1'; public const ROUTE='/planner/'; } }
namespace {
$fixture=__DIR__.'/native-manifest-fixture';
@mkdir($fixture.'/build/planner/assets',0777,true);
file_put_contents($fixture.'/build/planner/assets/planner.js','export {};');
function plugin_dir_path(string $file):string{return dirname($file).'/';}
function plugin_dir_url(string $file):string{return 'https://fixture.invalid/wp-content/plugins/linker-tools/';}
function wp_register_script_module(...$args):void{$GLOBALS['registered'][]=$args;}
function wp_set_script_module_translations(...$args):void{}
function is_admin():bool{return false;}
function wp_enqueue_script(...$args):void{}
function wp_enqueue_script_module(...$args):void{}
function rest_url(string $path):string{return 'https://fixture.invalid/wp-json/'.$path;}
function admin_url(string $path):string{return 'https://fixture.invalid/wp-admin/'.$path;}
function add_query_arg(...$args):string{return 'https://fixture.invalid/wp-admin/admin-ajax.php?action=rest-nonce';}
function determine_locale():string{return 'en_GB';}
function wp_json_encode($data):string|false{return json_encode($data,JSON_THROW_ON_ERROR);}
function esc_attr(string $value):string{return htmlspecialchars($value,ENT_QUOTES);}
function esc_html__(string $value,string $domain):string{return $value;}
require __DIR__.'/plugins/linker-tools/includes/Planner/Application.php';
$cases=['valid'=>'assets/SceneViewport-BQc4p_xn.js','missing'=>null,'query'=>'assets/SceneViewport-abc.js?x=1','fragment'=>'assets/SceneViewport-abc.js#x','external'=>'https://foreign.invalid/SceneViewport-abc.js','relative_escape'=>'../assets/SceneViewport-abc.js','nested'=>'assets/nested/SceneViewport-abc.js','other_module'=>'assets/planner-core-abc.js','bad_extension'=>'assets/SceneViewport-abc.mjs','empty_hash'=>'assets/SceneViewport-.js','linebreak'=>"assets/SceneViewport-abc.js\n",'percent_path'=>'assets/%53ceneViewport-abc.js','wrong_type'=>12,'array'=>[]];
$records=[];
foreach($cases as $name=>$scene){
 $manifest=['src/main.tsx'=>['file'=>'assets/planner.js']];if($name!=='missing')$manifest['src/components/design/SceneViewport.tsx']=['file'=>$scene];
 file_put_contents($fixture.'/build/planner/vite-manifest.json',json_encode($manifest,JSON_THROW_ON_ERROR));
 $GLOBALS['registered']=[];$app=new Linker\Tools\Planner\Application($fixture.'/linker-tools.php');$app->assets();$html=$app->mount();
 if(preg_match('/data-planner-config="([^"]+)"/',$html,$m)!==1)throw new RuntimeException('No config');
 $config=json_decode(html_entity_decode($m[1],ENT_QUOTES),true,512,JSON_THROW_ON_ERROR);$expected=$name==='valid'?'https://fixture.invalid/wp-content/plugins/linker-tools/build/planner/'.$scene:null;
 if($config['scene_module_url']!==$expected)throw new RuntimeException('Unexpected URL for '.$name);
 if(count($GLOBALS['registered'])!==1)throw new RuntimeException('Incorrect entry registration');
 if($app->mount()!=='')throw new RuntimeException('Duplicate mount');
 $records[]=['case'=>$name,'input'=>$scene,'scene_module_url'=>$config['scene_module_url'],'entry_registered_once'=>true,'duplicate_mount_refused'=>true];
}
file_put_contents(__DIR__.'/probe_native_config.results.json',json_encode(['php'=>PHP_VERSION,'method'=>'Actual fixed Application, local manifest variants, native function stubs; not WordPress acceptance','cases'=>$records],JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES)."\n");
echo count($records)." native-manifest cases passed\n";
}
