<?php
/**
 * Hooks of the settings module.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Settings;

/**
 * The settings tab and the pinned WooCommerce options.
 */
final class Module {

	/**
	 * Sets up the module.
	 *
	 * @param SettingsTab $tab     The settings tab.
	 * @param WooOptions  $options The pinned WooCommerce options.
	 */
	public function __construct(
		private readonly SettingsTab $tab,
		private readonly WooOptions $options
	) {}

	/**
	 * Adds the module's hooks.
	 */
	public function register(): void {
		add_filter( 'woocommerce_settings_tabs_array', array( $this->tab, 'add_tab' ), 50 );
		add_action( 'woocommerce_settings_' . SettingsTab::TAB, array( $this->tab, 'output' ) );
		add_action( 'woocommerce_update_options_' . SettingsTab::TAB, array( $this->tab, 'save' ) );
		add_filter( 'woocommerce_admin_settings_sanitize_option_' . Options::TEAM_BCC, array( $this->tab, 'sanitize_bcc' ) );
		add_filter( 'woocommerce_admin_settings_sanitize_option_' . Options::BANK_IBAN, array( $this->tab, 'sanitize_iban' ) );
		add_filter( 'woocommerce_admin_settings_sanitize_option_' . Options::BANK_BIC, array( $this->tab, 'sanitize_bic' ) );
		add_filter( 'woocommerce_admin_settings_sanitize_option_' . Options::PROFORMA_PREFIX, array( $this->tab, 'sanitize_prefix' ) );

		foreach ( array_keys( WooOptions::pinned() ) as $option ) {
			add_filter( 'pre_option_' . $option, array( $this->options, 'pin' ), 10, 2 );
		}
		foreach ( array_keys( WooOptions::endpoints() ) as $var ) {
			if ( 'order-received' !== $var ) {
				add_filter( 'pre_option_woocommerce_myaccount_' . str_replace( '-', '_', $var ) . '_endpoint', array( $this->options, 'pin_endpoint_option' ), 10, 2 );
			}
		}
		add_filter( 'woocommerce_get_query_vars', array( $this->options, 'endpoint_slugs' ) );
		add_action( 'init', array( $this->options, 'flush_rewrites_when_endpoints_change' ), 99 );
	}
}
