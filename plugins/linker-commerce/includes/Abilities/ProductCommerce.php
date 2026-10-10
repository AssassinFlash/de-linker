<?php
/**
 * Commerce fields on a product card: price visibility, stock, RFQ.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Abilities;

use Linker\Commerce\Gating\CommerceState;
use WC_Product;

/**
 * The commerce object of search-products and get-product. Price visibility
 * is CommerceState, the one rule every surface reads (docs/specs/11-commerce.md).
 * Stock is only ever "in stock" to the customer (owner 2026-10-02).
 */
final class ProductCommerce {

	/**
	 * JSON Schema of the commerce object.
	 *
	 * @return array<string, mixed>
	 */
	public static function schema(): array {
		return array(
			'type'                 => 'object',
			'properties'           => array(
				'price_visible' => array(
					'type'        => 'boolean',
					'description' => __( 'Whether this visitor sees the stored price.', 'linker-commerce' ),
				),
				'price'         => array(
					'type'        => 'string',
					'description' => __( 'Stored price when it is visible.', 'linker-commerce' ),
				),
				'in_stock'      => array(
					'type'        => 'boolean',
					'description' => __( 'Whether the product is in stock. The site only ever says it is.', 'linker-commerce' ),
				),
				'rfq_only'      => array(
					'type'        => 'boolean',
					'description' => __( 'Whether the product is quoted per project.', 'linker-commerce' ),
				),
			),
			'required'             => array( 'price_visible', 'in_stock', 'rfq_only' ),
			'additionalProperties' => false,
		);
	}

	/**
	 * Commerce fields of a product for the current visitor.
	 *
	 * @param int             $product_id Product ID.
	 * @param WC_Product|null $product    The product, when already loaded.
	 * @return array{price_visible: bool, price?: string, in_stock: bool, rfq_only: bool}
	 */
	public static function of( int $product_id, ?WC_Product $product = null ): array {
		if ( ! $product instanceof WC_Product ) {
			$loaded  = wc_get_product( $product_id );
			$product = $loaded instanceof WC_Product ? $loaded : null;
		}
		$state    = new CommerceState();
		$rfq      = $product instanceof WC_Product && $state->is_rfq_only( $product );
		$visible  = $product instanceof WC_Product && $state->shows_price( $product );
		$commerce = array(
			'price_visible' => $visible,
			'in_stock'      => true,
			'rfq_only'      => $rfq,
		);
		if ( $visible ) {
			$commerce['price'] = (string) $product->get_price( 'edit' );
		}

		return $commerce;
	}

	/**
	 * Commerce fields when there is no product to show.
	 *
	 * @return array{price_visible: false, in_stock: false, rfq_only: false}
	 */
	public static function hidden(): array {
		return array(
			'price_visible' => false,
			'in_stock'      => false,
			'rfq_only'      => false,
		);
	}
}
