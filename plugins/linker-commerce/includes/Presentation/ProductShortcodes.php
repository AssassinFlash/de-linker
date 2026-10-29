<?php
/**
 * The replica catalogue and product-page shortcodes: the dynamic blocks of the
 * design the site serves today, for the LiveCanvas templates to place.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

use Linker\Commerce\Products\DocumentLibrary;
use Linker\Commerce\Products\Materials;
use Linker\Commerce\Products\EngineeringReference;
use Linker\Commerce\Products\Publication;
use Linker\Commerce\Products\SelectionFacts;
use Linker\Commerce\Settings\Options;
use Linker\Commerce\Storefront\ProductFilters;
use Linker\Commerce\Storefront\ProductView;
use WC_Product;
use WP_Term;

/**
 * The catalogue head, the filter rail, the product card and the product-page
 * blocks carry the data; the LiveCanvas templates carry the page's static
 * structure and words. The markup answers the live page the templates
 * replicate (#16, owner ruling 2026-10-11): the same block order, the same
 * anchor classes (`linker-products`, `sf-card`, `pdp-*`).
 */
final class ProductShortcodes {

	/**
	 * Product families one catalogue page shows (the live shop's 24).
	 */
	public const PER_PAGE_FAMILIES = 24;

	/**
	 * One request-local grouping and page for grid, result line and navigation.
	 *
	 * @var FamilyPage|null
	 */
	private ?FamilyPage $family_page = null;

	/**
	 * One product-page presentation assembly; never used by business actions.
	 * Native publication and role are read afresh before every shortcode release.
	 *
	 * @var array<int,array<string,mixed>>
	 */
	private array $product_views = array();

	/**
	 * The rows the rail's Category section prints inside a group's expansion
	 * although the term is not one of that group's children, keyed by the
	 * group's English slug.
	 *
	 * The live rail expands Commercial Storage with three rows — Inverters,
	 * All-in-One Systems, Battery Systems — on the category itself and on
	 * every page of its branch (the captures of the live pages of
	 * 2026-10-13, `cat-aio-en-1440-live.png` and `cat-aio-de-1440-live.png`:
	 * Inverters / All-in-One Systems / Battery Systems under Commercial
	 * Storage, German Wechselrichter / All-in-One-Systeme / Batteriesysteme
	 * under Gewerbespeicher; the same three on the live Commercial Storage
	 * page, `cat-cstorage-en-1440-live.png`). Two of the three are the
	 * group's children in the data this build carries; Inverters is not —
	 * its term is flat at the top level, and /product-category/inverters/ is
	 * the address the products and the retired shelf slugs are served to, so
	 * the term tree stays as it is and the row is built here, in the
	 * navigation's own markup, as a second link to that term: the English
	 * one on the English page, the term's German twin (Wechselrichter) on
	 * the German one, the anchoring the crumb's name reads too.
	 *
	 * @var array<string, list<string>>
	 */
	private const RAIL_GROUP_ROWS = array( 'commercial-storage' => array( 'inverters' ) );

	/**
	 * Sets up the shortcodes.
	 *
	 * @param ProductFilters $filters The catalogue's facet data.
	 * @param ProductView    $views   The product's replica fields.
	 */
	public function __construct(
		private readonly ProductFilters $filters,
		private readonly ProductView $views
	) {}

	/**
	 * Registers the shortcodes.
	 */
	public function register(): void {
		( new FamilyNavigation( $this->family_page( ... ), $this->archive_base_url( ... ) ) )->register();
		add_shortcode( 'linker_products_head', array( $this, 'products_head' ) );
		add_shortcode( 'linker_products_filters', array( $this, 'products_filters' ) );
		add_shortcode( 'linker_products_sort', array( $this, 'products_sort' ) );
		add_shortcode( 'linker_products_empty', array( $this, 'products_empty' ) );
		add_shortcode( 'linker_products_card', array( $this, 'products_card' ) );
		add_shortcode( 'linker_products_families', array( $this, 'products_families' ) );
		add_shortcode( 'linker_products_actions', array( $this, 'products_actions' ) );
		add_shortcode( 'linker_products_chips', array( $this, 'products_chips' ) );
		add_shortcode( 'linker_header_utilities', array( $this, 'header_utilities' ) );
		add_shortcode( 'linker_language_switch', array( $this, 'language_switch' ) );
		add_shortcode( 'linker_products_family_count', array( $this, 'products_family_count' ) );
		add_shortcode( 'linker_products_family_pagination', array( $this, 'products_family_pagination' ) );
		add_shortcode( 'linker_products_contact', array( $this, 'products_contact' ) );
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
		add_shortcode( 'linker_pdp_configurator', array( $this, 'pdp_configurator' ) );
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
		add_shortcode( 'linker_pdp_faq_side', array( $this, 'pdp_faq_side' ) );
		add_shortcode( 'linker_pdp_features', array( $this, 'pdp_features' ) );
	}

	/**
	 * The catalogue head: breadcrumb row, title and intro, the search box,
	 * the tool entries and the category scope pills. On the shop page the
	 * title says Products; on a category archive it is the category's name.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function products_head( $atts = array() ): string {
		unset( $atts );
		$queried  = get_queried_object();
		$is_term  = $queried instanceof WP_Term;
		$shop_url = (string) wc_get_page_permalink( 'shop' );
		$action   = $is_term ? $this->term_link( $queried ) : $shop_url;
		$q        = (string) ( $this->filters->requested()['q'] ?? '' );

		$html = '<div class="wb-head">';
		// The page's own crumb: "HOME / PRODUCTS" on the shop (the second
		// entry bold, not a link), "HOME / PRODUCTS / COMMERCIAL STORAGE /
		// ALL-IN-ONE SYSTEMS" on a nested category (every ancestor of the
		// term linked, the term itself bold), all words uppercase as the
		// live page printed them (measured 2026-10-12; the recheck of
		// 2026-10-14 found the parent segment missing on the deployed tree).
		// Since the 2026-10-17 ruling every German page is German-only: the
		// home link follows the request's language (the shared PageUrls door
		// #263 added) and the category names are the queried terms' own
		// (German) names, not their English twins. The last live German
		// archive read "STARTSEITE / PRODUKTE / INVERTERS" above its own
		// "Wechselrichter" heading; that copy is the defect, not the
		// reference.
		$html .= '<div class="wb-metarow container"><span class="wbm-l"><a href="' . esc_url( PageUrls::home() ) . '">' . esc_html( self::upper( _x( 'Home', 'breadcrumb', 'linker-commerce' ) ) ) . '</a> / ';
		if ( $is_term ) {
			$html .= '<a href="' . esc_url( $shop_url ) . '">' . esc_html( self::upper( __( 'Products', 'linker-commerce' ) ) ) . '</a>';
			foreach ( $this->term_ancestors( $queried ) as $ancestor ) {
				$html .= ' / <a href="' . esc_url( $this->term_link( $ancestor ) ) . '">' . esc_html( self::upper( $this->category_crumb_name( $ancestor ) ) ) . '</a>';
			}
			$html .= ' / <b>' . esc_html( self::upper( $this->category_crumb_name( $queried ) ) ) . '</b>';
		} else {
			$html .= '<b>' . esc_html( self::upper( __( 'Products', 'linker-commerce' ) ) ) . '</b>';
		}
		$html .= '</span></div>';
		$html .= '<div class="wb-bar container">';
		$html .= '<div class="wb-copy"><h1 class="wb-title">' . esc_html( $is_term ? $queried->name : __( 'Products', 'linker-commerce' ) ) . '</h1>';
		// The live shop and archives both carry the generic subtitle; the
		// category's own description is not printed on the page.
		$html .= '<p class="wb-intro">' . esc_html__( 'Search products or filter by category and project requirements.', 'linker-commerce' ) . '</p></div>';
		$html .= '<form class="wb-search" method="get" action="' . esc_url( $action ) . '" role="search">';
		foreach ( $this->selection_parameters() as $key => $value ) {
			if ( 'q' !== $key ) {
				$html .= '<input type="hidden" name="' . esc_attr( (string) $key ) . '" value="' . esc_attr( (string) $value ) . '">';
			}
		}
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
	public function products_filters( $atts = array() ): string {
		unset( $atts );
		$queried    = get_queried_object();
		$is_term    = $queried instanceof WP_Term;
		$selected   = $this->filters->requested();
		$archive    = $this->filters->archive_product_ids();
		$facets     = $this->filters->facet_counts( $archive, $selected );
		$ranges     = $this->filters->range_folds( $archive );
		$applied    = $this->filters->applied_count( $is_term, $selected );
		$base_url   = $this->filters_reset_url();
		$has_facets = \count( \array_diff_key( $selected, array( 'q' => '' ) ) ) > 0;

		$html  = '<button type="button" class="product-filter-close" id="product-filter-close" aria-label="' . esc_attr__( 'Close filters', 'linker-commerce' ) . '">&times;</button>';
		$html .= '<details class="rail-fold" open>';
		// The rail-fold's summary is the live rail's own element, hidden there
		// as here (`#linker-products .rail-summary { display: none; }` in
		// storefront.css, outside any media query): the live shop and archive
		// markup both print this summary and neither shows it, the visible
		// line reading just "Filters". It carries the rail's applied
		// arithmetic — one for the category the visitor is on, one per
		// selected facet — which is the same number the narrow viewports'
		// "Filters · n" badge prints (products_actions()). The count is not
		// visible on the desktop rail; its visible symptom there is the Reset
		// link below.
		$html .= '<summary class="rail-summary"><span>' . ( $has_facets || ! $is_term
			? esc_html__( 'Filters', 'linker-commerce' )
			: esc_html( sprintf( /* translators: %d: number of selected filters. */ __( 'Filters (%d)', 'linker-commerce' ), $applied ) ) )
			. '</span><span class="rail-summary-mark" aria-hidden="true"></span></summary>';
		$html .= '<div class="rail-body">';
		// The visible header, and the row the filtered rail shows its Reset on:
		// the live filtered shelves read "Filters … Reset" at the rail's left
		// edge with the applied chips on the same line in the grid column
		// (the 2026-10-14 shelf captures; the recheck's family-10 "no Reset"
		// finding). Without a facet there is no Reset to offer.
		$html .= '<div class="rail-head"><span class="rail-head-label">' . esc_html__( 'Filters', 'linker-commerce' ) . '</span>'
			. ( $has_facets ? '<a class="rail-reset" href="' . esc_url( $base_url ) . '">' . esc_html__( 'Reset', 'linker-commerce' ) . '</a>' : '' )
			. '</div>';

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
			// live rule `#linker-products .family-link[aria-current="page"]`
			// lifts it to 600; on a category page it stays plain (measured
			// 2026-10-12: live "All products" aria-current=page fw 600 on
			// /products/ and /de/produkte/, absent on the archives — t16 showed
			// 400 everywhere because the attribute was never printed).
			$html .= '<a class="family-link"' . ( $is_term ? '' : ' aria-current="page"' ) . ' href="' . esc_url( (string) wc_get_page_permalink( 'shop' ) ) . '"><span>' . esc_html__( 'All products', 'linker-commerce' ) . '</span></a>';
			// The branch's ancestor ids, read once for the whole section
			// (each row asks whether it is on the queried term's line).
			$branch_ids = $is_term
				? array_map( static fn( WP_Term $term ): int => (int) $term->term_id, $this->term_ancestors( $queried ) )
				: array();
			foreach ( $categories as $category ) {
				$html .= $this->category_nav_row( $category, $is_term ? $queried : null, $branch_ids );
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

		if ( $ranges['has_power'] >= 3 ) {
			$html .= $this->range_form( __( 'AC power', 'linker-commerce' ), 'kw', __( 'Minimum AC power in kilowatts', 'linker-commerce' ), __( 'Maximum AC power in kilowatts', 'linker-commerce' ), 'kW', $selected );
		}
		if ( $ranges['has_energy'] >= 3 ) {
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
		$html .= '<div class="product-filter-actions">';
		$html .= '<a href="' . esc_url( $base_url ) . '">' . esc_html__( 'Clear', 'linker-commerce' ) . '</a>';
		$html .= '<button type="button" id="product-filter-apply">' . esc_html__( 'Show products', 'linker-commerce' ) . '</button>';
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
		$html             = '<details class="filter-section fgroup" open>';
		$html            .= '<summary class="filter-title">' . esc_html( $title ) . '</summary>';
		$html            .= '<div class="filter-options"><form class="frange" method="get" action="' . esc_url( $this->archive_root_url() ) . '">';
		$selected['sort'] = $this->filters->requested_sort();
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
		return (string) add_query_arg( $facet, rawurlencode( $value ), $this->archive_base_url() );
	}

	/**
	 * The result strip's sort select: the catalogue's own orders, the request's
	 * other facets kept as hidden inputs.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function products_sort( $atts = array() ): string {
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
		$html     = '<form class="wbsort woocommerce-ordering" method="get" action="' . esc_url( $this->archive_root_url() ) . '">';
		foreach ( $selected as $key => $value ) {
			$html .= '<input type="hidden" name="' . esc_attr( (string) $key ) . '" value="' . esc_attr( (string) $value ) . '" />';
		}
		// Woo's already loaded ordering handler submits this native GET form on change.
		$html .= '<select class="select-dropdown orderby" id="sort-select" name="sort" aria-label="' . esc_attr__( 'Sort products', 'linker-commerce' ) . '">';
		foreach ( $labels as $value => $label ) {
			$html .= '<option value="' . esc_attr( $value ) . '"' . selected( $sort, $value, false ) . '>' . esc_html( $label ) . '</option>';
		}
		$html .= '</select></form>';
		return $html;
	}

	/**
	 * The empty answer names the active search and filters, only when the
	 * archive's query has no products. Reading the loop does not advance it.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function products_empty( $atts = array() ): string {
		unset( $atts );
		if ( have_posts() ) {
			return '';
		}
		$selected = $this->filters->requested();
		$search   = isset( $selected['q'] );
		$facets   = array() !== \array_diff_key( $selected, array( 'q' => '' ) );
		if ( $search && $facets ) {
			$message = esc_html__( 'No products match your search and selected filters. Try another search term or change a filter.', 'linker-commerce' );
		} elseif ( $search ) {
			$message = esc_html__( 'No products match your search. Try another search term.', 'linker-commerce' );
		} elseif ( $facets ) {
			$message = esc_html__( 'No products match the selected filters. Try changing or clearing a filter.', 'linker-commerce' );
		} else {
			$message = esc_html__( 'No products are listed here.', 'linker-commerce' );
		}
		return '<div class="wb-empty"><p class="tv-empty-state">' . $message . '</p></div>';
	}

	/**
	 * The mobile actions bar: the Filters button with the applied count, the
	 * two tool entries and the AI entry — the live page's own
	 * `catalog-mobile-actions` (measured 2026-10-12 on the live shop and
	 * archives; the 2026-10-14 recheck found the deployed bar down to the
	 * one chip). The count's arithmetic is the rail's
	 * (ProductFilters::applied_count): the live bar reads "Filters · 0" on
	 * the shop, "Filters · 1" on a category, one more per selected facet.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function products_actions( $atts = array() ): string {
		unset( $atts );
		$queried = get_queried_object();
		$is_term = $queried instanceof WP_Term;
		$applied = $this->filters->applied_count( $is_term, $this->filters->requested() );
		$html    = '<nav class="product-mobile-actions" aria-label="' . esc_attr__( 'Product actions', 'linker-commerce' ) . '">';
		$html   .= '<button type="button" id="product-filter-open" aria-controls="sidebar-filters" aria-expanded="false"><span>' . esc_html__( 'Filters', 'linker-commerce' ) . '</span> &middot; <span data-linker-applied-filter-count>' . esc_html( (string) $applied ) . '</span></button>';
		$html   .= do_shortcode( '[linker_genie_chips page_type="category"]' );
		return $html . '</nav>';
	}

	/**
	 * The results strip's applied-filter chips, the live page's own
	 * `.wbc` content: one pill per selected facet that removes it, and the
	 * "Clear all" link (measured 2026-10-12 on the live shop filtered by
	 * GoodWe: a "GoodWe ×" pill and "Clear all"; recheck 2026-10-14 found
	 * the deployed strip empty). The search term stays in the search box,
	 * not a chip.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function products_chips( $atts = array() ): string {
		unset( $atts );
		$selected = \array_diff_key( $this->filters->requested(), array( 'q' => '' ) );
		if ( array() === $selected ) {
			return '';
		}
		$labels     = $this->selection_labels();
		$html       = '';
		$range_keys = array(
			'kw'  => array( __( 'AC power', 'linker-commerce' ), __( 'kW', 'linker-commerce' ), 'kw_min', 'kw_max' ),
			'kwh' => array( __( 'Usable energy', 'linker-commerce' ), __( 'kWh', 'linker-commerce' ), 'kwh_min', 'kwh_max' ),
		);
		foreach ( array( 'application', 'brand', 'phase', 'power' ) as $facet ) {
			if ( ! isset( $selected[ $facet ] ) ) {
				continue;
			}
			$value = (string) $selected[ $facet ];
			$html .= '<a class="wbchip" href="' . esc_url( $this->facet_remove_url( $facet ) ) . '" rel="nofollow">' . esc_html( $labels[ $facet ][ $value ] ?? $value ) . ' <span aria-hidden="true">&times;</span></a>';
		}
		foreach ( $range_keys as $range ) {
			list( $title, $unit, $min_key, $max_key ) = $range;
			if ( ! isset( $selected[ $min_key ] ) && ! isset( $selected[ $max_key ] ) ) {
				continue;
			}
			$min   = isset( $selected[ $min_key ] ) ? self::trim_number( (float) $selected[ $min_key ] ) : '';
			$max   = isset( $selected[ $max_key ] ) ? self::trim_number( (float) $selected[ $max_key ] ) : '';
			$label = $title . ' ' . $min . '&ndash;' . $max . ' ' . $unit;
			$html .= '<a class="wbchip" href="' . esc_url( $this->facet_remove_url( $min_key, $max_key ) ) . '" rel="nofollow">' . wp_kses_post( $label ) . ' <span aria-hidden="true">&times;</span></a>';
		}
		$html .= '<a class="wbclear" href="' . esc_url( $this->filters_reset_url() ) . '" rel="nofollow">' . esc_html__( 'Clear all', 'linker-commerce' ) . '</a>';
		return $html;
	}

	/**
	 * The facet values' printed labels, for the chips: the rail's own words
	 * (the facet data owns them), plus the brands' term names.
	 *
	 * @return array<string, array<int|string, string>> Labels by facet and value. The phase values are
	 *                                                   PHP's numeric strings: '3' lives under the int key 3,
	 *                                                   and lookups by either spelling reach it.
	 */
	private function selection_labels(): array {
		$labels = $this->filters->value_labels();
		$brands = get_terms(
			array(
				'taxonomy'   => 'pa_brand',
				'hide_empty' => false,
			)
		);
		foreach ( \is_array( $brands ) ? $brands : array() as $brand ) {
			$labels['brand'][ $brand->slug ] = $brand->name;
		}
		return $labels;
	}

	/**
	 * A number without trailing zeros, for a range chip's bound.
	 *
	 * @param float $value The bound.
	 */
	private static function trim_number( float $value ): string {
		$printed = (string) round( $value, 2 );
		return str_contains( $printed, '.' ) ? rtrim( rtrim( $printed, '0' ), '.' ) : $printed;
	}

	/**
	 * Native archive root with one facet (or both range bounds) removed.
	 * Other validated selections and sort remain; a changed set starts on page one.
	 *
	 * @param string ...$facets The query parameters to drop.
	 */
	private function facet_remove_url( string ...$facets ): string {
		return (string) remove_query_arg( $facets, $this->archive_base_url() );
	}

	/**
	 * The current product's catalogue card (inside [lc_loop], or called by the
	 * family grid with a family context).
	 *
	 * With a `family` context (the catalogue's family view, spec: the live
	 * shop lists one card per family) the card carries the live page's family
	 * anatomy: `data-linker-family-card`, the family's article payload in a
	 * `data-linker-products` JSON script, the series label as the title and
	 * the model picker in place of the single-article model row.
	 *
	 * @param array<string, mixed>|string $atts Shortcode attributes (`family`).
	 */
	public function products_card( $atts = array() ): string {
		$parsed     = \is_array( $atts ) ? $atts : shortcode_parse_atts( (string) $atts );
		$family     = isset( $parsed['family'] ) && \is_array( $parsed['family'] ) ? $parsed['family'] : null;
		$product_id = (int) get_the_ID();
		$card       = $this->views->card_fields( $product_id );
		if ( array() === $card ) {
			return '';
		}
		$product = wc_get_product( $product_id );
		$facts   = SelectionFacts::for_product( $product_id );
		$series  = (string) ( $card['series'] ?? '' );
		$multi   = null !== $family && \count( (array) $family['ids'] ) > 1;
		$title   = $multi ? self::series_title( $series, (string) $card['brand'], (string) $card['title'] ) : (string) $card['title'];
		// The picker's anchor only when the card actually shows the series.
		$label = $multi && $title !== (string) $card['title'] ? $series : '';
		$gated = '' !== (string) ( $card['price']['url'] ?? '' );
		$data  = array(
			'data-product-id="' . esc_attr( (string) $product_id ) . '"',
			'data-can-order="' . ( $gated ? '0' : '1' ) . '"',
			'data-sku="' . esc_attr( $card['sku'] ) . '"',
			'data-brand="' . esc_attr( $card['brand_slug'] ) . '"',
			'data-phase="' . esc_attr( (string) $facts->phase ) . '"',
			'data-power="' . esc_attr( \is_float( $facts->ac_power_kw ) ? (string) $facts->ac_power_kw : '0' ) . '"',
			'data-application="' . esc_attr( (string) $facts->application ) . '"',
			'data-compare-identities="' . esc_attr( (string) wp_json_encode( ComparePage::identities( null === $family ? array( $product_id ) : (array) $family['ids'] ) ) ) . '"',
		);
		$url   = (string) get_permalink( $product_id );

		$html = '<article class="sf-card product-card" data-linker-family-card ' . implode( ' ', $data ) . '>';
		if ( null !== $family && \count( (array) $family['ids'] ) > 1 ) {
			$html .= '<script type="application/json" data-linker-products>' . wp_json_encode( $this->family_payload( (array) $family['ids'] ) ) . '</script>';
		}
		$html .= '<div class="sf-card-media card-media">';
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
		$html .= '<a class="sf-card-title" data-card-title data-card-series-title="' . esc_attr( $label ) . '" href="' . esc_url( $url ) . '">' . esc_html( $title ) . '</a>';
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
		} else {
			$model_terms = get_the_terms( $product_id, 'pa_model' );
			$model       = \is_array( $model_terms ) && array() !== $model_terms ? (string) reset( $model_terms )->name : '';
			if ( '' !== trim( $model ) ) {
				$html .= '<span class="card-product" data-linker-exact-product><small>' . esc_html__( 'Model', 'linker-commerce' ) . '</small><strong data-card-selection>' . esc_html( $model ) . '</strong></span>';
			}
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
		$html     .= '</div>';
		$html     .= '<p class="sf-card-availability" data-card-availability>' . esc_html( $card['availability'] ) . '</p>';
		$html     .= '<div class="sf-card-actions">';
		$html     .= '<a class="sf-card-view tv-woo-card-action tv-woo-card-action--primary" data-card-view href="' . esc_url( $url ) . '">' . esc_html__( 'View product', 'linker-commerce' ) . '</a>';
		$html     .= '<button type="button" class="card-compare-checkbox" data-compare-product="' . esc_attr( (string) Publication::canonical_id( $product_id ) ) . '" aria-pressed="false" aria-label="'
			. esc_attr( sprintf( /* translators: %s: product name. */ __( 'Compare: %s', 'linker-commerce' ), (string) $card['title'] ) ) . '">' . self::icon( 'compare' )
			. '<span data-compare-label>' . esc_html__( 'Compare', 'linker-commerce' ) . '</span><svg class="compare-selected-mark" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="m5 12 4 4 10-10"/></svg></button>';
			$html .= '<a class="sf-card-atc tv-woo-card-action tv-woo-card-action--secondary" data-card-atc href="#" hidden>' . esc_html__( 'Add to solution draft', 'linker-commerce' ) . '</a>';
		if ( '' !== $card['price']['url'] ) {
			$html .= '<a class="tv-woo-card-action tv-woo-card-action--secondary" data-card-gate href="' . esc_url( $card['price']['url'] ) . '">' . esc_html__( 'Log in for pricing', 'linker-commerce' ) . '</a>' . AccountLinks::create();
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
			return '<a class="pdp-price-login" href="' . esc_url( (string) $view['price']['url'] ) . '">' . esc_html( (string) $view['price']['html'] ) . '</a>' . AccountLinks::create();
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
			$html .= '<div><span class="pdp-app-stat-icon" data-pdp-fact="' . esc_attr( (string) $stat['key'] ) . '" aria-hidden="true"></span>'
				. '<dt>' . esc_html( (string) $stat['label'] ) . '</dt><dd>' . self::pdp_stat_value( (string) $stat['value'] ) . '</dd></div>';
		}
		return $html;
	}

	/**
	 * Preserve the source text while marking distinct semicolon-separated facts.
	 * A semicolon inside parentheses belongs to the same fact, not a new one.
	 *
	 * @param string $value The complete formatted fact from Materials.
	 */
	private static function pdp_stat_value( string $value ): string {
		$parts = array();
		$start = 0;
		$depth = 0;
		$size  = strlen( $value );
		for ( $i = 0; $i < $size; ++$i ) {
			if ( '(' === $value[ $i ] ) {
				++$depth;
			} elseif ( ')' === $value[ $i ] ) {
				if ( 0 === $depth ) {
					return esc_html( $value );
				}
				--$depth;
			} elseif ( ';' === $value[ $i ] && 0 === $depth ) {
				$parts[] = substr( $value, $start, $i - $start + 1 );
				$start   = $i + 1;
			}
		}
		if ( 0 !== $depth || array() === $parts ) {
			return esc_html( $value );
		}
		$parts[] = substr( $value, $start );
		foreach ( $parts as $part ) {
			if ( '' === trim( $part, " \t\n\r\0\x0B;" ) ) {
				return esc_html( $value );
			}
		}
		return implode( '', array_map( static fn( string $part ): string => '<span class="pdp-spec-option">' . esc_html( $part ) . '</span>', $parts ) );
	}

	/**
	 * The availability line: the state with its dot and the delivery
	 * sentence the freight policy derives. The dot's class follows the
	 * product's own stock state (`WC_Product::is_in_stock()` — on a stock-
	 * managed product WooCommerce derives the status from the quantity,
	 * AGENTS.md §2's 2026-10-11 ruling); the stylesheet's `is-wait` rule is
	 * the warn colour, the base dot the prototype's accent.
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
		$dot     = 'pdp-dot' . ( $product instanceof WC_Product && ! $product->is_in_stock() ? ' is-wait' : '' );
		$html    = '<p class="pdp-avail-label"><span class="' . esc_attr( $dot ) . '"></span>' . esc_html( (string) $view['availability'] ) . '</p>';
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
	 * The three product tools: compare, ask, and documents.
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
		$html  = '<button type="button" class="pdp-tool" data-compare-identities="' . esc_attr( (string) wp_json_encode( ComparePage::identities( array( $product_id ) ) ) ) . '" data-compare-product="' . Publication::canonical_id( $product_id ) . '" aria-pressed="false">' . self::icon( 'compare' )
			. '<span data-compare-label>' . esc_html__( 'Compare', 'linker-commerce' ) . '</span><svg class="compare-selected-mark" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="m5 12 4 4 10-10"/></svg></button>';
		$html .= '<button type="button" class="pdp-tool" data-pdp-ask data-ask-message="' . esc_attr( $ask_message ) . '">' . self::icon( 'ask' )
			. esc_html__( 'Ask Genie', 'linker-commerce' ) . '</button>';
		$html .= '<a class="pdp-tool" href="#downloads">' . self::icon( 'file' )
			. esc_html__( 'Documents', 'linker-commerce' ) . '</a>';
		// The floating comparison chip is not copied here: ComparePage prints
		// it from the footer on every surface that carries a selection
		// control (spec 19 §5, one implementation).
		return $html;
	}

	/**
	 * The project-check action into the same Solution Configurator.
	 * The LiveCanvas region owns placement; this only carries the canonical product.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_configurator( $atts = array() ): string {
		unset( $atts );
		$view = $this->current_view();
		if ( null === $view ) {
			return '';
		}
		$planner = self::configurator_page_url();
		if ( '' === $planner ) {
			return '';
		}
		$canonical = Publication::canonical_id( (int) $view['id'] );
		if ( $canonical < 1 ) {
			return '';
		}
		return '<a class="pdp-project-choice" href="' . esc_url(
			add_query_arg(
				array(
					'step'       => 'equipment',
					'product_id' => (string) $canonical,
				),
				$planner
			)
		) . '">' . esc_html__( 'Open the Solution Configurator', 'linker-commerce' ) . '</a>';
	}

	/**
	 * The project entry's ways into the Advisor: one button per planning
	 * stage, each with its own opening message.
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
			// This secondary image is hidden in the current gallery layout.
			// Defer its full file; the thumbnail remains available and selects
			// the full image when a visitor asks to see it.
			$html .= '<button type="button" class="pdp-gallery-secondary" data-pdp-image data-src="' . esc_url( self::image_url( $ids[1] ) ) . '" data-caption="" aria-label="' . esc_attr__( 'Product image 2', 'linker-commerce' ) . '">'
				. self::image_tag(
					$ids[1],
					'full',
					array(
						'alt'     => '',
						'loading' => 'lazy',
					)
				) . '</button>';
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
				// On phones the controls are dots and the thumbnail images are hidden.
				'loading'  => 'lazy',
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
	 * The FAQ block's side panel: the product's gallery photo the accepted
	 * prototype carries there (prototype/pdp-redesign: docs/design/2026-10-15-pdp-prototype/index.html,
	 * variant A — `.faq-side` next to the accordion). The image is the last
	 * one of the gallery the page renders — for the prototype's own reference
	 * product GW60K-STS-G10 that is `…-product-20261007-02.png`, the last id
	 * of `Materials::gallery_ids()`, so the panel repeats no picture from the
	 * gallery or the feature band above it. A product whose gallery holds no
	 * picture beyond the featured one gets no panel and the block stays one
	 * column.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_faq_side( $atts = array() ): string {
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
		return '<div class="pdp-faq-side">' . self::image_tag(
			(int) $ids[ \count( $ids ) - 1 ],
			'large',
			array(
				'alt'     => '',
				'loading' => 'lazy',
			)
		) . '</div>';
	}

	/**
	 * The description's feature sections: the feature cards that carry an
	 * image, as the live page's `.pdp-feature` blocks (media beside the title
	 * and body). The cards without an image render as disclosure rows. The
	 * copy's kicker is the product's series (`ProductView::fields()`'s
	 * `series`; the prototype's band carries one, `.band-copy .kicker`), left
	 * out where the product states no series.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function pdp_features( $atts = array() ): string {
		unset( $atts );
		$view = $this->current_view();
		if ( null === $view ) {
			return '';
		}
		$series = (string) ( $view['series'] ?? '' );
		$html   = '';
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
				. '</div><div class="pdp-feature-copy">'
				. ( '' !== $series ? '<p class="pdp-kicker">' . esc_html( $series ) . '</p>' : '' )
				. '<h3 class="pdp-section-title">' . esc_html( (string) $feature['title'] ) . '</h3>'
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
		/**
		 * Current permitted documents from the existing page assembly.
		 *
		 * @var list<array{title:string,url:string,type:string,role:string,language:string}> $docs
		 */
		$docs = $view['downloads'];
		if ( array() === $docs ) {
			return '<p class="tv-empty-state">' . esc_html__( 'No documents are available for this product.', 'linker-commerce' ) . '</p>';
		}
		$rank = array(
			'datasheet' => 0,
			'manual'    => 1,
			'warranty'  => 2,
		);
		usort(
			$docs,
			static fn( array $left, array $right ): int =>
				( $rank[ DocumentLibrary::type( $left['type'], $left['role'] ) ] ?? 3 )
				<=> ( $rank[ DocumentLibrary::type( $right['type'], $right['role'] ) ] ?? 3 )
		);
		$html = '';
		foreach ( $docs as $document ) {
			$kind     = DocumentLibrary::type( $document['type'], $document['role'] );
			$language = DocumentLibrary::language( $document['language'] );
			$language = 'MUL' === $language ? __( 'Multilingual', 'linker-commerce' ) : $language;
			$title    = trim( $document['title'] );
			$title    = Materials::document_title_display( '' !== $title ? $title : Materials::document_kind_label( $kind ) );
			$meta     = array_filter(
				array(
					Materials::document_kind_label( $kind ),
					'PDF',
					$language,
				),
				static fn( string $part ): bool => '' !== $part
			);
			$html    .= '<a class="pdp-doc" href="' . esc_url( (string) $document['url'] ) . '" target="_blank" rel="noopener">';
			$html    .= '<span class="pdp-doc-icon">' . self::icon( 'file' ) . '</span>';
			$html    .= '<span class="grow">' . esc_html( $title )
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
	 * The relationship's recorded evidence status; qualifications remain below the cards.
	 *
	 * @param array<string, mixed> $relationship The registry relationship.
	 * @param string               $locale       'de' or 'en'.
	 */
	private static function pairing_status( array $relationship, string $locale ): string {
		if ( 'one_way' === ( $relationship['status'] ?? '' ) ) {
			return __( 'Partially documented', 'linker-commerce' );
		}
		if ( 'listed' !== ( $relationship['status'] ?? '' ) ) {
			return __( 'Compatibility information unavailable', 'linker-commerce' );
		}
		$by = trim( Materials::localized_text( $relationship, 'listed_by', $locale ) );
		if ( '' === $by ) {
			return __( 'Compatibility documented', 'linker-commerce' );
		}
		return sprintf( /* translators: %s: manufacturer */ __( 'Documented by %s', 'linker-commerce' ), $by );
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
	 * (filtered_product_ids(): published, catalog-visible, the queried
	 * category and the selected facets), grouped by the family the data
	 * defines.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function products_families( $atts = array() ): string {
		unset( $atts );
		$page = $this->family_page();
		$html = '';
		foreach ( $page->rows as $row ) {
			$lead = get_post( (int) $row['lead'] );
			if ( ! $lead instanceof \WP_Post ) {
				continue;
			}
			// The card fragment reads the loop's post; set it to this family's
			// lead article for the call.
			$GLOBALS['post'] = $lead; // phpcs:ignore WordPress.WP.GlobalVariablesOverride.Prohibited -- the loop contract the card fragment reads.
			setup_postdata( $lead );
			$html .= $this->products_card( array( 'family' => $row ) );
			wp_reset_postdata();
		}
		return $html;
	}

	/**
	 * The result line of the family view: "1-24 / 65 product families".
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function products_family_count( $atts = array() ): string {
		unset( $atts );
		$state = $this->family_page();
		$total = $state->total;
		$from  = $state->from;
		$to    = $state->to;
		return '<b>' . esc_html( $from . '-' . $to ) . '</b> / ' . esc_html( sprintf( /* translators: %d: number of product families. */ _n( '%d product family', '%d product families', $total, 'linker-commerce' ), $total ) );
	}

	/**
	 * The family view's pagination: the live page's own `product-page`
	 * addresses, one per family page.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function products_family_pagination( $atts = array() ): string {
		unset( $atts );
		$state = $this->family_page();
		$pages = $state->last;
		if ( $pages < 2 ) {
			return '';
		}
		$page = $state->current;
		$base = $this->archive_base_url();
		$html = '<nav class="tv-woo-pagination" aria-label="' . esc_attr__( 'Product pagination', 'linker-commerce' ) . '">';
		// Page one uses the native root; later slices retain product-page.
		if ( $page > 1 ) {
			$html .= '<a class="prev page-numbers" href="' . esc_url( $page > 2 ? add_query_arg( 'product-page', $page - 1, $base ) : $base ) . '">' . esc_html__( 'Previous', 'linker-commerce' ) . '</a>';
		}
		for ( $i = 1; $i <= $pages; $i++ ) {
			$url   = $i > 1 ? add_query_arg( 'product-page', $i, $base ) : $base;
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
	 * `section.linker-contact-invitation.linker-contact-products`, the last
	 * block of the results column after the pagination. The words are the
	 * live page's (verbatim, EN and DE, read off its four catalogue pages
	 * 2026-10-12); the address carries this page as the request's context,
	 * the contact page of the page's language as its target, the team
	 * mailbox beneath (the live page's own shape).
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function products_contact( $atts = array() ): string {
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
		$contact           = array(
			'kind'    => 'catalogue',
			'title'   => $title,
			'url'     => $source,
			'search'  => $search,
			'filters' => $filters,
			'intent'  => 'product',
		);
		$selection         = $request;
		$selection['sort'] = $this->filters->requested_sort();
		$url               = (string) add_query_arg(
			array(
				'intent' => 'product',
				\Linker\Commerce\Contact\SelectionContext::FIELD => rawurlencode(
					(string) wp_json_encode(
						array(
							'source'    => $source,
							'selection' => $selection,
						)
					)
				),
			),
			Shortcodes::contact_page_url()
		);

		$html  = '<section class="linker-contact-invitation linker-contact-products">';
		$html .= '<div>';
		$html .= '<span class="linker-contact-eyebrow">' . esc_html__( 'CONTACT LINKER', 'linker-commerce' ) . '</span>';
		$html .= '<h2>' . esc_html__( 'Not sure which model to look for?', 'linker-commerce' ) . '</h2>';
		$html .= '<p>' . esc_html__( 'Your question includes this page as context. You can remove it before sending.', 'linker-commerce' ) . '</p>';
		$html .= '</div>';
		$html .= '<div class="linker-contact-invitation-actions">';
		$html .= '<a class="linker-contact-primary" href="' . esc_url( $url ) . '" data-linker-contact="' . esc_attr( (string) wp_json_encode( $contact ) ) . '">' . esc_html__( 'Need help choosing?', 'linker-commerce' ) . '</a>';
		$html .= '<a class="linker-contact-email" href="mailto:' . esc_attr( ( new Options() )->team_mailbox() ) . '">' . esc_html( ( new Options() )->team_mailbox() ) . '</a>';
		$html .= '</div>';
		return $html . '</section>';
	}

	/**
	 * The family card's title: the data's series label, as the live page
	 * prints it ("ESA Series", "GoodWe BAT-C") — unless the label is the
	 * brand's own name and says nothing the brand line above doesn't: the
	 * SAJ CHS2 records carry product_series "SAJ", and the live all-in-one
	 * page printed their full model names ("SAJ CHS2-50K-T6-X", measured
	 * 2026-10-12; recheck 2026-10-14 found the deployed card reading just
	 * "SAJ").
	 *
	 * @param string $series The product's series label.
	 * @param string $brand  The product's brand name.
	 * @param string $title  The product's own name.
	 */
	public static function series_title( string $series, string $brand, string $title ): string {
		if ( '' !== $series && 0 !== strcasecmp( $series, $brand ) ) {
			return $series;
		}
		return $title;
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
	 * The category's name in the request's language: the queried term's own
	 * name (the German term on a German archive), never the English twin's.
	 * Polylang hands the request the term of its language (owner ruling
	 * 2026-10-17: a German page is German-only; ticket #264 H5).
	 *
	 * @param WP_Term $term The queried category or one of its ancestors.
	 */
	private function category_crumb_name( WP_Term $term ): string {
		// Term names are stored HTML-encoded ("Energiezähler &amp; Stromwandler");
		// uppercasing the entity would print "&AMP;", so decode first and let
		// esc_html() encode the clean name once.
		return \html_entity_decode( $term->name, ENT_QUOTES | ENT_HTML5, 'UTF-8' );
	}

	/**
	 * A term's English side: the twin the language layer links in the site's
	 * canonical language, the term itself where none runs.
	 *
	 * @param WP_Term $term The term.
	 */
	private function english_term( WP_Term $term ): WP_Term {
		if ( \function_exists( 'pll_get_term' ) ) {
			$english = (int) pll_get_term( (int) $term->term_id, 'en' );
			if ( $english > 0 ) {
				$source = get_term( $english, 'product_cat' );
				if ( $source instanceof WP_Term ) {
					return $source;
				}
			}
		}
		return $term;
	}

	/**
	 * The address of the current catalogue view without its page number.
	 */
	private function archive_root_url(): string {
		$queried = get_queried_object();
		return $queried instanceof \WP_Term ? $this->term_link( $queried ) : (string) wc_get_page_permalink( 'shop' );
	}

	/** Native root with the request's validated selection and order. */
	private function archive_base_url(): string {
		return $this->archive_url( $this->selection_parameters() );
	}

	/** Reset the facets while keeping the search, sort and current archive. */
	private function filters_reset_url(): string {
		$kept = \array_intersect_key(
			$this->selection_parameters(),
			array(
				'q'    => '',
				'sort' => '',
			)
		);
		return $this->archive_url( $kept );
	}

	/**
	 * The current native archive with validated selection parameters.
	 *
	 * @param array<string, string|float> $parameters Selection to carry.
	 */
	private function archive_url( array $parameters ): string {
		$encoded = array_map( static fn( $value ): string => rawurlencode( (string) $value ), $parameters );
		return (string) add_query_arg( $encoded, $this->archive_root_url() );
	}

	/**
	 * Selection is shared by links and GET forms; a change starts at page one.
	 *
	 * @return array<string, string|float> Validated facets, search and sort.
	 */
	private function selection_parameters(): array {
		$selected = $this->filters->requested();
		$sort     = $this->filters->requested_sort();
		if ( 'recommended' !== $sort ) {
			$selected['sort'] = $sort;
		}
		return $selected;
	}

	/** One grouped family result, reused by every current request consumer. */
	private function family_page(): FamilyPage {
		if ( null === $this->family_page ) {
			// phpcs:ignore WordPress.Security.NonceVerification.Recommended, WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- FamilyPage validates the public page before arithmetic or output.
			$requested         = array_key_exists( 'product-page', $_GET ) ? wp_unslash( $_GET['product-page'] ) : get_query_var( 'paged', 1 );
			$this->family_page = new FamilyPage( $this->family_rows( array_values( $this->filters->filtered_product_ids() ) ), $requested, self::PER_PAGE_FAMILIES );
		}
		return $this->family_page;
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
		if ( 'name' === $this->filters->requested_sort() ) {
			// Sort complete families before pagination by the title the card prints.
			$titles = array();
			foreach ( $rows as $row ) {
				$product                = wc_get_product( $row['lead'] );
				$card                   = $product instanceof \WC_Product ? $this->views->card_titles( $product ) : array();
				$title                  = (string) ( $card['title'] ?? '' );
				$titles[ $row['lead'] ] = \count( $row['ids'] ) > 1
					? self::series_title( (string) ( $card['series'] ?? '' ), (string) ( $card['brand'] ?? '' ), $title )
					: $title;
			}
			usort( $rows, static fn( array $a, array $b ): int => strcasecmp( $titles[ $a['lead'] ], $titles[ $b['lead'] ] ) );
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
	 * — live's `.card-product` ("RS485 · GW60K-STS-G10",
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
	 * `data-linker-products` JSON carries, one row per member.
	 *
	 * @param array<int> $ids The family's article ids.
	 * @return array<int, array<string, mixed>>
	 */
	private function family_payload( array $ids ): array {
		$payload = array();
		foreach ( $ids as $id ) {
			$card = $this->views->card_fields( (int) $id );
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
				'compareId'    => Publication::canonical_id( (int) $id ),
				/* translators: %s: product name. */
				'compareLabel' => sprintf( __( 'Compare: %s', 'linker-commerce' ), (string) $card['title'] ),
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
	 * `details.sf-card-variants.card-product-picker` with one button per
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
		$html    = '<details class="sf-card-variants card-product-picker" data-picker-heading="' . esc_attr( $heading ) . '">';
		$html   .= '<summary><span class="card-selection-copy"><small>' . esc_html__( 'Selected model', 'linker-commerce' ) . '</small> <strong data-card-selection>' . esc_html( $selection ) . '</strong></span> <span class="card-selection-action">' . esc_html( $heading ) . '</span></summary>';
		$html   .= '<div class="card-product-picker__list" data-picker-heading="' . esc_attr( $heading ) . '">';
		foreach ( $ids as $id ) {
			$row   = $this->views->card_fields( (int) $id );
			$html .= '<button type="button" class="sf-card-variant" data-linker-select-product="' . esc_attr( (string) $id ) . '"' . ( (int) $id === $current_id ? ' aria-current="true"' : '' ) . '><span>' . esc_html( (string) ( $row['model'] ?? '' ) ) . '</span> <small>' . esc_html__( 'Item no.', 'linker-commerce' ) . ' ' . esc_html( (string) ( $row['sku'] ?? '' ) ) . '</small></button>';
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
		$shop          = function_exists( 'wc_get_page_permalink' ) ? (string) wc_get_page_permalink( 'shop' ) : PageUrls::home();
		$search_icon   = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>';
		$cart_icon     = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M6 6h15l-1.5 9h-12z"/><circle cx="9" cy="20" r="1.4"/><circle cx="18" cy="20" r="1.4"/><path stroke-linecap="round" stroke-linejoin="round" d="M6 6L5 3H2"/></svg>';
		$user_icon     = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" aria-hidden="true"><circle cx="12" cy="8" r="3.4"/><path stroke-linecap="round" d="M5.2 19.4a7 7 0 0 1 13.6 0"/></svg>';
		$html          = '<a href="' . esc_url( $shop . '#search-box' ) . '" class="tv-header-utility tv-header-search" data-tv-header-search aria-label="' . esc_attr__( 'Search products', 'linker-commerce' ) . '">' . $search_icon . '<span class="tv-header-utility-label">' . esc_html__( 'Search', 'linker-commerce' ) . '</span></a>';
		// The live header hides the badge at zero (its markup carries the
		// counter with an inline display:none; an empty cart shows no pill).
		$badge = $count > 0 ? '<span class="tv-b2b-acct-count">' . esc_html( (string) $count ) . '</span>' : '';
		$html .= '<a href="' . esc_url( $cart_url ) . '" class="tv-header-utility tv-header-cart-link" aria-label="' . esc_attr__( 'Solution draft', 'linker-commerce' ) . '">' . $cart_icon . '<span class="tv-header-utility-label">' . esc_html__( 'Solution draft', 'linker-commerce' ) . '</span>' . $badge . '</a>';
		if ( 'mobile' === $attributes['part'] ) {
			return '<a href="' . esc_url( $cart_url ) . '" class="tv-mobile-utility tv-header-cart-link" aria-label="' . esc_attr__( 'Solution draft', 'linker-commerce' ) . '">' . $cart_icon . '<span class="tv-header-utility-label">' . esc_html__( 'Solution draft', 'linker-commerce' ) . '</span>' . $badge . '</a><a href="' . esc_url( $account ) . '" class="tv-mobile-utility tv-b2b-mobile-portal-link" aria-label="' . esc_attr( $account_label ) . '">' . $user_icon . '<span class="tv-header-utility-label">' . esc_html( $account_label ) . '</span></a>' . AccountLinks::create();
		}
		$html .= '<div class="tv-b2b-acct"><button type="button" class="tv-b2b-acct-btn" aria-haspopup="true" aria-controls="linker-header-account-menu" aria-expanded="false" aria-label="' . esc_attr( $account_label ) . '"><span class="tv-b2b-acct-avatar">' . $user_icon . '</span><span class="tv-header-utility-label">' . esc_html( $account_label ) . '</span><span class="tv-b2b-acct-chev"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg></span></button>';
		$html .= '<div id="linker-header-account-menu" class="tv-b2b-acct-menu" hidden>';
		if ( $logged_in ) {
			// Account\\Menu filters Woo's one menu; every account surface reads it.
			// The sign-out entry is Woo's nonce-carrying URL (one click, ticket
			// #184); the plain endpoint URL would ask for confirmation first.
			foreach ( wc_get_account_menu_items() as $endpoint => $label ) {
				$url   = 'customer-logout' === $endpoint && function_exists( 'linker_commerce_logout_url' ) ? linker_commerce_logout_url() : esc_url_raw( wc_get_account_endpoint_url( $endpoint ) );
				$html .= '<a class="tv-b2b-acct-link' . ( 'customer-logout' === $endpoint ? ' is-out' : '' ) . '" href="' . esc_url( $url ) . '">' . esc_html( $label ) . '</a>';
			}
		} else {
			$html .= '<a class="tv-b2b-acct-link" href="' . esc_url( $account ) . '">' . esc_html__( 'Sign in', 'linker-commerce' ) . '</a>' . AccountLinks::create();
		}
		$html .= '</div></div>';
		return $html . $this->language_toggle( 'lnk-lang-toggle--desktop' );
	}

	/**
	 * The footer's language switcher, from the same implementation as the
	 * header's toggle (LanguageLinks, ticket #263).
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function language_switch( $atts = array() ): string {
		unset( $atts );
		return ( new LanguageLinks() )->footer();
	}

	/**
	 * The language toggle, as the live header carries it.
	 *
	 * @param string $variant The toggle's variant class.
	 */
	private function language_toggle( string $variant ): string {
		return ( new LanguageLinks() )->toggle( $variant );
	}

	/**
	 * The comparison page's address in the page's language, '' when the page
	 * does not exist.
	 */
	public static function compare_page_url(): string {
		return PageUrls::translated( 'compare-products' );
	}

	/**
	 * The solution configurator page's address in the page's language, ''
	 * when the page does not exist (the sidebar tool card links here).
	 */
	public static function configurator_page_url(): string {
		return PageUrls::translated( 'solution-configurator' );
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
		);
		$open  = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">';
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
	 * The category's ancestors, nearest parent first, as the crumb walks
	 * them: the term's parent chain up to the top level.
	 *
	 * @param WP_Term $term The category.
	 * @return list<WP_Term> The ancestors, top level last.
	 */
	private function term_ancestors( WP_Term $term ): array {
		$ancestors = array();
		$parent_id = (int) $term->parent;
		$guard     = 0;
		while ( $parent_id > 0 && $guard < 10 ) {
			$parent = get_term( $parent_id, 'product_cat' );
			// A refused id answers a WP_Error, which is no WP_Term.
			if ( ! $parent instanceof WP_Term ) {
				break;
			}
			$ancestors[] = $parent;
			$parent_id   = (int) $parent->parent;
			++$guard;
		}
		return array_reverse( $ancestors );
	}

	/**
	 * One row of the rail's Category section, with the reference rail's own
	 * nesting: on a category page the branch the visitor is in expands — the
	 * group's own rows first (RAIL_GROUP_ROWS), then the children the term
	 * tree holds, the children indented under the group.
	 *
	 * Rows and indentation are the reference captures of 2026-10-13: the
	 * all-in-one page prints Inverters / All-in-One Systems / Battery
	 * Systems under Commercial Storage, the accessories page Meters &
	 * Current Transformers / Backup Power under Accessories, each child
	 * indented (measured 2026-10-12; `cat-aio-en-1440-live.png`,
	 * `cat-aio-de-1440-live.png`, `cat-cstorage-en-1440-live.png`). The
	 * deployed tree carries no such nesting — the recheck of 2026-10-14
	 * found its rail a flat list there, the nested rows and the crumb's
	 * parent segment gone (docs/debt/ADJUDICATION-2026-10-14.md, the
	 * Category EN recheck row, still `reproduced`). This expansion restores
	 * the reference's composition, not the deployed tree's.
	 *
	 * @param WP_Term      $category   The top-level category of this row.
	 * @param WP_Term|null $current    The category on display, null on the shop.
	 * @param array<int>   $branch_ids The queried category's ancestor ids, its own line in the section.
	 */
	private function category_nav_row( WP_Term $category, ?WP_Term $current, array $branch_ids = array() ): string {
		$row = $this->category_nav_link( $category, null !== $current && $current->term_id === $category->term_id );
		// The branch expands for the category on display, for its children's
		// parent and for its ancestors (a deep child keeps its whole line
		// open); the caller reads the ancestor ids once for the section.
		$expand = null !== $current
			&& ( $current->term_id === $category->term_id || $current->parent === $category->term_id || \in_array( (int) $category->term_id, $branch_ids, true ) );
		if ( ! $expand ) {
			return $row;
		}
		$children = get_terms(
			array(
				'taxonomy'   => 'product_cat',
				'hide_empty' => true,
				'parent'     => (int) $category->term_id,
			)
		);
		if ( ! \is_array( $children ) ) {
			return $row;
		}
		foreach ( $this->group_rows( $category, $children ) as $own ) {
			$row .= $this->category_nav_link( $own, $current->term_id === $own->term_id, 'family-link--child' );
		}
		foreach ( $children as $child ) {
			$row .= $this->category_nav_link( $child, $current->term_id === $child->term_id, 'family-link--child' );
		}
		return $row;
	}

	/**
	 * The rows a group's expansion carries above the children the term tree
	 * holds, in the order the live rail prints them.
	 *
	 * The map is a display addition, so a term the tree has since made a
	 * child keeps its one row: a row the children already carry is left out.
	 *
	 * @param WP_Term             $group    The group whose expansion is being built.
	 * @param array<int, WP_Term> $children The children the expansion carries.
	 * @return list<WP_Term> The group's own rows; empty for every group but the one the map names.
	 */
	private function group_rows( WP_Term $group, array $children ): array {
		$slugs = self::RAIL_GROUP_ROWS[ $this->english_term( $group )->slug ] ?? array();
		if ( array() === $slugs ) {
			return array();
		}
		$taken = array_map( static fn( WP_Term $child ): int => (int) $child->term_id, $children );
		$rows  = array();
		foreach ( $slugs as $slug ) {
			$term = $this->localized_category( $slug );
			if ( ! $term instanceof WP_Term || \in_array( (int) $term->term_id, $taken, true ) ) {
				continue;
			}
			$rows[] = $term;
		}
		return $rows;
	}

	/**
	 * A product category by its English slug, as the language on display
	 * shows it; null when the catalogue holds no such term.
	 *
	 * The lookup is anchored on the canonical side where the site runs a
	 * language layer — its `lang` argument narrows it, the scoping the
	 * redirects' own term reads use — and the twin that answers is the one
	 * the page prints.
	 *
	 * @param string $slug The term's English slug.
	 */
	private function localized_category( string $slug ): ?WP_Term {
		$args = array(
			'taxonomy'   => 'product_cat',
			'slug'       => $slug,
			'hide_empty' => true,
			'number'     => 1,
		);
		if ( \function_exists( 'pll_languages_list' ) ) {
			$args['lang'] = 'en';
		}
		$terms = get_terms( $args );
		if ( ! \is_array( $terms ) || array() === $terms ) {
			return null;
		}
		// A non-empty term answer carries terms; the read matches the
		// redirects' own lookup.
		$term = reset( $terms );
		if ( \function_exists( 'pll_get_term' ) ) {
			$twin = (int) pll_get_term( (int) $term->term_id );
			if ( $twin > 0 ) {
				$localized = get_term( $twin, 'product_cat' );
				if ( $localized instanceof WP_Term ) {
					return $localized;
				}
			}
		}
		return $term;
	}

	/**
	 * One link of the Category section.
	 *
	 * @param WP_Term $term    The category.
	 * @param bool    $current Whether it is the category on display.
	 * @param string  $variant Extra class (the child rows indent).
	 */
	private function category_nav_link( WP_Term $term, bool $current, string $variant = '' ): string {
		return '<a class="family-link' . ( '' !== $variant ? ' ' . $variant : '' ) . ( $current ? ' is-current' : '' ) . '" href="' . esc_url( $this->term_link( $term ) ) . '"' . ( $current ? ' aria-current="page"' : '' ) . '><span>' . esc_html( $term->name ) . '</span></a>';
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
		$id = (int) $product->get_id();
		if ( ! Publication::is_published( $id ) || EngineeringReference::is_reference( $id ) ) {
			unset( $this->product_views[ $id ] );
			return null;
		}
		$this->product_views[ $id ] ??= $this->views->fields( $id );
		$view                         = $this->product_views[ $id ];
		return array() === $view ? null : $view;
	}
}
