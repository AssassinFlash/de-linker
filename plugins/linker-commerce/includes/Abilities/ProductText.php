<?php
/**
 * Titles, URLs and term names of a product, in the page language.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Abilities;

use Linker\Commerce\Products\Publication;

/**
 * The language of an ability request is `en` or `de`. Titles and permalinks
 * follow the translated product when Polylang is loaded (#9); otherwise the
 * stored post.
 */
final class ProductText {

	/**
	 * `en` or `de`; anything else is English.
	 *
	 * @param mixed $lang Requested language.
	 * @return 'en'|'de'
	 */
	public static function lang( mixed $lang ): string {
		return is_string( $lang ) && str_starts_with( strtolower( $lang ), 'de' ) ? 'de' : 'en';
	}

	/**
	 * The WordPress locale of a language: German is the Sie form
	 * (linker-i18n's Setup, AGENTS.md §3), English the site's own.
	 *
	 * @param 'en'|'de' $lang Language.
	 */
	public static function locale( string $lang ): string {
		return 'de' === $lang ? 'de_DE_formal' : 'en_US';
	}

	/**
	 * The product shown for `$lang`: the Polylang translation when there is one.
	 *
	 * @param int                      $product_id Product ID.
	 * @param 'en'|'de'                $lang       Language.
	 * @param array<string,mixed>|null $manifest Current authority when called inside an ability projection.
	 */
	public static function translated_id( int $product_id, string $lang, ?array $manifest = null ): int {
		if ( ! self::published( $product_id, $manifest ) ) {
			return 0;
		}
		if ( ! function_exists( 'pll_get_post' ) ) {
			return $product_id;
		}
		$translated = pll_get_post( $product_id, 'de' === $lang ? 'de' : 'en' );
		if ( $translated < 1 ) {
			return $product_id;
		}
		return self::published( $translated, $manifest ) ? $translated : 0;
	}

	/**
	 * Resolve a standalone or already scoped product permission.
	 *
	 * @param int                      $id Locale product ID.
	 * @param array<string,mixed>|null $manifest Optional authority projection; standalone callers need a fresh read.
	 */
	private static function published( int $id, ?array $manifest ): bool {
		return null === $manifest ? Publication::is_published( $id ) : Publication::published_in_manifest( $id, $manifest );
	}

	/**
	 * Product title in `$lang`.
	 *
	 * @param int                      $product_id Product ID.
	 * @param 'en'|'de'                $lang       Language.
	 * @param array<string,mixed>|null $manifest Current authority when called inside an ability projection.
	 */
	public static function title( int $product_id, string $lang, ?array $manifest = null ): string {
		$id = self::translated_id( $product_id, $lang, $manifest );
		return $id > 0 ? html_entity_decode( (string) get_the_title( $id ), ENT_QUOTES | ENT_HTML5, 'UTF-8' ) : '';
	}

	/**
	 * Permalink of the product in `$lang` when translated, otherwise the stored post.
	 *
	 * @param int                      $product_id Product ID.
	 * @param 'en'|'de'|null           $lang    Language; omitted uses the stored post.
	 * @param array<string,mixed>|null $manifest Current authority when called inside an ability projection.
	 */
	public static function url( int $product_id, ?string $lang = null, ?array $manifest = null ): string {
		$id = null === $lang ? ( self::published( $product_id, $manifest ) ? $product_id : 0 ) : self::translated_id( $product_id, $lang, $manifest );
		if ( $id < 1 ) {
			return '';
		}
		$url = get_permalink( $id );

		return is_string( $url ) ? $url : '';
	}

	/**
	 * Name of the product's single term in a taxonomy, null without one.
	 *
	 * @param int    $product_id Product ID.
	 * @param string $taxonomy   Taxonomy.
	 */
	public static function term_name( int $product_id, string $taxonomy ): ?string {
		$terms = get_the_terms( $product_id, $taxonomy );
		if ( ! is_array( $terms ) || 1 !== count( $terms ) ) {
			return null;
		}
			$name = reset( $terms )->name;

			return '' === $name ? null : $name;
	}

	/**
	 * Slugs of the product's terms in a taxonomy.
	 *
	 * @param int    $product_id Product ID.
	 * @param string $taxonomy   Taxonomy.
	 * @return list<string>
	 */
	public static function term_slugs( int $product_id, string $taxonomy ): array {
		$terms = get_the_terms( $product_id, $taxonomy );
		$slugs = array();
		foreach ( is_array( $terms ) ? $terms : array() as $term ) {
			if ( '' !== $term->slug ) {
				$slugs[] = $term->slug;
			}
		}

		return $slugs;
	}
}
