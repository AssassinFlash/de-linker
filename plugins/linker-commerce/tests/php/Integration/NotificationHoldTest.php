<?php
/**
 * Native callbacks preserve held inquiry notifications without delivery.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Inquiry\Assessment\Queue;
use Linker\Commerce\Inquiry\Assessment\Result;
use Linker\Commerce\Inquiry\Assessment\StructuredMeta;
use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\Message;
use Linker\Commerce\Mail\Outbox;
use Linker\Commerce\Mail\NotificationHold;
use Linker\Commerce\Mail\Throttle;
use WC_Order;

/**
 * Public native retry and lifecycle seams; no model or remote mail is used.
 *
 * @coversNothing
 */
final class NotificationHoldTest extends IntegrationTestCase {
	/** Manual callbacks must honor the incident hold already stored in production. */
	public function test_manual_retry_of_existing_held_job_spends_no_mail_budget(): void {
		[ $order, $id ] = $this->held_inquiry();
		$jobs           = new JobStore();
		$before         = $jobs->load( $id );
		$budget         = get_option( Throttle::OPTION, array() );
		( new Outbox( $jobs, new Throttle() ) )->retry( $id );
		$this->assertSame( $budget, get_option( Throttle::OPTION, array() ) );
		$after = $jobs->load( $id );
		$this->assertNotNull( $after );
		$this->assertSame( $before['message']->to_array(), $after['message']->to_array() );
		$this->assertSame( 0, $after['attempts'] );
		$this->assertSame( 'private', get_post_status( $id ) );
		$this->assertFalse( as_has_scheduled_action( Outbox::HOOK, array( $id ), Outbox::GROUP ) );
	}

	/** Stale callbacks cannot rewrite evidence, spend a model budget or recreate a job. */
	public function test_all_stale_assessment_callbacks_leave_held_inquiry_unchanged(): void {
		[ $order, $id ] = $this->held_inquiry();
		$before         = Queue::data( $order );
		$jobs           = self::mail_jobs_after( 0 );
		$budget         = get_option( Throttle::OPTION, array() );
		$requests       = 0;
		$fetch          = static function ( $pre ) use ( &$requests ) {
			++$requests;
			return $pre;
		};
		add_filter( 'pre_http_request', $fetch );
		try {
			$queue = new Queue();
			$queue->process( $order->get_id() );
			$queue->finish( $order->get_id(), Result::unknown( 'late' ) );
			$queue->expire( $order->get_id() );
			$queue->recover();
		} finally {
			remove_filter( 'pre_http_request', $fetch ); }
		$order->read_meta_data( true );
		$this->assertSame( $before, Queue::data( $order ) );
		$this->assertSame( 'held', $order->get_meta( Queue::PENDING ) );
		$this->assertSame( 0, $requests );
		$this->assertSame( $budget, get_option( Throttle::OPTION, array() ) );
		$this->assertSame( $jobs, self::mail_jobs_after( 0 ) );
		$this->assertFalse( as_has_scheduled_action( Outbox::HOOK, array( $id ), Outbox::GROUP ) );
	}

	/** A repeated staff release keeps one original message and respects the real cap. */
	public function test_staff_release_is_idempotent_and_uses_original_job_with_throttle(): void {
		[ $order, $id ] = $this->held_inquiry();
		$staff          = $this->customer();
		$user           = get_userdata( $staff->get_id() );
		$this->assertInstanceOf( \WP_User::class, $user );
		$user->set_role( 'shop_manager' );
		$this->as_user( $staff->get_id() );
		$jobs      = new JobStore();
		$original  = $jobs->load( $id );
		$evidence  = Queue::data( $order );
		$reference = NotificationHold::reference( $order );
		$budget    = array_fill( 0, Throttle::PER_DAY, time() );
		update_option( Throttle::OPTION, $budget, false );
		$released = NotificationHold::release( $order->get_id(), $reference );
		$this->assertIsArray( $released );
		$this->assertSame( $id, $released['job'] );
		$this->assertSame( $released, NotificationHold::release( $order->get_id(), $reference ) );
		$order->read_meta_data( true );
		$this->assertSame( $evidence, Queue::data( $order ) );
		$this->assertSame( 'yes', $order->get_meta( Queue::PENDING ) );
		$this->assertFalse( NotificationHold::held( $order ) );
		$after = $jobs->load( $id );
		$this->assertNotNull( $after );
		$this->assertSame( $original['message']->to_array(), $after['message']->to_array() );
		$this->assertSame( $original['attempts'], $after['attempts'] );
		$this->assertSame( $budget, get_option( Throttle::OPTION ) );
		$actions = as_get_scheduled_actions(
			array(
				'hook'   => Outbox::HOOK,
				'args'   => array( $id ),
				'group'  => Outbox::GROUP,
				'status' => 'pending',
			)
		);
		$this->assertCount( 1, $actions );
		$action = reset( $actions );
		$this->assertGreaterThanOrEqual( ( new Throttle() )->next_slot( time() ), $action->get_schedule()->get_date()->getTimestamp() );
		$this->assertGreaterThan( 0, $released['event'] );
	}

	/**
	 * Native incident-compatible data.
	 *
	 * @return array{WC_Order, int} Inquiry and retained notification.
	 */
	private function held_inquiry(): array {
		$order = wc_create_order( array( 'status' => 'inquiry-received' ) );
		$this->assertInstanceOf( WC_Order::class, $order );
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$message = new Message( array( self::TESTER ), 'Held synthetic inquiry', 'Original notification body.', array( Message::INTERNAL_HEADER ), array() );
		$jobs    = new JobStore();
		$id      = $jobs->create( $message );
		$hold    = array(
			'incident'        => 'synthetic-incident',
			'at'              => time(),
			'reason'          => 'confirmed_campaign_notification_hold',
			'manifest_sha256' => str_repeat( 'a', 64 ),
			'order'           => $order->get_id(),
			'job'             => $id,
		);
		StructuredMeta::update(
			$order,
			Queue::META,
			array(
				'notification_job' => $id,
				'accepted_at'      => microtime( true ),
				'deadline'         => microtime( true ) + 10,
				'snapshot'         => array(),
				'result'           => Result::unknown( 'deadline' ),
			)
		);
		StructuredMeta::update( $order, '_linker_incident_hold', $hold );
		$order->update_meta_data( Queue::PENDING, 'held' );
		$order->save_meta_data();
		update_post_meta( $id, '_linker_incident_hold', $hold );
		return array( $order, $id );
	}
}
