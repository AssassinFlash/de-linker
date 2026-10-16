<?php
/**
 * What the solution draft and the Proforma request page say about prices.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Gating;

use Linker\Commerce\Account\AuthTemplates;
use WC_Order;
use WC_Product;

/**
 * For guests, the solution draft shows no totals but the way to prices: log in
 * and request a Proforma, or create an account. For customers, a draft with
 * lines that carry no price says that the Proforma prices them.
 */
final class DraftSummary {

	/**
	 * Sets up the summary.
	 *
	 * @param CommerceState $state   The price rule.
	 * @param PriceDisplay  $display The price display (inquiry lines without a price).
	 */
	public function __construct(
		private readonly CommerceState $state,
		private readonly PriceDisplay $display
	) {}

	/**
	 * Replaces the totals box of the solution draft with the login box for guests.
	 * Runs on woocommerce_cart_collaterals before WooCommerce prints the totals.
	 * "Register" opens the account's own register page (AuthTemplates).
	 */
	public function guest_totals(): void {
		if ( $this->state->visitor_sees_prices() ) {
			return;
		}
		remove_action( 'woocommerce_cart_collaterals', 'woocommerce_cart_totals', 10 );
		printf(
			'<div class="cart_totals linker-login-box"><p>%1$s</p><p><a class="button alt wc-forward" href="%2$s">%3$s</a></p><p><a href="%4$s">%5$s</a></p></div>',
			esc_html__( 'Prices are shown after you log in. Then you can request a Proforma invoice for this solution draft.', 'linker-commerce' ),
			esc_url( wc_get_checkout_url() ),
			esc_html__( 'Log in and request a Proforma', 'linker-commerce' ),
			esc_url( AuthTemplates::register_url() ),
			esc_html__( 'No account yet? Register', 'linker-commerce' )
		);
	}

	/**
	 * Under the totals: lines without a price are priced in the Proforma.
	 * Runs on woocommerce_cart_totals_after_order_total and
	 * woocommerce_review_order_after_order_total (inside the totals table).
	 */
	public function unpriced_note(): void {
		if ( ! $this->state->visitor_sees_prices() || ! $this->draft_has_unpriced_lines() ) {
			return;
		}
		printf(
			'<tr class="linker-unpriced-note"><td colspan="2">%s</td></tr>',
			esc_html__( 'For products without a price, we state the price in your Proforma invoice.', 'linker-commerce' )
		);
	}

	/**
	 * Under an inquiry's table (confirmation, inquiry page, customer email): lines
	 * without a price are priced in the Proforma. The note speaks to the customer,
	 * so the team's email leaves it out. Runs on
	 * woocommerce_order_details_after_order_table and woocommerce_email_after_order_table.
	 *
	 * @param WC_Order $order         Inquiry.
	 * @param bool     $sent_to_admin Whether the email goes to the team.
	 * @param bool     $plain_text    Whether the email is plain text.
	 */
	public function inquiry_note( WC_Order $order, bool $sent_to_admin = false, bool $plain_text = false ): void {
		if ( $sent_to_admin || ! $this->display->has_unpriced_lines( $order ) ) {
			return;
		}
		$note = __( 'For products without a price, we state the price in your Proforma invoice.', 'linker-commerce' );
		if ( $plain_text ) {
			echo "\n" . esc_html( $note ) . "\n";
		} else {
			printf( '<p class="linker-unpriced-note">%s</p>', esc_html( $note ) );
		}
	}

	/**
	 * Whether a line of the current solution draft shows a text instead of a price.
	 */
	private function draft_has_unpriced_lines(): bool {
		foreach ( WC()->cart->get_cart() as $line ) {
			$product = $line['data'] ?? null;
			if ( $product instanceof WC_Product && null !== $this->state->reason( $product ) ) {
				return true;
			}
		}
		return false;
	}
}
