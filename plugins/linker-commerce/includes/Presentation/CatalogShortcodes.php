<?php
/**
 * The replica catalogue and product-page shortcodes: the dynamic blocks of the
 * design the site serves today, for the LiveCanvas templates to place.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

use Linker\Commerce\Catalog\SelectionFacts;
use Linker\Commerce\Storefront\CatalogFilters;
use Linker\Commerce\Storefront\ProductView;
use WC_Product;
use WP_Term;

/**
 * The catalogue head, the filter rail, the product card and the product-page
 * blocks carry the data; the LiveCanvas templates carry the page's static
 * structure and words. The markup answers the live page the templates
 * replicate (#16, owner ruling 2026-10-11): the same block order, the same
 * anchor classes (`tv-woo-b2b-catalog`, `sf-card`, `pdp-*`).
 */
final class CatalogShortcodes {

	/**
	 * Sets up the shortcodes.
	 *
	 * @param CatalogFilters $filters The catalogue's facet data.
	 * @param ProductView    $views   The product's replica fields.
	 */
	public function __construct(
		private readonly CatalogFilters $filters,
		private readonly ProductView $views
	) {}

	/**
	 * Registers the shortcodes.
	 */
	public function register(): void {
		add_shortcode( 'linker_catalog_head', array( $this, 'catalog_head' ) );
		add_shortcode( 'linker_catalog_filters', array( $this, 'catalog_filters' ) );
		add_shortcode( 'linker_catalog_sort', array( $this, 'catalog_sort' ) );
		add_shortcode( 'linker_catalog_empty', array( $this, 'catalog_empty' ) );
		add_shortcode( 'linker_catalog_card', array( $this, 'catalog_card' ) );
		add_shortcode( 'linker_pdp_brand_class', array( $this, 'pdp_brand_class' ) );
		add_shortcode( 'linker_pdp_crumbs', array( $this, 'pdp_crumbs' ) );
		add_shortcode( 'linker_pdp_gallery', array( $this, 'pdp_gallery' ) );
		add_shortcode( 'linker_pdp_buy', array( $this, 'pdp_buy' ) );
		add_shortcode( 'linker_pdp_description', array( $this, 'pdp_description' ) );
		add_shortcode( 'linker_pdp_specs', array( $this, 'pdp_specs' ) );
		add_shortcode( 'linker_pdp_scenes', array( $this, 'pdp_scenes' ) );
		add_shortcode( 'linker_pdp_downloads', array( $this, 'pdp_downloads' ) );
		add_shortcode( 'linker_pdp_pairings', array( $this, 'pdp_pairings' ) );
		add_shortcode( 'linker_pdp_disclosures', array( $this, 'pdp_disclosures' ) );
	}

	/**
	 * The catalogue head: breadcrumb row, title and intro, the search box,
	 * the tool entries and the category scope pills. On the shop page the
	 * title says Products; on a category archive it is the category's name.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function catalog_head( $atts = array() ): string {
		unset( $atts );
		$queried  = get_queried_object();
		$is_term  = $queried instanceof WP_Term;
		$shop_url = (string) wc_get_page_permalink( 'shop' );
		$action   = $is_term ? $this->term_link( $queried ) : $shop_url;
		$q        = (string) ( $this->filters->requested()['q'] ?? '' );

		$html  = '<div class="wb-head">';
		$html .= '<div class="wb-metarow container"><span class="wbm-l"><a href="' . esc_url( home_url( '/' ) ) . '">' . esc_html__( 'Home', 'linker-commerce' ) . '</a> / <a href="' . esc_url( $shop_url ) . '">' . esc_html__( 'Products', 'linker-commerce' ) . '</a>' . ( $is_term ? ' / <b>' . esc_html( $queried->name ) . '</b>' : ' / <b>' . esc_html__( 'Products', 'linker-commerce' ) . '</b>' ) . '</span></div>';
		$html .= '<div class="wb-bar container">';
		$html .= '<div class="wb-copy"><h1 class="wb-title">' . esc_html( $is_term ? $queried->name : __( 'Products', 'linker-commerce' ) ) . '</h1>';
		$html .= '<p class="wb-intro">' . esc_html( $is_term ? term_description( (int) $queried->term_id ) : __( 'Search products or filter by category and project requirements.', 'linker-commerce' ) ) . '</p></div>';
		$html .= '<form class="wb-search" method="get" action="' . esc_url( $action ) . '" role="search">';
		$html .= '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>';
		$html .= '<input id="search-box" name="q" type="search" placeholder="' . esc_attr__( 'Search model or item number', 'linker-commerce' ) . '" value="' . esc_attr( $q ) . '" aria-label="' . esc_attr__( 'Search products', 'linker-commerce' ) . '">';
		$html .= '<button type="submit" class="wb-go">' . esc_html__( 'Search', 'linker-commerce' ) . '</button>';
		$html .= '</form>';
		$html .= '</div>';
		$html .= $this->scope_nav( $shop_url, $is_term ? $queried->term_id : 0 );
		$html .= '</div>';
		return $html;
	}

	/**
	 * The category scope pills: all products plus every top-level product
	 * category, the current one marked.
	 *
	 * @param string $shop_url      The shop page address.
	 * @param int    $current_term  The category on display, 0 on the shop page.
	 */
	private function scope_nav( string $shop_url, int $current_term ): string {
		$categories = get_terms(
			array(
				'taxonomy'   => 'product_cat',
				'hide_empty' => true,
				'parent'     => 0,
				'exclude'    => array( (int) get_option( 'default_product_cat' ) ),
			)
		);
		if ( ! \is_array( $categories ) || array() === $categories ) {
			return '';
		}
		$html  = '<nav class="wb-scope container" aria-label="' . esc_attr__( 'Product categories', 'linker-commerce' ) . '">';
		$html .= '<a class="wbs' . ( 0 === $current_term ? ' on' : '' ) . '" href="' . esc_url( $shop_url ) . '">' . esc_html__( 'All products', 'linker-commerce' ) . '</a>';
		foreach ( $categories as $category ) {
			$on    = $category->term_id === $current_term ? ' on' : '';
			$html .= '<a class="wbs' . $on . '" href="' . esc_url( $this->term_link( $category ) ) . '">' . esc_html( $category->name ) . '</a>';
		}
		$html .= '</nav>';
		return $html;
	}

	/**
	 * The filter rail: category links, the facet sections, the two power and
	 * energy range forms, the configurator help and the Clear / Show actions.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function catalog_filters( $atts = array() ): string {
		unset( $atts );
		$facets     = $this->filters->facet_counts( $this->filters->archive_product_ids() );
		$selected   = $this->filters->requested();
		$queried    = get_queried_object();
		$is_term    = $queried instanceof WP_Term;
		$selected_n = \count( \array_diff_key( $selected, array( 'q' => '' ) ) );

		$html  = '<button type="button" class="catalog-filter-close" id="catalog-filter-close" aria-label="' . esc_attr__( 'Close filters', 'linker-commerce' ) . '">&times;</button>';
		$html .= '<details class="rail-fold" open>';
		$html .= '<summary class="rail-summary"><span>' . esc_html( sprintf( /* translators: %d: number of selected filters. */ _n( 'Filters (%d)', 'Filters (%d)', $selected_n, 'linker-commerce' ), $selected_n ) ) . '</span><span class="rail-summary-mark" aria-hidden="true"></span></summary>';
		$html .= '<div class="rail-body">';
		$html .= '<div class="rail-head"><span class="rail-head-label">' . esc_html__( 'Filters', 'linker-commerce' ) . '</span></div>';

		$categories = get_terms(
			array(
				'taxonomy'   => 'product_cat',
				'hide_empty' => true,
				'parent'     => 0,
				'exclude'    => array( (int) get_option( 'default_product_cat' ) ),
			)
		);
		if ( \is_array( $categories ) && array() !== $categories ) {
			$html .= '<details class="filter-section fgroup rail-nav" open>';
			$html .= '<summary class="filter-title">' . esc_html__( 'Category', 'linker-commerce' ) . '</summary>';
			$html .= '<div class="filter-options">';
			$html .= '<a class="family-link" href="' . esc_url( (string) wc_get_page_permalink( 'shop' ) ) . '"><span>' . esc_html__( 'All products', 'linker-commerce' ) . '</span></a>';
			foreach ( $categories as $category ) {
				$current = $is_term && $queried->term_id === $category->term_id;
				$html   .= '<a class="family-link' . ( $current ? ' is-current' : '' ) . '" href="' . esc_url( $this->term_link( $category ) ) . '"' . ( $current ? ' aria-current="page"' : '' ) . '><span>' . esc_html( $category->name ) . '</span></a>';
			}
			$html .= '</div></details>';
		}

		$facet_titles = array(
			'application' => __( 'Application', 'linker-commerce' ),
			'brand'       => __( 'Brand', 'linker-commerce' ),
			'phase'       => __( 'Phase', 'linker-commerce' ),
			'power'       => __( 'Power', 'linker-commerce' ),
		);
		foreach ( $facet_titles as $facet => $facet_title ) {
			if ( empty( $facets[ $facet ] ) ) {
				continue;
			}
			$html .= '<details class="filter-section fgroup' . ( 'power' === $facet ? ' rail-pills' : '' ) . '" open>';
			$html .= '<summary class="filter-title">' . esc_html( $facet_title ) . '</summary>';
			$html .= '<div class="filter-options">';
			foreach ( $facets[ $facet ] as $value => $option ) {
				if ( $option['count'] > 0 ) {
					$active = isset( $selected[ $facet ] ) && $selected[ $facet ] === (string) $value;
					$html  .= '<a class="filter-option' . ( $active ? ' active' : '' ) . '" href="' . esc_url( $this->filter_url( $facet, (string) $value ) ) . '" rel="nofollow">';
					$html  .= '<span class="filter-checkbox-wrap"><span class="filter-checkbox"></span><span>' . esc_html( $option['label'] ) . '</span></span>';
					$html  .= '<span class="filter-count">' . esc_html( (string) $option['count'] ) . '</span></a>';
				} else {
					$html .= '<span class="filter-option is-disabled" aria-disabled="true">';
					$html .= '<span class="filter-checkbox-wrap"><span class="filter-checkbox"></span><span>' . esc_html( $option['label'] ) . '</span></span>';
					$html .= '<span class="filter-count">0</span></span>';
				}
			}
			$html .= '</div></details>';
		}

		$html .= $this->range_form( __( 'AC power', 'linker-commerce' ), 'kw', __( 'Minimum AC power in kilowatts', 'linker-commerce' ), __( 'Maximum AC power in kilowatts', 'linker-commerce' ), 'kW', $selected );
		$html .= $this->range_form( __( 'Usable energy', 'linker-commerce' ), 'kwh', __( 'Minimum usable energy in kilowatt hours', 'linker-commerce' ), __( 'Maximum usable energy in kilowatt hours', 'linker-commerce' ), 'kWh', $selected );

		$html .= '</div></details>';
		$html .= '<div class="catalog-filter-actions">';
		$html .= '<a href="' . esc_url( $is_term ? $this->term_link( $queried ) : (string) wc_get_page_permalink( 'shop' ) ) . '">' . esc_html__( 'Clear', 'linker-commerce' ) . '</a>';
		$html .= '<button type="button" id="catalog-filter-apply">' . esc_html__( 'Show products', 'linker-commerce' ) . '</button>';
		$html .= '</div>';
		return $html;
	}

	/**
	 * A min–max range form: one GET navigation that keeps the other facets.
	 *
	 * @param string                      $title      Section title.
	 * @param string                      $prefix     Parameter prefix (kw, kwh).
	 * @param string                      $min_label  Min input aria-label.
	 * @param string                      $max_label  Max input aria-label.
	 * @param string                      $unit       Unit shown after the inputs.
	 * @param array<string, string|float> $selected   The request's selections.
	 */
	private function range_form( string $title, string $prefix, string $min_label, string $max_label, string $unit, array $selected ): string {
		$html  = '<details class="filter-section fgroup" open>';
		$html .= '<summary class="filter-title">' . esc_html( $title ) . '</summary>';
		$html .= '<div class="filter-options"><form class="frange" method="get" action="">';
		foreach ( $selected as $key => $value ) {
			if ( "{$prefix}_min" === $key || "{$prefix}_max" === $key ) {
				continue;
			}
			$html .= '<input type="hidden" name="' . esc_attr( (string) $key ) . '" value="' . esc_attr( (string) $value ) . '" />';
		}
		$html .= '<span class="frange-row">';
		$html .= '<input type="number" name="' . esc_attr( $prefix ) . '_min" inputmode="decimal" step="0.1" min="0" placeholder="min" value="' . esc_attr( (string) ( $selected[ "{$prefix}_min" ] ?? '' ) ) . '" aria-label="' . esc_attr( $min_label ) . '" /><i>&ndash;</i>';
		$html .= '<input type="number" name="' . esc_attr( $prefix ) . '_max" inputmode="decimal" step="0.1" min="0" placeholder="max" value="' . esc_attr( (string) ( $selected[ "{$prefix}_max" ] ?? '' ) ) . '" aria-label="' . esc_attr( $max_label ) . '" /><b>' . esc_html( $unit ) . '</b>';
		$html .= '<button type="submit" class="frange-go">' . esc_html__( 'Set', 'linker-commerce' ) . '</button>';
		$html .= '</span></form></div></details>';
		return $html;
	}

	/**
	 * A filter link: the current request's address with one facet set.
	 *
	 * @param string $facet The facet's query parameter.
	 * @param string $value The facet's value.
	 */
	private function filter_url( string $facet, string $value ): string {
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- plain GET navigation.
		$params = wp_unslash( $_GET );
		unset( $params[ $facet ], $params['sort'] );
		$params[ $facet ] = $value;
		return add_query_arg( $params );
	}

	/**
	 * The result strip's sort select: the catalogue's own orders, the request's
	 * other facets kept as hidden inputs.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function catalog_sort( $atts = array() ): string {
		unset( $atts );
		$selected = $this->filters->requested();
		$sort     = $this->filters->requested_sort();
		$labels   = array(
			'recommended' => __( 'Recommended', 'linker-commerce' ),
			'newest'      => __( 'Newest first', 'linker-commerce' ),
			'name'        => __( 'Name A-Z', 'linker-commerce' ),
			'power-desc'  => __( 'Power high-low', 'linker-commerce' ),
			'power-asc'   => __( 'Power low-high', 'linker-commerce' ),
		);
		$html     = '<form class="wbsort" method="get" action="">';
		foreach ( $selected as $key => $value ) {
			$html .= '<input type="hidden" name="' . esc_attr( (string) $key ) . '" value="' . esc_attr( (string) $value ) . '" />';
		}
		$html .= '<select class="select-dropdown" id="sort-select" name="sort" aria-label="' . esc_attr__( 'Sort products', 'linker-commerce' ) . '">';
		foreach ( $labels as $value => $label ) {
			$html .= '<option value="' . esc_attr( $value ) . '"' . selected( $sort, $value, false ) . '>' . esc_html( $label ) . '</option>';
		}
		$html .= '</select></form>';
		return $html;
	}

	/**
	 * The empty answer: the replica's "no product matches" note, only when
	 * the archive's query has no products. Reads the loop's state without
	 * advancing it — the grid's [lc_loop] after it still walks every post.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function catalog_empty( $atts = array() ): string {
		unset( $atts );
		if ( have_posts() ) {
			return '';
		}
		return '<div class="wb-empty"><p class="tv-empty-state">' . esc_html__( 'No product matches these filters. Clear one to see more.', 'linker-commerce' ) . '</p></div>';
	}

	/**
	 * The current product's catalogue card (inside [lc_loop]).
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function catalog_card( $atts = array() ): string {
		unset( $atts );
		$product_id = (int) get_the_ID();
		$card       = $this->views->fields( $product_id );
		if ( array() === $card ) {
			return '';
		}
		$facts = SelectionFacts::for_product( $product_id );
		$data  = array(
			'data-product-id="' . esc_attr( (string) $product_id ) . '"',
			'data-sku="' . esc_attr( $card['sku'] ) . '"',
			'data-brand="' . esc_attr( $card['brand_slug'] ) . '"',
			'data-phase="' . esc_attr( (string) $facts->phase ) . '"',
			'data-power="' . esc_attr( \is_float( $facts->ac_power_kw ) ? (string) $facts->ac_power_kw : '0' ) . '"',
			'data-application="' . esc_attr( (string) $facts->application ) . '"',
		);
		$url   = (string) get_permalink( $product_id );

		$html  = '<article class="sf-card product-card" data-linker-product-card ' . implode( ' ', $data ) . '>';
		$html .= '<div class="sf-card-media card-media"><a data-card-media-link href="' . esc_url( $url ) . '" aria-label="' . esc_attr( $card['title'] ) . '">';
		foreach ( \array_slice( (array) $card['gallery'], 0, 1 ) as $image_id ) {
			$html .= wp_get_attachment_image(
				(int) $image_id,
				'medium',
				false,
				array(
					'loading' => 'lazy',
					'alt'     => $card['title'],
				)
			);
		}
		$html .= '</a></div>';
		$html .= '<div class="card-identity">';
		if ( '' !== $card['brand'] ) {
			$html .= '<p class="sf-card-brand">' . esc_html( $card['brand'] ) . '</p>';
		}
		$html .= '<a class="sf-card-title" data-card-title href="' . esc_url( $url ) . '">' . esc_html( $card['model'] ) . '</a>';
		if ( '' !== $card['designation'] ) {
			$html .= '<p class="sf-card-designation">' . esc_html( $card['designation'] ) . '</p>';
		}
		if ( '' !== $card['sku'] ) {
			$html .= '<p class="sf-card-sku">' . esc_html__( 'Item no.', 'linker-commerce' ) . ' <span data-card-sku>' . esc_html( $card['sku'] ) . '</span></p>';
		}
		$html .= '</div>';
		$stats = \is_array( $card['stats'] ) ? $card['stats'] : array();
		if ( array() !== $stats ) {
			$html .= '<span class="card-exact-article" data-linker-exact-article><small>' . esc_html__( 'Model', 'linker-commerce' ) . '</small><strong data-card-selection>' . esc_html( ( $stats[0]['value'] ?? '' ) . ' · ' . $card['model'] ) . '</strong></span>';
		}
		if ( array() !== $stats ) {
			$html .= '<dl class="card-facts" data-card-facts aria-label="' . esc_attr__( 'Key product data', 'linker-commerce' ) . '">';
			foreach ( \array_slice( $card['stats'], 0, 4 ) as $stat ) {
				$html .= '<div><dt>' . esc_html( $stat['label'] ) . '</dt><dd>' . esc_html( $stat['value'] ) . '</dd></div>';
			}
			$html .= '</dl>';
		}
		$html .= '<div class="sf-card-price" data-card-price>';
		if ( '' !== $card['price']['url'] ) {
			$html .= '<a class="sf-card-price-login" href="' . esc_url( $card['price']['url'] ) . '">' . esc_html( $card['price']['html'] ) . '</a>';
		} else {
			$html .= '<span class="sf-card-price-net">' . wp_kses_post( $card['price']['html'] ) . '</span>';
		}
		$html .= '</div>';
		$html .= '<p class="sf-card-availability" data-card-availability>' . esc_html( $card['availability'] ) . '</p>';
		$html .= '<div class="sf-card-actions">';
		$html .= '<a class="sf-card-view tv-woo-card-action tv-woo-card-action--primary" data-card-view href="' . esc_url( $url ) . '">' . esc_html__( 'View product', 'linker-commerce' ) . '</a>';
		$html .= '<a class="sf-card-atc tv-woo-card-action tv-woo-card-action--secondary" data-card-atc href="#" hidden>' . esc_html__( 'Add to cart', 'linker-commerce' ) . '</a>';
		if ( '' !== $card['price']['url'] ) {
			$html .= '<a class="tv-woo-card-action tv-woo-card-action--secondary" data-card-gate href="' . esc_url( $card['price']['url'] ) . '">' . esc_html__( 'Log in for pricing', 'linker-commerce' ) . '</a>';
		}
		$html .= '</div></article>';
		return $html;
	}


	/**
	 * The product page root's brand class: the page treats a brand's own
	 * scenes and photography with its own image boxing
	 * (`pdp-brand-<slug>` on `#tv-storefront-pdp`).
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_brand_class( $atts = array() ): string {
		unset( $atts );
		$view = $this->current_view();
		if ( null === $view || '' === (string) $view['brand_slug'] ) {
			return '';
		}
		return 'pdp-brand-' . sanitize_html_class( (string) $view['brand_slug'] );
	}

	/**
	 * The product page's own scripts: the gallery viewer and thumbnails, the

	 * specification tabs, the comparison selection. Enqueued once per page,
	 * from whichever block renders first.
	 */
	private function pdp_scripts(): void {
		$base = (string) plugin_dir_url( __DIR__ . '/../linker-commerce.php' ) . 'assets/';
		wp_enqueue_script( 'tv-b2b-compare-selection', $base . 'compare-selection.js', array(), '3', true );
		wp_localize_script(
			'tv-b2b-compare-selection',
			'tvB2bCompare',
			array(
				'storageKey' => 'linkerCompareIds',
				'max' => 4,
				'pageUrl' => self::compare_page_url(),
				'strings' => array(
					'compare' => __( 'Compare', 'linker-commerce' ),
					'inComparison' => __( 'In comparison', 'linker-commerce' ),
					'limitReached' => sprintf(
						/* translators: %d: maximum number of products in a comparison. */
						__( 'Up to %d products. Remove one to add another.', 'linker-commerce' ),
						4
					),
					'compareArticle' => __( 'Compare: %s', 'linker-commerce' ),
				),
			)
		);
		wp_enqueue_script( 'tv-b2b-pdp-ui', $base . 'pdp-ui.js', array( 'tv-b2b-compare-selection' ), '3', true );
	}

	/**
	 * The breadcrumb under the header: Products, the brand, the model.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_crumbs( $atts = array() ): string {
		unset( $atts );
		$view = $this->current_view();
		if ( null === $view ) {
			return '';
		}
		$crumbs = array();
		$shop   = get_permalink( (int) wc_get_page_id( 'shop' ) );
		if ( \is_string( $shop ) ) {
			$crumbs[] = '<a href="' . esc_url( $shop ) . '">' . esc_html__( 'Products', 'linker-commerce' ) . '</a>';
		}
		if ( '' !== $view['brand'] ) {
			$crumbs[] = '<span>' . esc_html( $view['brand'] ) . '</span>';
		}
		$crumbs[] = '<span>' . esc_html( $view['model'] ) . '</span>';
		return '<nav class="pdp-crumbs" aria-label="' . esc_attr__( 'Breadcrumb', 'linker-commerce' ) . '">'
			. implode( '<span aria-hidden="true">/</span>', $crumbs ) . '</nav>';
	}

	/**
	 * The gallery: the main and secondary image pair and the thumbnail
	 * column, in the featured-first order the product data holds.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_gallery( $atts = array() ): string {
		unset( $atts );
		$this->pdp_scripts();
		$view = $this->current_view();
		if ( null === $view ) {
			return '';
		}
		$product = wc_get_product( (int) $view['id'] );
		if ( ! $product instanceof WC_Product ) {
			return '';
		}
		$ids  = Materials::gallery_ids( $product, Materials::acf( (int) $view['id'] ) );
		$html = '<div class="pdp-gallery">';
		if ( array() === $ids ) {
			return $html . '<div class="pdp-gallery-pair"><div class="pdp-gallery-main-wrap pdp-gallery-empty">'
				. '<p class="tv-empty-state">' . esc_html__( 'Product photography for this model is in preparation.', 'linker-commerce' ) . '</p>'
				. '</div></div></div>';
		}
		$name = $view['title'];
		$html .= '<div class="pdp-gallery-pair">';
		$html .= '<button type="button" class="pdp-gallery-main-wrap" data-pdp-image data-pdp-main data-src="' . esc_url( self::image_url( $ids[0] ) ) . '" data-caption="">'
			. self::image_tag( $ids[0], 'full', array( 'class' => 'pdp-gallery-main', 'alt' => $name ) ) . '</button>';
		if ( isset( $ids[1] ) ) {
			$html .= '<button type="button" class="pdp-gallery-secondary" data-pdp-image data-src="' . esc_url( self::image_url( $ids[1] ) ) . '" data-caption="" aria-label="' . esc_attr__( 'Product image 2', 'linker-commerce' ) . '">'
				. self::image_tag( $ids[1], 'full', array( 'alt' => '' ) ) . '</button>';
		}
		$html .= '</div>';
		if ( \count( $ids ) > 1 ) {
			$html .= '<div class="pdp-thumbs">';
			foreach ( $ids as $index => $id ) {
				$html .= '<button type="button" data-pdp-thumb data-src="' . esc_url( self::image_url( $id ) ) . '" data-caption=""'
					. ' aria-label="' . esc_attr( sprintf( /* translators: %d: image number. */ __( 'Product image %d', 'linker-commerce' ), $index + 1 ) ) . '"'
					. ' aria-pressed="' . ( 0 === $index ? 'true' : 'false' ) . '" class="pdp-thumb">'
					. wp_get_attachment_image( $id, 'medium', false, array( 'sizes' => '72px' ) ) . '</button>';
			}
			$html .= '</div>';
		}
		return $html . '</div>';
	}

	/**
	 * The purchase panel: brand, identity, price prompt, the key figures, the
	 * availability line with its delivery note, the two calls to action, the
	 * three tools and the project entry.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_buy( $atts = array() ): string {
		unset( $atts );
		$view = $this->current_view();
		if ( null === $view ) {
			return '';
		}
		$product_id = (int) $view['id'];
		$product    = wc_get_product( $product_id );
		$html       = '';
		if ( \is_array( $view['brand_logo'] ) ) {
			$logo  = $view['brand_logo'];
			$html .= '<div class="pdp-brand pdp-brand--logo"><img class="pdp-brand-logo" src="' . esc_url( $logo['src'] ) . '" srcset="' . esc_attr( $logo['srcset'] ) . '" alt="' . esc_attr( $logo['alt'] ) . '" loading="eager" decoding="async" /></div>';
		} elseif ( '' !== $view['brand'] ) {
			$html .= '<div class="pdp-brand"><span class="pdp-brand-text">' . esc_html( $view['brand'] ) . '</span></div>';
		}
		$html .= '<h1 class="pdp-h1">' . esc_html( $view['model'] ) . '</h1>';
		if ( '' !== $view['designation'] ) {
			$html .= '<p class="pdp-designation">' . esc_html( $view['designation'] ) . '</p>';
		}
		if ( '' !== $view['sku'] ) {
			$html .= '<p class="pdp-sku">' . esc_html__( 'Item number:', 'linker-commerce' ) . ' ' . esc_html( $view['sku'] ) . '</p>';
		}
		$html .= '<div class="pdp-price">';
		if ( '' !== $view['price']['url'] ) {
			$html .= '<a class="pdp-price-login" href="' . esc_url( $view['price']['url'] ) . '">' . esc_html( $view['price']['html'] ) . '</a>';
		} else {
			$html .= '<span class="pdp-price-net">' . wp_kses_post( $view['price']['html'] ) . '</span>';
		}
		$html .= '</div>';
		$stats = $product instanceof WC_Product ? Materials::key_stats( $product, 4 ) : array();
		if ( array() !== $stats ) {
			$html .= '<dl class="pdp-spec-list">';
			foreach ( $stats as $stat ) {
				$html .= '<div><span class="pdp-app-stat-icon" data-icon="' . esc_attr( $stat['icon'] ) . '" aria-hidden="true"></span>'
					. '<dt>' . esc_html( $stat['label'] ) . '</dt><dd>' . esc_html( $stat['value'] ) . '</dd></div>';
			}
			$html .= '</dl>';
		}
		$note = $product instanceof WC_Product ? self::delivery_note( $product ) : '';
		$html .= '<div class="pdp-avail"><p class="pdp-avail-label"><span class="pdp-dot ' . ( $product instanceof WC_Product && $product->is_in_stock() ? 'is-ok' : 'is-wait' ) . '" aria-hidden="true"></span>' . esc_html( $view['availability'] ) . '</p>';
		if ( '' !== $note ) {
			$html .= '<p class="pdp-avail-note">' . esc_html( $note ) . '</p>';
		}
		$html .= '</div>';
		$html .= '<a class="pdp-btn pdp-btn-dark" href="' . esc_url( (string) $view['cta_url'] ) . '">' . esc_html( $view['cta_label'] ) . '</a>';
		$html .= '<a class="pdp-btn pdp-btn-secondary" href="' . esc_url( (string) $view['ask_url'] ) . '">' . esc_html__( 'Ask about this product', 'linker-commerce' ) . '</a>';
		$html .= self::tools_row( $product_id, $view, $product );
		$html .= self::project_check( $product_id, $view, $product );
		return $html;
	}

	/**
	 * The three product tools and the comparison chip
	 * (`tv_b2b_pdp_tools`): compare, ask, documents.
	 */
	private static function tools_row( int $product_id, array $view, ?WC_Product $product ): string {
		$ask_message = sprintf(
			/* translators: %s: product name with item number. */
			__( 'About %s: give me the key specs, which batteries or inverters it pairs with, and whether it fits my project.', 'linker-commerce' ),
			trim( (string) $view['title'] . ' (' . (string) $view['sku'] . ')' )
		);
		$html  = '<div class="pdp-product-tools">';
		$html .= '<button type="button" class="pdp-tool" data-compare-article="' . (int) $product_id . '" aria-pressed="false">'
			. '<span class="pdp-tool-icon" data-icon="compare" aria-hidden="true"></span>'
			. '<span data-compare-label>' . esc_html__( 'Compare', 'linker-commerce' ) . '</span></button>';
		$html .= '<button type="button" class="pdp-tool" data-pdp-ask data-ask-message="' . esc_attr( $ask_message ) . '">'
			. '<span class="pdp-tool-icon" data-icon="ask" aria-hidden="true"></span>'
			. esc_html__( 'Ask Linker Advisor', 'linker-commerce' ) . '</button>';
		$html .= '<a class="pdp-tool" href="#downloads">'
			. '<span class="pdp-tool-icon" data-icon="file" aria-hidden="true"></span>'
			. esc_html__( 'Documents', 'linker-commerce' ) . '</a>';
		$html .= '<a class="sf-compare-chip" id="compare-chip" hidden href="' . esc_url( self::compare_page_url() ) . '" aria-label="' . esc_attr__( 'Compare', 'linker-commerce' ) . '">'
			. '<span class="pdp-tool-icon" data-icon="compare" aria-hidden="true"></span>'
			. '<span class="sf-compare-chip-label">' . esc_html__( 'Compare', 'linker-commerce' ) . '</span>'
			. '<span class="sf-compare-chip-n" data-compare-count>0</span></a>';
		return $html . '</div>';
	}

	/**
	 * The project entry under the tools: "Plan with <model>" and the four
	 * ways into the Advisor, each with its own opening message.
	 *
	 * @param array<string, mixed> $view    The product's replica fields.
	 */
	private static function project_check( int $product_id, array $view, ?WC_Product $product ): string {
		if ( ! $product instanceof WC_Product ) {
			return '';
		}
		$model    = (string) $view['model'];
		$name     = (string) $view['title'];
		$sku      = (string) $view['sku'];
		$material = Materials::material_for_product( $product_id );
		$shared   = array(
			'data-linker-project-product-prompt' => '',
			'data-product-id' => (string) $product_id,
			'data-material-id' => \is_array( $material ) ? (string) ( $material['material_id'] ?? '' ) : '',
			'data-material-revision' => \is_array( $material ) ? (string) ( $material['revision'] ?? '' ) : '',
			'data-product-model' => $model,
		);
		$stages   = array(
			array( 'label' => __( 'New system', 'linker-commerce' ), 'lead' => __( 'I am planning a new system with %s.', 'linker-commerce' ) ),
			array( 'label' => __( 'Extend an existing system', 'linker-commerce' ), 'lead' => __( 'I am extending an existing system with %s.', 'linker-commerce' ) ),
			array( 'label' => __( 'Replace an existing unit', 'linker-commerce' ), 'lead' => __( 'I am replacing a unit in an existing system with %s.', 'linker-commerce' ) ),
		);
		$tail     = __( 'Then ask one question at a time for what you still need (existing model, quantity, installation postcode, installation date) and check compatibility, missing system components and delivery windows against current Linker data.', 'linker-commerce' );
		$html     = '<details class="pdp-project-check" data-linker-project-product-context aria-label="' . esc_attr__( 'Check this model for the project', 'linker-commerce' ) . '">';
		$html    .= '<summary><h2>' . esc_html( sprintf( /* translators: %s: product model. */ __( 'Plan with %s', 'linker-commerce' ), $model ) ) . '</h2></summary>';
		$html    .= '<div class="pdp-project-check__body">';
		$html    .= '<p>' . esc_html__( 'New system, extension or replacement? Linker Advisor starts from this model and asks only what is still missing.', 'linker-commerce' ) . '</p>';
		$html    .= '<div class="pdp-project-choices">';
		foreach ( $stages as $stage ) {
			$message = sprintf( (string) $stage['lead'], trim( $name . ' (' . $sku . ')' ) ) . ' ' . $tail;
			$html   .= '<button type="button" class="pdp-project-choice"';
			foreach ( $shared as $attribute => $value ) {
				$html .= ' ' . $attribute . '="' . esc_attr( $value ) . '"';
			}
			$html .= ' data-project-message="' . esc_attr( $message ) . '">' . esc_html( (string) $stage['label'] ) . '</button>';
		}
		$html .= '<button type="button" class="pdp-project-choice pdp-project-choice--nameplate" data-linker-assistant-open="nameplate">'
			. esc_html__( 'Identify a device from a nameplate photo', 'linker-commerce' ) . '</button>';
		$html .= '</div><p data-linker-project-product-feedback aria-live="polite"></p></div></details>';
		return $html;
	}

	/**
	 * The description section: the panel with the kicker, the title and the
	 * introduction, the benefit cards and the disclosure rows.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_description( $atts = array() ): string {
		unset( $atts );
		$view = $this->current_view();
		if ( null === $view ) {
			return '';
		}
		$html  = '<div class="pdp-overview"><div class="pdp-overview-copy">';
		$html .= '<p class="pdp-kicker">' . esc_html__( 'Description', 'linker-commerce' ) . '</p>';
		$html .= '<h2 class="pdp-section-title">' . esc_html( $view['title'] ) . '</h2>';
		$html .= '<div class="pdp-overview-intro pdp-reading">';
		if ( '' !== $view['intro'] ) {
			$html .= wp_kses_post( $view['intro'] );
		} elseif ( '' !== $view['body'] ) {
			$html .= wp_kses_post( wpautop( $view['body'] ) );
		} else {
			$html .= '<p class="tv-empty-state">' . esc_html__( 'Introduction in preparation. The specification below carries the values from the datasheet on file.', 'linker-commerce' ) . '</p>';
		}
		$html .= '</div></div></div>';
		$cards = array();
		foreach ( \is_array( $view['features'] ) ? $view['features'] : array() as $feature ) {
			$line = trim( (string) $feature['body'] );
			if ( '' === $line && '' !== (string) $feature['title'] ) {
				$line = (string) $feature['title'];
			}
			if ( '' !== $line ) {
				$cards[] = '<li class="pdp-benefit"><span class="pdp-benefit-icon" data-icon="check" aria-hidden="true"></span><div><p>' . esc_html( $line ) . '</p></div></li>';
			}
		}
		if ( array() !== $cards ) {
			$html .= '<ul class="pdp-benefits">' . implode( '', array_slice( $cards, 0, 2 ) ) . '</ul>';
		}
		return $html;
	}

	/**
	 * The product's disclosure rows below the description panel.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_disclosures( $atts = array() ): string {
		unset( $atts );
		$view = $this->current_view();
		if ( null === $view ) {
			return '';
		}
		$html = '';
		foreach ( \is_array( $view['features'] ) ? $view['features'] : array() as $feature ) {
			if ( '' === trim( (string) $feature['body'] ) ) {
				continue;
			}
			$html .= '<details class="pdp-disclose"><summary>' . esc_html( (string) $feature['title'] )
				. '<span class="pdp-chevron" data-icon="chevron" aria-hidden="true"></span></summary>'
				. '<div class="pdp-disclose-body pdp-reading"><p>' . esc_html( (string) $feature['body'] ) . '</p></div></details>';
		}
		return $html;
	}

	/**
	 * The technical data: the spec groups as the disclosure rows the page's
	 * script turns into the tab deck.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_specs( $atts = array() ): string {
		unset( $atts );
		$this->pdp_scripts();
		$view  = $this->current_view();
		$html  = '';
		$decks = array();
		$group = \is_array( $view['spec_groups'] ?? null ) ? $view['spec_groups'] : array();
		if ( array() !== $group ) {
			foreach ( $group as $spec_group ) {
				$body = '<dl class="pdp-stat-wrap">';
				foreach ( $spec_group['rows'] as $row ) {
					$body .= '<div class="pdp-stat-row"><dt>' . esc_html( $row['label'] ) . '</dt><dd>' . esc_html( $row['value'] );
					if ( '' !== $row['unit'] ) {
						$body .= '<span class="pdp-stat-unit">' . esc_html( $row['unit'] ) . '</span>';
					}
					if ( '' !== $row['note'] ) {
						$body .= '<div class="pdp-reading pdp-muted">' . esc_html( $row['note'] ) . '</div>';
					}
					$body .= '</dd></div>';
				}
				$body   .= '</dl>';
				$decks[] = array( 'title' => (string) $spec_group['title'], 'body' => $body );
			}
		}
		if ( array() === $decks ) {
			$attributes = \is_array( $view['attributes'] ?? null ) ? $view['attributes'] : array();
			if ( array() !== $attributes ) {
				$body = '<dl class="pdp-stat-wrap">';
				foreach ( $attributes as $row ) {
					$body .= '<div class="pdp-stat-row"><dt>' . esc_html( $row['label'] ) . '</dt><dd>' . esc_html( $row['value'] ) . '</dd></div>';
				}
				$body   .= '</dl>';
				$decks[] = array( 'title' => __( 'Specifications', 'linker-commerce' ), 'body' => $body );
			}
		}
		if ( array() === $decks ) {
			return '<p class="tv-empty-state">' . esc_html__( 'The specification table for this product is in preparation. Ask us for the datasheet.', 'linker-commerce' ) . '</p>';
		}
		$html .= '<div class="pdp-stats-layout"><div class="pdp-stats-summary"></div><div class="pdp-info-deck pdp-spec-deck">';
		$html .= '<div class="pdp-info-tabs" role="tablist" aria-label="' . esc_attr__( 'Specification group', 'linker-commerce' ) . '">';
		foreach ( $decks as $index => $deck ) {
			$html .= '<button type="button" id="pdp-spec-tab-' . $index . '" role="tab" aria-controls="pdp-spec-panel-' . $index . '" aria-selected="' . ( 0 === $index ? 'true' : 'false' ) . '" tabindex="' . ( 0 === $index ? '0' : '-1' ) . '">' . esc_html( $deck['title'] ) . '</button>';
		}
		$html .= '</div>';
		$html .= '<div class="pdp-info-panel" id="pdp-spec-panel-0" role="tabpanel" aria-labelledby="pdp-spec-tab-0" tabindex="0">';
		foreach ( $decks as $index => $deck ) {
			$html .= '<details class="pdp-disclose pdp-tab-disclosure"' . ( 0 === $index ? ' open' : '' ) . ' data-pdp-tab="' . $index . '">'
				. '<summary>' . esc_html( $deck['title'] ) . '<span class="pdp-chevron" data-icon="chevron" aria-hidden="true"></span></summary>'
				. '<div class="pdp-disclose-body pdp-reading">' . $deck['body'] . '</div></details>';
		}
		return $html . '</div></div>';
	}

	/**
	 * The documents: the file cards with their type and language.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_downloads( $atts = array() ): string {
		unset( $atts );
		$view = $this->current_view();
		if ( null === $view ) {
			return '';
		}
		$product = wc_get_product( (int) $view['id'] );
		$docs    = $product instanceof WC_Product ? Materials::documents( $product ) : array();
		if ( array() === $docs ) {
			return '<p class="tv-empty-state">' . esc_html__( 'No documents are attached to this product yet. Ask us and we will add them.', 'linker-commerce' ) . '</p>';
		}
		$html = '';
		foreach ( $docs as $document ) {
			$meta = array_filter(
				array(
					Materials::document_kind_label( (string) $document['kind'] ),
					'PDF',
					(string) $document['language'],
				),
				static fn( string $part ): bool => '' !== $part
			);
			$html .= '<a class="pdp-doc" href="' . esc_url( (string) $document['url'] ) . '" target="_blank" rel="noopener">';
			$html .= '<span class="pdp-doc-icon" data-icon="file" aria-hidden="true"></span>';
			$html .= '<span class="grow">' . esc_html( (string) $document['title'] );
			if ( array() !== $meta ) {
				$html .= '<span class="pdp-doc-meta">' . esc_html( implode( ' · ', $meta ) ) . '</span>';
			}
			$html .= '</span>';
			$html .= '<span class="pdp-doc-download" data-icon="download" aria-hidden="true"></span></a>';
		}
		return $html;
	}

	/**
	 * The compatibility records: the pairing cards from the registry's
	 * relationships and the contract's cells, with the footnote.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_pairings( $atts = array() ): string {
		unset( $atts );
		$view = $this->current_view();
		if ( null === $view ) {
			return '';
		}
		$product_id = (int) $view['id'];
		$locale     = Materials::locale();
		$cards      = array();
		$notes      = array();
		foreach ( Materials::relationships( self::source_id( $product_id ) ) as $relationship ) {
			$target_id = (int) ( $relationship['target_product_id'] ?? 0 );
			$target    = $target_id ? wc_get_product( $target_id ) : null;
			if ( ! $target instanceof WC_Product || 'publish' !== $target->get_status() ) {
				continue;
			}
			$cell_id = Materials::relationship_cell_id( $relationship );
			$cell    = '' !== $cell_id && isset( Materials::contract()['cells'][ $cell_id ] ) ? Materials::contract()['cells'][ $cell_id ] : null;
			$status  = self::pairing_status( $relationship, $locale );
			$cards[] = '<a class="pdp-pairing" href="' . esc_url( (string) get_permalink( $target_id ) ) . '">'
				. wp_get_attachment_image( (int) $target->get_image_id(), 'medium', false, array( 'alt' => $target->get_name(), 'loading' => 'lazy' ) )
				. '<span class="pdp-pairing-copy">'
				. '<span class="pdp-pairing-name">' . esc_html( $target->get_name() ) . '</span>'
				. '<span class="pdp-pairing-sku">' . esc_html__( 'Item number', 'linker-commerce' ) . ' ' . esc_html( (string) $target->get_sku() ) . '</span>'
				. '<span class="pdp-pairing-chips"><span class="pdp-doc-meta">' . esc_html( $status ) . '</span></span>'
				. '</span></a>';
			$constraint = Materials::localized_text( $relationship, 'constraint', $locale );
			if ( '' !== $constraint && ! isset( $notes[ $constraint ] ) ) {
				$notes[ $constraint ] = true;
			}
		}
		if ( array() === $cards ) {
			return '';
		}
		\usort( $cards, static fn( string $left, string $right ): int => strnatcasecmp( $left, $right ) );
		$html = '<section class="pdp-block"><h2 class="pdp-section-title">' . esc_html__( 'Compatibility records', 'linker-commerce' ) . '</h2>';
		$html .= '<div class="pdp-pairings">' . implode( '', $cards ) . '</div>';
		foreach ( array_keys( $notes ) as $note ) {
			$html .= '<div class="pdp-pairing-footnote pdp-reading pdp-muted"><p>' . esc_html( (string) $note ) . '</p></div>';
		}
		return $html . '</section>';
	}

	/**
	 * What the contract says about one relationship
	 * (tv_b2b_pdp_pairing_status).
	 */
	private static function pairing_status( array $relationship, string $locale ): string {
		$by = trim( Materials::localized_text( $relationship, 'listed_by', $locale ) );
		if ( '' === $by ) {
			return __( 'On the compatibility list on file', 'linker-commerce' );
		}
		return sprintf( /* translators: %s: manufacturer */ __( "On %s's compatibility list", 'linker-commerce' ), $by );
	}

	/**
	 * The product row an instance object belongs to: the German version's own
	 * registry binding follows the English source (#9's translation group).
	 */
	private static function source_id( int $product_id ): int {
		if ( \function_exists( 'pll_get_post' ) && \function_exists( 'pll_get_post_language' ) ) {
			$language = pll_get_post_language( $product_id );
			if ( 'en' !== $language ) {
				$source = pll_get_post( $product_id, 'en' );
				if ( \is_int( $source ) && $source > 0 ) {
					return $source;
				}
			}
		}
		return $product_id;
	}

	/**
	 * The delivery sentence of the availability line, from the product's
	 * freight outcome.
	 */
	private static function delivery_note( WC_Product $product ): string {
		$fact    = Materials::logistics( (int) $product->get_id(), $product );
		$outcome = Materials::freight_outcome( $fact );
		$parts   = array_filter( array( (string) ( $outcome['headline'] ?? '' ), (string) ( $outcome['detail'] ?? '' ) ) );
		return implode( ' · ', $parts );
	}

	/**
	 * An attachment image URL, '' when the id holds none.
	 */
	private static function image_url( int $image_id ): string {
		$url = wp_get_attachment_image_url( $image_id, 'full' );
		return \is_string( $url ) ? $url : '';
	}

	/**
	 * An image tag with the live renderer's attribute set: class, src, srcset
	 * and sizes, no width/height (the stylesheet sizes the box).
	 *
	 * @param array<string, string> $attributes Extra attributes.
	 */
	private static function image_tag( int $image_id, string $size, array $attributes ): string {
		$src    = wp_get_attachment_image_src( $image_id, $size );
		$srcset = wp_get_attachment_image_srcset( $image_id, $size );
		$sizes  = wp_get_attachment_image_sizes( $image_id, $size );
		if ( ! \is_array( $src ) ) {
			return '';
		}
		$html = '<img';
		foreach ( $attributes as $name => $value ) {
			$html .= ' ' . $name . '="' . esc_attr( $value ) . '"';
		}
		$html .= ' src="' . esc_url( (string) $src[0] ) . '"';
		if ( \is_string( $srcset ) && '' !== $srcset ) {
			$html .= ' srcset="' . esc_attr( $srcset ) . '"';
		}
		if ( \is_string( $sizes ) && '' !== $sizes ) {
			$html .= ' sizes="' . esc_attr( $sizes ) . '"';
		}
		return $html . ' />';
	}

	/**
	 * The application scenarios (#16 GAP-2): the live product page's
	 * `#fit` block, from the product's `application_scenarios`.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_scenes( $atts = array() ): string {
		unset( $atts );
		$view      = $this->current_view();
		$scenarios = \is_array( $view['scenarios'] ?? null ) ? $view['scenarios'] : array();
		if ( array() === $scenarios ) {
			return '';
		}
		$reel  = '';
		$cards = '';
		foreach ( $scenarios as $scenario ) {
			$text = '';
			if ( '' !== $scenario['situation'] ) {
				$text .= '<p>' . esc_html( $scenario['situation'] ) . '</p>';
			}
			if ( '' !== $scenario['fit'] ) {
				$text .= '<p>' . esc_html( $scenario['fit'] ) . '</p>';
			}
			if ( '' !== $scenario['verdict'] ) {
				$text .= '<p>' . esc_html( $scenario['verdict'] ) . '</p>';
			}
			if ( array() !== $scenario['checklist'] ) {
				$text .= '<ul>';
				foreach ( $scenario['checklist'] as $check ) {
					$text .= '<li>' . esc_html( $check ) . '</li>';
				}
				$text .= '</ul>';
			}
			if ( ! $text ) {
				continue;
			}
			$cards .= '<details class="pdp-disclose"><summary>' . esc_html( $scenario['title'] ) . '</summary>';
			$cards .= '<div class="pdp-disclose-body pdp-reading">' . $text;
			if ( '' !== $scenario['url'] ) {
				$cards .= '<p><a href="' . esc_url( $scenario['url'] ) . '">' . esc_html__( 'See the applications', 'linker-commerce' ) . '</a></p>';
			}
			$cards .= '</div></details>';
			if ( 0 !== $scenario['image'] ) {
				$reel .= '<figure class="pdp-scene-card">';
				$reel .= wp_get_attachment_image(
					(int) $scenario['image'],
					'large',
					false,
					array(
						'loading' => 'lazy',
						'alt'     => $scenario['title'],
					)
				);
				$reel .= '<figcaption><span class="pdp-kicker">' . esc_html( $scenario['title'] ) . '</span>';
				$reel .= '<p>' . esc_html( wp_strip_all_tags( $scenario['situation'] ) ) . '</p></figcaption>';
				$reel .= '</figure>';
			}
		}
		if ( '' === $cards && '' === $reel ) {
			return '';
		}
		$html = '';
		if ( '' !== $reel ) {
			$html .= '<div class="pdp-scene-reel">' . $reel . '</div>';
		}
		$html .= $cards;
		return '<section class="pdp-block pdp-scenes" id="fit"><h2 class="pdp-section-title">' . esc_html__( 'Applications', 'linker-commerce' ) . '</h2>' . $html . '</section>';
	}

	/**
	 * A term's link, '' when WordPress refuses it.
	 *
	 * @param WP_Term $term The term.
	 */
	private function term_link( WP_Term $term ): string {
		$link = get_term_link( $term );
		return is_wp_error( $link ) ? '' : $link;
	}

	/**
	 * The current product's replica fields; null outside a product.
	 *
	 * @return array<string, mixed>|null
	 */
	private function current_view(): ?array {
		$product = $GLOBALS['product'] ?? null;
		if ( ! $product instanceof WC_Product ) {
			$product = wc_get_product( (int) get_the_ID() );
		}
		if ( ! $product instanceof WC_Product ) {
			return null;
		}
		$view = $this->views->fields( (int) $product->get_id() );
		return array() === $view ? null : $view;
	}
}
