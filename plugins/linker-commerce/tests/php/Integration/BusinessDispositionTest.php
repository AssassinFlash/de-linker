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

	/** A different operator whose staff role was revoked cannot undo another employee's audit. */
	public function test_peer_revoked_current_operator_cannot_rollback_a_valid_disposition(): void {
		$order     = $this->source();
		$operation = wp_generate_uuid4();
		$body      = hash( 'sha256', BusinessDisposition::body( $order ) );
		self::assertIsArray( BusinessDisposition::run( $order->get_id(), $body, $operation ) );
		$staff = $this->customer();
		$user  = get_userdata( $staff->get_id() );
		self::assertInstanceOf( \WP_User::class, $user );
		$user->set_role( 'administrator' );
		$this->as_user( $user->ID );
		self::assertTrue( current_user_can( 'manage_woocommerce' ) );
		global $wpdb;
		$peer = new \wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
		try {
			// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- Exact synthetic operator capability row, without clearing this request's primed native cache.
			self::assertSame( 1, $peer->query( $wpdb->prepare( 'UPDATE %i SET meta_value=%s WHERE user_id=%d AND meta_key=%s', $wpdb->usermeta, maybe_serialize( array( 'subscriber' => true ) ), $user->ID, $wpdb->prefix . 'capabilities' ) ) );
			self::assertInstanceOf( \WP_Error::class, BusinessDisposition::run( $order->get_id(), $body, $operation, true ) );
			self::assertTrue( BusinessDisposition::processed( $order ) );
			self::assertFalse( $this->occupied( $order->get_id() ) );
		} finally {
			$peer->close(); }
	}

	/** Current native audit/body corruption, including a restored registry, counts debt again.
	 *
	 * @dataProvider corruption
	 * @param string $field The native source that changes.
	 */
	public function test_capacity_reader_recharges_invalidated_native_disposition( string $field ): void {
		if ( 'peer_staff' === $field ) {
			$staff = $this->customer();
			$user  = get_userdata( $staff->get_id() );
			self::assertInstanceOf( \WP_User::class, $user );
			$user->set_role( 'administrator' );
			$this->as_user( $staff->get_id() );
		}
		$order  = $this->source();
		$result = BusinessDisposition::run( $order->get_id(), hash( 'sha256', BusinessDisposition::body( $order ) ), wp_generate_uuid4() );
		self::assertIsArray( $result );
		self::assertFalse( $this->occupied( $order->get_id() ) );
		if ( str_starts_with( $field, 'peer_' ) ) {
			global $wpdb;
			$peer = new \wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
			self::assertIsArray( get_comment_meta( $result['note'], BusinessDisposition::META, true ) );
			if ( 'peer_body' === $field ) {
				$sql = \Automattic\WooCommerce\Utilities\OrderUtil::custom_orders_table_usage_is_enabled() ? $wpdb->prepare( "UPDATE {$wpdb->prefix}wc_orders SET customer_note='Peer changed source' WHERE id=%d", $order->get_id() ) : $wpdb->prepare( "UPDATE {$wpdb->posts} SET post_excerpt='Peer changed source' WHERE ID=%d", $order->get_id() );
			} elseif ( 'peer_note_meta' === $field ) {
				$sql = $wpdb->prepare( "UPDATE {$wpdb->commentmeta} SET meta_value=%s WHERE comment_id=%d AND meta_key=%s", maybe_serialize( array( 'tampered' => true ) ), $result['note'], BusinessDisposition::META );
			} else {
				$sql = $wpdb->prepare( "UPDATE {$wpdb->usermeta} SET meta_value=%s WHERE user_id=%d AND meta_key=%s", maybe_serialize( array( 'subscriber' => true ) ), get_current_user_id(), $wpdb->prefix . 'capabilities' );
			}
			self::assertIsString( $sql );
			try {
				self::assertSame( 1, $peer->query( $sql ) );
			} finally {
				$peer->close(); }
		}
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
		return array( array( 'body' ), array( 'note' ), array( 'delete_note' ), array( 'marker' ), array( 'peer_body' ), array( 'peer_note_meta' ), array( 'peer_staff' ) );
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

	/** A failed native HPOS discovery cannot become an authoritative empty history.
	 *
	 * @testWith ["ordinary"]
	 * ["audit"]
	 * @param string $kind Native history lookup whose real SQL fails.
	 */
	public function test_failed_native_history_read_preserves_existing_debt( string $kind ): void {
		$order = $this->source();
		if ( 'audit' === $kind ) {
			$result = BusinessDisposition::run( $order->get_id(), hash( 'sha256', BusinessDisposition::body( $order ) ), wp_generate_uuid4() );
			self::assertIsArray( $result );
			$state = get_option( IntakeStore::OPTION );
			unset( $state['business_dispositions'] );
			update_option( IntakeStore::OPTION, $state, false );
		} else {
			delete_option( IntakeStore::OPTION ); }
		$before = get_option( IntakeStore::OPTION );
		$hits   = 0;
		$hpos   = \Automattic\WooCommerce\Utilities\OrderUtil::custom_orders_table_usage_is_enabled();
		$fault  = static function ( string $sql ) use ( $kind, $hpos, &$hits ): string {
			global $wpdb;
			if ( 0 === $hits && str_starts_with( ltrim( $sql ), 'SELECT' ) && str_contains( $sql, $hpos ? $wpdb->prefix . 'wc_orders' : $wpdb->posts ) && ( 'audit' === $kind ? str_contains( $sql, BusinessDisposition::META ) : str_contains( $sql, 'ORDER BY' ) ) ) {
				++$hits;
				return 'SELECT id FROM linker_missing_business_history_fixture';
			}
			return $sql;
		};
		global $wpdb;
		$prior = $wpdb->suppress_errors( true );
		add_filter( 'query', $fault, 998 );
		try {
			$result = IntakeStore::edit(
				static function ( array &$state ): array {
					BusinessCapacity::synchronize( $state );
					IntakeStore::save( $state );
					return array();
				}
			);
		} finally {
			remove_filter( 'query', $fault, 998 );
			$wpdb->suppress_errors( $prior ); }
		self::assertSame( 1, $hits, 'The actual native discovery SQL must hit the fault.' );
		self::assertInstanceOf( \WP_Error::class, $result );
		self::assertSame( $before, get_option( IntakeStore::OPTION ) );
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
