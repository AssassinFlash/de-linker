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
 *
 * Every gate is one card: a badge where a state is named, the heading, the
 * body and the actions (ticket #184, the owner-accepted prototype's
 * gates.html). The look lives in content/windpress/auth.css.
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
	 * empty-draft (approved customer) HTML. A guest's gate names the draft it
	 * has: with products in it the draft is the reason to sign in, without
	 * them the Proforma request itself is.
	 */
	public function html(): string {
		$user_id = get_current_user_id();
		if ( $user_id > 0 ) {
			$status = $this->approval->status( $user_id );
			if ( Approval::APPROVED !== $status ) {
				return $this->approval_gate( $status );
			}
			return $this->empty_draft_gate();
		}
		return $this->draft_empty() ? $this->proforma_gate() : $this->guest_draft_gate();
	}

	/**
	 * The pending-review page, for the account page as well as the empty
	 * Proforma request. Both surfaces read this one markup.
	 */
	public function pending_html(): string {
		return $this->approval_gate( Approval::PENDING );
	}

	/**
	 * The gate of an account whose approval is pending or restricted: what the
	 * account keeps, what is paused, and the way back.
	 *
	 * @param string $status The account's approval state.
	 */
	private function approval_gate( string $status ): string {
		$products = $this->products_url();
		if ( Approval::RESTRICTED === $status ) {
			$reason = $this->approval->reason( get_current_user_id() );
			return $this->card(
				esc_attr__( 'Account with limited access', 'linker-commerce' ),
				$this->badge( 'restricted', esc_html__( 'Access currently limited', 'linker-commerce' ) ),
				esc_html__( 'Access currently limited', 'linker-commerce' ),
				'',
				$this->reason_notice( $reason )
					. '<p>' . esc_html__( 'Your partner account is limited for now: the products and your questions stay open, net prices and the Proforma request are paused.', 'linker-commerce' ) . '</p>'
					. '<p>' . $this->mailto_link( esc_html__( 'Write to sales@de-linker.com and we will look at your account again.', 'linker-commerce' ) ) . '</p>',
				$this->action( $products, esc_html__( 'Browse products', 'linker-commerce' ), 'primary' )
			);
		}
		return $this->card(
			esc_attr__( 'Account under review', 'linker-commerce' ),
			$this->badge( 'pending', esc_html__( 'Under review', 'linker-commerce' ) ),
			esc_html__( 'Your account is under review', 'linker-commerce' ),
			'',
			'<p>' . esc_html__( 'We are reviewing your partner account. Net prices and the Proforma request open as soon as it is approved, and we will email you.', 'linker-commerce' ) . '</p>'
				. '<p>' . $this->mailto_link( esc_html__( 'Until then, browse the products and write to sales@de-linker.com with any question.', 'linker-commerce' ) ) . '</p>',
			$this->action( $products, esc_html__( 'Browse products', 'linker-commerce' ), 'primary' )
		);
	}

	/**
	 * The team's mailbox inside an already-escaped sentence becomes the mailto
	 * link the prototype draws (gates.html wraps the same address). The
	 * sentence stays one translatable string; only the address is wrapped.
	 *
	 * @param string $sentence The escaped sentence.
	 */
	private function mailto_link( string $sentence ): string {
		return str_replace(
			'sales@de-linker.com',
			'<a href="mailto:sales@de-linker.com">sales@de-linker.com</a>',
			$sentence
		);
	}

	/**
	 * The approved customer whose draft is empty: nothing to send yet.
	 */
	private function empty_draft_gate(): string {
		return $this->card(
			esc_attr__( 'Empty solution draft', 'linker-commerce' ),
			'',
			esc_html__( 'Nothing to submit yet.', 'linker-commerce' ),
			'',
			'<p>' . esc_html__( 'Your solution draft is empty. Add matched systems, then come back for your Proforma.', 'linker-commerce' ) . '</p>',
			$this->action( $this->products_url(), esc_html__( 'Browse products', 'linker-commerce' ), 'primary' )
		);
	}

	/**
	 * The guest without a draft: what a Proforma request needs.
	 */
	private function proforma_gate(): string {
		return $this->card(
			esc_attr__( 'Proforma request sign-in', 'linker-commerce' ),
			'',
			esc_html__( 'Get your Proforma', 'linker-commerce' ),
			'<p class="linker-gate-sub">' . esc_html__( 'Sign in to get your Proforma.', 'linker-commerce' ) . '</p>' . $this->genie_pill(),
			'<p>' . esc_html__( 'The Proforma request is reserved for Linker partner accounts. Register, add your systems, and return here — VAT and delivery are ours to handle.', 'linker-commerce' ) . '</p>',
			$this->action( (string) wc_get_page_permalink( 'myaccount' ), esc_html__( 'Sign in or register', 'linker-commerce' ), 'primary' )
				. $this->action( $this->products_url(), esc_html__( 'Browse products', 'linker-commerce' ), 'ghost' )
		);
	}

	/**
	 * The guest whose draft holds products: the draft waits for the account.
	 */
	private function guest_draft_gate(): string {
		return $this->card(
			esc_attr__( 'Proforma request sign-in', 'linker-commerce' ),
			'',
			esc_html__( 'Sign in to request your Proforma', 'linker-commerce' ),
			'',
			'<p>' . esc_html__( 'Your solution draft is saved. Log in with your partner account to send the inquiry — no account yet? Register on the account page; the draft waits for you.', 'linker-commerce' ) . '</p>',
			$this->action( (string) wc_get_page_permalink( 'myaccount' ), esc_html__( 'Sign in or register', 'linker-commerce' ), 'primary' )
				. $this->action( $this->products_url(), esc_html__( 'Browse products', 'linker-commerce' ), 'ghost' ),
			'<p class="linker-gate-links">'
				/* phpcs:ignore WordPress.WP.I18n.TextDomainMismatch -- Woo native label. */
				. '<a href="' . esc_url( wp_lostpassword_url() ) . '">' . esc_html__( 'Lost your password?', 'woocommerce' ) . '</a></p>'
		);
	}

	/**
	 * One gate card: the badge (when the state has one), the heading, the body
	 * paragraphs and the actions. Every part is already escaped.
	 *
	 * @param string $label   The card's accessible name.
	 * @param string $badge   The state badge, or an empty string.
	 * @param string $title   The card's heading, escaped.
	 * @param string $meta    Any markup directly under the heading, escaped.
	 * @param string $body    The body paragraphs, escaped.
	 * @param string $actions The action links, escaped.
	 * @param string $links   Any links under the actions, escaped.
	 */
	private function card( string $label, string $badge, string $title, string $meta, string $body, string $actions, string $links = '' ): string {
		return sprintf(
			'<div class="linker-gate-col"><section class="linker-gate" aria-label="%1$s">%2$s<h1>%3$s</h1>%4$s<div class="linker-gate-body">%5$s</div><div class="linker-gate-actions">%6$s</div>%7$s</section></div>',
			$label,
			$badge,
			$title,
			$meta,
			$body,
			$actions,
			$links
		);
	}

	/**
	 * A state badge with its own mark.
	 *
	 * @param string $state pending or restricted.
	 * @param string $text  The badge's word, escaped.
	 */
	private function badge( string $state, string $text ): string {
		$clock = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7.6V12l3.2 2"/></svg>';
		$shield = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3.5 19 6v5.6c0 4.2-2.9 8-7 9.4-4.1-1.4-7-5.2-7-9.4V6Z"/><path d="M12 9.2v3.7"/><path d="M12 16.1h.01"/></svg>';
		return sprintf(
			'<span class="linker-gate-badge is-%1$s">%2$s<span>%3$s</span></span>',
			esc_attr( $state ),
			'restricted' === $state ? $shield : $clock,
			$text
		);
	}

	/**
	 * The restricted account's reason, as the card's info notice.
	 *
	 * @param string $reason The reason the team stored.
	 */
	private function reason_notice( string $reason ): string {
		if ( '' === $reason ) {
			return '';
		}
		$icon = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="M12 16.5V11"/><path d="M12 7.6h.01"/></svg>';
		return sprintf(
			'<div class="notice notice-info" role="status">%1$s<div><strong>%2$s</strong> %3$s</div></div>',
			$icon,
			esc_html__( 'Our reason:', 'linker-commerce' ),
			esc_html( $reason )
		);
	}

	/**
	 * One action link.
	 *
	 * @param string $url   The target.
	 * @param string $label The link's word, escaped.
	 * @param string $kind  primary or ghost.
	 */
	private function action( string $url, string $label, string $kind ): string {
		return sprintf(
			'<a class="linker-gate-btn is-%1$s" href="%2$s">%3$s</a>',
			esc_attr( $kind ),
			esc_url( $url ),
			$label
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
			'<p class="linker-gate-genie"><a class="linker-gate-genie-pill" href="%1$s" data-linker-genie-open aria-expanded="false">%2$s<span>%3$s</span></a></p>',
			esc_url( $url ),
			$mark,
			esc_html__( 'Genie', 'linker-commerce' )
		);
	}

	/**
	 * The products page's address, wherever the gate is shown.
	 */
	private function products_url(): string {
		return function_exists( 'wc_get_page_id' ) ? (string) get_permalink( (int) wc_get_page_id( 'shop' ) ) : '';
	}

	/**
	 * Whether the solution draft holds nothing.
	 */
	private function draft_empty(): bool {
		return function_exists( 'linker_commerce_draft_empty' ) ? (bool) linker_commerce_draft_empty() : true;
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
