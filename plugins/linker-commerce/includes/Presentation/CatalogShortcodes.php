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
		add_shortcode( 'linker_pdp_crumbs', array( $this, 'pdp_crumbs' ) );
		add_shortcode( 'linker_pdp_gallery', array( $this, 'pdp_gallery' ) );
		add_shortcode( 'linker_pdp_buy', array( $this, 'pdp_buy' ) );
		add_shortcode( 'linker_pdp_description', array( $this, 'pdp_description' ) );
		add_shortcode( 'linker_pdp_specs', array( $this, 'pdp_specs' ) );
		add_shortcode( 'linker_pdp_scenes', array( $this, 'pdp_scenes' ) );
		add_shortcode( 'linker_pdp_downloads', array( $this, 'pdp_downloads' ) );
		add_shortcode( 'linker_pdp_pairings', array( $this, 'pdp_pairings' ) );
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
	 * The product page breadcrumb.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_crumbs( $atts = array() ): string {
		unset( $atts );
		$view = $this->current_view();
		if ( null === $view ) {
			return '';
		}
		$html = '<nav class="pdp-crumbs" aria-label="' . esc_attr__( 'Breadcrumb', 'linker-commerce' ) . '">';
		foreach ( $view['crumbs'] as $crumb ) {
			if ( ! \is_array( $crumb ) ) {
				continue;
			}
			if ( $crumb['url'] ) {
				$html .= '<a href="' . esc_url( (string) $crumb['url'] ) . '">' . esc_html( (string) $crumb['label'] ) . '</a>';
			} else {
				$html .= '<span>' . esc_html( (string) $crumb['label'] ) . '</span>';
			}
		}
		$html .= '</nav>';
		return $html;
	}

	/**
	 * The product gallery: the large/secondary pair and the thumbnails.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_gallery( $atts = array() ): string {
		unset( $atts );
		$view    = $this->current_view();
		$gallery = \is_array( $view['gallery'] ?? null ) ? $view['gallery'] : array();
		$html    = '<div class="pdp-gallery">';
		if ( array() === $gallery ) {
			$html .= '<div class="pdp-gallery-pair"><div class="pdp-gallery-main-wrap pdp-gallery-empty">';
			$html .= '<p class="tv-empty-state">' . esc_html__( 'Product photography for this model is in preparation.', 'linker-commerce' ) . '</p>';
			$html .= '</div></div></div>';
			return $html;
		}
		$main  = \array_slice( $gallery, 0, 2 );
		$html .= '<div class="pdp-gallery-pair">';
		$html .= '<button class="pdp-gallery-main-wrap" type="button" data-pdp-viewer-open>';
		$html .= wp_get_attachment_image(
			(int) $main[0],
			'large',
			false,
			array(
				'class'         => 'pdp-gallery-main',
				'loading'       => 'eager',
				'fetchpriority' => 'high',
			)
		);
		$html .= '</button>';
		if ( isset( $main[1] ) ) {
			$html .= '<button class="pdp-gallery-secondary" type="button" data-pdp-viewer-open>';
			$html .= wp_get_attachment_image(
				(int) $main[1],
				'medium_large',
				false,
				array(
					'class'   => 'pdp-gallery-secondary-img',
					'loading' => 'lazy',
				)
			);
			$html .= '</button>';
		}
		$html .= '</div>';
		if ( \count( $gallery ) > 2 ) {
			$html .= '<div class="pdp-thumbs">';
			foreach ( $gallery as $image_id ) {
				$html .= '<button class="pdp-thumb" type="button" data-pdp-viewer-open>' . wp_get_attachment_image( (int) $image_id, 'thumbnail', false, array( 'loading' => 'lazy' ) ) . '</button>';
			}
			$html .= '</div>';
		}
		$html .= '</div>';
		return $html;
	}

	/**
	 * The purchase panel's content: brand, model, designation, item number,
	 * price, key numbers, availability, the two calls to action. The
	 * `pdp-purchase` and `pdp-buy-inner` wrappers belong to the template.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_buy( $atts = array() ): string {
		unset( $atts );
		$view = $this->current_view();
		if ( null === $view ) {
			return '';
		}
		$html = '';
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
		if ( \is_array( $view['stats'] ) && array() !== $view['stats'] ) {
			$html .= '<dl class="pdp-spec-list">';
			foreach ( $view['stats'] as $stat ) {
				$html .= '<div><dt>' . esc_html( $stat['label'] ) . '</dt><dd>' . esc_html( $stat['value'] ) . '</dd></div>';
			}
			$html .= '</dl>';
		}
		$html .= '<div class="pdp-avail"><p class="pdp-avail-label"><span class="pdp-dot is-ok" aria-hidden="true"></span>' . esc_html( $view['availability'] ) . '</p></div>';
		$html .= '<a class="pdp-btn pdp-btn-dark" href="' . esc_url( (string) $view['cta_url'] ) . '">' . esc_html( $view['cta_label'] ) . '</a>';
		$html .= '<a class="pdp-btn pdp-btn-secondary" href="' . esc_url( (string) $view['ask_url'] ) . '">' . esc_html__( 'Ask about this product', 'linker-commerce' ) . '</a>';
		return $html;
	}

	/**
	 * The description block: title, intro, feature cards as disclosure rows.
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
		$html .= '<h2 class="pdp-section-title">' . esc_html( $view['title'] ) . '</h2>';
		$html .= '<div class="pdp-overview-intro pdp-reading">';
		if ( '' !== $view['intro'] ) {
			// The field carries simple markup on some products (a wrapping <p>);
			// kses-post renders it as the live page does.
			$html .= wp_kses_post( $view['intro'] );
		} elseif ( '' !== $view['body'] ) {
			$html .= wp_kses_post( wpautop( $view['body'] ) );
		} else {
			$html .= '<p class="tv-empty-state">' . esc_html__( 'Introduction in preparation. The specification below carries the values from the datasheet on file.', 'linker-commerce' ) . '</p>';
		}
		$html .= '</div></div></div>';
		foreach ( \is_array( $view['features'] ) ? $view['features'] : array() as $feature ) {
			$html .= '<details class="pdp-disclose"' . ( $feature['priority'] ? ' open' : '' ) . '>';
			$html .= '<summary>' . esc_html( $feature['title'] ) . '</summary>';
			$html .= '<div class="pdp-disclose-body pdp-reading">';
			if ( '' !== $feature['body'] ) {
				$html .= '<p>' . esc_html( $feature['body'] ) . '</p>';
			}
			$html .= '</div></details>';
		}
		return $html;
	}

	/**
	 * The technical data: the spec groups as open disclosure rows, the
	 * product attributes when no groups exist.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_specs( $atts = array() ): string {
		unset( $atts );
		$view   = $this->current_view();
		$html   = '';
		$groups = \is_array( $view['spec_groups'] ?? null ) ? $view['spec_groups'] : array();
		if ( array() !== $groups ) {
			foreach ( $groups as $group ) {
				$html .= '<details class="pdp-disclose" open>';
				$html .= '<summary>' . esc_html( $group['title'] ) . '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg></summary>';
				$html .= '<div class="pdp-disclose-body pdp-reading"><dl class="pdp-stat-wrap">';
				foreach ( $group['rows'] as $row ) {
					$html .= '<div class="pdp-stat-row"><dt>' . esc_html( $row['label'] ) . '</dt><dd>' . esc_html( $row['value'] );
					if ( '' !== $row['unit'] ) {
						$html .= '<span class="pdp-stat-unit">' . esc_html( $row['unit'] ) . '</span>';
					}
					if ( '' !== $row['note'] ) {
						$html .= '<div class="pdp-reading pdp-muted">' . esc_html( $row['note'] ) . '</div>';
					}
					$html .= '</dd></div>';
				}
				$html .= '</dl></div></details>';
			}
			return $html;
		}
		$attributes = \is_array( $view['attributes'] ?? null ) ? $view['attributes'] : array();
		if ( array() !== $attributes ) {
			$html .= '<details class="pdp-disclose" open>';
			$html .= '<summary>' . esc_html__( 'Specifications', 'linker-commerce' ) . '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg></summary>';
			$html .= '<div class="pdp-disclose-body pdp-reading"><dl class="pdp-stat-wrap">';
			foreach ( $attributes as $row ) {
				$html .= '<div class="pdp-stat-row"><dt>' . esc_html( $row['label'] ) . '</dt><dd>' . esc_html( $row['value'] ) . '</dd></div>';
			}
			$html .= '</dl></div></details>';
			return $html;
		}
		return '<p class="tv-empty-state">' . esc_html__( 'The specification table for this product is in preparation. Ask us for the datasheet.', 'linker-commerce' ) . '</p>';
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
	 * The documents list: our media library files (ADR-0023).
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_downloads( $atts = array() ): string {
		unset( $atts );
		$view      = $this->current_view();
		$downloads = \is_array( $view['downloads'] ?? null ) ? $view['downloads'] : array();
		if ( array() === $downloads ) {
			return '<p class="tv-empty-state">' . esc_html__( 'No documents are attached to this product yet. Ask us and we will add them.', 'linker-commerce' ) . '</p>';
		}
		$html = '';
		foreach ( $downloads as $download ) {
			$html .= '<a class="pdp-doc" href="' . esc_url( (string) $download['url'] ) . '" target="_blank" rel="noopener noreferrer">';
			$html .= '<span class="pdp-doc-name">' . esc_html( $download['title'] ) . '</span>';
			$html .= '<span class="pdp-doc-meta">' . esc_html( $download['type'] ) . ' · ' . esc_html( $download['language'] ) . '</span></a>';
		}
		return $html;
	}

	/**
	 * The compatible products: the pairing cards.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_pairings( $atts = array() ): string {
		unset( $atts );
		$view     = $this->current_view();
		$pairings = \is_array( $view['pairings'] ?? null ) ? $view['pairings'] : array();
		if ( array() === $pairings ) {
			return '';
		}
		$html = '<div class="pdp-pairings">';
		foreach ( $pairings as $pairing ) {
			$html .= '<a class="pdp-pairing" href="' . esc_url( (string) $pairing['url'] ) . '">';
			if ( '' !== $pairing['image'] ) {
				$html .= '<img loading="lazy" src="' . esc_url( (string) $pairing['image'] ) . '" alt="' . esc_attr( $pairing['title'] ) . '" />';
			}
			$html .= '<span class="pdp-pairing-name">' . esc_html( $pairing['title'] ) . '</span></a>';
		}
		$html .= '</div>';
		return '<section class="pdp-block"><h2 class="pdp-section-title">' . esc_html__( 'Compatible products', 'linker-commerce' ) . '</h2>' . $html . '</section>';
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
