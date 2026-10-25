<?php
/**
 * Keep the public tool discoverable and private project URLs out of indexing.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Planner;

/** Native WordPress and SEOPress policy; no project content or identity is read. */
final class Indexing {

	/** Register before WordPress sends the page headers. */
	public function register(): void {
		add_filter( 'wp_headers', array( $this, 'headers' ) );
		add_filter( 'wp_robots', array( $this, 'robots' ) );
		add_filter( 'seopress_titles_noindex_bypass', array( $this, 'noindex' ) );
		add_filter( 'seopress_titles_robots_attrs', array( $this, 'seopress_robots' ) );
		add_filter( 'seopress_titles_canonical_on_noindex', array( $this, 'canonical' ), 20 );
		add_filter( 'pll_rel_hreflang_attributes', array( $this, 'hreflangs' ), 20 );
	}

	/**
	 * Private workspaces cannot be cached. The site's referrer policy is preserved.
	 *
	 * @param array<string,string|false> $headers Existing native headers.
	 * @return array<string,string|false>
	 */
	public function headers( array $headers ): array {
		if ( ! $this->private_context() ) {
			return $headers;
		}
		return array_merge(
			$headers,
			wp_get_nocache_headers(),
			array(
				'Cache-Control' => 'no-store, private, max-age=0',
				'X-Robots-Tag'  => 'noindex, nofollow, nosnippet',
			)
		);
	}

	/**
	 * Native fallback for sites without SEOPress.
	 *
	 * @param array<string,bool|string> $robots Existing robots policy.
	 * @return array<string,bool|string>
	 */
	public function robots( array $robots ): array {
		// SEOPress owns its one robots tag; keep core as the native fallback.
		if ( function_exists( 'seopress_get_service' ) ) {
			return $robots;
		}
		if ( $this->private_context() ) {
			unset( $robots['index'], $robots['follow'] );
			$robots['noindex']   = true;
			$robots['nofollow']  = true;
			$robots['nosnippet'] = true;
		}
		return $robots;
	}

	/**
	 * Use SEOPress's native decision before its metadata/hreflang lifecycle.
	 *
	 * @param mixed $decision Existing native noindex decision.
	 * @return mixed
	 */
	public function noindex( mixed $decision ): mixed {
		return $this->private_context() ? '1' : $decision;
	}

	/**
	 * Match the HTTP policy in SEOPress's existing robots tag.
	 *
	 * @param array<string> $robots Existing directives.
	 * @return array<string>
	 */
	public function seopress_robots( array $robots ): array {
		return $this->private_context() ? array_values( array_unique( array_merge( array_diff( $robots, array( 'index', 'follow' ) ), array( 'noindex', 'nofollow', 'nosnippet' ) ) ) ) : $robots;
	}

	/**
	 * Retain SEOPress's clean public-page canonical, without a project/run query.
	 *
	 * @param bool $allow Existing native policy.
	 */
	public function canonical( bool $allow ): bool {
		return $this->private_context() || $allow;
	}

	/**
	 * A private project is not an alternate public landing page in each language.
	 *
	 * @param array<string,string> $links Existing public language alternates.
	 * @return array<string,string>
	 */
	public function hreflangs( array $links ): array {
		return $this->private_context() ? array() : $links;
	}

	/**
	 * Presence alone is enough, including invalid/empty/array query values.
	 * This decision grants no access and never consumes a project identifier.
	 */
	private function private_context(): bool {
		$keys = array_keys( $_GET ); // phpcs:ignore WordPress.Security.NonceVerification.Recommended -- Read-only indexing policy uses names only, not values or authorisation.
		if ( array() === array_intersect( $keys, array( 'project', 'run', 'pv_kwp', 'annual_kwh', 'phase', 'backup', 'plz' ) ) || is_admin() || ! is_page() ) {
			return false;
		}
		$post = get_queried_object();
		if ( ! $post instanceof \WP_Post ) {
			return false;
		}
		if ( has_shortcode( $post->post_content, 'linker_planner' ) || has_shortcode( $post->post_content, 'linker_configurator' ) ) {
			return true;
		}
		// LiveCanvas owns the page body, so its shortcode need not be in post_content.
		$source = get_page_by_path( 'solution-configurator' );
		if ( ! $source instanceof \WP_Post ) {
			return false;
		}
		$ids = function_exists( 'pll_get_post_translations' ) ? pll_get_post_translations( $source->ID ) : array();
		return $source->ID === $post->ID || in_array( $post->ID, $ids, true );
	}
}
