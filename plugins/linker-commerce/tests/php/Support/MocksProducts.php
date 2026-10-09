<?php
/**
 * Products as SelectionFacts reads them, for WP_Mock.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Support;

use WP_Mock;

/**
 * Mocks the WordPress reads of SelectionFacts::for_product() for one product:
 * its product categories, its pa_application and pa_phase terms and its
 * figures meta. Terms are plain objects with the WP_Term properties the
 * reading uses.
 */
trait MocksProducts {

	/**
	 * Mocks one product.
	 *
	 * @param int                $id          Product ID.
	 * @param array<int, string> $categories  Category slug by term ID.
	 * @param string[]           $application Slugs of the pa_application terms.
	 * @param string[]           $phase       Slugs of the pa_phase terms.
	 * @param mixed              $figures     What get_post_meta() returns for _tv_b2b_figures.
	 */
	protected function mock_product( int $id, array $categories, array $application, array $phase, mixed $figures ): void {
		$terms = array(
			'product_cat'    => $categories,
			'pa_application' => array_values( $application ),
			'pa_phase'       => array_values( $phase ),
		);
		foreach ( $terms as $taxonomy => $slugs ) {
			WP_Mock::userFunction(
				'get_the_terms',
				array(
					'args'   => array( $id, $taxonomy ),
					'return' => self::terms( $slugs ),
				)
			);
		}
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'args'   => array( $id, '_tv_b2b_figures', true ),
				'return' => $figures,
			)
		);
	}

	/**
	 * What get_the_terms() returns: false without terms, otherwise the terms.
	 *
	 * @param array<int, string> $slugs Slug by term ID.
	 * @return object[]|false
	 */
	private static function terms( array $slugs ): array|false {
		if ( array() === $slugs ) {
			return false;
		}
		$terms = array();
		foreach ( $slugs as $term_id => $slug ) {
			$terms[] = (object) array(
				'term_id' => $term_id,
				'slug'    => $slug,
			);
		}

		return $terms;
	}
}
