<?php
/**
 * Sorting by price only for visitors who see prices.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Gating;

/**
 * A visitor without prices cannot sort products by price: the order alone would
 * tell which product costs more. The sort options leave out price, and a price
 * sort asked for in the address falls back to the default order.
 */
final class CatalogSorting {

	/**
	 * Sets up the sorting.
	 *
	 * @param CommerceState $state The price rule.
	 */
	public function __construct( private readonly CommerceState $state ) {}

	/**
	 * Sort options without price for guests; runs on woocommerce_catalog_orderby.
	 *
	 * @param array<string, string> $options Option → label.
	 * @return array<string, string>
	 */
	public function options( array $options ): array {
		if ( ! $this->state->visitor_sees_prices() ) {
			unset( $options['price'], $options['price-desc'] );
		}
		return $options;
	}

	/**
	 * The default order instead of a price order for guests; runs on woocommerce_get_catalog_ordering_args.
	 *
	 * @param array<string, mixed> $args    Query ordering arguments.
	 * @param string               $orderby Requested order.
	 * @return array<string, mixed>
	 */
	public function ordering( array $args, string $orderby ): array {
		if ( $this->state->visitor_sees_prices() || ! str_starts_with( $orderby, 'price' ) ) {
			return $args;
		}
		return array(
			'orderby'  => 'menu_order title',
			'order'    => 'ASC',
			'meta_key' => '', // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key -- clears WooCommerce's price key.
		);
	}
}
