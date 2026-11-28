<?php
/**
 * Localized equipment and guide links.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Storefront;

use Linker\Commerce\Presentation\PageUrls;
use Linker\Commerce\Products\Publication;
use WP_Post;
use WP_Term;

/** Resolve the editorial guide selection against published posts, terms and Woo models. */
final class GuideEquipmentMesh {
	private const MATRIX_GUIDES = array(
		'installer-checklist-inverter-battery-pairing',
		'hybrid-inverter-vs-ac-coupled-storage',
		'solar-plus-storage-commissioning-checklist',
		'ci-storage-peak-shaving-backup-scalability',
	);

	/** Canonical mappings for the journal.
	 *
	 * @return array<string,array{technical:bool,categories:list<string>,brands:list<string>,topics:list<string>,skus:list<string>,matrix:bool}>
	 */
	public static function entries(): array {
		static $entries = null;
		// phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- Checked-in editorial mappings.
		$entries ??= json_decode( (string) file_get_contents( dirname( __DIR__, 2 ) . '/data/guide-equipment-mesh.json' ), true, 512, JSON_THROW_ON_ERROR );
		return $entries;
	}

	/** Current journal entry with its public local equipment, category and matrix links.
	 *
	 * @param WP_Post $post Guide on display.
	 * @return array<string,mixed>
	 */
	public static function for_post( WP_Post $post ): array {
		if ( 'post' !== $post->post_type ) {
			return array();
		}
		$lang  = self::language();
		$slug  = 'en' === $lang ? $post->post_name : get_post_field( 'post_name', (int) pll_get_post( $post->ID, 'en' ) );
		$entry = self::entries()[ $slug ] ?? null;
		if ( ! $entry ) {
			return array();
		}
		$ids = array();
		foreach ( $entry['skus'] as $sku ) {
			$id = wc_get_product_id_by_sku( $sku );
			if ( $id ) {
				$ids[] = function_exists( 'pll_get_post' ) ? (int) pll_get_post( $id, $lang ) : $id;
			}
		}
		$categories = array();
		$sources    = get_terms(
			array(
				'taxonomy'   => 'product_cat',
				'lang'       => 'en',
				'slug'       => $entry['categories'],
				'hide_empty' => false,
			)
		);
		foreach ( is_array( $sources ) ? $sources : array() as $source ) {
			$term = 'en' === $lang ? $source : get_term( (int) pll_get_term( $source->term_id, $lang ), 'product_cat' );
			if ( $term instanceof WP_Term ) {
				$url = get_term_link( $term );
				if ( is_string( $url ) ) {
					$categories[] = array(
						'name' => html_entity_decode( $term->name, ENT_QUOTES | ENT_HTML5, 'UTF-8' ),
						'url'  => $url,
					);
				}
			}
		}
		return array(
			'technical'  => $entry['technical'],
			'topics'     => $entry['topics'],
			'brands'     => $entry['brands'],
			'products'   => SolutionProducts::links( Publication::published_ids( $ids ) ),
			'categories' => $categories,
			'matrix'     => $entry['matrix'] ? PageUrls::translated( 'inverter-battery-compatibility', $lang ) : '',
		);
	}

	/** Reading for this product's exact model, category or manufacturer.
	 *
	 * @param int $id Published local product.
	 * @return list<WP_Post>
	 */
	public static function for_product( int $id ): array {
		$source = Publication::canonical_id( $id );
		$cats   = get_the_terms( $source, 'product_cat' );
		$brands = get_the_terms( $source, 'product_brand' );
		return self::ranked(
			(string) get_post_meta( $source, '_sku', true ),
			is_array( $cats ) ? array_column( $cats, 'slug' ) : array(),
			is_array( $brands ) ? array_column( $brands, 'slug' ) : array(),
			3
		);
	}

	/** Reading for the current brand or category and general guides for the shop.
	 *
	 * @param WP_Term|null $term Current taxonomy archive.
	 * @return list<WP_Post>
	 */
	public static function for_archive( ?WP_Term $term ): array {
		if ( ! $term ) {
			return self::for_matrix();
		}
		if ( function_exists( 'pll_is_translated_taxonomy' ) && pll_is_translated_taxonomy( $term->taxonomy ) ) {
			$source = get_term( (int) pll_get_term( $term->term_id, 'en' ), $term->taxonomy );
			if ( $source instanceof WP_Term ) {
				$term = $source;
			}
		}
		return self::ranked( '', 'product_cat' === $term->taxonomy ? array( $term->slug ) : array(), 'product_brand' === $term->taxonomy ? array( $term->slug ) : array(), 4 );
	}

	/** Reading for the compatibility matrix.
	 *
	 * @return list<WP_Post>
	 */
	public static function for_matrix(): array {
		return self::local_guides( self::MATRIX_GUIDES, 4 );
	}

	/**
	 * Prefer exact model mentions to category matches, then manufacturer matches.
	 *
	 * @param string   $sku Source model.
	 * @param string[] $categories Source categories.
	 * @param string[] $brands Source manufacturers.
	 * @param int      $limit Maximum links.
	 * @return list<WP_Post>
	 */
	private static function ranked( string $sku, array $categories, array $brands, int $limit ): array {
		$scores = array();
		foreach ( self::entries() as $slug => $entry ) {
			$scores[ $slug ] = ( in_array( $sku, $entry['skus'], true ) ? 100 : 0 )
				+ 10 * count( array_intersect( $categories, $entry['categories'] ) )
				+ count( array_intersect( $brands, $entry['brands'] ) );
		}
		arsort( $scores, SORT_NUMERIC );
		$general = array( 'solar-plus-storage-commissioning-checklist', 'installer-handover-documentation-checklist', 'remote-monitoring-after-installation', 'gateway-meter-cloud-monitoring-data-layer' );
		return self::local_guides( array_unique( array_merge( array_keys( array_filter( $scores ) ), $general ) ), $limit );
	}

	/** Current language in a public request. */
	private static function language(): string {
		return function_exists( 'pll_current_language' ) && 'de' === pll_current_language() ? 'de' : 'en';
	}

	/**
	 * Look up the guide by its canonical slug and require a published twin in the current language.
	 *
	 * @param array<int,string> $slugs Preferred English guide slugs.
	 * @param int               $limit Maximum published guides.
	 * @return list<WP_Post>
	 */
	private static function local_guides( array $slugs, int $limit ): array {
		$lang   = self::language();
		$guides = array();
		foreach ( $slugs as $slug ) {
			$post = get_page_by_path( $slug, OBJECT, 'post' );
			if ( ! $post instanceof WP_Post || 'publish' !== $post->post_status ) {
				continue;
			}
			if ( 'de' === $lang ) {
				$id   = (int) pll_get_post( $post->ID, $lang );
				$post = $id ? get_post( $id ) : null;
			}
			if ( $post instanceof WP_Post && 'publish' === $post->post_status ) {
				$guides[] = $post;
				if ( count( $guides ) === $limit ) {
					break;
				}
			}
		}
		return $guides;
	}
}
