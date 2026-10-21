<?php
/**
 * Public native Woo draft transports, including direct HTTP and Store API.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

use WP_Error;
use WP_REST_Request;

/** Native Woo still validates products, stock, permissions and cart nonces. */
final class Draft {
	/**
	 * Current native operation.
	 *
	 * @var array<string,mixed>|null
	 */
	private ?array $permit = null;
	/**
	 * Early session hydration refusal.
	 *
	 * @var WP_Error|null
	 */
	private ?WP_Error $failure = null;

	/** Start after Woo loaded its session, immediately before its form handlers. */
	public function register(): void {
		add_action( 'wp_loaded', array( $this, 'native' ), 19 );
		add_action( 'woocommerce_load_cart_from_session', array( $this, 'reorder' ), 1 );
		add_filter( 'rest_dispatch_request', array( $this, 'rest' ), 10, 4 );
		add_action( 'shutdown', array( $this, 'complete' ) );
		add_action( 'woocommerce_before_add_to_cart_button', array( $this, 'fields' ) );
		add_action( 'woocommerce_cart_actions', array( $this, 'fields' ) );
	}

	/** Native Woo form fields, appended within its existing form. */
	public function fields(): void {
		// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- FormFields escapes variables.
		echo FormFields::render( 'draft_write' );
	}

	/** Direct GET/POST/wc-ajax transports cannot bypass admission by skipping the UI. */
	public function native(): void {
		if ( ! Business::enabled() ) {
			return;
		}
		// phpcs:ignore WordPress.Security.NonceVerification -- decision() verifies mutation nonces before the gate; Woo repeats them.
		$post = array_merge( wp_unslash( $_GET ), wp_unslash( $_POST ) );
		// The retired calculator is a POST-only native command, not a read query.
		if ( ! isset( $_POST['calc_shipping'] ) ) { // phpcs:ignore WordPress.Security.NonceVerification.Missing -- Presence only; no native write is allowed by this branch.
			unset( $post['calc_shipping'] );
		}
		$result = $this->failure ?? $this->decision( $post );
		if ( ! is_wp_error( $result ) ) {
			// Woo's native remove/restore dispatcher reads these from GET. A
			// protected same-origin POST avoids putting proof credentials in URLs.
			foreach ( array( 'remove_item', 'undo_item', 'remove_coupon' ) as $key ) {
				if ( isset( $post[ $key ] ) && is_string( $post[ $key ] ) ) {
					$_GET[ $key ] = wp_slash( $post[ $key ] );
				}
			}
			return;
		}
		if ( wp_doing_ajax() || isset( $post['wc-ajax'] ) ) {
			wp_send_json(
				array(
					'error'   => true,
					'message' => $result->get_error_message(),
				),
				400
			);
		}
		wc_add_notice( $result->get_error_message(), 'error' );
		wp_safe_redirect( wc_get_cart_url() );
		exit;
	}

	/** Reorder hydration happens before wp_loaded 19; protect it at its own native boundary. */
	public function reorder(): void {
		if ( ! Business::enabled() ) {
			return; }
		// phpcs:ignore WordPress.Security.NonceVerification -- Native nonce and order capability checked by decision().
		$post = array_merge( wp_unslash( $_GET ), wp_unslash( $_POST ) );
		if ( ! isset( $post['order_again'] ) ) {
			return; }
		$result = $this->decision( $post );
		if ( is_wp_error( $result ) ) {
			$this->failure = $result;
			unset( $_GET['order_again'] );
		} elseif ( is_scalar( $post['order_again'] ) ) {
			$_GET['order_again'] = (string) absint( $post['order_again'] );
			$_GET['_wpnonce']    = isset( $post['_wpnonce'] ) && is_string( $post['_wpnonce'] ) ? wp_slash( $post['_wpnonce'] ) : '';
		}
	}

	/**
	 * Server-native allowlist; no request body becomes an arbitrary permission.
	 *
	 * @param array<array-key,mixed> $post Current transport, unslashed, including malformed numeric keys.
	 * @return true|WP_Error Allowed or explicit refusal.
	 */
	public function decision( array $post ): true|WP_Error {
		if ( 'enforce' === Configuration::active_mode() && isset( $post['calc_shipping'] ) && ! wc_shipping_enabled() ) {
			return new WP_Error( 'linker_shipping_disabled', __( 'Please use the inquiry form to send your inquiry.', 'linker-commerce' ) );
		}
		if ( null !== $this->permit ) {
			return true; }
		$commands = array_intersect( array_keys( $post ), array( 'add-to-cart', 'remove_item', 'undo_item', 'remove_coupon', 'apply_coupon', 'update_cart', 'linker_solution_to_draft', 'order_again' ) );
		if ( array() === $commands && ! in_array( $post['wc-ajax'] ?? '', array( 'add_to_cart', 'remove_from_cart', 'apply_coupon', 'remove_coupon', 'update_shipping_method', 'update_order_review' ), true ) ) {
			return true;
		}
		$payload = array();
		foreach ( array( 'wc-ajax', 'cart_item_key', 'shipping_method', 'coupon', 'add-to-cart', 'product_id', 'quantity', 'variation_id', 'variation', 'remove_item', 'undo_item', 'remove_coupon', 'apply_coupon', 'coupon_code', 'update_cart', 'cart', 'order_again', 'linker_solution_to_draft' ) as $key ) {
			if ( isset( $post[ $key ] ) ) {
				$payload[ $key ] = $post[ $key ];
			}
		}
		foreach ( $post as $key => $value ) {
			if ( is_string( $key ) && str_starts_with( $key, 'attribute_' ) && is_string( $value ) ) {
				$payload[ $key ] = $value; }
		}
		if ( array() === $payload || ! Business::enabled() ) {
			return true;
		}
		$cart_action = array_intersect( array_keys( $payload ), array( 'remove_item', 'undo_item', 'remove_coupon', 'apply_coupon', 'update_cart' ) );
		if ( array() !== $cart_action ) {
			$nonce = $post['woocommerce-cart-nonce'] ?? ( $post['_wpnonce'] ?? '' );
			if ( ! is_string( $nonce ) || ! wp_verify_nonce( $nonce, 'woocommerce-cart' ) ) {
				return new WP_Error( 'linker_draft_nonce', __( 'Please refresh your solution draft and try again.', 'linker-commerce' ) );
			}
		}
		if ( isset( $payload['linker_solution_to_draft'] ) ) {
			$id    = absint( $payload['linker_solution_to_draft'] );
			$nonce = $post['_wpnonce'] ?? '';
			if ( $id < 1 || get_post_type( $id ) !== 'linker_solution' || (int) get_post_field( 'post_author', $id ) !== get_current_user_id() || ! is_user_logged_in() || ! is_string( $nonce ) || ! wp_verify_nonce( $nonce, 'linker_solution_to_draft_' . $id ) ) {
				return new WP_Error( 'linker_draft_permission', __( 'Please sign in to use your saved solution.', 'linker-commerce' ) );
			}
		}
		if ( isset( $payload['order_again'] ) ) {
			$id    = absint( $payload['order_again'] );
			$nonce = $post['_wpnonce'] ?? '';
			// phpcs:ignore WordPress.WP.Capabilities.Unknown -- Woo's native order_again meta capability is mapped by wc_customer_has_capability().
			if ( ! is_user_logged_in() || ! current_user_can( 'order_again', $id ) || ! is_string( $nonce ) || ! wp_verify_nonce( $nonce, 'woocommerce-order_again' ) ) {
				return new WP_Error( 'linker_draft_permission', __( 'Please sign in to use your saved solution.', 'linker-commerce' ) );
			}
		}

		$transport = array(
			'linker_request_id' => $post['linker_request_id'] ?? '',
			'linker_proof'      => $post['linker_proof'] ?? '',
		);
		$permit    = Operation::begin( 'draft_write', $transport, $payload );
		if ( is_wp_error( $permit ) ) {
			return $permit;
		}
		$this->permit = $permit;
		return true;
	}

	/**
	 * REST dispatch runs after WordPress validated route arguments and permissions.
	 * Batch subrequests repeat native permissions; the outer gate never grants them.
	 *
	 * @param mixed               $result Earlier override.
	 * @param WP_REST_Request     $request Native request.
	 * @param string              $route Matched route.
	 * @param array<string,mixed> $handler Native callback and permission handler.
	 * @return mixed Native reply or refusal.
	 */
	public function rest( mixed $result, WP_REST_Request $request, string $route, array $handler ): mixed {
		unset( $route );
		if ( null !== $result || ! Business::enabled() || in_array( $request->get_method(), array( 'GET', 'HEAD', 'OPTIONS' ), true ) || ! preg_match( '#^/wc/store/v[0-9]+/cart(?:/.*)?$#i', $request->get_route() ) ) {
			return $result;
		}
		$params  = $request->get_params();
		$payload = $params;
		foreach ( array( 'linker_request_id', 'linker_proof', '_wpnonce', '_locale', 'rest_route' ) as $key ) {
			unset( $payload[ $key ] );
		}
		$payload['route'] = $request->get_route();
		$permit           = Operation::begin( 'draft_write', $params, $payload );
		if ( is_wp_error( $permit ) ) {
			return $permit;
		}
		$reply = call_user_func( $handler['callback'], $request );
		if ( ! is_wp_error( $reply ) ) {
			Operation::finish( $permit );
		}
		return $reply;
	}

	/** Complete only a native dispatch seen by this request. */
	public function complete(): void {
		if ( null !== $this->permit ) {
			Operation::finish( $this->permit );
			$this->permit = null;
		}
	}
}
