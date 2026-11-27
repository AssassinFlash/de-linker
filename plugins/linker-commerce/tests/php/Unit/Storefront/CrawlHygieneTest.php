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
