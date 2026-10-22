<?php
/** Native submission-to-mail authorization boundary; no external delivery.
 *
 * @package Linker\Commerce
 */
declare( strict_types = 1 );
namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Contact\Submission;
use Linker\Commerce\Inquiry\Sender;
use Linker\Commerce\Inquiry\Assessment\Queue;
use Linker\Commerce\Mail\OptionBudgetLedger;
use Linker\Commerce\Mail\Throttle;
use WC_Order;
/** @coversNothing */
final class PreSendAuthorizationTest extends IntegrationTestCase {
	protected function setUp(): void {
		parent::setUp();
		foreach ( array( Queue::ENABLED, Queue::HEARTBEAT, 'linker_genie_url' ) as $name ) {
			$old = get_option( $name );
			$this->later(
				static function () use ( $name, $old ): void {
					false === $old ? delete_option( $name ) : update_option( $name, $old, false );
				}
			);
		}
		update_option( Queue::ENABLED, 'yes' );
		update_option( Queue::HEARTBEAT, microtime( true ) );
		update_option( 'linker_genie_url', '' );
	}
	private function submit(): WC_Order {
		$details = Submission::from_post(
			array(
				'name'    => 'Synthetic installer',
				'email'   => self::TESTER,
				'company' => 'Fixture EPC',
				'message' => 'Please quote a 10 kWh battery; full original content.',
				'consent' => '1',
			)
		);
		self::assertInstanceOf( Submission::class, $details );
		$order = ( new Sender() )->message( $details );
		$this->later(
			static function () use ( $order ): void {
				foreach ( array( Queue::PROCESS, Queue::EXPIRE ) as $hook ) {
					as_unschedule_all_actions( $hook, array( $order->get_id() ), \Linker\Commerce\Mail\Outbox::GROUP );
				} delete_option( \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::PREFIX . $order->get_id() );
				$order->delete( true );
			}
		);
		return $order;
	}
	public function test_unavailable_assessment_preserves_complete_record_without_receipt_team_or_budget(): void {
		$attempts = 0;
		$observe  = static function () use ( &$attempts ): void {
			++$attempts;
		};
		add_action( 'phpmailer_init', $observe, PHP_INT_MAX );
		$this->later(
			static function () use ( $observe ): void {
				remove_action( 'phpmailer_init', $observe, PHP_INT_MAX );
			}
		);
		$budget = get_option( OptionBudgetLedger::OPTION );
		$legacy = get_option( Throttle::OPTION );
		$order  = $this->submit();
		self::assertSame( 'Please quote a 10 kWh battery; full original content.', $order->get_customer_note() );
		self::assertSame( 0, $attempts );
		self::assertSame( $budget, get_option( OptionBudgetLedger::OPTION ) );
		self::assertSame( $legacy, get_option( Throttle::OPTION ) );
	}
	private function provider( string $decision ): void {
		require_once dirname( __DIR__, 2 ) . '/fixtures/AssessmentFixtureEnvironment.php';
		\Linker\Commerce\Tests\Fixtures\AssessmentFixtureEnvironment::configure();
		update_option( 'linker_genie_url', 'http://127.0.0.1:9' );
		$reply = static function ( $pre, $args, $url ) use ( $decision ) {
			if ( ! str_ends_with( $url, '/inquiries/assess' ) ) {
				return $pre; }
			$request = json_decode( $args['body'], true );
			$basis   = 'malicious' === $decision ? 'fraud_or_phishing' : ( 'normal' === $decision ? 'business_request' : 'insufficient_context' );
			$raw     = array(
				'primary'    => array(
					'model'   => 'typesafe/jev-1.13',
					'answers' => array(
						'classification' => array(
							'type'          => 'choice',
							'choice'        => $decision,
							'confidence'    => 0.99,
							'probabilities' => (object) array(),
						),
						'basis'          => array(
							'type'          => 'choice',
							'choice'        => $basis,
							'confidence'    => 0.99,
							'probabilities' => (object) array(),
						),
					),
				),
				'escalation' => null,
			);
			return array(
				'response' => array( 'code' => 200 ),
				'body'     => wp_json_encode(
					array(
						'binding'  => $request['binding'],
						'decision' => $decision,
						'basis'    => $basis,
						'reason'   => 'unknown' === $decision ? 'insufficient_confidence' : 'classified',
						'model'    => 'typesafe/jev-1.13',
						'rubric'   => 'inquiry-mail-v1',
						'raw'      => $raw,
					)
				),
			);
		};
		add_filter( 'pre_http_request', $reply, 10, 3 );
		$this->later(
			static function () use ( $reply ): void {
				remove_filter( 'pre_http_request', $reply, 10 );
			}
		);
	}
	public function test_normal_source_creates_two_bound_full_messages_and_both_native_attempts_are_allowed(): void {
		$this->provider( 'normal' );
		$order = $this->submit();
		\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process( $order->get_id() );
		$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
		self::assertIsArray( $state );
		self::assertSame( 'normal', $state['status'] );
		self::assertCount( 2, $state['jobs'] );
		foreach ( $state['jobs']as$purpose => $entry ) {
			$job = ( new \Linker\Commerce\Mail\JobStore() )->load( $entry['id'] );
			self::assertNotNull( $job );
			self::assertTrue( \Linker\Commerce\Inquiry\Assessment\SendAuthorization::allows( $job['message'], $entry['id'] ) );
			if ( 'team' === $purpose ) {
				self::assertStringContainsString( 'full original content.', $job['message']->body );
			}do_action( \Linker\Commerce\Mail\Outbox::HOOK, $entry['id'] );
			self::assertNull( ( new \Linker\Commerce\Mail\JobStore() )->load( $entry['id'] ) );}
	}
	/** @testWith ["malicious"]
	 *           ["unknown"]
	 * @param string $decision Service result.
	 */
	public function test_non_normal_never_creates_content_mail_or_debits_receipts( string $decision ): void {
		$this->provider( $decision );
		$marker = self::newest_mail_job();
		$budget = get_option( OptionBudgetLedger::OPTION );
		$legacy = get_option( Throttle::OPTION );
		$order  = $this->submit();
		\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process( $order->get_id() );
		self::assertSame( array(), self::mail_jobs_after( $marker ) );
		self::assertSame( $budget, get_option( OptionBudgetLedger::OPTION ) );
		self::assertSame( $legacy, get_option( Throttle::OPTION ) );
		$order->read_meta_data( true );
		self::assertSame( 'assessment_pending', $order->get_meta( \Linker\Commerce\Inquiry\ReceiptLimit::SKIPPED_META ) );
		self::assertSame( 'Please quote a 10 kWh battery; full original content.', $order->get_customer_note() );
	}
 /** A changed source, purpose or queued body cannot borrow an old normal grant.
  * @testWith ["source"]
  *           ["purpose"]
  *           ["body"]
  *           ["security"]
  * @param string $change Mutation after real native classification.
  */
 public function test_native_retry_rejects_a_changed_source_or_message( string $change ): void {
  $this->provider('normal');$order=$this->submit();\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process($order->get_id());
  $state=\Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read($order->get_id());self::assertIsArray($state);$job=$state['jobs']['team']['id'];$stored=(new \Linker\Commerce\Mail\JobStore())->load($job);self::assertNotNull($stored);
  if('source'===$change){$order->set_customer_note('Changed after classification');$order->save();}else{$data=$stored['message']->to_array();if('body'===$change){$data['body'].=' Changed';}elseif('security'===$change){$data['origin']=array('kind'=>'security','producer'=>'password_reset');}else{$data['origin']['purpose']='receipt';}update_post_meta($job,'_linker_mail_message',wp_slash((string)wp_json_encode($data)));}
  $budget=get_option(OptionBudgetLedger::OPTION);$attempts=0;$watch=static function()use(&$attempts):void{++$attempts;};add_action('phpmailer_init',$watch,PHP_INT_MAX);
  try{do_action(\Linker\Commerce\Mail\Outbox::HOOK,$job);}finally{remove_action('phpmailer_init',$watch,PHP_INT_MAX);}
  self::assertSame(0,$attempts);self::assertSame($budget,get_option(OptionBudgetLedger::OPTION));self::assertNotNull((new \Linker\Commerce\Mail\JobStore())->load($job));
 }
 public function test_late_normal_response_is_unknown_and_never_consumes_receipt_or_mail_capacity():void {
  $this->provider('normal');$order=$this->submit();$data=Queue::data($order);$data['deadline']=microtime(true)+0.01;\Linker\Commerce\Inquiry\Assessment\StructuredMeta::update($order,Queue::META,$data);$order->save_meta_data();
  $slow=static function($pre,$args,$url){if(str_ends_with($url,'/inquiries/assess')){usleep(25000);}return $pre;};add_filter('pre_http_request',$slow,11,3);
  try{\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process($order->get_id());}finally{remove_filter('pre_http_request',$slow,11);}
  $state=\Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read($order->get_id());self::assertIsArray($state);self::assertSame('pending',$state['status']);self::assertSame('deadline',$state['verdict']['reason']);self::assertSame(array(),$state['jobs']);$order->read_meta_data(true);self::assertSame('assessment_pending',$order->get_meta(\Linker\Commerce\Inquiry\ReceiptLimit::SKIPPED_META));
 }
 public function test_old_held_job_and_native_record_are_not_rewritten_or_released():void {
  $order=wc_create_order();self::assertInstanceOf(WC_Order::class,$order);$order->update_meta_data(\Linker\Commerce\Mail\NotificationHold::META,array('reason'=>'historical_incident'));$order->save();
  $this->later(static function()use($order):void{delete_option(\Linker\Commerce\Inquiry\Assessment\AuthorizationStore::PREFIX.$order->get_id());$order->delete(true);});
  $message=new \Linker\Commerce\Mail\Message(array(self::TESTER),'Synthetic historical notice','Original held content',array(),array());$job=(new \Linker\Commerce\Mail\JobStore())->create($message,$order->get_id());update_post_meta($job,\Linker\Commerce\Mail\NotificationHold::META,array('reason'=>'historical_incident','order'=>$order->get_id()));
  $before=get_post_meta($job);$order_before=$order->get_meta_data();$budget=get_option(OptionBudgetLedger::OPTION);
  \Linker\Commerce\Inquiry\Assessment\SendAuthorization::process($order->get_id());do_action(\Linker\Commerce\Mail\Outbox::HOOK,$job);
  self::assertSame($before,get_post_meta($job));self::assertEquals($order_before,wc_get_order($order->get_id())->get_meta_data());self::assertSame($budget,get_option(OptionBudgetLedger::OPTION));
 }
 public function test_unknown_recovery_is_bounded_and_can_later_classify_without_resubmitting():void {
  $this->provider('unknown');$order=$this->submit();\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process($order->get_id());$state=\Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read($order->get_id());self::assertIsArray($state);self::assertSame(1,$state['attempts']);self::assertGreaterThan(time(),$state['next_at']);
  \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::edit($order->get_id(),static function(array &$state):void{$state['next_at']=time()-1;});$this->provider('normal');\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process($order->get_id());
  $state=\Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read($order->get_id());self::assertIsArray($state);self::assertSame(2,$state['attempts']);self::assertSame('normal',$state['status']);self::assertCount(2,$state['jobs']);
 }
 public function test_native_core_profile_notifications_keep_their_security_purpose():void {
  $customer=$this->customer();$count=0;$watch=static function()use(&$count):void{++$count;};add_action('phpmailer_init',$watch,PHP_INT_MAX);
  try{$updated=wp_update_user(array('ID'=>$customer->get_id(),'user_pass'=>wp_generate_password(24),'user_email'=>'changed-'.$customer->get_id().'@example.test'));self::assertSame($customer->get_id(),$updated);}finally{remove_action('phpmailer_init',$watch,PHP_INT_MAX);}
  self::assertSame(2,$count);
 }
 public function test_real_classifier_wire_goldens_have_the_same_permission_semantics():void {
  foreach(array('normal-primary','normal-escalated')as$name){$wire=json_decode((string)file_get_contents(dirname(__DIR__,2).'/fixtures/pre-send/'.$name.'.json'),true);self::assertIsArray($wire);self::assertSame('normal',\Linker\Commerce\Inquiry\Assessment\SendVerdict::validate($wire,$wire['binding'])['decision']);$wire['raw']['primary']['answers']['classification']['confidence']='0.99';self::assertSame('unknown',\Linker\Commerce\Inquiry\Assessment\SendVerdict::validate($wire,$wire['binding'])['decision']);}
 }

 /** @testWith ["normal"]
  *           ["malicious"]
  * @param string $decision Independent conversation classification.
  */
 public function test_conversation_content_is_persisted_pending_and_cannot_borrow_an_inquiry_permit( string $decision ):void {
  $this->provider($decision);$messages=array(array('role'=>'user','content'=>'Please quote a commercial battery.','products'=>array()));
  $id=wp_insert_post(array('post_type'=>'linker_conversation','post_status'=>'private','post_title'=>'Synthetic source'));self::assertIsInt($id);$this->later(static function()use($id):void{wp_delete_post($id,true);});
  $source=static fn($current,int $candidate,array $frozen):bool=>$candidate===$id&&$frozen===$messages;add_filter('linker_commerce_conversation_mail_source_current',$source,10,3);$this->later(static function()use($source):void{remove_filter('linker_commerce_conversation_mail_source_current',$source,10);});
  $marker=self::newest_mail_job();$budget=get_option(OptionBudgetLedger::OPTION);
  $answer=apply_filters(\Linker\Commerce\Genie\Module::SEND_FILTER,false,array('conversation_id'=>$id,'to'=>self::TESTER,'locale'=>'en','messages'=>$messages));self::assertSame(array('status'=>'pending'),$answer);self::assertSame($budget,get_option(OptionBudgetLedger::OPTION));
  $jobs=self::mail_jobs_after($marker);self::assertCount(1,$jobs);$job=$jobs[0];
  $this->later(static function()use($job):void{as_unschedule_all_actions(\Linker\Commerce\Inquiry\Assessment\ConversationAuthorization::PROCESS,array($job),\Linker\Commerce\Mail\Outbox::GROUP);delete_option(\Linker\Commerce\Inquiry\Assessment\AuthorizationStore::PREFIX.'conversation-'.$job);});
  (new \Linker\Commerce\Inquiry\Assessment\ConversationAuthorization())->process($job);
  $loaded=(new \Linker\Commerce\Mail\JobStore())->load($job);self::assertNotNull($loaded);
  self::assertSame('normal'===$decision,\Linker\Commerce\Inquiry\Assessment\ConversationAuthorization::allows($loaded['message'],$job));
  if('malicious'===$decision){self::assertFalse(apply_filters(\Linker\Commerce\Genie\Module::SEND_FILTER,false,array('conversation_id'=>$id,'to'=>self::TESTER,'locale'=>'en','messages'=>$messages)));self::assertSame($budget,get_option(OptionBudgetLedger::OPTION));}else{do_action(\Linker\Commerce\Mail\Outbox::HOOK,$job);self::assertNull((new \Linker\Commerce\Mail\JobStore())->load($job));self::assertTrue(apply_filters(\Linker\Commerce\Genie\Module::SEND_FILTER,false,array('conversation_id'=>$id,'to'=>self::TESTER,'locale'=>'en','messages'=>$messages)));}
 }
 public function test_handoff_does_not_commit_or_rollback_the_native_callers_transaction():void {
  $this->provider('normal');$order=$this->submit();global $wpdb;
  $wpdb->query('START TRANSACTION');$marker='pre_send_outer_'.wp_generate_uuid4();$wpdb->query($wpdb->prepare("INSERT INTO {$wpdb->options} (option_name,option_value,autoload) VALUES (%s,'owned','off')",$marker));
  try{\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process($order->get_id());$state=\Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read($order->get_id());self::assertIsArray($state);self::assertSame('pending',$state['status']);self::assertSame(0,$state['attempts']);$wpdb->query('ROLLBACK');self::assertNull($wpdb->get_var($wpdb->prepare("SELECT option_value FROM {$wpdb->options} WHERE option_name=%s",$marker)));}finally{$wpdb->query('ROLLBACK');}
 }

}
