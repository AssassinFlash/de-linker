<?php
/**
 * Proven optional native summary envelope before any paid summary dispatch.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry;

use Linker\Commerce\Protection\BusinessCapacity;
use WC_Order;

/** No customer field is truncated; these bounds describe the existing generated summary. */
final class SummaryEnvelope {
	/**
	 * Existing Tools InquirySummary schema; a native test checks its real constants.
	 * U+0001 is the JSON worst case: six bytes per character, also after WP slashing.
	 *
	 * @return array<string,mixed> Maximum legal shape, never sent to a customer/model.
	 */
	public static function maximum(): array {
		return array(
			'summary'    => str_repeat( "\x01", 800 ),
			'quantities' => array_fill(
				0,
				12,
				array(
					'product_id' => PHP_INT_MAX,
					'quantity'   => PHP_INT_MAX,
				)
			),
			'conditions' => array_fill( 0, 6, str_repeat( "\x01", 120 ) ),
			'note'       => str_repeat( "\x01", 500 ),
			'source'     => 'model',
			'reason'     => 'transport_error',
		);
	}

	/**
	 * Measure the actual native three-copy serialization instead of guessing KiB.
	 * WC_Abstract_Order disables base deep cloning, so native init_meta_data gives
	 * this measurement its own current metadata objects; the real order is unchanged.
	 *
	 * @param WC_Order $order Complete prepared draft and frozen local context.
	 */
	public static function additional_bytes( WC_Order $order ): int {
		$maximum = clone $order;
		$maximum->init_meta_data(
			array_map(
				static fn ( \WC_Meta_Data $meta ): object => (object) array(
					'meta_id'    => $meta->id,
					'meta_key'   => $meta->key, // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key -- Native in-memory init_meta_data shape, no query.
					'meta_value' => $meta->value, // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_value -- Native in-memory init_meta_data shape, no query.
				),
				$order->get_meta_data()
			)
		);
		Assessment\StructuredMeta::update( $maximum, Sender::SUMMARY_META, self::maximum() );
		Assessment\Queue::refresh_summary( $maximum, false );
		// Three refreshed IEEE-754 JSON timestamps, each at most 24 ASCII bytes.
		// The actual maximum is measured with the same serializer in native tests.
		return max( 0, BusinessCapacity::bytes( $maximum ) - BusinessCapacity::bytes( $order ) ) + 3 * 24;
	}
}
