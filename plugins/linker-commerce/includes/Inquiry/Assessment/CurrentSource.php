<?php
/**
 * Fresh native business facts at a sending-permission boundary.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
namespace Linker\Commerce\Inquiry\Assessment;

use Automattic\WooCommerce\Caches\OrderCache;
use WC_Order;

/** Clear only this source's native caches; Woo still reconstructs all business objects. */
final class CurrentSource {
	/**
	 * Read core fields, items, account and product facts independently of pre-provider objects.
	 *
	 * @param int $id Persisted native source.
	 */
	public static function order( int $id ): ?WC_Order {
		try {
			clean_post_cache( $id );
			$cache = wc_get_container()->get( OrderCache::class );
			$cache->remove( $id );
			$store = \WC_Data_Store::load( 'order' )->get_current_class_name();
			// Woo's internal HPOS datastore is not exported in the official PHP stubs.
			// Resolve the verified native service and check its public per-record API.
			if ( is_a( $store, 'Automattic\\WooCommerce\\Internal\\DataStores\\Orders\\OrdersTableDataStore', true ) ) {
				$clear = array( wc_get_container()->get( $store ), 'clear_cached_data' );
				if ( ! is_callable( $clear ) ) {
					return null; }
				$clear( array( $id ) );
			}
			wp_cache_delete( 'order-items-' . $id, 'orders' );
			$order = wc_get_order( $id );
			if ( ! $order instanceof WC_Order ) {
				return null;
			}
			$order->read_meta_data( true );
			foreach ( $order->get_items() as $item ) {
				$item_id = $item->get_id();
				wp_cache_delete( 'item-' . $item_id, 'order-items' );
				wp_cache_delete( $item_id, 'order_item_meta' );
				wp_cache_delete( \WC_Data::generate_meta_cache_key( $item_id, 'order-items' ), 'order-items' );
				$read = array( $item->get_data_store(), 'read' );
				if ( ! is_callable( $read ) ) {
					return null; }
				$read( $item );
				if ( $item instanceof \WC_Order_Item_Product ) {
					foreach ( array( $item->get_product_id(), $item->get_variation_id() ) as $product ) {
						if ( $product > 0 ) {
							clean_post_cache( $product );
						}
					}
				}
			}
			if ( $order->get_customer_id() > 0 ) {
				clean_user_cache( $order->get_customer_id() );
				wp_cache_delete( $order->get_customer_id(), 'user_meta' );
			}
			return $order;
		} catch ( \Throwable $error ) {
			return null;
		}
	}
}
