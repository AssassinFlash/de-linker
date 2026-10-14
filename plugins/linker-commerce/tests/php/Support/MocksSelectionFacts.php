<?php
/**
 * Hand-built products' selection facts, for WP_Mock.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Support;

use WP_Mock;

/**
 * Mocks the reads the selection facts and the filter rail make of a set of
 * hand-built products: brand, application and phase terms plus the AC power
 * figure. The count tests only need those.
 */
trait MocksSelectionFacts {

	/**
	 * Mocks the given products' facts (and nothing else).
	 *
	 * @param array<int, array{brand: string, application: string, phase: int, kw: float}> $products Products by ID.
	 */
	protected function mock_selection_facts( array $products ): void {
		WP_Mock::userFunction(
			'get_the_terms',
			array(
				'return' => static function ( int $id, string $taxonomy ) use ( $products ) {
					if ( 'pa_brand' === $taxonomy ) {
						return array(
							(object) array(
								'slug' => $products[ $id ]['brand'],
								'name' => ucfirst( $products[ $id ]['brand'] ),
							),
						);
					}
					if ( 'pa_application' === $taxonomy ) {
						return array( (object) array( 'slug' => $products[ $id ]['application'] ) );
					}
					if ( 'pa_phase' === $taxonomy ) {
						return array( (object) array( 'slug' => 3 === $products[ $id ]['phase'] ? 'three-phase' : 'single-phase' ) );
					}
					return false;
				},
			)
		);
		WP_Mock::userFunction(
			'wp_get_post_terms',
			array(
				'return' => static function ( int $id, string $taxonomy ) use ( $products ) {
					if ( 'pa_brand' !== $taxonomy ) {
						return array();
					}
					return array(
						(object) array(
							'slug' => $products[ $id ]['brand'],
							'name' => ucfirst( $products[ $id ]['brand'] ),
						),
					);
				},
			)
		);
		WP_Mock::userFunction(
			'has_term',
			array(
				'return' => static fn ( string $slug, string $taxonomy, int $id ): bool => 'pa_brand' === $taxonomy && $products[ $id ]['brand'] === $slug,
			)
		);
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'return' => static function ( int $id, string $key ) use ( $products ) {
					if ( \Linker\Commerce\Products\SelectionFacts::FIGURES_META_KEY !== $key ) {
						return '';
					}
					return (string) json_encode(
						array(
							'ac_output_kw_nominal' => array(
								'value' => (string) $products[ $id ]['kw'],
								'unit'  => 'kW',
							),
						),
						JSON_UNESCAPED_SLASHES
					);
				},
			)
		);
		WP_Mock::userFunction( 'has_filter', array( 'return' => false ) );
	}
}
