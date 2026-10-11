<?php
/**
 * The Proforma request page and its confirmation.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry;

use Linker\Commerce\Registration\Approval;
use WC_Order;

/**
 * The checkout page as the Proforma request page: one way to send (the
 * ProformaGateway), the reply promise above the button and on the
 * confirmation, and no payment method on the stored inquiry. An account
 * without approval (ticket 73) gets no gateway at all — the page's gate is the
 * view, this is the send.
 */
final class Checkout {

	/**
	 * Sets up the page.
	 *
	 * @param Approval $approval The account approval rule.
	 */
	public function __construct( private readonly Approval $approval = new Approval() ) {}

	/**
	 * Only the Proforma gateway is offered, and only to accounts that may send;
	 * runs on woocommerce_available_payment_gateways.
	 *
	 * @param array<string, mixed> $gateways Available gateways by id.
	 * @return array<string, mixed>
	 */
	public function gateways( array $gateways ): array {
		$user_id = get_current_user_id();
		if ( $user_id > 0 && ! $this->approval->sees_prices( $user_id ) ) {
			return array();
		}
		return isset( $gateways[ ProformaGateway::ID ] ) ? array( ProformaGateway::ID => $gateways[ ProformaGateway::ID ] ) : array();
	}

	/**
	 * An inquiry has no payment method: the title stays empty, so no page or
	 * email prints a "payment method" line. Runs on woocommerce_checkout_create_order.
	 *
	 * @param WC_Order $order Order being created.
	 */
	public function without_payment_method_title( WC_Order $order ): void {
		$order->set_payment_method_title( '' );
	}

	/**
	 * The reply promise above the send button (owner ruling 2026-10-09: an answer
	 * within one business day). Runs on woocommerce_review_order_before_submit.
	 */
	public function reply_promise(): void {
		printf( '<p class="linker-reply-promise">%s</p>', esc_html__( 'We reply within one business day.', 'linker-commerce' ) );
	}

	/**
	 * A hidden "lang" field in the checkout form. The form submits by AJAX to
	 * ?wc-ajax=checkout (WooCommerce defines DOING_AJAX there), an address
	 * without the language's URL prefix, so Polylang's ajax branch reads the
	 * language from the request instead (src/frontend/choose-lang.php); without
	 * this field a German inquiry is recorded in English. Runs on
	 * woocommerce_after_order_notes.
	 */
	public function language_field(): void {
		$language = function_exists( 'pll_current_language' ) ? pll_current_language( 'slug' ) : false;
		if ( false !== $language ) {
			printf( '<input type="hidden" name="lang" value="%s" />', esc_attr( $language ) );
		}
	}

	/**
	 * What happens next, on the confirmation page; runs on woocommerce_thankyou_linker_proforma.
	 */
	public function next_steps(): void {
		printf(
			'<p class="linker-next-steps">%1$s</p><p class="linker-next-steps">%2$s</p>',
			esc_html__( 'We reply within one business day.', 'linker-commerce' ),
			esc_html__( 'Your Proforma invoice will be in your account under Inquiries, and we will send you a link by email.', 'linker-commerce' )
		);
	}

	/**
	 * The confirmation of a German inquiry is the German request page's: the
	 * checkout submits by AJAX whose address names no language, so WooCommerce
	 * builds the confirmation URL on the English page. Runs on
	 * woocommerce_get_checkout_order_received_url.
	 *
	 * @param string   $url   The confirmation URL.
	 * @param WC_Order $order The inquiry.
	 * @return string
	 */
	public function received_url( string $url, WC_Order $order ): string {
		if ( ! str_starts_with( OrderLocale::of( $order ), 'de' ) || ! function_exists( 'pll_get_post' ) ) {
			return $url;
		}
		$english = (string) get_permalink( (int) get_option( 'woocommerce_checkout_page_id' ) );
		$german  = (int) pll_get_post( (int) get_option( 'woocommerce_checkout_page_id' ), 'de' );
		if ( '' === $english || 0 === $german || ! str_starts_with( $url, $english ) ) {
			return $url;
		}
		return substr_replace( $url, (string) get_permalink( $german ), 0, strlen( $english ) );
	}
}
