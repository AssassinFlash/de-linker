<?php
/** Native submission-to-mail authorization boundary; no external delivery.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
namespace Linker\Commerce\Tests\Integration;

// phpcs:disable WordPress.PHP.DiscouragedPHPFunctions.runtime_configuration_putenv -- Only this native fixture process changes a named synthetic private mode, then restores it.
// phpcs:disable WordPress.DB.DirectDatabaseQuery -- Fault fixtures inspect their own native transaction and synthetic rows.
// phpcs:disable WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- Fixed native production hook constants under test.

use Linker\Commerce\Contact\Submission;
use Linker\Commerce\Inquiry\Sender;
use Linker\Commerce\Inquiry\Assessment\Queue;
use Linker\Commerce\Mail\OptionBudgetLedger;
use Linker\Commerce\Mail\Throttle;
use WC_Order;
/** Native authorization contract.
 *
 * @coversNothing
 */
final class PreSendAuthorizationTest extends IntegrationTestCase {
	/** Preserve native options and isolate the local provider configuration. */
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
	/** Persist one complete native synthetic inquiry. */
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
	/** Unavailable assessment preserves complete record without receipt team or budget. */
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
	/** Return typed local service evidence for the actual request binding.
	 *
	 * @param string $decision Synthetic classifier decision.
	 */
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
	/** Normal source creates two bound full messages and both native attempts are allowed. */
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
		\Linker\Commerce\Inquiry\Assessment\SendAuthorization::recover( $order->get_id() );
		$order->read_meta_data( true );
		self::assertSame( 'complete', $order->get_meta( Queue::PENDING ) );
	}
	/** Service result.
	 *
	 * @testWith ["malicious"]
	 * ["unknown"]
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
	 *
	 * @testWith ["source"]
	 * ["purpose"]
	 * ["body"]
	 * ["security"]
	 * @param string $change Mutation after real native classification.
	 */
	public function test_native_retry_rejects_a_changed_source_or_message( string $change ): void {
		$this->provider( 'normal' );
		$order = $this->submit();
		\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process( $order->get_id() );
		$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
		self::assertIsArray( $state );
		$job    = $state['jobs']['team']['id'];
		$stored = ( new \Linker\Commerce\Mail\JobStore() )->load( $job );
		self::assertNotNull( $stored );
		if ( 'source' === $change ) {
			$order->set_customer_note( 'Changed after classification' );
			$order->save();
		} else {
			$data = $stored['message']->to_array();
			if ( 'body' === $change ) {
				$data['body'] .= ' Changed';
			} elseif ( 'security' === $change ) {
				$data['origin'] = array(
					'kind'     => 'security',
					'producer' => 'password_reset',
				);
			} else {
				$data['origin']['purpose'] = 'receipt';
			}update_post_meta( $job, '_linker_mail_message', wp_slash( (string) wp_json_encode( $data ) ) );}
		$budget   = get_option( OptionBudgetLedger::OPTION );
		$attempts = 0;
		$watch    = static function () use ( &$attempts ): void {
			++$attempts;
		};
		add_action( 'phpmailer_init', $watch, PHP_INT_MAX );
		try {
			do_action( \Linker\Commerce\Mail\Outbox::HOOK, $job );
		} finally {
			remove_action( 'phpmailer_init', $watch, PHP_INT_MAX );}
		self::assertSame( 0, $attempts );
		self::assertSame( $budget, get_option( OptionBudgetLedger::OPTION ) );
		self::assertNotNull( ( new \Linker\Commerce\Mail\JobStore() )->load( $job ) );
	}
	/** Late normal response is unknown and never consumes receipt or mail capacity. */
	public function test_late_normal_response_is_unknown_and_never_consumes_receipt_or_mail_capacity(): void {
		$this->provider( 'normal' );
		$order = $this->submit();
		$slow  = static function ( $pre, $args, $url ) {
			if ( str_ends_with( $url, '/inquiries/assess' ) ) {
				usleep( Queue::WAIT_SECONDS * 1000000 + 25000 );
			}return $pre;
		};
		add_filter( 'pre_http_request', $slow, 11, 3 );
		try {
			\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process( $order->get_id() );
		} finally {
			remove_filter( 'pre_http_request', $slow, 11 );}
		$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
		self::assertIsArray( $state );
		self::assertSame( 'pending', $state['status'] );
		self::assertSame( 'deadline', $state['verdict']['reason'] );
		self::assertSame( array(), $state['jobs'] );
		$order->read_meta_data( true );
		self::assertSame( 'assessment_pending', $order->get_meta( \Linker\Commerce\Inquiry\ReceiptLimit::SKIPPED_META ) );
	}
	/** Old held job and native record are not rewritten or released. */
	public function test_old_held_job_and_native_record_are_not_rewritten_or_released(): void {
		$order = wc_create_order();
		self::assertInstanceOf( WC_Order::class, $order );
		$order->update_meta_data( \Linker\Commerce\Mail\NotificationHold::META, array( 'reason' => 'historical_incident' ) );
		$order->save();
		$this->later(
			static function () use ( $order ): void {
				delete_option( \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::PREFIX . $order->get_id() );
				$order->delete( true );
			}
		);
		$message = new \Linker\Commerce\Mail\Message( array( self::TESTER ), 'Synthetic historical notice', 'Original held content', array(), array() );
		$job     = ( new \Linker\Commerce\Mail\JobStore() )->create( $message, $order->get_id() );
		update_post_meta(
			$job,
			\Linker\Commerce\Mail\NotificationHold::META,
			array(
				'reason' => 'historical_incident',
				'order'  => $order->get_id(),
			)
		);
		$before       = get_post_meta( $job );
		$order_before = $order->get_meta_data();
		$budget       = get_option( OptionBudgetLedger::OPTION );
		\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process( $order->get_id() );
		do_action( \Linker\Commerce\Mail\Outbox::HOOK, $job );
		self::assertSame( $before, get_post_meta( $job ) );
		$fresh = wc_get_order( $order->get_id() );
		self::assertInstanceOf( WC_Order::class, $fresh );
		self::assertEquals( $order_before, $fresh->get_meta_data() );
		self::assertSame( $budget, get_option( OptionBudgetLedger::OPTION ) );
	}
	/** Unknown recovery is bounded and can later classify without resubmitting. */
	public function test_unknown_recovery_is_bounded_and_can_later_classify_without_resubmitting(): void {
		$this->provider( 'unknown' );
		$order = $this->submit();
		\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process( $order->get_id() );
		$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
		self::assertIsArray( $state );
		self::assertSame( 1, $state['attempts'] );
		self::assertGreaterThan( time(), $state['next_at'] );
		\Linker\Commerce\Inquiry\Assessment\AuthorizationStore::edit(
			$order->get_id(),
			static function ( array &$state ): void {
				$state['next_at'] = time() - 1;
			}
		);
		$this->provider( 'normal' );
		\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process( $order->get_id() );
		$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
		self::assertIsArray( $state );
		self::assertSame( 2, $state['attempts'] );
		self::assertSame( 'normal', $state['status'] );
		self::assertCount( 2, $state['jobs'] );
	}
	/** Native core profile notifications keep their security purpose. */
	public function test_native_core_profile_notifications_keep_their_security_purpose(): void {
		$customer = $this->customer();
		$count    = 0;
		$watch    = static function () use ( &$count ): void {
			++$count;
		};
		add_action( 'phpmailer_init', $watch, PHP_INT_MAX );
		try {
			$updated = wp_update_user(
				array(
					'ID'         => $customer->get_id(),
					'user_pass'  => wp_generate_password( 24 ),
					'user_email' => 'changed-' . $customer->get_id() . '@example.test',
				)
			);
			self::assertSame( $customer->get_id(), $updated );
		} finally {
			remove_action( 'phpmailer_init', $watch, PHP_INT_MAX );}
		self::assertSame( 2, $count );
	}
	/** Real classifier wire goldens have the same permission semantics. */
	public function test_real_classifier_wire_goldens_have_the_same_permission_semantics(): void {
		foreach ( array( 'normal-primary', 'normal-escalated' )as$name ) {
			$wire = json_decode( (string) file_get_contents( dirname( __DIR__, 2 ) . '/fixtures/pre-send/' . $name . '.json' ), true );
			self::assertIsArray( $wire );
			self::assertSame( 'normal', \Linker\Commerce\Inquiry\Assessment\SendVerdict::validate( $wire, $wire['binding'] )['decision'] );
			$wire['raw']['primary']['answers']['classification']['confidence'] = '0.99';
			self::assertSame( 'unknown', \Linker\Commerce\Inquiry\Assessment\SendVerdict::validate( $wire, $wire['binding'] )['decision'] );}
	}

	/** Independent conversation classification.
	 *
	 * @testWith ["normal"]
	 * ["malicious"]
	 * ["erase"]
	 * @param string $decision Independent conversation classification.
	 */
	public function test_conversation_content_is_persisted_pending_and_cannot_borrow_an_inquiry_permit( string $decision ): void {
		$this->provider( 'erase' === $decision ? 'normal' : $decision );
		$messages = array(
			array(
				'role'     => 'user',
				'content'  => 'Please quote a commercial battery.',
				'products' => array(),
			),
		);
		$id       = wp_insert_post(
			array(
				'post_type'   => 'linker_conversation',
				'post_status' => 'private',
				'post_title'  => 'Synthetic source',
			)
		);
		self::assertGreaterThan( 0, $id );
		$this->later(
			static function () use ( $id ): void {
				wp_delete_post( $id, true );
			}
		);
		$source = static fn( $current, int $candidate, array $frozen ): bool=>$candidate === $id && $frozen === $messages;
		add_filter( 'linker_commerce_conversation_mail_source_current', $source, 10, 3 );
		$this->later(
			static function () use ( $source ): void {
				remove_filter( 'linker_commerce_conversation_mail_source_current', $source, 10 );
			}
		);
		$marker = self::newest_mail_job();
		$budget = get_option( OptionBudgetLedger::OPTION );
		$answer = apply_filters(
			\Linker\Commerce\Genie\Module::SEND_FILTER,
			false,
			array(
				'conversation_id' => $id,
				'to'              => self::TESTER,
				'locale'          => 'en',
				'messages'        => $messages,
			)
		);
		self::assertSame( array( 'status' => 'pending' ), $answer );
		self::assertSame( $budget, get_option( OptionBudgetLedger::OPTION ) );
		$jobs = self::mail_jobs_after( $marker );
		self::assertCount( 1, $jobs );
		$job = $jobs[0];
		$this->later(
			static function () use ( $job ): void {
				as_unschedule_all_actions( \Linker\Commerce\Inquiry\Assessment\ConversationAuthorization::PROCESS, array( $job ), \Linker\Commerce\Mail\Outbox::GROUP );
				delete_option( \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::PREFIX . 'conversation-' . $job );
			}
		);
		( new \Linker\Commerce\Inquiry\Assessment\ConversationAuthorization() )->process( $job );
		$loaded = ( new \Linker\Commerce\Mail\JobStore() )->load( $job );
		self::assertNotNull( $loaded );
		if ( 'erase' === $decision ) {
			wp_delete_post( $id, true );
			\Linker\Commerce\Inquiry\Assessment\ConversationAuthorization::recover_job( $job );
			$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( 'conversation-' . $job );
			self::assertIsArray( $state );
			self::assertSame( 'erased', $state['status'] );
			self::assertFalse( \Linker\Commerce\Inquiry\Assessment\ConversationAuthorization::allows( $loaded['message'], $job ) );
			self::assertSame( '', get_post_meta( $job, \Linker\Commerce\Inquiry\Assessment\ConversationAuthorization::SOURCE, true ) );
			self::assertNull( ( new \Linker\Commerce\Mail\JobStore() )->load( $job ) );
			self::assertSame( $budget, get_option( OptionBudgetLedger::OPTION ) );
			return;
		}
		self::assertSame( 'normal' === $decision, \Linker\Commerce\Inquiry\Assessment\ConversationAuthorization::allows( $loaded['message'], $job ) );
		if ( 'malicious' === $decision ) {
			self::assertFalse(
				apply_filters(
					\Linker\Commerce\Genie\Module::SEND_FILTER,
					false,
					array(
						'conversation_id' => $id,
						'to'              => self::TESTER,
						'locale'          => 'en',
						'messages'        => $messages,
					)
				)
			);
			self::assertSame( $budget, get_option( OptionBudgetLedger::OPTION ) );
		} else {
			do_action( \Linker\Commerce\Mail\Outbox::HOOK, $job );
			self::assertNull( ( new \Linker\Commerce\Mail\JobStore() )->load( $job ) );
			self::assertTrue(
				apply_filters(
					\Linker\Commerce\Genie\Module::SEND_FILTER,
					false,
					array(
						'conversation_id' => $id,
						'to'              => self::TESTER,
						'locale'          => 'en',
						'messages'        => $messages,
					)
				)
			);}
	}
	/** Handoff does not commit or rollback the native callers transaction. */
	public function test_handoff_does_not_commit_or_rollback_the_native_callers_transaction(): void {
		$this->provider( 'normal' );
		$order = $this->submit();
		global $wpdb;
		$wpdb->query( 'START TRANSACTION' );
		$marker = 'pre_send_outer_' . wp_generate_uuid4();
		$wpdb->query( $wpdb->prepare( "INSERT INTO {$wpdb->options} (option_name,option_value,autoload) VALUES (%s,'owned','off')", $marker ) );
		try {
			\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process( $order->get_id() );
			$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
			self::assertIsArray( $state );
			self::assertSame( 'pending', $state['status'] );
			self::assertSame( 0, $state['attempts'] );
			$wpdb->query( 'ROLLBACK' );
			self::assertNull( $wpdb->get_var( $wpdb->prepare( "SELECT option_value FROM {$wpdb->options} WHERE option_name=%s", $marker ) ) );
		} finally {
			$wpdb->query( 'ROLLBACK' );}
	}

	/** Erasure revokes pending and normal copies before late work. */
	public function test_erasure_revokes_pending_and_normal_copies_before_late_work(): void {
		$this->provider( 'normal' );
		$order = $this->submit();
		\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process( $order->get_id() );
		$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
		self::assertIsArray( $state );
		$job = $state['jobs']['team']['id'];
		\WC_Privacy_Erasers::remove_order_personal_data( $order );
		$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
		self::assertIsArray( $state );
		self::assertSame( 'erased', $state['status'] );
		self::assertNull( ( new \Linker\Commerce\Mail\JobStore() )->load( $job ) );
		$order->read_meta_data( true );
		self::assertArrayNotHasKey( 'snapshot', Queue::data( $order ) );
		$budget = get_option( OptionBudgetLedger::OPTION );
		do_action( \Linker\Commerce\Mail\Outbox::HOOK, $job );
		\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process( $order->get_id() );
		self::assertSame( $budget, get_option( OptionBudgetLedger::OPTION ) );
		$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
		self::assertIsArray( $state );
		self::assertSame( 'erased', $state['status'] );
	}
	/** Staff correction alone does not send but explicit bound release is team only.
	 *
	 * @testWith ["malicious"]
	 *           ["unknown"]
	 * @param string $decision Original non-normal classifier evidence.
	 */
	public function test_staff_correction_alone_does_not_send_but_explicit_bound_release_is_team_only( string $decision ): void {
		$this->provider( $decision );
		$order = $this->submit();
		\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process( $order->get_id() );
		$order->read_meta_data( true );
		self::assertSame( 'malicious' === $decision, \Linker\Commerce\Mail\NotificationHold::held( $order ) );
		wp_set_current_user( 1 );
		self::assertInstanceOf( \WP_Error::class, \Linker\Commerce\Mail\NotificationHold::release( $order->get_id(), \Linker\Commerce\Mail\NotificationHold::reference( $order ) ) );
		$result = \Linker\Commerce\Inquiry\Assessment\Reviews::save(
			$order->get_id(),
			0,
			'correct',
			array(
				'label' => 'normal',
				'note'  => 'Native fixture checked complete source.',
				'basis' => \Linker\Commerce\Inquiry\Assessment\Reviews::reference( $order ),
			)
		);
		self::assertIsArray( $result );
		$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
		self::assertIsArray( $state );
		self::assertSame( 'manual', $state['status'] );
		self::assertSame( array(), $state['jobs'] );
		$order->read_meta_data( true );
		$release = \Linker\Commerce\Mail\NotificationHold::release( $order->get_id(), \Linker\Commerce\Mail\NotificationHold::reference( $order ) );
		self::assertIsArray( $release );
		$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
		self::assertIsArray( $state );
		self::assertSame( 'normal', $state['status'] );
		self::assertSame( array( 'team' ), array_keys( $state['jobs'] ) );
		self::assertNotEmpty( $state['staff_release'] );
		self::assertSame( 'human_override', $state['producer'] );
		self::assertSame( $decision, $state['verdict']['decision'] );
	}
	/** Job handoff storage fault rolls back jobs and receipt allowance. */
	public function test_job_handoff_storage_fault_rolls_back_jobs_and_receipt_allowance(): void {
		$this->provider( 'normal' );
		$order   = $this->submit();
		$marker  = self::newest_mail_job();
		$created = false;
		$hits    = 0;
		$observe = static function ( int $id, $post ) use ( &$created ): void {
			if ( \Linker\Commerce\Mail\JobStore::POST_TYPE === $post->post_type ) {
				$created = true;
			}};
		$fault   = static function ( string $sql ) use ( &$created, &$hits, $order ): string {
			if ( $created && 0 === $hits && str_starts_with( ltrim( $sql ), 'UPDATE' ) && str_contains( $sql, \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::PREFIX . $order->get_id() ) ) {
				++$hits;
					return 'SELECT 0';
			}return $sql;
		};
		add_action( 'wp_insert_post', $observe, 10, 2 );
		add_filter( 'query', $fault, 998 );
		try {
			\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process( $order->get_id() );
		} finally {
			remove_action( 'wp_insert_post', $observe, 10 );
			remove_filter( 'query', $fault, 998 );}
		self::assertSame( 1, $hits );
		self::assertSame( array(), self::mail_jobs_after( $marker ) );
		$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
		self::assertIsArray( $state );
		self::assertSame( 'approved', $state['status'] );
		self::assertSame( 1, $state['handoff_attempts'] );
		$order->read_meta_data( true );
		self::assertSame( 'assessment_pending', $order->get_meta( \Linker\Commerce\Inquiry\ReceiptLimit::SKIPPED_META ) );
	}
	/** Core admin password notice is a distinct native security producer. */
	public function test_core_admin_password_notice_is_a_distinct_native_security_producer(): void {
		$customer = $this->customer();
		$count    = 0;
		$watch    = static function () use ( &$count ): void {
			++$count;
		};
		add_action( 'phpmailer_init', $watch, PHP_INT_MAX );
		try {
			$user = get_userdata( $customer->get_id() );
			self::assertInstanceOf( \WP_User::class, $user );
			wp_password_change_notification( $user );
		} finally {
			remove_action( 'phpmailer_init', $watch, PHP_INT_MAX );
		}self::assertSame( 1, $count );
	}
	/** A staff release of an already queued source cannot re-enable its customer receipt. */
	public function test_existing_receipt_stays_blocked_after_explicit_team_only_release(): void {
		$this->provider( 'normal' );
		$order = $this->submit();
		\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process( $order->get_id() );
		$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
		self::assertIsArray( $state );
		$receipt = $state['jobs']['receipt']['id'];
		wp_set_current_user( 1 );
		$order->read_meta_data( true );
		self::assertIsArray(
			\Linker\Commerce\Inquiry\Assessment\Reviews::save(
				$order->get_id(),
				0,
				'correct',
				array(
					'label' => 'normal',
					'note'  => 'Native source reviewed.',
					'basis' => \Linker\Commerce\Inquiry\Assessment\Reviews::reference( $order ),
				)
			)
		);
		$order->read_meta_data( true );
		self::assertIsArray( \Linker\Commerce\Mail\NotificationHold::release( $order->get_id(), \Linker\Commerce\Mail\NotificationHold::reference( $order ) ) );
		$loaded = ( new \Linker\Commerce\Mail\JobStore() )->load( $receipt );
		self::assertNotNull( $loaded );
		self::assertFalse( \Linker\Commerce\Inquiry\Assessment\SendAuthorization::allows( $loaded['message'], $receipt ) );
		$order->read_meta_data( true );
		self::assertSame( 'staff_release_team_only', $order->get_meta( \Linker\Commerce\Inquiry\ReceiptLimit::SKIPPED_META ) );
	}
	/** A deleted job is not evidence of delivery; only an actual receipt ACK preserves its sent state.
	 *
	 * @testWith [false]
	 *           [true]
	 * @param bool $receipt_sent Whether the actual receipt transport already completed.
	 */
	public function test_missing_job_is_manual_and_completed_jobs_stop_the_native_heartbeat( bool $receipt_sent ): void {
		$this->provider( 'normal' );
		$order = $this->submit();
		\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process( $order->get_id() );
		$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
		self::assertIsArray( $state );
		if ( $receipt_sent ) {
			do_action( \Linker\Commerce\Mail\Outbox::HOOK, $state['jobs']['receipt']['id'] ); }
		( new \Linker\Commerce\Mail\JobStore() )->delete( $state['jobs']['team']['id'] );
		\Linker\Commerce\Inquiry\Assessment\SendAuthorization::recover( $order->get_id() );
		$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
		self::assertIsArray( $state );
		self::assertSame( 'manual', $state['status'] );
		$order->read_meta_data( true );
		self::assertSame( $receipt_sent ? '' : 'delivery_unconfirmed', $order->get_meta( \Linker\Commerce\Inquiry\ReceiptLimit::SKIPPED_META ) );
	}
	/** Probability mass never increases the selected confidence. */
	/** A late classifier cannot restore erased native content or permission. */
	public function test_erasure_during_provider_io_invalidates_the_claimed_operation(): void {
		$this->provider( 'normal' );
		$order = $this->submit();
		$erase = static function ( $pre, $args, $url ) use ( $order ) {
			if ( str_ends_with( $url, '/inquiries/assess' ) ) {
				\WC_Privacy_Erasers::remove_order_personal_data( $order );
			}
			return $pre;
		};
		add_filter( 'pre_http_request', $erase, 20, 3 );
		$marker = self::newest_mail_job();
		try {
			\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process( $order->get_id() );
		} finally {
			remove_filter( 'pre_http_request', $erase, 20 );
		}
		self::assertSame( array(), self::mail_jobs_after( $marker ) );
		$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
		self::assertIsArray( $state );
		self::assertSame( 'erased', $state['status'] );
	}
	/** The original bounded delays end in retained staff work, never a default send. */
	public function test_exhausted_unknown_stays_held_with_complete_content_and_no_mail_allowance(): void {
		$this->provider( 'unknown' );
		$order = $this->submit();
		\Linker\Commerce\Inquiry\Assessment\AuthorizationStore::edit(
			$order->get_id(),
			static function ( array &$state ): void {
				$state['attempts'] = count( \Linker\Commerce\Mail\Outbox::RETRY_DELAYS );
				$state['next_at']  = time();
			}
		);
		$budget = get_option( OptionBudgetLedger::OPTION );
		\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process( $order->get_id() );
		$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
		self::assertIsArray( $state );
		self::assertSame( 'manual', $state['status'] );
		$order->read_meta_data( true );
		self::assertTrue( \Linker\Commerce\Mail\NotificationHold::held( $order ) );
		self::assertStringContainsString( 'full original content.', $order->get_customer_note() );
		self::assertSame( $budget, get_option( OptionBudgetLedger::OPTION ) );
	}
	/** A second real native connection wins after the original connection loses its named lock. */
	public function test_reconnected_writer_cannot_overwrite_a_peer_authorization(): void {
		global $wpdb;
		$key = 'fixture-' . wp_generate_uuid4();
		$this->later(
			static function () use ( $key ): void {
				delete_option( \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::PREFIX . $key );
			}
		);
		self::assertTrue(
			\Linker\Commerce\Inquiry\Assessment\AuthorizationStore::edit(
				$key,
				static function ( array &$state ): void {
					$state = array( 'status' => 'pending' );
				}
			)
		);
		$peer = new \wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
		$peer->set_prefix( $wpdb->prefix );
		$connection = (int) $wpdb->get_var( 'SELECT CONNECTION_ID()' );
		$peer_hits  = 0;
		$written    = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::edit(
			$key,
			static function ( array &$state ) use ( $peer, $connection, $key, &$peer_hits ): void {
				global $wpdb;
				self::assertNotFalse( $peer->query( 'KILL CONNECTION ' . $connection ) );
				$sql = $wpdb->prepare( "UPDATE {$wpdb->options} SET option_value=%s WHERE option_name=%s", '{"status":"erased"}', \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::PREFIX . $key );
				self::assertIsString( $sql );
				$peer_hits       = (int) $peer->query( $sql );
				$state['status'] = 'normal';
			}
		);
		self::assertFalse( $written );
		self::assertSame( 1, $peer_hits );
		self::assertSame( '{"status":"erased"}', $peer->get_var( $wpdb->prepare( "SELECT option_value FROM {$wpdb->options} WHERE option_name=%s", \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::PREFIX . $key ) ) );
		self::assertNotSame( $connection, (int) $wpdb->get_var( 'SELECT CONNECTION_ID()' ) );
		$peer->close();
	}
	/** Source changes during a failed SMTP attempt revoke the separately budgeted PHP fallback. */
	public function test_smtp_failure_rechecks_current_source_before_any_php_fallback_allowance(): void {
		$this->provider( 'normal' );
		$order = $this->submit();
		\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process( $order->get_id() );
		$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
		self::assertIsArray( $state );
		$job   = $state['jobs']['team']['id'];
		$hooks = array();
		foreach ( array( 'pre_wp_mail', 'wp_mail_failed', 'phpmailer_init' ) as $name ) {
			$hooks[ $name ] = isset( $GLOBALS['wp_filter'][ $name ] ) ? clone $GLOBALS['wp_filter'][ $name ] : null;
			remove_all_filters( $name );
		}
		require_once ABSPATH . (string) constant( 'WPINC' ) . '/PHPMailer/PHPMailer.php';
		require_once ABSPATH . (string) constant( 'WPINC' ) . '/PHPMailer/SMTP.php';
		require_once ABSPATH . (string) constant( 'WPINC' ) . '/PHPMailer/Exception.php';
		require_once ABSPATH . (string) constant( 'WPINC' ) . '/class-wp-phpmailer.php';
		$previous             = $GLOBALS['phpmailer'] ?? null;
		$mailer               = new class( $order ) extends \WP_PHPMailer {
				/** Native SMTP attempts observed without network I/O.
				 *
				 * @var int
				 */
			public int $smtp_attempts = 0;
				/** Native PHP attempts observed without actual mail.
				 *
				 * @var int
				 */
			public int $php_attempts = 0;
			/** Native source changed at the first transport failure.
			 *
			 * @param WC_Order $source Native source changed at the first transport failure.
			 */
			public function __construct( private readonly WC_Order $source ) {
				parent::__construct( true ); }
			/** No actual network or PHP mail is permitted by this failure fixture.
			 *
			 * @throws \PHPMailer\PHPMailer\Exception Synthetic SMTP failure.
			 */
			public function postSend(): bool {
				if ( 'smtp' === $this->Mailer ) { // phpcs:ignore WordPress.NamingConventions.ValidVariableName.UsedPropertyNotSnakeCase -- PHPMailer owns this property.
					++$this->smtp_attempts;
					$this->source->set_customer_note( 'Changed source while the first SMTP attempt was in flight.' );
					$this->source->save();
					throw new \PHPMailer\PHPMailer\Exception( 'Synthetic local SMTP failure.' );
				}
				++$this->php_attempts;
				return true;
			}
		};
		$GLOBALS['phpmailer'] = $mailer;
		$file                 = tempnam( sys_get_temp_dir(), 'pre-send-fake-smtp-' );
		self::assertIsString( $file );
		file_put_contents( $file, "LINKER_SMTP_HOST=127.0.0.1\nLINKER_SMTP_PORT=9\nLINKER_SMTP_USER=sales@sunriverinverter.com\nLINKER_SMTP_PASS=fake-fixture-only\nLINKER_SMTP_SECURE=\n" );
		$smtp   = new \Linker\Commerce\Mail\InternalSmtp( $file );
		$outbox = new \Linker\Commerce\Mail\Outbox( new \Linker\Commerce\Mail\JobStore(), new Throttle( new OptionBudgetLedger(), $smtp ), new \Linker\Commerce\Mail\TestMode(), $smtp );
		add_filter( 'pre_wp_mail', array( $outbox, 'intercept' ), 10, 2 );
		add_action( 'phpmailer_init', array( $outbox, 'configure_mailer' ) );
		add_action( 'wp_mail_failed', array( $outbox, 'remember_error' ) );
		$php = get_option( Throttle::OPTION );
		try {
			$outbox->retry( $job );
		} finally {
			foreach ( $hooks as $name => $hook ) {
				if ( null === $hook ) {
					unset( $GLOBALS['wp_filter'][ $name ] );
				} else {
					$GLOBALS['wp_filter'][ $name ] = $hook; }
			}
			$GLOBALS['phpmailer'] = $previous;
			unlink( $file );
		}
		self::assertSame( 1, $mailer->smtp_attempts );
		self::assertSame( 0, $mailer->php_attempts );
		self::assertSame( $php, get_option( Throttle::OPTION ) );
		self::assertNotNull( ( new \Linker\Commerce\Mail\JobStore() )->load( $job ) );
	}
	/** Losing a transaction cannot replay the remaining native job writes in autocommit. */
	public function test_connection_loss_during_job_handoff_leaves_no_orphan_message_or_receipt_debit(): void {
		$this->provider( 'normal' );
		$order = $this->submit();
		global $wpdb;
		$peer       = new \wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
		$connection = (int) $wpdb->get_var( 'SELECT CONNECTION_ID()' );
		$hits       = 0;
		$created    = 0;
		$cut        = static function ( int $id, $post ) use ( $peer, $connection, &$hits, &$created ): void {
			if ( 0 === $hits && \Linker\Commerce\Mail\JobStore::POST_TYPE === $post->post_type ) {
				++$hits;
				$created = $id;
				$peer->query( 'KILL CONNECTION ' . $connection );
			}
		};
		$this->later(
			static function () use ( &$created ): void {
				if ( $created > 0 && false === get_post_status( $created ) ) {
					global $wpdb;
					$wpdb->delete( $wpdb->postmeta, array( 'post_id' => $created ), array( '%d' ) );
				}
			}
		);
		$marker  = self::newest_mail_job();
		$receipt = ( new \Linker\Commerce\Inquiry\RateLimit( 'public_receipts', \Linker\Commerce\Inquiry\ReceiptLimit::DAILY_CAP, DAY_IN_SECONDS ) )->spent( '' );
		add_action( 'wp_insert_post', $cut, 10, 2 );
		try {
			\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process( $order->get_id() );
		} finally {
			remove_action( 'wp_insert_post', $cut, 10 );
			$peer->close();
		}
		self::assertSame( 1, $hits );
		self::assertSame( array(), self::mail_jobs_after( $marker ) );
		self::assertSame( '0', $wpdb->get_var( $wpdb->prepare( "SELECT COUNT(*) FROM {$wpdb->postmeta} WHERE meta_key='_linker_mail_message' AND post_id=%d", $created ) ), 'No replayed orphan Message meta survives a lost transaction.' );
		self::assertSame( $receipt, ( new \Linker\Commerce\Inquiry\RateLimit( 'public_receipts', \Linker\Commerce\Inquiry\ReceiptLimit::DAILY_CAP, DAY_IN_SECONDS ) )->spent( '' ) );
		$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
		self::assertIsArray( $state );
		self::assertSame( 'approved', $state['status'] );
		self::assertSame( array(), $state['jobs'] );
	}
	/** Real service wire goldens preserve the conservative confidence computation. */
	/** A delayed native queue starts a complete model window without resubmission. */
	public function test_queue_delay_does_not_consume_the_first_model_attempt_window(): void {
		$this->provider( 'normal' );
		$order               = $this->submit();
		$data                = Queue::data( $order );
		$data['accepted_at'] = microtime( true ) - 2 * Queue::WAIT_SECONDS;
		$data['deadline']    = $data['accepted_at'] + Queue::WAIT_SECONDS;
		\Linker\Commerce\Inquiry\Assessment\StructuredMeta::update( $order, Queue::META, $data );
		$order->save_meta_data();
		$remaining = null;
		$observe   = static function ( $pre, $args, $url ) use ( &$remaining ) {
			if ( str_ends_with( $url, '/inquiries/assess' ) ) {
				$request   = json_decode( $args['body'], true );
				$remaining = $request['remaining_seconds'];
			}
			return $pre;
		};
		add_filter( 'pre_http_request', $observe, 20, 3 );
		try {
			\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process( $order->get_id() );
		} finally {
			remove_filter( 'pre_http_request', $observe, 20 );
		}
		self::assertIsFloat( $remaining );
		self::assertGreaterThan( Queue::WAIT_SECONDS - 1, $remaining );
		self::assertLessThanOrEqual( Queue::WAIT_SECONDS, $remaining );
		$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
		self::assertIsArray( $state );
		self::assertSame( 1, $state['attempts'] );
		self::assertSame( 'normal', $state['status'] );
		self::assertCount( 2, $state['jobs'] );
	}
	/** The real enforce receipt pool and full native template are used only after normal.
	 *
	 * @testWith ["normal"]
	 *           ["malicious"]
	 *           ["unknown"]
	 * @param string $decision Typed native classifier result.
	 */
	public function test_enforce_receipt_pool_waits_for_normal_and_restores_the_full_native_template( string $decision ): void {
		$mode = getenv( 'LINKER_PUBLIC_PROTECTION_MODE' );
		putenv( 'LINKER_PUBLIC_PROTECTION_MODE=enforce' );
		$this->later(
			static function () use ( $mode ): void {
				false === $mode ? putenv( 'LINKER_PUBLIC_PROTECTION_MODE' ) : putenv( 'LINKER_PUBLIC_PROTECTION_MODE=' . $mode );
			}
		);
		self::assertSame( 'enforce', \Linker\Commerce\Protection\Configuration::active_mode() );
		$this->provider( $decision );
		global $wpdb;
		$old = $wpdb->get_var( $wpdb->prepare( "SELECT option_value FROM {$wpdb->options} WHERE option_name=%s", \Linker\Commerce\Protection\Ledger::OPTION ) );
		$this->later(
			static function () use ( $old ): void {
				null === $old ? delete_option( \Linker\Commerce\Protection\Ledger::OPTION ) : update_option( \Linker\Commerce\Protection\Ledger::OPTION, $old, false );
			}
		);
		$legacy = ( new \Linker\Commerce\Inquiry\RateLimit( 'public_receipts', \Linker\Commerce\Inquiry\ReceiptLimit::DAILY_CAP, DAY_IN_SECONDS ) )->spent( '' );
		$order  = $this->submit();
		self::assertSame( 'yes', $order->get_meta( '_linker_fixed_receipt' ) );
		\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process( $order->get_id() );
		$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
		self::assertIsArray( $state );
		$order->read_meta_data( true );
		self::assertSame( $legacy, ( new \Linker\Commerce\Inquiry\RateLimit( 'public_receipts', \Linker\Commerce\Inquiry\ReceiptLimit::DAILY_CAP, DAY_IN_SECONDS ) )->spent( '' ) );
		if ( 'normal' === $decision ) {
			self::assertSame( '', $order->get_meta( '_linker_fixed_receipt' ) );
			$receipt = ( new \Linker\Commerce\Mail\JobStore() )->load( $state['jobs']['receipt']['id'] );
			self::assertNotNull( $receipt );
			self::assertStringContainsString( 'Thank you for your inquiry', $receipt['message']->body );
			self::assertStringContainsString( 'Synthetic installer', $receipt['message']->body );
		} else {
			self::assertSame( array(), $state['jobs'] );
			self::assertSame( $old, $wpdb->get_var( $wpdb->prepare( "SELECT option_value FROM {$wpdb->options} WHERE option_name=%s", \Linker\Commerce\Protection\Ledger::OPTION ) ) );
			self::assertSame( 'yes', $order->get_meta( '_linker_fixed_receipt' ) );
		}
	}
	/** Service-wire confidence and escalation eligibility remain conservative. */
	public function test_probability_mass_never_increases_the_selected_confidence(): void {
		foreach ( array( 'normal-under-mass', 'normal-excess-mass-escalated' )as$name ) {
			$wire = json_decode( (string) file_get_contents( dirname( __DIR__, 2 ) . '/fixtures/pre-send/' . $name . '.json' ), true );
			self::assertIsArray( $wire );
			self::assertSame( 'normal', \Linker\Commerce\Inquiry\Assessment\SendVerdict::validate( $wire, $wire['binding'] )['decision'] );}
		$wire = json_decode( (string) file_get_contents( dirname( __DIR__, 2 ) . '/fixtures/pre-send/normal-under-mass.json' ), true );
		$wire['raw']['primary']['answers']['classification']['probabilities'] = array(
			'normal'    => 0.89,
			'malicious' => 0.05,
			'unknown'   => 0.05,
		);
		self::assertSame( 'unknown', \Linker\Commerce\Inquiry\Assessment\SendVerdict::validate( $wire, $wire['binding'] )['decision'] );
		$escalated = json_decode( (string) file_get_contents( dirname( __DIR__, 2 ) . '/fixtures/pre-send/normal-escalated.json' ), true );
		$primary   = json_decode( (string) file_get_contents( dirname( __DIR__, 2 ) . '/fixtures/pre-send/normal-primary.json' ), true );
		self::assertIsArray( $escalated );
		self::assertIsArray( $primary );
		$escalated['raw']['primary'] = $primary['raw']['primary'];
		// A coherent high-confidence primary must never go through escalation, even when both say normal.
		self::assertSame( 'unknown', \Linker\Commerce\Inquiry\Assessment\SendVerdict::validate( $escalated, $escalated['binding'] )['decision'] );
		$a                                    = &$escalated['raw']['primary']['answers'];
		$a['classification']['choice']        = 'malicious';
		$a['classification']['probabilities'] = array(
			'normal'    => 0.02,
			'malicious' => 0.96,
			'unknown'   => 0.02,
		);
		$a['basis']['choice']                 = 'fraud_or_phishing';
		foreach ( $a['basis']['probabilities'] as $key => $number ) {
			$a['basis']['probabilities'][ $key ] = 'fraud_or_phishing' === $key ? 0.96 : 0.0; }
		self::assertSame( 'unknown', \Linker\Commerce\Inquiry\Assessment\SendVerdict::validate( $escalated, $escalated['binding'] )['decision'] );
	}
}
