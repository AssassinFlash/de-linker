<?php
/**
 * Queue and authorize quotation notices from the current order.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Quotation;

use Automattic\WooCommerce\Utilities\OrderUtil;
use Linker\Commerce\Account\PrivateFiles;
use Linker\Commerce\Inquiry\Assessment\CurrentSource;
use Linker\Commerce\Inquiry\Assessment\Reviews;
use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Mail\Message;
use Linker\Commerce\Quotation\Emails\QuotationIssuedEmail;
use Linker\Commerce\Registration\Approval;
use WC_Order;

/** Outbox decisions run independently of WooCommerce's email templates. */
final class Notice {
	/** Producer ID and native acceptance recorded on the inquiry. */
	public const ID       = 'linker_quotation_issued';
	public const ACCEPTED = '_linker_quotation_notice_number';
	public const JOB      = '_linker_quotation_notice_job';

	/**
	 * Queue a revision even though the WooCommerce status stays the same.
	 *
	 * @param int $id Inquiry ID.
	 */
	public static function notify( int $id ): void {
		$email = WC()->mailer()->get_emails()[ QuotationIssuedEmail::class ] ?? null;
		if ( $email instanceof QuotationIssuedEmail ) {
			$email->trigger( $id );
		}
	}

	/**
	 * Check the frozen destination against the current owner before each transport attempt.
	 *
	 * @param Message $message Outbox message, already authenticated by SendAuthorization.
	 * @param int     $job_id Native Outbox job.
	 */
	public static function deliverable( Message $message, int $job_id ): bool {
		$origin = $message->origin;
		$record = $origin['record'] ?? null;
		$order  = is_int( $record ) ? CurrentSource::order( $record ) : self::legacy_source( $job_id );
		if ( ! $order || ! $order->has_status( array( Statuses::QUOTATION, 'completed' ) ) || $order->get_meta( Reviews::ERASED ) ) {
			return false;
		}
		$id     = $order->get_customer_id();
		$number = (string) $order->get_meta( Issuer::NUMBER_META );
		if ( ! ( new Approval() )->sees_prices( $id ) || '' === $number || $number !== $order->get_meta( self::ACCEPTED ) || $job_id !== (int) $order->get_meta( self::JOB ) ) {
			return false;
		}
		if ( null !== $record && ( ( $origin['owner'] ?? 0 ) !== $id || ( $origin['number'] ?? '' ) !== $number ) ) {
			return false;
		}
		$owner = get_userdata( $id );
		if ( ! $owner instanceof \WP_User || 1 !== count( $message->to ) ) {
			return false;
		}
		$recipient = $message->to[0];
		$local     = strstr( $owner->user_email, '@', true );
		if ( false === $local || strstr( $recipient, '@', true ) !== $local || 0 !== strcasecmp( $owner->user_email, $recipient ) ) {
			return false;
		}
		foreach ( $message->headers as $header ) {
			if ( preg_match( '/^(?:Cc|Bcc):\s*\S/i', $header ) ) {
				return false;
			}
		}
		$files = new PrivateFiles( Issuer::DIRECTORY );
		return '' !== $files->path( (string) $order->get_meta( Issuer::FILE_META ) );
	}

	/**
	 * Earlier jobs recorded their accepted job ID and document number on the order.
	 *
	 * @param int $job_id Queued quotation job.
	 */
	private static function legacy_source( int $job_id ): ?WC_Order {
		if ( $job_id < 1 ) {
			return null;
		}
		$meta = array(
			array(
				'key'   => self::JOB,
				'value' => (string) $job_id,
			),
		);
		// phpcs:disable WordPress.DB.SlowDBQuery -- Resolve only an already queued pre-revision notice.
		$ids = OrderUtil::custom_orders_table_usage_is_enabled()
			? wc_get_orders(
				array(
					'type'       => 'shop_order',
					'status'     => array( Statuses::QUOTATION, 'completed' ),
					'return'     => 'ids',
					'limit'      => 2,
					'meta_query' => $meta,
				)
			)
			: get_posts(
				array(
					'post_type'      => 'shop_order',
					'post_status'    => array( 'wc-' . Statuses::QUOTATION, 'wc-completed' ),
					'fields'         => 'ids',
					'posts_per_page' => 2,
					'meta_query'     => $meta,
				)
			);
		// phpcs:enable
		return is_array( $ids ) && 1 === count( $ids ) && is_numeric( $ids[0] ) ? CurrentSource::order( (int) $ids[0] ) : null;
	}
}
