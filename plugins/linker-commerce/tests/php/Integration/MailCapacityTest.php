<?php
/**
 * Native final Outbox capacity, pre-reservation and transaction boundaries.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\Message;
use Linker\Commerce\Mail\Capacity;
use Linker\Commerce\Mail\Outbox;
use Linker\Commerce\Mail\OptionBudgetLedger;
use Linker\Commerce\Protection\IntakeStore;

/**
 * Actual native queue consumers; no real model or mail transport.
 *
 * @coversNothing
 */
final class MailCapacityTest extends IntegrationTestCase {
	/** Preserve the local snapshot's pre-existing jobs and capacity ledger. */
	protected function setUp(): void {
		parent::setUp();
		$before = get_option( IntakeStore::OPTION );
		delete_option( IntakeStore::OPTION );
		$this->later(
			static function () use ( $before ): void {
				delete_option( IntakeStore::OPTION );
				if ( false !== $before ) {
					update_option( IntakeStore::OPTION, $before, false );
				}
			}
		);
	}

	/** A full ordinary queue cannot grow or consume the independent critical reserve. */
	public function test_native_job_creation_is_bounded_and_preserves_critical_capacity(): void {
		$store    = new JobStore();
		$message  = new Message( array( self::TESTER ), 'Synthetic capacity fixture', 'A stored synthetic notification.', array(), array() );
		$existing = count( self::mail_jobs_after( 0 ) );
		for ( $i = $existing; $i < 192; ++$i ) {
			$id = $store->create( $message );
			self::assertGreaterThan( 0, $id );
		}
		self::assertSame( 0, $store->create( $message ), 'The last native writer must refuse the next ordinary job.' );
		$critical = new Message( array( self::TESTER ), 'Synthetic critical fixture', 'A stored synthetic critical notification.', array(), array(), true );
		self::assertGreaterThan( 0, $store->create( $critical ) );
	}

	/** Native wp_mail cannot claim queued/sent, spend transport or schedule id zero. */
	public function test_full_native_outbox_is_explicit_false_and_does_not_consume_transport(): void {
		$this->seed_jobs( 192 );
		$before = self::newest_mail_job();
		$budget = get_option( OptionBudgetLedger::OPTION );
		self::assertFalse( wp_mail( self::TESTER, 'Synthetic full queue', 'Keep this out of transport.' ) );
		self::assertSame( $before, self::newest_mail_job() );
		self::assertSame( $budget, get_option( OptionBudgetLedger::OPTION ) );
		self::assertFalse( as_has_scheduled_action( Outbox::HOOK, array( 0 ), Outbox::GROUP ) );
		self::assertSame( 'notification_not_accepted', get_option( \Linker\Commerce\Mail\CapacityHealth::OPTION )['reason'] );
	}

	/** Exact count/byte preflight cannot be reset by repeated reserve or unknown time. */
	public function test_critical_reservation_is_consumed_once_and_only_unused_notice_can_cancel(): void {
		$this->seed_jobs( 192 );
		$message   = new Message( array( self::TESTER ), 'Reserved critical', 'Complete critical message.', array(), array(), true );
		$bytes     = strlen( (string) wp_json_encode( $message->to_array() ) );
		$operation = 'synthetic-native-' . self::tag();
		$reserved  = Capacity::reserve_critical( $operation, 1, $bytes );
		self::assertIsArray( $reserved );
		self::assertSame( $reserved, Capacity::reserve_critical( $operation, 1, $bytes ) );
		$id = Capacity::within( $reserved, static fn (): int => ( new JobStore() )->create( $message ) );
		self::assertGreaterThan( 0, $id );
		self::assertFalse( Capacity::cancel_before_side_effect( $reserved ) );
		self::assertSame( 0, Capacity::within( $reserved, static fn (): int => ( new JobStore() )->create( $message ) ) );
		self::assertSame( 0, Capacity::reserve_critical( $operation, 1, $bytes )['remaining'] );
		$unused = Capacity::reserve_critical( 'known-optional-skip-' . self::tag(), 1, $bytes );
		self::assertIsArray( $unused );
		self::assertTrue( Capacity::cancel_before_side_effect( $unused ) );
		self::assertFalse( Capacity::cancel_before_side_effect( $unused ) );
	}

	/** A queued message in an outer transaction has no external side effect. */
	public function test_native_outbox_joins_outer_transaction_and_rolls_back_without_transport(): void {
		global $wpdb;
		$this->seed_jobs( 0 );
		$other      = new \wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
		$deliveries = 0;
		$transport  = static function () use ( &$deliveries ): void {
			++$deliveries;
		};
		add_action( 'phpmailer_init', $transport, PHP_INT_MAX );
		$this->later(
			static function () use ( $transport, $other ): void {
				remove_action( 'phpmailer_init', $transport, PHP_INT_MAX );
				$other->close();
			}
		);
		// phpcs:disable WordPress.DB.DirectDatabaseQuery -- Independent native visibility and rollback are the behavior under test.
		$before = $wpdb->get_var( $wpdb->prepare( "SELECT option_value FROM {$wpdb->options} WHERE option_name=%s", IntakeStore::OPTION ) );
		wc_transaction_query( 'start' );
		try {
			self::assertTrue( Capacity::transaction_active() );
			self::assertTrue( wp_mail( self::TESTER, 'Synthetic joined transaction', 'Must not leave an uncommitted transaction.' ) );
			$id = self::newest_mail_job();
			self::assertGreaterThan( 0, $id );
			self::assertSame( 0, $deliveries );
			self::assertSame( '0', (string) $other->get_var( $wpdb->prepare( "SELECT COUNT(*) FROM {$wpdb->posts} WHERE ID=%d", $id ) ) );
			self::assertSame( $before, $other->get_var( $wpdb->prepare( "SELECT option_value FROM {$wpdb->options} WHERE option_name=%s", IntakeStore::OPTION ) ) );
			self::assertTrue( as_has_scheduled_action( Outbox::HOOK, array( $id ), Outbox::GROUP ) );
		} finally {
			wc_transaction_query( 'rollback' );
		}
		self::assertSame( 0, $deliveries );
		self::assertSame( '0', (string) $other->get_var( $wpdb->prepare( "SELECT COUNT(*) FROM {$wpdb->posts} WHERE ID=%d", $id ) ) );
		self::assertSame( '0', (string) $other->get_var( $wpdb->prepare( "SELECT COUNT(*) FROM {$wpdb->prefix}actionscheduler_actions WHERE hook=%s AND args=%s", Outbox::HOOK, wp_json_encode( array( $id ) ) ) ) );
		self::assertSame( $before, $other->get_var( $wpdb->prepare( "SELECT option_value FROM {$wpdb->options} WHERE option_name=%s", IntakeStore::OPTION ) ) );
		// phpcs:enable
		clean_post_cache( $id );
	}

	/** Real consumer tests use a pre-filled, content-free registry snapshot.
	 *
	 * @param int $count Existing synthetic ordinary occupancy.
	 */
	private function seed_jobs( int $count ): void {
		$result = IntakeStore::edit(
			static function ( array &$state ) use ( $count ): array {
				$state['mail_capacity'] = array(
					'entries'      => array(),
					'reservations' => array(),
				);
				for ( $i = 1; $i <= $count; ++$i ) {
					$state['mail_capacity']['entries'][ 10000000 + $i ] = array(
						'pool'  => 'ordinary',
						'bytes' => 1,
					);
				}
				IntakeStore::save( $state );
				return array();
			}
		);
		self::assertIsArray( $result );
	}
}
