<?php
/**
 * Tests for the German shop's SEO description.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit;

use Linker\I18n\GermanTitles;
use Linker\I18n\Languages;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * The German shop carries a German description even when SEOPress resolves
 * the English shop page (ticket #264 H4).
 *
 * @covers \Linker\I18n\GermanTitles::shop_description
 * @covers \Linker\I18n\GermanTitles::shop_social_description
 */
final class GermanTitlesTest extends TestCase {

	/**
	 * The English description SEOPress computes on the English shop page.
	 */
	private const ENGLISH = 'Filter inverters, LFP batteries, all-in-one systems, meters and controllers by brand, or find an item by number or nameplate photo. Net prices for partners.';

	/**
	 * The German sentence the catalog carries.
	 */
	private const GERMAN = 'Filtern Sie Wechselrichter, LFP-Batterien, Komplettsysteme, Zähler und Steuerungen nach Marke oder finden Sie ein Produkt per Produktnummer oder Typenschildfoto. Nettopreise für Partner.';

	/**
	 * The German shop request.
	 */
	private function german_shop(): GermanTitles {
		WP_Mock::userFunction( 'get_option', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_shop', array( 'return' => true ) );
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'de' ) );
		return new GermanTitles( new Languages() );
	}

	/**
	 * The German shop names its description in German.
	 */
	public function test_the_german_shop_description_is_german(): void {
		WP_Mock::userFunction( '__' )
			->with( self::ENGLISH, 'linker-i18n' )
			->andReturn( self::GERMAN );

		$this->assertSame( self::GERMAN, $this->german_shop()->shop_description( self::ENGLISH ) );
	}

	/**
	 * The German sentence is the catalog's msgstr, so the instance prints it.
	 */
	public function test_the_german_sentence_is_in_the_catalog(): void {
		// phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- Checked-in catalog in the plugin directory.
		$catalog = (string) file_get_contents( \dirname( __DIR__, 3 ) . '/languages/linker-i18n-de_DE_formal.po' );
		$this->assertStringContainsString( 'msgid ""' . "\n" . '"Filter inverters, LFP batteries, all-in-one systems, meters and controllers "', $catalog );
		$this->assertStringContainsString( 'Filtern Sie Wechselrichter, LFP-Batterien, Komplettsysteme, Zähler und "', $catalog );
		$this->assertStringContainsString( '"Steuerungen nach Marke oder finden Sie ein Produkt per Produktnummer oder "', $catalog );
		$this->assertStringContainsString( '"Typenschildfoto. Nettopreise für Partner."', $catalog );
	}

	/**
	 * The English shop keeps SEOPress's description.
	 */
	public function test_the_english_shop_keeps_its_description(): void {
		WP_Mock::userFunction( 'get_option', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_shop', array( 'return' => true ) );
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'en' ) );

		$titles = new GermanTitles( new Languages() );

		$this->assertSame( self::ENGLISH, $titles->shop_description( self::ENGLISH ) );
	}

	/**
	 * A German page that is not the shop keeps SEOPress's description.
	 */
	public function test_another_german_page_keeps_its_description(): void {
		WP_Mock::userFunction( 'get_option', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_shop', array( 'return' => false ) );
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'de' ) );

		$titles = new GermanTitles( new Languages() );

		$this->assertSame( 'Eine andere Beschreibung.', $titles->shop_description( 'Eine andere Beschreibung.' ) );
	}
}
