<?php
/**
 * Archive rails and family cards share each product's source reads.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products;

use Linker\Commerce\Products\Materials;
use Linker\Commerce\Products\SelectionFacts;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Repeated archive reads of native and translated models.
 *
 * @covers \Linker\Commerce\Products\SelectionFacts
 * @covers \Linker\Commerce\Products\Materials
 */
final class ArchiveProductReadsTest extends TestCase {

	/**
	 * Both locale IDs share facts and keep separate display fields.
	 *
	 * @runInSeparateProcess
	 * @preserveGlobalState disabled
	 */
	public function test_archive_reads_one_figures_json_and_one_acf_json_per_language(): void {
		$reads  = array();
		$german = false;
		WP_Mock::userFunction( 'linker_i18n_is_de' )->andReturnUsing(
			static function () use ( &$german ): bool {
				return $german;
			}
		);
		WP_Mock::userFunction( 'has_filter' )->andReturn( true );
		$this->english_products(
			array(
				51 => 51,
				91 => 51,
			)
		);
		WP_Mock::userFunction( 'get_the_terms' )->andReturn( false );
		WP_Mock::userFunction( 'pll_get_post_language' )->andReturnUsing( static fn( int $id ): string => 91 === $id ? 'de' : 'en' );
		WP_Mock::userFunction( 'pll_get_post' )->with( 91, 'en' )->andReturn( 51 );
		WP_Mock::userFunction( 'get_post_meta' )->andReturnUsing(
			static function ( int $id, string $key ) use ( &$reads ): string {
				$reads[ $key ][ $id ] = ( $reads[ $key ][ $id ] ?? 0 ) + 1;
				return match ( $key ) {
					'_tv_legacy_acf_json' => '{"product_series":"ET Series"}',
					'_linker_de_acf_json' => 51 === $id ? '{"product_series":"ET-Serie"}' : '',
					default => '{"rated_ac_power_kw":{"value":"12","unit":"kW"}}',
				};
			}
		);
		foreach ( array( false, true, false, true ) as $german ) {
			$id = $german ? 91 : 51;
			self::assertSame( 12.0, SelectionFacts::for_product( $id )->ac_power_kw );
			self::assertSame( $german ? 'ET-Serie' : 'ET Series', Materials::acf( $id )['product_series'] );
		}
		self::assertSame( array( 51 => 1 ), $reads[ SelectionFacts::FIGURES_META_KEY ] );
		self::assertSame( array( 51 => 1 ), $reads['_tv_legacy_acf_json'] );
		self::assertSame(
			array(
				91 => 1,
				51 => 1,
			),
			$reads['_linker_de_acf_json']
		);
	}
}
