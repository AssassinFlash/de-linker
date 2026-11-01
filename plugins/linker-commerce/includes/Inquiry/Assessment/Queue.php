<?php
/**
 * Durable observation and one logical team notification per inquiry.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry\Assessment;

use Automattic\WooCommerce\Utilities\OrderUtil;
use Linker\Commerce\Protection\BusinessCapacity;
use Linker\Commerce\Inquiry\Emails\NewInquiryEmail;
use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\Outbox;
use Linker\Commerce\Mail\NotificationHold;
use WC_Order;

/** Woo stores evidence; Action Scheduler runs it; Outbox owns delivery. */
final class Queue {
	public const ENABLED         = 'linker_inquiry_assessment_enabled';
	public const META            = '_linker_inquiry_assessment';
	public const PENDING         = '_linker_inquiry_assessment_pending';
	public const PROCESS         = 'linker_inquiry_assessment_process';
	public const EXPIRE          = 'linker_inquiry_assessment_expire';
	public const FINISH          = 'linker_inquiry_assessment_finish';
	public const HEARTBEAT       = 'linker_inquiry_assessment_recovery';
	public const RECOVERY_OFFSET = 'linker_inquiry_assessment_recovery_offset';
	// Owner policy 2026-10-23: each claimed model attempt gets ten seconds; queue delay is excluded.
	public const WAIT_SECONDS = 10;
	// Recovery is a real once-per-minute CLI cron, not traffic-driven WP-Cron.
	// Two missed minute ticks make readiness stale; sending still requires a normal permit.
	public const RECOVERY_STALE = 120;

	/** Legacy observation display switch; it never bypasses mandatory sending authorization. */
	public static function enabled(): bool {
		return 'yes' === get_option( self::ENABLED, 'no' );
	}

	/**
	 * Add an immutable snapshot to the inquiry's ordinary save; no network I/O.
	 *
	 * @param WC_Order             $order Inquiry before received status.
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
				// Existing one-use wake capability expiry; the worker claims its own model deadline.
				'deadline'         => $now + self::WAIT_SECONDS,
				'snapshot'         => $snapshot,
				'result'           => Result::unknown( 'pending' ),
				'notification_job' => 0,
			)
		);
		$order->update_meta_data( self::PENDING, 'yes' );
	}

	/**
	 * Before first save, replace only the generated summary in the frozen evidence.
	 * Customer fields, history and account evidence never change during model work.
	 *
	 * @param WC_Order $order Unsaved prepared inquiry.
	 * @param bool     $clock Whether to start the native assessment wait now.
	 */
	public static function refresh_summary( WC_Order $order, bool $clock = true ): void {
		if ( $order->get_id() > 0 ) {
			return;
		}
		$legacy  = $order->get_data_store() instanceof \WC_Data_Store && is_a( $order->get_data_store()->get_current_class_name(), \WC_Order_Data_Store_CPT::class, true );
		$summary = $order->get_meta( \Linker\Commerce\Inquiry\Sender::SUMMARY_META );
		$summary = $legacy && is_array( $summary ) ? wp_unslash( $summary ) : $summary;
		$now     = microtime( true );
		foreach ( array( self::META, CustomerEvidence::META ) as $key ) {
			$data = $order->get_meta( $key );
			if ( ! is_array( $data ) ) {
				continue;
			}
			$data = $legacy ? wp_unslash( $data ) : $data;
			if ( self::META === $key ) {
				$data['snapshot']['submission']['summary'] = $summary;
				if ( $clock ) {
					$data['accepted_at'] = $now;
					$data['deadline']    = $now + self::WAIT_SECONDS;
				}
			} else {
				$data['request']['summary'] = $summary;
				if ( $clock ) {
					$data['captured_at'] = $now;
				}
			}
			StructuredMeta::update( $order, $key, $data );
		}
	}

	/** Persist deferred content mail without delaying the native submission.
	 *
	 * @param WC_Order $order Received inquiry.
	 */
	public static function defer( WC_Order $order ): bool {
		return SendAuthorization::defer( $order );
	}

	/**
	 * Fresh data, including after another worker committed a deadline result.
	 *
	 * @param WC_Order $order Record.
	 * @return array<string, mixed>
	 */
	public static function data( WC_Order $order ): array {
		$value = $order->get_meta( self::META );
		return is_array( $value ) ? $value : array();
	}

	/**
	 * Background only. A second worker cannot spend twice on the same job.
	 *
	 * @param int $id Inquiry id.
	 */
	public function process( int $id ): void {
		SendAuthorization::process( $id ); }

	/** Old delayed observation results cannot grant sending permission.
	 *
	 * @param int                 $id Inquiry.
	 * @param array<string,mixed> $result Historical observation, not a permit.
	 */
	public function finish( int $id, array $result ): void { // phpcs:ignore Generic.CodeAnalysis.UnusedFunctionParameter.FoundAfterLastUsed -- Historical AS callback signature; old observations never grant permits.
		SendAuthorization::recover( $id ); }

	/** Inquiry.
	 *
	 * @param int $id Inquiry.
	 */
	public function expire( int $id ): void {
		SendAuthorization::recover( $id ); }

	/** Native independent minute recovery; heartbeat records a completed bounded pass.
	 *
	 * @throws \Throwable First consumer failure, after the rest of the page is attempted.
	 */
	public function recover(): int {
		// Cron loads WC email base classes lazily, before invoking native rebuilders.
		WC()->mailer();
		\Linker\Commerce\Proforma\Emails\ProformaIssuedEmail::recover();
		\Linker\Commerce\Registration\VatNotice::recover();
		// Reuse the approved complete native intake envelope, not a new quota.
		$limit  = array_sum( array_column( BusinessCapacity::LIMITS, 'count' ) );
		$offset = max( 0, (int) get_option( self::RECOVERY_OFFSET, 0 ) );
		$ids    = self::pending_ids( $offset, $limit );
		if ( array() === $ids && $offset > 0 ) {
			// Earlier completions/deletions can move the remaining page left.
			$offset = 0;
			$ids    = self::pending_ids( $offset, $limit );
		}
		$count   = 0;
		$failure = null;
		try {
			foreach ( $ids as $id ) {
				try {
					SendAuthorization::recover( (int) $id );
				} catch ( \Throwable $error ) {
					// One failing source cannot block the rest of this bounded page.
					$failure ??= $error;
				}
				++$count;
			}
		} finally {
			// Round-robin even after a failed consumer: an old stuck page cannot
			// starve later history. Re-entry may repeat work; per-source permits
			// and locks remain authoritative. Short/empty pages wrap the scan.
			update_option( self::RECOVERY_OFFSET, count( $ids ) === $limit ? $offset + $limit : 0, false );
		}
		if ( null !== $failure ) {
			throw $failure;
		}
		update_option( self::HEARTBEAT, microtime( true ), false );
		return $count;
	}

	/**
	 * One ordered native ID page; only the authorization consumer loads sources.
	 *
	 * @param int $offset Position in the current pending set.
	 * @param int $limit Existing total business capacity.
	 * @return list<int> Native source IDs.
	 */
	private static function pending_ids( int $offset, int $limit ): array {
		$meta = array(
			array(
				'key'   => self::PENDING,
				'value' => 'yes',
			),
		); // phpcs:ignore WordPress.DB.SlowDBQuery -- Exact native pending-work lookup.
		// Woo's meta_query/field_query are HPOS-only. Use WP's native query
		// for CPT instead of hydrating unrelated orders or inventing SQL keysets.
		// phpcs:disable WordPress.DB.SlowDBQuery -- One bounded, pending-only native source page.
		$ids = OrderUtil::custom_orders_table_usage_is_enabled()
			? wc_get_orders(
				array(
					'limit'      => $limit,
					'offset'     => $offset,
					'return'     => 'ids',
					'orderby'    => 'ID',
					'order'      => 'ASC',
					'meta_query' => $meta,
				)
			)
			: get_posts(
				array(
					'post_type'      => wc_get_order_types( 'view-orders' ),
					'post_status'    => array_keys( wc_get_order_statuses() ),
					'posts_per_page' => $limit,
					'offset'         => $offset,
					'fields'         => 'ids',
					'orderby'        => 'ID',
					'order'          => 'ASC',
					'meta_query'     => $meta,
				)
			);
		// phpcs:enable
		return is_array( $ids ) ? array_values( array_map( 'absint', array_filter( $ids, 'is_numeric' ) ) ) : array();
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
