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
	 * Whether the product carries the project scenario the `#fit` section and
	 * the nav's `Applications` link are opened for: a scenario with a
	 * non-empty checklist.
	 *
	 * Measured on the live pages 2026-10-13 against the products' own scenario
	 * records: the GW60K-STS-G10, the GW75K-ET-G10 and the EcoFlow OCEAN
	 * hybrids each carry a checklist and no scene image, and the live page
	 * renders `<section class="pdp-block pdp-fit" id="fit">` with "Where this
	 * model fits." plus the nav link; the ESA GW10K-EHA-G20 carries neither
	 * and the live page renders no `#fit` and no link. The image is therefore
	 * not part of this section's gate — an earlier reading required both and
	 * left every checklist-only product closed, the GW60K among them.
	 *
	 * A product whose scenarios carry only a scene image renders the live
	 * page's other `#fit` variant ("Product views and project settings." with
	 * a `pdp-scene-reel`); the scenes shortcode does not implement that
	 * variant yet, so this predicate answers about the project-fit one only.
	 * The live page's `Applications` link opens whichever variant the product
	 * has; here it opens the project-fit section.
	 */
	function linker_commerce_pdp_has_scenes(): bool {
		$id = linker_commerce_pdp_product_id();
		if ( $id <= 0 ) {
			return false;
		}
		foreach ( ( new ProductView() )->scenarios( $id ) as $scenario ) {
			if ( array() !== (array) $scenario['checklist'] ) {
				return true;
			}
		}
		return false;
	}
}

if ( ! function_exists( 'linker_commerce_draft_empty' ) ) {
	/**
	 * Whether the solution draft has no lines: the cart template's empty
	 * branch, and the one answer the Proforma gate reads too.
	 *
	 * LiveCanvas resolves `[lc_if condition="…"]` with function_exists() and
	 * one call of the named function (livecanvas modules/shortcodes.php, the
	 * lc_if handler), so the cart template's conditions must be functions —
	 * a filter under the condition's name is never consulted. A confirmation
	 * or a pay page is not an empty draft: those requests can share the cart
	 * template, and the condition must not hide a receipt.
	 */
	function linker_commerce_draft_empty(): bool {
		if ( function_exists( 'is_wc_endpoint_url' ) && ( is_wc_endpoint_url( 'order-received' ) || is_wc_endpoint_url( 'order-pay' ) ) ) {
			return false;
		}
		// A request WooCommerce never gave a cart (an admin, a REST or a CLI
		// run without wc_load_cart) holds no lines either; asking its cart
		// directly would be a fatal.
		$cart = function_exists( 'WC' ) ? WC()->cart : null;
		return ! $cart instanceof WC_Cart || $cart->is_empty();
	}
}

if ( ! function_exists( 'linker_commerce_draft_filled' ) ) {
	/**
	 * The cart template's filled branch. Never true together with
	 * linker_commerce_draft_empty().
	 */
	function linker_commerce_draft_filled(): bool {
		return ! linker_commerce_draft_empty();
	}
}

if ( ! function_exists( 'linker_commerce_logout_url' ) ) {
	/**
	 * The one-click sign-out (ticket #184, owner ruling 2026-10-15): Woo's own
	 * nonce-carrying logout URL, landing back on the account page with the
	 * state the sign-in card reads. The account menu's plain endpoint URL
	 * carries no nonce, so the shop asks "Are you sure you want to log out?"
	 * on a page of its own first — the confirmation this replaces.
	 */
	function linker_commerce_logout_url(): string {
		return wc_logout_url( add_query_arg( 'signed-out', 'true', wc_get_page_permalink( 'myaccount' ) ) );
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
