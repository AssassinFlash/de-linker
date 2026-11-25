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
	/**
	 * The recipient whose delivery history belongs to this case.
	 *
	 * @var string
	 */
	private string $recipient;
	/** Preserve native options and isolate the local provider configuration. */
	protected function setUp(): void {
		parent::setUp();
		$this->recipient = 'receipt-native-' . self::tag() . '@example.test';
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
	/** Persist a complete native inquiry.
	 *
	 * @param string $email Customer destination.
	 */
	private function submit( ?string $email = null ): WC_Order {
		$email ??= $this->recipient;
		$details = Submission::from_post(
			array(
				'name'    => 'Synthetic installer',
				'email'   => $email,
				'company' => 'Fixture EPC',
				'message' => 'Please quote a 10 kWh battery; full original content.',
				'consent' => '1',
			)
		);
		self::assertInstanceOf( Submission::class, $details );
		$order = ( new Sender() )->message( $details );
		self::assertInstanceOf( WC_Order::class, $order );
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
	/** Read the stored permissions for a native inquiry.
	 *
	 * @param int $id Saved inquiry ID.
	 * @phpstan-impure
	 * @return array<string,mixed>
	 */
	private function permissions( int $id ): array {
		$permissions = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $id );
		self::assertIsArray( $permissions );
		return $permissions;
	}

	/** Woo email copies and attachments cannot receive the customer's personal receipt link. */
	public function test_customer_receipt_has_only_its_native_destination_and_no_attachments(): void {
		$copies = static fn ( $headers, $id ) => 'linker_inquiry_received' === $id ? $headers . "Cc: office@example.test\r\nBcc: records@example.test\r\n" : $headers;
		$files  = static fn ( $attachments, $id ) => 'linker_inquiry_received' === $id ? array( __FILE__ ) : $attachments;
		add_filter( 'woocommerce_email_headers', $copies, 20, 2 );
		add_filter( 'woocommerce_email_attachments', $files, 20, 2 );
		try {
			$this->provider( 'normal' );
			$order = $this->submit();
			do_action( Queue::PROCESS, $order->get_id() );
		} finally {
			remove_filter( 'woocommerce_email_headers', $copies, 20 );
			remove_filter( 'woocommerce_email_attachments', $files, 20 );
		}
		$job = ( new \Linker\Commerce\Mail\JobStore() )->load( $this->permissions( $order->get_id() )['jobs']['receipt']['id'] );
		self::assertNotNull( $job );
		self::assertSame( array( $order->get_billing_email() ), $job['message']->to );
		self::assertSame( array(), $job['message']->attachments );
		self::assertStringNotContainsString( 'office@example.test', implode( "\n", $job['message']->headers ) );
		self::assertStringNotContainsString( 'records@example.test', implode( "\n", $job['message']->headers ) );
	}

	/** A confirmed mailbox can receive each of its owner's separate inquiry receipts. */
	public function test_recipient_suppression_applies_only_to_unconfirmed_destinations(): void {
		$customer = $this->customer();
		$email    = $customer->get_email();
		$user     = get_userdata( $customer->get_id() );
		self::assertInstanceOf( \WP_User::class, $user );
		for ( $i = 0; $i < 2; ++$i ) {
			self::assertSame( '', \Linker\Commerce\Protection\ReceiptBudget::reason( $email, wp_generate_uuid4() ) );
		}
		$order = new \WC_Order();
		$order->set_billing_email( $email );
		$order->set_customer_id( $customer->get_id() );
		self::assertSame( 'target_cap', \Linker\Commerce\Inquiry\ReceiptLimit::reason( $order, false ) );
		// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- WooCommerce fires its own password-reset hook after verification.
		do_action( 'woocommerce_customer_reset_password', $user );
		self::assertSame( '', \Linker\Commerce\Inquiry\ReceiptLimit::reason( $order, false ) );
		$order->set_customer_id( 0 );
		self::assertSame( 'target_cap', \Linker\Commerce\Inquiry\ReceiptLimit::reason( $order, false ) );
		$order->set_customer_id( $customer->get_id() );
		$customer->set_email( 'changed-' . $email );
		$customer->save();
		self::assertSame( 'target_cap', \Linker\Commerce\Inquiry\ReceiptLimit::reason( $order, false ) );
		$customer->set_email( $email );
		$customer->save();
		self::assertSame( 'target_cap', \Linker\Commerce\Inquiry\ReceiptLimit::reason( $order, false ) );
	}

	/**
	 * New inquiries get a Woo record immediately. The classifier selects the two recipients.
	 *
	 * @testWith ["normal", ["team","receipt"]]
	 *           ["unknown", ["team"]]
	 *           ["timeout", ["team"]]
	 *           ["malicious", []]
	 * @param string   $decision Classifier response.
	 * @param string[] $purposes Expected authorized recipients.
	 */
	public function test_classification_routes_the_original_inquiry( string $decision, array $purposes ): void {
		$order = $this->submit();
		$id    = $order->get_id();
		self::assertSame( 'Please quote a 10 kWh battery; full original content.', $order->get_customer_note() );
		self::assertSame( array(), $this->permissions( $id )['jobs'] );
		$this->provider( $decision );
		do_action( Queue::PROCESS, $id );
		$jobs = $this->permissions( $id )['jobs'];
		self::assertEqualsCanonicalizing( $purposes, array_keys( $jobs ) );
		if ( in_array( $decision, array( 'unknown', 'timeout' ), true ) ) {
			$job = ( new \Linker\Commerce\Mail\JobStore() )->load( $jobs['team']['id'] );
			self::assertNotNull( $job );
			$team = $job['message'];
			self::assertTrue( $team->is_internal() );
			self::assertStringContainsString( 'Jev: manual review required', $team->body );
			$order->read_meta_data( true );
			$reference = \Linker\Commerce\Mail\NotificationHold::reference( $order );
			do_action( \Linker\Commerce\Mail\Outbox::HOOK, $jobs['team']['id'] );
			$delivered = $this->permissions( $id )['jobs']['team'];
			self::assertNotEmpty( $delivered['delivered_at'] );
			$order->read_meta_data( true );
			wp_set_current_user( 1 );
			$released = \Linker\Commerce\Mail\NotificationHold::release( $id, $reference );
			self::assertIsArray( $released );
			self::assertSame( $released, \Linker\Commerce\Mail\NotificationHold::release( $id, $reference ) );
			$approved = $this->permissions( $id )['jobs'];
			self::assertSame( $delivered, $approved['team'] );
			self::assertArrayHasKey( 'receipt', $approved );
			do_action( \Linker\Commerce\Mail\Outbox::HOOK, $approved['receipt']['id'] );
			self::assertSame( 'sent', \Linker\Commerce\Inquiry\ReceiptLimit::delivery_state( $order ) );
		}
	}

	/**
	 * The Woo editor and its release action agree after a later business transition.
	 *
	 * @testWith ["quotation-issued", true]
	 *           ["completed", true]
	 *           ["cancelled", false]
	 * @param string $status Current Woo order status.
	 * @param bool   $eligible Whether staff may approve the customer receipt.
	 */
	public function test_customer_receipt_review_follows_the_inquiry_status( string $status, bool $eligible ): void {
		$this->provider( 'unknown' );
		$order = $this->submit();
		$id    = $order->get_id();
		do_action( Queue::PROCESS, $id );
		$team = $this->permissions( $id )['jobs']['team']['id'];
		do_action( \Linker\Commerce\Mail\Outbox::HOOK, $team );
		$order->update_status( $status );
		wp_set_current_user( 1 );
		$order = wc_get_order( $id );
		self::assertInstanceOf( WC_Order::class, $order );
		ob_start();
		\Linker\Commerce\Inquiry\Assessment\NotificationHoldView::render( $order );
		$view = (string) ob_get_clean();
		self::assertSame( $eligible, str_contains( $view, 'Approve and send the customer receipt' ) );
		$reference = \Linker\Commerce\Mail\NotificationHold::reference( $order );
		$released  = \Linker\Commerce\Mail\NotificationHold::release( $id, $reference );
		$state     = $this->permissions( $id );
		self::assertSame( $team, $state['jobs']['team']['id'] );
		if ( ! $eligible ) {
			self::assertInstanceOf( \WP_Error::class, $released );
			self::assertArrayNotHasKey( 'receipt', $state['jobs'] );
			return;
		}
		self::assertIsArray( $released );
		self::assertSame( $released, \Linker\Commerce\Mail\NotificationHold::release( $id, $reference ) );
		self::assertArrayHasKey( 'receipt', $state['jobs'] );
		do_action( \Linker\Commerce\Mail\Outbox::HOOK, $state['jobs']['receipt']['id'] );
		\Linker\Commerce\Inquiry\Assessment\SendAuthorization::recover( $id );
		self::assertSame( 'sent', \Linker\Commerce\Inquiry\ReceiptLimit::delivery_state( $order ) );
		self::assertSame( $state['jobs']['receipt']['id'], $this->permissions( $id )['jobs']['receipt']['id'] );
	}

	/**
	 * Staff releases an unnotified historical hold without repeating a queued or delivered notice.
	 *
	 * @testWith ["unnotified"]
	 *           ["queued"]
	 *           ["delivered"]
	 * @param string $previous Earlier internal notification state.
	 */
	public function test_staff_releases_an_unnotified_historical_assessment_once( string $previous ): void {
		$order = $this->submit();
		$id    = $order->get_id();
		if ( 'unnotified' !== $previous ) {
			$this->provider( 'unknown' );
			do_action( Queue::PROCESS, $id );
			if ( 'delivered' === $previous ) {
				do_action( \Linker\Commerce\Mail\Outbox::HOOK, $this->permissions( $id )['jobs']['team']['id'] );
			}
			$order->read_meta_data( true );
			$order->delete_meta_data( \Linker\Commerce\Inquiry\ReceiptLimit::SKIPPED_META );
		}
		$before  = $this->permissions( $id )['jobs'];
		$unknown = \Linker\Commerce\Inquiry\Assessment\SendVerdict::unknown( 'deadline' );
		\Linker\Commerce\Inquiry\Assessment\AuthorizationStore::edit(
			$id,
			static function ( array &$state ) use ( $unknown ): void {
				$state['status']  = 'manual';
				$state['verdict'] = $unknown;
			}
		);
		$data                   = Queue::data( $order );
		$data['result']         = $unknown + array( 'label' => 'uncertain' );
		$data['initial_result'] = $data['result'];
		\Linker\Commerce\Inquiry\Assessment\StructuredMeta::update( $order, Queue::META, $data );
		$order->update_meta_data(
			\Linker\Commerce\Mail\NotificationHold::META,
			array(
				'policy'  => $unknown['rubric'],
				'reason'  => 'assessment_unresolved',
				'purpose' => 'team',
			)
		);
		$order->update_meta_data( Queue::PENDING, 'held' );
		$order->save_meta_data();
		\Linker\Commerce\Inquiry\Assessment\SendAuthorization::recover( $id );
		self::assertSame( $before, $this->permissions( $id )['jobs'] );
		wp_set_current_user( 1 );
		$reference = \Linker\Commerce\Mail\NotificationHold::reference( $order );
		$released  = \Linker\Commerce\Mail\NotificationHold::release( $id, $reference );
		if ( 'unnotified' !== $previous ) {
			self::assertInstanceOf( \WP_Error::class, $released );
			self::assertSame( $before, $this->permissions( $id )['jobs'] );
			return;
		}
		self::assertIsArray( $released );
		$jobs = $this->permissions( $id )['jobs'];
		self::assertSame( array( 'team' ), array_keys( $jobs ) );
		do_action( \Linker\Commerce\Mail\Outbox::HOOK, $jobs['team']['id'] );
		self::assertSame( $released, \Linker\Commerce\Mail\NotificationHold::release( $id, $reference ) );
		$after = $this->permissions( $id )['jobs'];
		self::assertSame( $jobs['team']['id'], $after['team']['id'] );
		self::assertNotEmpty( $after['team']['delivered_at'] );
		self::assertArrayNotHasKey( 'receipt', $after );
	}

	/** A corrected destination between permission checking and charging retires the original receipt. */
	public function test_revoked_receipt_leaves_no_job_or_transport_debit(): void {
		$this->provider( 'normal' );
		$order = $this->submit();
		do_action( Queue::PROCESS, $order->get_id() );
		$job     = $this->permissions( $order->get_id() )['jobs']['receipt']['id'];
		$changed = false;
		$change  = static function ( int $meta_id, int $post_id, string $key ) use ( $order, $job, &$changed ): void {
			if ( $job === $post_id && \Linker\Commerce\Mail\NativeAttempt::META === $key ) {
				$changed = true;
				$order->set_billing_email( 'corrected-receipt@example.test' );
				$order->save();
			}
		};
		add_action( 'added_post_meta', $change, 10, 3 );
		try {
			do_action( \Linker\Commerce\Mail\Outbox::HOOK, $job );
		} finally {
			remove_action( 'added_post_meta', $change, 10 );
		}
		self::assertTrue( $changed );
		self::assertNull( ( new \Linker\Commerce\Mail\JobStore() )->load( $job ) );
		self::assertSame( 0, ( new Throttle() )->used( time() ) );
		self::assertArrayNotHasKey( 'delivered_at', $this->permissions( $order->get_id() )['jobs']['receipt'] );
	}

	/** A persistent recipient-store outage follows Outbox's usual retry schedule to a visible failure. */
	public function test_receipt_store_outage_exhausts_the_original_job(): void {
		$this->provider( 'normal' );
		$order = $this->submit();
		do_action( Queue::PROCESS, $order->get_id() );
		$job = $this->permissions( $order->get_id() )['jobs']['receipt']['id'];
		global $wpdb;
		$previous = $wpdb->suppress_errors( true );
		$refuse   = static function ( string $query ): string {
			return str_starts_with( $query, 'SELECT option_value FROM' ) && str_contains( $query, 'linker_mail_target_v1.' ) ? 'SELECT missing_fixture_recipient_store' : $query;
		};
		$store    = new \Linker\Commerce\Mail\JobStore();
		add_filter( 'query', $refuse );
		try {
			foreach ( \Linker\Commerce\Mail\Outbox::RETRY_DELAYS as $index => $delay ) {
				do_action( \Linker\Commerce\Mail\Outbox::HOOK, $job );
				$loaded = $store->load( $job );
				self::assertNotNull( $loaded );
				self::assertSame( $index + 1, $loaded['attempts'] );
				self::assertSame( 'private', get_post_status( $job ) );
			}
			do_action( \Linker\Commerce\Mail\Outbox::HOOK, $job );
			self::assertSame( \Linker\Commerce\Mail\JobStore::FAILED_STATUS, get_post_status( $job ) );
			self::assertSame( 'Receipt authorization temporarily unavailable.', $store->error( $job ) );
			self::assertArrayNotHasKey( 'delivered_at', $this->permissions( $order->get_id() )['jobs']['receipt'] );
		} finally {
			remove_filter( 'query', $refuse );
			$wpdb->suppress_errors( $previous );
		}
	}

	/** Accept the native submission while Outbox storage is unavailable.
	 *
	 * @param string $email Customer destination.
	 */
	private function submit_before_outbox_recovery( ?string $email = null ): WC_Order {
		$unavailable = static function ( int $id, \WP_Post $post ): void {
			if ( \Linker\Commerce\Mail\JobStore::POST_TYPE === $post->post_type ) {
				throw new \RuntimeException( 'fixture_queue_unavailable' );
			}
		};
		add_action( 'wp_insert_post', $unavailable, 10, 2 );
		try {
			$this->provider( 'normal' );
			$order = $this->submit( $email );
			do_action( Queue::PROCESS, $order->get_id() );
			return $order;
		} finally {
			remove_action( 'wp_insert_post', $unavailable );
		}
	}

	/**
	 * Recover the original pending source once job storage returns, with current terminal states respected.
	 *
	 * @testWith ["received"]
	 *           ["budget_unavailable"]
	 *           ["trash"]
	 *           ["incident"]
	 * @param string $disposition Native outcome before the next recovery.
	 */
	public function test_recover_saved_pending_receipt_only_for_an_active_accepted_order( string $disposition ): void {
		$order = $this->submit_before_outbox_recovery();
		$id    = $order->get_id();
		$state = $this->permissions( $id );
		self::assertSame( array(), $state['jobs'] );
		self::assertSame( 'approved', $state['status'] );
		if ( 'trash' === $disposition ) {
			$order->delete();
		} elseif ( 'incident' === $disposition ) {
			$order->update_meta_data( \Linker\Commerce\Mail\NotificationHold::META, array( 'reason' => 'historical_incident' ) );
			$order->save_meta_data();
		}
		if ( 'budget_unavailable' === $disposition ) {
			global $wpdb;
			self::assertSame( 0, $order->get_customer_id() );
			$attempted   = false;
			$unavailable = static function ( string $sql ) use ( &$attempted ): string {
				if ( str_starts_with( $sql, 'SELECT option_value FROM' ) && str_contains( $sql, 'linker_mail_target_v1.' ) ) {
					$attempted = true;
					return 'SELECT unavailable_native_recipient_store';
				}
				return $sql;
			};
			$previous    = $wpdb->suppress_errors( true );
			add_filter( 'query', $unavailable );
			try {
				\Linker\Commerce\Inquiry\Assessment\SendAuthorization::recover( $id );
			} finally {
				remove_filter( 'query', $unavailable );
				$wpdb->suppress_errors( $previous );
			}
			self::assertTrue( $attempted, 'The unverified address requires its own recipient history.' );
			self::assertSame( array(), $this->permissions( $id )['jobs'] );
			self::assertSame( 'pending', \Linker\Commerce\Inquiry\ReceiptLimit::delivery_state( $order ) );
		}
		\Linker\Commerce\Inquiry\Assessment\SendAuthorization::recover( $id );
		$after = $this->permissions( $id );
		if ( in_array( $disposition, array( 'trash', 'incident' ), true ) ) {
			self::assertSame( $state['jobs'], $after['jobs'] );
			return;
		}
		self::assertSame( array( 'receipt' ), array_keys( $after['jobs'] ) );
		$job = $after['jobs']['receipt']['id'];
		self::assertSame( 'pending', \Linker\Commerce\Inquiry\ReceiptLimit::delivery_state( $order ) );
		do_action( \Linker\Commerce\Mail\Outbox::HOOK, $job );
		self::assertSame( 'sent', \Linker\Commerce\Inquiry\ReceiptLimit::delivery_state( $order ) );
		\Linker\Commerce\Inquiry\Assessment\SendAuthorization::recover( $id );
		$final = $this->permissions( $id );
		self::assertSame( $job, $final['jobs']['receipt']['id'] );
		self::assertNotEmpty( $final['jobs']['receipt']['delivered_at'] );
		self::assertSame( 1, $final['attempts'] );
	}

	/** A granted receipt follows its accepted inquiry into quotation preparation, never cancellation.
	 *
	 * @testWith ["quotation-issued", true]
	 *           ["completed", true]
	 *           ["cancelled", false]
	 * @param string $next Native staff status transition.
	 * @param bool   $deliver Whether this accepted receipt still belongs to the customer.
	 */
	public function test_pending_receipt_follows_a_valid_business_transition( string $next, bool $deliver ): void {
		$this->provider( 'normal' );
		$order = $this->submit();
		do_action( Queue::PROCESS, $order->get_id() );
		$grant = $this->permissions( $order->get_id() )['jobs']['receipt'];
		$order->update_status( $next );
		$moved = wc_get_order( $order->get_id() );
		self::assertInstanceOf( WC_Order::class, $moved );
		self::assertSame( $next, $moved->get_status() );
		do_action( \Linker\Commerce\Mail\Outbox::HOOK, $grant['id'] );
		$after = $this->permissions( $order->get_id() );
		self::assertSame( $deliver, ! empty( $after['jobs']['receipt']['delivered_at'] ) );
		self::assertSame( $grant['id'], $after['jobs']['receipt']['id'] );
		self::assertSame( $deliver ? 'sent' : 'omitted', \Linker\Commerce\Inquiry\ReceiptLimit::delivery_state( $order ) );
	}

	/** Only a matching customer claim preserves a guest's existing fixed receipt.
	 *
	 * @testWith [true]
	 *           [false]
	 * @param bool $claim Whether the ownership change is a verified native claim.
	 */
	public function test_guest_receipt_follows_only_its_own_account_claim( bool $claim ): void {
		$customer = $this->customer();
		$this->as_user( 0 );
		$this->provider( 'normal' );
		$order = $this->submit( $customer->get_email() );
		do_action( Queue::PROCESS, $order->get_id() );
		$receipt = $this->permissions( $order->get_id() )['jobs']['receipt']['id'];
		if ( $claim ) {
			$saved = $_GET; // phpcs:ignore WordPress.Security.NonceVerification.Recommended -- Preserve the WP request; the order key is checked by AccountLink.
			$_GET  = array(
				'linker_inquiry' => $order->get_id(),
				'linker_key'     => $order->get_order_key(),
			);
			try {
				( new \Linker\Commerce\Inquiry\AccountLink() )->claim( $customer->get_id() );
			} finally {
				$_GET = $saved;
			}
		} else {
			$order->set_customer_id( $customer->get_id() );
			$order->save();
		}
		do_action( \Linker\Commerce\Mail\Outbox::HOOK, $receipt );
		$after = $this->permissions( $order->get_id() );
		self::assertSame( $claim, ! empty( $after['jobs']['receipt']['delivered_at'] ) );
		self::assertSame( $receipt, $after['jobs']['receipt']['id'] );
	}

	/**
	 * The accepted source retains its customer acknowledgement while the queue is unavailable.
	 *
	 * @testWith ["claim", true]
	 *           ["quotation-issued", true]
	 *           ["completed", true]
	 *           ["transfer", false]
	 *           ["email", false]
	 *           ["cancelled", false]
	 * @param string $change Native change before the first receipt job.
	 * @param bool   $eligible Whether the original customer may still receive the acknowledgement.
	 */
	public function test_customer_changes_before_first_receipt_handoff( string $change, bool $eligible ): void {
		$customer = $this->customer();
		$this->as_user( 0 );
		$order = $this->submit_before_outbox_recovery( $customer->get_email() );
		$id    = $order->get_id();
		self::assertSame( array(), $this->permissions( $id )['jobs'] );
		if ( 'claim' === $change ) {
			$saved = $_GET; // phpcs:ignore WordPress.Security.NonceVerification.Recommended -- Preserve the request around native order-key validation.
			$_GET  = array(
				'linker_inquiry' => $id,
				'linker_key'     => $order->get_order_key(),
			);
			try {
				( new \Linker\Commerce\Inquiry\AccountLink() )->claim( $customer->get_id() );
			} finally {
				$_GET = $saved;
			}
		} elseif ( 'transfer' === $change ) {
			$order->set_customer_id( $customer->get_id() );
			$order->save();
		} elseif ( 'email' === $change ) {
			$order->set_billing_email( 'changed@example.test' );
			$order->save();
		} else {
			$order->update_status( $change );
		}

		( new Queue() )->recover();
		$jobs = $this->permissions( $id )['jobs'];
		if ( ! $eligible ) {
			self::assertArrayNotHasKey( 'receipt', $jobs );
			return;
		}
		self::assertArrayHasKey( 'receipt', $jobs );
		$receipt = $jobs['receipt']['id'];
		if ( 'claim' === $change ) {
			$claimed = wc_get_order( $id );
			self::assertInstanceOf( WC_Order::class, $claimed );
			$message = ( new \Linker\Commerce\Mail\JobStore() )->load( $receipt );
			self::assertNotNull( $message );
			self::assertStringContainsString( $claimed->get_view_order_url(), html_entity_decode( $message['message']->body ) );
		}
		do_action( \Linker\Commerce\Mail\Outbox::HOOK, $receipt );
		( new Queue() )->recover();
		$final = $this->permissions( $id );
		self::assertSame( $receipt, $final['jobs']['receipt']['id'] );
		self::assertNotEmpty( $final['jobs']['receipt']['delivered_at'] );
	}

	/** A completed Woo order without a received inquiry cannot originate a fixed receipt. */
	public function test_completed_order_without_inquiry_acceptance_does_not_generate_a_receipt(): void {
		$order = new WC_Order();
		$order->set_billing_email( self::TESTER );
		$order->set_payment_method( \Linker\Commerce\Inquiry\InquiryGateway::ID );
		$order->set_status( 'completed' );
		$order->save();
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		\Linker\Commerce\Inquiry\Assessment\SendAuthorization::recover( $order->get_id() );
		$state = $this->permissions( $order->get_id() );
		self::assertSame( 'pending', $state['status'] );
		self::assertArrayNotHasKey( 'receipt', $state['jobs'] );
		self::assertSame( 'omitted', \Linker\Commerce\Inquiry\ReceiptLimit::delivery_state( $order ) );
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
			if ( 'timeout' === $decision ) {
				return new \WP_Error( 'http_request_failed', 'Request timed out.' );
			}
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
	/** Normal content adds one bound team message to the accepted receipt. */
	public function test_normal_content_adds_bound_team_message_to_the_existing_receipt(): void {
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
		$order->read_meta_data( true );
		self::assertSame( 'complete', $order->get_meta( Queue::PENDING ), 'Delivery of all required inquiry jobs completes pending state immediately.' );
		self::assertFalse( as_has_scheduled_action( Queue::EXPIRE, array( $order->get_id() ), \Linker\Commerce\Mail\Outbox::GROUP ) );
		\Linker\Commerce\Inquiry\Assessment\SendAuthorization::recover( $order->get_id() );
		$order->read_meta_data( true );
		self::assertSame( 'complete', $order->get_meta( Queue::PENDING ) );
	}

	/** An orphaned open attempt on an inquiry job terminates on recovery and stops re-enqueuing Outbox::HOOK. */
	public function test_orphaned_inquiry_job_terminates_and_transitions_inquiry_to_manual(): void {
		$this->provider( 'normal' );
		$order = $this->submit();
		\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process( $order->get_id() );
		$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
		self::assertIsArray( $state );
		$team_id = $state['jobs']['team']['id'];
		$loaded  = ( new \Linker\Commerce\Mail\JobStore() )->load( $team_id );
		self::assertNotNull( $loaded );
		update_post_meta(
			$team_id,
			\Linker\Commerce\Mail\NativeAttempt::META,
			array(
				'token'   => wp_generate_uuid4(),
				'message' => hash( 'sha256', (string) wp_json_encode( $loaded['message']->to_array() ) ),
				'state'   => 'open',
				'at'      => time() - \Linker\Commerce\Mail\NativeAttempt::TIMEOUT - 5,
			)
		);
		\Linker\Commerce\Inquiry\Assessment\SendAuthorization::recover( $order->get_id() );
		clean_post_cache( $team_id );
		self::assertSame( \Linker\Commerce\Mail\JobStore::FAILED_STATUS, get_post_status( $team_id ) );
		self::assertFalse( as_has_scheduled_action( \Linker\Commerce\Mail\Outbox::HOOK, array( $team_id ), \Linker\Commerce\Mail\Outbox::GROUP ) );
		$after = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
		self::assertIsArray( $after );
		self::assertSame( 'manual', $after['status'] );
		$order->read_meta_data( true );
		self::assertSame( 'yes', $order->get_meta( Queue::PENDING ) );
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
		self::assertSame( 'normal', $state['status'] );
		self::assertSame( 'deadline', $state['verdict']['reason'] );
		self::assertSame( array( 'team' ), array_keys( $state['jobs'] ) );
		$order->read_meta_data( true );
		self::assertSame( 'jev_review', $order->get_meta( \Linker\Commerce\Inquiry\ReceiptLimit::SKIPPED_META ) );
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

	/** A team handoff that exhausts retries preserves the already granted customer receipt. */
	public function test_exhausted_team_job_creation_preserves_the_issued_customer_receipt(): void {
		$this->provider( 'normal' );
		$order = $this->submit();
		$id    = $order->get_id();
		\Linker\Commerce\Inquiry\Assessment\AuthorizationStore::edit(
			$id,
			static function ( array &$state ): void {
				$state['handoff_attempts'] = count( \Linker\Commerce\Mail\Outbox::RETRY_DELAYS );
			}
		);
		$posts = 0;
		$full  = static function ( int $job_id, \WP_Post $post ) use ( &$posts ): void {
			if ( \Linker\Commerce\Mail\JobStore::POST_TYPE === $post->post_type && ++$posts > 1 ) {
				throw new \RuntimeException( 'fixture_team_job_unavailable' );
			}
		};
		add_action( 'wp_insert_post', $full, 10, 2 );
		try {
			\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process( $id );
		} finally {
			remove_action( 'wp_insert_post', $full );
		}
		$state = $this->permissions( $id );
		self::assertSame( 'manual', $state['status'] );
		self::assertSame( array( 'receipt' ), array_keys( $state['jobs'] ) );
		do_action( \Linker\Commerce\Mail\Outbox::HOOK, $state['jobs']['receipt']['id'] );
		self::assertSame( 'sent', \Linker\Commerce\Inquiry\ReceiptLimit::delivery_state( $order ) );
		( new Queue() )->recover();
		$order->read_meta_data( true );
		self::assertTrue( \Linker\Commerce\Mail\NotificationHold::held( $order ) );
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
	 * ["changed"]
	 * ["tombstone"]
	 * ["tombstone_error"]
	 * @param string $decision Independent conversation classification.
	 */
	public function test_conversation_content_is_persisted_pending_and_cannot_borrow_an_inquiry_permit( string $decision ): void {
		$this->provider( in_array( $decision, array( 'erase', 'changed', 'tombstone', 'tombstone_error' ), true ) ? 'normal' : $decision );
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
		update_post_meta( $id, '_pre_send_fixture_transcript', $messages );
		$source = static fn( $current, int $candidate, array $frozen ): bool=>$candidate === $id && get_post_meta( $id, '_pre_send_fixture_transcript', true ) === $frozen;
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
		if ( 'changed' === $decision ) {
			$peer = new \wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
			$peer->set_prefix( $GLOBALS['wpdb']->prefix );
			$hits   = 0;
			$change = static function ( $pre, $args, $url ) use ( $peer, $id, $messages, &$hits ) {
				if ( str_ends_with( $url, '/inquiries/assess' ) ) {
					global $wpdb;
					$changed               = $messages;
					$changed[0]['content'] = 'Changed native transcript from another connection.';
					$sql                   = $wpdb->prepare( "UPDATE {$wpdb->postmeta} SET meta_value=%s WHERE post_id=%d AND meta_key='_pre_send_fixture_transcript'", maybe_serialize( $changed ), $id );
					self::assertIsString( $sql );
					$hits = $peer->query( $sql );
				}
				return $pre;
			};
			add_filter( 'pre_http_request', $change, 20, 3 );
			try {
				( new \Linker\Commerce\Inquiry\Assessment\ConversationAuthorization() )->process( $job ); } finally {
				remove_filter( 'pre_http_request', $change, 20 );
				$peer->close(); }
				self::assertSame( 1, $hits );
				$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( 'conversation-' . $job );
				self::assertIsArray( $state );
				self::assertSame( 'invalidated', $state['status'] );
				self::assertSame( $budget, get_option( OptionBudgetLedger::OPTION ) );
				return;
		}
		( new \Linker\Commerce\Inquiry\Assessment\ConversationAuthorization() )->process( $job );
		$loaded = ( new \Linker\Commerce\Mail\JobStore() )->load( $job );
		self::assertNotNull( $loaded );
		if ( in_array( $decision, array( 'tombstone', 'tombstone_error' ), true ) ) {
			$key   = 'conversation-erased-' . $id;
			$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( 'conversation-' . $job );
			self::assertIsArray( $state );
			self::assertSame( 'normal', $state['status'] );
			$hits  = 0;
			$fault = static function ( string $sql ) use ( $key, &$hits ): string {
				if ( str_starts_with( ltrim( $sql ), 'SELECT option_value' ) && str_contains( $sql, \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::PREFIX . $key ) ) {
					++$hits;
					return 'SELECT option_value FROM linker_missing_tombstone_fixture';
				}
				return $sql;
			};
			if ( 'tombstone' === $decision ) {
				self::assertTrue(
					\Linker\Commerce\Inquiry\Assessment\AuthorizationStore::edit(
						$key,
						static function ( array &$state ): void {
							$state['status'] = 'erased';
						}
					)
				);
			} else {
				add_filter( 'query', $fault, 998 );
			}
			global $wpdb;
			$previous = $wpdb->suppress_errors( true );
			try {
				self::assertFalse( \Linker\Commerce\Inquiry\Assessment\ConversationAuthorization::allows( $loaded['message'], $job ) );
				do_action( \Linker\Commerce\Mail\Outbox::HOOK, $job );
			} finally {
				remove_filter( 'query', $fault, 998 );
				$wpdb->suppress_errors( $previous );
			}
			if ( 'tombstone_error' === $decision ) {
				self::assertGreaterThan( 0, $hits ); }
			self::assertNotNull( ( new \Linker\Commerce\Mail\JobStore() )->load( $job ) );
			self::assertSame( $budget, get_option( OptionBudgetLedger::OPTION ) );
			return;
		}
		if ( 'erase' === $decision ) {
			$late         = null;
			$late_enqueue = static function ( int $deleted ) use ( $id, $messages, &$late ): void {
				if ( $deleted === $id ) {
					$late = apply_filters(
						\Linker\Commerce\Genie\Module::SEND_FILTER,
						false,
						array(
							'conversation_id' => $id,
							'to'              => self::TESTER,
							'locale'          => 'de',
							'messages'        => $messages,
						)
					);
				}
			};
			add_action( 'before_delete_post', $late_enqueue, 20 );
			try {
				wp_delete_post( $id, true ); } finally {
				remove_action( 'before_delete_post', $late_enqueue, 20 ); }
				self::assertFalse( $late );
				self::assertCount( 1, self::mail_jobs_after( $marker ) );
				\Linker\Commerce\Inquiry\Assessment\SendAuthorization::delivered( $loaded['message'], $job );
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
		self::assertSame( array(), array_keys( $state['jobs'] ) );
		$order->read_meta_data( true );
		$release = \Linker\Commerce\Mail\NotificationHold::release( $order->get_id(), \Linker\Commerce\Mail\NotificationHold::reference( $order ) );
		self::assertIsArray( $release );
		$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
		self::assertIsArray( $state );
		self::assertSame( 'normal', $state['status'] );
		self::assertArrayNotHasKey( 'receipt', $state['jobs'] );
		self::assertArrayHasKey( 'team', $state['jobs'] );
		self::assertTrue( $state['team_only'] );
		self::assertNotEmpty( $state['staff_release'] );
		self::assertSame( 'human_override', $state['producer'] );
		self::assertSame( $decision, $state['verdict']['decision'] );
	}
	/** A team job storage fault preserves the independent receipt. */
	public function test_team_handoff_fault_rolls_back_team_job_and_preserves_customer_receipt(): void {
		$this->provider( 'normal' );
		$order   = $this->submit();
		$marker  = self::newest_mail_job();
		$created = 0;
		$hits    = 0;
		$observe = static function ( int $id, $post ) use ( &$created ): void {
			if ( \Linker\Commerce\Mail\JobStore::POST_TYPE === $post->post_type ) {
				++$created;
			}};
		$fault   = static function ( string $sql ) use ( &$created, &$hits, $order ): string {
			if ( 2 === $created && 0 === $hits && str_starts_with( ltrim( $sql ), 'UPDATE' ) && str_contains( $sql, \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::PREFIX . $order->get_id() ) ) {
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
		self::assertSame( array( $this->permissions( $order->get_id() )['jobs']['receipt']['id'] ), self::mail_jobs_after( $marker ) );
		$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
		self::assertIsArray( $state );
		self::assertSame( 'approved', $state['status'] );
		self::assertSame( 1, $state['handoff_attempts'] );
		$order->read_meta_data( true );
		self::assertSame( '', $order->get_meta( \Linker\Commerce\Inquiry\ReceiptLimit::SKIPPED_META ) );
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
	public function test_team_delivery_failure_preserves_the_customer_receipt_in_either_order( bool $receipt_sent ): void {
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
		self::assertSame( '', $order->get_meta( \Linker\Commerce\Inquiry\ReceiptLimit::SKIPPED_META ) );
		self::assertSame( $receipt_sent ? 'sent' : 'pending', \Linker\Commerce\Inquiry\ReceiptLimit::delivery_state( $order ) );
		$receipt = $state['jobs']['receipt']['id'];
		do_action( \Linker\Commerce\Mail\Outbox::HOOK, $receipt );
		$done = $this->permissions( $order->get_id() );
		self::assertSame( $receipt, $done['jobs']['receipt']['id'] );
		self::assertNotEmpty( $done['jobs']['receipt']['delivered_at'] );
		self::assertSame( 'manual', $done['status'] );
		self::assertArrayNotHasKey( 'delivered_at', $done['jobs']['team'] );
	}
	/** Failure of a customer receipt leaves the normal team job deliverable. */
	public function test_customer_job_failure_preserves_the_authorized_team_notification(): void {
		$this->provider( 'normal' );
		$order = $this->submit();
		\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process( $order->get_id() );
		$before = $this->permissions( $order->get_id() );
		( new \Linker\Commerce\Mail\JobStore() )->delete( $before['jobs']['receipt']['id'] );
		\Linker\Commerce\Inquiry\Assessment\SendAuthorization::recover( $order->get_id() );
		do_action( \Linker\Commerce\Mail\Outbox::HOOK, $before['jobs']['team']['id'] );
		$done = $this->permissions( $order->get_id() );
		self::assertNotEmpty( $done['jobs']['team']['delivered_at'] );
		self::assertSame( $before['jobs']['receipt'], $done['jobs']['receipt'] );
		self::assertSame( 'omitted', \Linker\Commerce\Inquiry\ReceiptLimit::delivery_state( $order ) );
		$order->read_meta_data( true );
		self::assertSame( 'delivery_unconfirmed', $order->get_meta( \Linker\Commerce\Inquiry\ReceiptLimit::SKIPPED_META ) );
		self::assertSame( 'complete', $order->get_meta( Queue::PENDING ) );
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
		$outbox = new \Linker\Commerce\Mail\Outbox( new \Linker\Commerce\Mail\JobStore(), new Throttle( new OptionBudgetLedger() ), new \Linker\Commerce\Mail\TestMode(), $smtp );
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
		$cut        = static function ( int $id, $post ) use ( $peer, $connection, &$hits, &$created, &$posts ): void {
			if ( 0 === $hits && \Linker\Commerce\Mail\JobStore::POST_TYPE === $post->post_type && 2 === ++$posts ) {
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
		$receipt = \Linker\Commerce\Inquiry\ReceiptLimit::reason( $order, false );
		add_action( 'wp_insert_post', $cut, 10, 2 );
		try {
			\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process( $order->get_id() );
		} finally {
			remove_action( 'wp_insert_post', $cut, 10 );
			$peer->close();
		}
		self::assertSame( 1, $hits );
		self::assertSame( array( $this->permissions( $order->get_id() )['jobs']['receipt']['id'] ), self::mail_jobs_after( $marker ) );
		self::assertSame( '0', $wpdb->get_var( $wpdb->prepare( "SELECT COUNT(*) FROM {$wpdb->postmeta} WHERE meta_key='_linker_mail_message' AND post_id=%d", $created ) ), 'No replayed orphan Message meta survives a lost transaction.' );
		self::assertSame( $receipt, \Linker\Commerce\Inquiry\ReceiptLimit::reason( $order, false ) );
		$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
		self::assertIsArray( $state );
		self::assertSame( 'approved', $state['status'] );
		self::assertSame( array( 'receipt' ), array_keys( $state['jobs'] ) );
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
	/** The saved source consumes its recipient allowance once; content assessment adds only the team job.
	 *
	 * @testWith ["normal"]
	 *           ["malicious"]
	 *           ["unknown"]
	 * @param string $decision Typed native classifier result.
	 */
	public function test_content_assessment_does_not_debit_the_public_receipt_budget( string $decision ): void {
		$mode = getenv( 'LINKER_PUBLIC_PROTECTION_MODE' );
		putenv( 'LINKER_PUBLIC_PROTECTION_MODE=enforce' );
		$this->later(
			static function () use ( $mode ): void {
				false === $mode ? putenv( 'LINKER_PUBLIC_PROTECTION_MODE' ) : putenv( 'LINKER_PUBLIC_PROTECTION_MODE=' . $mode );
			}
		);
		self::assertSame( 'enforce', \Linker\Commerce\Protection\Configuration::active_mode() );
		$this->provider( $decision );
		$email    = 'assessment-receipt-' . self::tag() . '@example.test';
		$order    = $this->submit( $email );
		$admitted = $this->permissions( $order->get_id() );
		self::assertSame( array(), array_keys( $admitted['jobs'] ) );
		$charged = \Linker\Commerce\Protection\ReceiptRecipients::privacy( $email, false );
		\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process( $order->get_id() );
		$state = $this->permissions( $order->get_id() );
		self::assertSame( 'normal' === $decision, isset( $state['jobs']['receipt'] ) );
		self::assertSame( $charged, \Linker\Commerce\Protection\ReceiptRecipients::privacy( $email, false ) );
		self::assertSame( 'malicious' !== $decision, isset( $state['jobs']['team'] ) );
		if ( 'normal' !== $decision ) {
			return;
		}
		$receipt = ( new \Linker\Commerce\Mail\JobStore() )->load( $state['jobs']['receipt']['id'] );
		self::assertNotNull( $receipt );
		self::assertStringContainsString( '#' . $order->get_order_number(), $receipt['message']->subject );
		self::assertStringNotContainsString( 'Synthetic installer', $receipt['message']->body );
		self::assertStringNotContainsString( 'full original content', $receipt['message']->body );
		self::assertArrayHasKey( 'team', $state['jobs'] );
	}
	/** Classified junk consumes neither transport nor recipient capacity before a physical send. */
	public function test_junk_before_dispatch_preserves_both_real_recipient_slots(): void {
		$mode = getenv( 'LINKER_PUBLIC_PROTECTION_MODE' );
		putenv( 'LINKER_PUBLIC_PROTECTION_MODE=enforce' );
		$this->later(
			static function () use ( $mode ): void {
				putenv( false === $mode ? 'LINKER_PUBLIC_PROTECTION_MODE' : 'LINKER_PUBLIC_PROTECTION_MODE=' . $mode );
			}
		);
		$ledger = \Linker\Commerce\Protection\Ledger::OPTION;
		$prior  = get_option( $ledger );
		delete_option( $ledger );
		$this->later(
			static function () use ( $ledger, $prior ): void {
				delete_option( $ledger );
				if ( false !== $prior ) {
					update_option( $ledger, $prior, false );
				}
			}
		);
		$this->provider( 'malicious' );
		$junk      = $this->submit();
		$transport = get_option( OptionBudgetLedger::OPTION );
		\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process( $junk->get_id() );
		self::assertSame( array(), $this->permissions( $junk->get_id() )['jobs'] );
		self::assertSame( $transport, get_option( OptionBudgetLedger::OPTION ) );
		self::assertSame( 'omitted', \Linker\Commerce\Inquiry\ReceiptLimit::delivery_state( $junk ) );
		$usage = ( new \Linker\Commerce\Protection\Ledger() )->summary();
		self::assertIsArray( $usage );
		self::assertArrayNotHasKey( 'customer_receipt', $usage['counts'] );
		$this->provider( 'normal' );
		$email  = 'receipt-' . self::tag() . '@example.test';
		$orders = array( $this->submit( $email ), $this->submit( $email ), $this->submit( $email ) );
		foreach ( $orders as $order ) {
			do_action( Queue::PROCESS, $order->get_id() );
		}
		update_option( $ledger, 'unrelated_tools_journal_unavailable', false );
		foreach ( $orders as $index => $order ) {
			$receipt = $this->permissions( $order->get_id() )['jobs']['receipt']['id'];
			do_action( \Linker\Commerce\Mail\Outbox::HOOK, $receipt );
			self::assertSame( $index < 2 ? 'sent' : 'omitted', \Linker\Commerce\Inquiry\ReceiptLimit::delivery_state( $order ) );
		}
		self::assertSame( 'unrelated_tools_journal_unavailable', get_option( $ledger ) );
		self::assertSame( 2, ( new Throttle() )->used( time() ) );
		self::assertSame( 'target_cap', $orders[2]->get_meta( \Linker\Commerce\Inquiry\ReceiptLimit::SKIPPED_META ) );
		$limited = $this->submit( $email );
		do_action( Queue::PROCESS, $limited->get_id() );
		$limited->read_meta_data( true );
		self::assertSame( 'target_cap', $limited->get_meta( \Linker\Commerce\Inquiry\ReceiptLimit::SKIPPED_META ) );
	}

	/** A peer route change invalidates permission at both classification and retry boundaries.
	 *
	 * @testWith ["provider"]
	 * ["retry"]
	 * @param string $phase Native permission boundary after the exact routing option was cached.
	 */
	public function test_peer_route_changes_cannot_use_a_cached_recipient_grant( string $phase ): void {
		$name = \Linker\Commerce\Settings\Options::NOTIFY_BCC;
		$old  = get_option( $name );
		$this->later(
			static function () use ( $name, $old ): void {
				false === $old ? delete_option( $name ) : update_option( $name, $old );
			}
		);
		update_option( $name, 'before-route@example.test' );
		$this->provider( 'normal' );
		$order    = $this->submit();
		$marker   = self::newest_mail_job();
		$budget   = get_option( OptionBudgetLedger::OPTION );
		$peer     = new \wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
		$hits     = 0;
		$change   = static function () use ( $name, $peer, &$hits ): void {
			global $wpdb;
			$sql = $wpdb->prepare( "UPDATE {$wpdb->options} SET option_value=%s WHERE option_name=%s", 'after-route@example.test', $name );
			self::assertIsString( $sql );
			$hits = $peer->query( $sql );
		};
		$callback = static function ( $pre, $args, $url ) use ( $change ) {
			if ( str_ends_with( $url, '/inquiries/assess' ) ) {
				$change();
			} return $pre;
		};
		try {
			if ( 'provider' === $phase ) {
				add_filter( 'pre_http_request', $callback, 20, 3 ); }
			\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process( $order->get_id() );
			$jobs = self::mail_jobs_after( $marker );
			if ( 'retry' === $phase ) {
				self::assertCount( 2, $jobs );
				$jobs = array( $this->permissions( $order->get_id() )['jobs']['team']['id'] );
				get_option( $name );
				$change();
				foreach ( $jobs as $job ) {
					do_action( \Linker\Commerce\Mail\Outbox::HOOK, $job );
					self::assertNotNull( ( new \Linker\Commerce\Mail\JobStore() )->load( $job ) ); }
			} else {
				self::assertSame( array(), $jobs );
				$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
				self::assertIsArray( $state );
				self::assertSame( 'invalidated', $state['status'] );
			}
		} finally {
			remove_filter( 'pre_http_request', $callback, 20 );
			$peer->close();
			wp_cache_delete( $name, 'options' );
			wp_cache_delete( 'alloptions', 'options' );
		}
		self::assertSame( 1, $hits );
		self::assertSame( $budget, get_option( OptionBudgetLedger::OPTION ) );
	}
	/** A second connection cannot change business facts behind the request's native caches.
	 *
	 * @testWith ["note"]
	 *           ["billing"]
	 *           ["quantity"]
	 *           ["account"]
	 *           ["sku"]
	 *           ["sku_cached"]
	 * @param string $field Source field changed during the actual service callback.
	 */
	public function test_peer_source_changes_during_provider_io_cannot_receive_normal_permission( string $field ): void {
		if ( 'sku_cached' === $field ) {
			$name = 'woocommerce_feature_product_instance_caching_enabled';
			$old  = get_option( $name );
			$this->later(
				static function () use ( $name, $old ): void {
					false === $old ? delete_option( $name ) : update_option( $name, $old );
				}
			);
			update_option( $name, 'yes' );
			self::assertTrue( \Automattic\WooCommerce\Utilities\FeaturesUtil::feature_is_enabled( 'product_instance_caching' ) );
			$field = 'sku';
		}
		$this->provider( 'normal' );
		$order    = $this->submit();
		$customer = $this->customer();
		$product  = $this->product( '100' );
		$product->set_sku( 'pre-send-frozen-' . $product->get_id() );
		$product->save();
		$order->set_customer_id( $customer->get_id() );
		$item = $order->add_product( $product, 1 );
		self::assertGreaterThan( 0, $item );
		$order->save();
		// Re-freeze this native fixture before classification, never through a public input.
		$order->delete_meta_data( Queue::META );
		$order->save_meta_data();
		delete_option( \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::PREFIX . $order->get_id() );
		\Linker\Commerce\Inquiry\Assessment\SendAuthorization::defer( $order );
		$frozen = Queue::data( $order );
		self::assertSame( 'pre-send-frozen-' . $product->get_id(), $frozen['snapshot']['products'][0]['sku'] );
		$peer = new \wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
		$peer->set_prefix( $GLOBALS['wpdb']->prefix );
		$hits   = 0;
		$change = static function ( $pre, $args, $url ) use ( $peer, $order, $customer, $product, $item, $field, &$hits ) {
			if ( ! str_ends_with( $url, '/inquiries/assess' ) ) {
				return $pre; }
			global $wpdb;
			$before = null;
			if ( 'quantity' === $field ) {
				$sql = $wpdb->prepare( "UPDATE {$wpdb->prefix}woocommerce_order_itemmeta SET meta_value='9' WHERE order_item_id=%d AND meta_key='_qty'", $item );
			} elseif ( 'account' === $field ) {
				$sql = $wpdb->prepare( "UPDATE {$wpdb->usermeta} SET meta_value='rejected' WHERE user_id=%d AND meta_key=%s", $customer->get_id(), \Linker\Commerce\Registration\Approval::STATUS_META );
			} elseif ( 'sku' === $field ) {
				$before = $wpdb->prepare( "SELECT meta_value FROM {$wpdb->postmeta} WHERE post_id=%d AND meta_key='_sku'", $product->get_id() );
				self::assertIsString( $before );
				self::assertSame( 'pre-send-frozen-' . $product->get_id(), $peer->get_var( $before ) );
				$sql = $wpdb->prepare( "UPDATE {$wpdb->postmeta} SET meta_value='changed-peer-sku' WHERE post_id=%d AND meta_key='_sku'", $product->get_id() );
			} elseif ( \Automattic\WooCommerce\Utilities\OrderUtil::custom_orders_table_usage_is_enabled() ) {
				$sql = 'billing' === $field ? $wpdb->prepare( "UPDATE {$wpdb->prefix}wc_order_addresses SET first_name='Changed peer' WHERE order_id=%d AND address_type='billing'", $order->get_id() ) : $wpdb->prepare( "UPDATE {$wpdb->prefix}wc_orders SET customer_note='Changed peer' WHERE id=%d", $order->get_id() );
			} else {
				$sql = 'billing' === $field ? $wpdb->prepare( "UPDATE {$wpdb->postmeta} SET meta_value='Changed peer' WHERE post_id=%d AND meta_key='_billing_first_name'", $order->get_id() ) : $wpdb->prepare( "UPDATE {$wpdb->posts} SET post_excerpt='Changed peer' WHERE ID=%d", $order->get_id() );
			}
			self::assertIsString( $sql );
			$hits = $peer->query( $sql );
			self::assertSame( 1, $hits );
			if ( 'sku' === $field ) {
				self::assertIsString( $before );
				self::assertSame( 'changed-peer-sku', $peer->get_var( $before ) ); }
			return $pre;
		};
		$marker = self::newest_mail_job();
		add_filter( 'pre_http_request', $change, 20, 3 );
		try {
			\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process( $order->get_id() ); } finally {
			remove_filter( 'pre_http_request', $change, 20 );
			$peer->close(); }
			self::assertSame( 1, $hits );
			$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
			self::assertIsArray( $state );
			self::assertSame( 'invalidated', $state['status'] );
			self::assertSame( array(), self::mail_jobs_after( $marker ) );
	}
	/** An unchanged cached native product is still allowed through the full normal handoff. */
	public function test_unchanged_cached_product_keeps_normal_two_message_permission(): void {
		$name = 'woocommerce_feature_product_instance_caching_enabled';
		$old  = get_option( $name );
		$this->later(
			static function () use ( $name, $old ): void {
				false === $old ? delete_option( $name ) : update_option( $name, $old );
			}
		);
		update_option( $name, 'yes' );
		$this->provider( 'normal' );
		$order   = $this->submit();
		$product = $this->product( '100' );
		$product->set_sku( 'stable-cached-' . $product->get_id() );
		$product->save();
		$order->add_product( $product, 1 );
		$order->save();
		$order->delete_meta_data( Queue::META );
		$order->save_meta_data();
		delete_option( \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::PREFIX . $order->get_id() );
		\Linker\Commerce\Inquiry\Assessment\SendAuthorization::defer( $order );

		\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process( $order->get_id() );
		$jobs = array_column( $this->permissions( $order->get_id() )['jobs'], 'id' );
		self::assertCount( 2, $jobs );
		foreach ( $jobs as $job ) {
			$loaded = ( new \Linker\Commerce\Mail\JobStore() )->load( $job );
			self::assertNotNull( $loaded );
			self::assertTrue( \Linker\Commerce\Inquiry\Assessment\SendAuthorization::allows( $loaded['message'], $job ) );
		}
	}
	/** A handoff published before the erasure mutex is acquired is included in copy removal. */
	public function test_erasure_reads_the_job_set_inside_its_authoritative_record_lock(): void {
		$this->provider( 'normal' );
		$order = $this->submit();
		global $wpdb;
		$lock    = 'linker-send-' . md5( (string) constant( 'DB_NAME' ) . '/' . $wpdb->prefix . '/' . $order->get_id() );
		$hits    = 0;
		$publish = static function ( string $sql ) use ( $lock, $order, &$hits ): string {
			if ( 0 === $hits && str_contains( $sql, 'SELECT GET_LOCK(' ) && str_contains( $sql, $lock ) ) {
				++$hits;
				\Linker\Commerce\Inquiry\Assessment\SendAuthorization::process( $order->get_id() );
			}
			return $sql;
		};

		add_filter( 'query', $publish, 998 );
		try {
			\Linker\Commerce\Inquiry\Assessment\SendAuthorization::erase( $order ); } finally {
			remove_filter( 'query', $publish, 998 ); }
			self::assertSame( 1, $hits );
			$state = \Linker\Commerce\Inquiry\Assessment\AuthorizationStore::read( $order->get_id() );
			self::assertIsArray( $state );
			self::assertSame( 'erased', $state['status'] );
			$jobs = array_column( $state['jobs'], 'id' );
			self::assertCount( 2, $jobs );
			foreach ( $jobs as $job ) {
				wp_cache_delete( $job, 'post_meta' );
				self::assertSame( '', get_post_meta( $job, '_linker_mail_message', true ) );
				self::assertSame( 'erased', get_post_field( 'post_title', $job, 'raw' ) ); }
	}
	/** Golden responses enforce conservative probability mass and escalation eligibility. */
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
		$binding = $escalated['binding'];
		self::assertIsArray( $binding );
		$malicious                            = $escalated;
		$a                                    = $malicious['raw']['primary']['answers'];
		$a['classification']['choice']        = 'malicious';
		$a['classification']['probabilities'] = array(
			'normal'    => 0.02,
			'malicious' => 0.96,
			'unknown'   => 0.02,
		);
		$a['basis']['choice']                 = 'fraud_or_phishing';
		foreach ( $a['basis']['probabilities'] as $key => $number ) {
			$a['basis']['probabilities'][ $key ] = 'fraud_or_phishing' === $key ? 0.96 : 0.0; }
		$malicious['raw']['primary']['answers'] = $a;
		$malicious['binding']                   = $binding;
		self::assertSame( 'unknown', \Linker\Commerce\Inquiry\Assessment\SendVerdict::validate( $malicious, $malicious['binding'] )['decision'] );
	}
}
