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
			),
			array( 46 => 150 )
		);
		WP_Mock::userFunction( 'wp_parse_url', array( 'return' => static fn( string $url, int $component = -1 ) => -1 === $component ? parse_url( $url ) : parse_url( $url, $component ) ) ); // phpcs:ignore WordPress.WP.AlternativeFunctions.parse_url_parse_url -- stands in for wp_parse_url.
		WP_Mock::userFunction( 'home_url', array( 'return' => static fn( string $path = '' ) => rtrim( PolylangDouble::HOME, '/' ) . $path ) );
		WP_Mock::userFunction(
			'url_to_postid',
			array(
				'return' => static fn( string $url ) => array(
					PolylangDouble::HOME . 'contact/' => 33,
				)[ $url ] ?? 0,
			)
		);
		WP_Mock::userFunction(
			'get_permalink',
			array(
				'return' => static fn( int $id ) => array(
					58 => PolylangDouble::HOME . 'de/kontakt/',
					42 => PolylangDouble::HOME . 'de/produkte/',
				)[ $id ] ?? false,
			)
		);
		WP_Mock::userFunction(
			'wc_get_permalink_structure',
			array( 'return' => array( 'category_rewrite_slug' => 'product-category' ) )
		);
		WP_Mock::userFunction( 'get_terms', array( 'return' => static fn( array $args ) => 'accessories' === $args['slug'] ? array( PolylangDouble::term( 46 ) ) : array() ) );
		WP_Mock::userFunction(
			'get_term_link',
			array(
				'args'   => array( 150, 'product_cat' ),
				'return' => PolylangDouble::HOME . 'de/produkt-kategorie/zubehoer/',
			)
		);
		WP_Mock::userFunction(
			'get_option',
			array(
				'args'   => array( 'woocommerce_shop_page_id' ),
				'return' => '15',
			)
		);
		WP_Mock::userFunction(
			'get_page_uri',
			array(
				'args'   => array( 15 ),
				'return' => 'products',
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
	 * In HTML only the href of links changes.
	 */
	public function test_localize_html(): void {
		$this->assertSame(
			'<p>Write to <a class="btn" href="/de/kontakt/">us</a> or <a href="https://www.goodwe.com/">GoodWe</a>; <img src="/contact/x.png" alt="contact"></p>',
			$this->localizer()->localize( '<p>Write to <a class="btn" href="/contact/">us</a> or <a href="https://www.goodwe.com/">GoodWe</a>; <img src="/contact/x.png" alt="contact"></p>' )
		);
	}
}
