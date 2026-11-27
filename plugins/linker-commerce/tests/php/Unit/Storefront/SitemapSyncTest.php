<?php
/**
 * Public brand sitemap membership and index freshness.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Storefront;

use Linker\Commerce\Storefront\SitemapSync;
use WP_Mock;
use Linker\Commerce\Tests\TestCase;

/**
 * Public outputs supplied to the SEOPress sitemap serializer.
 *
 * @covers \Linker\Commerce\Storefront\SitemapSync
 */
final class SitemapSyncTest extends TestCase {
	/**
	 * A shared term can have published equipment in either or both languages.
	 *
	 * @dataProvider languages
	 * @param string[] $live Languages with models.
	 */
	public function test_brand_entries_reflect_available_languages( array $live ): void {
		$sync = new SitemapSync();
		$term = new \WP_Term(
			(object) array(
				'taxonomy' => 'product_brand',
				'slug'     => 'testbrand',
				'term_id'  => 42,
			)
		);
		WP_Mock::userFunction( 'get_posts' )->andReturnUsing(
			function ( $args ) use ( $live ) {
				$this->assertSame( 'publish', $args['post_status'] );
				$this->assertSame( 'product', $args['post_type'] );
				$tax = array_column( $args['tax_query'], null, 'taxonomy' );
				$this->assertSame( 42, $tax['product_brand']['terms'] );
				return in_array( $tax['language']['terms'], $live, true ) ? array( 12 ) : array();
			}
		);
		WP_Mock::userFunction( 'esc_url', array( 'return_arg' => 0 ) );
		WP_Mock::userFunction( 'get_option' )->with( 'home' )->andReturn( 'https://linker.test/' );
		WP_Mock::userFunction( 'trailingslashit', array( 'return' => static fn( $s ) => rtrim( $s, '/' ) . '/' ) );
		$entry = $sync->brand_urls( array( 'loc' => 'https://linker.test/brand/testbrand/' ), $term );
		if ( ! $live ) {
			$this->assertNull( $entry );
			return;
		}
		$this->assertIsArray( $entry );
		$xml = $sync->brand_xml( '<url><loc>' . $entry['loc'] . '</loc></url>', $entry );
		$this->assertSame( count( $live ), substr_count( $xml, '<loc>' ) );
		foreach ( $live as $lang ) {
			$this->assertStringContainsString( '<loc>https://linker.test/' . ( 'de' === $lang ? 'de/' : '' ) . 'brand/testbrand/</loc>', $xml );
		}
	}

	/**
	 * Published-model languages on a shared manufacturer term.
	 *
	 * @return array<string,array<int,array<int,string>>>
	 */
	public function languages(): array {
		return array(
			'both'         => array( array( 'en', 'de' ) ),
			'german only'  => array( array( 'de' ) ),
			'english only' => array( array( 'en' ) ),
			'retired'      => array( array() ),
		);
	}

	/** Saves and deletions invalidate native index entries at the configured pagination size. */
	public function test_index_cache_refreshes_for_pages_and_products(): void {
		$sync = new SitemapSync();
		$this->filter_returns( 'seopress_sitemaps_max_posts_per_sitemap', 250, array( 1000 ) );
		foreach ( array( 'page', 'product' ) as $type ) {
			foreach ( array( 250, 1000 ) as $size ) {
				WP_Mock::userFunction( 'delete_transient' )->with( 'seopress_sitemap_lastmod_all_' . $type . '_' . $size )->once();
			}
		}
		$sync->post_changed( 7, new \WP_Post( (object) array( 'post_type' => 'page' ) ) );
		$sync->product_changed();
		$this->assertSame( 900, $sync->cache_duration( 43200 ) );
		$this->assertSame( 60, $sync->cache_duration( 60 ) );
		$this->assertSame( 900, $sync->cache_duration( 0 ) );
	}
}
