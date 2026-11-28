<?php
/**
 * Feed and media responses on the public site.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Storefront;

use Linker\Commerce\Storefront\CrawlHygiene;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Responses for public feed and attachment URLs.
 *
 * @covers \Linker\Commerce\Storefront\CrawlHygiene
 */
final class CrawlHygieneTest extends TestCase {
	/**
	 * Product and comment feeds retire, while blog RSS remains readable.
	 *
	 * @dataProvider feed_requests
	 * @param string $kind Request type.
	 */
	public function test_feed_responses( string $kind ): void {
		WP_Mock::userFunction( 'is_feed' )->andReturn( 'none' !== $kind );
		WP_Mock::userFunction( 'is_comment_feed' )->andReturn( 'comments' === $kind );
		WP_Mock::userFunction( 'is_post_type_archive' )->with( 'product' )->andReturn( 'archive' === $kind );
		WP_Mock::userFunction( 'is_tax' )->with( array( 'product_cat', 'product_brand' ) )->andReturn( 'term' === $kind );
		WP_Mock::userFunction( 'is_singular' )->with( 'product' )->andReturn( 'single' === $kind );
		$policy = new CrawlHygiene();
		if ( in_array( $kind, array( 'none', 'blog' ), true ) ) {
			self::assertSame( 'blog' === $kind ? array( 'X-Robots-Tag' => 'noindex, follow' ) : array(), $policy->headers( array() ) );
			return;
		}
		WP_Mock::userFunction( 'status_header' )->with( 410 )->once()->andThrow( new \RuntimeException( 'Gone' ) );
		$this->expectException( \RuntimeException::class );
		$this->expectExceptionMessage( 'Gone' );
		$policy->headers( array() );
	}

	/**
	 * Native WordPress feed contexts.
	 *
	 * @return list<array{string}>
	 */
	public function feed_requests(): array {
		return array( array( 'none' ), array( 'blog' ), array( 'comments' ), array( 'archive' ), array( 'term' ), array( 'single' ) );
	}

	/** Add missing directives to the wildcard group exactly once. */
	public function test_robots_txt_keeps_crawler_groups_and_site_search(): void {
		$policy   = new CrawlHygiene();
		$special  = "User-agent: ArchiveBot\nDisallow: /\n";
		$original = $special . "User-agent: *\nDisallow: /*?intent=\nAllow: /wp-admin/admin-ajax.php\n\nSitemap: https://example.test/sitemaps.xml\n";
		$robots   = $policy->robots_txt( $original, true );
		self::assertStringStartsWith( $special . "User-agent: *\n", $robots );
		self::assertStringEndsWith( "Allow: /wp-admin/admin-ajax.php\n\nSitemap: https://example.test/sitemaps.xml\n", $robots );
		self::assertSame( $robots, $policy->robots_txt( $robots, true ) );
		foreach ( array( 'redirect_to', 'intent', 'linker_contact_selection', 'wc-ajax' ) as $key ) {
			self::assertSame( 1, substr_count( $robots, 'Disallow: /*?' . $key . '=' ) );
			self::assertSame( 1, substr_count( $robots, 'Disallow: /*?*' . $key . '=' ) );
		}
		self::assertStringNotContainsString( '/*?s=', $robots );
		self::assertSame( $original, $policy->robots_txt( $original, false ) );
	}

	/**
	 * Historical product searches and malformed selections retire on public reads.
	 *
	 * @dataProvider catalog_queries
	 * @param string $query Query fixture.
	 * @param bool   $shop On a catalog archive.
	 * @param bool   $gone Expected retirement.
	 */
	public function test_query_responses( string $query, bool $shop, bool $gone ): void {
		$before = $_GET; // phpcs:ignore WordPress.Security.NonceVerification.Recommended -- Restore request fixture.
		parse_str( $query, $params );
		$_GET = $params;
		try {
			WP_Mock::userFunction( 'is_admin' )->andReturn( false );
			WP_Mock::userFunction( 'wp_doing_ajax' )->andReturn( isset( $params['wc-ajax'] ) );
			WP_Mock::userFunction( 'is_feed' )->andReturn( false );
			WP_Mock::userFunction( 'is_shop' )->andReturn( $shop );
			WP_Mock::userFunction( 'is_product_taxonomy' )->andReturn( false );
			if ( $gone ) {
				WP_Mock::userFunction( 'status_header' )->with( 410 )->once()->andThrow( new \RuntimeException( 'Gone' ) );
				$this->expectExceptionMessage( 'Gone' );
			}
			self::assertSame( array(), ( new CrawlHygiene() )->headers( array() ) );
		} finally {
			$_GET = $before;
		}
	}

	/**
	 * Real search and archive query shapes.
	 *
	 * @return list<array{string,bool,bool}>
	 */
	public static function catalog_queries(): array {
		return array(
			array( 's&post_type=product&power=mid,high', false, true ),
			array( 's=goodwe', false, false ),
			array( 's=goodwe&post_type=post', false, false ),
			array( 'wc-ajax=%25%25endpoint%25%25', false, true ),
			array( 'wc-ajax=get_refreshed_fragments', false, false ),
			array( 'phase=3,1,1', true, true ),
			array( 'phase=3,1,1', false, false ),
			array( 'phase=3,1', true, false ),
		);
	}

	/** Only publicly viewable published parents receive an attachment redirect. */
	public function test_attachment_parent(): void {
		$parent = new \WP_Post(
			(object) array(
				'ID'          => 50,
				'post_status' => 'publish',
			)
		);
		WP_Mock::userFunction( 'get_post' )->with( 50 )->andReturn( $parent );
		WP_Mock::userFunction( 'is_post_publicly_viewable' )->with( $parent )->andReturn( true );
		WP_Mock::userFunction( 'get_permalink' )->with( $parent )->andReturn( 'https://example.test/about/' );
		WP_Mock::userFunction( 'trailingslashit' )->andReturnUsing( static fn( string $p ): string => rtrim( $p, '/' ) . '/' );
		$attachment = new \WP_Post(
			(object) array(
				'ID'          => 9,
				'post_parent' => 50,
			)
		);
		$policy     = new CrawlHygiene();
		self::assertSame( 'https://example.test/about/', $policy->attachment_parent( $attachment ) );
		$parent->post_status = 'draft';
		self::assertNull( $policy->attachment_parent( $attachment ) );
		$attachment->post_parent = 0;
		self::assertNull( $policy->attachment_parent( $attachment ) );
	}

	/** Missing products, hidden products and preview requests use distinct responses. */
	public function test_product_shortlinks(): void {
		$policy = new CrawlHygiene();
		$before = $_GET; // phpcs:ignore WordPress.Security.NonceVerification.Recommended -- Restore request fixture.
		$post   = new \WP_Post(
			(object) array(
				'ID'        => 42,
				'post_type' => 'product',
			)
		);
		WP_Mock::userFunction( 'get_post' )->andReturnUsing( static fn( $id ) => 42 === $id ? $post : null );
		WP_Mock::userFunction( 'is_admin' )->andReturn( false );
		WP_Mock::userFunction( 'wp_doing_ajax' )->andReturn( false );
		WP_Mock::userFunction( 'is_feed' )->andReturn( false );
		WP_Mock::userFunction( 'wp_cache_supports' )->andReturn( true );
		WP_Mock::userFunction( 'wp_cache_flush_runtime' )->andReturn( true );
		WP_Mock::userFunction( 'get_post_type' )->andReturn( 'product' );
		WP_Mock::userFunction( 'get_post_status' )->andReturn( 'publish' );
		WP_Mock::userFunction( 'get_post_meta' )->andReturn( '' );
		WP_Mock::userFunction( 'has_filter' )->andReturn( false );
		WP_Mock::userFunction( 'has_term' )->with( 'exclude-from-catalog', 'product_visibility', 42 )->andReturn( false, true );
		WP_Mock::userFunction( 'status_header' )->with( 410 )->andThrow( new \RuntimeException( 'Gone', 410 ) );
		try {
			$_GET = array(
				'post_type' => 'product',
				'p'         => '42',
			);
			self::assertSame( array(), $policy->headers( array() ) );
			foreach ( array( '42', '3255', '3588', '3589', '6593', '6652', '6668', '6671', '6675', '42abc', '0' ) as $id ) {
				$_GET['p'] = $id;
				try {
					$policy->headers( array() );
					self::fail( 'Retired product query reached the template.' );
				} catch ( \RuntimeException $error ) {
					self::assertSame( 410, $error->getCode() );
				}
			}
			$_GET['preview'] = 'true';
			WP_Mock::userFunction( 'is_user_logged_in' )->andReturn( true );
			self::assertSame( array(), $policy->headers( array() ) );
		} finally {
			$_GET = $before;
		}
	}

	/** Only the clean localized configurator links stay followable. */
	public function test_configurator_link_targets(): void {
		foreach ( array( '/solution-configurator/', '/de/loesungskonfigurator/' ) as $url ) {
			self::assertFalse( CrawlHygiene::nofollow_path( $url ) );
			foreach ( array( 'step=roof', 'utm_source=site&scope=storage_addition', 'compare=preliminary', 'projects=1', 'view=equipment' ) as $state ) {
				self::assertTrue( CrawlHygiene::nofollow_path( $url . '?' . $state ) );
			}
		}
	}

	/** Invalid changes never reach the SEOPress callback. */
	public function test_indexnow_forwards_only_indexable_public_posts(): void {
		$policy = new CrawlHygiene();
		$post   = new \WP_Post(
			(object) array(
				'ID'        => 7,
				'post_type' => 'post',
			)
		);
		WP_Mock::userFunction( 'seopress_instant_indexing_on_post_publish' )->with( 'publish', 'draft', $post )->once();
		foreach ( array( 'draft', 'private', 'trash', 'future' ) as $status ) {
			$policy->guard_instant_indexing( $status, 'publish', $post );
		}
		$post->post_password = 'private';
		$policy->guard_instant_indexing( 'publish', 'publish', $post );
		$post->post_password = '';
		WP_Mock::userFunction( 'get_post_meta' )->with( 7, '_seopress_robots_index', true )->andReturn( 'yes', '' );
		WP_Mock::userFunction( 'get_permalink' )->andReturn( 'https://example.test/?p=7', 'https://example.test/news__trashed/', 'https://example.test/news/' );
		foreach ( range( 1, 4 ) as $attempt ) {
			$policy->guard_instant_indexing( 'publish', 'draft', $post );
		}
		$post->post_type = 'product';
		WP_Mock::userFunction( 'wp_cache_supports' )->andReturn( true );
		WP_Mock::userFunction( 'wp_cache_flush_runtime' )->andReturn( true );
		WP_Mock::userFunction( 'get_post_type' )->andReturn( 'product' );
		WP_Mock::userFunction( 'get_post_status' )->andReturn( 'publish' );
		WP_Mock::userFunction( 'get_post_meta' )->with( 7, '_linker_engineering_role', true )->andReturn( '' );
		WP_Mock::userFunction( 'has_filter' )->andReturn( false );
		WP_Mock::userFunction( 'has_term' )->with( 'exclude-from-catalog', 'product_visibility', 7 )->andReturn( true );
		$policy->guard_instant_indexing( 'publish', 'draft', $post );
		$this->assertConditionsMet();
	}

	/** SEOPress batches are sanitized before the transport and unrelated requests pass through. */
	public function test_indexnow_filters_mixed_and_empty_batches(): void {
		$policy   = new CrawlHygiene();
		$endpoint = 'https://api.indexnow.org/indexnow/';
		$bad      = array( 'https://example.test/?post_type=product&p=1', 'https://example.test/?p=1', 'https://example.test/?page_id=2', 'https://example.test/news__trashed/' );
		$good     = 'https://example.test/news/';
		$mixed    = array_merge( $bad, array( $good ) );
		$args     = $policy->indexnow_args( array( 'body' => wp_json_encode( array( 'urlList' => $mixed ) ) ) );
		self::assertSame( array( $good ), json_decode( $args['body'], true )['urlList'] );
		$http = array( 'method' => 'POST' );
		self::assertFalse( $policy->skip_empty_indexnow( false, $http, $endpoint ) );
		$policy->indexnow_args( array( 'body' => wp_json_encode( array( 'urlList' => $bad ) ) ) );
		self::assertFalse( $policy->skip_empty_indexnow( false, $http, 'https://example.test/' ) );
		$response = $policy->skip_empty_indexnow( false, $http, $endpoint );
		self::assertSame( 200, $response['response']['code'] );
		self::assertFalse( $policy->skip_empty_indexnow( false, $http, $endpoint ) );
	}
}
