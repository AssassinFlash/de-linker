<?php
/**
 * Preserve structured evidence through both native Woo order stores.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry\Assessment;

use WC_Order;

/** A narrow adapter for Woo's first-add array slashing asymmetry. */
final class StructuredMeta {

	/**
	 * Set data for the caller's ordinary save, then reload before using its value.
	 * WC_Data_Store_WP::add_meta slashes strings only; add_metadata unslashes
	 * arrays recursively. Updates by meta id and HPOS do not strip arrays.
	 *
	 * @param WC_Order             $order Inquiry.
	 * @param string               $key Protected meta key.
	 * @param array<string, mixed> $value Canonical unslashed evidence.
	 */
	public static function update( WC_Order $order, string $key, array $value ): void {
		$store  = $order->get_data_store();
		$legacy = $store instanceof \WC_Data_Store && is_a( $store->get_current_class_name(), \WC_Order_Data_Store_CPT::class, true );
		$order->update_meta_data( $key, $legacy && ! $order->meta_exists( $key ) ? wp_slash( $value ) : $value );
	}
}
