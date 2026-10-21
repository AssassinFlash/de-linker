<?php
/**
 * Private review revisions and privacy on real Woo orders.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Inquiry\Assessment\Admin;
use Linker\Commerce\Inquiry\Assessment\CustomerEvidence;
use Linker\Commerce\Inquiry\Assessment\EvidencePrivacy;
use Linker\Commerce\Inquiry\Assessment\Queue;
use Linker\Commerce\Inquiry\Assessment\Reviews;
use WC_Order;
use WP_Error;

/**
 * Exercises native private notes and both Woo order stores.
 *
 * @coversNothing
 */
final class CustomerReviewTest extends IntegrationTestCase {

	/**
	 * Isolated inquiry without a classifier or notification transition.
	 */
	private function inquiry(): WC_Order {
		foreach ( array( Queue::ENABLED => 'yes' ) as $key => $value ) {
			$previous = get_option( $key );
			update_option( $key, $value );
			$this->later(
				static function () use ( $key, $previous ): void {
					false === $previous ? delete_option( $key ) : update_option( $key, $previous );
				}
			);
		}
		$order = wc_create_order();
		$this->assertInstanceOf( WC_Order::class, $order );
		$order->set_billing_email( self::TESTER );
		$order->set_customer_note( 'Synthetic original request' );
		Queue::prepare( $order );
		$order->save();
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$this->as_user( 1 );
		return $order;
	}

	/**
	 * Submit the same reference that a freshly rendered staff form supplies.
	 *
	 * @param int                  $id Inquiry.
	 * @param int                  $revision Displayed revision.
	 * @param string               $operation Staff action.
	 * @param array<string, mixed> $input Form fields; explicit basis tests staleness.
	 * @return array<string, mixed>|WP_Error Save result.
	 */
	private function save_review( int $id, int $revision, string $operation, array $input ): array|WP_Error {
		$order = wc_get_order( $id );
		$this->assertInstanceOf( WC_Order::class, $order );
		return Reviews::save( $id, $revision, $operation, array_merge( array( 'basis' => Reviews::reference( $order ) ), $input ) );
	}

	/** A late model response cannot silently change the observation being corrected. */
	public function test_review_binds_the_rendered_observation_and_previous_value(): void {
		$order                    = $this->inquiry();
		$basis                    = Reviews::reference( $order );
		$data                     = Queue::data( $order );
		$data['result']['reason'] = 'late_fixture';
		$order->update_meta_data( Queue::META, $data );
		$order->save_meta_data();
		$stale = $this->save_review(
			$order->get_id(),
			0,
			'correct',
			array(
				'basis' => $basis,
				'label' => 'normal',
			)
		);
		$this->assertInstanceOf( WP_Error::class, $stale );
		$this->assertSame( 'review_stale', $stale->get_error_code() );
		$this->assertSame( array(), Reviews::history( $order ) );
		$this->assertIsArray( $this->save_review( $order->get_id(), 0, 'correct', array( 'label' => 'normal' ) ) );
		$reviewed = wc_get_order( $order->get_id() );
		$this->assertInstanceOf( WC_Order::class, $reviewed );
		$events = Reviews::history( $reviewed );
		$this->assertSame( $data['result'], $events[0]['basis']['observation'] );
		$this->assertSame( Reviews::reference( $order ), $events[0]['basis']['reference'] );
		$this->assertSame( 'uncertain', $events[0]['previous']['label'] );
		$this->assertIsArray( $this->save_review( $order->get_id(), 1, 'withdraw', array() ) );
		$withdrawn = wc_get_order( $order->get_id() );
		$this->assertInstanceOf( WC_Order::class, $withdrawn );
		$events = Reviews::history( $withdrawn );
		$this->assertSame( 'normal', $events[1]['previous']['label'] );
		$this->assertSame( $events[0]['id'], $events[1]['previous']['event'] );
	}

	/**
	 * Corrections, sources and withdrawal never alter raw evidence or send mail.
	 */
	public function test_review_history_and_native_privacy(): void {
		$order    = $this->inquiry();
		$original = Queue::data( $order );
		$marker   = self::newest_mail_job();
		$note     = 'Reviewed "synthetic" claim C:\\docs\\evidence';
		$state    = $this->save_review(
			$order->get_id(),
			0,
			'correct',
			array(
				'label' => 'normal',
				'note'  => $note,
			)
		);
		$this->assertIsArray( $state );
		$this->assertSame( 1, $state['revision'] );
		$stale = $this->save_review(
			$order->get_id(),
			0,
			'correct',
			array(
				'label' => 'suspected_spam',
				'note'  => 'Stale edit',
			)
		);
		$this->assertInstanceOf( WP_Error::class, $stale );
		$this->assertSame( 'review_stale', $stale->get_error_code() );
		$state = $this->save_review(
			$order->get_id(),
			1,
			'evidence',
			array(
				'note'        => 'Synthetic register excerpt',
				'source'      => 'official_registry',
				'url'         => 'https://register.example.invalid/record/123',
				'observed_at' => 1600000000,
			)
		);
		$this->assertIsArray( $state );
		$this->assertSame( 2, $state['revision'] );
		$order->read_meta_data( true );
		$this->assertSame( 'normal', $order->get_meta( Admin::OVERRIDE )['label'], 'Adding evidence cannot change the correction.' );
		$state = $this->save_review( $order->get_id(), 2, 'withdraw', array( 'note' => 'Correction no longer needed' ) );
		$this->assertIsArray( $state );
		$this->assertSame( 3, $state['revision'] );
		$order->read_meta_data( true );
		$this->assertSame( '', $order->get_meta( Admin::OVERRIDE ) );
		$events = Reviews::history( $order );
		$this->assertSame( array( 'correct', 'evidence', 'withdraw' ), array_column( $events, 'operation' ) );
		$this->assertSame( $note, $events[0]['note'], 'Quotes and backslashes survive native metadata slashing.' );
		$this->assertSame( 1600000000, $events[1]['observed_at'] );
		foreach ( $events as $event ) {
			$record = wc_get_order_note( $event['id'] );
			$this->assertInstanceOf( \stdClass::class, $record );
			$this->assertFalse( $record->customer_note );
			$this->assertStringNotContainsString( 'Synthetic register excerpt', $record->content );
		}
		$this->assertSame( $original, Queue::data( $order ) );
		$this->assertSame( 'pending', $order->get_status() );
		$this->assertSame( $marker, self::newest_mail_job() );
		$export = \WC_Privacy_Exporters::order_data_exporter( self::TESTER, 1 );
		$items  = array_column( $export['data'], null, 'item_id' );
		$this->assertArrayHasKey( 'order-' . $order->get_id(), $items );
		$this->assertStringContainsString( 'Synthetic register excerpt', (string) wp_json_encode( $items[ 'order-' . $order->get_id() ] ) );
		\WC_Privacy_Erasers::remove_order_personal_data( $order );
		$order->read_meta_data( true );
		$this->assertSame( '', $order->get_meta( CustomerEvidence::META ) );
		$this->assertSame( '', $order->get_meta( Reviews::META ) );
		$this->assertSame( array(), Reviews::history( $order ) );
		$this->assertSame( array(), ( new EvidencePrivacy() )->export( array(), $order ) );
		$erased = $this->save_review( $order->get_id(), 0, 'correct', array( 'label' => 'normal' ) );
		$this->assertInstanceOf( WP_Error::class, $erased );
		$this->assertSame( 'invalid_inquiry', $erased->get_error_code() );
	}

	/** Import preserves the old correction's actual actor and timestamp. */
	public function test_legacy_correction_starts_history_without_invention(): void {
		$order  = $this->inquiry();
		$legacy = array(
			'label' => 'suspected_spam',
			'note'  => 'Earlier synthetic note',
			'user'  => 77,
			'at'    => 1600000000,
		);
		$order->update_meta_data( Admin::OVERRIDE, $legacy );
		$order->save_meta_data();
		$this->assertIsArray( $this->save_review( $order->get_id(), 0, 'withdraw', array( 'note' => 'Reviewed again' ) ) );
		$events = Reviews::history( $order );
		$this->assertCount( 2, $events );
		$this->assertSame( 'legacy', $events[0]['operation'] );
		$this->assertSame( $legacy, array_intersect_key( $events[0], $legacy ) );
		$this->assertSame( 0, $events[0]['revision'] );
	}

	/** A failed metadata write must roll back the note and revision together. */
	public function test_partial_event_write_rolls_back_and_retries(): void {
		$order = $this->inquiry();
		$count = count( wc_get_order_notes( array( 'order_id' => $order->get_id() ) ) );
		$block = static fn ( $value, $id, $key ) => Reviews::EVENT === $key ? false : $value;
		add_filter( 'add_comment_metadata', $block, 10, 3 );
		try {
			$result = $this->save_review(
				$order->get_id(),
				0,
				'correct',
				array(
					'label' => 'normal',
					'note'  => 'Must roll back',
				)
			);
		} finally {
			remove_filter( 'add_comment_metadata', $block );
		}
		$this->assertInstanceOf( WP_Error::class, $result );
		$this->assertSame( 'review_write_failed', $result->get_error_code() );
		$order->read_meta_data( true );
		$this->assertSame( 0, Reviews::state( $order )['revision'] );
		$this->assertSame( '', $order->get_meta( Admin::OVERRIDE ) );
		$this->assertCount( $count, wc_get_order_notes( array( 'order_id' => $order->get_id() ) ) );
		$this->assertIsArray( $this->save_review( $order->get_id(), 0, 'correct', array( 'label' => 'normal' ) ) );
		$this->assertCount( 1, Reviews::history( $order ) );
	}

	/** Permission and source validation fail before creating any private note. */
	public function test_staff_capability_and_source_validation(): void {
		$order = $this->inquiry();
		$this->as_user( 0 );
		$result = $this->save_review( $order->get_id(), 0, 'correct', array( 'label' => 'normal' ) );
		$this->assertInstanceOf( WP_Error::class, $result );
		$this->assertSame( 'forbidden', $result->get_error_code() );
		$this->as_user( 1 );
		$result = $this->save_review( $order->get_id(), 0, 'evidence', array( 'note' => 'No provenance' ) );
		$this->assertInstanceOf( WP_Error::class, $result );
		$this->assertSame( 'invalid_evidence', $result->get_error_code() );
		$this->assertSame( array(), Reviews::history( $order ) );
	}

	/** Repeated corrections preserve both notes, including native-store updates. */
	public function test_second_correction_preserves_the_first_and_original_model(): void {
		$order = $this->inquiry();
		$raw   = Queue::data( $order );
		$this->assertIsArray(
			$this->save_review(
				$order->get_id(),
				0,
				'correct',
				array(
					'label' => 'normal',
					'note'  => 'First \\company\\file',
				)
			)
		);
		$this->assertIsArray(
			$this->save_review(
				$order->get_id(),
				1,
				'correct',
				array(
					'label' => 'uncertain',
					'note'  => 'Second \\review\\file',
				)
			)
		);
		$order->read_meta_data( true );
		$this->assertSame( 'Second \\review\\file', $order->get_meta( Admin::OVERRIDE )['note'] );
		$this->assertSame( array( 'First \\company\\file', 'Second \\review\\file' ), array_column( Reviews::history( $order ), 'note' ) );
		$this->assertSame( $raw, Queue::data( $order ) );
	}

	/** A record-specific native nonce is required before any review mutation. */
	public function test_admin_endpoint_rejects_an_invalid_nonce(): void {
		$order    = $this->inquiry();
		$previous = $_POST; // phpcs:ignore WordPress.Security.NonceVerification.Missing -- Preserve the runner input before exercising native nonce rejection.
		$_POST    = array(
			'inquiry'   => (string) $order->get_id(),
			'revision'  => '0',
			'operation' => 'correct',
			'label'     => 'normal',
			'_wpnonce'  => 'invalid-test-nonce',
		);
		$status   = 0;
		$handler  = static function () use ( &$status ) {
			return static function ( $message, $title, $args ) use ( &$status ): void {
				$status = (int) ( $args['response'] ?? 0 );
				throw new \RuntimeException( 'native_nonce_rejected' );
			};
		};
		add_filter( 'wp_die_handler', $handler );
		try {
			( new Admin() )->correct();
			$this->fail( 'Invalid nonce reached the write path.' );
		} catch ( \RuntimeException $error ) {
			$this->assertSame( 'native_nonce_rejected', $error->getMessage() );
		} finally {
			remove_filter( 'wp_die_handler', $handler );
			$_POST = $previous;
		}
		$this->assertSame( 403, $status );
		$this->assertSame( array(), Reviews::history( $order ) );
	}

	/** A second real DB connection prevents lost writes and false erasure success. */
	public function test_busy_review_and_erasure_are_explicitly_retryable(): void {
		$order = $this->inquiry();
		global $wpdb;
		$other    = new \wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
		$database = (string) constant( 'DB_NAME' );
		$name     = 'linker-assessment-' . md5( $database . '/' . $wpdb->prefix . '/review-' . $order->get_id() );
		// phpcs:disable WordPress.DB.DirectDatabaseQuery -- A real second connection owns the server-wide mutex during this race fixture.
		$this->assertSame( '1', (string) $other->get_var( $other->prepare( 'SELECT GET_LOCK(%s, 0)', $name ) ) );
		try {
			$result = $this->save_review( $order->get_id(), 0, 'correct', array( 'label' => 'normal' ) );
			$this->assertInstanceOf( WP_Error::class, $result );
			$this->assertSame( 'review_busy', $result->get_error_code() );
			try {
				( new EvidencePrivacy() )->erase( $order );
				$this->fail( 'Busy erasure must not report success.' );
			} catch ( \RuntimeException $error ) {
				$this->assertSame( 'customer_evidence_review_busy', $error->getMessage() );
			}
		} finally {
			$other->get_var( $other->prepare( 'SELECT RELEASE_LOCK(%s)', $name ) );
			$other->close();
		}
		// phpcs:enable
		$order->read_meta_data( true );
		$this->assertIsArray( $order->get_meta( CustomerEvidence::META ) );
		$this->assertSame( 0, Reviews::state( $order )['revision'] );
		$this->assertIsArray( $this->save_review( $order->get_id(), 0, 'correct', array( 'label' => 'normal' ) ) );
		$this->assertCount( 1, Reviews::history( $order ) );
	}
}
