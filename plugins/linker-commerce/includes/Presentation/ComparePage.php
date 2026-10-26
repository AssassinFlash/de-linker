<?php
/**
 * The standalone comparison page and the chip that leads to it.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

use Linker\Commerce\Products\Comparison;
use Linker\Commerce\Abilities\ProductText;
use Linker\Commerce\Products\Publication;

/**
 * /compare-products/: the page a visitor builds a comparison on, and the
 * floating chip that shows the selection while they browse
 * (docs/specs/19-tool-pages.md).
 *
 * The page is a LiveCanvas dynamic template assigned to the page of that
 * slug (LiveCanvas's own "custom dynamic template" per-post choice), so its
 * composition is the template's; the shortcodes here only assemble data into
 * semantic markup and class names. The selection itself (which products, in
 * which order, at most four) lives in the tab's sessionStorage as IDs only,
 * and the page's address carries the same ordered list — opening the address
 * writes the server-normalized list back into the tab, which is what makes a
 * refresh, a bookmark and a shared link all work.
 */
final class ComparePage {

	/**
	 * English source slug; the German page is its native Polylang twin.
	 */
	public const PAGE_SLUG = 'compare-products';

	/**
	 * Session storage key of the tab's selection, ordered product IDs only.
	 */
	public const STORAGE_KEY = 'linkerCompareIds';

	/**
	 * What a table cell shows where the product data states nothing.
	 */
	private const EM_DASH = '—';

	/**
	 * The comparison assembly the table renders.
	 *
	 * @var Comparison
	 */
	private readonly Comparison $comparison;

	/**
	 * Sets up the page.
	 *
	 * @param Comparison|null $comparison Assembly override (tests).
	 */
	public function __construct( ?Comparison $comparison = null ) {
		$this->comparison = $comparison ?? new Comparison();
	}

	/**
	 * Adds the page's hooks.
	 */
	public function register(): void {
		add_shortcode( 'linker_compare_table', array( $this, 'table' ) );
		add_shortcode( 'linker_compare_chip', array( $this, 'chip_shortcode' ) );
		add_action( 'template_redirect', array( $this, 'canonical_address' ), 5 );
		add_action( 'wp_enqueue_scripts', array( $this, 'assets' ) );
		add_action( 'wp_footer', array( $this, 'standing_chip' ) );
	}

	/**
	 * The page's language, `en` or `de`: the language layer answers it for the
	 * request, the same way the product page's FAQ block asks it
	 * (docs/specs/9-i18n.md). Titles, links and the row labels follow it.
	 *
	 * @return 'en'|'de'
	 */
	private static function language(): string {
		return function_exists( 'pll_current_language' ) && 'de' === pll_current_language() ? 'de' : 'en';
	}

	/**
	 * The `ids` query value of this request, null when the request names none.
	 */
	private function requested_ids(): ?string {
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended, WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- a public, read-only page: the selection is the visitor's own address, and parse_ids() validates every token of it.
		return isset( $_GET['ids'] ) && is_string( $_GET['ids'] ) ? wp_unslash( $_GET['ids'] ) : null;
	}

	/**
	 * Whether the request marks its selection as shortened.
	 */
	private function requested_capped(): bool {
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- a public, read-only page; the flag only says the address held more IDs than a comparison shows.
		return isset( $_GET['capped'] ) && '1' === sanitize_text_field( wp_unslash( (string) $_GET['capped'] ) );
	}

	/**
	 * The ordered selection this request asks for, capped at the maximum.
	 *
	 * @return array{ids: list<int>, capped: bool}
	 */
	public function selection(): array {
		$parsed           = self::canonical_selection( (string) $this->requested_ids() );
		$parsed['capped'] = $parsed['capped'] || $this->requested_capped();

		return $parsed;
	}

	/**
	 * Native source identities for the products already rendered on this page.
	 *
	 * @param int[] $ids Rendered product IDs, including family members.
	 * @return array<int,int> Locale ID => source ID; no product facts or permissions.
	 */
	public static function identities( array $ids ): array {
		$map = array();
		foreach ( $ids as $id ) {
			$source = Publication::canonical_id( $id );
			if ( $source < 1 ) {
				continue;
			}
			$map[ $id ]     = $source;
			$map[ $source ] = $source;
			if ( function_exists( 'pll_get_post' ) ) {
				$twin = (int) pll_get_post( $source, 'de' );
				if ( $twin > 0 ) {
					$map[ $twin ] = $source;
				}
			}
		}

		return $map;
	}

	/**
	 * Deduplicate locale aliases before applying the shared four-product limit.
	 *
	 * @param string $raw Address or legacy selection.
	 * @return array{ids:list<int>,capped:bool}
	 */
	private static function canonical_selection( string $raw ): array {
		$ids  = array();
		$seen = array();
		foreach ( explode( ',', $raw ) as $token ) {
			$id = Comparison::parse_ids( $token )['ids'][0] ?? 0;
			if ( $id < 1 || isset( $seen[ $id ] ) ) {
				continue;
			}
			$seen[ $id ] = true;
			$source      = Publication::canonical_id( $id );
			if ( $source > 0 && ! in_array( $source, $ids, true ) ) {
				$ids[] = $source;
			}
			// One additional identity is enough to retain the existing capped warning.
			if ( count( $ids ) > Comparison::MAX_PRODUCTS ) {
				break;
			}
		}

		return Comparison::parse_ids( implode( ',', $ids ) );
	}

	/** The current comparison page, including a twin with its own slug. */
	private static function is_comparison_page(): bool {
		if ( is_page( self::PAGE_SLUG ) ) {
			return true;
		}
		$page = get_queried_object();
		if ( ! $page instanceof \WP_Post || 'page' !== $page->post_type || ! function_exists( 'pll_get_post' ) ) {
			return false;
		}
		$source_id = (int) pll_get_post( (int) $page->ID, 'en' );
		$source    = $source_id > 0 ? get_post( $source_id ) : null;

		return $source instanceof \WP_Post && self::PAGE_SLUG === $source->post_name;
	}

	/**
	 * Retain this page's selection through the shared header/footer switcher.
	 *
	 * @param array<string,mixed> $query Public, unslashed request query.
	 * @param string              $language Target language.
	 * @return array<string,string>
	 */
	public static function language_query( array $query, string $language ): array {
		if ( ! is_string( $query['ids'] ?? null ) || ! self::is_comparison_page() ) {
			return array();
		}
		$parsed = self::canonical_selection( $query['ids'] );
		$ids    = array();
		foreach ( $parsed['ids'] as $id ) {
			$translated = ProductText::translated_id( $id, ProductText::lang( $language ) );
			if ( $translated > 0 ) {
				$ids[] = $id;
			}
		}
		if ( array() === $ids ) {
			return array();
		}
		$kept = array( 'ids' => implode( ',', $ids ) );
		if ( $parsed['capped'] || '1' === ( $query['capped'] ?? null ) ) {
			$kept['capped'] = '1';
		}

		return $kept;
	}

	/**
	 * The comparison page keeps one address per selection: the `ids` in order,
	 * no duplicates, no more than a comparison holds. A visitor who pastes
	 * five IDs, or the same ID twice, is sent to the address of the
	 * comparison they asked for instead of being shown a table that does not
	 * match the address (the page stays refreshable and shareable).
	 */
	public function canonical_address(): void {
		if ( ! self::is_comparison_page() ) {
			return;
		}
		$parsed = $this->selection();
		$want   = implode( ',', $parsed['ids'] );
		$have   = $this->requested_ids();
		$ids_ok = '' === $want ? null === $have : $want === $have;
		if ( $ids_ok && ( ! $parsed['capped'] || $this->requested_capped() ) ) {
			return;
		}
		wp_safe_redirect( $this->page_url( $parsed['ids'], $parsed['capped'] ), 302 );
		exit;
	}

	/**
	 * The page's address with a selection in it: `?ids=1,2,3`, and `capped=1`
	 * when the address asked for more products than a comparison holds. The
	 * address is the request language's own page — the language layer swaps in
	 * the page's twin, the route ProductText::url takes for a product — so a
	 * German visitor's chip, canonical redirect and Remove links all stay on
	 * the German page.
	 *
	 * @param int[] $ids    Ordered product IDs.
	 * @param bool  $capped Whether to mark the selection as shortened.
	 */
	public function page_url( array $ids = array(), bool $capped = false ): string {
		$page = get_page_by_path( self::PAGE_SLUG );
		$id   = $page instanceof \WP_Post ? self::translated_page_id( (int) $page->ID ) : 0;
		$url  = 0 < $id ? (string) get_permalink( $id ) : PageUrls::page( self::PAGE_SLUG );
		$url  = trailingslashit( (string) preg_replace( '#\?.*$#', '', $url ) );
		$ids  = array_values( array_filter( array_map( 'intval', $ids ) ) );
		if ( array() === $ids ) {
			return $url;
		}
		$url .= '?ids=' . implode( ',', $ids );
		if ( $capped ) {
			$url .= '&capped=1';
		}

		return $url;
	}

	/**
	 * The page as the request's language has it: the language layer's twin of
	 * the page the slug resolved to — that page itself when it is already in
	 * the language, has no twin, or there is no language layer.
	 *
	 * @param int $page_id The page ID the slug resolved to.
	 */
	private static function translated_page_id( int $page_id ): int {
		if ( ! function_exists( 'pll_get_post' ) ) {
			return $page_id;
		}
		$translated = (int) pll_get_post( $page_id, self::language() );

		return 0 < $translated ? $translated : $page_id;
	}

	/**
	 * The table fragment: the columns and rows of the current selection, the
	 * em-dash cell for a fact the product data does not establish, and the
	 * empty state when nothing is selected. Every label it prints is the
	 * assembly's own (the same words Genie's comparison table uses); the
	 * words of the page around it belong to the template.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes, unused.
	 */
	public function table( $atts = array() ): string {
		unset( $atts );
		$parsed     = $this->selection();
		$comparison = array() === $parsed['ids'] ? array(
			'products' => array(),
			'rows'     => array(),
			'specs'    => array(),
		) : $this->comparison->of( $parsed['ids'], self::language() );
		$columns    = $comparison['products'];

		$html = '<div id="linker-compare" class="linker-compare" data-compare-identities="' . esc_attr( (string) wp_json_encode( self::identities( array_column( $columns, 'product_id' ) ) ) ) . '" data-compare-ids="' . esc_attr( implode( ',', array_column( $columns, 'product_id' ) ) ) . '">';
		if ( $parsed['capped'] ) {
			$html .= sprintf(
				'<p class="linker-compare-note mb-4 text-sm text-neutral-600" role="status">%s</p>',
				esc_html(
					sprintf(
						/* translators: %d: maximum number of products in a comparison. */
						__( 'Only the first %d products are shown.', 'linker-commerce' ),
						Comparison::MAX_PRODUCTS
					)
				)
			);
		}
		if ( array() === $columns ) {
			return $html . '<p class="linker-compare-empty text-neutral-600">' . esc_html__( 'Choose products to compare their specifications.', 'linker-commerce' ) . '</p></div>';
		}

		$html .= '<p class="linker-compare-actions mb-4 text-sm"><a class="text-(--proto-accent) underline" href="' . esc_url( $this->page_url() ) . '">' . esc_html__( 'Clear comparison', 'linker-commerce' ) . '</a></p>';
		$html .= '<p class="linker-compare-hint" data-compare-scroll-hint hidden>' . esc_html__( 'Scroll sideways to compare products.', 'linker-commerce' ) . '</p>';
		$html .= '<div class="linker-compare-scroll overflow-x-auto" role="region" tabindex="0" aria-label="' . esc_attr__( 'Product comparison table', 'linker-commerce' ) . '">';
		$html .= '<table class="linker-compare-table w-full border-collapse text-sm">';
		$html .= '<thead><tr><th scope="col" class="linker-compare-cell border-b border-neutral-200 p-3 text-left align-top font-semibold text-neutral-500">' . esc_html__( 'Products', 'linker-commerce' ) . '</th>';
		foreach ( $columns as $column ) {
			$html .= '<th scope="col" class="linker-compare-cell linker-compare-column border-b border-neutral-200 p-3 text-left align-top">';
			$html .= '<div class="flex flex-col gap-2">';
			if ( '' !== $column['image'] ) {
				$html .= '<img class="linker-compare-image h-24 w-24 object-contain" src="' . esc_url( $column['image'] ) . '" alt="' . esc_attr( $column['title'] ) . '" loading="lazy">';
			}
			$html .= '<a class="linker-compare-name font-semibold text-(--proto-accent) underline" href="' . esc_url( $column['url'] ) . '">' . esc_html( $column['title'] ) . '</a>';
			$html .= '<a class="linker-compare-remove text-sm text-neutral-500 underline" href="' . esc_url( $this->page_url( $this->without( $parsed['ids'], (int) $column['product_id'] ) ) ) . '">' . esc_html__( 'Remove', 'linker-commerce' ) . '</a>';
			$html .= '</div></th>';
		}
		$html .= '</tr></thead><tbody>';

		$html .= $this->row( __( 'Item number', 'linker-commerce' ), array_map( static fn( array $column ): string => $column['sku'], $columns ) );
		$html .= $this->row( __( 'Net price', 'linker-commerce' ), array_map( static fn( array $column ): string => $column['price_visible'] ? $column['price'] : AccountLinks::comparison_price( $column['price'] ), $columns ), true );
		$html .= $this->row( __( 'Availability', 'linker-commerce' ), array_map( static fn( array $column ): string => $column['availability'], $columns ) );
		foreach ( $comparison['rows'] as $dimension ) {
			$values = array_map(
				static fn( $value ): string => match ( $dimension['field'] ) {
					'application' => self::application( $value ),
					'device_class' => self::category( $value ),
					default => self::cell_value( $value ),
				},
				array_values( $dimension['values'] )
			);
			$html  .= $this->row( $dimension['label'], $values );
		}
		foreach ( $comparison['specs'] as $spec ) {
			$html .= $this->row( $spec['label'], array_map( array( self::class, 'cell_value' ), array_values( $spec['values'] ) ) );
		}

		return $html . '</tbody></table></div></div>';
	}

	/**
	 * The chip as a shortcode, for a template that mounts it itself.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes, unused.
	 */
	public function chip_shortcode( $atts = array() ): string {
		unset( $atts );

		return $this->chip();
	}

	/**
	 * The chip on the pages a selection is built on — the catalogue and the
	 * product pages — the way the Genie dock stands on every page: printed on
	 * wp_footer, hidden until the tab's selection is not empty. The chip's
	 * words and classes are this element's; its visibility, count and address
	 * are the browser's (assets/compare-selection.js).
	 */
	public function standing_chip(): void {
		if ( is_admin() || ! $this->is_selection_surface() ) {
			return;
		}
		echo $this->chip(); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- chip() escapes every value it prints.
	}

	/**
	 * Where a selection is built: the product archive and its category pages,
	 * and the single product. The same surfaces the catalogue card and the
	 * product page's compare button live on.
	 */
	private function is_selection_surface(): bool {
		if ( function_exists( 'is_product' ) && is_product() ) {
			return true;
		}

		return function_exists( 'is_shop' ) && ( is_shop() || is_product_taxonomy() );
	}

	/**
	 * The selection-state script: on the pages that carry the chip, and on the
	 * comparison page itself (which writes the tab's selection back from its
	 * own address).
	 */
	public function assets(): void {
		$page = self::is_comparison_page();
		if ( ! $page && ! $this->is_selection_surface() ) {
			return;
		}
		$path = dirname( __DIR__, 2 ) . '/assets/compare-selection.js';
		wp_enqueue_script(
			'linker-commerce-compare',
			plugins_url( 'assets/compare-selection.js', dirname( __DIR__, 2 ) . '/linker-commerce.php' ),
			array(),
			(string) filemtime( $path ),
			array( 'in_footer' => true )
		);
	}

	/**
	 * The chip element. Hidden until the tab has a selection (the browser
	 * reveals it), because the server cannot know the tab's sessionStorage;
	 * it carries the page address, the maximum and its own count in markup,
	 * so the script needs no configuration of its own.
	 */
	private function chip(): string {
		return sprintf(
			'<a id="compare-chip" class="linker-compare-chip fixed bottom-24 left-5 z-40 inline-flex items-center gap-2 rounded-full bg-[#15352f] px-4 py-3 font-medium text-white shadow-lg" data-compare-chip data-compare-page="%1$s" data-compare-max="%2$d" hidden href="%1$s"><span class="linker-compare-chip-label">%3$s</span> <span class="linker-compare-chip-count" data-compare-count>0/%2$d</span></a>',
			esc_url( $this->page_url() ),
			Comparison::MAX_PRODUCTS,
			esc_html__( 'Compare', 'linker-commerce' )
		);
	}

	/**
	 * One table row: a row header and one cell per product, an em dash where
	 * the product's data does not state the value.
	 *
	 * @param string   $label   Row label.
	 * @param string[] $values  One value per column, in column order.
	 * @param bool     $trusted Whether the values are already safe markup (a formatted price).
	 */
	private function row( string $label, array $values, bool $trusted = false ): string {
		$html = '<tr class="linker-compare-row"><th scope="row" class="linker-compare-cell border-b border-neutral-200 p-3 text-left align-top font-semibold text-neutral-500">' . esc_html( $label ) . '</th>';
		foreach ( $values as $value ) {
			$cell  = trim( $value );
			$html .= '<td class="linker-compare-cell border-b border-neutral-200 p-3 align-top">' . ( $trusted && '' !== $cell ? wp_kses_post( $cell ) : esc_html( '' === $cell ? self::EM_DASH : $cell ) ) . '</td>';
		}

		return $html . '</tr>';
	}

	/**
	 * The comparison selection without one product: what a Remove link leads to.
	 *
	 * @param int[] $ids       Ordered product IDs.
	 * @param int   $remove_id The product to leave out.
	 * @return list<int>
	 */
	private function without( array $ids, int $remove_id ): array {
		return array_values( array_filter( $ids, static fn( int $id ): bool => $id !== $remove_id ) );
	}

	/**
	 * An application fact as the page words it: the same two words the
	 * catalogue card and the product page print for it (#7's value is
	 * `home`/`commercial`, the product data's own word).
	 *
	 * @param mixed $value Fact value.
	 */
	private static function application( $value ): string {
		return match ( $value ) {
			'home'       => __( 'Home', 'linker-commerce' ),
			'commercial' => __( 'Commercial', 'linker-commerce' ),
			default      => self::cell_value( $value ),
		};
	}

	/**
	 * Use the maintained WooCommerce category name and its native translation.
	 *
	 * @param mixed $value Device-class slug.
	 */
	private static function category( $value ): string {
		if ( ! is_string( $value ) || '' === $value || 'unknown' === $value ) {
			return self::EM_DASH;
		}
		$terms = get_terms(
			array(
				'taxonomy'   => 'product_cat',
				'slug'       => $value,
				'lang'       => 'en',
				'hide_empty' => false,
				'number'     => 1,
			)
		);
		$term  = is_array( $terms ) ? reset( $terms ) : null;
		if ( ! $term instanceof \WP_Term ) {
			return self::EM_DASH;
		}
		if ( function_exists( 'pll_get_term' ) ) {
			$id         = (int) pll_get_term( (int) $term->term_id, self::language() );
			$translated = $id > 0 ? get_term( $id, 'product_cat' ) : null;
			if ( $translated instanceof \WP_Term ) {
				$term = $translated;
			}
		}

		return (string) $term->name;
	}

	/**
	 * The print of a cell value: the fact's own value, an em dash for unknown.
	 *
	 * @param mixed $value A fact value or a technical-table cell.
	 */
	private static function cell_value( $value ): string {
		if ( is_bool( $value ) ) {
			return $value ? 'yes' : 'no';
		}
		if ( is_array( $value ) ) {
			$range = array_map( 'strval', $value );
			return implode( ' – ', $range );
		}
		$text = is_scalar( $value ) ? trim( (string) $value ) : '';

		return '' === $text || 'unknown' === $text ? self::EM_DASH : $text;
	}
}
