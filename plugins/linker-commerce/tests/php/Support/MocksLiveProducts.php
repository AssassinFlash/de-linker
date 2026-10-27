<?php
/**
 * Live-catalogue products as the Genie abilities read them, for WP_Mock.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Support;

use Linker\Commerce\Gating\CommerceState;
use Linker\Commerce\Abilities\PublicationData;
use Linker\Commerce\Products\EngineeringData;
use Linker\Commerce\Products\Publication\CompatibilityClaims;
use Linker\Commerce\Products\Publication\CompatibilityMigration;
use Linker\Commerce\Products\Publication\DocumentFiles;
use Linker\Commerce\Products\SelectionFacts;
use Linker\Commerce\Registration\Approval;
use Mockery;
use WC_Product;
use WP_Mock;

/**
 * Mocks the WordPress and WooCommerce reads of a set of fixture products:
 * categories, attributes, figures, titles, permalinks and a WC_Product with
 * a stored price. Pairing uses pa_model term names; the fixture only stores
 * slugs, so a small map restores the names Compatibility matches.
 */
trait MocksLiveProducts {
	/** Whether the cited-facts fixture migration is active.
	 *
	 * @var bool
	 */
	private bool $publication_migrated = false;

	/** Whether this case installed native product readers.
	 *
	 * @var bool
	 */
	private bool $live_products_mocked = false;

	/** Synthetic native Woo declarations populated by the explicit fixture migration.
	 *
	 * @var array<int,array<string,mixed>>
	 */
	private array $compatibility_fixture_claims = array();


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
	 * @param int[] $ids         Product IDs.
	 * @param bool  $migrated    Whether tools/migrate/7-facts.json is applied.
	 * @param bool  $sees_prices Whether the visitor is an approved account.
	 * @throws \LogicException When WP_Mock answers with another responder.
	 */
	protected function mock_live_products( array $ids, bool $migrated = false, bool $sees_prices = false ): void {
		$this->live_products_mocked = true;
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => static fn( mixed $value, int $flags = 0 ): string|false => json_encode( $value, $flags ) ) );
		WP_Mock::userFunction( 'wp_cache_supports', array( 'return' => true ) );
		WP_Mock::userFunction( 'wp_cache_flush_runtime', array( 'return' => true ) );
		WP_Mock::userFunction( 'wp_parse_url', array( 'return' => static fn( string $url, int $part = -1 ) => parse_url( $url, $part ) ) );
		WP_Mock::userFunction( 'home_url', array( 'return' => 'https://de-linker.com' ) );
		WP_Mock::userFunction( 'pll_get_post', array( 'return' => 0 ) )->byDefault();
		$this->publication_migrated = $migrated;
		WP_Mock::userFunction( 'metadata_exists' )->andReturnUsing( fn ( string $type, int $id, string $key ): bool => CompatibilityClaims::META_KEY === $key && isset( $this->compatibility_fixture_claims[ $id ] ) );
		$this->compatibility_fixture_claims = array();
		$products                           = LiveProducts::products( $migrated );
		$bindings                           = array();
		foreach ( $products as $id => $product ) {
			$figures = json_decode( $product['figures'], true );
			foreach ( is_array( $figures ) ? $figures : array() as $field => $entry ) {
				$citation = $entry['citation'] ?? array();
				$url      = $citation['url'] ?? ( isset( $citation['doc'] ) ? 'https://de-linker.com/wp-content/uploads/fixture/' . $citation['doc'] : null );
				if ( is_string( $url ) ) {
					$bindings[ $id ][ $field ] = array(
						'document_id'     => hash( 'sha256', $url ),
						'blob_sha256'     => hash( 'sha256', $url ),
						'figure_revision' => \Linker\Commerce\Products\Publication::revision( $entry ),
					);
				}
			}
		}
		// No language layer swaps a product: SelectionFacts asks has_filter()
		// first, and a test class earlier in the run may already have made
		// WP_Mock define the function for the rest of the process
		// (ComparisonLiveProductsTest has the same guard); CommerceState asks
		// the filter itself, and each fixture product answers for itself.
		WP_Mock::userFunction(
			'has_filter',
			array(
				'return' => false,
				'times'  => '0+',
			)
		);
		foreach ( $ids as $id ) {
			$responder = WP_Mock::onFilter( 'linker_commerce_facts_product_id' )->with( $id );
			if ( ! $responder instanceof \WP_Mock\Filter_Responder ) {
				throw new \LogicException( 'WP_Mock::onFilter() answers with a Filter_Responder.' );
			}
			$responder->reply( $id );
		}
		// An English request: the price line needs no locale switch.
		WP_Mock::userFunction( 'determine_locale', array( 'return' => 'en_US' ) );
		WP_Mock::userFunction( 'wp_strip_all_tags', array( 'return' => static fn ( string $html ): string => strip_tags( $html ) ) );
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
				'return' => function ( int $id, string $key ) use ( $products, $bindings ) {
					if ( CompatibilityClaims::META_KEY === $key ) {
						return $this->compatibility_fixture_claims[ $id ] ?? '';
					}
					$product = $products[ $id ] ?? null;
					if ( null === $product ) {
						return '';
					}
					if ( SelectionFacts::FIGURES_META_KEY === $key ) {
						return $product['figures'];
					}
					if ( \Linker\Commerce\Products\Publication\EvidenceBindings::META_KEY === $key ) {
						return $bindings[ $id ] ?? array();
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
		)->byDefault();
		WP_Mock::userFunction(
			'get_permalink',
			array(
				'return' => static function ( int $id ): string {
					return 'https://de-linker.com/product/' . $id . '/';
				},
			)
		)->byDefault();
		WP_Mock::userFunction(
			'get_post_type',
			array(
				'return' => static function ( int $id ) use ( $products ): string {
					return isset( $products[ $id ] ) ? 'product' : '';
				},
			)
		)->byDefault();
		WP_Mock::userFunction(
			'get_post_status',
			array(
				'return' => static function ( int $id ) use ( $products ): string {
					return $products[ $id ]['status'] ?? '';
				},
			)
		)->byDefault();
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => $sees_prices ) );
		if ( $sees_prices ) {
			// Customer 7 is an approved account, so CommerceState shows prices.
			WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 7 ) );
			WP_Mock::userFunction(
				'get_user_meta',
				array(
					'return' => static function ( int $user_id, string $key, bool $single = false ): string {
						unset( $single );

						return 7 === $user_id && Approval::STATUS_META === $key ? Approval::APPROVED : '';
					},
				)
			);
		}
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
					$product->allows( 'get_price_html' )->andReturn( '<span class="woocommerce-Price-amount">' . $id . '</span>' );
					$product->allows( 'is_in_stock' )->andReturn( true );

					return $product;
				},
			)
		);
		WP_Mock::userFunction( 'get_ancestors', array( 'return' => array() ) );
		WP_Mock::userFunction(
			'get_the_post_thumbnail_url',
			array(
				'return' => '',
				'times'  => '0+',
			)
		);
	}

	/** Synthetic permission for isolated qualification tests, without a filesystem copy.
	 * These aliases are test inputs, never a production citation migration.
	 *
	 * @return PublicationData
	 */
	protected function publication_data(): PublicationData {
		if ( ! $this->live_products_mocked ) {
			return new PublicationData(
				static fn (): array => array(
					'source_revision'        => 'fixture',
					'compatibility_revision' => 'fixture',
					'products'               => array(),
					'documents'              => array(),
				)
			);
		}
		return new PublicationData(
			function (): array {
				$products  = array();
				$documents = array();
				$fixture   = LiveProducts::published( $this->publication_migrated );
				foreach ( $fixture as $id => $product ) {
						$products[] = array(
							'product_id'           => $id,
							'product_revision'     => (string) $id,
							'model'                => self::MODEL_NAMES[ array_values( $product['attributes']['pa_model'] ?? array( '' ) )[0] ] ?? array_values( $product['attributes']['pa_model'] ?? array( '' ) )[0],
							'published_locale_ids' => array( $id ),
						);
						$figures    = json_decode( $product['figures'], true );
					foreach ( is_array( $figures ) ? $figures : array() as $entry ) {
						$citation = is_array( $entry ) ? ( $entry['citation'] ?? array() ) : array();
						$url      = $citation['url'] ?? ( isset( $citation['doc'] ) ? 'https://de-linker.com/wp-content/uploads/fixture/' . $citation['doc'] : null );
						if ( is_string( $url ) ) {
							$key                                = hash( 'sha256', $url );
							$documents[ $key ]                ??= array(
								'document_id'       => $key,
								'document_revision' => $key,
								'blob_sha256'       => $key,
								'url'               => $url,
								'aliases'           => array( $url ),
								'product_ids'       => array(),
								'title'             => basename( $url ),
								'type'              => 'datasheet',
								'lang'              => 'en',
							);
							$documents[ $key ]['product_ids'][] = $id;
						}
					}
				}
				$input = EngineeringData::json( EngineeringData::COMPATIBILITY_FILE );
				foreach ( array_merge( $input['pairs'] ?? array(), $input['requirements'] ?? array() ) as $pair ) {
					foreach ( (array) ( $pair['documents'] ?? array() ) as $document ) {
						$url               = $document['url'];
						$key               = DocumentFiles::id( $url );
						$documents[ $key ] = array(
							'document_id'       => $key,
							'document_revision' => $key,
							'blob_sha256'       => $key,
							'url'               => $url,
							'aliases'           => array( $url ),
							'product_ids'       => array_keys( $fixture ),
							'title'             => basename( $url ),
							'type'              => 'compatibility',
							'lang'              => 'en',
						);
					}
				}
				$manifest = array(
					'source_revision'        => 'fixture',
					'compatibility_revision' => 'fixture',
					'products'               => $products,
					'documents'              => array_values( $documents ),
				);
				if ( is_array( $input ) ) {
					foreach ( CompatibilityMigration::plan( $input, str_repeat( 'a', 64 ), $manifest )['changes'] as $change ) {
						$this->compatibility_fixture_claims[ $change['product_id'] ] = $change['after'];
					}
				}
				return $manifest;
			}
		);
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
