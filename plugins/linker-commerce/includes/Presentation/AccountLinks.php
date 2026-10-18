<?php
/**
 * Native account addresses and reviewed words for LC guest entry fragments.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

use Linker\Commerce\Account\AuthTemplates;

/** LC owns the links' markup; Woo owns whether registration is available. */
final class AccountLinks {

	/** Data fragments used by the LC partials and the tool mount. */
	public function register(): void {
		add_shortcode( 'linker_create_account', array( self::class, 'create' ) );
		add_shortcode( 'linker_guest_account_links', array( self::class, 'guest_links' ) );
		add_shortcode( 'linker_footer_account', array( self::class, 'footer' ) );
		add_shortcode( 'linker_footer_account_count', array( self::class, 'footer_count' ) );
	}

	/** The existing footer account tile, with independent guest destinations. */
	public static function footer(): string {
		return strtr(
			Tokens::read( dirname( __DIR__, 2 ) . '/content/livecanvas/account/footer-entry.html' ),
			array(
				'{{signin-url}}' => esc_url( wc_get_page_permalink( 'myaccount' ) ),
				'{{signin}}'     => esc_html__( 'Sign in', 'linker-commerce' ),
				'{{create}}'     => self::create(),
			)
		);
	}

	/** The number of account destinations in the footer panel. */
	public static function footer_count(): string {
		return '' === self::create() ? '03' : '04';
	}

	/** The guest's two account entries, outside the tool's React root. */
	public static function guest_links(): string {
		if ( is_user_logged_in() ) {
			return '';
		}
		return strtr(
			Tokens::read( dirname( __DIR__, 2 ) . '/content/livecanvas/account/guest-links.html' ),
			array(
				'{{signin-url}}' => esc_url( wc_get_page_permalink( 'myaccount' ) ),
				'{{signin}}'     => esc_html__( 'Sign in', 'linker-commerce' ),
				'{{create}}'     => self::create(),
			)
		);
	}

	/** Localized account destinations for a guest comparison price cell.
	 *
	 * @param string $price Existing safe price prompt.
	 */
	public static function comparison_price( string $price ): string {
		$create = self::create();
		if ( '' === $create ) {
			return $price;
		}
		return strtr(
			Tokens::read( dirname( __DIR__, 2 ) . '/content/livecanvas/account/compare-price.html' ),
			array(
				'{{price}}'      => wp_kses_post( $price ),
				'{{signin-url}}' => esc_url( wc_get_page_permalink( 'myaccount' ) ),
				'{{create}}'     => $create,
			)
		);
	}

	/** One direct registration entry, empty when this visitor cannot register. */
	public static function create(): string {
		if ( is_user_logged_in() || 'yes' !== get_option( 'woocommerce_enable_myaccount_registration', 'no' ) ) {
			return '';
		}
		$url = AuthTemplates::register_url();
		if ( '' === $url ) {
			return '';
		}
		return strtr(
			Tokens::read( dirname( __DIR__, 2 ) . '/content/livecanvas/account/create-account.html' ),
			array(
				'{{register-url}}' => esc_url( $url ),
				'{{create}}'       => esc_html__( 'Create account', 'linker-commerce' ),
			)
		);
	}
}
