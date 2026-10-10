<?php
/**
 * Tests for the settings module's hooks.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Settings;

use Linker\Commerce\Settings\Module;
use Linker\Commerce\Settings\Options;
use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Settings\SettingsTab;
use Linker\Commerce\Settings\WooOptions;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for Module.
 *
 * @covers \Linker\Commerce\Settings\Module
 */
final class ModuleTest extends TestCase {

	/**
	 * The tab, its sanitizers, every pinned option and the endpoint slugs are hooked.
	 */
	public function test_register_adds_the_hooks(): void {
		$tab     = new SettingsTab( new JobStore() );
		$options = new WooOptions();

		WP_Mock::expectFilterAdded( 'woocommerce_settings_tabs_array', array( $tab, 'add_tab' ), 50 );
		WP_Mock::expectActionAdded( 'woocommerce_settings_' . SettingsTab::TAB, array( $tab, 'output' ) );
		WP_Mock::expectActionAdded( 'woocommerce_update_options_' . SettingsTab::TAB, array( $tab, 'save' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_admin_settings_sanitize_option_' . Options::TEAM_BCC, array( $tab, 'sanitize_bcc' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_admin_settings_sanitize_option_' . Options::BANK_IBAN, array( $tab, 'sanitize_iban' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_admin_settings_sanitize_option_' . Options::BANK_BIC, array( $tab, 'sanitize_bic' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_admin_settings_sanitize_option_' . Options::PROFORMA_PREFIX, array( $tab, 'sanitize_prefix' ) );
		foreach ( array_keys( WooOptions::pinned() ) as $option ) {
			WP_Mock::expectFilterAdded( 'pre_option_' . $option, array( $options, 'pin' ), 10, 2 );
		}
		foreach ( array( 'orders', 'view_order', 'edit_address', 'downloads', 'payment_methods', 'add_payment_method', 'delete_payment_method', 'set_default_payment_method' ) as $endpoint ) {
			WP_Mock::expectFilterAdded( 'pre_option_woocommerce_myaccount_' . $endpoint . '_endpoint', array( $options, 'pin_endpoint_option' ), 10, 2 );
		}
		WP_Mock::expectFilterAdded( 'woocommerce_get_query_vars', array( $options, 'endpoint_slugs' ) );
		WP_Mock::expectActionAdded( 'init', array( $options, 'flush_rewrites_when_endpoints_change' ), 99 );

		( new Module( $tab, $options ) )->register();

		$this->assertConditionsMet();
	}
}
