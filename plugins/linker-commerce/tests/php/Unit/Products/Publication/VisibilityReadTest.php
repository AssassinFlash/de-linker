<?php
/**
 * Native archive permissions refresh once per batch, never once per product.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products\Publication;

use Linker\Commerce\Products\EngineeringReference;
use Linker\Commerce\Products\Publication;
use Linker\Commerce\Products\Publication\Visibility;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WP_Mock;

/**
 * A cache-shaped fixture distinguishes native persisted state from runtime copies.
 *
 * @covers \Linker\Commerce\Products\Publication
 * @covers \Linker\Commerce\Products\Publication\Visibility
 */
final class VisibilityReadTest extends TestCase {

	/** A collection and its next read see source/mirror changes without PDF IO. */
	public function test_archive_refreshes_once_and_the_next_read_observes_withdrawal(): void {
		$persisted = array(
			11 => 'publish',
			12 => 'publish',
			13 => 'draft',
			14 => 'publish',
		);
		$runtime   = $persisted;
		$refreshes = 0;
		WP_Mock::userFunction( 'is_admin' )->andReturn( false );
		WP_Mock::userFunction( 'wp_cache_supports' )->with( 'flush_runtime' )->andReturn( true );
		WP_Mock::userFunction( 'wp_cache_flush_runtime' )->andReturnUsing(
			static function () use ( &$runtime, &$persisted, &$refreshes ): bool {
				$runtime = $persisted;
				++$refreshes;
				return true;
			}
		);
		WP_Mock::userFunction( 'get_posts' )->andReturnUsing(
			static function ( array $args ): array {
				self::assertFalse( $args['cache_results'] );
				self::assertTrue( $args['linker_publication_internal'] );
				return array( 11, 12, 13, 14 );
			}
		);
		WP_Mock::userFunction( 'get_post_type' )->andReturn( 'product' );
		WP_Mock::userFunction( 'get_post_status' )->andReturnUsing(
			static function ( int $id ) use ( &$runtime ): string {
				return $runtime[ $id ];
			}
		);
		WP_Mock::userFunction( 'get_post_meta' )->andReturnUsing( static fn ( int $id, string $key ): string => 14 === $id && EngineeringReference::ROLE_META_KEY === $key ? EngineeringReference::PV_MODULE : '' );
		WP_Mock::userFunction( 'has_filter' )->andReturn( true );
		foreach ( array(
			11 => 11,
			12 => 11,
			13 => 13,
			14 => 14,
		) as $locale => $source ) {
			$this->filter_returns( 'linker_commerce_facts_product_id', $source, array( $locale ) );
		}
		WP_Mock::userFunction( 'wp_upload_dir' )->andReturnUsing(
			static function (): never {
				throw new \LogicException( 'Archive permission batches must not inspect PDF files.' );
			}
		);
		$allowed = null;
		$query   = Mockery::mock( \WP_Query::class );
		$query->allows( 'get' )->with( 'post_type' )->andReturn( 'product' );
		$query->allows( 'get' )->with( 'linker_publication_internal' )->andReturn( false );
		$query->allows( 'get' )->with( 'post__in' )->andReturn( array( 11, 12, 13, 14 ) );
		$query->allows( 'is_preview' )->andReturn( false );
		$query->allows( 'set' )->with( 'post__in', Mockery::any() )->andReturnUsing(
			static function ( string $key, array $ids ) use ( &$allowed ): void {
				$allowed = $ids;
			}
		);
		$visibility = new Visibility();
		$visibility->query( $query );
		$this->assertSame( array( 11, 12 ), $allowed );
		$this->assertSame( 1, $refreshes );
		// A second process changes persisted state; the first read left a stale copy.
		$persisted[11] = 'draft';
		$visibility->query( $query );
		$this->assertSame( array( 0 ), $allowed );
		$this->assertSame( 2, $refreshes );
		$persisted[11] = 'publish';
		$persisted[12] = 'draft';
		$this->assertSame( array( 11 ), Publication::published_ids( array( 11, 12 ) ) );
		$this->assertSame( 3, $refreshes );
		$this->assertFalse( Publication::is_published( 12 ) );
		$this->assertSame( 4, $refreshes, 'The independent single-product authority remains fresh.' );
	}
}
