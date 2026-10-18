<?php
/**
 * Commerce fields on a product card: price visibility, stock, RFQ.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Abilities;

use Linker\Commerce\Gating\CommerceState;
use Linker\Commerce\Mail\LocaleSwitch;
use Linker\Commerce\Registration\Approval;
use Linker\Commerce\Storefront\ProductView;
use WC_Product;

/**
 * The commerce object of search-products and get-product. Price visibility
 * is CommerceState, the one rule every surface reads (docs/specs/11-commerce.md).
 * Stock is the product's own (the ERP pushes it through linker/v1/stock,
 * ticket #69); the site says only the state, never a quantity (owner ruling
 * 2026-10-02).
 *
 * Prices follow the account (#242, docs/specs/13-genie.md 目标 8): Genie calls
 * these abilities with the customer's short-lived token (linker-tools'
 * UserContext), so "the current visitor" is the customer. `price_line` is
 * what the customer's own product page prints where the price stands
 * (ProductView::price_html, in the turn's language): the price for an approved
 * account, otherwise the page's sentence; `price_reason` names why there is no
 * price, in the page's order (CommerceState::reason on its PAGE surface).
 */
final class ProductCommerce {

	/**
	 * Why a card shows no price: the product page's reasons, the approval split
	 * into the two account states a customer can be in while signed in (a
	 * rejected account cannot sign in, Approval::gate_login).
	 */
	public const REASONS = array( 'login', 'pending', 'restricted', 'project', 'unpriced' );

	/**
	 * JSON Schema of the commerce object.
	 *
	 * @return array<string, mixed>
	 */
	public static function schema(): array {
		return array(
			'type'                 => 'object',
			'properties'           => array(
				'price_visible' => array(
					'type'        => 'boolean',
					'description' => __( 'Whether this visitor sees the stored price.', 'linker-commerce' ),
				),
				'price'         => array(
					'type'        => 'string',
					'description' => __( 'Stored price when it is visible.', 'linker-commerce' ),
				),
				'price_line'    => array(
					'type'        => 'string',
					'description' => __( 'What the product page prints where the price stands, for this visitor.', 'linker-commerce' ),
				),
				'price_reason'  => array(
					'type'        => 'string',
					'enum'        => self::REASONS,
					'description' => __( 'Why this visitor sees no price.', 'linker-commerce' ),
				),
				'in_stock'      => array(
					'type'        => 'boolean',
					'description' => __( 'Whether the product is in stock (the stock the ERP pushed).', 'linker-commerce' ),
				),
				'rfq_only'      => array(
					'type'        => 'boolean',
					'description' => __( 'Whether the product is quoted per project.', 'linker-commerce' ),
				),
			),
			'required'             => array( 'price_visible', 'in_stock', 'rfq_only' ),
			'additionalProperties' => false,
		);
	}

	/**
	 * Commerce fields of a product for the current visitor.
	 *
	 * @param int             $product_id Product ID.
	 * @param WC_Product|null $product    The product, when already loaded.
	 * @param 'en'|'de'       $lang       The turn's language (ProductText::lang).
	 * @return array{price_visible: bool, price?: string, price_line?: string, price_reason?: string, in_stock: bool, rfq_only: bool}
	 */
	public static function of( int $product_id, ?WC_Product $product = null, string $lang = 'en' ): array {
		if ( ! $product instanceof WC_Product ) {
			$loaded  = wc_get_product( $product_id );
			$product = $loaded instanceof WC_Product ? $loaded : null;
		}
		if ( ! $product instanceof WC_Product ) {
			return self::hidden();
		}
		$state    = new CommerceState();
		$visible  = $state->shows_price( $product );
		$commerce = array(
			'price_visible' => $visible,
			'in_stock'      => $product->is_in_stock(),
			'rfq_only'      => $state->is_rfq_only( $product ),
			'price_line'    => self::price_line( $product, $state, $lang ),
		);
		if ( $visible ) {
			$commerce['price'] = (string) $product->get_price( 'edit' );
		}
		$reason = $state->reason( $product, CommerceState::PAGE );
		if ( null !== $reason ) {
			$commerce['price_reason'] = self::reason( $reason, $state );
		}

		return $commerce;
	}

	/**
	 * Commerce fields when there is no product to show.
	 *
	 * @return array{price_visible: false, in_stock: false, rfq_only: false}
	 */
	public static function hidden(): array {
		return array(
			'price_visible' => false,
			'in_stock'      => false,
			'rfq_only'      => false,
		);
	}

	/**
	 * The product page's price line as text, in the turn's language: the
	 * money format (Vocabulary\LocaleFormat: "€1,680.00", "1.680,00 €") and
	 * the page's sentences ("Nettopreis nach Partner-Anmeldung") follow the
	 * locale, so the line is made inside it (Mail\LocaleSwitch, which reloads
	 * this plugin's catalog for the switch).
	 *
	 * @param WC_Product    $product The product.
	 * @param CommerceState $state   The price rule.
	 * @param 'en'|'de'     $lang    Language.
	 */
	private static function price_line( WC_Product $product, CommerceState $state, string $lang ): string {
		$view   = new ProductView( $state );
		$locale = ProductText::locale( $lang );
		if ( determine_locale() === $locale ) {
			$html = $view->price_html( $product );
		} else {
			$switch = new LocaleSwitch();
			$switch->to( $locale );
			try {
				$html = $view->price_html( $product );
			} finally {
				$switch->back();
			}
		}
		return trim( html_entity_decode( wp_strip_all_tags( $html ), ENT_QUOTES | ENT_HTML5, 'UTF-8' ) );
	}

	/**
	 * The card's reason code, with the approval named.
	 *
	 * @param string        $reason One of the CommerceState reasons.
	 * @param CommerceState $state  The price rule.
	 */
	private static function reason( string $reason, CommerceState $state ): string {
		return match ( $reason ) {
			CommerceState::LOGIN    => 'login',
			CommerceState::PROJECT  => 'project',
			CommerceState::APPROVAL => Approval::PENDING === $state->current_approval_status() ? 'pending' : 'restricted',
			default                 => 'unpriced',
		};
	}
}
