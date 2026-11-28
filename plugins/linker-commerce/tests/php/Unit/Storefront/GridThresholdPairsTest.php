<?php
/**
 * Both directions of the model comparisons in both site languages.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Storefront;

use Linker\Commerce\Storefront\GridThresholdPairs;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Seven bidirectional pairs remain within the visitor’s language.
 *
 * @covers \Linker\Commerce\Storefront\GridThresholdPairs
 */
final class GridThresholdPairsTest extends TestCase {
	/** The published twin is resolved by SKU and current page language. */
	public function test_seven_reciprocal_pairs(): void {
		$pairs = array(
			array( 'DLK-GOODWE-GW9999KETAG20', 'DLK-GOODWE-GW10KETAG20' ),
			array( 'DLK-GOODWE-GW29999KETAG20', 'DLK-GOODWE-GW30KETAG20' ),
			array( 'DLK-SAJ-H230KT3DE', 'DLK-SAJ-H225KT3' ),
			array( 'DLK-SAJ-CHS2299KT4X', 'DLK-SAJ-CHS230KT4X' ),
			array( 'DLK-GOODWE-GW9999KETG10', 'DLK-GOODWE-GW100KETG10' ),
			array( 'DLK-GOODWE-GW9999KETRG10', 'DLK-GOODWE-GW100KETRG10' ),
			array( 'DLK-GOODWE-GW12499KETRG10', 'DLK-GOODWE-ETR125' ),
		);
		$ids   = array_flip( array_merge( ...$pairs ) );
		$this->plain_text();
		WP_Mock::userFunction( 'wc_get_product_id_by_sku' )->andReturnUsing( static fn( string $sku ): int => $ids[ $sku ] + 1 );
		WP_Mock::userFunction( 'pll_get_post' )->andReturnUsing( static fn( int $id, string $lang ): int => $id + ( 'de' === $lang ? 100 : 0 ) );
		WP_Mock::userFunction( 'get_permalink' )->andReturnUsing( static fn( int $id ): string => "/product-{$id}/" );
		WP_Mock::userFunction( 'wp_cache_supports' )->andReturn( true );
		WP_Mock::userFunction( 'wp_cache_flush_runtime' )->andReturn( true );
		WP_Mock::userFunction( 'has_filter' )->andReturn( false );
		WP_Mock::userFunction( 'get_post_type' )->andReturn( 'product' );
		WP_Mock::userFunction( 'get_post_status' )->andReturn( 'publish' );
		WP_Mock::userFunction( 'get_post_meta' )->andReturn( '' );

		foreach ( $pairs as list( $a, $b ) ) {
			foreach ( array(
				$a => $b,
				$b => $a,
			) as $sku => $twin ) {
				foreach ( array( 'en', 'de' ) as $lang ) {
					$target = $ids[ $twin ] + ( 'de' === $lang ? 101 : 1 );
					$html   = GridThresholdPairs::render( $sku, $lang );
					self::assertStringContainsString( 'href="/product-' . $target . '/"', $html );
					self::assertStringContainsString( GridThresholdPairs::badge( $twin, $lang ), $html );
				}
			}
		}
		self::assertSame( '', GridThresholdPairs::render( 'unpaired', 'en' ) );
		self::assertSame( '124,99 kVA maximal', GridThresholdPairs::badge( 'DLK-GOODWE-GW12499KETRG10', 'de' ) );
	}
}
