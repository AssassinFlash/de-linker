<?php
/**
 * Commerce fields on a product card: price visibility, stock, RFQ.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Abilities;

use Linker\Commerce\Gating\CommerceState;
use Linker\Commerce\Registration\Approval;
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
 * UserContext), so "the current visitor" is the customer, and an approved
 * account reads the price exactly as its product page prints it
 * (`price_text`, WooCommerce's own price HTML as text, in the turn's
 * language). Every other visitor reads why there is none (`price_reason`):
 * the guest must sign in, the pending account waits for approval, the
 * restricted account has no prices, a product quoted per project shows none
 * to anyone, and a product without a stored price is on request.
 */
final class ProductCommerce {

	/**
	 * Why a card shows no price: the product page's reasons, the approval split
	 * into the two account states a customer can be in while signed in (a
	 * rejected account cannot sign in, Approval::gate_login).
	 */
	public const REASONS = array( 'login', 'pending', 'restricted', 'project', 'unpriced' );

	/**
	 * The WordPress locale of the German turn (linker-i18n's Setup: the Sie form).
	 */
	private const GERMAN_LOCALE = 'de_DE_formal';

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
				'price_text'    => array(
					'type'        => 'string',
					'description' => __( 'The price as the product page prints it, when it is visible.', 'linker-commerce' ),
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
	 * @param string          $lang       The turn's language, 'en' or 'de'.
	 * @return array{price_visible: bool, price?: string, price_text?: string, price_reason?: string, in_stock: bool, rfq_only: bool}
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
		);
		if ( $visible ) {
			$commerce['price'] = (string) $product->get_price( 'edit' );
		}
		$reason = $state->page_reason( $product );
		if ( null === $reason ) {
			$commerce['price_text'] = self::price_text( $product, $lang );
		} else {
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
	 * The product page's price line as text: WooCommerce's price HTML, whose
	 * money format follows the language (Vocabulary\LocaleFormat reads the
	 * locale: "€1,680.00", "1.680,00 €"), so a German turn makes it inside
	 * the German locale.
	 *
	 * @param WC_Product $product The product.
	 * @param string     $lang    'en' or 'de'.
	 */
	private static function price_text( WC_Product $product, string $lang ): string {
		$switched = 'de' === $lang && switch_to_locale( self::GERMAN_LOCALE );
		$html     = (string) $product->get_price_html();
		if ( $switched ) {
			restore_previous_locale();
		}
		return trim( html_entity_decode( wp_strip_all_tags( $html ), ENT_QUOTES | ENT_HTML5, 'UTF-8' ) );
	}

	/**
	 * The card's reason: the product page's (CommerceState::page_reason), with
	 * the approval named.
	 *
	 * @param string        $reason One of the CommerceState reasons.
	 * @param CommerceState $state  The price rule.
	 */
	private static function reason( string $reason, CommerceState $state ): string {
		if ( CommerceState::APPROVAL !== $reason ) {
			return CommerceState::LOGIN === $reason ? 'login' : ( CommerceState::PROJECT === $reason ? 'project' : 'unpriced' );
		}
		return Approval::PENDING === $state->current_approval_status() ? 'pending' : 'restricted';
	}
}
