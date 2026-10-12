<?php
/**
 * The condition functions the product template asks through LiveCanvas's own
 * tags (`[lc_if condition="linker_commerce_pdp_has_pairings"]`): each answers one
 * question about the product on display, so the template decides what exists
 * and the data layer only answers. Data only — these print nothing.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

use Linker\Commerce\Products\Faqs;
use Linker\Commerce\Products\Materials;
use Linker\Commerce\Storefront\ProductView;

if ( ! function_exists( 'linker_commerce_pdp_product_id' ) ) {
	/**
	 * The product of the page being rendered, 0 outside a product.
	 */
	function linker_commerce_pdp_product_id(): int {
		$product = $GLOBALS['product'] ?? null;
		if ( $product instanceof WC_Product ) {
			return (int) $product->get_id();
		}
		$id = (int) get_the_ID();
		return is_singular( 'product' ) ? $id : 0;
	}
}

if ( ! function_exists( 'linker_commerce_pdp_has_pairings' ) ) {
	/**
	 * Whether the product has at least one compatibility record whose paired
	 * product is published.
	 */
	function linker_commerce_pdp_has_pairings(): bool {
		$id = linker_commerce_pdp_product_id();
		if ( $id <= 0 ) {
			return false;
		}
		foreach ( Materials::relationships( Materials::source_product_id( $id ) ) as $relationship ) {
			$target_id = (int) ( $relationship['target_product_id'] ?? 0 );
			$target    = $target_id ? wc_get_product( $target_id ) : null;
			if ( $target instanceof WC_Product && 'publish' === $target->get_status() ) {
				return true;
			}
		}
		return false;
	}
}

if ( ! function_exists( 'linker_commerce_pdp_has_scenes' ) ) {
	/**
	 * Whether the product carries an application scenario the live page opens
	 * the section for. Measured on the live pages 2026-10-11: the section
	 * needs a scene image and a checklist — the battery and the ETA inverter
	 * carry neither, the SAJ transfer switch carries an image but no checklist
	 * (live renders no `#fit` block), while the BAT-AC cabinet and the
	 * ETA/ETR inverters carry both and the section renders.
	 */
	function linker_commerce_pdp_has_scenes(): bool {
		$id = linker_commerce_pdp_product_id();
		if ( $id <= 0 ) {
			return false;
		}
		foreach ( ( new ProductView() )->scenarios( $id ) as $scenario ) {
			if ( (int) $scenario['image'] > 0 && array() !== (array) $scenario['checklist'] ) {
				return true;
			}
		}
		return false;
	}
}

if ( ! function_exists( 'linker_commerce_pdp_has_faqs' ) ) {
	/**
	 * Whether the product carries FAQ rows.
	 */
	function linker_commerce_pdp_has_faqs(): bool {
		$id = linker_commerce_pdp_product_id();
		return $id > 0 && array() !== Faqs::of( $id );
	}
}
