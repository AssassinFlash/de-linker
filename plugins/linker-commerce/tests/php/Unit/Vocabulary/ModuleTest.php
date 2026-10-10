<?php
/**
 * Tests for the vocabulary module's hooks.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Vocabulary;

use Linker\Commerce\Tests\TestCase;
use Linker\Commerce\Vocabulary\Labels;
use Linker\Commerce\Vocabulary\LocaleFormat;
use Linker\Commerce\Vocabulary\Module;
use Linker\Commerce\Vocabulary\Overrides;
use Linker\Commerce\Vocabulary\Terms;
use WP_Mock;

/**
 * Tests for Module.
 *
 * @covers \Linker\Commerce\Vocabulary\Module
 */
final class ModuleTest extends TestCase {

	/**
	 * Gettext for WooCommerce's domain, the locale reset, buttons and titles are hooked.
	 */
	public function test_register_adds_the_hooks(): void {
		$overrides = new Overrides( new Terms() );
		$labels    = new Labels();
		$formats   = new LocaleFormat();

		WP_Mock::expectFilterAdded( 'gettext_woocommerce', array( $overrides, 'gettext' ), 10, 2 );
		WP_Mock::expectFilterAdded( 'gettext_with_context_woocommerce', array( $overrides, 'gettext_with_context' ), 10, 3 );
		WP_Mock::expectFilterAdded( 'ngettext_woocommerce', array( $overrides, 'ngettext' ), 10, 4 );
		WP_Mock::expectActionAdded( 'change_locale', array( $overrides, 'reset' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_product_single_add_to_cart_text', array( $labels, 'add_to_draft' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_product_add_to_cart_text', array( $labels, 'add_to_draft' ), 10, 2 );
		WP_Mock::expectFilterAdded( 'woocommerce_order_button_text', array( $labels, 'send_inquiry' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_thankyou_order_received_text', array( $labels, 'inquiry_received' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_checkout_must_be_logged_in_message', array( $labels, 'log_in_to_send' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_get_privacy_policy_text', array( $labels, 'privacy_text' ), 10, 2 );
		WP_Mock::expectFilterAdded( 'the_title', array( $labels, 'page_title' ), 5, 2 );
		WP_Mock::expectFilterAdded( 'document_title_parts', array( $labels, 'document_title' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_get_breadcrumb', array( $labels, 'breadcrumb' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_date_format', array( $formats, 'wc_date_format' ) );
		WP_Mock::expectFilterAdded( 'wc_get_price_decimal_separator', array( $formats, 'decimal_separator' ) );
		WP_Mock::expectFilterAdded( 'wc_get_price_thousand_separator', array( $formats, 'thousand_separator' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_price_format', array( $formats, 'price_format' ) );
		WP_Mock::expectFilterAdded( 'woocommerce_rate_label', array( $formats, 'rate_label' ), 10, 2 );
		WP_Mock::expectFilterAdded( 'woocommerce_order_get_tax_totals', array( $formats, 'order_tax_totals' ) );

		( new Module( $overrides, $labels, $formats ) )->register();

		$this->assertConditionsMet();
	}
}
