<?php
/**
 * Tests for the German URL segments.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit;

use Linker\I18n\Languages;
use Linker\I18n\UrlSegments;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for UrlSegments.
 *
 * @covers \Linker\I18n\UrlSegments
 * @covers \Linker\I18n\Languages
 */
final class UrlSegmentsTest extends TestCase {

	/**
	 * The segments, with WooCommerce's default bases and the shop page at /products/.
	 */
	private function segments(): UrlSegments {
		PolylangDouble::mock();
		WP_Mock::userFunction(
			'wc_get_permalink_structure',
			array(
				'return' => array(
					'product_rewrite_slug'  => '/product',
					'category_rewrite_slug' => 'product-category',
				),
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
		return new UrlSegments( new Languages() );
	}

	/**
	 * German links get the German segments, English links made from German
	 * ones the English segments back; anything else is left alone.
	 *
	 * @return array<string, array{string, string}>
	 */
	public function provide_links(): array {
		$home = PolylangDouble::HOME;
		return array(
			'German product'           => array( $home . 'de/product/goodwe-gw60k-sts-g10/', $home . 'de/produkt/goodwe-gw60k-sts-g10/' ),
			'German category path'     => array( $home . 'de/product-category/zubehoer/notstrom/', $home . 'de/produkt-kategorie/zubehoer/notstrom/' ),
			'German shop'              => array( $home . 'de/products/', $home . 'de/produkte/' ),
			'German shop, page 2'      => array( $home . 'de/products/page/2/', $home . 'de/produkte/page/2/' ),
			'German page untouched'    => array( $home . 'de/ueber-uns/', $home . 'de/ueber-uns/' ),
			'English made from German' => array( $home . 'produkte/', $home . 'products/' ),
			'English product kept'     => array( $home . 'product/x/', $home . 'product/x/' ),
			'not product-category'     => array( $home . 'de/products-old/', $home . 'de/products-old/' ),
			'other site'               => array( 'https://example.org/de/product/x/', 'https://example.org/de/product/x/' ),
		);
	}

	/**
	 * A link in its language's segments.
	 *
	 * @dataProvider provide_links
	 *
	 * @param string $link     Link.
	 * @param string $expected Expected link.
	 */
	public function test_link( string $link, string $expected ): void {
		$this->assertSame( $expected, $this->segments()->link( $link ) );
	}

	/**
	 * The German rules come first and send the German segments to the
	 * product, category and shop queries in German.
	 */
	public function test_rules_come_first(): void {
		$rules = $this->segments()->rules( array( '(.?.+?)(?:/([0-9]+))?/?$' => 'index.php?pagename=$matches[1]' ) );

		$this->assertSame(
			array(
				'de/produkt/([^/]+)/?$'            => 'index.php?product=$matches[1]&lang=de',
				'de/produkt-kategorie/(.+?)/page/?([0-9]{1,})/?$' => 'index.php?product_cat=$matches[1]&paged=$matches[2]&lang=de',
				'de/produkt-kategorie/(.+?)/?$'    => 'index.php?product_cat=$matches[1]&lang=de',
				'de/produkte/page/?([0-9]{1,})/?$' => 'index.php?post_type=product&paged=$matches[1]&lang=de',
				'de/produkte/?$'                   => 'index.php?post_type=product&lang=de',
				'(.?.+?)(?:/([0-9]+))?/?$'         => 'index.php?pagename=$matches[1]',
			),
			$rules
		);
	}

	/**
	 * Polylang writes no /de/ version of the English product, category and shop rules.
	 */
	public function test_polylang_rules(): void {
		$segments = new UrlSegments( new Languages() );

		$this->assertFalse( $segments->polylang_rule( true, array(), 'product', false ) );
		$this->assertFalse( $segments->polylang_rule( true, array(), 'product_cat', false ) );
		$this->assertFalse( $segments->polylang_rule( true, array(), 'rewrite_rules_array', 'product' ) );
		$this->assertTrue( $segments->polylang_rule( true, array(), 'page', false ) );
		$this->assertTrue( $segments->polylang_rule( true, array(), 'rewrite_rules_array', 'post' ) );
	}

	/**
	 * The rewrite cache is written again only when the German rules changed.
	 */
	public function test_refresh_flushes_once(): void {
		$segments = $this->segments();
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => 'rules' ) );
		WP_Mock::userFunction(
			'get_option',
			array(
				'args'   => array( 'linker_i18n_rewrite_fingerprint' ),
				'return' => md5( 'old' ),
			)
		);
		WP_Mock::userFunction(
			'flush_rewrite_rules',
			array(
				'times' => 1,
				'args'  => array( false ),
			)
		);
		WP_Mock::userFunction(
			'update_option',
			array(
				'times' => 1,
				'args'  => array( 'linker_i18n_rewrite_fingerprint', md5( 'rules' ), false ),
			)
		);

		$segments->refresh();

		$this->assertConditionsMet();
	}
}
