<?php
/** Exact staff historical disposition preserves native records, jobs and holds.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Protection\BusinessCapacity;
use Linker\Commerce\Protection\BusinessDisposition;
use Linker\Commerce\Protection\IntakeStore;
use Linker\Commerce\Inquiry\Assessment\Queue;
use Linker\Commerce\Inquiry\Assessment\StructuredMeta;
use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\Message;
use Linker\Commerce\Mail\NotificationHold;

/** Native acceptance contract.
 *
 * @coversNothing
 */
final class BusinessDispositionTest extends IntegrationTestCase {
	/** The instance's original registry and incident jobs are preserved. */
	protected function setUp(): void {
		parent::setUp();
		$before = get_option( IntakeStore::OPTION );
		delete_option( IntakeStore::OPTION );
		$this->later(
			static function () use ( $before ): void {
				delete_option( IntakeStore::OPTION );
				if ( false !== $before ) {
					update_option( IntakeStore::OPTION, $before, false );
				} }
		);
		$this->as_user( 1 );
	}

	/** An exact employee decision frees unhandled capacity only; rollback restores debt. */
	public function test_apply_is_idempotent_and_rollback_restores_occupancy_without_altering_original_job_or_body(): void {
		$order     = $this->source();
		$body      = BusinessDisposition::body( $order );
		$operation = wp_generate_uuid4();
		$job       = ( new JobStore() )->create( new Message( array( self::TESTER ), 'Synthetic held historic job', 'Complete original body.', array( Message::INTERNAL_HEADER ), array() ), $order->get_id() );
		update_post_meta( $job, NotificationHold::META, array( 'order' => $order->get_id() ) );
		$original = ( new JobStore() )->load( $job );
		$result   = BusinessDisposition::run( $order->get_id(), hash( 'sha256', $body ), $operation );
		self::assertIsArray( $result );
		self::assertSame( 'applied', $result['status'] );
		self::assertTrue( BusinessDisposition::processed( $order ) );
		self::assertFalse( $this->occupied( $order->get_id() ) );
		$repeat = BusinessDisposition::run( $order->get_id(), hash( 'sha256', $body ), $operation );
		self::assertIsArray( $repeat );
		self::assertSame( 'already_applied', $repeat['status'] );
		self::assertSame( $body, BusinessDisposition::body( $order ) );
		self::assertTrue( NotificationHold::held( $order ) );
		self::assertSame( Statuses::RECEIVED, $order->get_status() );
		self::assertEquals( $original, ( new JobStore() )->load( $job ), 'Every message field and attempt count is unchanged.' );
		$reversed = BusinessDisposition::run( $order->get_id(), hash( 'sha256', $body ), $operation, true );
		self::assertIsArray( $reversed );
		self::assertSame( 'rolled_back', $reversed['status'] );
		self::assertTrue( $this->occupied( $order->get_id() ) );
		self::assertFalse( BusinessDisposition::processed( $order ) );
		self::assertNull( get_comment( $result['note'] ) );
		self::assertSame( $body, BusinessDisposition::body( $order ) );
		self::assertEquals( $original, ( new JobStore() )->load( $job ), 'Every message field and attempt count is unchanged.' );
	}

	/** Current native audit/body corruption, including a restored registry, counts debt again.
	 *
	 * @dataProvider corruption
	 * @param string $field The native source that changes.
	 */
	public function test_capacity_reader_recharges_invalidated_native_disposition( string $field ): void {
		$order  = $this->source();
		$result = BusinessDisposition::run( $order->get_id(), hash( 'sha256', BusinessDisposition::body( $order ) ), wp_generate_uuid4() );
		self::assertIsArray( $result );
		self::assertFalse( $this->occupied( $order->get_id() ) );
		if ( 'body' === $field ) {
			$order->set_customer_note( 'A real replacement business question.' );
			$order->save();
		} elseif ( 'note' === $field ) {
			wp_update_comment(
				array(
					'comment_ID'      => $result['note'],
					'comment_content' => 'Altered audit.',
				)
			);
		} elseif ( 'delete_note' === $field ) {
			wp_delete_comment( $result['note'], true );
		} elseif ( 'marker' === $field ) {
			$order->read_meta_data( true );
			$marker       = $order->get_meta( BusinessDisposition::META );
			$marker['by'] = 0;
			StructuredMeta::update( $order, BusinessDisposition::META, $marker );
			$order->save_meta_data();
		}
		self::assertFalse( BusinessDisposition::processed( $order ), $field );
		self::assertTrue( $this->occupied( $order->get_id() ) );
	}

	/** Native fixture return shape.
	 *
	 * @return list<array{string}> Native corruption modes.
	 */
	public static function corruption(): array {
		return array( array( 'body' ), array( 'note' ), array( 'delete_note' ), array( 'marker' ) );
	}

	/** A fresh old registry rediscovers a valid ruling, and corruption then recharges it. */
	public function test_old_registry_restore_rediscovers_valid_native_audit_and_recharges_later_change(): void {
		$order  = $this->source();
		$result = BusinessDisposition::run( $order->get_id(), hash( 'sha256', BusinessDisposition::body( $order ) ), wp_generate_uuid4() );
		self::assertIsArray( $result );
		delete_option( IntakeStore::OPTION );
		self::assertFalse( $this->occupied( $order->get_id() ) );
		wp_delete_comment( $result['note'], true );
		self::assertTrue( $this->occupied( $order->get_id() ) );
	}

	/** A changed SHA, non-staff actor and synthetic controlled inquiry cannot be disposed. */
	public function test_forbidden_or_changed_manifest_cannot_release_anything(): void {
		$order = $this->source();
		self::assertInstanceOf( \WP_Error::class, BusinessDisposition::run( $order->get_id(), str_repeat( 'a', 64 ), wp_generate_uuid4() ) );
		self::assertTrue( $this->occupied( $order->get_id() ) );
		self::assertInstanceOf( \WP_Error::class, BusinessDisposition::run( 8037, str_repeat( 'a', 64 ), wp_generate_uuid4() ) );
		$this->as_user( 0 );
		self::assertInstanceOf( \WP_Error::class, BusinessDisposition::run( $order->get_id(), hash( 'sha256', BusinessDisposition::body( $order ) ), wp_generate_uuid4() ) );
		self::assertFalse( BusinessDisposition::processed( $order ) );
	}

	/** The exact incident shape is synthetic; no original customer content is copied. */
	private function source(): \WC_Order {
		$order = new \WC_Order();
		$order->set_customer_note( 'Вам перевод 123 руб. забрать тут https://fredmer.buzz/synthetic-568' );
		$order->update_meta_data( '_linker_inquiry_source', 'contact' );
		$order->set_status( Statuses::RECEIVED );
		StructuredMeta::update( $order, Queue::META, array( 'snapshot' => array( 'submission' => array( 'message' => $order->get_customer_note() ) ) ) );
		$order->update_meta_data( NotificationHold::META, array( 'reason' => 'synthetic-incident' ) );
		$order->save();
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		return $order;
	}

	/** Read via the same final admission initializer, never a test-only predicate.
	 *
	 * @param int $id Native inquiry.
	 */
	private function occupied( int $id ): bool {
		$result = IntakeStore::edit(
			static function ( array &$state ) use ( $id ): array {
				BusinessCapacity::synchronize( $state );
				IntakeStore::save( $state );
				return array( 'occupied' => in_array( $id, array_column( $state['business'], 'order' ), true ) );
			}
		);
		self::assertIsArray( $result );
		return $result['occupied'];
	}
}
