<?php
/**
 * The addresses the site answered with a 301 before this one.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools;

use WP_Post;
use WP_Term;

/**
 * Sends the addresses the site retired — the tool entries this site itself
 * retired (#12), and the addresses the site before it retired
 * (data/legacy-redirects.json, extracted 2026-10-11: 255 product slugs, 31
 * category slugs, 18 retired page paths, the retired /checkout/ slug) — to
 * what answers them today.
 *
 * The maps are data, not code: the JSON file holds them, this class only
 * dispatches. Product and category requests are read from WordPress's own
 * routing (the `product` and `product_cat` query vars), so the German
 * product addresses carry the same slug as the English ones. Page paths are
 * matched with the language prefix folded away, and a redirect into the
 * German site asks Polylang for the German twin's own address.
 *
 * What the maps do not decide, WordPress and WooCommerce do:
 *
 * - A published product on a mapped slug wins: a withdrawn product that comes
 *   back is served again without touching the file. Only a slug no published
 *   product holds redirects.
 * - A retired category only redirects while its term is gone, or — a retired
 *   term kept with nothing on it — while it holds no published product
 *   (children included), so a shelf that fills again is served again.
 * - A `/shop/` or `/product-category/<slug>/` target resolves to the route
 *   that answers it now: the shop page's permalink, or the term's own
 *   permalink, which is what keeps a flat child shelf target at one hop.
 */
final class Redirects {

	/**
	 * The mapping tables, beside this plugin's other shipped data.
	 */
	public const DATA_FILE = 'data/legacy-redirects.json';

	/**
	 * This site's own retired tool entries: request paths, exact match.
	 */
	private const RETIRED_TOOLS = 'retired_tools';

	/**
	 * Adds the plugin's hooks. Priority 1: ahead of WordPress's canonical
	 * redirects, so a retired address answers the map's target rather than a
	 * guess of WordPress's.
	 */
	public function register(): void {
		add_action(
			'template_redirect',
			function (): void {
				$target = $this->target( $this->request_path() );
				if ( null !== $target ) {
					// phpcs:ignore WordPress.Security.SafeRedirect.wp_redirect_wp_redirect -- the target is built from this site's own home_url(), never visitor input.
					wp_redirect( $target, 301 );
					exit;
				}
			},
			1
		);
	}

	/**
	 * The request path, with one trailing slash, as the site addresses pages.
	 *
	 * @return string The path, '/' when the request names none.
	 */
	public function request_path(): string {
		// phpcs:ignore WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- wp_parse_url() takes the path verbatim; the value only feeds the map lookups.
		$uri = isset( $_SERVER['REQUEST_URI'] ) ? wp_unslash( $_SERVER['REQUEST_URI'] ) : '/';
		$raw = (string) wp_parse_url( $uri, PHP_URL_PATH );
		return trailingslashit( '' === $raw ? '/' : $raw );
	}

	/**
	 * Where a request path goes: the absolute URL of the target, or null when
	 * the path is not retired (and the request stays with WordPress).
	 *
	 * @param string $path The request path, with its trailing slash.
	 */
	public function target( string $path ): ?string {
		$maps = self::maps();
		if ( null === $maps ) {
			return null;
		}

		$path = trailingslashit( $path );
		if ( isset( $maps[ self::RETIRED_TOOLS ][ $path ] ) ) {
			return home_url( $maps[ self::RETIRED_TOOLS ][ $path ] );
		}

		$language = $this->request_language();
		$path     = $this->without_language( $path );

		$checkout = $this->checkout_target( $path, $maps['checkout'] );
		if ( null !== $checkout ) {
			return $this->url( $checkout, $language );
		}

		if ( isset( $maps['pages'][ $path ] ) ) {
			return $this->url( $this->resolve( $maps['pages'][ $path ] ), $language );
		}

		$category = $this->category_target( $maps['categories'], $language );
		if ( null !== $category ) {
			return $this->url( $this->resolve( $category ), $language );
		}

		$product = $this->product_target( $maps['products'] );
		if ( null !== $product ) {
			return $this->url( $this->resolve( $product ), $language );
		}

		return null;
	}

	/**
	 * Where the retired checkout slug goes: the checkout page's own address,
	 * with the rest of the path and the query string it was requested with
	 * (WooCommerce's received page and its order links live under it).
	 *
	 * The rule answers the slug the checkout page *used* to have: while the
	 * checkout page answers that address itself (a site where it was never
	 * renamed), the address is the page and nothing redirects.
	 *
	 * @param string                                     $path     The request path, its language prefix folded away.
	 * @param array{slugs: list<string>, target: string} $checkout The map's checkout rule.
	 */
	private function checkout_target( string $path, array $checkout ): ?string {
		$segments = $this->segments( $path );
		if ( array() === $segments || ! in_array( $segments[0], $checkout['slugs'], true ) ) {
			return null;
		}
		if ( $path === $this->checkout_path() ) {
			return null;
		}
		$rest = array() === array_slice( $segments, 1 ) ? '' : implode( '/', array_slice( $segments, 1 ) ) . '/';
		// phpcs:ignore WordPress.Security.ValidatedSanitizedInput.InputNotSanitized, WordPress.Security.ValidatedSanitizedInput.MissingUnslash -- the query string is carried through to the target verbatim, as the request addressed it.
		$query = isset( $_SERVER['QUERY_STRING'] ) ? wp_unslash( $_SERVER['QUERY_STRING'] ) : '';

		return $checkout['target'] . $rest . ( '' === $query ? '' : '?' . $query );
	}

	/**
	 * The target of a category the map retires, or null. The map's keys are
	 * the slugs the site files those shelves under, in either language (a
	 * German address carries the same slug as its English twin: AGENTS.md §4).
	 *
	 * A category is retired while its term is gone, or while it holds no
	 * published product. A slug that is a live shelf again is not retired,
	 * whatever the map still says. The last path segment names the shelf, so
	 * a nested address matches too.
	 *
	 * @param array<string, string> $map      The category map.
	 * @param string|null           $language Language of the request.
	 */
	private function category_target( array $map, ?string $language ): ?string {
		$requested = (string) get_query_var( 'product_cat' );
		$segments  = $this->segments( $requested );
		if ( array() === $segments ) {
			return null;
		}
		foreach ( array_unique( array( (string) end( $segments ), $segments[0] ) ) as $slug ) {
			if ( ! isset( $map[ $slug ] ) ) {
				continue;
			}
			$term = $this->term( $slug, $language );
			if ( null === $term || $this->shelf_is_empty( $term ) ) {
				return $map[ $slug ];
			}
		}

		return null;
	}

	/**
	 * The target of a product the map retires, or null. Only a slug no
	 * published product holds redirects; a withdrawn product that comes back
	 * is served again.
	 *
	 * @param array<string, string> $map The product map.
	 */
	private function product_target( array $map ): ?string {
		$slug = $this->requested_product();
		if ( '' === $slug || ! isset( $map[ $slug ] ) || $this->is_published_product( $slug ) ) {
			return null;
		}

		return $map[ $slug ];
	}

	/**
	 * The product slug a request names: WordPress's parsed request holds it
	 * as the `product` query var, or — WordPress resolves a slug that names
	 * an existing product, in any status and language, to the post — as the
	 * `name` of a product request.
	 */
	private function requested_product(): string {
		$type = get_query_var( 'post_type' );
		$name = get_query_var( 'name' );
		if ( 'product' === $type && is_string( $name ) && '' !== $name ) {
			return $name;
		}
		$product = get_query_var( 'product' );

		return is_string( $product ) ? $product : '';
	}

	/**
	 * The product category term with a slug in a language, null when there is
	 * none. Polylang's `lang` argument narrows the lookup while Polylang runs
	 * (the same scoping the site's own term reads use).
	 *
	 * @param string      $slug     Term slug.
	 * @param string|null $language Language slug, null for any.
	 */
	private function term( string $slug, ?string $language ): ?WP_Term {
		$args = array(
			'taxonomy'   => 'product_cat',
			'slug'       => $slug,
			'hide_empty' => false,
			'number'     => 1,
		);
		if ( null !== $language && function_exists( 'pll_languages_list' ) ) {
			$args['lang'] = $language;
		}
		$terms = get_terms( $args );
		if ( ! is_array( $terms ) || array() === $terms ) {
			return null;
		}

		return reset( $terms );
	}

	/**
	 * Whether a shelf holds no published product, its children included —
	 * WooCommerce's own question about a product category.
	 *
	 * @param WP_Term $term The shelf.
	 */
	private function shelf_is_empty( WP_Term $term ): bool {
		return array() === $this->published_products(
			array(
				// phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_tax_query -- a shelf is what the map's category entries ask about; the query asks for one product id.
				'tax_query' => array(
					array(
						'taxonomy'         => 'product_cat',
						'field'            => 'term_id',
						'terms'            => array( $term->term_id ),
						'include_children' => true,
					),
				),
			)
		);
	}

	/**
	 * Whether a published product holds a slug, in any language.
	 *
	 * @param string $slug Product slug.
	 */
	private function is_published_product( string $slug ): bool {
		return array() !== $this->published_products( array( 'name' => $slug ) );
	}

	/**
	 * One published product id matching a query, e.g. a shelf or a slug.
	 *
	 * @param array<string, mixed> $query Query beyond the product type and status.
	 * @return list<int>
	 */
	private function published_products( array $query ): array {
		$found = get_posts(
			$query + array(
				'post_type'      => 'product',
				'post_status'    => 'publish',
				'posts_per_page' => 1,
				'fields'         => 'ids',
				'lang'           => '',
			)
		);
		$ids   = array();
		foreach ( $found as $post ) {
			$ids[] = $post instanceof WP_Post ? $post->ID : (int) $post;
		}

		return $ids;
	}

	/**
	 * Where a map target answers now, as a path: the shop page's own
	 * permalink, the term's own permalink for a category target (its query
	 * string, e.g. a filter, rides along), and anything else as the map wrote
	 * it.
	 *
	 * @param string $target Target, '/shop/', '/product-category/<slug>/[?filter]' or a path.
	 */
	private function resolve( string $target ): string {
		if ( '/shop/' === $target ) {
			return $this->shop_path();
		}
		[ $path, $query ] = array_pad( explode( '?', $target, 2 ), 2, '' );
		if ( ! $this->is_category_path( $path ) ) {
			return $target;
		}
		$segments = $this->segments( $path );
		$term     = array() === $segments ? null : $this->term( (string) end( $segments ), $this->default_language() );
		$link     = null === $term ? false : get_term_link( $term );
		if ( ! is_string( $link ) ) {
			return $target;
		}
		$resolved = (string) wp_parse_url( $link, PHP_URL_PATH );
		if ( '' === $resolved ) {
			return $target;
		}

		return trailingslashit( $resolved ) . ( '' === $query ? '' : '?' . $query );
	}

	/**
	 * Whether a path addresses a product category, by the site's own category
	 * base (WooCommerce's permalink structure).
	 *
	 * @param string $path Root-relative path.
	 */
	private function is_category_path( string $path ): bool {
		$base = $this->permalink_slug( 'category_rewrite_slug' );
		return '' !== $base && str_starts_with( $path, '/' . $base . '/' );
	}

	/**
	 * One of WooCommerce's permalink bases, without surrounding slashes; ''
	 * while WooCommerce does not answer.
	 *
	 * @param string $key Key of wc_get_permalink_structure().
	 */
	private function permalink_slug( string $key ): string {
		if ( ! function_exists( 'wc_get_permalink_structure' ) ) {
			return '';
		}
		$structure = wc_get_permalink_structure();
		$value     = $structure[ $key ] ?? '';

		return is_string( $value ) ? trim( $value, '/' ) : '';
	}

	/**
	 * The absolute URL of a target in the language of the request: the
	 * target as it stands in the default language, the twin's own address in
	 * another language. The twin is Polylang's answer — the same one the i18n
	 * plugin's link localizer gives stored German — and a target without one
	 * falls back to the default-language address rather than a 404.
	 *
	 * @param string      $target   Root-relative target, query string included.
	 * @param string|null $language Language of the request.
	 */
	private function url( string $target, ?string $language ): string {
		$default = $this->default_language();
		if ( null === $language || null === $default || $language === $default ) {
			return home_url( $target );
		}
		[ $path, $query ] = array_pad( explode( '?', $target, 2 ), 2, '' );
		$url              = $this->localized_url( $path, $language ) ?? home_url( $path );

		return '' === $query ? $url : $url . '?' . $query;
	}

	/**
	 * The address of an English path in another language: its page, product,
	 * category or shop twin's own permalink; null when there is none.
	 *
	 * @param string $path     English path.
	 * @param string $language Language to localize into.
	 */
	private function localized_url( string $path, string $language ): ?string {
		if ( ! function_exists( 'pll_get_post' ) ) {
			return null;
		}
		$id = url_to_postid( home_url( $path ) );
		if ( $id > 0 ) {
			$twin = pll_get_post( $id, $language );
			$link = is_int( $twin ) ? get_permalink( $twin ) : false;

			return is_string( $link ) ? $link : null;
		}
		if ( ! $this->is_category_path( $path ) || ! function_exists( 'pll_get_term' ) ) {
			return null;
		}
		$segments = $this->segments( $path );
		$term     = array() === $segments ? null : $this->term( (string) end( $segments ), $this->default_language() );
		if ( null === $term ) {
			return null;
		}
		$twin = pll_get_term( $term->term_id, $language );
		$link = is_int( $twin ) ? get_term_link( $twin, 'product_cat' ) : false;

		return is_string( $link ) ? $link : null;
	}

	/**
	 * The path of the checkout page (WooCommerce's own answer), '' when
	 * WooCommerce does not answer.
	 */
	private function checkout_path(): string {
		if ( ! function_exists( 'wc_get_checkout_url' ) ) {
			return '';
		}
		$path = (string) wp_parse_url( wc_get_checkout_url(), PHP_URL_PATH );

		return '' === $path ? '' : trailingslashit( $path );
	}

	/**
	 * The path of the shop page (WooCommerce's own answer), '/' when there is
	 * none.
	 */
	private function shop_path(): string {
		$path = '';
		if ( function_exists( 'wc_get_page_permalink' ) ) {
			$path = (string) wp_parse_url( wc_get_page_permalink( 'shop' ), PHP_URL_PATH );
		}
		if ( '' === $path ) {
			$shop = (int) get_option( 'woocommerce_shop_page_id' );
			$uri  = $shop > 0 ? get_page_uri( $shop ) : '';
			$path = is_string( $uri ) && '' !== $uri ? '/' . trim( $uri, '/' ) . '/' : '';
		}

		return '' === $path ? '/' : trailingslashit( $path );
	}

	/**
	 * A path without a leading language segment: /de/... and /en/... address
	 * the same path as /..., which is how the map's English page keys match a
	 * German request.
	 *
	 * @param string $path The request path.
	 */
	private function without_language( string $path ): string {
		$segments = $this->segments( $path );
		if ( array() === $segments || ! function_exists( 'pll_languages_list' ) ) {
			return $path;
		}
		$languages = pll_languages_list();
		if ( ! is_array( $languages ) || ! in_array( $segments[0], $languages, true ) ) {
			return $path;
		}
		array_shift( $segments );

		return array() === $segments ? '/' : '/' . implode( '/', $segments ) . '/';
	}

	/**
	 * The non-empty segments of a path.
	 *
	 * @param string $path Path.
	 * @return list<string>
	 */
	private function segments( string $path ): array {
		return array_values( array_filter( explode( '/', trim( $path, '/' ) ), static fn( string $segment ): bool => '' !== $segment ) );
	}

	/**
	 * The language of the request (Polylang's answer), null while Polylang
	 * does not.
	 */
	private function request_language(): ?string {
		if ( ! function_exists( 'pll_current_language' ) ) {
			return null;
		}
		$language = pll_current_language();

		return is_string( $language ) && '' !== $language ? $language : null;
	}

	/**
	 * The language objects are written in (Polylang's default), null while
	 * Polylang does not.
	 */
	private function default_language(): ?string {
		if ( ! function_exists( 'pll_default_language' ) ) {
			return null;
		}
		$language = pll_default_language();

		return is_string( $language ) && '' !== $language ? $language : null;
	}

	/**
	 * The mapping tables, read once per request: null when the data file is
	 * unreadable or malformed, which fails as "no redirects", never as half a
	 * file.
	 *
	 * @return array{products: array<string, string>, categories: array<string, string>, pages: array<string, string>, retired_tools: array<string, string>, checkout: array{slugs: list<string>, target: string}}|null
	 */
	public static function maps(): ?array {
		static $maps = null;
		static $read = false;
		if ( ! $read ) {
			$read = true;
			$maps = self::maps_from( dirname( __DIR__ ) . '/' . self::DATA_FILE );
		}

		return $maps;
	}

	/**
	 * The tables of one data file: null when anything in it is missing or not
	 * a string map. The shipping file is one instance of this.
	 *
	 * @param string $file Absolute path.
	 * @return array{products: array<string, string>, categories: array<string, string>, pages: array<string, string>, retired_tools: array<string, string>, checkout: array{slugs: list<string>, target: string}}|null
	 */
	public static function maps_from( string $file ): ?array {
		// phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- a data file of this plugin.
		$bytes = is_readable( $file ) ? file_get_contents( $file ) : false;
		if ( false === $bytes ) {
			return null;
		}
		$decoded = json_decode( $bytes, true );
		if ( ! is_array( $decoded ) ) {
			return null;
		}

		$products   = self::string_map( $decoded['products'] ?? null );
		$categories = self::string_map( $decoded['categories'] ?? null );
		$pages      = self::string_map( $decoded['pages'] ?? null );
		$tools      = self::string_map( $decoded[ self::RETIRED_TOOLS ] ?? null );
		$checkout   = self::checkout( $decoded['checkout'] ?? null );
		if ( null === $products || null === $categories || null === $pages || null === $tools || null === $checkout ) {
			return null;
		}

		return array(
			'products'          => $products,
			'categories'        => $categories,
			'pages'             => $pages,
			self::RETIRED_TOOLS => $tools,
			'checkout'          => $checkout,
		);
	}

	/**
	 * A JSON object of strings, or null when it holds anything else.
	 *
	 * @param mixed $value Decoded value.
	 * @return array<string, string>|null
	 */
	private static function string_map( mixed $value ): ?array {
		if ( ! is_array( $value ) ) {
			return null;
		}
		$map = array();
		foreach ( $value as $key => $entry ) {
			if ( ! is_string( $key ) || ! is_string( $entry ) ) {
				return null;
			}
			$map[ $key ] = $entry;
		}

		return $map;
	}

	/**
	 * The checkout rule: the retired slugs and the page that answers them,
	 * null when the entry is missing or malformed.
	 *
	 * @param mixed $value Decoded value.
	 * @return array{slugs: list<string>, target: string}|null
	 */
	private static function checkout( mixed $value ): ?array {
		if ( ! is_array( $value ) || ! is_array( $value['slugs'] ?? null ) || ! is_string( $value['target'] ?? null ) ) {
			return null;
		}
		$slugs = array();
		foreach ( $value['slugs'] as $slug ) {
			if ( ! is_string( $slug ) ) {
				return null;
			}
			$slugs[] = $slug;
		}

		return array(
			'slugs'  => $slugs,
			'target' => $value['target'],
		);
	}
}
