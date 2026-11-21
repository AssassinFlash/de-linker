<?php
/**
 * Local Woo identities and public presentation in the selected language.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Integration;

use Linker\Commerce\Planning\Module;
use Linker\Commerce\Products\EngineeringReference;
use PHPUnit\Framework\TestCase;

/** Exercise publication and withdrawal with real Woo and Polylang records. */
final class PlannerProductCardsTest extends TestCase {

	/** Current English and German cards follow published products. Frozen project IDs stay canonical. */
	public function test_current_product_card_requires_a_public_sales_model_and_the_requested_translation(): void {
		if ( ! function_exists( 'pll_set_post_language' ) || ! function_exists( 'pll_save_post_translations' ) ) {
			self::fail( 'The native card translation test requires Polylang.' );
		}
		$english = new \WC_Product_Simple();
		$english->set_name( 'Sample inverter' );
		$english->set_status( 'publish' );
		$english->set_short_description( 'Example single-phase inverter.' );
		$en     = $english->save();
		$german = new \WC_Product_Simple();
		$german->set_name( 'Beispielwechselrichter' );
		$german->set_status( 'publish' );
		$german->set_short_description( 'Beispiel für einen einphasigen Wechselrichter.' );
		$de = $german->save();
		try {
			pll_set_post_language( $en, 'en' );
			pll_set_post_language( $de, 'de' );
			pll_save_post_translations(
				array(
					'en' => $en,
					'de' => $de,
				)
			);
			$cards = Module::product_cards( array( $en ), 'de' );
			self::assertSame( 'Beispielwechselrichter', $cards[ $en ]['label'] );
			self::assertSame( get_permalink( $de ), $cards[ $en ]['product_url'] );
			self::assertSame( $german->get_short_description(), $cards[ $en ]['highlight'] );
			update_post_meta( $en, EngineeringReference::ROLE_META_KEY, EngineeringReference::CABLE );
			self::assertSame( array(), Module::product_cards( array( $en ), 'de' ) );
			delete_post_meta( $en, EngineeringReference::ROLE_META_KEY );
			$german->set_status( 'draft' );
			$german->save();
			self::assertSame( array(), Module::product_cards( array( $en ), 'de' ) );
			self::assertSame( 'Sample inverter', Module::product_cards( array( $en ), 'en' )[ $en ]['label'] );
			$german->set_status( 'publish' );
			$german->save();
			$english->set_catalog_visibility( 'hidden' );
			$english->save();
			self::assertSame( array(), Module::product_cards( array( $en ), 'en' ) );
			self::assertSame( array(), Module::product_cards( array( $en ), 'de' ) );
		} finally {
			$german->delete( true );
			$english->delete( true );
		}
	}
}
