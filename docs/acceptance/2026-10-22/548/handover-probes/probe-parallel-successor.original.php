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
class MemoryDb {public $prefix='wp_';public $options='wp_options';public ?string $raw=null;function prepare($sql,...$args){return [$sql,$args];}function get_var($q){[$s,$a]=$q;if(str_contains($s,'GET_LOCK')||str_contains($s,'RELEASE_LOCK'))return '1';return $this->raw;}function query($q){[$s,$a]=$q;if(str_starts_with($s,'INSERT IGNORE')){$this->raw??=$a[1];return 1;}if(str_starts_with($s,'UPDATE')){if($this->raw!==$a[2])return 0;$this->raw=$a[0];return 1;}throw new Exception($s);}}
$wpdb=new MemoryDb;
spl_autoload_register(function($class){foreach(['Linker\\Commerce\\'=>__DIR__.'/plugins/linker-commerce/includes/','Linker\\Tools\\'=>__DIR__.'/plugins/linker-tools/includes/']as$p=>$dir){if(str_starts_with($class,$p)){require $dir.str_replace('\\','/',substr($class,strlen($p))).'.php';return;}}});
use Linker\Commerce\Protection\{Identity,Allowance,Ledger};
use Linker\Tools\Planner\{Principal,Admission,Transport};
$_COOKIE[Identity::COOKIE]=str_repeat('a',32);
$quota=Identity::current();$principal=new Principal('guest','wp:1:guest:'.str_repeat('b',64));
$key='11111111-1111-4111-8111-111111111111';$hash=str_repeat('c',64);$command=['schema_version'=>1,'title'=>'Synthetic request','inputs'=>(object)[],'key'=>$key];$body=json_encode($command);
$admission=new Admission;$fp=(new ReflectionMethod(Admission::class,'fingerprint'))->invoke($admission,$principal,'projects/create','create',$hash);
$limits=[new Allowance('planner_projects',$quota->browser,10,DAY_IN_SECONDS),new Allowance('planner_projects_site','site',500,DAY_IN_SECONDS)];


class LockedFileDb extends MemoryDb {
 private $lock=null;private int $reads=0;
 public function __construct(private string $path,private ?int $worker=null){}
 public function get_var($q){[$s,$a]=$q;
  if(str_contains($s,'GET_LOCK')){$this->lock=fopen($this->path.'.lock','c+');flock($this->lock,LOCK_EX);$this->reads++;return '1';}
  if(str_contains($s,'RELEASE_LOCK')){flock($this->lock,LOCK_UN);fclose($this->lock);$this->lock=null;
   if($this->worker!==null&&$this->reads===5){file_put_contents($this->path.'.ready'.$this->worker,'ready');$start=microtime(true);while(!is_file($this->path.'.ready'.(1-$this->worker))){if(microtime(true)-$start>5)throw new RuntimeException('barrier timed out');usleep(1000);}}
   return '1';}
  $this->raw=is_file($this->path)?file_get_contents($this->path):null;return $this->raw;
 }
 public function query($q){$this->raw=is_file($this->path)?file_get_contents($this->path):null;$result=parent::query($q);file_put_contents($this->path,$this->raw);return $result;}
}
$journal=tempnam(sys_get_temp_dir(),'planner-independent-journal-');unlink($journal);$wpdb=new LockedFileDb($journal);
$resolve=new ReflectionMethod(Admission::class,'operation_id');$ids=[];
for($i=0;$i<3;$i++){$id=$resolve->invoke($admission,$principal,$key,$quota->binding(),$fp);assert(is_string($id));$ids[]=$id;$l=new Ledger();assert(!is_wp_error($l->reserve($id,$fp,$limits,30,[],'planner_write',$quota->binding(),$quota->owners())));assert(!is_wp_error($l->cancel($id,$fp)));}
$before=json_decode(file_get_contents($journal),true);$children=[];
for($i=0;$i<2;$i++){
 $pid=pcntl_fork();if($pid===-1)throw new RuntimeException('fork failed');
 if($pid===0){try{$wpdb=new LockedFileDb($journal,$i);$mutations=0;$transport=new Transport(function($url,$args)use($hash,&$mutations){if(str_contains($url,'/operations/replay/'))$x=['schema_version'=>1,'status'=>'absent','command_scope'=>'create','command_sha256'=>$hash];else{$mutations++;usleep(50000);$x=['id'=>str_repeat('d',32),'revision'=>1];}return ['response'=>['code'=>200],'headers'=>['content-type'=>'application/json'],'body'=>json_encode($x)];});$r=(new Admission())->send($principal,'projects/create',$command,$body,$transport);if(is_wp_error($r))throw new RuntimeException($r->get_error_code());file_put_contents($journal.'.result'.$i,json_encode(['status'=>$r['status'],'mutations'=>$mutations]));exit(0);}catch(Throwable $e){file_put_contents($journal.'.result'.$i,json_encode(['error'=>$e->getMessage()]));exit(1);}}
 $children[]=$pid;
}
$ok=true;foreach($children as $pid){pcntl_waitpid($pid,$status);$ok=$ok&&pcntl_wifexited($status)&&pcntl_wexitstatus($status)===0;}
$after=json_decode(file_get_contents($journal),true);$new=array_values(array_diff(array_keys($after['receipts']),$ids));$unchanged=true;foreach($before['receipts']as$id=>$r)$unchanged=$unchanged&&($after['receipts'][$id]??null)===$r;
$out=['workers'=>[json_decode(file_get_contents($journal.'.result0'),true),json_decode(file_get_contents($journal.'.result1'),true)],'new_attempts'=>count($new),'old_receipts_unchanged'=>$unchanged,'bucket_spend'=>array_values(array_column($after['buckets'],'used')),'barrier_before_atomic_reserve'=>true];echo json_encode($out),PHP_EOL;
foreach(glob($journal.'*') as $f)unlink($f);
if(!$ok||count($new)!==1||!$unchanged||count(array_filter($out['bucket_spend'],static fn($v)=>$v!==1))>0)exit(1);
