<?php
/**
 * Shortcodes that feed LiveCanvas templates with B2B data.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

use Linker\Commerce\Catalog\Faqs;
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
	 * The current product's FAQ from `_linker_faqs` (docs/specs/15-faq.md).
	 * German requests (Polylang `de`) use question_de / answer_de.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function faqs( $atts = array() ): string {
		unset( $atts );
		$product = $GLOBALS['product'] ?? null;
		if ( ! $product instanceof WC_Product ) {
			return '';
		}
		$items = Faqs::of( $product->get_id() );
		if ( array() === $items ) {
			return '';
		}
		$german = function_exists( 'pll_current_language' ) && 'de' === pll_current_language();
		$html   = sprintf(
			'<section class="pdp-block pdp-faqs linker-faqs" id="faq" data-faq-count="%d">',
			count( $items )
		);
		$html  .= '<h2 class="pdp-section-title">' . esc_html__( 'Product questions', 'linker-commerce' ) . '</h2>';
		foreach ( $items as $item ) {
			$question = $german && '' !== $item['question_de'] ? $item['question_de'] : $item['question'];
			$answer   = $german && '' !== $item['answer_de'] ? $item['answer_de'] : $item['answer'];
			$page     = (int) $item['citation']['page'];
			$title    = (string) ( $item['citation']['title'] ?? '' );
			$cite     = '' !== $title
				? sprintf(
					/* translators: 1: document title, 2: page number. */
					__( '%1$s, p. %2$d', 'linker-commerce' ),
					$title,
					$page
				)
				: sprintf(
					/* translators: %d: page number. */
					__( 'p. %d', 'linker-commerce' ),
					$page
				);
			$html .= '<details class="linker-faq border-b border-neutral-200 py-3">';
			$html .= '<summary class="cursor-pointer font-semibold text-[#15352f]">' . esc_html( $question ) . '</summary>';
			$html .= '<div class="mt-2 leading-relaxed text-neutral-700">' . wp_kses_post( wpautop( $answer ) );
			$html .= sprintf(
				'<p class="mt-2 text-sm text-neutral-500"><a href="%1$s">%2$s</a></p>',
				esc_url( $item['citation']['url'] . '#page=' . $page ),
				esc_html( $cite )
			);
			$html .= '</div></details>';
		}
		$html .= '</section>';
		return $html;
	}
}
