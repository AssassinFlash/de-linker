<?php
/**
 * Native bounded contact/inquiry reception and recovery.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

// phpcs:disable WordPress.PHP.DiscouragedPHPFunctions.runtime_configuration_putenv -- Per-test private mode restored on teardown.
// phpcs:disable WordPress.Security.NonceVerification -- Synthetic native requests exercise the real nonce/proof validators.

use Linker\Commerce\Contact\Form as ContactForm;
use Linker\Commerce\Contact\Handler as ContactHandler;
use Linker\Commerce\Inquiry\Handler;
use Linker\Commerce\Inquiry\Assessment\Queue;
use Linker\Commerce\Inquiry\Assessment\Result;
use Linker\Commerce\Mail\NotificationHold;
use Linker\Commerce\Mail\Throttle;
use Linker\Commerce\Mail\Outbox;
use Linker\Commerce\Protection\Allowance;
use Linker\Commerce\Protection\BusinessRecord;
use Linker\Commerce\Protection\Campaign;
use Linker\Commerce\Protection\Identity;
use Linker\Commerce\Protection\Intake;
use Linker\Commerce\Protection\IntakeStore;
use Linker\Commerce\Protection\Ledger;
use Linker\Commerce\Contact\Submission;
use Linker\Commerce\Inquiry\BillingFields;
use Linker\Commerce\Inquiry\Sender;
use Linker\Commerce\Protection\Fingerprint;
use WC_Order;
use WP_Error;

/**
 * Native intake boundaries with synthetic customer data.
 *
 * @coversNothing
 */
final class SafeIntakeTest extends IntegrationTestCase {
	/** Native isolation, deterministic private mode, no provider calls. */
	protected function setUp(): void {
		parent::setUp();
		$this->as_user( 0 );
		$settings = array(
			'LINKER_PUBLIC_PROTECTION_MODE' => 'enforce',
			'LINKER_TURNSTILE_SITE_KEY'     => '1x00000000000000000000AA',
			'LINKER_TURNSTILE_SECRET_KEY'   => '1x0000000000000000000000000000000AA',
			'LINKER_TURNSTILE_HOSTNAME'     => 'example.com',
		);
		foreach ( $settings as $key => $value ) {
			$old = getenv( $key );
			putenv( $key . '=' . $value );
			$this->later(
				static function () use ( $old, $key ): void {
					putenv( false === $old ? $key : $key . '=' . $old );
				}
			);
		}
		foreach ( array( Ledger::OPTION, IntakeStore::OPTION, Campaign::DISABLED, \Linker\Commerce\Mail\OptionBudgetLedger::OPTION ) as $key ) {
			$old = get_option( $key );
			delete_option( $key );
			$this->later(
				static function () use ( $key, $old ): void {
					delete_option( $key );
					if ( false !== $old ) {
						update_option( $key, $old, false );
					}
				}
			);
		}
		$_COOKIE[ Identity::COOKIE ] = str_repeat( 'a', 32 );
		$this->use_empty_mail_queue();
		wc_load_cart();
		WC()->cart->empty_cart();
		$this->later( static fn () => WC()->cart->empty_cart() );
	}

	/**
	 * Synthetic native form using the official Turnstile test keys.
	 *
	 * @param bool $verified Whether this request includes the public test token.
	 * @return array<string,string>
	 */
	private function post( bool $verified = false ): array {
		$started = (string) time();
		$post    = array(
			'name'                  => 'Safe intake fixture',
			'email'                 => 'intake-' . self::tag() . '@example.test',
			'company'               => '',
			'message'               => 'Please advise on a 10 kWh system. https://example.test/product',
			'consent'               => '1',
			'lang'                  => 'en',
			'linker_request_id'     => wp_generate_uuid4(),
			'cf-turnstile-response' => $verified ? 'XXXX.DUMMY.TOKEN.XXXX' : '',
			'linker_started'        => $started,
			'linker_started_nonce'  => wp_create_nonce( 'linker_inquiry_started_' . $started ),
			'linker_inquiry_nonce'  => wp_create_nonce( Handler::ACTION ),
			'linker_contact_nonce'  => wp_create_nonce( ContactForm::NONCE_ACTION ),
			'linker_draft_hash'     => WC()->cart->get_cart_hash(),
		);

		$this->later(
			static function () use ( $post ): void {
				$orders = wc_get_orders(
					array(
						'billing_email' => $post['email'],
						'limit'         => -1,
					)
				);
				self::assertIsArray( $orders );
				foreach ( $orders as $order ) {
					$order->delete( true );
				}
			}
		);
		return $post;
	}

	/** A single stored review order dating from before the native form cutover.
	 *
	 * @param array<string,string> $post Original native customer input.
	 * @param string               $action Historical form.
	 */
	private function historical_submission( array $post, string $action = 'inquiry' ): WC_Order|WP_Error {
		$identity = Identity::current();
		self::assertInstanceOf( Identity::class, $identity );
		$details = Submission::from_post( $post, 'contact' === $action );
		self::assertInstanceOf( Submission::class, $details );
		$payload     = 'contact' === $action ? get_object_vars( $details ) : array(
			'details' => get_object_vars( $details ),
			'billing' => BillingFields::values( $post ),
			'draft'   => $post['linker_draft_hash'],
		);
		$fingerprint = Fingerprint::make( $identity, $action, $payload );
		self::assertIsString( $fingerprint );
		return Intake::run(
			'verification',
			$action,
			$post['linker_request_id'],
			$fingerprint,
			$identity,
			$payload,
			array( new Allowance( 'historical_review', $identity->browser, 10, HOUR_IN_SECONDS ) ),
			array(),
			array( Allowance::owner_for( Identity::recipient( $details->email ) ) ),
			static fn () => 'contact' === $action ? ( new Sender() )->message( $details ) : ( new Sender() )->request( $details, $post, false )
		);
	}

	/** A guest who has not finished verification creates no new order or notification.
	 *
	 * @testWith ["contact"]
	 *           ["inquiry"]
	 * @param string $action Native door.
	 */
	public function test_required_verification_rejects_before_any_native_record( string $action ): void {
		$post = $this->post();
		$jobs = self::newest_mail_job();
		if ( 'inquiry' === $action ) {
			$result = ( new Handler() )->process( $post );
			self::assertInstanceOf( WP_Error::class, $result );
			self::assertSame( 'linker_admission_proof', $result->get_error_code() );
		} else {
			self::assertSame( 'verification_failed', ( new ContactHandler() )->process( $post ) );
		}
		self::assertSame( array(), wc_get_orders( array( 'billing_email' => $post['email'] ) ) );
		self::assertSame( array(), self::mail_jobs_after( $jobs ) );
	}

	/** Valid customers retain their complete native result and safe UUID retries.
	 *
	 * @testWith ["contact"]
	 *           ["inquiry"]
	 * @param string $action Native door.
	 */
	public function test_verified_submission_is_recovered_and_new_input_requires_a_new_check( string $action ): void {
		$post = $this->post( true );
		$send = 'contact' === $action ? new ContactHandler() : new Handler();
		$send->process( $post );
		$orders = wc_get_orders( array( 'billing_email' => $post['email'] ) );
		self::assertIsArray( $orders );
		self::assertCount( 1, $orders );
		$order = $orders[0];
		self::assertSame( $post['message'], $order->get_customer_note() );
		self::assertFalse( NotificationHold::held( $order ) );
		$retry                          = $post;
		$retry['cf-turnstile-response'] = '';
		$send->process( $retry );
		$retry_orders = wc_get_orders( array( 'billing_email' => $post['email'] ) );
		self::assertIsArray( $retry_orders );
		self::assertCount( 1, $retry_orders );
		$retry['message'] .= ' changed';
		$changed           = $send->process( $retry );
		self::assertTrue( 'contact' === $action ? 'verification_failed' === $changed : $changed instanceof WP_Error );
		$post['linker_request_id']     = wp_generate_uuid4();
		$post['cf-turnstile-response'] = '';
		$reused                        = $send->process( $post );
		self::assertTrue( 'contact' === $action ? 'verification_failed' === $reused : $reused instanceof WP_Error );
		$final_orders = wc_get_orders( array( 'billing_email' => $post['email'] ) );
		self::assertIsArray( $final_orders );
		self::assertCount( 1, $final_orders );
	}

	/** Service configuration failure retains a retry, never a new review record. */
	public function test_required_configuration_outage_cannot_persist_an_unverified_inquiry(): void {
		$post = $this->post( true );
		$old  = getenv( 'LINKER_TURNSTILE_SECRET_KEY' );
		putenv( 'LINKER_TURNSTILE_SECRET_KEY' );
		try {
			$result = ( new Handler() )->process( $post );
		} finally {
			putenv( false === $old ? 'LINKER_TURNSTILE_SECRET_KEY' : 'LINKER_TURNSTILE_SECRET_KEY=' . $old );
		}
		self::assertInstanceOf( WP_Error::class, $result );
		self::assertSame( 'linker_admission_configuration', $result->get_error_code() );
		self::assertSame( array(), wc_get_orders( array( 'billing_email' => $post['email'] ) ) );
		self::assertSame( array(), get_option( IntakeStore::OPTION )['entries'] );
	}

	/** Canonical names and normalized contact selection cannot enter recovery. */
	public function test_campaign_is_not_stored_in_failed_contact_recovery(): void {
		$post = $this->post();
		$key  = 'linker_form_recovery_contact';
		$old  = WC()->session->get( $key );
		$this->later( static fn () => WC()->session->set( $key, $old ) );
		$activity = 'Вам перевод 100 руб. забрать тут https://fredmer.buzz/path';
		foreach ( array( $activity, str_replace( 'Вам перевод', "Вам\nперевод", $activity ), $activity . str_repeat( 'x', 200 ) . ' trailing' ) as $name ) {
			$post['name'] = $name;
			\Linker\Commerce\Protection\FormRecovery::save( 'contact', $post );
			self::assertSame( $old, WC()->session->get( $key ) );
		}
		$post['name'] = 'Installer recovery fixture';

		\Linker\Commerce\Protection\FormRecovery::save( 'contact', $post );
		$saved = WC()->session->get( $key );
		self::assertIsArray( $saved );
		self::assertSame( $post['name'], $saved['fields']['name'] );
		self::assertSame( $post['message'], $saved['fields']['message'] );
	}

	/** A normalized search condition is checked independently of editable text. */
	public function test_campaign_selection_is_not_stored_in_contact_recovery(): void {
		$post     = $this->post();
		$key      = 'linker_form_recovery_contact';
		$old      = WC()->session->get( $key );
		$activity = 'Вам перевод 100 руб. забрать тут https://fredmer.buzz/path';
		$this->later( static fn () => WC()->session->set( $key, $old ) );
		$product = $this->product( '10' );
		$post[ \Linker\Commerce\Contact\SelectionContext::FIELD ] = (string) wp_json_encode(
			array(
				'source'    => get_permalink( $product->get_id() ),
				'selection' => array( 'q' => $activity ),
			)
		);
		\Linker\Commerce\Protection\FormRecovery::save( 'contact', $post );
		self::assertSame( $old, WC()->session->get( $key ) );
	}

	/** Actual native transport also excludes refused activity from inquiry recovery. */
	public function test_refused_inquiry_transport_excludes_activity_and_keeps_normal_retry_input(): void {
		$old_post = $_POST;
		$old      = WC()->session->get( 'linker_inquiry_fields' );
		$this->later( static fn () => WC()->session->set( 'linker_inquiry_fields', $old ) );
		$redirect = static function ( string $location ): string {
			if ( '' === $location ) {
				return $location;
			}
			throw new \RuntimeException( 'fixture_redirect_reached' );
		};
		add_filter( 'wp_redirect', $redirect );
		try {
			foreach ( array( "Вам\nперевод 100 руб. забрать тут https://fredmer.buzz/path", 'Installer transport fixture' ) as $name ) {
				$post         = $this->post();
				$post['name'] = $name;
				$_POST        = wp_slash( $post );
				try {
					( new Handler() )->handle();
					self::fail( 'Native redirect was not reached.' );
				} catch ( \RuntimeException $error ) {
					self::assertSame( 'fixture_redirect_reached', $error->getMessage() );
				}
				$saved = WC()->session->get( 'linker_inquiry_fields' );
				if ( 'Installer transport fixture' === $name ) {
					self::assertIsArray( $saved );
					self::assertSame( $post['name'], $saved['name'] );
					self::assertSame( $post['message'], $saved['message'] );
				} else {
					self::assertNull( $saved );
				}
				self::assertSame( array(), wc_get_orders( array( 'billing_email' => $post['email'] ) ) );
			}
		} finally {
			remove_filter( 'wp_redirect', $redirect );
			$_POST = $old_post;
		}
	}

	/** A historical review record retains its original acknowledgement through a modern retry. */
	public function test_historical_held_submission_recovers_its_original_woo_order(): void {
		$post   = $this->post();
		$jobs   = self::newest_mail_job();
		$budget = get_option( Throttle::OPTION );
		$order  = $this->historical_submission( $post );
		self::assertInstanceOf( WC_Order::class, $order );
		self::assertSame( $post['message'], $order->get_customer_note() );
		self::assertSame( $post['email'], $order->get_billing_email() );
		self::assertSame( $post['linker_request_id'], $order->get_meta( BusinessRecord::REQUEST ) );
		self::assertSame( 'verification', $order->get_meta( Intake::META )['lane'] );
		self::assertTrue( NotificationHold::held( $order ) );
		self::assertSame( $post['message'], Queue::data( $order )['snapshot']['submission']['message'] );
		$pending = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
		self::assertIsArray( $pending );
		self::assertSame( 'pending', $pending['status'] );
		self::assertSame( 0, $pending['attempts'] );
		$receipt = self::fixed_receipt_job( $order );
		self::assertSame( array( $receipt ), self::mail_jobs_after( $jobs ) );
		self::assertSame( $budget, get_option( Throttle::OPTION ) );
		$retry = ( new Handler() )->process( $post );
		self::assertInstanceOf( WC_Order::class, $retry );
		self::assertSame( $order->get_id(), $retry->get_id() );
		$post['message'] .= ' edited';
		$changed          = ( new Handler() )->process( $post );
		self::assertInstanceOf( WP_Error::class, $changed );
		self::assertSame( 'linker_admission_payload_changed', $changed->get_error_code() );
		$queue = new Queue();
		$queue->process( $order->get_id() );
		$queue->expire( $order->get_id() );
		$queue->finish( $order->get_id(), Result::unknown( 'late' ) );
		self::assertSame( array( $receipt ), self::mail_jobs_after( $jobs ) );
	}

	/**
	 * Both accepted customer paths deliver only the fixed acknowledgement before the content decision.
	 *
	 * @dataProvider accepted_verifications
	 * @param bool $verified Whether the native verification proof is present.
	 */
	public function test_accepted_order_acknowledges_once_before_the_team_is_authorized( bool $verified ): void {
		$post    = $this->post( $verified );
		$handler = new Handler();
		$order   = $verified ? $handler->process( $post ) : $this->historical_submission( $post );
		self::assertInstanceOf( WC_Order::class, $order );
		self::assertSame( ! $verified, NotificationHold::held( $order ) );
		$job = self::fixed_receipt_job( $order );

		$sent    = 0;
		$observe = static function () use ( &$sent ): void {
			++$sent;
		};
		add_action( 'wp_mail_succeeded', $observe );
		try {
			do_action( Outbox::HOOK, $job ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Drive the original job.
			$replay = $handler->process( $post );
			self::assertInstanceOf( WC_Order::class, $replay );
			self::assertSame( $order->get_id(), $replay->get_id() );
			do_action( Outbox::HOOK, $job ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Replay the same consumer.
		} finally {
			remove_action( 'wp_mail_succeeded', $observe );
		}
		$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
		self::assertIsArray( $state );
		self::assertSame( 'pending', $state['status'] );
		self::assertSame( array( 'receipt' ), array_keys( $state['jobs'] ) );
		self::assertSame( $job, $state['jobs']['receipt']['id'] );
		self::assertNotEmpty( $state['jobs']['receipt']['delivered_at'] );
		self::assertSame( 1, $sent );
	}

	/** Accepted guest verification paths.
	 *
	 * @return array<string,array{bool}>
	 */
	public static function accepted_verifications(): array {
		return array(
			'verified visitor'  => array( true ),
			'historical review' => array( false ),
		);
	}

	/** Native notification handoff releases one slot and preserves the completed request. */
	public function test_normal_verification_frees_its_slot_after_notification_handoff(): void {
		require_once dirname( __DIR__, 2 ) . '/fixtures/NormalMailAuthorizationFixture.php';
		$authorization = \Linker\Commerce\Tests\Fixtures\NormalMailAuthorizationFixture::install( $this->later( ... ) );
		$handler       = new Handler();
		$post          = $this->post();
		$check         = $post + array( 'linker_inquiry_receipt_only' => '1' );
		$unknown       = $handler->process( $check );
		self::assertInstanceOf( WP_Error::class, $unknown );
		self::assertSame( 'linker_inquiry_pending', $unknown->get_error_code() );
		self::assertSame( array(), get_option( IntakeStore::OPTION )['entries'] ?? array() );
		$order = $this->historical_submission( $post );
		self::assertInstanceOf( WC_Order::class, $order );
		$pending = $this->post();
		$other   = $this->historical_submission( $pending );
		self::assertInstanceOf( WC_Order::class, $other );
		self::assertTrue( NotificationHold::held( $order ) );
		$before = get_option( IntakeStore::OPTION )['entries'];
		self::assertArrayHasKey( $post['linker_request_id'], $before );
		$state = $authorization->process( $order );
		self::assertEqualsCanonicalizing( array( 'team', 'receipt' ), array_keys( $state['jobs'] ) );
		foreach ( $state['jobs'] as $job ) {
			self::assertNotNull( ( new \Linker\Commerce\Mail\JobStore() )->load( $job['id'] ) );
		}
		$order->read_meta_data( true );
		self::assertFalse( NotificationHold::held( $order ) );
		self::assertSame( array( $pending['linker_request_id'] ), array_keys( get_option( IntakeStore::OPTION )['entries'] ) );
		$replay = $handler->process( $check );
		self::assertInstanceOf( WC_Order::class, $replay );
		self::assertSame( $order->get_id(), $replay->get_id() );
		self::assertSame( $state, \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() ) );
	}

	/** Maintenance recovers a terminal handoff even after it leaves the pending notification queue. */
	public function test_completed_verification_release_recovers_after_an_interruption(): void {
		require_once dirname( __DIR__, 2 ) . '/fixtures/NormalMailAuthorizationFixture.php';
		$authorization = \Linker\Commerce\Tests\Fixtures\NormalMailAuthorizationFixture::install( $this->later( ... ) );
		$post          = $this->post();
		$order         = $this->historical_submission( $post );
		self::assertInstanceOf( WC_Order::class, $order );
		$request = $post['linker_request_id'];
		$entry   = get_option( IntakeStore::OPTION )['entries'][ $request ];
		$authorization->process( $order, true );
		$order->read_meta_data( true );
		self::assertSame( 'complete', $order->get_meta( Queue::PENDING ) );
		$before = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
		self::assertIsArray( $before );
		self::assertNotEmpty( $before['jobs']['team']['delivered_at'] );
		self::assertNotEmpty( $before['jobs']['receipt']['delivered_at'] );
		// Restore the exact slot and unresolved journal state from before native binding.
		$entry['order'] = 0;
		$ledger         = json_decode( (string) get_option( Ledger::OPTION ), true, 512, JSON_THROW_ON_ERROR );

		$ledger['receipts'][ $request ]['status']  = 'unresolved';
		$ledger['receipts'][ $request ]['outcome'] = 0;
		update_option( Ledger::OPTION, wp_json_encode( $ledger ), false );
		self::assertIsArray(
			IntakeStore::edit(
				static function ( array &$state ) use ( $request, $entry ): array {
					$state['entries'][ $request ] = $entry;
					IntakeStore::save( $state );
					return array();
				}
			)
		);
		$job_marker = self::newest_mail_job();
		$module     = new \Linker\Commerce\Protection\Module( __FILE__ );
		self::assertTrue( \Linker\Commerce\Inquiry\Assessment\Lock::run( 'intake-write-' . $request, $module->maintain( ... ) ) );
		self::assertArrayHasKey( $request, get_option( IntakeStore::OPTION )['entries'] );
		$module->maintain();
		$module->maintain();
		self::assertArrayNotHasKey( $request, get_option( IntakeStore::OPTION )['entries'] );
		$receipt = ( new Ledger() )->lookup( $request, $entry['fingerprint'] );
		self::assertIsArray( $receipt );
		self::assertSame( 'completed', $receipt['status'] );
		self::assertSame( $order->get_id(), $receipt['outcome'] );
		self::assertSame( $before, \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() ) );
		self::assertSame( array(), self::mail_jobs_after( $job_marker ) );
		$retry = ( new Handler() )->process( $post );
		self::assertInstanceOf( WC_Order::class, $retry );
		self::assertSame( $order->get_id(), $retry->get_id() );
	}

	/** Native field limits are UTF-8 characters, not JSON escape sequences. */
	public function test_valid_full_length_unicode_message_is_completely_saved(): void {
		$post            = $this->post( true );
		$post['message'] = str_repeat( '🔋', \Linker\Commerce\Contact\Submission::MAX_MESSAGE );
		$order           = ( new Handler() )->process( $post );
		self::assertInstanceOf( WC_Order::class, $order );
		self::assertSame( $post['message'], $order->get_customer_note() );
		self::assertFalse( NotificationHold::held( $order ) );
	}

	/** Historical pending reviews do not block a new completed submission. */
	public function test_full_historical_review_queue_allows_new_verified_requests(): void {
		$entries = array();
		for ( $i = 0; $i < IntakeStore::CAPACITY['verification']; ++$i ) {
			$entries[ wp_generate_uuid4() ] = array(
				'lane'  => 'verification',
				'order' => 0,
				'at'    => time() - 2 * DAY_IN_SECONDS,
			);
		}
		update_option(
			IntakeStore::OPTION,
			array(
				'entries'        => $entries,
				'campaign_count' => 0,
			),
			false
		);
		$normal = ( new Handler() )->process( $this->post( true ) );
		self::assertInstanceOf( WC_Order::class, $normal );
		self::assertFalse( NotificationHold::held( $normal ) );
		self::assertSame( $entries, get_option( IntakeStore::OPTION )['entries'] );
	}

	/** Confirmed activity in any customer text field is refused before every writer. */
	public function test_confirmed_campaign_fields_cannot_create_grouped_or_individual_records(): void {
		$http  = 0;
		$block = static function () use ( &$http ): WP_Error {
			++$http;
			return new WP_Error( 'fixture_no_external_requests' );
		};
		add_filter( 'pre_http_request', $block );
		$this->later(
			static function () use ( $block ): void {
				remove_filter( 'pre_http_request', $block );
			}
		);
		$marker = self::newest_mail_job();
		foreach ( array( 'inquiry', 'contact' ) as $action ) {
			foreach ( array( 'name', 'company', 'message' ) as $field ) {
				foreach ( array( '', '1' ) as $individual ) {
					$post                             = $this->post( true );
					$post[ $field ]                   = 'Вам перевод 100 руб. забрать тут https://xtimex.buzz/synthetic';
					$post['linker_individual_review'] = $individual;
					$ledger                           = get_option( Ledger::OPTION );
					$intake                           = get_option( IntakeStore::OPTION );
					$budget                           = get_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION );
					$throttle                         = get_option( Throttle::OPTION );
					if ( 'inquiry' === $action ) {
						$result = ( new Handler() )->process( $post );
						self::assertInstanceOf( WP_Error::class, $result );
						self::assertSame( 'linker_admission_input', $result->get_error_code() );
					} else {
						self::assertSame( 'verification_failed', ( new ContactHandler() )->process( $post ) );
					}
					self::assertSame( array(), wc_get_orders( array( 'billing_email' => $post['email'] ) ) );
					self::assertSame( $ledger, get_option( Ledger::OPTION ) );
					self::assertSame( $intake, get_option( IntakeStore::OPTION ) );
					self::assertSame( $budget, get_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION ) );
					self::assertSame( $throttle, get_option( Throttle::OPTION ) );
				}
			}
		}
		self::assertSame( array(), self::mail_jobs_after( $marker ) );
		self::assertSame( 0, $http );
	}

	/** The observed profit activity survives native name truncation without a URL. */
	public function test_confirmed_profit_activity_is_blocked_in_native_name_and_company_fields(): void {
		$messages = array(
			'Добрый день! Для вас открыт к платформе с доходностью от 12% в неделю. Мин. сумма 100 долларов, регистрация за 2 минуты.',
			'Здравствуйте. Вам доступен к системе с доходом от 12% в неделю. Вход 100 долларов, регистрация занимает 2 минуты.',
			'Для вас открыт закрытому фонду #7. Система автоматически генерирует доход от 12% еженедельно от вложенной суммы. Вход 100 долларов.',
			'Здравствуйте. Для вас открыт к платформе с доходностью от 12% в неделю. Вход 100 долларов, подключение за 2 минуты. Начать: https://xtimex.buzz/synthetic',
			'Здравствуйте. Вы получили это письмо по своей подписке, и для новых участников открыт доступ к закрытому фонду. Доходность от 12% в неделю при минимальном вложении 100$.',
			'Добрый день. Вы получили это письмо по своей подписке, и для новых участников открыт доступ к закрытому фонду. Доходность от 12% в неделю при депозите от 100$.',
		);
		foreach ( $messages as $message ) {
			self::assertTrue( Campaign::matches( $message ) );
			foreach ( array( 'name', 'company', 'message' ) as $field ) {
				$post           = $this->post( true );
				$post[ $field ] = $message;
				$result         = ( new Handler() )->process( $post );
				self::assertInstanceOf( WP_Error::class, $result );
				self::assertSame( 'linker_admission_input', $result->get_error_code() );
				self::assertSame( array(), wc_get_orders( array( 'billing_email' => $post['email'] ) ) );
			}
		}
	}

	/** Technical Russian, quotations, normal links and domain substrings stay normal. */
	public function test_campaign_rule_does_not_generalize_language_or_links(): void {
		$messages = array( 'Нужна батарея 10 кВт·ч https://fredmer.buzz/manual', 'Вам перевод 100 руб. забрать тут https://fredmer.buzz.evil.test/x', 'Вам перевод 100 руб. забрать тут https://example.test/fredmer.buzz', 'Please investigate this scam: Вам перевод 100 руб. забрать тут https://fredmer.buzz/x', "Вам перевод 100 руб. забрать тут https://fredmer.buzz/x\nPlease quote an inverter.", 'Нужна батарея 10 кВт·ч https://xtimex.buzz/manual', 'Вам перевод 100 руб. забрать тут https://xtimex.buzz.evil.test/x', 'Вам перевод 100 руб. забрать тут https://xtimex.buzz@example.test/x', 'Please investigate this scam: Вам перевод 100 руб. забрать тут https://xtimex.buzz/x', "Вам перевод 100 руб. забрать тут https://xtimex.buzz/x\nPlease quote an inverter." );
		foreach ( $messages as $message ) {
			self::assertFalse( Campaign::matches( $message ) );
			$post            = $this->post( true );
			$post['name']    = 'Александр Müller';
			$post['company'] = 'EPC Köln / 光伏工程';
			$post['message'] = $message;
			$order           = ( new Handler() )->process( $post );
			self::assertInstanceOf( WC_Order::class, $order );
			self::assertFalse( NotificationHold::held( $order ) );
		}
		self::assertTrue( Campaign::matches( 'Вам перевод 100 руб. получить тут https://fredmer.buzz/x' ) );
		self::assertTrue( Campaign::matches( 'Вам перевод 100 руб. забрать тут https://xtimex.buzz/x' ) );
		self::assertTrue( Campaign::matches( 'Вам перевод 100 руб. получить тут https://xtimex.buzz/x' ) );
		update_option( Campaign::DISABLED, 'yes', false );
		self::assertFalse( Campaign::matches( 'Вам перевод 100 руб. получить тут https://fredmer.buzz/x' ) );
		self::assertFalse( Campaign::matches( 'Вам перевод 100 руб. получить тут https://xtimex.buzz/x' ) );
	}

	/** Technical finance, quoted reports and multilingual customer names remain valid. */
	public function test_technical_roi_prices_and_quoted_activity_remain_normal(): void {
		$messages = array(
			'Здравствуйте. Нужна батарея 10 кВт·ч. Цена 100 долларов? КПД выше на 12%. https://example.test/datasheet.pdf',
			'Please quote the 100 USD monitoring option. Our technical ROI report assumes 12% yearly savings. https://example.test/report.pdf',
			'Bitte senden Sie das Datenblatt. Unser Bericht nennt 12% Wirkungsgradverbesserung und 100$ Mehrkosten. https://example.test/datenblatt.pdf',
			'Please investigate this quoted report: Добрый день! Для вас открыт к платформе с доходностью от 12% в неделю. Мин. сумма 100 долларов.',
			'Здравствуйте. Прошу проверить цитату: Для вас открыт закрытому фонду #7. Система автоматически генерирует доход от 12% еженедельно от вложенной суммы. Вход 100 долларов.',
		);
		foreach ( $messages as $message ) {
			self::assertFalse( Campaign::matches( $message ) );
			$post            = $this->post( true );
			$post['name']    = 'Александр Müller';
			$post['company'] = 'EPC Köln / 光伏工程';
			$post['message'] = $message;
			$order           = ( new Handler() )->process( $post );
			self::assertInstanceOf( WC_Order::class, $order );
			self::assertFalse( NotificationHold::held( $order ) );
		}
	}

	/** The original-job-absent case hands off exactly once, preserving all content. */
	public function test_staff_can_release_new_review_record_without_original_job_once(): void {
		$order = $this->historical_submission( $this->post() );
		self::assertInstanceOf( WC_Order::class, $order );
		$basis = NotificationHold::reference( $order );
		self::assertInstanceOf( WP_Error::class, NotificationHold::release( $order->get_id(), $basis ) );
		$staff = $this->customer();
		$user  = get_userdata( $staff->get_id() );
		self::assertInstanceOf( \WP_User::class, $user );
		$user->set_role( 'shop_manager' );
		$this->as_user( $staff->get_id() );
		$budget = array_fill( 0, Throttle::PER_DAY, time() );
		update_option( Throttle::OPTION, $budget, false );
		$marker = self::newest_mail_job();
		$review = \Linker\Commerce\Inquiry\Assessment\Reviews::save(
			$order->get_id(),
			0,
			'correct',
			array(
				'label' => 'normal',
				'note'  => 'Native fixture checked the complete source.',
				'basis' => \Linker\Commerce\Inquiry\Assessment\Reviews::reference( $order ),
			)
		);
		self::assertIsArray( $review );
		self::assertSame( array(), self::mail_jobs_after( $marker ), 'A staff correction alone does not authorize transport.' );
		$order->read_meta_data( true );
		$basis  = NotificationHold::reference( $order );
		$result = NotificationHold::release( $order->get_id(), $basis );
		self::assertIsArray( $result );
		$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
		self::assertIsArray( $state );
		self::assertEqualsCanonicalizing( array( 'team', 'receipt' ), array_keys( $state['jobs'] ) );
		self::assertSame( $marker, $state['jobs']['receipt']['id'] );
		$job = $state['jobs']['team']['id'];
		self::assertGreaterThan( 0, $job );
		self::assertFalse( ( new \Linker\Commerce\Mail\JobStore() )->critical( $job ), 'Public content retains the ordinary quota after a native explicit staff release.' );
		self::assertSame( $result, NotificationHold::release( $order->get_id(), $basis ) );
		self::assertCount( 1, self::mail_jobs_after( $marker ) );
		self::assertSame( $budget, get_option( Throttle::OPTION ) );
		$order->read_meta_data( true );
		self::assertFalse( NotificationHold::held( $order ) );
		self::assertSame( array(), get_option( IntakeStore::OPTION )['entries'] );
		self::assertSame( 'human_override', $state['producer'] );
		self::assertSame( 'staff_release_team_only', $order->get_meta( \Linker\Commerce\Inquiry\ReceiptLimit::SKIPPED_META ) );
		self::assertTrue( as_has_scheduled_action( Outbox::HOOK, array( $job ), Outbox::GROUP ) );
	}

	/** Native PII removal includes added registry and intake metadata. */
	public function test_native_erasure_removes_added_links_and_review_metadata(): void {
		$order = $this->historical_submission( $this->post() );
		self::assertInstanceOf( WC_Order::class, $order );
		\WC_Privacy_Erasers::remove_order_personal_data( $order );
		$order->read_meta_data( true );
		self::assertSame( '', $order->get_meta( Intake::META ) );
		self::assertSame( '[deleted]', $order->get_meta( BusinessRecord::REQUEST ) );
		self::assertSame( array(), get_option( IntakeStore::OPTION )['entries'] );
		self::assertStringNotContainsString( 'example.test', (string) wp_json_encode( get_option( IntakeStore::OPTION ) ) );
	}

	/** Public erasure cannot be undone by a later staff notification release. */
	public function test_erased_review_association_cannot_be_released(): void {
		$post  = $this->post();
		$order = $this->historical_submission( $post );
		self::assertInstanceOf( WC_Order::class, $order );
		self::assertTrue( ( new \Linker\Commerce\Protection\Privacy() )->erase( $post['email'] )['items_removed'] );
		$staff = $this->customer();
		$user  = get_userdata( $staff->get_id() );
		self::assertInstanceOf( \WP_User::class, $user );
		$user->set_role( 'shop_manager' );
		$this->as_user( $staff->get_id() );
		$marker = self::newest_mail_job();
		self::assertInstanceOf( WP_Error::class, NotificationHold::release( $order->get_id(), NotificationHold::reference( $order ) ) );
		self::assertSame( array(), self::mail_jobs_after( $marker ) );
		$order->read_meta_data( true );
		self::assertTrue( NotificationHold::held( $order ) );
	}

	/** Native erasure cannot pass an employee holding the record's release lock. */
	public function test_native_erasure_and_staff_release_serialize_across_connections(): void {
		$order = $this->historical_submission( $this->post() );
		self::assertInstanceOf( WC_Order::class, $order );
		$reference = NotificationHold::reference( $order );
		$erasure   = array();
		$released  = null;
		self::assertTrue(
			\Linker\Commerce\Inquiry\Assessment\Lock::run(
				'release-' . $order->get_id(),
				function () use ( $order, $reference, &$erasure, &$released ): void {
					// A retains its pre-erasure object; B attempts the entire native eraser.
					$erasure  = $this->erase_in_other_connection( $order->get_id() );
					$released = \Linker\Commerce\Protection\IntakeRelease::run( $order, $reference );
				}
			)
		);
		self::assertSame( 'intake_erasure_busy', $erasure['status'] );
		self::assertIsArray( $released );
		self::assertGreaterThan( 0, $released['job'] );
		$order->read_meta_data( true );
		self::assertSame( '', $order->get_meta( \Linker\Commerce\Inquiry\Assessment\Reviews::ERASED ) );
	}

	/** A completed erase wins even when staff retained a complete stale Woo object. */
	public function test_completed_native_erasure_cannot_be_resurrected_from_stale_object(): void {
		$post  = $this->post();
		$order = $this->historical_submission( $post );
		self::assertInstanceOf( WC_Order::class, $order );
		$reference = NotificationHold::reference( $order );
		$marker    = self::newest_mail_job();
		self::assertSame( 'erased', $this->erase_in_other_connection( $order->get_id() )['status'] );
		self::assertSame( $post['email'], $order->get_billing_email() );
		self::assertNotEmpty( $order->get_meta( Intake::META ) );
		$released = null;
		self::assertTrue(
			\Linker\Commerce\Inquiry\Assessment\Lock::run(
				'release-' . $order->get_id(),
				static function () use ( $order, $reference, &$released ): void {
					$released = \Linker\Commerce\Protection\IntakeRelease::run( $order, $reference );
				}
			)
		);
		self::assertInstanceOf( WP_Error::class, $released );
		self::assertSame( array(), self::mail_jobs_after( $marker ) );
		$persisted = \Linker\Commerce\Inquiry\Assessment\CurrentSource::order( $order->get_id() );
		self::assertInstanceOf( WC_Order::class, $persisted );
		self::assertSame( 'yes', $persisted->get_meta( \Linker\Commerce\Inquiry\Assessment\Reviews::ERASED ) );
		self::assertSame( '', $persisted->get_meta( Intake::META ) );
		wp_cache_delete( IntakeStore::OPTION, 'options' );
		self::assertSame( array(), get_option( IntakeStore::OPTION )['entries'] );
	}

	/**
	 * Run Woo's real eraser while the caller keeps its own DB connection and cache.
	 *
	 * @param int $id Synthetic native inquiry.
	 * @return array<string,mixed>
	 */
	private function erase_in_other_connection( int $id ): array {
		return $this->run_native_worker( 'intake_privacy_worker.php', array( (string) $id ) );
	}

	/**
	 * Execute one local worker with its own native DB connection and object cache.
	 *
	 * @param string   $fixture Tracked fixture filename.
	 * @param string[] $arguments Fixture arguments.
	 * @phpstan-param list<string> $arguments
	 * @return array<string,mixed>
	 */
	private function run_native_worker( string $fixture, array $arguments ): array {
		$pipes = array();
		// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open -- Independent local WordPress/DB connection, no external calls.
		$process = proc_open(
			array_merge( array( PHP_BINARY, '-d', 'memory_limit=2048M', dirname( __DIR__, 2 ) . '/fixtures/' . $fixture ), $arguments ),
			array(
				0 => array( 'pipe', 'r' ),
				1 => array( 'pipe', 'w' ),
				2 => array( 'pipe', 'w' ),
			),
			$pipes
		);
		self::assertIsResource( $process );
		fclose( $pipes[0] );
		$out = stream_get_contents( $pipes[1] );
		$err = stream_get_contents( $pipes[2] );
		fclose( $pipes[1] );
		fclose( $pipes[2] );
		self::assertSame( 0, proc_close( $process ), (string) $err );
		$result = json_decode( (string) $out, true );
		self::assertIsArray( $result, (string) $out );
		return $result;
	}

	/** A failed durable staff audit rolls back its job and preserves both budgets. */
	public function test_staff_release_rollback_preserves_existing_transport_history(): void {
		$order = $this->historical_submission( $this->post() );
		self::assertInstanceOf( WC_Order::class, $order );
		$staff = $this->customer();
		$user  = get_userdata( $staff->get_id() );
		self::assertInstanceOf( \WP_User::class, $user );
		$user->set_role( 'shop_manager' );
		$this->as_user( $staff->get_id() );
		$legacy = array( time() - 120 );
		$state  = wp_json_encode(
			array(
				'entries' => array(
					array(
						'time'      => time() - 120,
						'transport' => Throttle::PHP,
					),
				),
			)
		);
		update_option( Throttle::OPTION, $legacy, false );
		update_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION, $state, false );
		$marker = self::newest_mail_job();
		$fail   = static fn ( $check, $id, $key ) => NotificationHold::EVENT === $key ? false : $check;
		add_filter( 'add_comment_metadata', $fail, 10, 3 );
		try {
			self::assertInstanceOf( WP_Error::class, NotificationHold::release( $order->get_id(), NotificationHold::reference( $order ) ) );
		} finally {
			remove_filter( 'add_comment_metadata', $fail, 10 );
		}
		self::assertSame( array(), self::mail_jobs_after( $marker ) );
		wp_cache_delete( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION, 'options' );
		self::assertSame( $state, get_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION ) );
		self::assertSame( $legacy, get_option( Throttle::OPTION ) );
		$order->read_meta_data( true );
		self::assertTrue( NotificationHold::held( $order ) );
		self::assertCount( 1, get_option( IntakeStore::OPTION )['entries'] );
	}

	/** A crash after the first native save recovers the same full record. */
	public function test_interrupted_native_save_recovers_original_without_second_debit(): void {
		$post      = $this->post( true );
		$armed     = false;
		$committed = false;
		$arm       = static function ( WC_Order $order ) use ( $post, &$armed ): void {
			if ( $order->get_billing_email() === $post['email'] && $order->has_status( \Linker\Commerce\Inquiry\Statuses::RECEIVED ) ) {
				$armed = true; }
		};
		$fail      = static function ( string $sql ) use ( &$armed, &$committed ): string {
			if ( $armed && ! $committed && 'COMMIT' === $sql ) {
				global $wpdb;
				// phpcs:ignore WordPress.DB.RestrictedFunctions -- Execute the exact owned native commit before losing its application acknowledgement.
				$wpdb->__get( 'dbh' )->query( 'COMMIT' );
				$committed = true;
				throw new \Error( 'fixture_interrupted_commit_ack' );
			}
			return $sql;
		};
		add_action( 'woocommerce_after_order_object_save', $arm );
		add_filter( 'query', $fail, 999 );
		try {
			$result = ( new ContactHandler() )->process( $post ); } finally {
			remove_action( 'woocommerce_after_order_object_save', $arm );
			remove_filter( 'query', $fail, 999 ); }
			self::assertTrue( $committed, 'The native row/status commit really occurred; only its response is unknown.' );
			self::assertSame( 'receipt_pending', $result );
			$orders = wc_get_orders( array( 'billing_email' => $post['email'] ) );
			self::assertIsArray( $orders );
			self::assertCount( 1, $orders );
			$before = json_decode( (string) get_option( Ledger::OPTION ), true );
			self::assertSame( 'receipt_pending', ( new ContactHandler() )->process( $post ) );
			$recovered = wc_get_order( $orders[0]->get_id() );
			self::assertInstanceOf( WC_Order::class, $recovered );
			self::assertSame( $orders[0]->get_id(), $recovered->get_id() );
			self::assertSame( $post['message'], $recovered->get_customer_note() );
			self::assertFalse( NotificationHold::held( $recovered ) );
			$after = json_decode( (string) get_option( Ledger::OPTION ), true );
			self::assertSame( $before['buckets'], $after['buckets'] );
			self::assertSame( \Linker\Commerce\Inquiry\Statuses::RECEIVED, $recovered->get_status() );
	}
	/** The native order keeps the complete native product draft for guest/pending/approved customers. */
	public function test_native_submission_retains_product_and_quantity_for_all_customer_states(): void {
		$product = $this->product( '1800' );
		foreach ( array( 'guest', 'pending', 'approved' ) as $status ) {
			if ( 'guest' === $status ) {
				$this->as_user( 0 );
			} else {
				$customer = $this->customer();
				update_user_meta( $customer->get_id(), \Linker\Commerce\Registration\Approval::STATUS_META, $status );
				$this->as_user( $customer->get_id() );
			}
			self::assertIsString( WC()->cart->add_to_cart( $product->get_id(), 2 ) );
			$post            = $this->post( 'guest' === $status );
			$post['message'] = '';
			$order           = ( new Handler() )->process( $post );
			self::assertInstanceOf( WC_Order::class, $order );
			self::assertFalse( NotificationHold::held( $order ) );
			self::assertCount( 1, $order->get_items() );
			$line = current( $order->get_items() );
			self::assertInstanceOf( \WC_Order_Item_Product::class, $line );
			self::assertSame( $product->get_id(), $line->get_product_id() );
			self::assertSame( 2, $line->get_quantity() );
			self::assertTrue( WC()->cart->is_empty() );
		}
	}

	/** Confirmation uses its actual record rather than a later form's session number. */
	public function test_review_confirmation_uses_authorized_record_and_no_duplicate_receipt_notice(): void {
		$order = $this->historical_submission( $this->post() );
		self::assertInstanceOf( WC_Order::class, $order );
		WC()->session->set( 'linker_review_saved', 'a-different-later-record' );
		ob_start();
		( new \Linker\Commerce\Inquiry\Checkout() )->next_steps( $order->get_id() );
		$html = (string) ob_get_clean();
		self::assertStringContainsString( '#' . $order->get_order_number(), $html );
		self::assertStringNotContainsString( 'a-different-later-record', $html );
		self::assertStringNotContainsString( 'We have not sent a confirmation email.', $html );
		self::assertStringContainsString( 'We reply within one business day', $html );
	}
	/** Erasure can find a crash before the first Woo ID, without refunding its slot. */
	public function test_privacy_erases_unwritten_reservation_and_prevents_resurrection(): void {
		$post = $this->post();
		$fail = static function ( WC_Order $order ) use ( $post ): void {
			if ( $order->get_billing_email() === $post['email'] ) {
				throw new \Error( 'fixture_before_first_write' );
			}
		};
		add_action( 'woocommerce_before_order_object_save', $fail, 99 );
		try {
			self::assertInstanceOf( WP_Error::class, $this->historical_submission( $post, 'contact' ) );
		} finally {
			remove_action( 'woocommerce_before_order_object_save', $fail, 99 );
		}
		self::assertSame( array(), wc_get_orders( array( 'billing_email' => $post['email'] ) ) );
		$privacy = new \Linker\Commerce\Protection\Privacy();
		$export  = $privacy->export( $post['email'] );
		self::assertNotEmpty( array_filter( $export['data'], static fn ( array $row ): bool => str_starts_with( $row['item_id'], 'review-capacity-' ) ) );
		$erased = $privacy->erase( $post['email'] );
		self::assertTrue( $erased['items_removed'] );
		$state = get_option( IntakeStore::OPTION );
		self::assertCount( 1, $state['entries'] );
		$entry = $state['entries'][ $post['linker_request_id'] ];
		self::assertSame( array(), $entry['owners'] );
		self::assertSame( '', $entry['fingerprint'] );
		self::assertSame( '', $entry['binding'] );
		self::assertSame( 'pending', ( new ContactHandler() )->process( $post ) );
		self::assertSame(
			array(),
			wc_get_orders(
				array(
					'billing_email' => $post['email'],
					'limit'         => 10,
				)
			)
		);
	}
	/** The operational summary includes genuine review requests, not campaign samples. */
	public function test_pending_summary_excludes_confirmed_campaign_and_normal_jev_requests(): void {
		$review = $this->historical_submission( $this->post() );
		self::assertInstanceOf( WC_Order::class, $review );
		$historical = function ( string $lane ): WC_Order {
			$post  = $this->post();
			$order = new WC_Order();
			$order->set_billing_email( $post['email'] );
			$order->set_customer_note( 'Вам перевод 100 руб. забрать тут https://fredmer.buzz/synthetic-history' );
			$order->update_meta_data( Intake::META, array( 'lane' => $lane ) );
			$order->update_meta_data( Intake::LANE_META, $lane );
			$order->update_meta_data( NotificationHold::META, array( 'reason' => 'historical_fixture' ) );
			$order->save();
			$result = IntakeStore::edit(
				static function ( array &$state ) use ( $lane, $post, $order ): array {
					$state['entries'][ $post['linker_request_id'] ] = array(
						'lane'  => $lane,
						'order' => $order->get_id(),
						'at'    => time(),
					);
					IntakeStore::save( $state );
					return array();
				}
			);
			self::assertIsArray( $result );
			return $order;
		};
		$campaign   = $historical( 'campaign' );
		$summary    = Intake::pending_summary();
		self::assertIsArray( $summary );
		self::assertSame( 1, $summary['count'] );
		self::assertGreaterThan( 0, $summary['oldest'] );
		self::assertStringContainsString( 'linker_intake_review=1', $summary['url'] );
		// phpcs:ignore WooCommerce.Commenting.CommentHooks.MissingHookComment -- Trusted read-only producer seam for aggregate operational alerts.
		self::assertSame( $summary, apply_filters( 'linker_commerce_pending_review_summary', null ) );
		$individual = $historical( 'individual' );
		self::assertInstanceOf( WC_Order::class, ( new Handler() )->process( $this->post( true ) ) );
		$summary = Intake::pending_summary();
		self::assertIsArray( $summary );
		self::assertSame( 2, $summary['count'] );
		foreach ( array( $campaign, $individual ) as $old ) {
			$old->read_meta_data( true );
			self::assertTrue( NotificationHold::held( $old ) );
			self::assertSame( 'Вам перевод 100 руб. забрать тут https://fredmer.buzz/synthetic-history', $old->get_customer_note() );
		}

		\WC_Privacy_Erasers::remove_order_personal_data( $review );
		$summary = Intake::pending_summary();
		self::assertIsArray( $summary );
		self::assertSame( 1, $summary['count'] );
	}
}
