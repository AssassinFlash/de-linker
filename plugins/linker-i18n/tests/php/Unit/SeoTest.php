<?php
/**
 * Tests for the SEO filters and the translated types.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit;

use Linker\I18n\Seo;
use Linker\I18n\TranslatedTypes;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for Seo and TranslatedTypes.
 *
 * @covers \Linker\I18n\Seo
 * @covers \Linker\I18n\TranslatedTypes
 */
final class SeoTest extends TestCase {

	/**
	 * The x-default alternate points at the English URL.
	 */
	public function test_x_default_is_english(): void {
		WP_Mock::userFunction( 'is_search', array( 'return' => false ) );
		$this->assertSame(
			array(
				'en'        => 'http://example.test/product/x/',
				'de'        => 'http://example.test/de/produkt/x/',
				'x-default' => 'http://example.test/product/x/',
			),
			( new Seo() )->hreflangs(
				array(
					'en' => 'http://example.test/product/x/',
					'de' => 'http://example.test/de/produkt/x/',
				)
			)
		);
		$this->assertSame( array( 'de' => 'http://example.test/de/x/' ), ( new Seo() )->hreflangs( array( 'de' => 'http://example.test/de/x/' ) ) );
	}

	/**
	 * Search results, which WordPress marks noindex, get no hreflang links.
	 */
	public function test_no_hreflang_on_search_results(): void {
		WP_Mock::userFunction( 'is_search', array( 'return' => true ) );
		$this->assertSame(
			array(),
			( new Seo() )->hreflangs(
				array(
					'en' => 'http://example.test/?s=x',
					'de' => 'http://example.test/de/?s=x',
				)
			)
		);
	}

	/**
	 * No 404 guessing: it would cross languages.
	 */
	public function test_no_404_guessing(): void {
		$this->assertFalse( ( new Seo() )->guess_404() );
	}

	/**
	 * Pages, posts, products and LiveCanvas partials and templates are translated;
	 * so are product categories and the attributes whose values are words.
	 */
	public function test_translated_types(): void {
		$types = new TranslatedTypes();

		$post_types = $types->post_types( array( 'page' => 'page' ), false );
		$taxonomies = $types->taxonomies( array(), true );

		foreach ( array( 'page', 'post', 'product', 'lc_partial', 'lc_dynamic_template' ) as $post_type ) {
			$this->assertSame( $post_type, $post_types[ $post_type ] );
		}
		$this->assertArrayHasKey( 'product_cat', $taxonomies );
		$this->assertArrayHasKey( 'pa_phase', $taxonomies );
		$this->assertArrayNotHasKey( 'pa_brand', $taxonomies );
		$this->assertArrayNotHasKey( 'pa_model', $taxonomies );
	}
}
