<?php
/**
 * Current Woo supply names for sentence fragments owned by LiveCanvas.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

use Linker\Commerce\Products\Publication;
use Linker\Commerce\Storefront\SitemapSync;

/** Aggregate native product attributes without reading technical documents. */
final class SupplyBrands {
	/**
	 * Active archive destinations for the current frontend language.
	 *
	 * @var array<string,array{label:string,url:string,id:int}>|null
	 */
	private ?array $archives = null;

	/** Register the data fragment; LC retains its words, markup and styling. */
	public function register(): void {
		add_shortcode( 'linker_supply_brands', array( $this, 'render' ) );
		add_shortcode( 'linker_brand_links', array( $this, 'links' ) );
	}

	/**
	 * Brand links lead to the same indexable archives published in the sitemap.
	 *
	 * @param array<string,string>|string $atts Header, mobile drawer, footer or archive.
	 */
	public function links( $atts = array() ): string {
		$variant = is_array( $atts ) ? ( $atts['variant'] ?? 'scope' ) : 'scope';
		if ( null === $this->archives ) {
			$terms = get_terms(
				array(
					'taxonomy'   => 'product_brand',
					'hide_empty' => true,
					'orderby'    => 'name',
				)
			);
			if ( ! is_array( $terms ) ) {
				return '';
			}
			$archives = array();
			$sitemap  = new SitemapSync();
			foreach ( $terms as $term ) {
				$link = get_term_link( $term );
				if ( ! is_string( $link ) ) {
					continue;
				}
				$entry = $sitemap->brand_urls( array( 'loc' => $link ), $term );
				if ( null !== $entry && in_array( $link, array( $entry['loc'], $entry['linker_brand_twin'] ?? '' ), true ) ) {
					$archives[ $term->slug ] = array(
						'label' => $term->name,
						'url'   => $link,
						'id'    => $term->term_id,
					);
				}
			}
			$order = array_flip( array( 'goodwe', 'saj', 'pylontech', 'chint' ) );
			uksort( $archives, static fn( string $a, string $b ): int => ( $order[ $a ] ?? 4 ) <=> ( $order[ $b ] ?? 4 ) );
			$this->archives = $archives;
		}
		if ( empty( $this->archives ) ) {
			return '';
		}
		$scope = 'scope' === $variant;
		$label = esc_html__( 'Brands', 'linker-commerce' );
		$html  = $scope ? '<nav class="wb-scope wb-brands sf-container" aria-label="' . esc_attr( $label ) . '">' : '<div class="brand-links"><strong>' . $label . '</strong>';
		foreach ( $this->archives as $brand ) {
			$active = $scope && is_tax( 'product_brand', $brand['id'] );
			$class  = $scope ? ' class="wbs' . ( $active ? ' on' : '' ) . '"' : '';
			$role   = 'header' === $variant ? ' role="menuitem"' : '';
			$html  .= '<a' . $class . $role . ( $active ? ' aria-current="page"' : '' ) . ' href="' . esc_url( $brand['url'] ) . '">' . esc_html( $brand['label'] ) . '</a>';
		}
		return $html . ( $scope ? '</nav>' : '</div>' );
	}

	/**
	 * Names belonging to currently published sales products in these branches.
	 *
	 * @param array<string,string>|string $atts LC sentence and category scope.
	 */
	public function render( $atts = array() ): string {
		$atts       = shortcode_atts(
			array(
				'categories'  => '',
				'prefix'      => '',
				'suffix'      => '',
				'conjunction' => 'and',
			),
			is_array( $atts ) ? $atts : array(),
			'linker_supply_brands'
		);
		$categories = array_values( array_filter( array_map( 'sanitize_title', explode( ',', $atts['categories'] ) ) ) );
		if ( array() === $categories ) {
			return '';
		}
		$ids = Publication::published_ids( fn (): array => $this->candidate_ids( $categories ), true );
		if ( array() === $ids ) {
			return '';
		}
		$names = get_terms(
			array(
				'taxonomy'   => 'pa_brand',
				'object_ids' => $ids,
				'fields'     => 'names',
				'hide_empty' => false,
				'orderby'    => 'name',
				'order'      => 'ASC',
			)
		);
		if ( ! is_array( $names ) || array() === $names ) {
			return '';
		}
		$names = array_values( array_unique( array_filter( array_map( 'trim', $names ) ) ) );
		if ( array() === $names ) {
			return '';
		}
		$last = array_pop( $names );
		$list = array() === $names ? $last : implode( ', ', $names ) . ' ' . $atts['conjunction'] . ' ' . $last;
		return esc_html( $atts['prefix'] . $list . $atts['suffix'] );
	}

	/**
	 * Read native candidates only inside Publication's freshly opened batch.
	 *
	 * Visibility term names are Woo's own identifiers. Resolve them natively,
	 * without wc_get_product_visibility_term_ids()'s unflushable static ID map.
	 *
	 * @param string[] $categories Native category branches.
	 * @return int[]
	 */
	private function candidate_ids( array $categories ): array {
		// Resolve outside WP_Tax_Query: Polylang otherwise scopes its internal
		// English-slug lookup to the active German frontend language.
		$terms = get_terms(
			array(
				'taxonomy'   => 'product_cat',
				'slug'       => $categories,
				'fields'     => 'ids',
				'hide_empty' => false,
				'lang'       => '',
			)
		);
		if ( ! is_array( $terms ) || array() === $terms ) {
			return array();
		}
		$tax_query = array(
			array(
				'taxonomy'         => 'product_cat',
				'field'            => 'term_id',
				'terms'            => array_map( 'intval', $terms ),
				'include_children' => true,
			),
		);
		$hidden    = array( 'exclude-from-catalog' );
		if ( 'yes' === get_option( 'woocommerce_hide_out_of_stock_items' ) ) {
			$hidden[] = 'outofstock';
		}
		$tax_query[] = array(
			'taxonomy' => 'product_visibility',
			'field'    => 'name',
			'terms'    => $hidden,
			'operator' => 'NOT IN',
		);
		$ids         = get_posts(
			array(
				'post_type'                   => 'product',
				'post_status'                 => 'publish',
				'fields'                      => 'ids',
				'posts_per_page'              => -1,
				'suppress_filters'            => true,
				'lang'                        => '',
				'linker_publication_internal' => true,
				'cache_results'               => false,
				'tax_query'                   => $tax_query, // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_tax_query -- the native category/visibility intersection, one query per fragment.
			)
		);
		return array_map( 'intval', $ids );
	}
}
