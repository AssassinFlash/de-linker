<?php
/**
 * Hooks of the stock module.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Stock;

/**
 * The ERP push channel: its REST route, its audit rows and the retention of
 * those rows. It needs WooCommerce (the pushes land on products), so like the
 * other commerce modules it registers once every plugin is loaded.
 */
final class Module {

	/**
	 * Sets up the module.
	 *
	 * @param StockController $stock     The push route.
	 * @param BatchLog        $log       The audit rows.
	 * @param Retention       $retention The audit rows' retention.
	 */
	public function __construct(
		private readonly StockController $stock,
		private readonly BatchLog $log,
		private readonly Retention $retention
	) {}

	/**
	 * Adds the module's hooks.
	 */
	public function register(): void {
		add_action( 'init', array( $this->log, 'register_post_type' ) );
		add_action( 'rest_api_init', array( $this->stock, 'register_routes' ) );
		$this->retention->register();
	}
}
