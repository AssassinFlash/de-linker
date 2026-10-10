<?php
/**
 * Live-catalogue products as the Genie abilities read them, for WP_Mock.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Support;

use Linker\Commerce\Catalog\SelectionFacts;
use Linker\Commerce\Gating\CommerceState;
use Mockery;
use WC_Product;
use WP_Mock;

/**
 * Mocks the WordPress and WooCommerce reads of a set of fixture products:
 * categories, attributes, figures, titles, permalinks and a WC_Product with
 * a stored price. Pairing uses pa_model term names; the fixture only stores
 * slugs, so a small map restores the names Compatibility matches.
 */
trait MocksCatalogue {

	/**
	 * Model slugs of the fixture mapped to the names the compatibility contract uses.
	 */
	private const MODEL_NAMES = array(
		'h2-10k-t3'        => 'H2-10K-T3',
		'gw10k-eta-g20'    => 'GW10K-ETA-G20',
		'gw5-1-bat-d-g20'  => 'GW5.1-BAT-D-G20',
		'b2-5-0-hv1'       => 'B2-5.0-HV1',
		'b2-10-0-hv1'      => 'B2-10.0-HV1',
		'bu2-5-0-hv1'      => 'BU2-5.0-HV1',
		'hs2-10k-t2-x'     => 'HS2-10K-T2-X',
		'hs2-5k-t2-x'      => 'HS2-5K-T2-X',
		'hs2-6k-t2-x'      => 'HS2-6K-T2-X',
		'hs3-5k-t2-w-g-px' => 'HS3-5K-T2-W/G-PX',
		'gw80k-etr-g10'    => 'GW80K-ETR-G10',
		'ef-hd-p3-10k0-s2' => 'EF HD-P3-10K0-S2',
		'ef-bd-5-s2'       => 'EF BD-5-S2',
	);

	/**
	 * Mocks the given fixture products (and nothing else).
	 *
	 * @param int[] $ids      Product IDs.
	 * @param bool  $migrated Whether tools/migrate/7-facts.json is applied.
	 */
	protected function mock_catalogue( array $ids, bool $migrated = false ): void {
		$products = LiveCatalogue::products( $migrated );
		WP_Mock::userFunction(
			'get_the_terms',
			array(
				'return' => static function ( int $id, string $taxonomy ) use ( $products ) {
					$product = $products[ $id ] ?? null;
					if ( null === $product ) {
						return false;
					}
					if ( 'product_cat' === $taxonomy ) {
						return self::term_objects( $product['categories'] );
					}
					$slugs = $product['attributes'][ $taxonomy ] ?? array();

					return self::term_objects( array_values( $slugs ) );
				},
			)
		);
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'return' => static function ( int $id, string $key ) use ( $products ) {
					$product = $products[ $id ] ?? null;
					if ( null === $product ) {
						return '';
					}
					if ( SelectionFacts::FIGURES_META_KEY === $key ) {
						return $product['figures'];
					}
					if ( CommerceState::MODE_META === $key ) {
						return '';
					}

					return '';
				},
			)
		);
		WP_Mock::userFunction(
			'get_the_title',
			array(
				'return' => static function ( int $id ) use ( $products ): string {
					return $products[ $id ]['name'] ?? '';
				},
			)
		);
		WP_Mock::userFunction(
			'get_permalink',
			array(
				'return' => static function ( int $id ): string {
					return 'https://de-linker.com/product/' . $id . '/';
				},
			)
		);
		WP_Mock::userFunction(
			'get_post_type',
			array(
				'return' => static function ( int $id ) use ( $products ): string {
					return isset( $products[ $id ] ) ? 'product' : '';
				},
			)
		);
		WP_Mock::userFunction(
			'get_post_status',
			array(
				'return' => static function ( int $id ) use ( $products ): string {
					return $products[ $id ]['status'] ?? '';
				},
			)
		);
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => false ) );
		WP_Mock::userFunction(
			'wc_get_product',
			array(
				'return' => static function ( int $id ) use ( $products ) {
					if ( ! isset( $products[ $id ] ) ) {
						return false;
					}
					$product = Mockery::mock( WC_Product::class );
					$product->allows( 'get_id' )->andReturn( $id );
					$product->allows( 'get_parent_id' )->andReturn( 0 );
					$product->allows( 'get_price' )->with( 'edit' )->andReturn( (string) $id );
					$product->allows( 'get_sku' )->andReturn( '' );

					return $product;
				},
			)
		);
		WP_Mock::userFunction( 'get_ancestors', array( 'return' => array() ) );
	}

	/**
	 * Term objects SelectionFacts and Compatibility read: slug, and for pa_model a name.
	 *
	 * @param array<int, string> $slugs Slug by term ID, or a list of slugs.
	 * @return object[]|false
	 */
	private static function term_objects( array $slugs ): array|false {
		if ( array() === $slugs ) {
			return false;
		}
		$terms = array();
		foreach ( $slugs as $term_id => $slug ) {
			$terms[] = (object) array(
				'term_id' => $term_id,
				'slug'    => $slug,
				'name'    => self::MODEL_NAMES[ $slug ] ?? $slug,
			);
		}

		return $terms;
	}
}
