<?php
/**
 * The PDP's native related-products loop, ordered stably.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

/**
 * Woo shuffles the related loop's cards on every render
 * (woocommerce_related_products(), `orderby => 'rand'`); a page cache freezes
 * one shuffle and every uncached render disagrees with it. The same product
 * set in a stable title order keeps the native loop, the page cache and the
 * live|local parity gate consistent. Woo's own filter is the whole change:
 * no query, markup or style is replaced.
 */
final class RelatedProducts {

	/**
	 * Adds the module's hooks.
	 */
	public function register(): void {
		add_filter( 'woocommerce_related_products_args', array( $this, 'order' ) );
	}

	/**
	 * One stable order for the native related loop: title, ascending.
	 *
	 * @param array<string,mixed> $args The loop's args, `orderby => 'rand'` by default.
	 * @return array<string,mixed> The same args, ordered by title.
	 */
	public function order( array $args ): array {
		$args['orderby'] = 'title';
		$args['order']   = 'ASC';
		return $args;
	}
}
