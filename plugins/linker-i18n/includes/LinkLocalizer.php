<?php
/**
 * Links in content point at the same page in the language being rendered.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n;

use Linker\I18n\Translation\HtmlToken;
use Linker\I18n\Translation\HtmlTokenizer;
use WP_Post;
use WP_Term;

/**
 * Rewrites the site's links from one language to the other: when the German
 * is written (target German, the translation workflow), and at render time
 * for the request's own language, so a translation job that has not run yet
 * cannot leave a German page pointing at its English twin
 * (docs/research/2026-10-17-i18n-audit/AUDIT.md, H3/M2/S1/S2).
 *
 * The resolver reads the object behind the address — a page, post, product,
 * product category or blog category — through Polylang's translation pair,
 * and keeps the query and fragment untouched. Marked contact links also carry
 * their same-origin source page into the target language. External addresses,
 * other URL schemes and addresses with no translation stay as they are.
 */
final class LinkLocalizer {

	/**
	 * Answers already resolved in this request: target language and URL =>
	 * URL. Rendering one page asks for the same links more than once; the
	 * pairs cannot change within the request.
	 *
	 * @var array<string, string>
	 */
	private array $resolved = array();

	/**
	 * Sets up the localizer.
	 *
	 * @param Languages     $languages The site's languages.
	 * @param HtmlTokenizer $tokenizer The HTML tokenizer.
	 */
	public function __construct( private readonly Languages $languages, private readonly HtmlTokenizer $tokenizer ) {}

	/**
	 * The HTML with the href of every link to the other language's version of
	 * the same object replaced by the target language's URL.
	 *
	 * @param string $html     HTML.
	 * @param string $language Target language slug.
	 */
	public function localize( string $html, string $language = Languages::TARGET ): string {
		if ( ! str_contains( $html, 'href' ) ) {
			return $html;
		}
		$out = '';
		foreach ( $this->tokenizer->tokens( $html ) as $token ) {
			$href = HtmlToken::TAG === $token->type && 'a' === $token->name ? $token->attribute( 'href' ) : null;
			if ( null !== $href ) {
				$localized = null === $token->attribute( 'data-linker-contact' ) ? $this->url( $href, $language ) : $this->contact_url( $href, $language );
				if ( $localized !== $href ) {
					$out .= $token->with_attribute( 'href', $localized );
					continue;
				}
			}
			$out .= $token->raw;
		}
		return $out;
	}

	/**
	 * The URL of the same object in `$language`; unchanged when it is
	 * external, in another scheme, already in the target language, or has no
	 * translation there.
	 *
	 * @param string $url      URL, absolute or root-relative.
	 * @param string $language Target language slug.
	 */
	public function url( string $url, string $language = Languages::TARGET ): string {
		$key = $language . ' ' . $url;
		if ( ! array_key_exists( $key, $this->resolved ) ) {
			$this->resolved[ $key ] = $this->resolve( $url, $language );
		}
		return $this->resolved[ $key ];
	}

	/**
	 * Localize an explicitly marked contact handoff, including its source URL.
	 * Other query fields keep their original bytes; source metadata is not trusted.
	 *
	 * @param string $url      Contact URL.
	 * @param string $language Target language slug.
	 */
	private function contact_url( string $url, string $language ): string {
		if ( ! $this->same_origin( $url, true ) ) {
			return $url;
		}
		$localized = $this->url( $url, $language );
		$parts     = wp_parse_url( $localized );
		if ( ! is_array( $parts ) || ! isset( $parts['query'] ) ) {
			return $localized;
		}
		$fields = explode( '&', $parts['query'] );
		foreach ( $fields as &$field ) {
			$pair = explode( '=', $field, 2 );
			if ( 'source' !== urldecode( $pair[0] ) || ! isset( $pair[1] ) ) {
				continue;
			}
			$source = urldecode( $pair[1] );
			if ( $this->same_origin( $source ) ) {
				$target = $this->url( $source, $language );
				if ( $target !== $source ) {
					$field = $pair[0] . '=' . rawurlencode( $target );
				}
			}
		}
		unset( $field );
		$offset = strpos( $localized, '?' );
		return false === $offset ? $localized : substr_replace( $localized, implode( '&', $fields ), $offset + 1, strlen( $parts['query'] ) );
	}

	/**
	 * Contact sources use the same scheme, host and port, with no userinfo.
	 * A contact destination may also be root-relative, never protocol-relative.
	 *
	 * @param string $url           Proposed URL.
	 * @param bool   $root_relative Whether a root-relative destination is allowed.
	 */
	private function same_origin( string $url, bool $root_relative = false ): bool {
		$parts = wp_parse_url( $url );
		$home  = wp_parse_url( $this->languages->home_url( Languages::SOURCE ) );
		if ( ! is_array( $parts ) || ! is_array( $home ) || isset( $parts['user'] ) || isset( $parts['pass'] ) ) {
			return false;
		}
		if ( $root_relative && ! isset( $parts['scheme'] ) && ! isset( $parts['host'] ) ) {
			return str_starts_with( $url, '/' ) && ! str_starts_with( $url, '//' );
		}
		return in_array( $parts['scheme'] ?? '', array( 'http', 'https' ), true )
			&& ( $home['scheme'] ?? '' ) === $parts['scheme']
			&& strtolower( (string) ( $parts['host'] ?? '' ) ) === strtolower( (string) ( $home['host'] ?? '' ) )
			&& ( $parts['port'] ?? null ) === ( $home['port'] ?? null );
	}

	/**
	 * The URL of the same object in `$language`, uncached.
	 *
	 * @param string $url      URL, absolute or root-relative.
	 * @param string $language Target language slug.
	 */
	private function resolve( string $url, string $language ): string {
		$parts = wp_parse_url( $url );
		$home  = $this->languages->home_url( Languages::SOURCE );
		if ( ! is_array( $parts ) || ( isset( $parts['scheme'] ) && ! in_array( strtolower( $parts['scheme'] ), array( 'http', 'https' ), true ) ) ) {
			return $url;
		}
		$relative = ! isset( $parts['host'] );
		if ( $relative ? ! str_starts_with( $url, '/' ) || str_starts_with( $url, '//' ) : strtolower( $parts['host'] ) !== strtolower( (string) wp_parse_url( $home, PHP_URL_HOST ) ) ) {
			return $url;
		}
		$path       = $parts['path'] ?? '/';
		$translated = $this->translated( $path, $language );
		if ( null === $translated || $translated === $path ) {
			return $url;
		}
		if ( $relative ) {
			$translated = (string) wp_parse_url( $translated, PHP_URL_PATH );
		}
		return $translated . ( isset( $parts['query'] ) ? '?' . $parts['query'] : '' ) . ( isset( $parts['fragment'] ) ? '#' . $parts['fragment'] : '' );
	}

	/**
	 * The target language's URL for a path of a page, post, product, category
	 * or the home page; null when the path is already in the target language
	 * or has no translation there.
	 *
	 * @param string $path     Path.
	 * @param string $language Target language slug.
	 */
	private function translated( string $path, string $language ): ?string {
		$home         = untrailingslashit( (string) wp_parse_url( $this->languages->home_url( Languages::TARGET ), PHP_URL_PATH ) );
		$german       = '' !== $home && str_starts_with( trailingslashit( $path ), trailingslashit( $home ) );
		$unprefixed   = $german ? '/' . ltrim( substr( $path, strlen( $home ) ), '/' ) : $path;
		$url_language = $german ? Languages::TARGET : Languages::SOURCE;
		if ( '' === trim( $unprefixed, '/' ) ) {
			return $this->languages->home_url( $language );
		}

		$post_id = url_to_postid( home_url( $german ? $path : $unprefixed ) );
		if ( $post_id <= 0 && $german ) {
			// A German descriptive slug has no English rewrite; the English
			// path is the same path without /de/, and resolves the source.
			$post_id = url_to_postid( home_url( $unprefixed ) );
		}
		if ( $post_id <= 0 ) {
			// Polylang's frontend home_url filter can make url_to_postid miss
			// an English page while a German theme is rendering its content.
			$page = get_page_by_path( trim( $unprefixed, '/' ) );
			if ( $page instanceof WP_Post && 'page' === $page->post_type && 'publish' === $page->post_status && '' === $page->post_password ) {
				$canonical = get_permalink( $page->ID );
				if ( is_string( $canonical ) && untrailingslashit( $path ) === untrailingslashit( (string) wp_parse_url( $canonical, PHP_URL_PATH ) ) ) {
					$post_id = $page->ID;
				}
			}
		}
		if ( $post_id > 0 ) {
			if ( $this->languages->of_post( $post_id ) === $language ) {
				return null;
			}
			$source = $this->languages->source_post( $post_id );
			$twin   = null === $source ? null : $this->languages->post_translation( $source, $language );
			$link   = null === $twin ? false : get_permalink( $twin );
			return false === $link ? null : $link;
		}

		$segments = explode( '/', trim( $unprefixed, '/' ) );
		$slug     = (string) end( $segments );
		foreach ( $this->taxonomy_bases() as $taxonomy => $bases ) {
			if ( count( $segments ) > 1 && in_array( $segments[0], $bases, true ) ) {
				$url = $this->term_url( $taxonomy, $slug, $url_language, $language );
				return $url ?? $this->retired_category_url( $slug, $language );
			}
		}

		$shop = (int) get_option( 'woocommerce_shop_page_id' );
		if ( $shop > 0 && $this->is_page_path( $shop, $unprefixed, $url_language ) ) {
			if ( $url_language === $language ) {
				return null;
			}
			$twin = $this->languages->post_translation( $shop, $language );
			$link = null === $twin ? false : get_permalink( $twin );
			return false === $link ? null : $link;
		}
		return null;
	}

	/**
	 * The current language's address of a retired category's target. The
	 * live posts still link the previous site's shelves (blog posts point at
	 * /product-category/residential-storage/res-accessories/, whose term has
	 * no German twin); the retired-address map names the shelf that answers
	 * it now, and that shelf's twin is the German address (AUDIT.md M2).
	 *
	 * @param string $slug     Slug the retired address ended with.
	 * @param string $language Target language.
	 */
	private function retired_category_url( string $slug, string $language ): ?string {
		$target = self::retired_categories()[ $slug ] ?? null;
		if ( ! is_string( $target ) ) {
			return null;
		}
		$path = (string) wp_parse_url( $target, PHP_URL_PATH );
		if ( '' === trim( $path, '/' ) ) {
			return null;
		}
		return $this->translated( $path, $language );
	}

	/**
	 * The category half of the retired-address map: the previous site's
	 * shelf slug => the address that answers it now. Read from the one file
	 * that owns the map (linker-tools' data/legacy-redirects.json), so a
	 * retired address is never duplicated here.
	 *
	 * @return array<string, string>
	 */
	private static function retired_categories(): array {
		static $categories = null;
		if ( is_array( $categories ) ) {
			return $categories;
		}
		$categories = array();
		$file       = dirname( __DIR__, 3 ) . '/plugins/linker-tools/data/legacy-redirects.json';
		if ( ! is_readable( $file ) ) {
			return $categories;
		}
		$decoded = json_decode( (string) file_get_contents( $file ), true ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- a repository data file, read once.
		$map     = is_array( $decoded ) ? ( $decoded['categories'] ?? null ) : null;
		if ( is_array( $map ) ) {
			foreach ( $map as $slug => $target ) {
				if ( is_string( $slug ) && is_string( $target ) ) {
					$categories[ $slug ] = $target;
				}
			}
		}
		return $categories;
	}

	/**
	 * The term in the URL's language, paired to the target language.
	 *
	 * @param string $taxonomy      Taxonomy.
	 * @param string $slug          Term slug in the URL's language.
	 * @param string $url_language  Language of the URL.
	 * @param string $language      Target language.
	 */
	private function term_url( string $taxonomy, string $slug, string $url_language, string $language ): ?string {
		$terms = get_terms(
			array(
				'taxonomy'   => $taxonomy,
				'slug'       => $slug,
				'lang'       => $url_language,
				'hide_empty' => false,
				'number'     => 1,
			)
		);
		$term  = is_array( $terms ) ? reset( $terms ) : false;
		if ( ! $term instanceof WP_Term || $this->languages->of_term( $term->term_id ) === $language ) {
			return null;
		}
		$twin = $this->languages->term_translation( $term->term_id, $language );
		$link = null === $twin ? null : get_term_link( $twin, $taxonomy );
		return is_string( $link ) ? $link : null;
	}

	/**
	 * Whether the path is the page's address, in either language: its own
	 * URI or its twin's.
	 *
	 * @param int    $page_id      Page ID.
	 * @param string $path         Path without the language prefix.
	 * @param string $url_language Language of the URL.
	 */
	private function is_page_path( int $page_id, string $path, string $url_language ): bool {
		$candidates = array();
		$uri        = get_page_uri( $page_id );
		if ( is_string( $uri ) && '' !== $uri ) {
			$candidates[] = trim( $uri, '/' );
		}
		$twin     = $this->languages->post_translation( $page_id, Languages::TARGET === $url_language ? Languages::SOURCE : Languages::TARGET );
		$twin_uri = null === $twin ? false : get_page_uri( $twin );
		if ( is_string( $twin_uri ) && '' !== $twin_uri ) {
			$candidates[] = trim( $twin_uri, '/' );
		}
		return in_array( trim( $path, '/' ), $candidates, true );
	}

	/**
	 * The path bases of the translated taxonomies, in both languages.
	 *
	 * @return array<string, list<string>> Taxonomy => bases.
	 */
	private function taxonomy_bases(): array {
		$structure = function_exists( 'wc_get_permalink_structure' ) ? wc_get_permalink_structure() : array();
		$product   = trim( (string) ( $structure['category_rewrite_slug'] ?? '' ), '/' );
		$blog      = trim( (string) get_option( 'category_base' ), '/' );
		return array(
			'product_cat' => array_values( array_unique( array_filter( array( $product, 'produkt-kategorie' ) ) ) ),
			'category'    => array_values( array_unique( array_filter( array( '' === $blog ? 'category' : $blog, 'kategorie' ) ) ) ),
		);
	}
}
