<?php
/**
 * One pushed stock batch, applied row by row.
 *
 * @package Linker\Commerce\Stock
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Stock;

use WC_Product;

/**
 * Applies what an ERP pushed to WooCommerce's own stock (ticket #69): the
 * product is resolved by SKU and the values go through WooCommerce's own
 * writers — wc_update_product_stock() for quantities, which keep the stock
 * status, the product_visibility term and every reading surface in sync on
 * save, and wc_update_product_stock_status() for the state of a product
 * without managed stock (on those the quantity is meaningless, so state is
 * its word). The values are compared before anything is written, so
 * pushing what is already in place is a no-op row. A row that does not
 * parse, or a SKU the site does not know, is an error row of its own; the
 * batch is never rolled back.
 */
final class Batch {

	/**
	 * The stock states a push may set. The site has no backorder concept
	 * (AGENTS.md §1: products → inquiry, everything after is offline), so
	 * onbackorder is not on the list; a push of it is an error row.
	 */
	public const STATES = array( 'instock', 'outofstock' );

	/**
	 * The row statuses.
	 */
	public const APPLIED   = 'applied';
	public const UNCHANGED = 'unchanged';
	public const ERROR     = 'error';

	/**
	 * Applies a batch and answers its per-SKU rows in request order.
	 *
	 * @param mixed[] $items The pushed rows, as received.
	 * @return array{results: list<array<string, mixed>>, applied: int, unchanged: int, errors: int}
	 */
	public static function apply( array $items ): array {
		$results = array();
		$counts  = array(
			'applied'   => 0,
			'unchanged' => 0,
			'errors'    => 0,
		);
		foreach ( $items as $item ) {
			$row       = self::apply_row( $item );
			$results[] = $row;
			++$counts[ self::ERROR === $row['status'] ? 'errors' : (string) $row['status'] ];
		}
		return array(
			'results'   => $results,
			'applied'   => $counts['applied'],
			'unchanged' => $counts['unchanged'],
			'errors'    => $counts['errors'],
		);
	}

	/**
	 * Applies one row: parse, resolve, compare, write.
	 *
	 * @param mixed $item The pushed row, as received.
	 * @return array<string, mixed> The row's result.
	 */
	private static function apply_row( $item ): array {
		if ( ! \is_array( $item ) ) {
			return array(
				'sku'    => '',
				'status' => self::ERROR,
				'code'   => 'invalid_item',
			);
		}
		$sku = $item['sku'] ?? null;
		if ( ! \is_string( $sku ) || '' === $sku ) {
			return array(
				'sku'    => '',
				'status' => self::ERROR,
				'code'   => 'invalid_sku',
			);
		}
		$qty = $item['qty'] ?? null;
		if ( null !== $qty && ( ! \is_int( $qty ) || $qty < 0 ) ) {
			return array(
				'sku'    => $sku,
				'status' => self::ERROR,
				'code'   => 'invalid_qty',
			);
		}
		$state = $item['state'] ?? null;
		if ( null !== $state && ! \in_array( $state, self::STATES, true ) ) {
			return array(
				'sku'    => $sku,
				'status' => self::ERROR,
				'code'   => 'invalid_state',
			);
		}
		if ( null === $qty && null === $state ) {
			return array(
				'sku'    => $sku,
				'status' => self::ERROR,
				'code'   => 'missing_target',
			);
		}

		$product_id = wc_get_product_id_by_sku( $sku );
		$product    = $product_id ? wc_get_product( $product_id ) : null;
		if ( ! $product instanceof WC_Product ) {
			return array(
				'sku'    => $sku,
				'status' => self::ERROR,
				'code'   => 'unknown_sku',
			);
		}
		// A quantity needs managed stock to land anywhere; a state-only push
		// also works on a product that does not manage stock.
		if ( null !== $qty && ! $product->managing_stock() ) {
			return array(
				'sku'    => $sku,
				'status' => self::ERROR,
				'code'   => 'not_stock_managed',
			);
		}

		// WooCommerce's own rule (validate_props, the same on every save):
		// a product that manages stock carries the status its quantity
		// derives — an explicit state cannot stick there, the product admin
		// hides the status select for exactly those products. So the
		// quantity rules managed products, and `state` is the word for
		// products without managed stock. A state that contradicts what the
		// quantity derives is a per-row error, never a silent no-op: the ERP
		// pulling a product that the shop would still list is the
		// failure this channel must not make.
		if ( $product->managing_stock() ) {
			$probe = wc_get_product( $product_id );
			$probe->set_stock_quantity( $qty ?? (int) $product->get_stock_quantity() );
			$probe->validate_props();
			$target_status = $probe->get_stock_status();
			if ( null !== $state && $state !== $target_status ) {
				return array(
					'sku'    => $sku,
					'status' => self::ERROR,
					'code'   => 'state_overridden',
				);
			}
			$target_qty = $qty ?? (int) $product->get_stock_quantity();
		} else {
			$target_qty    = null;
			$target_status = (string) $state;
		}
		$same_qty   = null === $target_qty || (int) $product->get_stock_quantity() === $target_qty;
		$same_state = $product->get_stock_status() === $target_status;
		if ( $same_qty && $same_state ) {
			return array(
				'sku'          => $sku,
				'status'       => self::UNCHANGED,
				'qty'          => (int) $product->get_stock_quantity(),
				'stock_status' => $product->get_stock_status(),
			);
		}

		if ( null !== $target_qty ) {
			wc_update_product_stock( $product, $target_qty, 'set' );
		} else {
			wc_update_product_stock_status( $product_id, $target_status );
		}
		$final = wc_get_product( $product_id );
		return array(
			'sku'          => $sku,
			'status'       => self::APPLIED,
			'qty'          => (int) $final->get_stock_quantity(),
			'stock_status' => $final->get_stock_status(),
		);
	}
}
