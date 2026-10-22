<?php
/**
 * Durable observation and one logical team notification per inquiry.
 *
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry\Assessment;

use Linker\Commerce\Inquiry\Emails\NewInquiryEmail;
use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\Outbox;
use Linker\Commerce\Mail\NotificationHold;
use WC_Order;

/** Woo stores evidence; Action Scheduler runs it; Outbox owns delivery. */
final class Queue {
	public const ENABLED   = 'linker_inquiry_assessment_enabled';
	public const META      = '_linker_inquiry_assessment';
	public const PENDING   = '_linker_inquiry_assessment_pending';
	public const PROCESS   = 'linker_inquiry_assessment_process';
	public const EXPIRE    = 'linker_inquiry_assessment_expire';
	public const FINISH    = 'linker_inquiry_assessment_finish';
	public const HEARTBEAT = 'linker_inquiry_assessment_recovery';
	// Owner confirmed 2026-10-22, issue 511: queue delay consumes this budget.
	public const WAIT_SECONDS = 10;
	// Recovery is a real once-per-minute CLI cron, not traffic-driven WP-Cron.
	// Two missed minute ticks make readiness fail open for new submissions.
	public const RECOVERY_STALE = 120;

	/** Feature stays dormant until the deployment runbook enables it. */
	public static function enabled(): bool {
		return 'yes' === get_option( self::ENABLED, 'no' );
	}

	/**
	 * Add an immutable snapshot to the inquiry's ordinary save; no network I/O.
	 *
	 *
 * @param WC_Order             $order Inquiry before received status.
	 *
 * @param array<string, mixed> $context Trusted current source link.
	 */
	public static function prepare( WC_Order $order, array $context = array() ): void {
		if ( $order->get_meta( Reviews::ERASED ) || is_array( $order->get_meta( self::META ) ) ) {
			return;
		}
		$now      = microtime( true );
		$snapshot = Snapshot::make( $order, $context );
		// Staff decision provenance stays local; the provider snapshot is unchanged.
		try {
			StructuredMeta::update( $order, CustomerEvidence::META, CustomerEvidence::capture( $order, $snapshot, $now ) );
		} catch ( \Throwable $error ) {
			// A local advisory record cannot prevent the normal inquiry path.
			$order->update_meta_data(
				CustomerEvidence::META,
				array(
					'captured_at' => $now,
					'status'      => 'unavailable',
				)
			);
		}
		StructuredMeta::update(
			$order,
			self::META,
			array(
				'accepted_at'      => $now,
				'deadline'         => $now + self::WAIT_SECONDS,
				'snapshot'         => $snapshot,
				'result'           => Result::unknown( 'pending' ),
				'notification_job' => 0,
			)
		);
		$order->update_meta_data( self::PENDING, 'yes' );
	}

	/**
	 * Intercept only the team listener; customer receipts/status stay independent.
	 *
	 *
 * @param WC_Order $order Received inquiry.
	 */
	public static function defer( WC_Order $order ): bool {
		return SendAuthorization::defer( $order );
	}

	/**
	 * Fresh data, including after another worker committed a deadline result.
	 *
	 *
 * @param WC_Order $order Record.
	 *
 * @return array<string, mixed>
	 */
	public static function data( WC_Order $order ): array {
		$value = $order->get_meta( self::META );
		return is_array( $value ) ? $value : array();
	}

	/**
	 * Background only. A second worker cannot spend twice on the same job.
	 *
	 *
 * @param int $id Inquiry id.
	 */
	public function process( int $id ): void { SendAuthorization::process( $id ); }

	/** Old delayed observation results cannot grant sending permission.
	 *
 * @param int $id Inquiry.
	 *
 * @param array<string,mixed> $result Historical observation, not a permit.
	 */
	public function finish( int $id, array $result ): void { SendAuthorization::recover( $id ); }

	/**
 * @param int $id Inquiry. */
	public function expire( int $id ): void { SendAuthorization::recover( $id ); }

	/** Native independent minute heartbeat; no visitor or synchronous provider is needed. */
	public function recover(): int {
		update_option( self::HEARTBEAT, microtime( true ), false );
		$orders = wc_get_orders( array( 'limit' => -1, 'meta_query' => array( array( 'key' => self::PENDING, 'value' => 'yes' ) ) ) );
		$count = 0;
		foreach ( is_array( $orders ) ? $orders : array() as $order ) {
			SendAuthorization::recover( $order->get_id() );
			++$count;
		}
		return $count;
	}

	/** Register background handlers without doing any work in a submit. */
	public function register(): void {
		( new RecoverySchedule() )->register();
		( new ConversationAuthorization() )->register();
		if ( class_exists( \WP_Async_Request::class ) ) {
			new AsyncRunner();
		}
		add_action( self::PROCESS, array( $this, 'process' ) );
		add_action( self::EXPIRE, array( $this, 'expire' ) );
		add_action( self::FINISH, array( $this, 'finish' ), 10, 2 );
		( new Admin() )->register();
		( new EvidencePrivacy() )->register();
		add_action( 'woocommerce_privacy_before_remove_order_personal_data', array( SendAuthorization::class, 'erase' ), 9 );
	}
}
