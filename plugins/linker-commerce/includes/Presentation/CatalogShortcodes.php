<?php
/**
 * The replica catalogue and product-page shortcodes: the dynamic blocks of the
 * design the site serves today, for the LiveCanvas templates to place.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

use Linker\Commerce\Catalog\Materials;
use Linker\Commerce\Catalog\SelectionFacts;
use Linker\Commerce\Settings\Options;
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
	 * Product families one catalogue page shows (the live shop's 24).
	 */
	public const PER_PAGE_FAMILIES = 24;

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
		add_shortcode( 'linker_catalog_families', array( $this, 'catalog_families' ) );
		add_shortcode( 'linker_header_utilities', array( $this, 'header_utilities' ) );
		add_shortcode( 'linker_catalog_family_count', array( $this, 'catalog_family_count' ) );
		add_shortcode( 'linker_catalog_family_pagination', array( $this, 'catalog_family_pagination' ) );
		add_shortcode( 'linker_catalog_contact', array( $this, 'catalog_contact' ) );
		add_shortcode( 'linker_pdp_brand_class', array( $this, 'pdp_brand_class' ) );
		add_shortcode( 'linker_pdp_brand', array( $this, 'pdp_brand' ) );
		add_shortcode( 'linker_pdp_model', array( $this, 'pdp_model' ) );
		add_shortcode( 'linker_pdp_brand_logo', array( $this, 'pdp_brand_logo' ) );
		add_shortcode( 'linker_pdp_designation', array( $this, 'pdp_designation' ) );
		add_shortcode( 'linker_pdp_sku', array( $this, 'pdp_sku' ) );
		add_shortcode( 'linker_pdp_price', array( $this, 'pdp_price' ) );
		add_shortcode( 'linker_pdp_key_stats', array( $this, 'pdp_key_stats' ) );
		add_shortcode( 'linker_pdp_availability', array( $this, 'pdp_availability' ) );
		add_shortcode( 'linker_pdp_cta', array( $this, 'pdp_cta' ) );
		add_shortcode( 'linker_pdp_ask', array( $this, 'pdp_ask' ) );
		add_shortcode( 'linker_pdp_tools', array( $this, 'pdp_tools' ) );
		add_shortcode( 'linker_pdp_project_choices', array( $this, 'pdp_project_choices' ) );
		add_shortcode( 'linker_pdp_gallery_pair', array( $this, 'pdp_gallery_pair' ) );
		add_shortcode( 'linker_pdp_gallery_thumbs', array( $this, 'pdp_gallery_thumbs' ) );
		add_shortcode( 'linker_pdp_intro', array( $this, 'pdp_intro' ) );
		add_shortcode( 'linker_pdp_benefits', array( $this, 'pdp_benefits' ) );
		add_shortcode( 'linker_pdp_specs', array( $this, 'pdp_specs' ) );
		add_shortcode( 'linker_pdp_scenes', array( $this, 'pdp_scenes' ) );
		add_shortcode( 'linker_pdp_downloads', array( $this, 'pdp_downloads' ) );
		add_shortcode( 'linker_pdp_pairings', array( $this, 'pdp_pairings' ) );
		add_shortcode( 'linker_pdp_disclosures', array( $this, 'pdp_disclosures' ) );
		add_shortcode( 'linker_pdp_features', array( $this, 'pdp_features' ) );
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

		$html = '<div class="wb-head">';
		// The live page's own crumb: "HOME / PRODUCTS" on the shop (the
		// second entry bold, not a link), "HOME / PRODUCTS / INVERTERS" on a
		// category (the category linked, its name bold), all words uppercase
		// as the live page prints them (measured 2026-10-12). The category's
		// name is the English one on both language pages — the live German
		// archive prints "STARTSEITE / PRODUKTE / INVERTERS" above its own
		// "Wechselrichter" heading.
		$html .= '<div class="wb-metarow container"><span class="wbm-l"><a href="' . esc_url( home_url( '/' ) ) . '">' . esc_html( self::upper( _x( 'Home', 'breadcrumb', 'linker-commerce' ) ) ) . '</a> / '
			. ( $is_term ? '<a href="' . esc_url( $shop_url ) . '">' . esc_html( self::upper( __( 'Products', 'linker-commerce' ) ) ) . '</a> / <b>' . esc_html( self::upper( $this->category_crumb_name( $queried ) ) ) . '</b>' : '<b>' . esc_html( self::upper( __( 'Products', 'linker-commerce' ) ) ) . '</b>' )
			. '</span></div>';
		$html .= '<div class="wb-bar container">';
		$html .= '<div class="wb-copy"><h1 class="wb-title">' . esc_html( $is_term ? $queried->name : __( 'Products', 'linker-commerce' ) ) . '</h1>';
		// The live shop and archives both carry the generic subtitle; the
		// category's own description is not printed on the page.
		$html .= '<p class="wb-intro">' . esc_html__( 'Search products or filter by category and project requirements.', 'linker-commerce' ) . '</p></div>';
		$html .= '<form class="wb-search" method="get" action="' . esc_url( $action ) . '" role="search">';
		$html .= '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>';
		$html .= '<input id="search-box" name="q" type="search" placeholder="' . esc_attr__( 'Search model or item number', 'linker-commerce' ) . '" value="' . esc_attr( $q ) . '" aria-label="' . esc_attr__( 'Search products', 'linker-commerce' ) . '">';
		$html .= '<button type="submit" class="wb-go">' . esc_html__( 'Search', 'linker-commerce' ) . '</button>';
		$html .= '</form>';
		// The catalogue's AI entry, at the position the live page keeps its
		// toolbar chips: the delivered chip shows itself when the typed text
		// reads as a question (spec 13 §C); the live page's other two chips
		// (batch item numbers, nameplate photo) are owner-ruled out.
		$html .= '<div class="wb-acts">' . do_shortcode( '[linker_genie_chips page_type="category"]' ) . do_shortcode( '[linker_genie_ask]' ) . '</div>';
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
			// The live rail marks the shelf the visitor is on: on the shop page
			// the "All products" row carries aria-current="page" and the copied
			// live rule `#tv-woo-b2b-catalog .family-link[aria-current="page"]`
			// lifts it to 600; on a category page it stays plain (measured
			// 2026-10-12: live "All products" aria-current=page fw 600 on
			// /products/ and /de/produkte/, absent on the archives — t16 showed
			// 400 everywhere because the attribute was never printed).
			$html .= '<a class="family-link"' . ( $is_term ? '' : ' aria-current="page"' ) . ' href="' . esc_url( (string) wc_get_page_permalink( 'shop' ) ) . '"><span>' . esc_html__( 'All products', 'linker-commerce' ) . '</span></a>';
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

		if ( ( $facets['has_power'] ?? 0 ) >= 3 ) {
			$html .= $this->range_form( __( 'AC power', 'linker-commerce' ), 'kw', __( 'Minimum AC power in kilowatts', 'linker-commerce' ), __( 'Maximum AC power in kilowatts', 'linker-commerce' ), 'kW', $selected );
		}
		if ( ( $facets['has_energy'] ?? 0 ) >= 3 ) {
			$html .= $this->range_form( __( 'Usable energy', 'linker-commerce' ), 'kwh', __( 'Minimum usable energy in kilowatt hours', 'linker-commerce' ), __( 'Maximum usable energy in kilowatt hours', 'linker-commerce' ), 'kWh', $selected );
		}

		$html .= '</div></details>';
		// The live page's sidebar tool card, at the same place (after the
		// filter folds, before the actions), with the review's copy for the
		// renamed tool (docs/acceptance/2026-10-10/12/copy-review.md).
		$configurator = self::configurator_page_url();
		if ( '' !== $configurator ) {
			$html .= '<div class="rail-help">'
				. '<b>' . esc_html__( 'Plan with the Solution Configurator', 'linker-commerce' ) . '</b>'
				. '<p>' . esc_html__( 'Configure a storage system from your site data; the result is a solution draft you can send as an inquiry.', 'linker-commerce' ) . '</p>'
				. '<a class="rail-help-btn" href="' . esc_url( $configurator ) . '">' . esc_html__( 'Open the Solution Configurator', 'linker-commerce' ) . '</a>'
				. '</div>';
		}
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
	 * The current product's catalogue card (inside [lc_loop], or called by the
	 * family grid with a family context).
	 *
	 * With a `family` context (the catalogue's family view, spec: the live
	 * shop lists one card per family) the card carries the live page's family
	 * anatomy: `data-linker-family-card`, the family's article payload in a
	 * `data-linker-articles` JSON script, the series label as the title and
	 * the model picker in place of the single-article model row.
	 *
	 * @param array<string, mixed>|string $atts Shortcode attributes (`family`).
	 */
	public function catalog_card( $atts = array() ): string {
		$parsed     = \is_array( $atts ) ? $atts : shortcode_parse_atts( (string) $atts );
		$family     = isset( $parsed['family'] ) && \is_array( $parsed['family'] ) ? $parsed['family'] : null;
		$product_id = (int) get_the_ID();
		$card       = $this->views->fields( $product_id );
		if ( array() === $card ) {
			return '';
		}
		$product = wc_get_product( $product_id );
		$facts   = SelectionFacts::for_product( $product_id );
		$series  = (string) ( $card['series'] ?? '' );
		$multi   = null !== $family && \count( (array) $family['ids'] ) > 1;
		$title   = $multi && '' !== $series ? $series : (string) $card['title'];
		$gated   = '' !== (string) ( $card['price']['url'] ?? '' );
		$data    = array(
			'data-product-id="' . esc_attr( (string) $product_id ) . '"',
			'data-can-order="' . ( $gated ? '0' : '1' ) . '"',
			'data-sku="' . esc_attr( $card['sku'] ) . '"',
			'data-brand="' . esc_attr( $card['brand_slug'] ) . '"',
			'data-phase="' . esc_attr( (string) $facts->phase ) . '"',
			'data-power="' . esc_attr( \is_float( $facts->ac_power_kw ) ? (string) $facts->ac_power_kw : '0' ) . '"',
			'data-application="' . esc_attr( (string) $facts->application ) . '"',
		);
		$url     = (string) get_permalink( $product_id );

		$html = '<article class="sf-card product-card" data-linker-family-card ' . implode( ' ', $data ) . '>';
		if ( null !== $family && \count( (array) $family['ids'] ) > 1 ) {
			$html .= '<script type="application/json" data-linker-articles>' . wp_json_encode( $this->family_payload( (array) $family['ids'] ) ) . '</script>';
		}
		$html .= '<div class="sf-card-media card-media">';
		$html .= '<button type="button" class="card-compare-checkbox" data-compare-article="' . esc_attr( (string) $product_id ) . '" aria-pressed="false" aria-label="'
			. esc_attr( sprintf( /* translators: %s: product name. */ __( 'Compare: %s', 'linker-commerce' ), (string) $card['title'] ) ) . '">+</button>';
		$html .= '<a data-card-media-link href="' . esc_url( $url ) . '" aria-label="' . esc_attr( $title ) . '">';
		foreach ( \array_slice( (array) $card['gallery'], 0, 1 ) as $image_id ) {
			// The live card image's own attribute set: the stylesheet sizes
			// the box, and the family picker switches src/alt through
			// `data-card-image` (WordPress strips data-* from
			// wp_get_attachment_image's attributes, so the tag is printed
			// here).
			$image_src = wp_get_attachment_image_url( (int) $image_id, 'medium' );
			if ( \is_string( $image_src ) && '' !== $image_src ) {
				$html .= '<img data-card-image src="' . esc_url( $image_src ) . '" alt="' . esc_attr( (string) $card['title'] ) . '" loading="lazy">';
			}
		}
		$html .= '</a></div>';
		$html .= '<div class="card-identity">';
		if ( '' !== $card['brand'] ) {
			$html .= '<p class="sf-card-brand">' . esc_html( $card['brand'] ) . '</p>';
		}
		$html .= '<a class="sf-card-title" data-card-title data-card-series-title="' . esc_attr( $multi && '' !== $series ? $series : '' ) . '" href="' . esc_url( $url ) . '">' . esc_html( $title ) . '</a>';
		// The live catalogue card carries brand, title and item number only:
		// no designation line (measured 2026-10-12, 0/65 cards).
		if ( '' !== $card['sku'] ) {
			$html .= '<p class="sf-card-sku">' . esc_html__( 'Item no.', 'linker-commerce' ) . ' <span data-card-sku>' . esc_html( $card['sku'] ) . '</span></p>';
		}
		$html     .= '</div>';
		$stats     = \is_array( $card['stats'] ) ? $card['stats'] : array();
		$selection = $this->selection_line( $product, $card );
		if ( $multi ) {
			// The live page's family card: the model picker replaces the
			// single-article model row.
			$html .= $this->family_picker( (array) $family['ids'], $product_id, $card, $stats, $selection );
		} elseif ( array() !== $stats ) {
			$html .= '<span class="card-exact-article" data-linker-exact-article><small>' . esc_html__( 'Model', 'linker-commerce' ) . '</small><strong data-card-selection>' . esc_html( $selection ) . '</strong></span>';
		}
		$facts = $product instanceof WC_Product ? Materials::card_facts( $product, 4 ) : array();
		if ( array() !== $facts ) {
			$html .= '<dl class="card-facts" data-card-facts aria-label="' . esc_attr__( 'Key product data', 'linker-commerce' ) . '">';
			foreach ( $facts as $fact ) {
				$html .= '<div><dt>' . esc_html( $fact['label'] ) . '</dt><dd>' . esc_html( $fact['value'] ) . '</dd></div>';
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
	 * The brand name: the breadcrumb's middle segment and the purchase
	 * panel's plain-text fallback when the library holds no logo.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_brand( $atts = array() ): string {
		unset( $atts );
		$view = $this->current_view();
		return null === $view ? '' : esc_html( (string) $view['brand'] );
	}

	/**
	 * The model designation: the H1, the breadcrumb's tail and the project
	 * entry's title.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_model( $atts = array() ): string {
		unset( $atts );
		$view = $this->current_view();
		return null === $view ? '' : esc_html( (string) $view['model'] );
	}

	/**
	 * The purchase panel's brand mark: the brand's light logo image, or the
	 * brand's plain name when the library holds no logo file.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_brand_logo( $atts = array() ): string {
		unset( $atts );
		$view = $this->current_view();
		if ( null === $view ) {
			return '';
		}
		if ( \is_array( $view['brand_logo'] ) ) {
			$logo = $view['brand_logo'];
			$html = '<div class="pdp-brand pdp-brand--logo"><img class="pdp-brand-logo" src="' . esc_url( (string) $logo['src'] ) . '"';
			if ( '' !== (string) $logo['srcset'] ) {
				$html .= ' srcset="' . esc_attr( (string) $logo['srcset'] ) . '"';
			}
			return $html . ' alt="' . esc_attr( (string) $logo['alt'] ) . '" loading="eager" decoding="async" fetchpriority="high" /></div>';
		}
		if ( '' === (string) $view['brand'] ) {
			return '';
		}
		return '<div class="pdp-brand"><span class="pdp-brand-text">' . esc_html( (string) $view['brand'] ) . '</span></div>';
	}

	/**
	 * The line under the H1: what the product name says besides brand and
	 * model.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_designation( $atts = array() ): string {
		unset( $atts );
		$view = $this->current_view();
		return null === $view ? '' : esc_html( (string) $view['designation'] );
	}

	/**
	 * The bare item number (the template prints the "Item number:" label).
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_sku( $atts = array() ): string {
		unset( $atts );
		$view = $this->current_view();
		return null === $view ? '' : esc_html( (string) $view['sku'] );
	}

	/**
	 * The price area: the sign-in prompt and its link for a visitor without
	 * prices, the product's net price for one with (the business gate is the
	 * one authority on which of the two shows).
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_price( $atts = array() ): string {
		unset( $atts );
		$view = $this->current_view();
		if ( null === $view ) {
			return '';
		}
		if ( '' !== (string) $view['price']['url'] ) {
			return '<a class="pdp-price-login" href="' . esc_url( (string) $view['price']['url'] ) . '">' . esc_html( (string) $view['price']['html'] ) . '</a>';
		}
		return '<span class="pdp-price-net">' . wp_kses_post( (string) $view['price']['html'] ) . '</span>';
	}

	/**
	 * The purchase panel's key figures, one row each: the registry's first
	 * figures of the product type, in the type's own order.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_key_stats( $atts = array() ): string {
		unset( $atts );
		$view = $this->current_view();
		if ( null === $view ) {
			return '';
		}
		$product = wc_get_product( (int) $view['id'] );
		if ( ! $product instanceof WC_Product ) {
			return '';
		}
		$html = '';
		foreach ( Materials::key_stats( $product, 4 ) as $stat ) {
			$html .= '<div><span class="pdp-app-stat-icon" aria-hidden="true">' . self::icon( (string) $stat['icon'] ) . '</span>'
				. '<dt>' . esc_html( (string) $stat['label'] ) . '</dt><dd>' . esc_html( (string) $stat['value'] ) . '</dd></div>';
		}
		return $html;
	}

	/**
	 * The availability line: the state with its dot and the delivery
	 * sentence the freight policy derives.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_availability( $atts = array() ): string {
		unset( $atts );
		$view = $this->current_view();
		if ( null === $view ) {
			return '';
		}
		$product = wc_get_product( (int) $view['id'] );
		$html    = '<p class="pdp-avail-label"><span class="pdp-dot is-wait"></span>' . esc_html( (string) $view['availability'] ) . '</p>';
		$note    = $product instanceof WC_Product ? self::delivery_note( $product ) : '';
		if ( '' !== $note ) {
			$html .= '<p class="pdp-avail-note">' . esc_html( $note ) . '</p>';
		}
		return $html;
	}

	/**
	 * The purchase panel's primary action: sign in for partner pricing, or
	 * the solution draft entry when the visitor sees prices.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_cta( $atts = array() ): string {
		unset( $atts );
		$view = $this->current_view();
		if ( null === $view ) {
			return '';
		}
		return '<a class="pdp-btn pdp-btn-dark" href="' . esc_url( (string) $view['cta_url'] ) . '">' . esc_html( (string) $view['cta_label'] ) . '</a>';
	}

	/**
	 * The purchase panel's secondary action: the contact request carrying the
	 * product as its subject.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_ask( $atts = array() ): string {
		unset( $atts );
		$view = $this->current_view();
		if ( null === $view ) {
			return '';
		}
		$contact = array(
			'kind'       => 'product',
			'title'      => (string) $view['title'],
			'url'        => (string) get_permalink( (int) $view['id'] ),
			'source_id'  => (int) $view['id'],
			'product_id' => (int) $view['id'],
			'intent'     => 'product',
		);
		return '<a class="pdp-btn pdp-btn-secondary" href="' . esc_url( (string) $view['ask_url'] ) . '" data-linker-contact="' . esc_attr( (string) wp_json_encode( $contact ) ) . '">'
			. esc_html__( 'Ask about this product', 'linker-commerce' ) . '</a>';
	}

	/**
	 * The three product tools and the comparison chip (`tv_b2b_pdp_tools`):
	 * compare, ask, documents.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_tools( $atts = array() ): string {
		unset( $atts );
		$view = $this->current_view();
		if ( null === $view ) {
			return '';
		}
		$product_id  = (int) $view['id'];
		$ask_message = sprintf(
			/* translators: %s: product name with item number. */
			__( 'About %s: give me the key specs, which batteries or inverters it pairs with, and whether it fits my project.', 'linker-commerce' ),
			trim( (string) $view['title'] . ' (' . (string) $view['sku'] . ')' )
		);
		$html  = '<button type="button" class="pdp-tool" data-compare-article="' . $product_id . '" aria-pressed="false">' . self::icon( 'compare' )
			. '<span data-compare-label>' . esc_html__( 'Compare', 'linker-commerce' ) . '</span></button>';
		$html .= '<button type="button" class="pdp-tool" data-pdp-ask data-ask-message="' . esc_attr( $ask_message ) . '">' . self::icon( 'ask' )
			. esc_html__( 'Ask Linker Advisor', 'linker-commerce' ) . '</button>';
		$html .= '<a class="pdp-tool" href="#downloads">' . self::icon( 'file' )
			. esc_html__( 'Documents', 'linker-commerce' ) . '</a>';
		// The floating comparison chip is not copied here: ComparePage prints
		// it from the footer on every surface that carries a selection
		// control (spec 19 §5, one implementation).
		return $html;
	}

	/**
	 * The project entry's ways into the Advisor: one button per planning
	 * stage, each with its own opening message, plus the nameplate entry.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_project_choices( $atts = array() ): string {
		unset( $atts );
		$view = $this->current_view();
		if ( null === $view ) {
			return '';
		}
		$product_id = (int) $view['id'];
		$material   = Materials::material_for_product( $product_id );
		$shared     = array(
			'data-linker-project-product-prompt' => '',
			'data-product-id'                    => (string) $product_id,
			'data-material-id'                   => \is_array( $material ) ? (string) ( $material['material_id'] ?? '' ) : '',
			'data-material-revision'             => \is_array( $material ) ? (string) ( $material['revision'] ?? '' ) : '',
			'data-product-model'                 => (string) $view['model'],
		);
		$stages     = array(
			array(
				'label' => __( 'New system', 'linker-commerce' ),
				/* translators: %s: product name with item number. */
				'lead'  => __( 'I am planning a new system with %s.', 'linker-commerce' ),
			),
			array(
				'label' => __( 'Extend an existing system', 'linker-commerce' ),
				/* translators: %s: product name with item number. */
				'lead'  => __( 'I am extending an existing system with %s.', 'linker-commerce' ),
			),
			array(
				'label' => __( 'Replace an existing unit', 'linker-commerce' ),
				/* translators: %s: product name with item number. */
				'lead'  => __( 'I am replacing a unit in an existing system with %s.', 'linker-commerce' ),
			),
		);
		$tail       = __( 'Then ask one question at a time for what you still need (existing model, quantity, installation postcode, installation date) and check compatibility, missing system components and delivery windows against current Linker data.', 'linker-commerce' );
		$html       = '';
		foreach ( $stages as $stage ) {
			$message = sprintf( (string) $stage['lead'], trim( (string) $view['title'] . ' (' . (string) $view['sku'] . ')' ) ) . ' ' . $tail;
			$html   .= '<button type="button" class="pdp-project-choice"';
			foreach ( $shared as $attribute => $value ) {
				$html .= ' ' . $attribute . '="' . esc_attr( $value ) . '"';
			}
			$html .= ' data-project-message="' . esc_attr( $message ) . '">' . esc_html( (string) $stage['label'] ) . '</button>';
		}
		$html .= '<button type="button" class="pdp-project-choice pdp-project-choice--nameplate" data-linker-assistant-open="nameplate">'
			. esc_html__( 'Identify a device from a nameplate photo', 'linker-commerce' ) . '</button>';
		return $html;
	}

	/**
	 * The gallery's image pair: the featured image and the first gallery
	 * image side by side, each opening the viewer.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_gallery_pair( $atts = array() ): string {
		unset( $atts );
		$view = $this->current_view();
		if ( null === $view ) {
			return '';
		}
		$product = wc_get_product( (int) $view['id'] );
		if ( ! $product instanceof WC_Product ) {
			return '';
		}
		$ids  = Materials::gallery_ids( $product, Materials::acf( (int) $view['id'] ) );
		$html = '<div class="pdp-gallery-pair">';
		if ( array() === $ids ) {
			return $html . '<div class="pdp-gallery-main-wrap pdp-gallery-empty">'
				. '<p class="tv-empty-state">' . esc_html__( 'Product photography for this model is in preparation.', 'linker-commerce' ) . '</p>'
				. '</div></div>';
		}
		$html .= '<button type="button" class="pdp-gallery-main-wrap" data-pdp-image data-pdp-main data-src="' . esc_url( self::image_url( $ids[0] ) ) . '" data-caption="">'
			. self::image_tag(
				$ids[0],
				'full',
				array(
					'class'  => 'pdp-gallery-main',
					'alt'    => (string) $view['title'],
					'srcset' => null,
				)
			) . '</button>';
		if ( isset( $ids[1] ) ) {
			$html .= '<button type="button" class="pdp-gallery-secondary" data-pdp-image data-src="' . esc_url( self::image_url( $ids[1] ) ) . '" data-caption="" aria-label="' . esc_attr__( 'Product image 2', 'linker-commerce' ) . '">'
				. self::image_tag( $ids[1], 'full', array( 'alt' => '' ) ) . '</button>';
		}
		return $html . '</div>';
	}

	/**
	 * The gallery's thumbnail column: one button per image, the first pressed.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_gallery_thumbs( $atts = array() ): string {
		unset( $atts );
		$view = $this->current_view();
		if ( null === $view ) {
			return '';
		}
		$product = wc_get_product( (int) $view['id'] );
		if ( ! $product instanceof WC_Product ) {
			return '';
		}
		$ids = Materials::gallery_ids( $product, Materials::acf( (int) $view['id'] ) );
		if ( \count( $ids ) < 2 ) {
			return '';
		}
		$html = '<div class="pdp-thumbs">';
		foreach ( $ids as $index => $id ) {
			// The live page renders the 300w candidate at `sizes="72px"`, i.e.
			// at density 300/72 — and that density is visible: the same file at
			// density 1 rasterises differently on this strip. Measured
			// 2026-10-11: with the full srcset the browser re-selects the
			// original file (naturalWidth 72, as live's own re-selection does),
			// so the tag offers exactly the candidate the live page renders —
			// same decoded bitmap as live, strip 0/48640 pixels.
			$medium     = wp_get_attachment_image_src( $id, 'medium' );
			$attributes = array(
				'class'    => 'attachment-medium size-medium',
				'alt'      => '',
				'sizes'    => '72px',
				'decoding' => 'async',
			);
			if ( \is_array( $medium ) ) {
				$attributes['srcset'] = $medium[0] . ' ' . (int) $medium[1] . 'w';
			}
			$html .= '<button type="button" data-pdp-thumb data-src="' . esc_url( self::image_url( $id ) ) . '" data-caption=""'
				. ' aria-label="' . esc_attr( sprintf( /* translators: %d: image number. */ __( 'Product image %d', 'linker-commerce' ), $index + 1 ) ) . '"'
				. ' aria-pressed="' . ( 0 === $index ? 'true' : 'false' ) . '" class="pdp-thumb">'
				. self::image_tag( $id, 'medium', $attributes ) . '</button>';
		}
		return $html . '</div>';
	}

	/**
	 * The description panel's introduction paragraphs.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_intro( $atts = array() ): string {
		unset( $atts );
		$view = $this->current_view();
		if ( null === $view ) {
			return '';
		}
		if ( '' !== (string) $view['intro'] ) {
			return wp_kses_post( wpautop( (string) $view['intro'] ) );
		}
		if ( '' !== (string) $view['body'] ) {
			return wp_kses_post( wpautop( (string) $view['body'] ) );
		}
		return '<p class="tv-empty-state">' . esc_html__( 'Introduction in preparation. The specification below carries the values from the datasheet on file.', 'linker-commerce' ) . '</p>';
	}

	/**
	 * The description panel's benefit cards, two at most.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_benefits( $atts = array() ): string {
		unset( $atts );
		$view  = $this->current_view();
		$items = array();
		foreach ( \is_array( $view['benefits'] ?? null ) ? $view['benefits'] : array() as $line ) {
			if ( '' !== $line ) {
				$items[] = '<li class="pdp-benefit">' . self::icon( 'check' ) . '<div><p>' . esc_html( $line ) . '</p></div></li>';
			}
		}
		if ( array() === $items ) {
			return '';
		}
		return '<ul class="pdp-benefits">' . implode( '', $items ) . '</ul>';
	}

	/**
	 * The disclosure rows under the description panel: the product's feature
	 * cards as closed rows.
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
			if ( '' === trim( (string) $feature['body'] ) || (int) ( $feature['image'] ?? 0 ) > 0 ) {
				continue;
			}
			$html .= '<details class="pdp-disclose"><summary>' . esc_html( (string) $feature['title'] ) . self::icon( 'chevron' ) . '</summary>'
				. '<div class="pdp-disclose-body pdp-reading"><p>' . esc_html( (string) $feature['body'] ) . '</p></div></details>';
		}
		return $html;
	}

	/**
	 * The description's feature sections: the feature cards that carry an
	 * image, as the live page's `.pdp-feature` blocks (media beside the title
	 * and body). The cards without an image render as disclosure rows.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_features( $atts = array() ): string {
		unset( $atts );
		$view = $this->current_view();
		if ( null === $view ) {
			return '';
		}
		$html = '';
		foreach ( \is_array( $view['features'] ) ? $view['features'] : array() as $feature ) {
			$image = (int) ( $feature['image'] ?? 0 );
			if ( $image <= 0 ) {
				continue;
			}
			$html .= '<section class="pdp-feature"><div class="pdp-feature-media">'
				. self::image_tag(
					$image,
					'large',
					array(
						'class'   => 'pdp-feature-image',
						'alt'     => (string) $feature['title'],
						'loading' => 'lazy',
					)
				)
				. '</div><div class="pdp-feature-copy"><h3 class="pdp-section-title">' . esc_html( (string) $feature['title'] ) . '</h3>'
				. '<div class="pdp-reading pdp-muted pdp-feature-body"><p>' . esc_html( (string) $feature['body'] ) . '</p></div></div></section>';
		}
		return $html;
	}

	/**
	 * The technical data: the spec groups as the tab deck the page shows —
	 * one tab per group, one panel per tab, the first one open.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_specs( $atts = array() ): string {
		unset( $atts );
		$view  = $this->current_view();
		$html  = '';
		$decks = array();
		$group = \is_array( $view['spec_groups'] ?? null ) ? $view['spec_groups'] : array();
		if ( array() !== $group ) {
			foreach ( $group as $spec_group ) {
				$body = '<dl class="pdp-stat-wrap">';
				foreach ( $spec_group['rows'] as $row ) {
					$value = trim( (string) $row['value'] . ' ' . (string) $row['unit'] );
					$body .= '<div class="pdp-stat-row"><dt>' . esc_html( $row['label'] ) . '</dt><dd>' . esc_html( $value );
					if ( '' !== $row['note'] ) {
						$body .= '<div class="pdp-reading pdp-muted">' . esc_html( $row['note'] ) . '</div>';
					}
					$body .= '</dd></div>';
				}
				$body   .= '</dl>';
				$decks[] = array(
					'title' => (string) $spec_group['title'],
					'body'  => $body,
				);
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
				$decks[] = array(
					'title' => __( 'Specifications', 'linker-commerce' ),
					'body'  => $body,
				);
			}
		}
		if ( array() === $decks ) {
			return '<p class="tv-empty-state">' . esc_html__( 'The specification table for this product is in preparation. Ask us for the datasheet.', 'linker-commerce' ) . '</p>';
		}
		$html .= '<div class="pdp-stats-layout">' . $this->stats_summary( $view, $group ) . '<div class="pdp-info-deck pdp-spec-deck">';
		$html .= '<div class="pdp-info-tabs" role="tablist" aria-label="' . esc_attr__( 'Specification group', 'linker-commerce' ) . '">';
		foreach ( $decks as $index => $deck ) {
			$html .= '<button type="button" id="pdp-spec-tab-' . $index . '" role="tab" aria-controls="pdp-spec-panel-' . $index . '" aria-selected="' . ( 0 === $index ? 'true' : 'false' ) . '" tabindex="' . ( 0 === $index ? '0' : '-1' ) . '">' . esc_html( $deck['title'] ) . '</button>';
		}
		$html .= '</div>';
		foreach ( $decks as $index => $deck ) {
			$html .= '<div class="pdp-info-panel" id="pdp-spec-panel-' . $index . '"' . ( 0 === $index ? '' : ' hidden' ) . ' role="tabpanel" aria-labelledby="pdp-spec-tab-' . $index . '" tabindex="0">'
				. '<details class="pdp-disclose pdp-tab-disclosure" open><summary>' . esc_html( $deck['title'] ) . self::icon( 'chevron' ) . '</summary>'
				. '<div class="pdp-disclose-body pdp-reading">' . $deck['body'] . '</div></details></div>';
		}
		return $html . '</div></div>';
	}

	/**
	 * The technical data's summary column: the live page's `.pdp-stats-summary`
	 * — the claim's kicker, the highlighted specification rows as a stat wrap,
	 * and the "About these specifications" context. Empty as the live page
	 * leaves it when the product carries no claim and no highlighted rows.
	 *
	 * @param array<string, mixed>|null $view  The product's replica fields.
	 * @param array<mixed>              $group The spec groups.
	 */
	private function stats_summary( ?array $view, array $group ): string {
		$claim = \is_array( $view['stats_claim'] ?? null ) ? $view['stats_claim'] : array();
		$rows  = \is_array( $claim['cards'] ?? null ) ? $claim['cards'] : array();
		if ( array() === $claim && array() === $group ) {
			return '<div class="pdp-stats-summary"></div>';
		}
		$html = '<div class="pdp-stats-summary">';
		if ( '' !== (string) ( $claim['label'] ?? '' ) ) {
			$html .= '<p class="pdp-kicker">' . esc_html( (string) $claim['label'] ) . '</p>';
		}
		if ( array() !== $rows ) {
			$html .= '<dl class="pdp-stat-wrap">';
			foreach ( $rows as $row ) {
				$html .= '<div class="pdp-stat-row"><dt>' . esc_html( (string) $row['label'] ) . '</dt><dd>' . esc_html( (string) $row['value'] ) . '</dd></div>';
			}
			$html .= '</dl>';
		}
		if ( '' !== (string) ( $claim['title'] ?? '' ) || '' !== (string) ( $claim['body'] ?? '' ) ) {
			$html .= '<details class="pdp-stats-context"><summary>' . esc_html__( 'About these specifications', 'linker-commerce' ) . '</summary>';
			if ( '' !== (string) $claim['title'] ) {
				$html .= '<h3 class="pdp-section-title">' . esc_html( (string) $claim['title'] ) . '</h3>';
			}
			if ( '' !== (string) $claim['body'] ) {
				$html .= '<div class="pdp-reading pdp-muted">' . wp_kses_post( $claim['body'] ) . '</div>';
			}
			$html .= '</details>';
		}
		return $html . '</div>';
	}

	/**
	 * The project-fit section's body (#16 GAP-2): the intra-page navigation
	 * aside and one scenario block per `application_scenarios` entry.
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
		$html = '<p class="pdp-reading">' . esc_html(
			sprintf(
				/* translators: %s: product name. */
				__( "Scenarios that show which projects the %s belongs in, and the limits behind our engineers' recommendation.", 'linker-commerce' ),
				(string) $view['title']
			)
		) . '</p>';
		$index = 0;
		foreach ( $scenarios as $scenario ) {
			$kind  = 'application' === (string) ( $scenario['kind'] ?? '' ) ? __( 'Project scenario', 'linker-commerce' ) : __( 'Project note', 'linker-commerce' );
			$html .= '<div class="fit-scn">';
			$html .= '<header class="fit-head"><span class="fit-num">' . esc_html( sprintf( '%02d', $index + 1 ) ) . '</span>'
				. '<div><span class="fit-kind">' . esc_html( $kind ) . '</span>'
				. '<h3>' . esc_html( (string) $scenario['title'] ) . '</h3></div></header>';
			// The scenario's three parts are one deck, as the live page renders
			// them: the tab strip stays hidden and every panel shows.
			$tabs  = array( __( 'Project', 'linker-commerce' ), __( 'Checks', 'linker-commerce' ), __( 'Linker view', 'linker-commerce' ) );
			$html .= '<div class="pdp-info-deck pdp-project-deck pdp-all-panels">';
			$html .= '<div class="pdp-info-tabs" role="tablist" aria-label="' . esc_attr__( 'Project information', 'linker-commerce' ) . '" hidden>';
			foreach ( $tabs as $position => $label ) {
				$html .= '<button type="button" id="pdp-project-' . $index . '-tab-' . $position . '" role="tab" aria-controls="pdp-project-' . $index . '-panel-' . $position . '"'
					. ' aria-selected="' . ( 0 === $position ? 'true' : 'false' ) . '" tabindex="' . ( 0 === $position ? '0' : '-1' ) . '">' . esc_html( $label ) . '</button>';
			}
			$html .= '</div>';
			$html .= '<div class="pdp-info-panel" id="pdp-project-' . $index . '-panel-0"><div class="fit-body">';
			if ( (int) $scenario['image'] > 0 ) {
				$html .= '<figure>' . wp_get_attachment_image( (int) $scenario['image'], 'large', false, array( 'alt' => (string) $scenario['title'] ) ) . '</figure>';
			}
			$html .= '<div class="fit-text">';
			if ( '' !== (string) $scenario['situation'] ) {
				$html .= '<p class="fit-lede">' . esc_html( (string) $scenario['situation'] ) . '</p>';
			}
			if ( '' !== (string) $scenario['fit'] ) {
				$html .= '<div class="fit-prose pdp-reading">' . wp_kses_post( wpautop( (string) $scenario['fit'] ) ) . '</div>';
			}
			$html .= '</div></div></div>';
			$html .= '<div class="pdp-info-panel" id="pdp-project-' . $index . '-panel-1"><div class="fit-checkwrap"><span class="fit-label">' . esc_html__( 'Limits for the configuration', 'linker-commerce' ) . '</span><ul class="fit-check">';
			foreach ( (array) $scenario['checklist'] as $check ) {
				$html .= '<li>' . esc_html( (string) $check ) . '</li>';
			}
			$html .= '</ul></div></div>';
			$html .= '<div class="pdp-info-panel" id="pdp-project-' . $index . '-panel-2"><aside class="fit-verdict"><span class="fit-label">' . esc_html__( "Linker's read", 'linker-commerce' ) . '</span>'
				. '<p>' . esc_html( (string) $scenario['verdict'] ) . '</p></aside></div>';
			$html .= '</div>';
			$html .= '</div>';
			++$index;
		}
		return $html;
	}

	/**
	 * The document cards: one card per hosted document of the product.
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
			$meta  = array_filter(
				array(
					Materials::document_kind_label( (string) $document['kind'] ),
					'PDF',
					(string) $document['language'],
				),
				static fn( string $part ): bool => '' !== $part
			);
			$html .= '<a class="pdp-doc" href="' . esc_url( (string) $document['url'] ) . '" target="_blank" rel="noopener">';
			$html .= '<span class="pdp-doc-icon">' . self::icon( 'file' ) . '</span>';
			$html .= '<span class="grow">' . esc_html( (string) $document['title'] )
				. '<span class="pdp-doc-meta">' . esc_html( implode( ' · ', $meta ) ) . '</span>'
				. '</span>' . self::icon( 'download' ) . '</a>';
		}
		return $html;
	}

	/**
	 * The compatibility records: the pairing cards from the registry's
	 * relationships, in the order of the paired products' names, and the
	 * constraints the cited documents state.
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
			if ( 'de' === $locale && \function_exists( 'pll_get_post' ) ) {
				$twin = (int) pll_get_post( $target_id, 'de' );
				if ( $twin > 0 ) {
					$target_id = $twin;
				}
			}
			$target = $target_id ? wc_get_product( $target_id ) : null;
			if ( ! $target instanceof WC_Product || 'publish' !== $target->get_status() ) {
				continue;
			}
			$status     = self::pairing_status( $relationship, $locale );
			$cards[]    = array(
				'name' => (string) $target->get_name(),
				'html' => '<a class="pdp-pairing" href="' . esc_url( (string) get_permalink( $target_id ) ) . '">'
					. wp_get_attachment_image(
						(int) $target->get_image_id(),
						'medium',
						false,
						array(
							'alt'     => $target->get_name(),
							'loading' => 'lazy',
						)
					)
					. '<span class="pdp-pairing-copy">'
					. '<span class="pdp-pairing-name">' . esc_html( $target->get_name() ) . '</span>'
					. '<span class="pdp-pairing-sku">' . esc_html__( 'Item number', 'linker-commerce' ) . ' ' . esc_html( (string) $target->get_sku() ) . '</span>'
					. '<span class="pdp-pairing-chips"><span class="pdp-doc-meta">' . esc_html( $status ) . '</span></span>'
					. '</span></a>',
			);
			$constraint = Materials::localized_text( $relationship, 'constraint', $locale );
			if ( '' !== $constraint && ! isset( $notes[ $constraint ] ) ) {
				$notes[ $constraint ] = true;
			}
		}
		if ( array() === $cards ) {
			return '';
		}
		\usort( $cards, static fn( array $left, array $right ): int => strnatcasecmp( $left['name'], $right['name'] ) );
		$html = '<div class="pdp-pairings">' . implode( '', array_column( $cards, 'html' ) ) . '</div>';
		foreach ( array_keys( $notes ) as $note ) {
			$html .= '<div class="pdp-pairing-footnote pdp-reading pdp-muted"><p>' . esc_html( (string) $note ) . '</p></div>';
		}
		return $html;
	}

	/**
	 * What the contract says about one relationship
	 * (tv_b2b_pdp_pairing_status).
	 *
	 * @param array<string, mixed> $relationship The registry relationship.
	 * @param string               $locale       'de' or 'en'.
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
	 *
	 * @param int $product_id The product.
	 */
	private static function source_id( int $product_id ): int {
		return Materials::source_product_id( $product_id );
	}

	/**
	 * The delivery sentence of the availability line, from the product's
	 * freight outcome.
	 *
	 * @param WC_Product $product The product.
	 */
	private static function delivery_note( WC_Product $product ): string {
		$fact    = Materials::logistics( (int) $product->get_id(), $product );
		$outcome = Materials::freight_outcome( $fact );
		$parts   = array_filter( array( (string) $outcome['headline'], (string) $outcome['detail'] ) );
		return implode( ' · ', $parts );
	}

	/**
	 * The catalogue's family grid: the live shop lists one card per family
	 * (docs/acceptance/2026-10-11/16/working/replica-r4/EVIDENCE.md §6-2).
	 *
	 * The rows come from the same product set the filters scope
	 * (archive_product_ids(): published, catalog-visible, the queried category
	 * and the selected filters), grouped by the family the data defines.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function catalog_families( $atts = array() ): string {
		unset( $atts );
		$ids  = array_values( $this->filters->archive_product_ids() );
		$rows = $this->family_rows( $ids );
		$page = max( 1, (int) wp_unslash( $_GET['product-page'] ?? 1 ) ); // phpcs:ignore WordPress.Security.NonceVerification.Recommended, WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- a public catalogue page number, cast to int.
		$html = '';
		foreach ( \array_slice( $rows, ( $page - 1 ) * self::PER_PAGE_FAMILIES, self::PER_PAGE_FAMILIES ) as $row ) {
			$lead = get_post( (int) $row['lead'] );
			if ( ! $lead instanceof \WP_Post ) {
				continue;
			}
			// The card fragment reads the loop's post; set it to this family's
			// lead article for the call.
			$GLOBALS['post'] = $lead; // phpcs:ignore WordPress.WP.GlobalVariablesOverride.Prohibited -- the loop contract the card fragment reads.
			setup_postdata( $lead );
			$html .= $this->catalog_card( array( 'family' => $row ) );
			wp_reset_postdata();
		}
		return $html;
	}

	/**
	 * The result line of the family view: "1-24 / 65 product families".
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function catalog_family_count( $atts = array() ): string {
		unset( $atts );
		$total = \count( $this->family_rows( array_values( $this->filters->archive_product_ids() ) ) );
		$page  = max( 1, (int) wp_unslash( $_GET['product-page'] ?? 1 ) ); // phpcs:ignore WordPress.Security.NonceVerification.Recommended, WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- a public catalogue page number, cast to int.
		$from  = $total > 0 ? ( $page - 1 ) * self::PER_PAGE_FAMILIES + 1 : 0;
		$to    = min( $total, $page * self::PER_PAGE_FAMILIES );
		return '<b>' . esc_html( $from . '-' . $to ) . '</b> / ' . esc_html( sprintf( /* translators: %d: number of product families. */ _n( '%d product family', '%d product families', $total, 'linker-commerce' ), $total ) );
	}

	/**
	 * The family view's pagination: the live page's own `product-page`
	 * addresses, one per family page.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function catalog_family_pagination( $atts = array() ): string {
		unset( $atts );
		$total = \count( $this->family_rows( array_values( $this->filters->archive_product_ids() ) ) );
		$pages = (int) ceil( $total / self::PER_PAGE_FAMILIES );
		if ( $pages < 2 ) {
			return '';
		}
		$page = max( 1, min( $pages, (int) wp_unslash( $_GET['product-page'] ?? 1 ) ) ); // phpcs:ignore WordPress.Security.NonceVerification.Recommended, WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- a public catalogue page number, cast to int.
		$base = $this->archive_base_url();
		$html = '<nav class="tv-woo-pagination" aria-label="' . esc_attr__( 'Product pagination', 'linker-commerce' ) . '">';
		// The live page numbers every address, page one included, and adds the
		// "Previous" step on the pages after it (measured 2026-10-12).
		if ( $page > 1 ) {
			$html .= '<a class="prev page-numbers" href="' . esc_url( add_query_arg( 'product-page', $page - 1, $base ) ) . '">' . esc_html__( 'Previous', 'linker-commerce' ) . '</a>';
		}
		for ( $i = 1; $i <= $pages; $i++ ) {
			$url   = add_query_arg( 'product-page', $i, $base );
			$html .= $i === $page
				? '<span aria-current="page" class="page-numbers current">' . esc_html( (string) $i ) . '</span>'
				: '<a class="page-numbers" href="' . esc_url( $url ) . '">' . esc_html( (string) $i ) . '</a>';
		}
		if ( $page < $pages ) {
			$html .= '<a class="next page-numbers" href="' . esc_url( add_query_arg( 'product-page', $page + 1, $base ) ) . '">' . esc_html__( 'Next', 'linker-commerce' ) . '</a>';
		}
		return $html . '</nav>';
	}

	/**
	 * The catalogue's contact invitation: the live page's own
	 * `section.linker-contact-invitation.linker-contact-catalog`, the last
	 * block of the results column after the pagination. The words are the
	 * live page's (verbatim, EN and DE, read off its four catalogue pages
	 * 2026-10-12); the address carries this page as the request's context,
	 * the contact page of the page's language as its target, the team
	 * mailbox beneath (the live page's own shape).
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function catalog_contact( $atts = array() ): string {
		unset( $atts );
		$queried = get_queried_object();
		$is_term = $queried instanceof WP_Term;
		$shop_id = function_exists( 'wc_get_page_id' ) ? (int) wc_get_page_id( 'shop' ) : 0;
		$source  = $is_term
			? $this->term_link( $queried )
			: ( $shop_id > 0 ? (string) get_permalink( $shop_id ) : (string) wc_get_page_permalink( 'shop' ) );
		$name    = $is_term
			? (string) $queried->name
			: ( $shop_id > 0 ? (string) get_the_title( $shop_id ) : __( 'Products', 'linker-commerce' ) );
		$title   = $is_term
			/* translators: %s: product category name. */
			? sprintf( __( 'Category: %s', 'linker-commerce' ), $name )
			/* translators: %s: shop page title. */
			: sprintf( __( 'Archives: %s', 'linker-commerce' ), $name );
		$request = $this->filters->requested();
		$search  = (string) ( $request['q'] ?? '' );
		$filters = array();
		foreach ( $request as $facet => $value ) {
			if ( 'q' !== $facet ) {
				$filters[ $facet ] = $value;
			}
		}
		$contact = array(
			'kind'    => 'catalogue',
			'title'   => $title,
			'url'     => $source,
			'search'  => $search,
			'filters' => $filters,
			'intent'  => 'product',
		);
		$url     = (string) add_query_arg(
			array(
				'intent' => 'product',
				'kind'   => 'catalogue',
				'title'  => $title,
				'search' => $search,
				'source' => $source,
			),
			Shortcodes::contact_page_url()
		);

		$html  = '<section class="linker-contact-invitation linker-contact-catalog">';
		$html .= '<div>';
		$html .= '<span class="linker-contact-eyebrow">' . esc_html__( 'CONTACT LINKER', 'linker-commerce' ) . '</span>';
		$html .= '<h2>' . esc_html__( 'Not sure which model to look for?', 'linker-commerce' ) . '</h2>';
		$html .= '<p>' . esc_html__( 'Your question includes this page as context. You can remove it before sending.', 'linker-commerce' ) . '</p>';
		$html .= '</div>';
		$html .= '<div class="linker-contact-invitation-actions">';
		$html .= '<a class="linker-contact-primary" href="' . esc_url( $url ) . '" data-linker-contact="' . esc_attr( (string) wp_json_encode( $contact ) ) . '">' . esc_html__( 'Need help choosing?', 'linker-commerce' ) . '</a>';
		$html .= '<a class="linker-contact-email" href="mailto:' . esc_attr( ( new Options() )->team_to() ) . '">' . esc_html( ( new Options() )->team_to() ) . '</a>';
		$html .= '</div>';
		return $html . '</section>';
	}

	/**
	 * A crumb word as the live page prints it: uppercase.
	 *
	 * @param string $word The word.
	 */
	private static function upper( string $word ): string {
		return \function_exists( 'mb_strtoupper' ) ? \mb_strtoupper( $word ) : \strtoupper( $word );
	}

	/**
	 * The category's name as the live crumb prints it: the English term's,
	 * on the German page too (the live German archive reads "INVERTERS").
	 *
	 * @param WP_Term $term The queried category.
	 */
	private function category_crumb_name( WP_Term $term ): string {
		if ( \function_exists( 'pll_get_term' ) ) {
			$english = (int) pll_get_term( (int) $term->term_id, 'en' );
			if ( $english > 0 ) {
				$source = get_term( $english );
				if ( $source instanceof WP_Term ) {
					return (string) $source->name;
				}
			}
		}
		return (string) $term->name;
	}

	/**
	 * The address of the current catalogue view without its page number.
	 */
	private function archive_base_url(): string {
		$queried = get_queried_object();
		$base    = $queried instanceof \WP_Term ? $this->term_link( $queried ) : (string) wc_get_page_permalink( 'shop' );
		// The selected filters stay in the address; only the page number is
		// rewritten per link.
		return remove_query_arg( array( 'product-page' ), $base );
	}

	/**
	 * The catalogue's family rows: one row per family, first row wins,
	 * over the given product ids in their order.
	 *
	 * A product's family is the article list the product data carries
	 * (`_tv_legacy_acf_json`'s `family_variants`, the same field the product
	 * page's model selector reads) plus the product itself; products that
	 * list no sibling are their own family. Measured on the live shop
	 * 2026-10-11: 65 families over its 104 catalog-visible articles, 24 to a
	 * page, the family card's payload carrying the member articles.
	 *
	 * @param array<int> $ids The catalogue's product ids, in display order.
	 * @return array<int, array{lead: int, ids: array<int>}>
	 */
	private function family_rows( array $ids ): array {
		$present = array_fill_keys( array_map( 'intval', $ids ), true );
		$lists   = $this->family_lists( $ids );
		$rows    = array();
		$seen    = array();
		foreach ( $ids as $id ) {
			$id = (int) $id;
			if ( isset( $seen[ $id ] ) ) {
				continue;
			}
			$members = $this->family_members( $id, $present, $lists );
			foreach ( $members as $member ) {
				$seen[ $member ] = true;
			}
			$rows[] = array(
				'lead' => $id,
				'ids'  => $members,
			);
		}
		return $rows;
	}

	/**
	 * Every catalogue product's own family list, in the current language
	 * (the English product carries the list; the German twin resolves through
	 * the pair).
	 *
	 * @param array<int> $ids The catalogue's product ids.
	 * @return array<int, array<int, array<string, mixed>>> Lists by product id.
	 */
	private function family_lists( array $ids ): array {
		$lang  = \function_exists( 'pll_current_language' ) ? (string) pll_current_language() : '';
		$lists = array();
		foreach ( $ids as $id ) {
			$id     = (int) $id;
			$source = $id;
			if ( '' !== $lang && \function_exists( 'pll_get_post' ) ) {
				$english = (int) pll_get_post( $id, 'en' );
				if ( $english > 0 ) {
					$source = $english;
				}
			}
			$legacy       = json_decode( (string) get_post_meta( $source, '_tv_legacy_acf_json', true ), true );
			$variants     = \is_array( $legacy ) ? ( $legacy['family_variants'] ?? null ) : null;
			$lists[ $id ] = \is_array( $variants ) ? array_values( $variants ) : array();
		}
		return $lists;
	}

	/**
	 * Whether the sibling names the family back (in the current language).
	 *
	 * @param int                                          $sibling    The sibling id.
	 * @param int                                          $product_id The product asking.
	 * @param array<int, array<int, array<string, mixed>>> $lists      The catalogue's lists.
	 * @param string                                       $lang       The current language.
	 */
	private function names_family( int $sibling, int $product_id, array $lists, string $lang ): bool {
		foreach ( $lists[ $sibling ] ?? array() as $row ) {
			$id = (int) ( $row['id'] ?? 0 );
			if ( $id <= 0 ) {
				continue;
			}
			if ( '' !== $lang && \function_exists( 'pll_get_post' ) ) {
				$translated = (int) pll_get_post( $id, $lang );
				if ( $translated > 0 ) {
					$id = $translated;
				}
			}
			if ( $id === $product_id ) {
				return true;
			}
		}
		return false;
	}

	/**
	 * One product's family members, filtered to the catalogue's set: the
	 * product plus the sibling ids its data lists, ordered as the data lists
	 * them (the picker's order) with the product first only when it leads its
	 * own list.
	 *
	 * @param int                                          $product_id The product.
	 * @param array<int, true>                             $present    The ids the catalogue shows.
	 * @param array<int, array<int, array<string, mixed>>> $lists      Every product's own family list.
	 * @return array<int>
	 */
	private function family_members( int $product_id, array $present, array $lists ): array {
		$lang = \function_exists( 'pll_current_language' ) ? (string) pll_current_language() : '';
		// The family list lives on the English product; the German twin
		// carries the same family through the translation pair of every
		// member.
		$source = $product_id;
		if ( '' !== $lang && \function_exists( 'pll_get_post' ) ) {
			$english = (int) pll_get_post( $product_id, 'en' );
			if ( $english > 0 ) {
				$source = $english;
			}
		}
		$rows = $lists[ $product_id ] ?? array();
		$ids  = array();
		foreach ( $rows as $row ) {
			$id = (int) ( $row['id'] ?? 0 );
			if ( $id <= 0 ) {
				continue;
			}
			if ( '' !== $lang && \function_exists( 'pll_get_post' ) ) {
				$translated = (int) pll_get_post( $id, $lang );
				if ( $translated > 0 ) {
					$id = $translated;
				}
			}
			// A sibling counts as family only when it names the family back:
			// the live page renders the same list this way (the products that
			// carry no list of their own stay single cards — EVIDENCE §6-2).
			if ( isset( $present[ $id ] ) && $this->names_family( $id, $product_id, $lists, $lang ) ) {
				$ids[] = $id;
			}
		}
		if ( ! \in_array( $product_id, $ids, true ) ) {
			$ids[] = $product_id;
		}
		$ids = \array_values( \array_unique( $ids ) );
		if ( $product_id !== $ids[0] ) {
			$ids = \array_values( \array_filter( $ids, static fn( int $id ): bool => $id !== $product_id ) );
			\array_unshift( $ids, $product_id );
		}
		return $ids;
	}

	/**
	 * The card's model line: the product's own first key figure plus the model
	 * — live's `.card-exact-article` ("RS485 · GW60K-STS-G10",
	 * "Class B / 1.0 · DTSU666").
	 *
	 * @param \WC_Product|false|null $product The product.
	 * @param array<string, mixed>   $card    The card fields.
	 */
	private function selection_line( $product, array $card ): string {
		$facts = $product instanceof \WC_Product ? Materials::card_facts( $product, 1 ) : array();
		$first = (string) ( $facts[0]['value'] ?? '' );
		if ( '' === $first ) {
			$first = (string) ( \is_array( $card['stats'] ) ? ( $card['stats'][0]['value'] ?? '' ) : '' );
		}
		return '' !== $first ? $first . ' · ' . (string) $card['model'] : (string) $card['model'];
	}

	/**
	 * The family card's article payload: the same keys the live page's
	 * `data-linker-articles` JSON carries, one row per member.
	 *
	 * @param array<int> $ids The family's article ids.
	 * @return array<int, array<string, mixed>>
	 */
	private function family_payload( array $ids ): array {
		$payload = array();
		foreach ( $ids as $id ) {
			$card = $this->views->fields( (int) $id );
			if ( array() === $card ) {
				continue;
			}
			$product   = wc_get_product( (int) $id );
			$stats     = \is_array( $card['stats'] ) ? $card['stats'] : array();
			$gated     = '' !== (string) ( $card['price']['url'] ?? '' );
			$facts     = $product instanceof WC_Product ? Materials::card_facts( $product, 4 ) : array();
			$factshtml = '';
			foreach ( $facts as $fact ) {
				$factshtml .= '<div><dt>' . esc_html( $fact['label'] ) . '</dt><dd>' . esc_html( $fact['value'] ) . '</dd></div>';
			}
			$payload[] = array(
				'id'           => (int) $id,
				'sku'          => (string) $card['sku'],
				'name'         => (string) $card['title'],
				'model'        => (string) $card['model'],
				'url'          => (string) get_permalink( (int) $id ),
				'image'        => (string) wp_get_attachment_image_url( (int) ( $card['gallery'][0] ?? 0 ), 'medium' ),
				'priceHtml'    => $gated
					? '<a class="sf-card-price-login" href="' . esc_url( (string) $card['price']['url'] ) . '">' . esc_html( (string) $card['price']['html'] ) . '</a>'
					: '<span class="sf-card-price-net">' . esc_html( wp_strip_all_tags( (string) $card['price']['html'] ) ) . '</span>',
				'availability' => (string) $card['availability'],
				'canPurchase'  => ! $gated,
				'addToCartUrl' => '',
				'accountUrl'   => (string) $card['price']['url'],
				'selection'    => $this->selection_line( $product, $card ),
				'factsHtml'    => $factshtml,
			);
		}
		return $payload;
	}

	/**
	 * The family card's model picker: the live page's
	 * `details.sf-card-variants.card-article-picker` with one button per
	 * member article (the current one marked).
	 *
	 * @param array<int>                                      $ids        The family's article ids.
	 * @param int                                             $current_id The article the card shows.
	 * @param array<string, mixed>                            $card       The current card fields.
	 * @param array<int, array{label: string, value: string}> $stats      The current key figures.
	 * @param string                                          $selection  The card's model line.
	 */
	private function family_picker( array $ids, int $current_id, array $card, array $stats, string $selection ): string {
		$heading = __( 'All models', 'linker-commerce' );
		$html    = '<details class="sf-card-variants card-article-picker" data-picker-heading="' . esc_attr( $heading ) . '">';
		$html   .= '<summary><span class="card-selection-copy"><small>' . esc_html__( 'Selected model', 'linker-commerce' ) . '</small> <strong data-card-selection>' . esc_html( $selection ) . '</strong></span> <span class="card-selection-action">' . esc_html( $heading ) . '</span></summary>';
		$html   .= '<div class="card-article-picker__list" data-picker-heading="' . esc_attr( $heading ) . '">';
		foreach ( $ids as $id ) {
			$row   = $this->views->fields( (int) $id );
			$html .= '<button type="button" class="sf-card-variant" data-linker-select-article="' . esc_attr( (string) $id ) . '"' . ( (int) $id === $current_id ? ' aria-current="true"' : '' ) . '><span>' . esc_html( (string) ( $row['model'] ?? '' ) ) . '</span> <small>' . esc_html__( 'Item no.', 'linker-commerce' ) . ' ' . esc_html( (string) ( $row['sku'] ?? '' ) ) . '</small></button>';
		}
		return $html . '</div></details>';
	}

	/**
	 * The header's utility cluster: search, cart (with its count), account and
	 * the language toggle — the four controls the live header carries in
	 * `[data-tv-account-slot]` (measured 2026-10-12: 46 + 46 + 44 + 88 px in
	 * one row). Markup only, with the live classes; the header partial's own
	 * stylesheet lays them out. `part="mobile-language"` renders only the
	 * toggle the header shows beside the hamburger under 1280px.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function header_utilities( $atts = array() ): string {
		$attributes = shortcode_atts( array( 'part' => 'all' ), (array) $atts );
		if ( 'mobile-language' === $attributes['part'] ) {
			return $this->language_toggle( 'lnk-lang-toggle--mobile' );
		}
		$cart_url      = function_exists( 'wc_get_cart_url' ) ? (string) wc_get_cart_url() : '';
		$account       = function_exists( 'wc_get_account_endpoint_url' ) ? (string) wc_get_account_endpoint_url( 'dashboard' ) : '';
		$logged_in     = is_user_logged_in();
		$account_label = $logged_in ? __( 'My account', 'linker-commerce' ) : __( 'Sign in', 'linker-commerce' );
		$count         = function_exists( 'WC' ) && null !== WC()->cart ? (int) WC()->cart->get_cart_contents_count() : 0;
		$shop          = function_exists( 'wc_get_page_permalink' ) ? (string) wc_get_page_permalink( 'shop' ) : home_url( '/' );
		$search_icon   = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>';
		$cart_icon     = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M6 6h15l-1.5 9h-12z"/><circle cx="9" cy="20" r="1.4"/><circle cx="18" cy="20" r="1.4"/><path stroke-linecap="round" stroke-linejoin="round" d="M6 6L5 3H2"/></svg>';
		$user_icon     = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" aria-hidden="true"><circle cx="12" cy="8" r="3.4"/><path stroke-linecap="round" d="M5.2 19.4a7 7 0 0 1 13.6 0"/></svg>';
		$html          = '<a href="' . esc_url( $shop . '#search-box' ) . '" class="tv-header-utility tv-header-search" data-tv-header-search aria-label="' . esc_attr__( 'Search products', 'linker-commerce' ) . '">' . $search_icon . '<span class="tv-header-utility-label">' . esc_html__( 'Search', 'linker-commerce' ) . '</span></a>';
		// The live header hides the badge at zero (its markup carries the
		// counter with an inline display:none; an empty cart shows no pill).
		$badge = $count > 0 ? '<span class="tv-b2b-acct-count">' . esc_html( (string) $count ) . '</span>' : '';
		$html .= '<a href="' . esc_url( $cart_url ) . '" class="tv-header-utility tv-header-cart-link" aria-label="' . esc_attr__( 'Solution draft', 'linker-commerce' ) . '">' . $cart_icon . '<span class="tv-header-utility-label">' . esc_html__( 'Solution draft', 'linker-commerce' ) . '</span>' . $badge . '</a>';
		if ( 'mobile' === $attributes['part'] ) {
			return '<a href="' . esc_url( $cart_url ) . '" class="tv-mobile-utility tv-header-cart-link" aria-label="' . esc_attr__( 'Solution draft', 'linker-commerce' ) . '">' . $cart_icon . '<span class="tv-header-utility-label">' . esc_html__( 'Solution draft', 'linker-commerce' ) . '</span>' . $badge . '</a><a href="' . esc_url( $account ) . '" class="tv-mobile-utility tv-b2b-mobile-portal-link" aria-label="' . esc_attr( $account_label ) . '">' . $user_icon . '<span class="tv-header-utility-label">' . esc_html( $account_label ) . '</span></a>';
		}
		$html .= '<div class="tv-b2b-acct"><button type="button" class="tv-b2b-acct-btn" aria-haspopup="true" aria-controls="linker-header-account-menu" aria-expanded="false" aria-label="' . esc_attr( $account_label ) . '"><span class="tv-b2b-acct-avatar">' . $user_icon . '</span><span class="tv-header-utility-label">' . esc_html( $account_label ) . '</span><span class="tv-b2b-acct-chev"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg></span></button>';
		$html .= '<div id="linker-header-account-menu" class="tv-b2b-acct-menu" hidden>';
		if ( $logged_in ) {
			// Account\\Menu filters Woo's one menu; every account surface reads it.
			foreach ( wc_get_account_menu_items() as $endpoint => $label ) {
				$html .= '<a class="tv-b2b-acct-link' . ( 'customer-logout' === $endpoint ? ' is-out' : '' ) . '" href="' . esc_url( wc_get_account_endpoint_url( $endpoint ) ) . '">' . esc_html( $label ) . '</a>';
			}
		} else {
			$html .= '<a class="tv-b2b-acct-link" href="' . esc_url( $account ) . '">' . esc_html__( 'Sign in', 'linker-commerce' ) . '</a>';
			$html .= '<a class="tv-b2b-acct-link" href="' . esc_url( $account ) . '">' . esc_html__( 'My account', 'linker-commerce' ) . '</a>';
		}
		$html .= '</div></div>';
		return $html . $this->language_toggle( 'lnk-lang-toggle--desktop' );
	}

	/**
	 * The language toggle, as the live header and footer carry it: a globe
	 * (hidden by the header's own stylesheet) beside the two halves, the
	 * current language marked.
	 *
	 * @param string $variant The toggle's variant class.
	 */
	private function language_toggle( string $variant ): string {
		$en_url = $this->language_url( 'en' );
		$de_url = $this->language_url( 'de' );
		$is_de  = \function_exists( 'pll_current_language' ) && 'de' === pll_current_language();
		$globe  = '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path fill="currentColor" d="M12 2a10 10 0 100 20 10 10 0 000-20zm6.9 6h-2.6a15.6 15.6 0 00-1.2-3.5A8 8 0 0118.9 8zM12 4c.7 1 1.3 2.4 1.7 4H10.3c.4-1.6 1-3 1.7-4zM4.3 14a8 8 0 010-4h3a19 19 0 000 4h-3zm.8 2h2.6c.3 1.3.7 2.5 1.2 3.5A8 8 0 015.1 16zm2.6-8H5.1a8 8 0 013.8-3.5A15.6 15.6 0 007.7 8zM12 20c-.7-1-1.3-2.4-1.7-4h3.4c-.4 1.6-1 3-1.7 4zm2.1-6H9.9a17 17 0 010-4h4.2a17 17 0 010 4zm.9 5.5c.5-1 .9-2.2 1.2-3.5h2.6a8 8 0 01-3.8 3.5zM16.7 14a19 19 0 000-4h3a8 8 0 010 4h-3z"/></svg>';
		$html   = '<span class="lnk-lang-toggle ' . esc_attr( $variant ) . '" role="group" aria-label="' . esc_attr__( 'Language', 'linker-commerce' ) . '">' . $globe;
		$html  .= '<a class="lnk-lang-half' . ( $is_de ? '' : ' is-active' ) . '" href="' . esc_url( $en_url ) . '" data-lnk-flang="en" hreflang="en" lang="en" data-linker-language-choice="en" title="English"' . ( $is_de ? '' : ' aria-current="true"' ) . '>EN</a>';
		$html  .= '<a class="lnk-lang-half' . ( $is_de ? ' is-active' : '' ) . '" href="' . esc_url( $de_url ) . '" data-lnk-flang="de" hreflang="de" lang="de" data-linker-language-choice="de" title="Deutsch"' . ( $is_de ? ' aria-current="true"' : '' ) . '>DE</a>';
		return $html . '</span>';
	}

	/**
	 * The current page in the given language.
	 *
	 * Polylang's switcher (`pll_the_languages()`, filtered by linker-i18n's
	 * UrlSegments on `pll_translation_url`) translates the queried page and
	 * the language segment, and stops there: a page permalink has no
	 * WooCommerce endpoint, no confirmation value and no query. The current
	 * language's half is the address the visitor is on. The other half is
	 * that translation's permalink with the request path past the queried
	 * object's permalink kept as-is, then the query keys the visitor set.
	 * Home is the fallback only when neither the queried object nor the
	 * switcher has an answer.
	 *
	 * @param string $lang Language code.
	 */
	private function language_url( string $lang ): string {
		$current = \function_exists( 'pll_current_language' ) ? pll_current_language() : '';
		if ( \is_string( $current ) && $current === $lang ) {
			return $this->requested_url();
		}
		return $this->with_request_context( $this->translated_switcher_url( $lang ), $lang );
	}

	/**
	 * Polylang's switcher URL for `$lang`, or the language home when the
	 * switcher has no answer.
	 *
	 * @param string $lang Language code.
	 */
	private function translated_switcher_url( string $lang ): string {
		if ( \function_exists( 'pll_the_languages' ) ) {
			$languages = pll_the_languages(
				array(
					'raw'           => 1,
					'hide_if_empty' => 0,
				)
			);
			if ( \is_array( $languages ) && isset( $languages[ $lang ]['url'] ) && \is_string( $languages[ $lang ]['url'] ) ) {
				return $languages[ $lang ]['url'];
			}
		}
		return 'de' === $lang && \function_exists( 'pll_home_url' ) ? (string) pll_home_url( 'de' ) : home_url( '/' );
	}

	/**
	 * The other language's page with the request's path past the queried
	 * object, and the query the visitor set, kept.
	 *
	 * The base is the queried object's permalink in `$lang` (account page,
	 * confirmation page, category, shop). The request path minus that
	 * object's permalink in the current language is the remainder — endpoint,
	 * value, nested endpoint, paging — and is appended unchanged. A request
	 * that is not that object, or has no translation, keeps the switcher's
	 * URL. The query is part of the request, not a second translation.
	 *
	 * @param string $url  The switcher's URL.
	 * @param string $lang Language code.
	 */
	private function with_request_context( string $url, string $lang ): string {
		$base = $this->translated_permalink( $lang );
		if ( '' !== $base ) {
			$remainder = $this->path_remainder();
			if ( '' !== $remainder ) {
				$url = $this->append_path( $base, $remainder );
			} else {
				$url = $base;
			}
		}
		// The request's own query, not the query vars WordPress rewrites:
		// a catalogue page sets orderby to its default even when the address
		// carried none. `key` is the order key the confirmation page needs —
		// without it Woo renders the thank-you page without order details.
		$kept = array();
		foreach ( array( 's', 'orderby', 'step', 'key' ) as $query_key ) {
			// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- the public address, not a submitted form.
			if ( ! isset( $_GET[ $query_key ] ) || ! \is_string( $_GET[ $query_key ] ) || '' === $_GET[ $query_key ] ) {
				continue;
			}
			$kept[ $query_key ] = sanitize_text_field( wp_unslash( $_GET[ $query_key ] ) ); // phpcs:ignore WordPress.Security.NonceVerification.Recommended -- same public address.
		}
		return (string) add_query_arg( $kept, remove_query_arg( array( 's', 'orderby', 'step', 'key', 'cbq' ), $url ) );
	}

	/**
	 * The address the visitor requested: the current language's half points
	 * at it rather than at a rebuilt permalink. The cache-bust key is not
	 * part of that address.
	 */
	private function requested_url(): string {
		$requested = \function_exists( 'pll_get_requested_url' ) ? pll_get_requested_url() : home_url( (string) wp_unslash( $_SERVER['REQUEST_URI'] ?? '/' ) ); // phpcs:ignore WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- the public address the visitor is on.
		return (string) remove_query_arg( 'cbq', $requested );
	}

	/**
	 * The queried object's permalink in `$lang`, via the same Polylang
	 * translation the other page links use (`pll_get_post` / `pll_get_term`
	 * + `get_permalink` / `get_term_link`). '' when there is no queried
	 * object, or its translation cannot be resolved — the caller then keeps
	 * the switcher's URL rather than inventing a second one.
	 *
	 * @param string $lang Language code.
	 */
	private function translated_permalink( string $lang ): string {
		if ( ! \function_exists( 'pll_get_post' ) && ! \function_exists( 'pll_get_term' ) ) {
			return '';
		}
		$queried = get_queried_object();
		if ( $queried instanceof \WP_Post ) {
			if ( ! \function_exists( 'pll_get_post' ) ) {
				return '';
			}
			$translated = (int) pll_get_post( (int) $queried->ID, $lang );
			if ( $translated <= 0 ) {
				return '';
			}
			$link = get_permalink( $translated );
			return \is_string( $link ) ? $link : '';
		}
		if ( $queried instanceof \WP_Term ) {
			if ( ! \function_exists( 'pll_get_term' ) ) {
				return '';
			}
			$translated = (int) pll_get_term( (int) $queried->term_id, $lang );
			if ( $translated <= 0 ) {
				return '';
			}
			$link = get_term_link( $translated );
			return \is_string( $link ) ? $link : '';
		}
		if ( \function_exists( 'is_shop' ) && is_shop() && \function_exists( 'wc_get_page_id' ) && \function_exists( 'pll_get_post' ) ) {
			$page_id = (int) wc_get_page_id( 'shop' );
			if ( $page_id <= 0 ) {
				return '';
			}
			$translated = (int) pll_get_post( $page_id, $lang );
			if ( $translated <= 0 ) {
				return '';
			}
			$link = get_permalink( $translated );
			return \is_string( $link ) ? $link : '';
		}
		if ( \function_exists( 'is_post_type_archive' ) && is_post_type_archive( 'product' ) ) {
			$link = get_post_type_archive_link( 'product' );
			return \is_string( $link ) ? $link : '';
		}
		return '';
	}

	/**
	 * The request path after the queried object's permalink, '' when the
	 * request is that permalink or does not start with it.
	 *
	 * Read from the path, not from the endpoint query var: WooCommerce maps
	 * `inquiries` onto `orders` and stores only the value, so the query var
	 * cannot rebuild `inquiries/2/` or `company/billing/`.
	 */
	private function path_remainder(): string {
		$base = $this->queried_permalink();
		if ( '' === $base ) {
			return '';
		}
		$request = trim( (string) wp_parse_url( (string) wp_unslash( $_SERVER['REQUEST_URI'] ?? '' ), PHP_URL_PATH ), '/' ); // phpcs:ignore WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- a path, compared against the queried permalink only.
		$prefix  = trim( (string) wp_parse_url( $base, PHP_URL_PATH ), '/' );
		if ( $request === $prefix ) {
			return '';
		}
		$needle = $prefix . '/';
		if ( '' === $prefix || ! str_starts_with( $request . '/', $needle ) ) {
			return '';
		}
		return substr( $request, strlen( $needle ) );
	}

	/**
	 * The queried object's permalink in the current language, the path
	 * prefix the remainder is measured against. '' when the request has no
	 * queried object whose permalink is a path prefix.
	 */
	private function queried_permalink(): string {
		$queried = get_queried_object();
		if ( $queried instanceof \WP_Post ) {
			$link = get_permalink( $queried );
			// A post argument is string; the no-argument form of get_permalink() is string|false.
			return \is_string( $link ) ? $link : ''; // @phpstan-ignore function.alreadyNarrowedType
		}
		if ( $queried instanceof \WP_Term ) {
			$link = get_term_link( $queried );
			return \is_string( $link ) ? $link : '';
		}
		if ( \function_exists( 'is_shop' ) && is_shop() && \function_exists( 'wc_get_page_permalink' ) ) {
			return (string) wc_get_page_permalink( 'shop' );
		}
		if ( \function_exists( 'is_post_type_archive' ) && is_post_type_archive( 'product' ) ) {
			$link = get_post_type_archive_link( 'product' );
			return \is_string( $link ) ? $link : '';
		}
			return '';
	}

	/**
	 * Appends the request's remaining path to a permalink, keeping that
	 * permalink's own query. The remainder is the request path past the
	 * queried object's permalink.
	 *
	 * @param string $permalink Permalink of the translated queried object.
	 * @param string $remainder Remaining path, without a leading slash.
	 */
	private function append_path( string $permalink, string $remainder ): string {
		$parts = wp_parse_url( $permalink );
		$path  = untrailingslashit( \is_array( $parts ) ? (string) ( $parts['path'] ?? '' ) : $permalink ) . '/' . $remainder;
		$path  = user_trailingslashit( $path );
		if ( ! \is_array( $parts ) ) {
			return $path;
		}
		$url = '';
		if ( isset( $parts['scheme'] ) ) {
			$url .= $parts['scheme'] . '://';
		}
		if ( isset( $parts['user'] ) ) {
			$url .= $parts['user'];
			if ( isset( $parts['pass'] ) ) {
				$url .= ':' . $parts['pass'];
			}
			$url .= '@';
		}
		if ( isset( $parts['host'] ) ) {
			$url .= $parts['host'];
		}
		if ( isset( $parts['port'] ) ) {
			$url .= ':' . $parts['port'];
		}
		$url .= $path;
		if ( isset( $parts['query'] ) && '' !== $parts['query'] ) {
			$url .= '?' . $parts['query'];
		}
		if ( isset( $parts['fragment'] ) && '' !== $parts['fragment'] ) {
			$url .= '#' . $parts['fragment'];
		}
		return $url;
	}

	/**
	 * The comparison page's address in the page's language, '' when the page
	 * does not exist.
	 */
	public static function compare_page_url(): string {
		$page = get_page_by_path( 'compare-products' );
		if ( ! $page instanceof \WP_Post ) {
			return '';
		}
		$id = (int) $page->ID;
		if ( \function_exists( 'pll_get_post' ) && \function_exists( 'pll_current_language' ) && 'de' === pll_current_language() ) {
			$twin = (int) pll_get_post( $id, 'de' );
			if ( $twin > 0 ) {
				$id = $twin;
			}
		}
		$link = get_permalink( $id );
		return \is_string( $link ) ? $link : '';
	}

	/**
	 * The solution configurator page's address in the page's language, ''
	 * when the page does not exist (the sidebar tool card links here).
	 */
	public static function configurator_page_url(): string {
		$page = get_page_by_path( 'linker-planner' );
		if ( ! $page instanceof \WP_Post ) {
			return '';
		}
		$id = (int) $page->ID;
		if ( \function_exists( 'pll_get_post' ) && \function_exists( 'pll_current_language' ) && 'de' === pll_current_language() ) {
			$twin = (int) pll_get_post( $id, 'de' );
			if ( $twin > 0 ) {
				$id = $twin;
			}
		}
		$link = get_permalink( $id );
		return \is_string( $link ) ? $link : '';
	}

	/**
	 * An attachment image URL, '' when the id holds none.
	 *
	 * @param int $image_id The attachment.
	 */
	private static function image_url( int $image_id ): string {
		$url = wp_get_attachment_image_url( $image_id, 'full' );
		return \is_string( $url ) ? $url : '';
	}

	/**
	 * An image tag with the live renderer's attribute set: class, src, srcset
	 * and sizes, no width/height (the stylesheet sizes the box).
	 *
	 * @param int                        $image_id   The attachment.
	 * @param string                     $size       Registered size name.
	 * @param array<string, string|null> $attributes Extra attributes; `srcset => null`
	 *                                               suppresses the generated candidates.
	 */
	private static function image_tag( int $image_id, string $size, array $attributes ): string {
		$src    = wp_get_attachment_image_src( $image_id, $size );
		$srcset = wp_get_attachment_image_srcset( $image_id, $size );
		$sizes  = wp_get_attachment_image_sizes( $image_id, $size );
		if ( ! \is_array( $src ) ) {
			return '';
		}
		// A caller that names `srcset` replaces the generated candidates;
		// `null` suppresses the attribute entirely. The live main picture
		// carries no srcset, so the browser takes the full-size file (measured
		// 2026-10-12 at 390: live currentSrc = the 1000px original, t16's
		// generated candidates had it pick the 600×450).
		if ( \array_key_exists( 'srcset', $attributes ) ) {
			$srcset = $attributes['srcset'];
			unset( $attributes['srcset'] );
		}
		// WordPress's canonical attribute order (width, height, src, then the
		// rest, srcset last): measured 2026-10-11, the browser picks a
		// different srcset candidate when sizes/src sit in another order, so
		// the markup keeps the order the live page carries.
		$html = '<img';
		if ( ! isset( $attributes['width'] ) && (int) $src[1] > 0 ) {
			$html .= ' width="' . (int) $src[1] . '" height="' . (int) $src[2] . '"';
		}
		$html .= ' src="' . esc_url( (string) $src[0] ) . '"';
		foreach ( $attributes as $name => $value ) {
			if ( null === $value ) {
				continue;
			}
			$html .= ' ' . $name . '="' . esc_attr( $value ) . '"';
		}
		// An explicit srcset (the thumbnails carry the live page's candidate)
		// replaces the generated one; null left none to print.
		if ( \is_string( $srcset ) && '' !== $srcset ) {
			$html .= ' srcset="' . esc_attr( $srcset ) . '"';
		}
		return $html . ' />';
	}

	/**
	 * One of the page's line icons as the design draws it: a 20px stroke icon
	 * from the page's own icon set. The name maps to the shape; the CSS sizes
	 * and colors it.
	 *
	 * @param string $name The icon name.
	 */
	public static function icon( string $name ): string {
		$paths = array(
			'check'    => '<path d="m5 12 4 4L19 6"/>',
			'chevron'  => '<path d="m6 9 6 6 6-6"/>',
			'compare'  => '<path d="M5 4v16M12 4v16M19 4v16M3 8h4M10 15h4M17 10h4"/>',
			'ask'      => '<path d="M21 15a4 4 0 0 1-4 4H8l-5 4V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z"/>',
			'file'     => '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8ZM14 2v6h6M8 13h8M8 17h6"/>',
			'download' => '<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
			'energy'   => '<rect x="3" y="6" width="17" height="12" rx="3"/><path d="M22 10v4M7 10v4m4-4v4m4-4v4"/>',
			'power'    => '<path d="m13 2-8 12h6l-1 8 9-12h-6z"/>',
			'grid'     => '<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/>',
			'gauge'    => '<path d="M4 18a9 9 0 1 1 16 0M12 12l5-5M5 18h14"/>',
		);
		$open  = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">';
		if ( 'energy' === $name || 'power' === $name || 'grid' === $name || 'gauge' === $name ) {
			// The purchase panel's figure icons carry no pixel size; the CSS
			// sizes them in the row.
			$open = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">';
		}
		return $open . ( $paths[ $name ] ?? '' ) . '</svg>';
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
