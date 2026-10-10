<?php
/**
 * German URL segments for products, product categories and the shop.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n;

/**
 * Serves /de/produkt/<slug>/, /de/produkt-kategorie/<path>/ and /de/produkte/
 * and makes every German link use them; the English segments under /de/ are
 * not German addresses and answer 404.
 *
 * The German segments are those of the live site's 150 German URLs
 * (/de-sitemap.xml on 2026-10-09: 104 under /de/produkt/, 10 under
 * /de/produkt-kategorie/, the shop at /de/produkte/). Translated URL slugs
 * are a Polylang Pro feature (docs/research/2026-10-09/i18n-opensource-replication.md §2.3, §5.3).
 */
final class UrlSegments {

	/**
	 * The German segment of the product base.
	 */
	public const PRODUCT = 'produkt';

	/**
	 * The German segment of the product category base.
	 */
	public const PRODUCT_CATEGORY = 'produkt-kategorie';

	/**
	 * The German segment of the shop (the product archive).
	 */
	public const SHOP = 'produkte';

	/**
	 * Option holding the fingerprint of the rules last written to the rewrite cache.
	 */
	private const FINGERPRINT_OPTION = 'linker_i18n_rewrite_fingerprint';

	/**
	 * Sets up the URL segments.
	 *
	 * @param Languages $languages The site's languages.
	 */
	public function __construct( private readonly Languages $languages ) {}

	/**
	 * The English segments with their German counterparts: WooCommerce's
	 * product and category bases and the shop page's path.
	 *
	 * @return array<string, string> English segment => German segment.
	 */
	public function segments(): array {
		$structure = wc_get_permalink_structure();
		$segments  = array(
			trim( (string) $structure['product_rewrite_slug'], '/' )  => self::PRODUCT,
			trim( (string) $structure['category_rewrite_slug'], '/' ) => self::PRODUCT_CATEGORY,
		);
		$shop_page = (int) get_option( 'woocommerce_shop_page_id' );
		$shop_path = $shop_page > 0 ? get_page_uri( $shop_page ) : '';
		if ( is_string( $shop_path ) && '' !== $shop_path ) {
			$segments[ $shop_path ] = self::SHOP;
		}
		unset( $segments[''] );
		return $segments;
	}

	/**
	 * The German rewrite rules, ahead of all others (filter `rewrite_rules_array`).
	 *
	 * @param array<string, string> $rules Rewrite rules.
	 * @return array<string, string>
	 */
	public function rules( array $rules ): array {
		return $this->german_rules() + $rules;
	}

	/**
	 * Stops Polylang from writing /de/ versions of the English product,
	 * product category and shop rules (filter `pll_modify_rewrite_rule`):
	 * those addresses are served by the German rules or not at all.
	 *
	 * @param bool                  $modify  Whether Polylang adds the language to the rule.
	 * @param array<string, string> $rule    The rule.
	 * @param string                $filter  Rule set being filtered.
	 * @param string|false          $archive Post type of an archive rule, false otherwise.
	 */
	public function polylang_rule( bool $modify, array $rule, string $filter, $archive ): bool {
		unset( $rule );
		if ( in_array( $filter, array( 'product', 'product_cat' ), true ) || 'product' === $archive ) {
			return false;
		}
		return $modify;
	}

	/**
	 * Writes the rewrite cache again when the German rules changed (action
	 * `wp_loaded`, after Polylang prepared its rule filters at priority 9).
	 */
	public function refresh(): void {
		if ( ! $this->languages->ready() ) {
			return;
		}
		$fingerprint = md5( (string) wp_json_encode( $this->german_rules() ) );
		if ( get_option( self::FINGERPRINT_OPTION ) === $fingerprint ) {
			return;
		}
		flush_rewrite_rules( false );
		update_option( self::FINGERPRINT_OPTION, $fingerprint, false );
	}

	/**
	 * Puts a link into the segments of its language (filters `post_type_link`,
	 * `term_link`, `post_type_archive_link` and Polylang's `pll_translation_url`,
	 * which gives the language switcher and hreflang their URLs).
	 *
	 * A German link gets the German segment (/de/product/x/ → /de/produkt/x/);
	 * an English link made from a German one by swapping the language gets the
	 * English segment back (/produkte/ → /products/).
	 *
	 * @param mixed $url The link.
	 * @return mixed
	 */
	public function link( $url ) {
		if ( ! is_string( $url ) || ! $this->languages->ready() ) {
			return $url;
		}
		$german  = $this->languages->home_url( Languages::TARGET );
		$english = $this->languages->home_url( Languages::SOURCE );
		if ( str_starts_with( $url, $german ) ) {
			return $german . $this->swap( substr( $url, strlen( $german ) ), $this->segments() );
		}
		if ( str_starts_with( $url, $english ) ) {
			return $english . $this->swap( substr( $url, strlen( $english ) ), array_flip( $this->segments() ) );
		}
		return $url;
	}

	/**
	 * Replaces the first segment of a path when the map knows it.
	 *
	 * @param string                $path Path below the language's home URL.
	 * @param array<string, string> $map  Segment => replacement.
	 */
	private function swap( string $path, array $map ): string {
		foreach ( $map as $from => $to ) {
			if ( $path === $from || str_starts_with( $path, $from . '/' ) || str_starts_with( $path, $from . '?' ) ) {
				return $to . substr( $path, strlen( $from ) );
			}
		}
		return $path;
	}

	/**
	 * The German rules: single product, product category (with paging) and
	 * the shop (with paging).
	 *
	 * @return array<string, string>
	 */
	private function german_rules(): array {
		$base = Languages::TARGET . '/';
		$lang = '&lang=' . Languages::TARGET;
		return array(
			$base . self::PRODUCT . '/([^/]+)/?$'        => 'index.php?product=$matches[1]' . $lang,
			$base . self::PRODUCT_CATEGORY . '/(.+?)/page/?([0-9]{1,})/?$' => 'index.php?product_cat=$matches[1]&paged=$matches[2]' . $lang,
			$base . self::PRODUCT_CATEGORY . '/(.+?)/?$' => 'index.php?product_cat=$matches[1]' . $lang,
			$base . self::SHOP . '/page/?([0-9]{1,})/?$' => 'index.php?post_type=product&paged=$matches[1]' . $lang,
			$base . self::SHOP . '/?$'                   => 'index.php?post_type=product' . $lang,
		);
	}
}
