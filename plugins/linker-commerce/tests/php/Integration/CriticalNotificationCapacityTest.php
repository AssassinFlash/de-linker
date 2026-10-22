<?php
/**
 * Native critical producer recovery and atomic held-job promotion.
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
final class CriticalNotificationCapacityTest extends IntegrationTestCase {
	/** Actual metadata writer has reached its chosen native write.
	 *
	 * @var bool
	 */
	private bool $fault_armed = false;
	/** The local original connection was killed exactly once.
	 *
	 * @var bool
	 */
	private bool $fault_killed = false;
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

	/**
	 * Native staff approval cannot leave a changed state without its audit and notice.
	 *
	 * @testWith [false]
	 *           [true]
	 * @param bool $partial Kill after status, before the reason/audit/notification writes.
	 */
	public function test_real_approval_connection_loss_does_not_publish_partial_state_or_notice( bool $partial ): void {
		global $wpdb;
		$this->seed_jobs( 0 );
		$customer = $this->customer();
		$id       = $customer->get_id();
		$approval = new \Linker\Commerce\Registration\Approval();
		$old      = $approval->status( $id );
		$this->as_user( 1 );
		$other  = new \wpdb( (string) constant( 'DB_USER' ), (string) constant( 'DB_PASSWORD' ), (string) constant( 'DB_NAME' ), (string) constant( 'DB_HOST' ) );
		$marker = self::newest_mail_job();
		$target = $partial ? $approval::REASON_META : $approval::STATUS_META;
		$arm    = function ( $pre, $user, $key ) use ( $id, $target ) {
			if ( $id === $user && $target === $key ) {
				$this->fault_armed = true;
			}
			return $pre;
		};
		$kill   = function ( string $sql ) use ( $other ): string {
			global $wpdb;
			if ( $this->fault_armed && ! $this->fault_killed && str_contains( $sql, $wpdb->usermeta ) && ( str_starts_with( $sql, 'INSERT' ) || str_starts_with( $sql, 'UPDATE' ) ) ) {
				$this->fault_killed = true;
				$other->query( 'KILL CONNECTION ' . $wpdb->__get( 'dbh' )->thread_id );
			}
			return $sql;
		};
		add_filter( 'update_user_metadata', $arm, 10, 3 );
		add_filter( 'query', $kill, 999 );
		try {
			$changed = $approval->set( $id, $approval::RESTRICTED, 'Synthetic complete staff reason.' );
		} finally {
			remove_filter( 'update_user_metadata', $arm, 10 );
			remove_filter( 'query', $kill, 999 );
		}
		self::assertTrue( $this->fault_killed );
		self::assertFalse( $changed );
		self::assertSame( $old, $other->get_var( $wpdb->prepare( 'SELECT meta_value FROM %i WHERE user_id=%d AND meta_key=%s', $wpdb->usermeta, $id, $approval::STATUS_META ) ) );
		self::assertTrue( $wpdb->db_connect( false ) );
		wp_cache_delete( $id, 'user_meta' );
		self::assertSame( $old, $approval->status( $id ) );
		self::assertSame( '', $approval->reason( $id ) );
		self::assertSame( $marker, self::newest_mail_job() );
		$other->close();
	}

	/** Issued native Proforma state remains an explicit rebuild source while critical is full. */
	public function test_issued_proforma_notice_stays_pending_then_recovers_one_original_job(): void {
		$this->seed_jobs( 0 );
		$blocked = Capacity::reserve_critical( 'synthetic-proforma-block-' . self::tag(), 64, 1 );
		self::assertIsArray( $blocked );
		$order = new \WC_Order();
		$order->set_billing_email( self::TESTER );
		$order->set_status( \Linker\Commerce\Inquiry\Statuses::PROFORMA );
		$number = 'SYNTHETIC-568-' . self::tag();
		$order->update_meta_data( \Linker\Commerce\Proforma\Issuer::NUMBER_META, $number );
		$order->update_meta_data( \Linker\Commerce\Proforma\Issuer::ISSUED_META, (string) time() );
		$order->save();
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$email = WC()->mailer()->get_emails()[ \Linker\Commerce\Proforma\Emails\ProformaIssuedEmail::class ];
		self::assertInstanceOf( \Linker\Commerce\Proforma\Emails\ProformaIssuedEmail::class, $email );
		$before = self::newest_mail_job();
		$email->trigger( $order->get_id(), $order );
		$order->read_meta_data( true );
		self::assertSame( 'yes', $order->get_meta( $email::PENDING ) );
		self::assertSame( '', $order->get_meta( $email::ACCEPTED ) );
		self::assertSame( $before, self::newest_mail_job() );
		self::assertTrue( Capacity::cancel_before_side_effect( $blocked ) );
		update_option( \Linker\Commerce\Mail\Throttle::OPTION, array_fill( 0, \Linker\Commerce\Mail\Throttle::PER_DAY, time() ), false );
		$email::recover();
		$order->read_meta_data( true );
		$id = (int) $order->get_meta( $email::JOB );
		self::assertGreaterThan( $before, $id );
		self::assertSame( $number, $order->get_meta( $email::ACCEPTED ) );
		self::assertSame( 'no', $order->get_meta( $email::PENDING ) );
		$job = ( new JobStore() )->load( $id );
		self::assertNotNull( $job );
		self::assertTrue( $job['message']->critical );
		$email->trigger( $order->get_id(), $order );
		$email::recover();
		self::assertSame( $id, self::newest_mail_job() );
	}

	/** Full critical capacity never releases an ordinary held job before atomic promotion. */
	public function test_staff_promotion_keeps_same_held_job_when_critical_is_full(): void {
		$this->seed_jobs( 0 );
		$this->as_user( 1 );
		$order = new \WC_Order();
		$order->set_billing_email( self::TESTER );
		$order->save();
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$message = new Message( array( self::TESTER ), 'Synthetic held original', 'Keep the complete original notice.', array( Message::INTERNAL_HEADER ), array() );
		$id      = ( new JobStore() )->create( $message, $order->get_id() );
		self::assertGreaterThan( 0, $id );
		\Linker\Commerce\Inquiry\Assessment\StructuredMeta::update( $order, \Linker\Commerce\Inquiry\Assessment\Queue::META, array( 'notification_job' => $id ) );
		$order->update_meta_data( \Linker\Commerce\Mail\NotificationHold::META, array( 'reason' => 'synthetic-retained-notice' ) );
		$order->save_meta_data();
		update_post_meta( $id, \Linker\Commerce\Mail\NotificationHold::META, array( 'order' => $order->get_id() ) );
		$reference = \Linker\Commerce\Mail\NotificationHold::reference( $order );
		$blocked   = Capacity::reserve_critical( 'synthetic-promotion-block-' . self::tag(), 64, 1 );
		self::assertIsArray( $blocked );
		self::assertInstanceOf( \WP_Error::class, \Linker\Commerce\Mail\NotificationHold::release( $order->get_id(), $reference ) );
		$order->read_meta_data( true );
		self::assertTrue( \Linker\Commerce\Mail\NotificationHold::held( $order ) );
		self::assertFalse( ( new JobStore() )->critical( $id ) );
		self::assertSame( 'ordinary', get_option( IntakeStore::OPTION )['mail_capacity']['entries'][ $id ]['pool'] );
		$original = ( new JobStore() )->load( $id );
		self::assertNotNull( $original );
		self::assertSame( $message->to_array(), $original['message']->to_array() );
		self::assertTrue( Capacity::cancel_before_side_effect( $blocked ) );
		self::assertIsArray( \Linker\Commerce\Mail\NotificationHold::release( $order->get_id(), $reference ) );
		self::assertTrue( ( new JobStore() )->critical( $id ) );
		self::assertSame( 'critical', get_option( IntakeStore::OPTION )['mail_capacity']['entries'][ $id ]['pool'] );
		self::assertSame( $id, self::newest_mail_job() );
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
