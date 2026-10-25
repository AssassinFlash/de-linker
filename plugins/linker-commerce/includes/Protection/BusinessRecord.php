<?php
/**
 * Native inquiry association for interrupted acknowledgements and safe retries.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

use Linker\Commerce\Inquiry\Statuses;
use WC_Order;

/** Store scalar HMAC references, never posted raw bodies or proof credentials. */
final class BusinessRecord {
	public const REQUEST = '_linker_public_request';
	public const INPUT   = '_linker_public_input';
	public const SUBJECT = '_linker_public_subject';

	/** Stamp before Woo's first save, including checkout-created inquiries. */
	public function register(): void {
		add_action( 'woocommerce_before_order_object_save', array( $this, 'stamp' ) );
		add_filter( 'woocommerce_privacy_remove_order_personal_data_meta', array( $this, 'erase_fields' ) );
	}

	/**
	 * Native Woo erasure removes pseudonymous retry links with the order's PII.
	 *
	 * @param array<string,string> $fields Native erasure fields and data types.
	 * @return array<string,string>
	 */
	public function erase_fields( array $fields ): array {
		return array_merge(
			$fields,
			array(
				self::REQUEST         => 'text',
				self::INPUT           => 'text',
				self::SUBJECT         => 'text',
				BusinessCapacity::KEY => 'text',
			)
		);
	}

	/**
	 * Context is set only around a dispatched server callback, never from POST.
	 *
	 * @param WC_Order $order Native order about to be saved.
	 */
	public function stamp( WC_Order $order ): void {
		if ( $order->get_id() > 0 ) {
			return;
		}
		$context = apply_filters( 'linker_commerce_public_business_context', null ); // phpcs:ignore WooCommerce.Commenting.CommentHooks.MissingHookComment -- Trusted current dispatch context shared with Tools; removed in finally.
		if ( ! is_array( $context ) || empty( $context['enforced'] ) || empty( $context['id'] ) || empty( $context['fingerprint'] ) || empty( $context['binding'] ) ) {
			return;
		}
		$order->update_meta_data( self::REQUEST, $context['id'] );
		$order->update_meta_data( self::INPUT, $context['fingerprint'] );
		$order->update_meta_data( self::SUBJECT, $context['binding'] );
	}

	/**
	 * A result reference alone does not authorize disclosure of an inquiry.
	 *
	 * @param string              $id Stable logical UUID.
	 * @param string              $fingerprint Current request HMAC.
	 * @param string              $binding Current server-derived subject.
	 * @param array<string,mixed> $receipt The journal receipt checked by the caller.
	 */
	public static function recover( string $id, string $fingerprint, string $binding, array $receipt ): ?WC_Order {
		$native = (int) ( $receipt['outcome'] ?? 0 );
		if ( $native > 0 ) {
			$order = wc_get_order( $native );
			return $order instanceof WC_Order && self::matches( $order, $id, $fingerprint, $binding ) ? $order : null;
		}
		// phpcs:disable WordPress.DB.SlowDBQuery -- Exact rare interrupted-write lookup by HMAC-associated UUID, never a listing.
		// Woo supports meta queries with HPOS. Classic storage uses WP's native
		// exact postmeta query, then Woo's object API for status and final checks.
		if ( \Automattic\WooCommerce\Utilities\OrderUtil::custom_orders_table_usage_is_enabled() ) {
			$orders = wc_get_orders(
				array(
					'limit'      => 2,
					'meta_query' => array(
						array(
							'key'   => self::REQUEST,
							'value' => $id,
						),
					),
				)
			);
		} else {
			$ids    = get_posts(
				array(
					'post_type'   => 'shop_order',
					'post_status' => 'any',
					'numberposts' => 2,
					'fields'      => 'ids',
					'meta_key'    => self::REQUEST,
					'meta_value'  => $id,
				)
			); // phpcs:ignore WordPress.DB.SlowDBQuery -- Exact rare interrupted-write recovery, never the normal listing path.
			$orders = array_map( 'wc_get_order', $ids );
		}
		// phpcs:enable WordPress.DB.SlowDBQuery
		if ( ! is_array( $orders ) || 1 !== count( $orders ) || ! $orders[0] instanceof WC_Order ) {
			return null;
		}
		return self::matches( $orders[0], $id, $fingerprint, $binding ) ? $orders[0] : null;
	}

	/**
	 * Only an actually received inquiry can be reported as received.
	 *
	 * @param WC_Order $order Candidate native result.
	 * @param string   $id UUID.
	 * @param string   $fingerprint Current input HMAC.
	 * @param string   $binding Current subject.
	 */
	private static function matches( WC_Order $order, string $id, string $fingerprint, string $binding ): bool {
		return ( $order->has_status( array( Statuses::RECEIVED, Statuses::PROFORMA, 'completed', 'cancelled' ) ) || ( $order->has_status( 'pending' ) && $order->get_meta( Intake::META ) && \Linker\Commerce\Mail\NotificationHold::held( $order ) ) )
			&& $id === $order->get_meta( self::REQUEST ) && $fingerprint === $order->get_meta( self::INPUT ) && $binding === $order->get_meta( self::SUBJECT );
	}
}
