<?php
/**
 * The inquiry page and its confirmation.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry;

use Linker\Commerce\Settings\Options;
use Automattic\WooCommerce\Internal\Utilities\Users;
use Linker\Commerce\Planning\InquiryTransfer;
use Linker\Commerce\Presentation\PageUrls;

use WC_Order;

/**
 * The public inquiry request, its confirmation, and retired checkout transports.
 */
final class Checkout {
	/**
	 * Retired checkout must stop before Woo mutates customer/session totals.
	 * Woo catches this exception and renders its native failure response.
	 *
	 * @throws \RuntimeException This site accepts inquiries through its inquiry form.
	 */
	public function block_native_checkout(): void {
		throw new \RuntimeException( esc_html__( 'Please use the inquiry form to send your inquiry.', 'linker-commerce' ) );
	}

	/**
	 * Consume a successful native product add before showing its destination.
	 * Leaving add-to-cart in the address repeats that command on reload and on
	 * Woo's native undo fragment refresh. Woo owns the cart and checkout permalinks in the current language.
	 *
	 * @param string|false $url An earlier explicit Woo redirect, or no destination.
	 */
	public function after_add_destination( string|false $url ): string {
		if ( $url ) {
			return $url;
		}
		$draft = wc_get_cart_url();
		// phpcs:ignore WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- Compare paths only; the destination always comes from Woo.
		$path = wp_parse_url( wp_unslash( $_SERVER['REQUEST_URI'] ?? '' ), PHP_URL_PATH );
		return wp_parse_url( $draft, PHP_URL_PATH ) === $path ? $draft : wc_get_checkout_url();
	}

	/**
	 * Read the draft and inquiry after the customer's pending quantity change reaches Woo.
	 *
	 * @param string[] $paths Paths already excluded from WordPress speculative loading.
	 * @return string[]
	 */
	public function session_page_paths( array $paths ): array {
		$paths[] = wp_make_link_relative( wc_get_cart_url() );
		$paths[] = wp_make_link_relative( wc_get_checkout_url() );
		return $paths;
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
		return preg_match( '#^/wc/store/v[0-9]+/checkout(?:/|$)#i', $request->get_route() )
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
	 * Only the inquiry gateway is offered; inquiries are open to everyone. It
	 * runs on woocommerce_available_payment_gateways.
	 *
	 * @param array<string, mixed> $gateways Available gateways by id.
	 * @return array<string, mixed>
	 */
	public function gateways( array $gateways ): array {
		return isset( $gateways[ InquiryGateway::ID ] ) ? array( InquiryGateway::ID => $gateways[ InquiryGateway::ID ] ) : array();
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
	 * Show a project inquiry using Woo's receipt views and access rules.
	 *
	 * The project order already consumed its own lines, so the remaining
	 * solution draft stays available when its receipt is opened.
	 */
	public static function scoped_receipt(): ?string {
		$id = absint( get_query_var( 'order-received' ) );
		if ( 0 === $id ) {
			return null;
		}
		$order = wc_get_order( $id );
		if ( ! $order instanceof WC_Order || '' === $order->get_meta( InquiryTransfer::ORDER_META ) ) {
			return null;
		}
		return \WC_Shortcodes::shortcode_wrapper( array( self::class, 'render_scoped_receipt' ), array( 'order' => $order ) );
	}

	/**
	 * Render the selected order through Woo's receipt shortcode presentation.
	 *
	 * @param array{order:WC_Order} $attributes The stored project inquiry.
	 */
	public static function render_scoped_receipt( array $attributes ): void {
		$order = $attributes['order'];
		$key   = isset( $_GET['key'] ) && is_string( $_GET['key'] ) ? sanitize_text_field( wp_unslash( $_GET['key'] ) ) : ''; // phpcs:ignore WordPress.Security.NonceVerification.Recommended -- Woo receipt keys authenticate emailed links.
		// phpcs:disable WooCommerce.Commenting.CommentHooks.MissingHookComment,WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- WooCommerce's own receipt access filters.
		$key = (string) apply_filters( 'woocommerce_thankyou_order_key', $key );
		if ( ! hash_equals( $order->get_order_key(), $key ) ) {
			wc_get_template( 'checkout/thankyou.php', array( 'order' => false ) );
			return;
		}
		$verify_customer = apply_filters( 'woocommerce_order_received_verify_known_shoppers', true );
		// phpcs:enable WooCommerce.Commenting.CommentHooks.MissingHookComment,WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound
		$customer_id = $order->get_customer_id();
		if ( $verify_customer && $customer_id && get_current_user_id() !== $customer_id ) {
			wc_get_template( 'checkout/order-received.php', array( 'order' => false ) );
			wc_print_notice( __( 'Please log in to your account to view this inquiry.', 'linker-commerce' ), 'notice' );
			woocommerce_login_form( array( 'redirect' => $order->get_checkout_order_received_url() ) );
			return;
		}
		$nonce = filter_input( INPUT_POST, 'check_submission' );
		$email = is_string( $nonce ) && wp_verify_nonce( $nonce, 'wc_verify_email' )
			? sanitize_email( wp_unslash( (string) filter_input( INPUT_POST, 'email' ) ) )
			: null;
		if ( Users::should_user_verify_order_email( $order->get_id(), $email, 'order-received' ) ) {
			wc_get_template( 'checkout/order-received.php', array( 'order' => false ) );
			wc_get_template(
				'checkout/form-verify-email.php',
				array(
					'failed_submission' => ! empty( $_POST['email'] ), // phpcs:ignore WordPress.Security.NonceVerification.Missing -- Woo uses the presence for feedback only.
					'verify_url'        => $order->get_checkout_order_received_url(),
				)
			);
			return;
		}
		wc_get_template( 'checkout/thankyou.php', array( 'order' => $order ) );
	}

	/**
	 * What happens next, on the confirmation page; runs on woocommerce_thankyou_linker_inquiry.
	 *
	 * @param int $order_id Received inquiry.
	 */
	public function next_steps( int $order_id = 0 ): void {
		$order = $order_id > 0 ? wc_get_order( $order_id ) : false;
		if ( ! $order instanceof WC_Order ) {
			return;
		}
		$guest       = 0 === $order->get_customer_id();
		$individual  = 'individual' === $order->get_meta( \Linker\Commerce\Protection\Intake::LANE_META ) && \Linker\Commerce\Mail\NotificationHold::held( $order );
		$preliminary = '' !== $order->get_meta( \Linker\Commerce\Planning\Context::PROJECT_META );
		$html        = strtr(
			\Linker\Commerce\Presentation\Tokens::read( dirname( __DIR__, 2 ) . '/content/livecanvas/inquiry/received.html' ),
			array(
				/* translators: %s: inquiry number. */
				'{{number}}'         => esc_html( sprintf( __( 'Inquiry #%s', 'linker-commerce' ), $order->get_order_number() ) ),
				'{{next}}'           => esc_html__( 'Next steps', 'linker-commerce' ),
				'{{request_id}}'     => $preliminary ? esc_attr( (string) $order->get_meta( \Linker\Commerce\Protection\BusinessRecord::REQUEST ) ) : '',
				'{{title}}'          => $individual ? esc_html__( 'Inquiry saved for review', 'linker-commerce' ) : esc_html__( 'Inquiry received', 'linker-commerce' ),
				'{{promise}}'        => $individual ? esc_html( \Linker\Commerce\Protection\IntakeAdmin::saved_message( $order ) ) : esc_html__( 'We reply within one business day to the email address you provided.', 'linker-commerce' ),
				'{{url}}'            => esc_url( $guest ? AccountLink::url( $order ) : wc_get_account_endpoint_url( 'orders' ) ),
				'{{action}}'         => $guest ? esc_html__( 'Create an account with this email', 'linker-commerce' ) : esc_html__( 'View inquiries', 'linker-commerce' ),
				/* translators: %s: public team email address. */
				'{{receipt_notice}}' => $individual ? esc_html( sprintf( __( 'You can also email %s and quote this inquiry number.', 'linker-commerce' ), ( new Options() )->team_mailbox() ) ) : ( 'omitted' === ReceiptLimit::delivery_state( $order )
					? esc_html__( 'We have not sent a confirmation email.', 'linker-commerce' ) : '' ),
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
		// A guest checking their email on an English receipt must return to that same receipt.
		if ( function_exists( 'pll_current_language' ) && 'en' === pll_current_language() && (int) get_query_var( 'order-received' ) === $order->get_id() ) {
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
