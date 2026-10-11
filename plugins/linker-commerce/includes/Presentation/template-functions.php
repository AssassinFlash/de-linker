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

use Linker\Commerce\Catalog\Faqs;
use Linker\Commerce\Catalog\Materials;
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
	 * Whether the product carries application scenarios with a scene image.
	 * Measured on the live pages 2026-10-11: a scenario without an image does
	 * not open the section (the battery and the ETA inverter have one scenario
	 * each, no image, and no `#fit` block; the BAT-AC cabinet's scenario has
	 * one and the section renders).
	 */
	function linker_commerce_pdp_has_scenes(): bool {
		$id = linker_commerce_pdp_product_id();
		if ( $id <= 0 ) {
			return false;
		}
		foreach ( ( new ProductView() )->scenarios( $id ) as $scenario ) {
			if ( (int) $scenario['image'] > 0 ) {
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
