<?php
/**
 * Shortcodes that feed LiveCanvas templates with B2B data.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

use Linker\Commerce\Products\Faqs;
use Linker\Commerce\Registration\Approval;
use WC_Product;

/**
 * Price gating and the empty Proforma-request gate: the two shortcodes the
 * exported templates consume.
 */
final class Shortcodes {

	/**
	 * Sets up the shortcodes.
	 *
	 * @param LoginGate $gate     The empty Proforma-request page.
	 * @param Approval  $approval The account approval rule.
	 */
	public function __construct( private readonly LoginGate $gate, private readonly Approval $approval = new Approval() ) {}

	/**
	 * Registers the shortcodes.
	 */
	public function register(): void {
		add_shortcode( 'linker_price', array( $this, 'price' ) );
		add_shortcode( 'linker_checkout', array( $this, 'checkout' ) );
		add_shortcode( 'linker_faqs', array( $this, 'faqs' ) );
		add_shortcode( 'linker_contact_link', array( $this, 'contact_link' ) );
	}

	/**
	 * The contact page in the page's language; every contact entry (the site
	 * chrome's, the catalogue's invitation) resolves its target here.
	 */
	public static function contact_page_url(): string {
		$page = get_page_by_path( 'contact' );
		$id   = $page instanceof \WP_Post ? (int) $page->ID : 0;
		if ( $id > 0 && function_exists( 'pll_get_post' ) && function_exists( 'pll_current_language' ) && 'de' === pll_current_language() ) {
			$twin = (int) pll_get_post( $id, 'de' );
			if ( $twin > 0 ) {
				$id = $twin;
			}
		}
		return $id > 0 ? (string) get_permalink( $id ) : home_url( '/contact/' );
	}

	/**
	 * The site chrome's contact entry: the contact page in the page's
	 * language, carrying the product on display as the request's subject.
	 * Placement selects the chrome's own class (header, mobile header,
	 * footer).
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function contact_link( $atts = array() ): string {
		$attributes = shortcode_atts(
			array(
				'placement' => 'header',
				'class'     => '',
			),
			(array) $atts
		);
		$classes    = '' !== trim( (string) $attributes['class'] )
			? trim( (string) $attributes['class'] )
			: ( 'mobile' === $attributes['placement'] ? 'tv-header-cta tv-mobile-cta' : 'tv-header-cta' );
		$url        = self::contact_page_url();
		if ( function_exists( 'is_product' ) && is_product() ) {
			$product = wc_get_product( (int) get_the_ID() );
			if ( $product instanceof WC_Product ) {
				$url = (string) add_query_arg(
					array(
						'intent'     => 'product',
						'kind'       => 'product',
						'title'      => rawurlencode( $product->get_name() ),
						'source_id'  => $product->get_id(),
						'product_id' => $product->get_id(),
						'source'     => $product->get_permalink(),
					),
					$url
				);
			}
		}
		return '<a class="' . esc_attr( $classes ) . '" href="' . esc_url( $url ) . '">' . esc_html__( 'Contact Linker', 'linker-commerce' ) . '</a>';
	}

	/**
	 * The current product's gated price HTML.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function price( $atts = array() ): string {
		unset( $atts );
		$product = $GLOBALS['product'] ?? null;
		if ( ! $product instanceof WC_Product ) {
			return '';
		}
		return '<div class="linker-price font-semibold text-[#0c7f73]">' . $product->get_price_html() . '</div>';
	}

	/**
	 * The Proforma request: the gate when the draft is empty or the account
	 * may not send, otherwise WooCommerce's checkout.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function checkout( $atts = array() ): string {
		unset( $atts );
		$user_id = get_current_user_id();
		if ( $this->is_empty_request() || ( $user_id > 0 && ! $this->approval->sees_prices( $user_id ) ) ) {
			return $this->gate->html();
		}
		return do_shortcode( '[woocommerce_checkout]' );
	}

	/**
	 * Whether this is an empty Proforma request (not a confirmation or pay page).
	 */
	private function is_empty_request(): bool {
		if ( is_wc_endpoint_url( 'order-received' ) || is_wc_endpoint_url( 'order-pay' ) ) {
			return false;
		}
		return WC()->cart->is_empty();
	}

	/**
	 * The current product's FAQ rows from `_linker_faqs` (docs/specs/15-faq.md),
	 * as the live page's accordion rows. German requests (Polylang `de`) use
	 * question_de / answer_de. The section frame and its title live in the
	 * template; this carries the rows.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function faqs( $atts = array() ): string {
		unset( $atts );
		$product = $GLOBALS['product'] ?? null;
		if ( ! $product instanceof WC_Product ) {
			$product = wc_get_product( (int) get_the_ID() );
		}
		if ( ! $product instanceof WC_Product ) {
			return '';
		}
		$items = Faqs::of( $product->get_id() );
		if ( array() === $items ) {
			return '';
		}
		$german = function_exists( 'pll_current_language' ) && 'de' === pll_current_language();
		$html   = '';
		foreach ( $items as $item ) {
			$question = $german && '' !== $item['question_de'] ? $item['question_de'] : $item['question'];
			$answer   = $german && '' !== $item['answer_de'] ? $item['answer_de'] : $item['answer'];
			$html    .= '<details class="pdp-disclose"><summary>' . esc_html( $question ) . ProductShortcodes::icon( 'chevron' ) . '</summary>'
				. '<div class="pdp-disclose-body pdp-reading">' . wp_kses_post( wpautop( $answer ) ) . '</div></details>';
		}
		return $html;
	}
}
