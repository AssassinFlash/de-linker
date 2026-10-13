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
				'<section class="sf-checkout-empty mx-auto max-w-xl rounded-xl border border-neutral-200 bg-white p-8" aria-label="%1$s"><h1 class="text-3xl font-bold tracking-tight text-[#15352f]">%2$s</h1><p class="mt-4 text-neutral-600">%3$s</p><div class="mt-6 flex flex-wrap gap-3"><a class="inline-flex min-h-11 items-center rounded-lg bg-[#0c7f73] px-5 font-bold text-white" href="%4$s">%5$s</a></div></section>',
				esc_attr__( 'Empty solution draft', 'linker-commerce' ),
				esc_html__( 'Nothing to submit yet.', 'linker-commerce' ),
				esc_html__( 'Your solution draft is empty. Add matched systems, then come back for your Proforma.', 'linker-commerce' ),
				esc_url( $products ),
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
					'<p class="mt-3 text-neutral-600"><strong>%1$s</strong> %2$s</p>',
					esc_html__( 'Our reason:', 'linker-commerce' ),
					esc_html( $reason )
				)
				: '';
			return sprintf(
				'<section class="sf-checkout-empty mx-auto max-w-xl rounded-xl border border-neutral-200 bg-white p-8" aria-label="%1$s"><h1 class="text-3xl font-bold tracking-tight text-[#15352f]">%2$s</h1><p class="mt-3 text-neutral-600">%3$s</p>%4$s<p class="mt-3 text-neutral-600">%5$s</p><div class="mt-6 flex flex-wrap gap-3"><a class="inline-flex min-h-11 items-center rounded-lg bg-[#0c7f73] px-5 font-bold text-white" href="%6$s">%7$s</a></div></section>',
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
			'<section class="sf-checkout-empty mx-auto max-w-xl rounded-xl border border-neutral-200 bg-white p-8" aria-label="%1$s"><h1 class="text-3xl font-bold tracking-tight text-[#15352f]">%2$s</h1><p class="mt-3 text-neutral-600">%3$s</p><p class="mt-3 text-neutral-600">%4$s</p><div class="mt-6 flex flex-wrap gap-3"><a class="inline-flex min-h-11 items-center rounded-lg bg-[#0c7f73] px-5 font-bold text-white" href="%5$s">%6$s</a></div></section>',
			esc_attr__( 'Account under review', 'linker-commerce' ),
			esc_html__( 'Your account is under review', 'linker-commerce' ),
			esc_html__( 'We are reviewing your partner account. Net prices and the Proforma request open as soon as it is approved, and we will email you.', 'linker-commerce' ),
			esc_html__( 'Until then, browse the products and write to sales@de-linker.com with any question.', 'linker-commerce' ),
			esc_url( $products ),
			esc_html__( 'Browse products', 'linker-commerce' )
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
