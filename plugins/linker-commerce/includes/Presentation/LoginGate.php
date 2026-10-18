<?php
/**
 * Account status presentation and the restricted inquiry notice.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

use Linker\Commerce\Registration\Approval;

/** Account notices and the native empty-checkout redirect rule. */
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

	/** Pending and restricted status within the usable account, using the live card design. */
	public function account_status_html(): string {
		$status     = $this->approval->status( get_current_user_id() );
		$restricted = Approval::RESTRICTED === $status;
		return strtr(
			Tokens::read( dirname( __DIR__, 2 ) . '/content/livecanvas/account/status-notice.html' ),
			array(
				'{{status}}'   => esc_attr( $status ),
				'{{label}}'    => esc_attr( $restricted ? __( 'Access currently limited', 'linker-commerce' ) : __( 'Account under review', 'linker-commerce' ) ),
				'{{badge}}'    => esc_html( $restricted ? __( 'Restricted', 'linker-commerce' ) : __( 'Under review', 'linker-commerce' ) ),
				'{{title}}'    => esc_html( $restricted ? __( 'Access currently limited', 'linker-commerce' ) : __( 'Your account is under review', 'linker-commerce' ) ),
				'{{message}}'  => esc_html( $restricted ? __( 'You can send inquiries. Net prices are unavailable while your account is limited.', 'linker-commerce' ) : __( 'We are reviewing your partner account and will email you when it is approved. You can send inquiries now; approval opens net prices.', 'linker-commerce' ) ),
				'{{reason}}'   => $restricted ? $this->reason_notice( $this->approval->reason( get_current_user_id() ) ) : '',
				'{{contact}}'  => $this->mailto_sentence(
					/* translators: %s: the team's email address. */
					__( 'Until then, browse the products and write to %s with any question.', 'linker-commerce' )
				),
				'{{products}}' => esc_url( $this->products_url() ),
				'{{browse}}'   => esc_html__( 'Browse products', 'linker-commerce' ),
			)
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
	 * The restricted account's reason, as the card's info notice.
	 *
	 * @param string $reason The reason the team stored.
	 */
	private function reason_notice( string $reason ): string {
		if ( '' === $reason ) {
			return '';
		}
		return strtr(
			Tokens::read( dirname( __DIR__, 2 ) . '/content/livecanvas/inquiry/restriction-reason.html' ),
			array(
				'{{label}}'  => esc_html__( 'Our reason:', 'linker-commerce' ),
				'{{reason}}' => esc_html( $reason ),
			)
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
