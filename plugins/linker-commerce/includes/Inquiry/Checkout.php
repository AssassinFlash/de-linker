<?php
/**
 * The Proforma request page and its confirmation.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry;

use Linker\Commerce\Presentation\PageUrls;

use WC_Order;

/**
 * The public inquiry request, its confirmation, and retired checkout transports.
 */
final class Checkout {
	/**
	 * Consume a successful native product add before the inquiry is rendered.
	 * Leaving add-to-cart in the address repeats that command on reload and on
	 * Woo's native undo fragment refresh. Woo owns the add, notice and redirect;
	 * its checkout URL already resolves the current language.
	 *
	 * @param string|false $url An earlier explicit Woo redirect, or no destination.
	 */
	public function after_add_destination( string|false $url ): string {
		return $url ? $url : wc_get_checkout_url();
	}

	/**
	 * Blocks the unused Store API checkout before it can create a draft order.
	 * The Store API cart and product routes remain available.
	 *
	 * @param mixed            $result Earlier short-circuit result.
	 * @param \WP_REST_Server  $server REST server.
	 * @param \WP_REST_Request $request REST request.
	 * @return mixed
	 */
	public function block_store_checkout( $result, \WP_REST_Server $server, \WP_REST_Request $request ) {
		unset( $server );
		return preg_match( '#^/wc/store/v[0-9]+/checkout(?:/|$)#', $request->get_route() )
			? new \WP_Error( 'linker_inquiry_form_required', __( 'Please use the inquiry form to send your inquiry.', 'linker-commerce' ), array( 'status' => 403 ) )
			: $result;
	}


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
		$twin = PageUrls::twin( $item->get_product_id(), OrderLocale::of( $order ) );
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
			$twin = PageUrls::twin( $id, $locale );
			$id   = $twin > 0 ? $twin : $id;
		}
		return (string) get_permalink( $id );
	}

	/**
	 * Only the Proforma gateway is offered; inquiries are open to everyone. It
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
				'{{title}}'          => esc_html__( 'Inquiry received', 'linker-commerce' ),
				'{{promise}}'        => esc_html__( 'We reply within one business day.', 'linker-commerce' ),
				'{{url}}'            => esc_url( $guest ? AccountLink::url( $order ) : wc_get_account_endpoint_url( 'orders' ) ),
				'{{action}}'         => $guest ? esc_html__( 'Create an account with this email', 'linker-commerce' ) : esc_html__( 'View inquiries', 'linker-commerce' ),
				'{{reply}}'          => esc_html__( 'The Linker team will reply to the email address you provided.', 'linker-commerce' ),
				'{{receipt_notice}}' => $order instanceof WC_Order && 'daily_cap' === $order->get_meta( ReceiptLimit::SKIPPED_META )
					? esc_html__( 'We have not sent a confirmation email.', 'linker-commerce' ) : '',
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
		$german  = PageUrls::twin( (int) get_option( 'woocommerce_checkout_page_id' ), OrderLocale::of( $order ) );
		if ( '' === $english || 0 === $german || ! str_starts_with( $url, $english ) ) {
			return $url;
		}
		$translated = substr_replace( $url, (string) get_permalink( $german ), 0, strlen( $english ) );
		// The recorded language can differ from the staff/cron request language.
		// Reuse Woo's native URL seam after resolving that language's page.
		// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks.MissingHookComment -- Woo's native URL seam, after resolving the recorded language's page.
		return (string) apply_filters( 'woocommerce_get_endpoint_url', $translated, 'order-received', (string) $order->get_id(), (string) get_permalink( $german ) );
	}
	/**
	 * Retire Woo's native AJAX submission; public writes use the shared sender.
	 *
	 * @param array<string, mixed> $data   Native validated checkout fields.
	 * @param \WP_Error            $errors Native checkout errors.
	 */
	public function validate_public( array $data, \WP_Error $errors ): void {
		unset( $data );
		$errors->add( 'linker_inquiry_form_required', __( 'Please use the inquiry form to send your inquiry.', 'linker-commerce' ) );
	}
}
