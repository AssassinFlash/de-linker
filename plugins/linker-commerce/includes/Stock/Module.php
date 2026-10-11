<?php
/**
 * Hooks of the stock module.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Stock;

/**
 * The ERP push channel: its audit rows and its REST route. It needs
 * WooCommerce (the pushes land on products), so like the other commerce
 * modules it registers once every plugin is loaded.
 */
final class Module {

	/**
	 * Sets up the module.
	 *
	 * @param StockController $stock The push route.
	 * @param BatchLog        $log   The audit rows.
	 */
	public function __construct(
		private readonly StockController $stock,
		private readonly BatchLog $log
	) {}

	/**
	 * Adds the module's hooks.
	 */
	public function register(): void {
		add_action( 'init', array( $this->log, 'register_post_type' ) );
		add_action( 'rest_api_init', array( $this->stock, 'register_routes' ) );
	}
}
