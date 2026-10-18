<?php
/**
 * The pending account page and the restricted inquiry notice.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

use Linker\Commerce\Registration\Approval;

/** Pending account presentation and the native empty-checkout redirect rule. */
final class LoginGate {

	/**
	 * The public mailbox every gate names (the site's sales address, the same
	 * one the refusal notice and the contact form print).
	 */
	private const TEAM_ADDRESS = 'sales@de-linker.com';

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
	 * The pending-review page, for the account page as well as the empty
	 * Proforma request. Both surfaces read this one markup.
	 */
	public function pending_html(): string {
		return $this->approval_gate();
	}

	/**
	 * The pending account page; inquiries stay open during review.
	 */
	private function approval_gate(): string {
		$products = $this->products_url();

		return $this->card(
			esc_attr__( 'Account under review', 'linker-commerce' ),
			$this->badge( 'pending', esc_html__( 'Under review', 'linker-commerce' ) ),
			esc_html__( 'Your account is under review', 'linker-commerce' ),
			'',
			'<p>' . esc_html__( 'We are reviewing your partner account and will email you when it is approved. You can send inquiries now; approval opens net prices.', 'linker-commerce' ) . '</p>'
				. '<p>' . $this->mailto_sentence(
					/* translators: %s: the team's email address. */
					__( 'Until then, browse the products and write to %s with any question.', 'linker-commerce' )
				) . '</p>',
			$this->action( $products, esc_html__( 'Browse products', 'linker-commerce' ), 'primary' )
		);
	}

	/** A restricted account can still send; show the team's saved reason above the form. */
	public function restricted_notice(): string {
		if ( Approval::RESTRICTED !== $this->approval->status( get_current_user_id() ) ) {
			return '';
		}
		return strtr(
			Tokens::read( dirname( __DIR__, 2 ) . '/content/livecanvas/inquiry/restricted.html' ),
			array(
				'{{title}}'   => esc_html__( 'Access currently limited', 'linker-commerce' ),
				'{{message}}' => esc_html__( 'You can send inquiries. Net prices are unavailable while your account is limited.', 'linker-commerce' ),
				'{{reason}}'  => $this->reason_notice( $this->approval->reason( get_current_user_id() ) ),
			)
		);
	}

	/**
	 * The team's mailbox as the linkable part of a sentence. The address is the
	 * message's own placeholder, never a word inside it: the sentence links the
	 * mailbox whatever a translation does with the words around it, so a
	 * reworded or reordered translation can never silently swallow the link.
	 *
	 * @param string $message The translated sentence with one %s for the address.
	 */
	private function mailto_sentence( string $message ): string {
		return sprintf(
			esc_html( $message ),
			'<a href="mailto:' . esc_attr( self::TEAM_ADDRESS ) . '">' . esc_html( self::TEAM_ADDRESS ) . '</a>'
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
		return sprintf(
			'<span class="linker-gate-badge is-%1$s">%2$s<span>%3$s</span></span>',
			esc_attr( $state ),
			$clock,
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
	 * The products page's address, wherever the gate is shown.
	 */
	private function products_url(): string {
		return function_exists( 'wc_get_page_id' ) ? (string) get_permalink( (int) wc_get_page_id( 'shop' ) ) : '';
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
