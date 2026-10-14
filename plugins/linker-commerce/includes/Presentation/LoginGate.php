<?php
/**
 * The empty Proforma-request page.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

use Linker\Commerce\Registration\Approval;

/**
 * An empty Proforma request stays on the checkout page (200) and shows the
 * live login-gate copy instead of WooCommerce's redirect to the solution
 * draft. A default WooCommerce checkout (the local stack's empty install)
 * still redirects: this only applies to the site's checkout page — in any
 * language, so the decision reads the page's translation group (Polylang),
 * never a slug. An account without approval (ticket 73) reads its own gate:
 * pending names the review, restricted names the limit with the reason.
 */
final class LoginGate {

	/**
	 * Sets up the gate.
	 *
	 * @param Approval $approval The account approval rule.
	 */
	public function __construct( private readonly Approval $approval = new Approval() ) {}

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
	 * The login-gate (guest), approval-gate (account without approval) or
	 * empty-draft (approved customer) HTML.
	 */
	public function html(): string {
		$account  = wc_get_page_permalink( 'myaccount' );
		$products = (string) get_permalink( wc_get_page_id( 'shop' ) );
		$user_id  = get_current_user_id();
		if ( $user_id > 0 ) {
			$status = $this->approval->status( $user_id );
			if ( Approval::APPROVED !== $status ) {
				return $this->approval_gate( $status, $products );
			}
			return sprintf(
				'<section class="sf-checkout-empty" aria-label="%1$s"><h1>%2$s</h1><p>%3$s</p><div class="sf-checkout-empty__actions"><a class="sf-checkout-btn" href="%4$s">%5$s</a></div></section>',
				esc_attr__( 'Empty solution draft', 'linker-commerce' ),
				esc_html__( 'Nothing to submit yet.', 'linker-commerce' ),
				esc_html__( 'Your solution draft is empty. Add matched systems, then come back for your Proforma.', 'linker-commerce' ),
				esc_url( $products ),
				esc_html__( 'Browse products', 'linker-commerce' )
			);
		}
		return sprintf(
			'<section class="sf-checkout-empty" aria-label="%1$s"><h1>%2$s</h1>%3$s<h2>%4$s</h2><p>%5$s</p><div class="sf-checkout-empty__actions"><a class="sf-checkout-btn" href="%6$s">%7$s</a><a class="sf-checkout-btn sf-checkout-btn--ghost" href="%8$s">%9$s</a></div></section>',
			esc_attr__( 'Proforma request sign-in', 'linker-commerce' ),
			esc_html__( 'Get your Proforma', 'linker-commerce' ),
			$this->genie_pill(),
			esc_html__( 'Sign in to get your Proforma.', 'linker-commerce' ),
			esc_html__( 'The Proforma request is reserved for Linker partner accounts. Register, add your systems, and return here — VAT and delivery are ours to handle.', 'linker-commerce' ),
			esc_url( (string) $account ),
			esc_html__( 'Sign in or register', 'linker-commerce' ),
			esc_url( $products ),
			esc_html__( 'Browse products', 'linker-commerce' )
		);
	}

	/**
	 * The pending-review page, for the account page as well as the empty
	 * Proforma request. Both surfaces read this one markup.
	 *
	 * @param string $products The products page's address.
	 */
	public function pending_html( string $products ): string {
		return $this->approval_gate( Approval::PENDING, $products );
	}

	/**
	 * The gate of an account whose approval is pending or restricted: what the
	 * account keeps, what is paused, and the way back.
	 *
	 * @param string $status   The account's approval state.
	 * @param string $products The products page's address.
	 */
	private function approval_gate( string $status, string $products ): string {
		if ( Approval::RESTRICTED === $status ) {
			$reason = $this->approval->reason( get_current_user_id() );
			$why    = '' !== $reason
					? sprintf(
						'<p class="sf-checkout-empty__reason"><strong>%1$s</strong> %2$s</p>',
						esc_html__( 'Our reason:', 'linker-commerce' ),
						esc_html( $reason )
					)
				: '';
			return sprintf(
				'<section class="sf-checkout-empty" aria-label="%1$s"><h1>%2$s</h1><p>%3$s</p>%4$s<p>%5$s</p><div class="sf-checkout-empty__actions"><a class="sf-checkout-btn" href="%6$s">%7$s</a></div></section>',
				esc_attr__( 'Account with limited access', 'linker-commerce' ),
				esc_html__( 'Access currently limited', 'linker-commerce' ),
				esc_html__( 'Your partner account is limited for now: the products and your questions stay open, net prices and the Proforma request are paused.', 'linker-commerce' ),
				$why,
				esc_html__( 'Write to sales@de-linker.com and we will look at your account again.', 'linker-commerce' ),
				esc_url( $products ),
				esc_html__( 'Browse products', 'linker-commerce' )
			);
		}
		return sprintf(
			'<section class="sf-checkout-empty" aria-label="%1$s"><h1>%2$s</h1><p>%3$s</p><p>%4$s</p><div class="sf-checkout-empty__actions"><a class="sf-checkout-btn" href="%5$s">%6$s</a></div></section>',
			esc_attr__( 'Account under review', 'linker-commerce' ),
			esc_html__( 'Your account is under review', 'linker-commerce' ),
			esc_html__( 'We are reviewing your partner account. Net prices and the Proforma request open as soon as it is approved, and we will email you.', 'linker-commerce' ),
			esc_html__( 'Until then, browse the products and write to sales@de-linker.com with any question.', 'linker-commerce' ),
			esc_url( $products ),
			esc_html__( 'Browse products', 'linker-commerce' )
		);
	}

	/**
	 * The Genie entry on the empty Proforma request.
	 *
	 * The live page opened the assistant from a dark pill under the title
	 * (then named Advisor / Berater). The pill keeps that place and opens
	 * Genie, the name the site uses now. Without the dock script the same
	 * control is the Genie page, so the entry is not JavaScript-only.
	 */
	private function genie_pill(): string {
		$url = '';
		if ( function_exists( 'pll_current_language' ) && 'de' === pll_current_language() && function_exists( 'pll_get_post' ) ) {
			$page = get_page_by_path( 'genie' );
			if ( $page instanceof \WP_Post ) {
				$twin = (int) pll_get_post( (int) $page->ID, 'de' );
				$link = $twin > 0 ? get_permalink( $twin ) : false;
				if ( is_string( $link ) && '' !== $link ) {
					$url = $link;
				}
			}
		}
		if ( '' === $url ) {
			$url = home_url( '/genie/' );
		}
		$mark = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7.4 5v10.9a1.8 1.8 0 0 0 1.8 1.8H17"/><path d="M8.8 8.4C11.8 4.5 16.4 3.1 19.6 3.5"/><circle cx="20.7" cy="4.9" r="1.5" fill="currentColor" stroke="none"/></svg>';
		// aria-expanded declares the collapsed state up front: the dock's
		// shell() flips it to true only when it reports the panel open, so
		// the opener never claims an expansion that never happened.
		return sprintf(
			'<p class="sf-checkout-genie"><a class="sf-checkout-genie__pill" href="%1$s" data-linker-genie-open aria-expanded="false">%2$s<span>%3$s</span></a></p>',
			esc_url( $url ),
			$mark,
			esc_html__( 'Genie', 'linker-commerce' )
		);
	}

	/**
	 * Whether the current request is the site's checkout page or one of its
	 * translations: WooCommerce's checkout is a single (English) page whose
	 * translations — the German Proforma-Anfrage — must keep the same
	 * empty-draft behavior, so the check reads the translation group of the
	 * checkout page id instead of matching a slug.
	 */
	private function is_proforma_request(): bool {
		$checkout_id = (int) wc_get_page_id( 'checkout' );
		if ( $checkout_id <= 0 ) {
			return false;
		}
		$ids = array( $checkout_id );
		if ( function_exists( 'pll_get_post_translations' ) ) {
			foreach ( (array) pll_get_post_translations( $checkout_id ) as $translation ) {
				$ids[] = (int) $translation;
			}
		}
		return is_page( array_values( array_unique( $ids ) ) );
	}
}
