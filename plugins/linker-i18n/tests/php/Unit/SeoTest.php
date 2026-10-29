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
use Mockery;
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
	 * Proper-name archives keep shared terms while native Polylang filters products.
	 */
	public function test_shared_archives_preserve_native_and_other_plugin_entries(): void {
		$types = new TranslatedTypes();
		$this->assertSame(
			array( 'post_format', 'custom_shared', 'pa_brand', 'product_brand', 'pa_series' ),
			$types->shared_archives( array( 'post_format', 'custom_shared', 'pa_brand' ) )
		);
		foreach ( array( 'product_brand', 'pa_brand', 'pa_series' ) as $taxonomy ) {
			$this->assertArrayNotHasKey( $taxonomy, $types->taxonomies( array(), false ) );
		}
	}

	/**
	 * Empty product type is scoped only on the main shared archive.
	 *
	 * @return array<string, array{mixed, bool, bool, bool}>
	 */
	public function provide_shared_archive_queries(): array {
		return array(
			'empty native product archive' => array( '', true, true, true ),
			'implicit product archive'     => array( null, true, true, true ),
			'explicit product'             => array( 'product', true, true, false ),
			'explicit other type'          => array( 'post', true, true, false ),
			'explicit any'                 => array( 'any', true, true, false ),
			'explicit list'                => array( array(), true, true, false ),
			'secondary query'              => array( '', false, true, false ),
			'other taxonomy'               => array( '', true, false, false ),
		);
	}

	/**
	 * Keep native main-query identity explicit without broad query rewriting.
	 *
	 * @dataProvider provide_shared_archive_queries
	 * @param mixed $post_type Existing post-type declaration.
	 * @param bool  $main      Main query.
	 * @param bool  $shared    One of the approved shared product archives.
	 * @param bool  $scoped    Whether the empty type should become product.
	 */
	public function test_shared_archive_query( mixed $post_type, bool $main, bool $shared, bool $scoped ): void {
		$query = Mockery::mock( \WP_Query::class );
		$query->allows( 'is_main_query' )->andReturn( $main );
		$query->allows( 'is_tax' )->with( TranslatedTypes::SHARED_ARCHIVES )->andReturn( $shared );
		$query->allows( 'get' )->with( 'post_type' )->andReturn( $post_type );
		$query->shouldReceive( 'set' )->with( 'post_type', 'product' )->times( $scoped ? 1 : 0 );

		( new TranslatedTypes() )->shared_archive_query( $query );

		$this->assertConditionsMet();
	}

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
	 * The 404 title is the request's: SEOPress's stored template is rewritten
	 * with WordPress's own 404 sentence, which the core language pack holds in
	 * the request's locale (the German request reads "Seite nicht gefunden").
	 * A title that does not carry that sentence passes through untouched.
	 */
	public function test_the_404_title_speaks_the_requests_language(): void {
		WP_Mock::userFunction( 'is_404', array( 'return' => true ) );
		WP_Mock::userFunction( '__' )->with( 'Page not found', 'default' )->andReturn( 'Seite nicht gefunden' );

		$this->assertSame(
			'Seite nicht gefunden | Linker',
			( new Seo() )->not_found_title( 'Page not found | Linker' )
		);

		// Another page's title is not the 404 title, whatever matches.
		$this->assertSame( 'Genie - Linker\'s AI assistant | Linker', ( new Seo() )->not_found_title( 'Genie - Linker\'s AI assistant | Linker' ) );
	}

	/**
	 * The English request: the core pack answers with the English words, so the
	 * title comes back as SEOPress wrote it.
	 */
	public function test_the_english_404_title_is_unchanged(): void {
		WP_Mock::userFunction( 'is_404', array( 'return' => true ) );
		WP_Mock::userFunction( '__' )->with( 'Page not found', 'default' )->andReturn( 'Page not found' );

		$this->assertSame( 'Page not found | Linker', ( new Seo() )->not_found_title( 'Page not found | Linker' ) );
	}

	/**
	 * Not a 404: the filter leaves the title alone.
	 */
	public function test_a_page_title_is_left_alone(): void {
		WP_Mock::userFunction( 'is_404', array( 'return' => false ) );

		$this->assertSame( 'Page not found | Linker', ( new Seo() )->not_found_title( 'Page not found | Linker' ) );
	}

	/**
	 * SEOPress's own noindex decision is retained on the English source, but
	 * the German twin inherits the source's per-page ruling at render time.
	 */
	public function test_the_german_twin_inherits_the_english_noindex_ruling(): void {
		WP_Mock::userFunction( 'is_admin', array( 'return' => false ) );
		WP_Mock::userFunction( 'is_singular', array( 'return' => true ) );
		WP_Mock::userFunction(
			'get_queried_object',
			array(
				'return' => PolylangDouble::post(
					6873,
					array( 'post_type' => 'page' )
				),
			)
		);
		WP_Mock::userFunction(
			'pll_get_post',
			array(
				'args'   => array( 6873, 'en' ),
				'return' => 623,
			)
		);
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'args'   => array( 623, '_seopress_robots_index', true ),
				'return' => 'yes',
			)
		);

		$this->assertSame( '1', ( new Seo() )->twin_noindex( '' ) );
		$this->assertSame(
			array( 'follow', 'noindex' ),
			( new Seo() )->twin_robots( array( 'index', 'follow' ) )
		);
		$this->assertConditionsMet();
	}

	/**
	 * The English source is not touched, and an ordinary German twin keeps
	 * SEOPress's own decision.
	 */
	public function test_the_noindex_mirror_is_scoped_to_a_different_twin(): void {
		WP_Mock::userFunction( 'is_admin', array( 'return' => false ) );
		WP_Mock::userFunction( 'is_singular', array( 'return' => true ) );
		WP_Mock::userFunction(
			'get_queried_object',
			array(
				'return' => PolylangDouble::post(
					623,
					array( 'post_type' => 'page' )
				),
			)
		);
		WP_Mock::userFunction(
			'pll_get_post',
			array(
				'args'   => array( 623, 'en' ),
				'return' => 623,
			)
		);

		$this->assertSame( '', ( new Seo() )->twin_noindex( '' ) );
		$this->assertSame(
			array( 'index', 'follow' ),
			( new Seo() )->twin_robots( array( 'index', 'follow' ) )
		);
		$this->assertConditionsMet();
	}

	/**
	 * Pages, posts, products and LiveCanvas partials and templates are translated;
	 * so are product categories and the attributes whose values are words.
	 */
	public function test_translated_types(): void {
		$types = new TranslatedTypes();
		$this->assertSame( array( 'page', 'post', 'product' ), TranslatedTypes::POST_TYPES );

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
