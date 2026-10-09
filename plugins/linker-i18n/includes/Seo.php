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
 * search results, and keeps WordPress from guessing a 404 into another
 * language.
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
}
