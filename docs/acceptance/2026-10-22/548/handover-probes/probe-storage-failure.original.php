<?php
declare(strict_types=1);
const DAY_IN_SECONDS=86400;
const HOUR_IN_SECONDS=3600;
const DB_NAME='synthetic-review';
const LINKER_GENIE_SERVICE_TOKEN='synthetic-review-only';
class WP_Error {public function __construct(public string $code='',public string $message='',public mixed $data=null){}public function get_error_code(){return $this->code;}public function get_error_data(){return $this->data;}}
function __($s,$d=''){return $s;}
function is_wp_error($x){return $x instanceof WP_Error;}
function wp_hash($data,$scheme='auth',$algo='md5'){return hash_hmac($algo,$data,'synthetic-'.$scheme);}
function wp_salt($scheme='auth'){return 'synthetic-'.$scheme;}
function wp_json_encode($x,$flags=0){return json_encode($x,$flags);}
function wp_is_uuid($x,$v=4){return preg_match('/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/D',$x)===1;}
function get_current_user_id(){return 0;}
function sanitize_text_field($x){return $x;}
function wp_unslash($x){return $x;}
function wp_cache_delete(...$args){}
function get_option($name,$default=false){global $wpdb;if($name==='linker_planner_url')return 'https://engine.invalid';return $name==='linker_public_admission_ledger'?($wpdb->raw??false):$default;}
function wp_remote_retrieve_response_code($x){return $x['response']['code'];}
function wp_remote_retrieve_body($x){return $x['body'];}
function wp_remote_retrieve_header($x,$key){return $x['headers'][$key]??'';}
class MemoryDb {public $prefix='wp_';public $options='wp_options';public ?string $raw=null;function prepare($sql,...$args){return [$sql,$args];}function get_var($q){[$s,$a]=$q;if(str_contains($s,'GET_LOCK')||str_contains($s,'RELEASE_LOCK'))return '1';return $this->raw;}function query($q){[$s,$a]=$q;if(str_starts_with($s,'INSERT IGNORE')){$this->raw??=$a[1];return 1;}if(str_starts_with($s,'UPDATE')){if($GLOBALS['failStorage']??false)return false;if($this->raw!==$a[2])return 0;$this->raw=$a[0];return 1;}throw new Exception($s);}}
$wpdb=new MemoryDb;
spl_autoload_register(function($class){foreach(['Linker\\Commerce\\'=>__DIR__.'/plugins/linker-commerce/includes/','Linker\\Tools\\'=>__DIR__.'/plugins/linker-tools/includes/']as$p=>$dir){if(str_starts_with($class,$p)){require $dir.str_replace('\\','/',substr($class,strlen($p))).'.php';return;}}});
use Linker\Commerce\Protection\{Identity,Allowance,Ledger};
use Linker\Tools\Planner\{Principal,Admission,Transport};
$_COOKIE[Identity::COOKIE]=str_repeat('a',32);
$quota=Identity::current();$principal=new Principal('guest','wp:1:guest:'.str_repeat('b',64));
$key='11111111-1111-4111-8111-111111111111';$hash=str_repeat('c',64);$command=['schema_version'=>1,'title'=>'Synthetic request','inputs'=>(object)[],'key'=>$key];$body=json_encode($command);
$admission=new Admission;$fp=(new ReflectionMethod(Admission::class,'fingerprint'))->invoke($admission,$principal,'projects/create','create',$hash);
$limits=[new Allowance('planner_projects',$quota->browser,10,DAY_IN_SECONDS),new Allowance('planner_projects_site','site',500,DAY_IN_SECONDS)];

$resolve=new ReflectionMethod(Admission::class,'operation_id');
$depth=(int)($argv[1]??5);$mode=$argv[2]??'expired';$confirmed=in_array('confirmed',$argv,true);$ids=[];
for($i=0;$i<$depth;$i++){
 $id=$resolve->invoke($admission,$principal,$key,$quota->binding(),$fp);
 if(is_wp_error($id))throw new RuntimeException('could not prepare requested layer '.$i.':'.$id->get_error_code());
 if(in_array($id,$ids,true))throw new RuntimeException('resurrected terminal receipt');
 $ids[]=$id;$l=new Ledger($mode==='expired'?static fn()=>time()-31:null);
 $r=$l->reserve($id,$fp,$limits,30,[],'planner_write',$quota->binding(),$quota->owners());
 if(is_wp_error($r))throw new RuntimeException('fixture reserve failed');
 if($mode==='cancelled')$l->cancel($id,$fp);
 if($mode==='erased'){$l->privacy([$limits[0]->owner()],true);break;}
}
if($ids)(new Ledger())->lookup_context(end($ids),$fp,'planner_write',$quota->binding());
$before=json_decode($wpdb->raw,true);$mutations=0;$GLOBALS['failStorage']=in_array('storage-fail',$argv,true);
$transport=new Transport(function($url,$args)use(&$mutations,$hash,$confirmed){
 if(str_contains($url,'/operations/replay/')){$x=['schema_version'=>1,'status'=>$confirmed?'replayed':'absent','command_scope'=>'create','command_sha256'=>$hash];if($confirmed)$x['result']=['id'=>str_repeat('d',32),'revision'=>1];}
 else{$mutations++;$x=['id'=>str_repeat('d',32),'revision'=>1];}
 return ['response'=>['code'=>200],'headers'=>['content-type'=>'application/json'],'body'=>json_encode($x)];
});
$result=$admission->send($principal,'projects/create',$command,$body,$transport);$after=json_decode($wpdb->raw,true);
$unchanged=true;foreach($before['receipts'] as $id=>$r)if(($after['receipts'][$id]??null)!==$r)$unchanged=false;
echo json_encode(['depth'=>$depth,'mode'=>$mode,'permanent_engine_receipt'=>$confirmed,'status'=>is_wp_error($result)?$result->get_error_code():$result['status'],'http'=>is_wp_error($result)?$result->get_error_data()['status']:$result['status'],'count_before'=>count($before['receipts']),'count_after'=>count($after['receipts']),'used_before'=>array_sum(array_column($before['buckets'],'used')),'used_after'=>array_sum(array_column($after['buckets'],'used')),'old_receipts_unchanged'=>$unchanged,'mutation_calls'=>$mutations]),PHP_EOL;
