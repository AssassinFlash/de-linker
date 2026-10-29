<?php
/**
 * The hreflang links and the 404 rule of the two languages.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n;

/**
 * The search-engine side of the two languages. Polylang writes the hreflang
 * links of every translated page; this adds the x-default, leaves them off
 * search results, keeps WordPress from guessing a 404 into another language,
 * and gives the 404 title the request's own language.
 */
final class Seo {

	/**
	 * Polylang's hreflang links (filter `pll_rel_hreflang_attributes`): with
	 * x-default on the English URL, as the live site has it
	 * (docs/research/2026-10-09/i18n-audit.md §A2), and none on search
	 * results, which WordPress marks noindex (the audit's finding of hreflang
	 * on noindex pages).
	 *
	 * @param array<string, string> $hreflangs Language code => URL.
	 * @return array<string, string>
	 */
	public function hreflangs( array $hreflangs ): array {
		if ( is_search() ) {
			return array();
		}
		if ( isset( $hreflangs[ Languages::SOURCE ] ) && ! isset( $hreflangs['x-default'] ) ) {
			$hreflangs['x-default'] = $hreflangs[ Languages::SOURCE ];
		}
		return $hreflangs;
	}

	/**
	 * Turns off WordPress's redirect of an unknown URL to a post with a
	 * similar slug (filter `do_redirect_guess_404_permalink`). The guess
	 * ignores languages: /de/about/ would be sent to the English /about/
	 * and an English typo to a German post, where both must be 404.
	 */
	public function guess_404(): bool {
		return false;
	}

	/**
	 * The 404 title in the request's language (filter `seopress_titles_title`).
	 *
	 * SEOPress keeps one 404 title for the whole site: the option
	 * (`seopress_titles_archives_404_title`) holds "Page not found %%sep%%
	 * %%sitetitle%%", and SEOPress replaces both placeholders before this
	 * filter runs, so what arrives here is "Page not found | Linker". The
	 * sentence is a stored option, not a gettext string, so the German
	 * language pack cannot reach it — measured 2026-10-16: a German 404
	 * carried the English tab title on the live site and on the local
	 * instance, while the German core pack already holds the words
	 * ("Seite nicht gefunden"). The sentence is WordPress's own — core's
	 * `<title>` fallback for a 404 — and the core language pack translates it
	 * with the request's locale, which Polylang has already switched; the
	 * "default" text domain is the one linker-i18n's phpcs ruleset allows for
	 * exactly this. The title's suffix (the site name SEOPress appended)
	 * stays as it is.
	 *
	 * @param string $title SEOPress's document title.
	 */
	public function not_found_title( string $title ): string {
		if ( ! is_404() || ! str_starts_with( $title, 'Page not found' ) ) {
			return $title;
		}

		return __( 'Page not found', 'default' ) . substr( $title, strlen( 'Page not found' ) );
	}

	/**
	 * Mirrors the English page's noindex ruling onto its German twin at
	 * render time (filter `seopress_titles_noindex_bypass`).
	 *
	 * Measured on production, 2026-10-29: the English thank-you page (post
	 * 623) carries `_seopress_robots_index = yes` while its German twin does
	 * not, so the German page answered indexable and sat in the sitemap —
	 * an asymmetric pair under matching hreflang links. Twins now mirrors
	 * the meta on save; this filter is the render-time half, so a twin whose
	 * stored meta has not been rewritten yet still answers noindex. Only the
	 * English source's own meta is read: the twin's own value (which the
	 * migration or Twins wrote) keeps SEOPress's native decision unchanged.
	 *
	 * @param mixed $decision Existing noindex decision.
	 * @return mixed
	 */
	public function twin_noindex( mixed $decision ): mixed {
		return $this->source_says_noindex() ? '1' : $decision;
	}

	/**
	 * The same mirror in SEOPress's robots tag (filter
	 * `seopress_titles_robots_attrs`): `follow` stays whatever the page's own
	 * meta says, as the English noindex page itself does.
	 *
	 * @param string[] $robots Existing directives.
	 * @return string[]
	 */
	public function twin_robots( array $robots ): array {
		if ( ! $this->source_says_noindex() ) {
			return $robots;
		}
		return array_values( array_unique( array_merge( array_diff( $robots, array( 'index' ) ), array( 'noindex' ) ) ) );
	}

	/**
	 * Whether the English twin of the queried page rules it noindex: a German
	 * singular page whose English source carries `_seopress_robots_index`.
	 */
	private function source_says_noindex(): bool {
		if ( is_admin() || ! is_singular() ) {
			return false;
		}
		$post = get_queried_object();
		if ( ! $post instanceof \WP_Post ) {
			return false;
		}
		if ( ! function_exists( 'pll_get_post' ) ) {
			return false;
		}
		$source = (int) pll_get_post( (int) $post->ID, Languages::SOURCE );
		return $source > 0 && $source !== (int) $post->ID && 'yes' === get_post_meta( $source, '_seopress_robots_index', true );
	}
}
