<?php
/**
 * Keeps Genie's page out of the search index and the XML sitemap.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

use WP_Post;

/**
 * /genie/ and /de/genie/ are the workspace's login wall, not a content page:
 * an anonymous visitor gets the tool's name and "Anmelden / Konto erstellen",
 * and the conversation itself needs an account (docs/specs/19-tool-pages.md
 * §2). Google indexed the English page on 2026-10-26 and both addresses were
 * listed in SEOPress's page-sitemap1.xml, so both now answer noindex and leave
 * that sitemap.
 *
 * The decision lands on SEOPress's own extension points — the filters the
 * plugin and its PRO add-on already use — instead of on the two pages' stored
 * robots option. The stored option (`_seopress_robots_index`, the per-post
 * "No index" checkbox) is the same signal and produces the same output, but it
 * is WordPress data: this tree's migration and `present` own the pages, and a
 * page re-imported or recreated without that meta would silently return to the
 * index. A rule that ships with the plugin survives that and needs no
 * production write.
 *
 * - `seopress_titles_noindex_bypass` is the effective robots decision the meta
 *   tag is built from. A page it answers noindex for also loses its canonical
 *   and Polylang's hreflang alternates, which is SEOPress's established
 *   treatment of a noindexed URL (options-titles-metas.php) and exactly what
 *   the stored option would produce. The English and German pages stay
 *   Polylang twins either way; the alternates are suppressed on both sides,
 *   not on one.
 * - `seopress_sitemaps_single_url` is where the XML sitemap drops an entry.
 *   SEOPress returns null there for a post whose stored robots option says
 *   noindex (src/Services/Sitemap/Render/Single.php), but reads the post meta
 *   only — a decision made in code is invisible to it, so this filter repeats
 *   the exclusion for the workspace page.
 *
 * The page is identified by the path both languages share — the English post
 * and its German twin are both named `genie` (Polylang puts German under
 * /de/) — and by being a top-level page, so a page that merely ends in
 * /genie/ under another parent is not caught. When the page moves or is
 * renamed this rule stops applying with it; that is the point, the address it
 * names is the one the site serves.
 */
final class PageIndexing {

	/**
	 * The workspace page's slug, in both languages.
	 */
	private const SLUG = 'genie';

	/**
	 * Registers the two SEOPress filters.
	 */
	public function register(): void {
		add_filter( 'seopress_titles_noindex_bypass', array( $this, 'noindex' ) );
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
	private static function is_workspace_post( WP_Post $post ): bool {
		return 'page' === $post->post_type && self::SLUG === $post->post_name && 0 === (int) $post->post_parent;
	}
}
