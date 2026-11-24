<?php
/**
 * Keeps Genie's page out of the search index and the XML sitemap.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

use WP_Post;

/** Keep both language versions of the Genie workspace outside the index. */
final class PageIndexing {

	/**
	 * The workspace page's slug, in both languages.
	 */
	private const SLUG = 'genie';

	/**
	 * Registers the indexing filters: SEOPress's decision, its robots array,
	 * the native robots policy, and the sitemap entry.
	 */
	public function register(): void {
		add_filter( 'seopress_titles_noindex_bypass', array( $this, 'noindex' ) );
		add_filter( 'seopress_titles_robots_attrs', array( $this, 'seopress_robots' ) );
		add_filter( 'pll_rel_hreflang_attributes', array( $this, 'alternates' ), 50 );
		add_filter( 'seopress_titles_desc', array( $this, 'description' ), 50 );
		add_filter( 'wp_robots', array( $this, 'robots' ) );
		add_filter( 'seopress_sitemaps_single_url', array( $this, 'drop_from_sitemap' ), 10, 2 );
	}

	/**
	 * The workspace page answers noindex; every other decision is untouched.
	 *
	 * @param mixed $noindex SEOPress's effective noindex decision so far.
	 * @return mixed The native decision, or '1' on the workspace page.
	 */
	public function noindex( mixed $noindex ): mixed {
		if ( ! empty( $noindex ) || ! $this->request_is_workspace() ) {
			return $noindex;
		}
		return '1';
	}

	/**
	 * The workspace page's robots tag carries noindex; every other directive,
	 * including `follow`, stays as SEOPress built it.
	 *
	 * @param string[] $robots SEOPress's robots directives.
	 * @return string[]
	 */
	public function seopress_robots( array $robots ): array {
		if ( ! $this->request_is_workspace() ) {
			return $robots;
		}
		return array_values( array_unique( array_merge( array_diff( $robots, array( 'index' ) ), array( 'noindex' ) ) ) );
	}

	/**
	 * The workspace page is noindex in WordPress's own policy — the fallback
	 * for a host without SEOPress, where this policy prints the only robots
	 * tag.
	 *
	 * @param array<string,bool|string> $robots Existing robots policy.
	 * @return array<string,bool|string>
	 */
	public function robots( array $robots ): array {
		// SEOPress owns its one robots tag; core's directives are emptied while
		// it is active, so the fallback stays aside rather than adding a tag.
		if ( function_exists( 'seopress_get_service' ) ) {
			return $robots;
		}
		if ( $this->request_is_workspace() ) {
			unset( $robots['index'] );
			$robots['noindex'] = true;
		}
		return $robots;
	}

	/**
	 * The workspace page leaves the XML sitemap.
	 *
	 * @param mixed $url  The sitemap entry; null when an earlier filter dropped it.
	 * @param mixed $post The post the entry describes.
	 * @return mixed The entry, or null when it must not be listed.
	 */
	public function drop_from_sitemap( mixed $url, mixed $post ): mixed {
		return $post instanceof WP_Post && self::is_workspace_post( $post ) ? null : $url;
	}

	/**
	 * Omit alternate index URLs for private workspaces.
	 *
	 * @param array<string,string> $links Language alternates.
	 * @return array<string,string>
	 */
	public function alternates( array $links ): array {
		return $this->request_is_workspace() ? array() : $links;
	}

	/**
	 * Describe the public tool in the page language.
	 *
	 * @param string $description SEOPress description.
	 */
	public function description( string $description ): string {
		return $this->request_is_workspace() ? __( 'Ask Genie about inverter and battery compatibility, product specifications and manufacturer documents for your project.', 'linker-tools' ) : $description;
	}

	/**
	 * Whether this request's main query is the workspace page.
	 */
	private function request_is_workspace(): bool {
		if ( ! is_page() ) {
			return false;
		}
		$object = get_queried_object();
		return $object instanceof WP_Post && self::is_workspace_post( $object );
	}

	/**
	 * One page post is a workspace address: top-level, named `genie`.
	 *
	 * @param WP_Post $post The page post.
	 */
	public static function is_workspace_post( WP_Post $post ): bool {
		return 'page' === $post->post_type && self::SLUG === $post->post_name && 0 === (int) $post->post_parent;
	}
}
