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
}
