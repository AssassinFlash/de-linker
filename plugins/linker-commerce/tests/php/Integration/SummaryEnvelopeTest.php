<?php
/**
 * Native inquiry summaries, recovery and mail handoff.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

// phpcs:disable WordPress.PHP.DiscouragedPHPFunctions.runtime_configuration_putenv -- Private fixture configuration is restored, never production.

use Linker\Commerce\Contact\Submission;
use Linker\Commerce\Inquiry\Assessment\Queue;
use Linker\Commerce\Inquiry\Assessment\StructuredMeta;
use Linker\Commerce\Inquiry\Sender;
use Linker\Commerce\Inquiry\SummaryEnvelope;
use Linker\Commerce\Protection\BusinessCapacity;
use Linker\Commerce\Protection\IntakeStore;
use WC_Order;

/** Native frozen-summary and side-effect boundaries.
 *
 * @coversNothing
 */
final class SummaryEnvelopeTest extends IntegrationTestCase {
	/** Local native state is restored, not inferred from a previous fixture. */
	protected function setUp(): void {
		parent::setUp();
		foreach ( array( IntakeStore::OPTION, Queue::ENABLED, Queue::HEARTBEAT ) as $name ) {
			$old = get_option( $name );
			$this->later(
				static function () use ( $name, $old ): void {
					false === $old ? delete_option( $name ) : update_option( $name, $old, false );
				}
			);
		}
		delete_option( IntakeStore::OPTION );
		IntakeStore::edit(
			static function ( array &$state ): array {
				$state['business'] = array();
				IntakeStore::save( $state );
				return array();
			}
		);
		$this->use_empty_mail_queue();
		update_option( Queue::ENABLED, 'yes' );
		update_option( Queue::HEARTBEAT, microtime( true ) );
		$old = getenv( 'LINKER_PUBLIC_PROTECTION_MODE' );
		putenv( 'LINKER_PUBLIC_PROTECTION_MODE=enforce' ); // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.runtime_configuration_putenv -- Exclusive fixture, restored below.
		$this->later(
			static function () use ( $old ): void {
				putenv( false === $old ? 'LINKER_PUBLIC_PROTECTION_MODE' : 'LINKER_PUBLIC_PROTECTION_MODE=' . $old );
			}
		); // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.runtime_configuration_putenv
		$this->as_user( 0 );
		wc_load_cart();
		WC()->cart->empty_cart();
	}

	/** Schema drift fails this seam; actual pending metadata is measured three times. */
	public function test_generated_summary_bound_tracks_real_schema_and_native_three_copy_serialization(): void {
		$schema  = new \ReflectionClass( \Linker\Tools\Genie\InquirySummary::class );
		$maximum = SummaryEnvelope::maximum();
		self::assertSame( $schema->getConstant( 'MAX_SUMMARY' ), mb_strlen( $maximum['summary'] ) );
		self::assertSame( $schema->getConstant( 'MAX_NOTE' ), mb_strlen( $maximum['note'] ) );
		self::assertSame( $schema->getConstant( 'MAX_CONDITIONS' ), count( $maximum['conditions'] ) );
		self::assertSame( $schema->getConstant( 'MAX_CONDITION' ), mb_strlen( $maximum['conditions'][0] ) );
		self::assertSame( $schema->getConstant( 'MAX_QUANTITIES' ), count( $maximum['quantities'] ) );
		foreach ( array( PHP_FLOAT_MAX, -PHP_FLOAT_MAX, PHP_FLOAT_MIN, -PHP_FLOAT_MIN, microtime( true ) ) as $value ) {
			self::assertLessThanOrEqual( 24, strlen( (string) wp_json_encode( $value ) ) );
		}
		$order = new WC_Order();
		$order->set_billing_email( self::TESTER );
		$order->set_customer_note( 'Keep this customer sentence.' );
		Queue::prepare( $order );
		$before   = BusinessCapacity::bytes( $order );
		$headroom = SummaryEnvelope::additional_bytes( $order );
		self::assertSame( $before, BusinessCapacity::bytes( $order ), 'Deep preview does not alter the actual draft.' );
		self::assertSame( '', $order->get_meta( Sender::SUMMARY_META ) );
		StructuredMeta::update( $order, Sender::SUMMARY_META, $maximum );
		Queue::refresh_summary( $order );
		self::assertLessThanOrEqual( $before + $headroom, BusinessCapacity::bytes( $order ) );
		self::assertSame( $maximum, Queue::data( $order )['snapshot']['submission']['summary'] );
		self::assertSame( $maximum, $order->get_meta( \Linker\Commerce\Inquiry\Assessment\CustomerEvidence::META )['request']['summary'] );
		self::assertSame( 'Keep this customer sentence.', $order->get_customer_note() );
	}

	/** Existing inquiries occupying the former shared pool do not veto the customer's write. */
	public function test_historical_business_occupancy_leaves_the_native_inquiry_available(): void {
		IntakeStore::edit(
			static function ( array &$state ): array {
				$state['business']['historical'] = array(
					'id'    => 42,
					'pool'  => 'ordinary',
					'bytes' => 40 * MB_IN_BYTES,
				);
				IntakeStore::save( $state );
				return array();
			},
			1
		);
		$result = ( new Sender() )->request( $this->details() );
		self::assertInstanceOf( WC_Order::class, $result );
		$this->later(
			static function () use ( $result ): void {
				$result->delete( true );
			}
		);
		self::assertTrue( $result->has_status( \Linker\Commerce\Inquiry\Statuses::RECEIVED ) );
	}

	/** Collecting a summary and delivering mail do not reserve the shared business pool. */
	public function test_summary_and_actual_mail_transport_never_hold_the_shared_capacity_mutex(): void {
		$calls = 0;
		$this->summary_filter(
			static function () use ( &$calls ): array {
				++$calls;
				self::assert_capacity_mutex_free();
				$state = get_option( IntakeStore::OPTION );
				self::assertSame( array(), $state['business'] );
				return SummaryEnvelope::maximum();
			}
		);
		$order = ( new Sender() )->request( $this->details() );
		self::assertInstanceOf( WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		self::assertSame( 1, $calls );
		self::assertSame( '', $order->get_meta( BusinessCapacity::KEY ) );
		self::assertSame( SummaryEnvelope::maximum(), $order->get_meta( Sender::SUMMARY_META ) );
		$transport = 0;
		$observer  = static function () use ( &$transport ): void {
			++$transport;
			self::assert_capacity_mutex_free();
		};
		add_action( 'phpmailer_init', $observer, PHP_INT_MAX );
		try {
			$customer = $this->customer();
			$user     = get_userdata( $customer->get_id() );
			self::assertInstanceOf( \WP_User::class, $user );
			wp_password_change_notification( $user );
		} finally {
			remove_action( 'phpmailer_init', $observer, PHP_INT_MAX );
		}
		self::assertSame( 1, $transport );
	}

	/** The customer recovers the saved summary and a single receipt after a lost response. */
	public function test_retry_keeps_the_same_order_summary_and_receipt(): void {
		$calls = 0;
		$this->summary_filter(
			static function () use ( &$calls ): array {
				++$calls;
				self::assert_capacity_mutex_free();
				return SummaryEnvelope::maximum();
			}
		);
		$intent = wp_generate_uuid4();
		$owner  = new \Linker\Commerce\Protection\Identity( wp_generate_uuid4(), '' );
		$send   = fn () => \Linker\Commerce\Protection\Business::write_once(
			$intent,
			'inquiry',
			array( 'message' => 'Please review our solution.' ),
			fn () => ( new Sender() )->request( $this->details() ),
			static fn (): bool => true,
			$owner
		);
		$before = self::newest_mail_job();
		$order  = $send();
		self::assertInstanceOf( WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$retry = $send();
		self::assertInstanceOf( WC_Order::class, $retry );
		self::assertSame( $order->get_id(), $retry->get_id() );
		self::assertSame( SummaryEnvelope::maximum(), $retry->get_meta( Sender::SUMMARY_META ) );
		self::assertSame( 1, $calls );
		\Linker\Commerce\Inquiry\Assessment\SendAuthorization::recover( $order->get_id() );
		self::assertSame( array( self::fixed_receipt_job( $order ) ), self::mail_jobs_after( $before ) );
	}

	/** A pre-save unknown summary outcome stays occupied, without free paid redispatch. */
	public function test_interrupted_review_before_first_save_does_not_retry_unknown_provider_work(): void {
		$id       = wp_generate_uuid4();
		$fp       = hash( 'sha256', $id );
		$identity = new \Linker\Commerce\Protection\Identity( str_repeat( 'b', 64 ), '' );
		$calls    = 0;
		$this->summary_filter(
			static function () use ( &$calls ): array {
				++$calls;
				self::assert_capacity_mutex_free();
				throw new \Error( 'synthetic_unknown_paid_outcome' );
			}
		);
		$work = fn () => ( new Sender() )->request( $this->details() );
		for ( $i = 0; $i < 2; ++$i ) {
			$result = \Linker\Commerce\Protection\Intake::run( 'verification', 'inquiry', $id, $fp, $identity, array(), array( new \Linker\Commerce\Protection\Allowance( 'synthetic_review', $id, 2, HOUR_IN_SECONDS ) ), array(), array(), $work );
			self::assertInstanceOf( \WP_Error::class, $result );
			self::assertSame( 'linker_intake_pending', $result->get_error_code() );
		}
		self::assertSame( 1, $calls );
		self::assertCount( 1, get_option( IntakeStore::OPTION )['entries'] );
		self::assertSame( 0, get_option( IntakeStore::OPTION )['entries'][ $id ]['order'] );
	}

	/** A separate DB observer sees no site mutex owner during upstream/transport work. */
	private static function assert_capacity_mutex_free(): void {
		global $wpdb;
		$database = isset( $wpdb->dbname ) ? $wpdb->dbname : (string) constant( 'DB_NAME' );
		$name     = 'linker-assessment-' . md5( $database . '/' . $wpdb->prefix . '/intake-capacity' );
		$other    = new \wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
		// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- Independent observer proves actual connection ownership, not source intent.
		self::assertNull( $other->get_var( $other->prepare( 'SELECT IS_USED_LOCK(%s)', $name ) ) );
		$other->close();
	}

	/** Replace only the paid seam with a deterministic complete native summary.
	 *
	 * @param callable $callback Simulated provider work.
	 */
	private function summary_filter( callable $callback ): void {
		global $wp_filter;
		$old = $wp_filter['linker_genie_inquiry_summary'] ?? null;
		remove_all_filters( 'linker_genie_inquiry_summary' );
		add_filter( 'linker_genie_inquiry_summary', $callback );
		$this->later(
			static function () use ( $old ): void {
				global $wp_filter;
				remove_all_filters( 'linker_genie_inquiry_summary' );
				if ( null !== $old ) {
					$wp_filter['linker_genie_inquiry_summary'] = $old;
				}
			}
		);
	}

	/** Complete ordinary customer input; no native message is truncated. */
	private function details(): Submission {
		$details = Submission::from_post(
			array(
				'name'    => 'Synthetic summary fixture',
				'email'   => self::TESTER,
				'message' => 'Please review our solution.',
				'consent' => '1',
				'lang'    => 'en',
			)
		);
		self::assertInstanceOf( Submission::class, $details );
		return $details;
	}
}
