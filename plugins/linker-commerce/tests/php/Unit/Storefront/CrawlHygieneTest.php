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
	/** Product and comment feeds retire, while the blog RSS remains readable. */
	public function test_feed_responses(): void {
		$kind = 'none';
		foreach ( array( 'is_feed', 'is_comment_feed', 'is_post_type_archive', 'is_tax', 'is_singular' ) as $flag ) {
			WP_Mock::userFunction( $flag )->andReturnUsing(
				static function ( $type = null ) use ( &$kind, $flag ): bool {
					return match ( $flag ) {
						'is_feed'              => 'none' !== $kind,
						'is_comment_feed'      => 'comments' === $kind,
						'is_post_type_archive' => 'archive' === $kind && 'product' === $type,
						'is_tax'               => 'term' === $kind && array( 'product_cat', 'product_brand' ) === $type,
						default                => 'single' === $kind && 'product' === $type,
					};
				}
			);
		}
		$policy = new CrawlHygiene();
		self::assertSame( array(), $policy->headers( array() ) );
		$kind = 'blog';
		self::assertSame( array( 'X-Robots-Tag' => 'noindex, follow' ), $policy->headers( array() ) );
		$gone = new \RuntimeException( 'Gone' );
		WP_Mock::userFunction( 'status_header' )->with( 410 )->times( 4 )->andThrow( $gone );
		foreach ( array( 'comments', 'archive', 'term', 'single' ) as $kind ) {
			try {
				$policy->headers( array() );
				self::fail( $kind . ' should return 410' );
			} catch ( \RuntimeException $error ) {
				self::assertSame( $gone, $error );
			}
		}
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
