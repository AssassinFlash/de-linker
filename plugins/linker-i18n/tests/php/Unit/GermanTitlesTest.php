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
	private const ENGLISH = 'Compare inverters, LFP storage and accessories for your project. Filter by brand or look up a device by model or product number.';

	/**
	 * The German sentence the catalog carries.
	 */
	private const GERMAN = 'Vergleichen Sie Wechselrichter, LFP-Speicher und Zubehör für Ihr Projekt. Filtern Sie nach Marke oder suchen Sie nach Modell und Produktnummer.';

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
	/**
	 * The German post owns its translated cover text even with a shared attachment.
	 */
	public function test_social_image_uses_the_german_post_cover(): void {
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'de' ) );
		WP_Mock::userFunction( 'is_singular' )->with( 'post' )->andReturn( true );
		WP_Mock::userFunction( 'get_queried_object_id', array( 'return' => 85 ) );
		WP_Mock::userFunction( 'get_post_meta' )->with( 85, \Linker\I18n\CoverAlt::DISPLAY, true )->andReturn( 'Speicher im Technikraum' );
		WP_Mock::userFunction( 'esc_attr', array( 'return' => static fn( $s ) => $s ) );
		$titles = new GermanTitles( new Languages() );
		$input  = '<meta property="og:image" content="https://example.org/cover.jpg"><meta property="og:image:alt" content="Battery in the utility room">';
		$this->assertSame( str_replace( 'Battery in the utility room', 'Speicher im Technikraum', $input ), $titles->social_image_alt( $input ) );
	}

	/** Native product images get the German product name if there was no alt tag. */
	public function test_social_image_adds_german_product_title(): void {
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'de' ) );
		WP_Mock::userFunction( 'is_singular' )->with( 'post' )->andReturn( false );
		WP_Mock::userFunction( 'is_singular' )->with( array( 'product', 'page' ) )->andReturn( true );
		WP_Mock::userFunction( 'get_queried_object_id', array( 'return' => 27 ) );
		WP_Mock::userFunction( 'get_the_title' )->with( 27 )->andReturn( 'Gewerbespeicher' );
		WP_Mock::userFunction( 'wp_strip_all_tags', array( 'return' => static fn( $s ) => $s ) );
		WP_Mock::userFunction( 'esc_attr', array( 'return' => static fn( $s ) => $s ) );
		$titles = new GermanTitles( new Languages() );
		$this->assertStringContainsString( '<meta property="og:image:alt" content="Gewerbespeicher">', $titles->social_image_alt( '<meta property="og:image" content="https://example.org/product.webp">' ) );
	}

	/** Site and journal artwork carry distinct reviewed German descriptions. */
	public function test_social_image_labels_each_german_fallback(): void {
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'de' ) );
		WP_Mock::userFunction( 'esc_attr', array( 'return' => static fn( $s ) => $s ) );
		$titles = new GermanTitles( new Languages() );
		$this->assertStringContainsString( 'für Wohngebäude, Gewerbe und Industrie', $titles->social_image_alt( '<meta property="og:image" content="/og-linker-default-1200x630.jpg">' ) );
		$this->assertStringContainsString( 'Technische Leitfäden', $titles->social_image_alt( '<meta property="og:image" content="/og-linker-blog-1200x630.jpg">' ) );
	}

	/** The English attachment owns its original alternative text. */
	public function test_social_image_preserves_english_output(): void {
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'en' ) );
		$titles = new GermanTitles( new Languages() );
		$html   = '<meta property="og:image" content="/og-linker-blog-1200x630.jpg"><meta property="og:image:alt" content="Linker Journal">';
		$this->assertSame( $html, $titles->social_image_alt( $html ) );
	}
	/** Both social networks receive the title of the shop in the visitor's language. */
	public function test_german_shop_shares_its_german_title(): void {
		require_once dirname( __DIR__, 4 ) . '/linker-commerce/tests/php/Doubles/wordpress.php';
		WP_Mock::userFunction( 'get_option', array( 'return' => true ) );
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'de' ) );
		WP_Mock::userFunction( 'is_shop', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_404', array( 'return' => false ) );
		WP_Mock::userFunction( 'get_query_var', array( 'return' => 0 ) );
		WP_Mock::userFunction( 'is_wc_endpoint_url', array( 'return' => false ) );
		WP_Mock::userFunction( 'is_account_page', array( 'return' => false ) );
		WP_Mock::userFunction( '__' )->with( 'Inverters, storage and systems', 'linker-i18n' )->andReturn( 'Wechselrichter, Speicher und Systeme' );
		WP_Mock::userFunction( 'wp_strip_all_tags', array( 'return_arg' => 0 ) );
		WP_Mock::userFunction( 'get_bloginfo', array( 'return' => 'Linker' ) );
		$titles = new GermanTitles( new Languages() );
		foreach ( array( 'og:title', 'twitter:title' ) as $key ) {
			$this->assertStringContainsString( 'property="' . $key . '" content="Wechselrichter, Speicher und Systeme | Linker"', $titles->shop_social_title( '<meta property="' . $key . '" content="Products | Linker">' ) );
		}
	}
}
