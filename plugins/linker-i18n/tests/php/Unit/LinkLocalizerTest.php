<?php
/**
 * Tests for links to German pages.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit;

use Linker\I18n\Languages;
use Linker\I18n\LinkLocalizer;
use Linker\I18n\Translation\HtmlTokenizer;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for LinkLocalizer.
 *
 * @covers \Linker\I18n\LinkLocalizer
 */
final class LinkLocalizerTest extends TestCase {

	/**
	 * The localizer on a site where /contact/ (33) has the German page
	 * /de/kontakt/ (58), the category accessories (46) Zubehör (150), the
	 * shop page products (15) produkte (42).
	 */
	private function localizer(): LinkLocalizer {
		PolylangDouble::mock(
			array(
				33 => 'en',
				58 => 'de',
				15 => 'en',
				42 => 'de',
			),
			array(
				33 => 58,
				15 => 42,
			),
			array(
				46  => 'en',
				150 => 'de',
				300 => 'de',
				301 => 'en',
			),
			array(
				46  => 150,
				301 => 300,
			)
		);
		WP_Mock::userFunction( 'wp_parse_url', array( 'return' => static fn( string $url, int $component = -1 ) => -1 === $component ? parse_url( $url ) : parse_url( $url, $component ) ) ); // phpcs:ignore WordPress.WP.AlternativeFunctions.parse_url_parse_url -- stands in for wp_parse_url.
		WP_Mock::userFunction( 'home_url', array( 'return' => static fn( string $path = '' ) => rtrim( PolylangDouble::HOME, '/' ) . $path ) );
		WP_Mock::userFunction( 'untrailingslashit', array( 'return' => static fn( string $url ): string => rtrim( $url, '/' ) ) );
		WP_Mock::userFunction(
			'url_to_postid',
			array(
				'return' => static fn( string $url ) => array(
					PolylangDouble::HOME . 'contact/'     => 33,
					PolylangDouble::HOME . 'de/kontakt/'  => 58,
					PolylangDouble::HOME . 'products/'    => 15,
					PolylangDouble::HOME . 'de/produkte/' => 42,
				)[ $url ] ?? 0,
			)
		);
		WP_Mock::userFunction(
			'get_permalink',
			array(
				'return' => static fn( int $id ) => array(
					33 => PolylangDouble::HOME . 'contact/',
					58 => PolylangDouble::HOME . 'de/kontakt/',
					15 => PolylangDouble::HOME . 'products/',
					42 => PolylangDouble::HOME . 'de/produkte/',
				)[ $id ] ?? false,
			)
		);
		WP_Mock::userFunction(
			'wc_get_permalink_structure',
			array( 'return' => array( 'category_rewrite_slug' => 'product-category' ) )
		);
		WP_Mock::userFunction(
			'get_terms',
			array(
				'return' => static function ( array $args ) {
					$slugs = array(
						'accessories'     => 46,
						'zubehoer'        => 150,
						'system-design'   => 301,
						'systemauslegung' => 300,
					);
					return isset( $slugs[ $args['slug'] ] ) ? array( PolylangDouble::term( $slugs[ $args['slug'] ] ) ) : array();
				},
			)
		);
		WP_Mock::userFunction(
			'get_term_link',
			array(
				'return' => static function ( int $id, string $taxonomy ) {
					unset( $taxonomy );
					return array(
						150 => PolylangDouble::HOME . 'de/produkt-kategorie/zubehoer/',
						46  => PolylangDouble::HOME . 'product-category/accessories/',
						300 => PolylangDouble::HOME . 'de/kategorie/systemauslegung/',
						301 => PolylangDouble::HOME . 'category/system-design/',
					)[ $id ] ?? false;
				},
			)
		);
		WP_Mock::userFunction(
			'get_option',
			array(
				'return' => static fn( string $name ) => 'woocommerce_shop_page_id' === $name ? '15' : '',
			)
		);
		WP_Mock::userFunction(
			'get_page_uri',
			array(
				'return' => static fn( int $id ) => array(
					15 => 'products',
					42 => 'produkte',
				)[ $id ] ?? false,
			)
		);
		return new LinkLocalizer( new Languages(), new HtmlTokenizer() );
	}

	/**
	 * Links of the site go to the German page; others are left as they are.
	 *
	 * @return array<string, array{string, string}>
	 */
	public function provide_urls(): array {
		$home = PolylangDouble::HOME;
		return array(
			'absolute page'     => array( $home . 'contact/', $home . 'de/kontakt/' ),
			'relative page'     => array( '/contact/#form', '/de/kontakt/#form' ),
			'query kept'        => array( $home . 'contact/?ref=footer', $home . 'de/kontakt/?ref=footer' ),
			'category'          => array( '/product-category/accessories/', '/de/produkt-kategorie/zubehoer/' ),
			'shop'              => array( $home . 'products/', $home . 'de/produkte/' ),
			'home'              => array( $home, $home . 'de/' ),
			'already German'    => array( $home . 'de/kontakt/', $home . 'de/kontakt/' ),
			'no German page'    => array( $home . 'imprint/', $home . 'imprint/' ),
			'external'          => array( 'https://www.goodwe.com/', 'https://www.goodwe.com/' ),
			'mail'              => array( 'mailto:sales@de-linker.com', 'mailto:sales@de-linker.com' ),
			'anchor'            => array( '#top', '#top' ),
			'protocol-relative' => array( '//cdn.example.test/x.js', '//cdn.example.test/x.js' ),
		);
	}

	/**
	 * The German URL.
	 *
	 * @dataProvider provide_urls
	 *
	 * @param string $url      URL.
	 * @param string $expected German URL.
	 */
	public function test_url( string $url, string $expected ): void {
		$this->assertSame( $expected, $this->localizer()->url( $url ) );
	}

	/**
	 * A link in either language becomes the target language's page: the
	 * render-time fallback asks for the request's own language, while the
	 * translation workflow keeps asking for German.
	 *
	 * @return array<string, array{string, string, string}>
	 */
	public function provide_target_urls(): array {
		$home = PolylangDouble::HOME;
		return array(
			'English page to German'          => array( $home . 'contact/', 'de', $home . 'de/kontakt/' ),
			'German page to English'          => array( $home . 'de/kontakt/', 'en', $home . 'contact/' ),
			'German page to English, query'   => array( '/de/kontakt/?ref=footer#form', 'en', '/contact/?ref=footer#form' ),
			'English page to German, query'   => array( '/contact/?ref=footer#form', 'de', '/de/kontakt/?ref=footer#form' ),
			'English page stays English'      => array( $home . 'contact/', 'en', $home . 'contact/' ),
			'German page stays German'        => array( $home . 'de/kontakt/', 'de', $home . 'de/kontakt/' ),
			'English home to German'          => array( $home, 'de', $home . 'de/' ),
			'German home to English'          => array( $home . 'de/', 'en', $home ),
			'German category to English'      => array( '/de/produkt-kategorie/zubehoer/', 'en', '/product-category/accessories/' ),
			'English category to German'      => array( '/product-category/accessories/', 'de', '/de/produkt-kategorie/zubehoer/' ),
			'retired category to German'      => array( '/product-category/residential-storage/res-accessories/', 'de', '/de/produkt-kategorie/zubehoer/' ),
			'German blog category to English' => array( '/de/kategorie/systemauslegung/', 'en', '/category/system-design/' ),
			'English blog category to German' => array( '/category/system-design/', 'de', '/de/kategorie/systemauslegung/' ),
			'German shop to English'          => array( '/de/produkte/', 'en', '/products/' ),
			'English shop to German'          => array( '/products/', 'de', '/de/produkte/' ),
		);
	}

	/**
	 * The URL in the target language.
	 *
	 * @dataProvider provide_target_urls
	 *
	 * @param string $url      URL.
	 * @param string $language Target language.
	 * @param string $expected Target URL.
	 */
	public function test_url_in_the_target_language( string $url, string $language, string $expected ): void {
		$this->assertSame( $expected, $this->localizer()->url( $url, $language ) );
	}

	/**
	 * The render-time fallback localizes HTML for the request's language.
	 */
	public function test_localize_html_in_the_target_language(): void {
		$this->assertSame(
			'<p><a href="/contact/">Contact</a> and <a href="https://www.goodwe.com/">GoodWe</a></p>',
			$this->localizer()->localize( '<p><a href="/de/kontakt/">Contact</a> and <a href="https://www.goodwe.com/">GoodWe</a></p>', 'en' )
		);
	}

	/**
	 * In HTML only the href of links changes.
	 */
	public function test_localize_html(): void {
		$this->assertSame(
			'<p>Write to <a class="btn" href="/de/kontakt/">us</a> or <a href="https://www.goodwe.com/">GoodWe</a>; <img src="/contact/x.png" alt="contact"></p>',
			$this->localizer()->localize( '<p>Write to <a class="btn" href="/contact/">us</a> or <a href="https://www.goodwe.com/">GoodWe</a>; <img src="/contact/x.png" alt="contact"></p>' )
		);
	}
}
