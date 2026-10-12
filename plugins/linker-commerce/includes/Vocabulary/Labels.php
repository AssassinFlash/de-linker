<?php
/**
 * Buttons and page titles in the site's words.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Vocabulary;

use WC_Product;

/**
 * The texts WooCommerce passes through filters of their own: the product
 * button, the send button, the confirmation, the login request on the Proforma
 * request page, the privacy text, and the titles of the solution draft and
 * Proforma request pages (docs/specs/11-commerce.md, journey steps 3 and 4).
 */
final class Labels {

	/**
	 * "Add to solution draft" on a product a customer can add; WooCommerce's
	 * text otherwise (e.g. "Read more" for a product out of stock).
	 *
	 * @param string          $text    WooCommerce's text.
	 * @param WC_Product|null $product Product.
	 */
	public function add_to_draft( string $text, $product = null ): string {
		if ( $product instanceof WC_Product && ! ( $product->is_purchasable() && $product->is_in_stock() && $product->is_type( array( 'simple', 'variation' ) ) ) ) {
			return $text;
		}
		return __( 'Add to solution draft', 'linker-commerce' );
	}

	/**
	 * The send button of the Proforma request page.
	 */
	public function send_inquiry(): string {
		return __( 'Request Proforma', 'linker-commerce' );
	}

	/**
	 * The first line of the confirmation page.
	 */
	public function inquiry_received(): string {
		return __( 'Thank you. Your inquiry has been received.', 'linker-commerce' );
	}

	/**
	 * What a visitor who is not logged in reads on the Proforma request page.
	 */
	public function log_in_to_send(): string {
		return __( 'Please log in to request a Proforma invoice. No account yet? Register on the account page.', 'linker-commerce' );
	}

	/**
	 * The privacy texts under the send and register buttons, in the visitor's
	 * language (WooCommerce stores them as settings, in one language).
	 *
	 * @param string $text WooCommerce's text (from its settings).
	 * @param string $type "checkout" or "registration".
	 */
	public function privacy_text( string $text, string $type ): string {
		if ( 'checkout' === $type ) {
			return __( 'We use your personal data to process your inquiry and for the other purposes described in our [privacy_policy].', 'linker-commerce' );
		}
		if ( 'registration' === $type ) {
			return __( 'We use your personal data to manage your account and for the other purposes described in our [privacy_policy].', 'linker-commerce' );
		}
		return $text;
	}

	/**
	 * Titles of the solution draft and Proforma request pages; runs on the_title
	 * before WooCommerce sets endpoint titles.
	 *
	 * @param string $title   Title.
	 * @param int    $post_id Post.
	 */
	public function page_title( string $title, $post_id = 0 ): string {
		return $this->title_of( (int) $post_id ) ?? $title;
	}

	/**
	 * The same titles in the browser tab.
	 *
	 * @param array<string, string> $parts Parts of the document title.
	 * @return array<string, string>
	 */
	public function document_title( array $parts ): array {
		// On an endpoint (the confirmation) WooCommerce's own title stays.
		if ( is_page() && ! is_wc_endpoint_url() ) {
			$title = $this->title_of( (int) get_queried_object_id() );
			if ( null !== $title ) {
				$parts['title'] = $title;
			}
		}
		return $parts;
	}

	/**
	 * The same titles in the breadcrumb: on an endpoint (the confirmation)
	 * WooCommerce takes the page's stored title for its crumb, not the_title.
	 *
	 * @param array<int, array{0: string, 1?: string}> $crumbs Crumbs: name and address.
	 * @return array<int, array{0: string, 1?: string}>
	 */
	public function breadcrumb( array $crumbs ): array {
		foreach ( array( wc_get_page_id( 'cart' ), wc_get_page_id( 'checkout' ) ) as $page_id ) {
			$url = get_permalink( $page_id );
			foreach ( $crumbs as $index => $crumb ) {
				if ( false !== $url && ( $crumb[1] ?? '' ) === $url ) {
					$crumbs[ $index ][0] = (string) $this->title_of( $page_id );
				}
			}
		}
		return $crumbs;
	}

	/**
	 * Title of a WooCommerce page this plugin names, or null.
	 *
	 * @param int $post_id Post.
	 */
	private function title_of( int $post_id ): ?string {
		if ( $post_id <= 0 ) {
			return null;
		}
		if ( wc_get_page_id( 'cart' ) === $post_id ) {
			return __( 'Solution draft', 'linker-commerce' );
		}
		if ( wc_get_page_id( 'checkout' ) === $post_id ) {
			return __( 'Proforma request', 'linker-commerce' );
		}
		return null;
	}

	/**
	 * The heading of the solution draft.
	 *
	 * The cart surface prints "Shopping cart" on woocommerce_before_cart at
	 * priority 1, and it registers that callback on template_redirect, after
	 * this hook is added. Runs on the same action at priority 0, so it can
	 * take that callback off before it prints, then print the draft's name.
	 * Another page is left alone.
	 */
	public function draft_heading(): void {
		if ( ! function_exists( 'is_cart' ) || ! is_cart() ) {
			return;
		}
		if ( function_exists( 'remove_action' ) ) {
			remove_action( 'woocommerce_before_cart', 'tv_woo_b2b_cart_title', 1 );
		}
		echo '<h1 class="sf-cart-title">' . esc_html__( 'Solution draft', 'linker-commerce' ) . '</h1>';
	}
}
