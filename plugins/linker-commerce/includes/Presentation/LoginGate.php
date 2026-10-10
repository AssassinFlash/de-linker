<?php
/**
 * The empty Proforma-request page.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

/**
 * An empty /proforma-request/ stays on that URL (200) and shows the live
 * login-gate copy instead of WooCommerce's redirect to the solution draft.
 * A default WooCommerce checkout (the local stack's empty install) still
 * redirects: this only applies to the site's Proforma-request slug.
 */
final class LoginGate {

	/**
	 * Checkout page slug of the Proforma request (docs/specs/11-commerce.md).
	 */
	public const SLUG = 'proforma-request';

	/**
	 * Stops WooCommerce sending an empty Proforma request to the cart.
	 */
	public function register(): void {
		add_filter( 'woocommerce_checkout_redirect_empty_cart', array( $this, 'keep_empty_checkout' ) );
	}

	/**
	 * Keep the empty Proforma request on its own page; leave other checkouts alone.
	 *
	 * @param bool $redirect WooCommerce's default.
	 */
	public function keep_empty_checkout( bool $redirect ): bool {
		return $this->is_proforma_request() ? false : $redirect;
	}

	/**
	 * The login-gate (guest) or empty-draft (customer) HTML.
	 */
	public function html(): string {
		$account  = wc_get_page_permalink( 'myaccount' );
		$products = get_permalink( wc_get_page_id( 'shop' ) );
		if ( is_user_logged_in() ) {
			return sprintf(
				'<section class="sf-checkout-empty mx-auto max-w-xl rounded-xl border border-neutral-200 bg-white p-8" aria-label="%1$s"><h1 class="text-3xl font-bold tracking-tight text-[#15352f]">%2$s</h1><p class="mt-4 text-neutral-600">%3$s</p><div class="mt-6 flex flex-wrap gap-3"><a class="inline-flex min-h-11 items-center rounded-lg bg-[#0c7f73] px-5 font-bold text-white" href="%4$s">%5$s</a></div></section>',
				esc_attr__( 'Empty solution draft', 'linker-commerce' ),
				esc_html__( 'Nothing to submit yet.', 'linker-commerce' ),
				esc_html__( 'Your solution draft is empty. Add matched systems, then come back for your Proforma.', 'linker-commerce' ),
				esc_url( (string) $products ),
				esc_html__( 'Browse products', 'linker-commerce' )
			);
		}
		return sprintf(
			'<section class="sf-checkout-empty mx-auto max-w-xl rounded-xl border border-neutral-200 bg-white p-8" aria-label="%1$s"><h1 class="text-3xl font-bold tracking-tight text-[#15352f]">%2$s</h1><p class="mt-3 text-neutral-600">%3$s</p><p class="mt-3 text-neutral-600">%4$s</p><div class="mt-6 flex flex-wrap gap-3"><a class="inline-flex min-h-11 items-center rounded-lg bg-[#0c7f73] px-5 font-bold text-white" href="%5$s">%6$s</a><a class="inline-flex min-h-11 items-center rounded-lg border border-[#0c7f73] px-5 font-bold text-[#0c7f73]" href="%7$s">%8$s</a></div></section>',
			esc_attr__( 'Proforma request sign-in', 'linker-commerce' ),
			esc_html__( 'Get your Proforma', 'linker-commerce' ),
			esc_html__( 'Sign in with your partner account, add matched systems, and your Proforma is one step away.', 'linker-commerce' ),
			esc_html__( 'The Proforma request is reserved for Linker partner accounts. Register, add your systems, and return here — VAT and delivery are ours to handle.', 'linker-commerce' ),
			esc_url( (string) $account ),
			esc_html__( 'Sign in or register', 'linker-commerce' ),
			esc_url( (string) $products ),
			esc_html__( 'Browse products', 'linker-commerce' )
		);
	}

	/**
	 * Whether the current request is the site's Proforma-request checkout.
	 */
	private function is_proforma_request(): bool {
		$page = get_post( wc_get_page_id( 'checkout' ) );
		return $page instanceof \WP_Post && self::SLUG === $page->post_name;
	}
}
