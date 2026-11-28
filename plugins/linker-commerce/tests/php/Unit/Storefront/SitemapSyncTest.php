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
	/** Both configurator pages publish their three localized UI captures once. */
	public function test_tool_sitemap_images(): void {
		$sync = new SitemapSync();
		WP_Mock::userFunction( 'pll_get_post' )->andReturn( 14 );
		WP_Mock::userFunction( 'get_post_field' )->with( 'post_name', 14 )->andReturn( 'solution-configurator' );
		WP_Mock::userFunction( 'pll_get_post_language' )->andReturnUsing( static fn( $id ) => 14 === $id ? 'en' : 'de' );
		WP_Mock::userFunction( 'plugins_url' )->andReturnUsing( static fn( $asset ) => 'https://linker.test/' . $asset );
		WP_Mock::passthruFunction( 'esc_url_raw' );
		foreach ( array(
			14 => 'en',
			15 => 'de',
		) as $id => $lang ) {
			$post = new \WP_Post(
				(object) array(
					'ID'        => $id,
					'post_type' => 'page',
					'post_name' => 'en' === $lang ? 'solution-configurator' : 'loesungskonfigurator',
				)
			);
			$xml  = $sync->page_images( '<url>', $post );
			self::assertSame( 3, substr_count( $xml, '<image:image>' ) );
			foreach ( array( 'compare', 'equipment', 'roof' ) as $view ) {
				self::assertStringContainsString( "/{$view}-{$lang}-1440.webp", $xml );
			}
			self::assertSame( $xml, $sync->page_images( $xml, $post ) );
		}
	}

	/** A plain query shortlink is excluded even during nested alternate resolution. */
	public function test_plain_post_url_stays_out_of_sitemap(): void {
		$post = new \WP_Post( (object) array( 'ID' => 42 ) );
		foreach ( array(
			array( 'loc' => 'https://example.test/?p=42' ),
			array(
				'loc'               => 'https://example.test/?p=42',
				'linker_alternates' => array(),
			),
		) as $entry ) {
			self::assertNull( ( new SitemapSync() )->post_entry( $entry, $post ) );
		}
	}

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
		$rows = array();
		foreach ( $live as $lang ) {
			$rows[] = $this->date_row( 'product_brand', 42, $lang );
		}
		$this->archive_rows( $rows );
		WP_Mock::userFunction( 'esc_url', array( 'return_arg' => 0 ) );
		WP_Mock::userFunction( 'get_option' )->with( 'home' )->andReturn( 'https://linker.test/' );
		WP_Mock::userFunction( 'trailingslashit', array( 'return' => static fn( $s ) => rtrim( $s, '/' ) . '/' ) );
		$entry = $sync->brand_urls( array( 'loc' => 'https://linker.test/brand/testbrand/' ), $term );
		if ( ! $live ) {
			$this->assertNull( $entry );
			return;
		}
		$this->assertIsArray( $entry );
		$doc   = $this->xml( $sync, $sync->entry_xml( '<url><loc>' . $entry['loc'] . '</loc></url>', $entry ) );
		$links = array();
		foreach ( $live as $lang ) {
			$links[ $lang ] = 'https://linker.test/' . ( 'de' === $lang ? 'de/marke/' : 'brand/' ) . 'testbrand/';
		}
		self::assertSame( count( $live ), $doc->getElementsByTagName( 'url' )->length );
		foreach ( $doc->getElementsByTagName( 'url' ) as $url ) {
			$loc  = $url->getElementsByTagName( 'loc' )->item( 0 )?->textContent;
			$lang = array_search( $loc, $links, true );
			self::assertIsString( $lang );
			$this->assert_links( $url, $links );
			$this->assert_date( $url, $lang );
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

	/**
	 * XML alternates are namespaced and point to exactly the indexable language pair.
	 *
	 * @param \DOMElement          $url   URL node.
	 * @param array<string,string> $links Published language URLs.
	 */
	private function assert_links( \DOMElement $url, array $links ): void {
		$actual = array();
		foreach ( $url->getElementsByTagNameNS( 'http://www.w3.org/1999/xhtml', 'link' ) as $link ) {
			self::assertSame( 'alternate', $link->getAttribute( 'rel' ) );
			$actual[ $link->getAttribute( 'hreflang' ) ] = $link->getAttribute( 'href' );
		}
		self::assertSame( isset( $links['en'], $links['de'] ) ? array_merge( $links, array( 'x-default' => $links['en'] ) ) : array(), $actual );
	}

	/**
	 * The date belongs to the language of the URL.
	 *
	 * @param \DOMElement $url URL element.
	 * @param string      $lang Language.
	 */
	private function assert_date( \DOMElement $url, string $lang ): void {
		self::assertSame( '2026-11-' . ( 'en' === $lang ? '20' : '25' ) . 'T12:00:00+00:00', $url->getElementsByTagName( 'lastmod' )->item( 0 )?->textContent );
	}

	/**
	 * Parse the same wrapper SEOPress uses.
	 *
	 * @param SitemapSync $sync Filter provider.
	 * @param string      $rows Serialized entries.
	 */
	private function xml( SitemapSync $sync, string $rows ): \DOMDocument {
		$doc = new \DOMDocument();
		self::assertTrue( $doc->loadXML( $sync->xmlns( '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' ) . $rows . '</urlset>' ) );
		self::assertSame( 'http://www.w3.org/1999/xhtml', $doc->getElementsByTagName( 'urlset' )->item( 0 )?->lookupNamespaceURI( 'xhtml' ) );
		return $doc;
	}

	/**
	 * Date returned by the grouped WordPress query.
	 *
	 * @param string $taxonomy Grouping taxonomy.
	 * @param int    $id       Term ID.
	 * @param string $lang     Language.
	 */
	private function date_row( string $taxonomy, int $id, string $lang ): object {
		return (object) array(
			'post_type' => 'category' === $taxonomy ? 'post' : 'product',
			'taxonomy'  => $taxonomy,
			'term_id'   => $id,
			'lang'      => $lang,
			'modified'  => '2026-11-' . ( 'en' === $lang ? '20' : '25' ) . ' 12:00:00',
		);
	}

	/**
	 * All rows must be served by one database aggregate.
	 *
	 * @param object[] $rows Grouped rows.
	 */
	private function archive_rows( array $rows ): void {
		$db = \Mockery::mock( \wpdb::class );
		foreach ( array( 'posts', 'terms', 'term_relationships', 'term_taxonomy' ) as $table ) {
			$db->$table = 'wp_' . $table;
		}
		$db->expects( 'get_results' )->once()->andReturn( $rows );
		$GLOBALS['wpdb'] = $db;
	}

	/** Release the database double used by the aggregate. */
	public function tearDown(): void {
		unset( $GLOBALS['wpdb'] );
		parent::tearDown();
	}

	/** Both term languages include products attached only to a child. */
	public function test_category_and_product_category_dates_cover_descendants(): void {
		$sync = new SitemapSync();
		$rows = array();
		$ids  = array(
			'en' => 12,
			'de' => 13,
		);
		foreach ( array( 'category', 'product_cat' ) as $tax ) {
			foreach ( $ids as $lang => $id ) {
				$rows[] = $this->date_row( $tax, $id + 100, $lang );
			}
		}
		$this->archive_rows( $rows );
		WP_Mock::userFunction( 'get_term_children' )->andReturnUsing( static fn( $id ) => array( $id + 100 ) );
		WP_Mock::userFunction( 'pll_get_term_translations' )->andReturn( $ids );
		WP_Mock::userFunction( 'get_term_meta' )->andReturn( '' );
		WP_Mock::userFunction( 'get_term_link' )->andReturnUsing( static fn( $id ) => "https://linker.test/cat/$id/" );
		$links = array(
			'en' => 'https://linker.test/cat/12/',
			'de' => 'https://linker.test/cat/13/',
		);
		foreach ( array( 'category', 'product_cat' ) as $tax ) {
			foreach ( $ids as $lang => $id ) {
				$term  = new \WP_Term(
					(object) array(
						'taxonomy' => $tax,
						'term_id'  => $id,
					)
				);
				$entry = $sync->term_entry( array( 'loc' => $links[ $lang ] ), $term );
				$doc   = $this->xml( $sync, $sync->entry_xml( '<url><loc>' . $links[ $lang ] . '</loc></url>', $entry ) );
				$url   = $doc->getElementsByTagName( 'url' )->item( 0 );
				self::assertNotNull( $url );
				$this->assert_links( $url, $links );
				$this->assert_date( $url, $lang );
			}
			WP_Mock::userFunction( 'wp_cache_supports' )->with( 'flush_runtime' )->andReturn( true );
			WP_Mock::userFunction( 'wp_cache_flush_runtime' )->andReturn( true );
			WP_Mock::userFunction( 'get_posts' )->andReturn( array() );
			WP_Mock::userFunction( 'get_option' )->with( 'linker_publication_document_hashes_v1', array() )->andReturn( array() );
			WP_Mock::userFunction( 'get_option' )->with( 'home' )->andReturn( 'https://linker.test/' );
			WP_Mock::passthruFunction( 'esc_xml' );
			$index = $sync->index_xml( "<sitemapindex><sitemap><loc>https://linker.test/$tax-sitemap1.xml</loc>\n</sitemap></sitemapindex>" );
			self::assertStringContainsString( '<lastmod>2026-11-25T12:00:00+00:00</lastmod>', $index );
			self::assertSame( 1, substr_count( $index, 'https://linker.test/pdf-sitemap1.xml</loc><lastmod>' ) );
			self::assertSame( $index, $sync->index_xml( $index ) );
		}
	}

	/** Post, page and product twins retain their native lastmod when alternates are added. */
	public function test_translated_posts_and_unpaired_post(): void {
		$sync  = new SitemapSync();
		$ids   = array(
			'en' => 12,
			'de' => 13,
		);
		$links = array(
			'en' => 'https://linker.test/story/',
			'de' => 'https://linker.test/de/beitrag/',
		);
		$posts = array();
		foreach ( $ids as $lang => $id ) {
			$posts[ $id ] = new \WP_Post( (object) array( 'ID' => $id ) );
		}
		WP_Mock::userFunction( 'get_post' )->andReturnUsing( static fn( $id ) => $posts[ $id ] );
		WP_Mock::userFunction( 'get_permalink' )->andReturnUsing( static fn( $post ) => $links[ 12 === $post->ID ? 'en' : 'de' ] );
		WP_Mock::userFunction( 'pll_get_post_translations' )->andReturn( $ids );
		foreach ( $ids as $lang => $id ) {
			$other_id = 12 === $id ? 13 : 12;
			$row      = array(
				'loc'               => $links[ 'en' === $lang ? 'de' : 'en' ],
				'linker_alternates' => array(),
			);
			$this->filter_returns( 'seopress_sitemaps_single_url', $row, array( $row, $posts[ $other_id ] ) );
			$entry = $sync->post_entry( array( 'loc' => $links[ $lang ] ), $posts[ $id ] );
			$doc   = $this->xml( $sync, $sync->entry_xml( '<url><loc>' . $links[ $lang ] . '</loc><lastmod>2026-11-26T09:00:00Z</lastmod></url>', $entry ) );
			$url   = $doc->getElementsByTagName( 'url' )->item( 0 );
			self::assertNotNull( $url );
			$this->assert_links( $url, $links );
			self::assertSame( 1, $doc->getElementsByTagName( 'lastmod' )->length );
		}
		$posts[13]->post_status = 'draft';
		$entry                  = $sync->post_entry( array( 'loc' => $links['en'] ), $posts[12] );
		self::assertSame( array( 'en' => $links['en'] ), $entry['linker_alternates'] ?? null );
	}

	/** Archive links emitted outside the post entry filter also carry reciprocal tags and dates. */
	public function test_product_archive_dates_and_links(): void {
		$sync  = new SitemapSync();
		$ids   = array(
			'en' => 12,
			'de' => 13,
		);
		$links = array(
			'en' => 'https://linker.test/products/',
			'de' => 'https://linker.test/de/produkte/',
		);
		$this->archive_rows( array( $this->date_row( 'language', 2, 'en' ), $this->date_row( 'language', 4, 'de' ) ) );
		WP_Mock::userFunction( 'get_option' )->with( 'woocommerce_shop_page_id' )->andReturn( 12 );
		WP_Mock::userFunction( 'pll_get_post_translations' )->with( 12 )->andReturn( $ids );
		WP_Mock::userFunction( 'get_post' )->andReturnUsing( static fn( $id ) => new \WP_Post( (object) array( 'ID' => $id ) ) );
		WP_Mock::userFunction( 'get_permalink' )->andReturnUsing( static fn( $post ) => $links[ 12 === $post->ID ? 'en' : 'de' ] );
		WP_Mock::userFunction( 'esc_url', array( 'return_arg' => 0 ) );
		WP_Mock::userFunction( 'get_post_meta' )->andReturn( '' );
		foreach ( $links as $lang => $link ) {
			$doc = $this->xml( $sync, $sync->archive_xml( '<url><loc>' . $link . '</loc></url>', 'product' ) );
			$url = $doc->getElementsByTagName( 'url' )->item( 0 );
			self::assertNotNull( $url );
			$this->assert_links( $url, $links );
			$this->assert_date( $url, $lang );
		}
	}

	/** SEOPress also calls the XML hook when an omitted Woo page has no entry. */
	public function test_excluded_page_stays_out_of_post_sitemaps(): void {
		$this->assertSame( '', ( new SitemapSync() )->entry_xml( '', null ) );
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
		WP_Mock::expectAction( 'litespeed_purge', 'LK.pdf.sitemap' );
		$sync->product_changed();
		$this->assertSame( 900, $sync->cache_duration( 43200 ) );
		$this->assertSame( 60, $sync->cache_duration( 60 ) );
		$this->assertSame( 900, $sync->cache_duration( 0 ) );
	}
}
