<?php
/**
 * The Proforma request page and its confirmation.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry;

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
	 * The receipt's product links stay in the inquiry's own language.
	 *
	 * @param string                 $url Native product link.
	 * @param \WC_Order_Item_Product $item Order line.
	 * @param WC_Order               $order Inquiry.
	 */
	public function item_permalink( string $url, \WC_Order_Item_Product $item, WC_Order $order ): string {
		if ( ! function_exists( 'pll_get_post' ) ) {
			return $url;
		}
		$twin = (int) pll_get_post( $item->get_product_id(), str_starts_with( OrderLocale::of( $order ), 'de' ) ? 'de' : 'en' );
		return $twin > 0 ? (string) get_permalink( $twin ) : $url;
	}

	/**
	 * Return an invalid submission to its own language's request page.
	 *
	 * @param string $locale Form locale.
	 */
	public static function request_url( string $locale ): string {
		$id = (int) get_option( 'woocommerce_checkout_page_id' );
		if ( function_exists( 'pll_get_post' ) ) {
			$twin = (int) pll_get_post( $id, str_starts_with( $locale, 'de' ) ? 'de' : 'en' );
			$id   = $twin > 0 ? $twin : $id;
		}
		return (string) get_permalink( $id );
	}


	/**
	 * Keep Woo's checkout error notice beside the invalid field on mobile,
	 * without its one-second page-scroll animation. Validation and notice
	 * lifecycle stay Woo's own; desktop retains the original scroll handler.
	 */
	public function feedback(): void {
		if ( ! is_checkout() || is_wc_endpoint_url( 'order-received' ) ) {
			return;
		}
		wp_add_inline_script(
			'wc-checkout',
			<<<'JS'
jQuery(function ($) {
	const nativeScroll = $.scroll_to_notices;
	$.scroll_to_notices = function (notice) {
		const form = document.querySelector('#tv-woo-b2b-checkout form.checkout');
		if (!form || !window.matchMedia('(max-width: 639px)').matches) {
			if (nativeScroll) nativeScroll(notice);
			return;
		}
		const row = form.querySelector('.woocommerce-invalid');
		if (row && notice && notice.length) {
			row.appendChild(notice[0]);
			notice.find('.woocommerce-error').removeAttr('tabindex');
			const input = row.querySelector('input, select, textarea');
			if (input) input.focus({ preventScroll: true });
		}
	};
});
JS
		);
	}

	/**
	 * Woo review fragments render outside the page URL. Read the same hidden
	 * language field as the final checkout, after Woo verified its nonce, and
	 * switch through WordPress so Woo's and this plugin's translations agree.
	 * Runs on woocommerce_checkout_update_order_review.
	 *
	 * @param string $posted Serialized checkout fields.
	 */
	public function review_language( string $posted ): void {
		parse_str( $posted, $values );
		$language = $values['lang'] ?? '';
		if ( ! is_string( $language ) || ! in_array( $language, array( 'en', 'de' ), true ) ) {
			return;
		}
		switch_to_locale( 'de' === $language ? 'de_DE_formal' : 'en_US' );
	}

	/**
	 * Only the Proforma gateway is offered, and only to accounts that may send;
	 * runs on woocommerce_available_payment_gateways.
	 *
	 * @param array<string, mixed> $gateways Available gateways by id.
	 * @return array<string, mixed>
	 */
	public function gateways( array $gateways ): array {
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
	 *
	 * @param int $order_id Received inquiry.
	 */
	public function next_steps( int $order_id = 0 ): void {
		$order = $order_id > 0 ? wc_get_order( $order_id ) : false;
		$guest = $order instanceof WC_Order && 0 === $order->get_customer_id();
		$html  = strtr(
			\Linker\Commerce\Presentation\Tokens::read( dirname( __DIR__, 2 ) . '/content/livecanvas/inquiry/received.html' ),
			array(
				'{{title}}'   => esc_html__( 'Inquiry received', 'linker-commerce' ),
				'{{promise}}' => esc_html__( 'We reply within one business day.', 'linker-commerce' ),
				'{{url}}'     => esc_url( $guest ? AccountLink::url( $order ) : wc_get_account_endpoint_url( 'orders' ) ),
				'{{action}}'  => $guest ? esc_html__( 'Create an account with this email', 'linker-commerce' ) : esc_html__( 'View inquiries', 'linker-commerce' ),
				'{{reply}}'   => esc_html__( 'The Linker team will reply to the email address you provided.', 'linker-commerce' ),
			)
		);
		echo wp_kses_post( $html );
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
	/**
	 * Protect Woo's alternate AJAX transport with the same public checks.
	 *
	 * @param array<string, mixed> $data   Native validated checkout fields.
	 * @param \WP_Error            $errors Native checkout errors.
	 */
	public function validate_public( array $data, \WP_Error $errors ): void {
		unset( $data );
     // phpcs:ignore WordPress.Security.NonceVerification.Missing -- Woo verified its checkout nonce before this hook.
		$post = wp_unslash( $_POST );
		if ( ! ( new PublicGuard() )->allows( $post ) ) {
			$errors->add( 'linker_inquiry_invalid', __( 'Please check your entries and send the form again.', 'linker-commerce' ) );
		}
	}
}
