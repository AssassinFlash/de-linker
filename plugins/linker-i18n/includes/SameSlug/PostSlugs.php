<?php
/**
 * One slug for an English post and its German version.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\SameSlug;

use Linker\I18n\Languages;

/**
 * Lets a post keep a slug that only posts of the other language hold.
 *
 * WordPress makes a slug unique across all posts of a type and appends "-2"
 * to the second one (`wp_unique_post_slug()`); Polylang's free edition does
 * the same, sharing slugs is a Pro feature
 * (docs/research/2026-10-09/i18n-opensource-replication.md §5.1). The 104
 * German product URLs and three German page URLs reuse the English slug
 * (§5.2), so uniqueness here is per language.
 */
final class PostSlugs {

	/**
	 * Sets up the filter.
	 *
	 * @param Languages $languages The site's languages.
	 */
	public function __construct( private readonly Languages $languages ) {}

	/**
	 * Gives back the slug WordPress refused when only posts of another
	 * language hold it (filter `wp_unique_post_slug`).
	 *
	 * @param string $slug          The slug WordPress made unique.
	 * @param int    $post_id       Post ID.
	 * @param string $post_status   Post status.
	 * @param string $post_type     Post type.
	 * @param int    $post_parent   Parent post ID.
	 * @param string $original_slug The slug asked for.
	 */
	public function unique( string $slug, int $post_id, string $post_status, string $post_type, int $post_parent, string $original_slug ): string {
		unset( $post_status );
		if ( $slug === $original_slug || '' === $original_slug || ! $this->languages->translates_post_type( $post_type ) ) {
			return $slug;
		}
		$language = $this->languages->of_post( $post_id );
		if ( null === $language || $this->reserved( $original_slug, $post_type, $post_parent ) ) {
			return $slug;
		}
		$holders = $this->holders( $original_slug, $post_id, $post_type, $post_parent );
		if ( array() === $holders ) {
			return $slug;
		}
		foreach ( $holders as $holder ) {
			$holder_language = $this->languages->of_post( $holder );
			if ( null === $holder_language || $holder_language === $language ) {
				return $slug;
			}
		}
		return $original_slug;
	}

	/**
	 * The posts that hold the slug, by the same rule as `wp_unique_post_slug()`:
	 * same type (pages also clash with attachments) and, for hierarchical
	 * types, the same parent.
	 *
	 * @param string $slug        Slug.
	 * @param int    $post_id     The post being saved, which does not count.
	 * @param string $post_type   Post type.
	 * @param int    $post_parent Parent post ID.
	 * @return list<int>
	 */
	private function holders( string $slug, int $post_id, string $post_type, int $post_parent ): array {
		global $wpdb;
		if ( is_post_type_hierarchical( $post_type ) ) {
			// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- the query wp_unique_post_slug() itself runs, with the IDs instead of the slug.
			$ids = $wpdb->get_col( $wpdb->prepare( "SELECT ID FROM $wpdb->posts WHERE post_name = %s AND post_type IN ( %s, 'attachment' ) AND ID != %d AND post_parent = %d", $slug, $post_type, $post_id, $post_parent ) );
		} else {
			// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- the query wp_unique_post_slug() itself runs, with the IDs instead of the slug.
			$ids = $wpdb->get_col( $wpdb->prepare( "SELECT ID FROM $wpdb->posts WHERE post_name = %s AND post_type = %s AND ID != %d", $slug, $post_type, $post_id ) );
		}
		return array_values( array_map( 'intval', $ids ) );
	}

	/**
	 * Whether WordPress refuses the slug for a reason other than another post:
	 * feed names, "embed", numeric slugs and what plugins mark bad through
	 * `wp_unique_post_slug()`'s own filters.
	 *
	 * @param string $slug        Slug.
	 * @param string $post_type   Post type.
	 * @param int    $post_parent Parent post ID.
	 */
	private function reserved( string $slug, string $post_type, int $post_parent ): bool {
		global $wp_rewrite;
		$feeds = $wp_rewrite instanceof \WP_Rewrite ? $wp_rewrite->feeds : array();
		if ( in_array( $slug, $feeds, true ) || 'embed' === $slug || 1 === preg_match( '/^\d+$/', $slug ) ) {
			return true;
		}
		if ( is_post_type_hierarchical( $post_type ) ) {
			$pagination = $wp_rewrite instanceof \WP_Rewrite ? preg_quote( $wp_rewrite->pagination_base, '@' ) : 'page';
			if ( 1 === preg_match( "@^($pagination)?\d+$@", $slug ) ) {
				return true;
			}
			/** This filter is documented in wp-includes/post.php (wp_unique_post_slug()). */
			return (bool) apply_filters( 'wp_unique_post_slug_is_bad_hierarchical_slug', false, $slug, $post_type, $post_parent ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- WordPress's own filter, applied as wp_unique_post_slug() applies it.
		}
		/** This filter is documented in wp-includes/post.php (wp_unique_post_slug()). */
		return (bool) apply_filters( 'wp_unique_post_slug_is_bad_flat_slug', false, $slug, $post_type ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- WordPress's own filter, applied as wp_unique_post_slug() applies it.
	}
}
