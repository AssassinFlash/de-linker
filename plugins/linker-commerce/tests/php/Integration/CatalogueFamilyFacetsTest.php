<?php
/**
 * Native catalogue facets count the same model families as the matching grid.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Storefront\ProductFilters;
use Linker\Commerce\Storefront\ProductFamilies;

/**
 * Woo variations and their shared published model list.
 *
 * @covers \Linker\Commerce\Storefront\ProductFilters
 */
final class CatalogueFamilyFacetsTest extends IntegrationTestCase {
	/** Real Woo products retain their individual model choices in one family. */
	public function test_facets_count_cards_and_keep_every_matching_model(): void {
		$ids     = array();
		$filters = new ProductFilters();
		foreach ( array( '10', '12', '25' ) as $kw ) {
			$id    = $this->product( '120' )->get_id();
			$ids[] = $id;
			update_post_meta(
				$id,
				\Linker\Commerce\Products\SelectionFacts::FIGURES_META_KEY,
				wp_json_encode(
					array(
						'ac_output_kw_nominal' => array(
							'value' => $kw,
							'unit'  => 'kW',
						),
					)
				)
			);
		}
		$family = array_slice( $ids, 0, 2 );
		foreach ( $family as $id ) {
			update_post_meta( $id, '_tv_legacy_acf_json', wp_json_encode( array( 'family_variants' => array_map( static fn( int $member ): array => array( 'id' => $member ), $family ) ) ) );
		}
		$rows = ( new ProductFamilies( $ids ) )->rows( $filters->matching( $ids, array( 'power' => 'mid' ) ) );
		self::assertCount( 1, $rows );
		self::assertSame( $family, $rows[0]['ids'] );
		self::assertSame( count( $rows ), $filters->facet_counts( $ids )['power']['mid']['count'] );
	}
}
