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
	 * Replaces the totals box of the solution draft when the visitor sees no
	 * prices. A guest reads the guest box; a signed-in account under review or
	 * restricted reads its own state and never "No account yet? Register" —
	 * it already has an account, and the register page would bounce it back.
	 * Runs on woocommerce_cart_collaterals before WooCommerce prints the totals.
	 */
	public function guest_totals(): void {
		if ( $this->state->visitor_sees_prices() ) {
			return;
		}
		remove_action( 'woocommerce_cart_collaterals', 'woocommerce_cart_totals', 10 );
		$reason = $this->state->visitor_reason();
		$links  = sprintf(
			'<p><a class="button alt wc-forward" href="%s">%s</a></p>',
			esc_url( wc_get_checkout_url() ),
			esc_html__( 'Send inquiry', 'linker-commerce' )
		);
		if ( CommerceState::LOGIN === $reason ) {
			$text   = esc_html__( 'You can send this solution draft without an account. Net prices are available after account approval.', 'linker-commerce' );
			$links .= sprintf(
				'<p><a href="%s">%s</a></p>',
				esc_url( AuthTemplates::register_url() ),
				esc_html__( 'No account yet? Register', 'linker-commerce' )
			);
		} elseif ( CommerceState::APPROVAL === $reason ) {
			$text = esc_html__( 'You can send this solution draft. Your account is under review; net prices appear after approval.', 'linker-commerce' );
		} else {
			$text = esc_html__( 'You can send this solution draft. Net prices are not available for your account.', 'linker-commerce' );
		}
		printf( '<div class="cart_totals linker-login-box"><p>%s</p>%s</div>', $text, $links ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- both parts escaped above.
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
			if ( $product instanceof WC_Product && null !== $this->state->reason( $product, CommerceState::CARD ) ) {
				return true;
			}
		}
		return false;
	}
}
