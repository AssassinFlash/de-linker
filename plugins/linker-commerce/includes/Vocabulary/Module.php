<?php
/**
 * Hooks of the vocabulary module.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Vocabulary;

/**
 * The site's words in WooCommerce's strings, buttons and page titles, and its
 * money, date and tax-label forms per language.
 */
final class Module {

	/**
	 * Sets up the module.
	 *
	 * @param Overrides    $overrides The gettext replacements.
	 * @param Labels       $labels    Buttons and page titles.
	 * @param LocaleFormat $formats   Money, dates and tax labels by language.
	 */
	public function __construct(
		private readonly Overrides $overrides,
		private readonly Labels $labels,
		private readonly LocaleFormat $formats
	) {}

	/**
	 * Adds the module's hooks.
	 */
	public function register(): void {
		add_filter( 'gettext_woocommerce', array( $this->overrides, 'gettext' ), 10, 2 );
		add_filter( 'gettext_with_context_woocommerce', array( $this->overrides, 'gettext_with_context' ), 10, 3 );
		add_filter( 'ngettext_woocommerce', array( $this->overrides, 'ngettext' ), 10, 4 );
		add_action( 'change_locale', array( $this->overrides, 'reset' ) );

		add_filter( 'woocommerce_product_single_add_to_cart_text', array( $this->labels, 'add_to_draft' ) );
		add_filter( 'woocommerce_product_add_to_cart_text', array( $this->labels, 'add_to_draft' ), 10, 2 );
		add_filter( 'woocommerce_order_button_text', array( $this->labels, 'send_inquiry' ) );
		add_filter( 'woocommerce_thankyou_order_received_text', array( $this->labels, 'inquiry_received' ) );
		add_filter( 'woocommerce_checkout_must_be_logged_in_message', array( $this->labels, 'log_in_to_send' ) );
		add_filter( 'woocommerce_get_privacy_policy_text', array( $this->labels, 'privacy_text' ), 10, 2 );
		add_filter( 'the_title', array( $this->labels, 'page_title' ), 5, 2 );
		add_filter( 'document_title_parts', array( $this->labels, 'document_title' ) );
		add_filter( 'woocommerce_get_breadcrumb', array( $this->labels, 'breadcrumb' ) );
		add_action( 'woocommerce_before_cart', array( $this->labels, 'draft_heading' ), 0 );

		add_filter( 'woocommerce_date_format', array( $this->formats, 'wc_date_format' ) );
		add_filter( 'wc_get_price_decimal_separator', array( $this->formats, 'decimal_separator' ) );
		add_filter( 'wc_get_price_thousand_separator', array( $this->formats, 'thousand_separator' ) );
		add_filter( 'woocommerce_price_format', array( $this->formats, 'price_format' ) );
		add_filter( 'woocommerce_rate_label', array( $this->formats, 'rate_label' ), 10, 2 );
		add_filter( 'woocommerce_order_get_tax_totals', array( $this->formats, 'order_tax_totals' ) );
	}
}
