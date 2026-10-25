<?php
/**
 * The language entry: the header toggle and the footer switcher.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

/**
 * The one implementation behind every language entry. The header's toggle
 * and the footer's switcher differ in markup, never in where they send the
 * visitor: Polylang's switcher translates the queried page and the language
 * segment, and the request's own path past that object (WooCommerce
 * endpoint, confirmation value, paging) and query are kept.
 *
 * The footer used to carry static hrefs — "/de/" for "Deutsch" on every
 * English page and "/de/" for "Englisch" on every German page
 * (docs/research/2026-10-17-i18n-audit/AUDIT.md, H2).
 */
final class LanguageLinks {

	/**
	 * Visitor query state retained when switching this page's language.
	 */
	private const LANGUAGE_QUERY_KEYS = array( 's', 'orderby', 'step', 'key', 'admin-access', 'q', 'sort', 'application', 'brand', 'phase', 'power', 'kw_min', 'kw_max', 'kwh_min', 'kwh_max', 'product-page' );

	/**
	 * The header's toggle: a globe (hidden by the header's own stylesheet)
	 * beside the two halves, the current language marked.
	 *
	 * @param string $variant The toggle's variant class.
	 */
	public function toggle( string $variant ): string {
		$en_url = $this->url( 'en' );
		$de_url = $this->url( 'de' );
		$is_de  = \function_exists( 'pll_current_language' ) && 'de' === pll_current_language();
		$globe  = '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path fill="currentColor" d="M12 2a10 10 0 100 20 10 10 0 000-20zm6.9 6h-2.6a15.6 15.6 0 00-1.2-3.5A8 8 0 0118.9 8zM12 4c.7 1 1.3 2.4 1.7 4H10.3c.4-1.6 1-3 1.7-4zM4.3 14a8 8 0 010-4h3a19 19 0 000 4h-3zm.8 2h2.6c.3 1.3.7 2.5 1.2 3.5A8 8 0 015.1 16zm2.6-8H5.1a8 8 0 013.8-3.5A15.6 15.6 0 007.7 8zM12 20c-.7-1-1.3-2.4-1.7-4h3.4c-.4 1.6-1 3-1.7 4zm2.1-6H9.9a17 17 0 010-4h4.2a17 17 0 010 4zm.9 5.5c.5-1 .9-2.2 1.2-3.5h2.6a8 8 0 01-3.8 3.5zM16.7 14a19 19 0 000-4h3a8 8 0 010 4h-3z"/></svg>';
		$html   = '<span class="lnk-lang-toggle ' . esc_attr( $variant ) . '" role="group" aria-label="' . esc_attr__( 'Language', 'linker-commerce' ) . '">' . $globe;
		$html  .= '<a class="lnk-lang-half' . ( $is_de ? '' : ' is-active' ) . '" href="' . esc_url( $en_url ) . '" data-lnk-flang="en" hreflang="en" lang="en" data-linker-language-choice="en" title="English"' . ( $is_de ? '' : ' aria-current="true"' ) . '>EN</a>';
		$html  .= '<a class="lnk-lang-half' . ( $is_de ? ' is-active' : '' ) . '" href="' . esc_url( $de_url ) . '" data-lnk-flang="de" hreflang="de" lang="de" data-linker-language-choice="de" title="Deutsch"' . ( $is_de ? ' aria-current="true"' : '' ) . '>DE</a>';
		return $html . '</span>';
	}

	/**
	 * The footer's switcher: the two words the footer prints in place of the
	 * header's halves, with the same destinations.
	 */
	public function footer(): string {
		$is_de = \function_exists( 'pll_current_language' ) && 'de' === pll_current_language();
		return '<a data-linker-language-choice="en" data-lnk-flang="en" href="' . esc_url( $this->url( 'en' ) ) . '" hreflang="en" lang="en"' . ( $is_de ? '' : ' aria-current="true"' ) . '>' . esc_html__( 'English', 'linker-commerce' ) . '</a>'
			. "\n" . '<a data-linker-language-choice="de" data-lnk-flang="de" href="' . esc_url( $this->url( 'de' ) ) . '" hreflang="de" lang="de"' . ( $is_de ? ' aria-current="true"' : '' ) . '>' . esc_html( 'Deutsch' ) . '</a>';
	}

	/**
	 * The current page in the given language.
	 *
	 * Polylang's switcher (`pll_the_languages()`, filtered by linker-i18n's
	 * UrlSegments on `pll_translation_url`) translates the queried page and
	 * the language segment, and stops there: a page permalink has no
	 * WooCommerce endpoint, no confirmation value and no query. The current
	 * language's half is the address the visitor is on. The other half is
	 * that translation's permalink with the request path past the queried
	 * object's permalink kept as-is, then the query keys the visitor set.
	 * Home is the fallback only when neither the queried object nor the
	 * switcher has an answer.
	 *
	 * @param string $lang Language code.
	 */
	public function url( string $lang ): string {
		$current = \function_exists( 'pll_current_language' ) ? pll_current_language() : '';
		if ( \is_string( $current ) && $current === $lang ) {
			return $this->requested_url();
		}
		return $this->with_request_context( $this->translated_switcher_url( $lang ), $lang );
	}

	/**
	 * Polylang's switcher URL for `$lang`, or the language home when the
	 * switcher has no answer.
	 *
	 * @param string $lang Language code.
	 */
	private function translated_switcher_url( string $lang ): string {
		if ( \function_exists( 'pll_the_languages' ) ) {
			$languages = pll_the_languages(
				array(
					'raw'           => 1,
					'hide_if_empty' => 0,
				)
			);
			if ( \is_array( $languages ) && isset( $languages[ $lang ]['url'] ) && \is_string( $languages[ $lang ]['url'] ) ) {
				return $languages[ $lang ]['url'];
			}
		}
		if ( \function_exists( 'pll_home_url' ) ) {
			return trailingslashit( (string) pll_home_url( $lang ) );
		}
		return PageUrls::home();
	}

	/**
	 * The other language's page with the request's path past the queried
	 * object, and the query the visitor set, kept.
	 *
	 * The base is the queried object's permalink in `$lang` (account page,
	 * confirmation page, category, shop). The request path minus that
	 * object's permalink in the current language is the remainder — endpoint,
	 * value, nested endpoint, paging — and is appended unchanged. A request
	 * that is not that object, or has no translation, keeps the switcher's
	 * URL. The query is part of the request, not a second translation.
	 *
	 * @param string $url  The switcher's URL.
	 * @param string $lang Language code.
	 */
	private function with_request_context( string $url, string $lang ): string {
		$base = $this->translated_permalink( $lang );
		if ( '' !== $base ) {
			$remainder = $this->path_remainder();
			if ( '' !== $remainder ) {
				$url = $this->append_path( $base, $remainder );
			} else {
				$url = $base;
			}
		}
		// The request's own query, not the query vars WordPress rewrites:
		// a catalogue page sets orderby to its default even when the address
		// carried none. `key` is the order key the confirmation page needs —
		// without it Woo renders the thank-you page without order details.
		// `admin-access` keeps the explanation selected in the other language;
		// its visibility still requires Woo's recorded session decision.
		$kept = array();
		foreach ( self::LANGUAGE_QUERY_KEYS as $query_key ) {
			// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- the public address, not a submitted form.
			if ( ! isset( $_GET[ $query_key ] ) || ! \is_string( $_GET[ $query_key ] ) || '' === $_GET[ $query_key ] ) {
				continue;
			}
			$kept[ $query_key ] = rawurlencode( sanitize_text_field( wp_unslash( $_GET[ $query_key ] ) ) ); // phpcs:ignore WordPress.Security.NonceVerification.Recommended -- same public address.
		}
		// Preserve the journal form's explicit scope when general search spans the site.
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- public GET navigation, exact known type only.
		if ( isset( $kept['s'], $_GET['post_type'] ) && \is_string( $_GET['post_type'] ) && 'post' === sanitize_text_field( wp_unslash( $_GET['post_type'] ) ) ) {
			$kept['post_type'] = 'post';
		}
		// A Contact handoff is revalidated, rather than retaining arbitrary transport JSON.
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- public GET navigation.
		$contact = \Linker\Commerce\Contact\SelectionContext::language_query( wp_unslash( $_GET ), $lang );
		foreach ( $contact as $key => $value ) {
			$kept[ $key ] = rawurlencode( $value );
		}
		$url = (string) add_query_arg( $kept, remove_query_arg( array_merge( self::LANGUAGE_QUERY_KEYS, array( 'post_type', 'cbq', 'intent', \Linker\Commerce\Contact\SelectionContext::FIELD ) ), $url ) );
		/**
		 * Reapply Polylang's native URL translation after retaining request context.
		 *
		 * @since 0.2.0
		 *
		 * @param string $url Translated object plus endpoint or pagination.
		 * @param string $lang Target language.
		 */
		return (string) apply_filters( 'pll_translation_url', $url, $lang ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- Polylang's existing public translation seam.
	}

	/**
	 * The address the visitor requested: the current language's half points
	 * at it rather than at a rebuilt permalink. The cache-bust key is not
	 * part of that address.
	 */
	private function requested_url(): string {
		$requested = \function_exists( 'pll_get_requested_url' ) ? pll_get_requested_url() : home_url( (string) wp_unslash( $_SERVER['REQUEST_URI'] ?? '/' ) ); // phpcs:ignore WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- the public address the visitor is on.
		return (string) remove_query_arg( 'cbq', $requested );
	}

	/**
	 * The queried object's permalink in `$lang`, via the same Polylang
	 * translation the other page links use (`pll_get_post` / `pll_get_term`
	 * + `get_permalink` / `get_term_link`). '' when there is no queried
	 * object, or its translation cannot be resolved — the caller then keeps
	 * the switcher's URL rather than inventing a second one.
	 *
	 * @param string $lang Language code.
	 */
	private function translated_permalink( string $lang ): string {
		if ( ! \function_exists( 'pll_get_post' ) && ! \function_exists( 'pll_get_term' ) ) {
			return '';
		}
		$queried = get_queried_object();
		if ( $queried instanceof \WP_Post ) {
			if ( ! \function_exists( 'pll_get_post' ) ) {
				return '';
			}
			$translated = (int) pll_get_post( (int) $queried->ID, $lang );
			if ( $translated <= 0 ) {
				return '';
			}
			$link = get_permalink( $translated );
			return \is_string( $link ) ? $link : '';
		}
		if ( $queried instanceof \WP_Term ) {
			if ( ! \function_exists( 'pll_get_term' ) ) {
				return '';
			}
			$translated = (int) pll_get_term( (int) $queried->term_id, $lang );
			if ( $translated <= 0 ) {
				return '';
			}
			$link = get_term_link( $translated );
			return \is_string( $link ) ? $link : '';
		}
		if ( \function_exists( 'is_shop' ) && is_shop() && \function_exists( 'wc_get_page_id' ) && \function_exists( 'pll_get_post' ) ) {
			$page_id = (int) wc_get_page_id( 'shop' );
			if ( $page_id <= 0 ) {
				return '';
			}
			$translated = (int) pll_get_post( $page_id, $lang );
			if ( $translated <= 0 ) {
				return '';
			}
			$link = get_permalink( $translated );
			return \is_string( $link ) ? $link : '';
		}
		if ( \function_exists( 'is_post_type_archive' ) && is_post_type_archive( 'product' ) ) {
			$link = get_post_type_archive_link( 'product' );
			return \is_string( $link ) ? $link : '';
		}
		return '';
	}

	/**
	 * The request path after the queried object's permalink, '' when the
	 * request is that permalink or does not start with it.
	 *
	 * Read from the path, not from the endpoint query var: WooCommerce maps
	 * `inquiries` onto `orders` and stores only the value, so the query var
	 * cannot rebuild `inquiries/2/` or `company/billing/`.
	 */
	private function path_remainder(): string {
		$base = $this->queried_permalink();
		if ( '' === $base ) {
			return '';
		}
		$request = trim( (string) wp_parse_url( (string) wp_unslash( $_SERVER['REQUEST_URI'] ?? '' ), PHP_URL_PATH ), '/' ); // phpcs:ignore WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- a path, compared against the queried permalink only.
		$prefix  = trim( (string) wp_parse_url( $base, PHP_URL_PATH ), '/' );
		if ( $request === $prefix ) {
			return '';
		}
		$needle = $prefix . '/';
		if ( '' === $prefix || ! str_starts_with( $request . '/', $needle ) ) {
			return '';
		}
		return substr( $request, strlen( $needle ) );
	}

	/**
	 * The queried object's permalink in the current language, the path
	 * prefix the remainder is measured against. '' when the request has no
	 * queried object whose permalink is a path prefix.
	 */
	private function queried_permalink(): string {
		$queried = get_queried_object();
		if ( $queried instanceof \WP_Post ) {
			$link = get_permalink( $queried );
			// A post argument is string; the no-argument form of get_permalink() is string|false.
			return \is_string( $link ) ? $link : ''; // @phpstan-ignore function.alreadyNarrowedType
		}
		if ( $queried instanceof \WP_Term ) {
			$link = get_term_link( $queried );
			return \is_string( $link ) ? $link : '';
		}
		if ( \function_exists( 'is_shop' ) && is_shop() && \function_exists( 'wc_get_page_permalink' ) ) {
			return (string) wc_get_page_permalink( 'shop' );
		}
		if ( \function_exists( 'is_post_type_archive' ) && is_post_type_archive( 'product' ) ) {
			$link = get_post_type_archive_link( 'product' );
			return \is_string( $link ) ? $link : '';
		}
		return '';
	}

	/**
	 * Appends the request's remaining path to a permalink, keeping that
	 * permalink's own query. The remainder is the request path past the
	 * queried object's permalink.
	 *
	 * @param string $permalink Permalink of the translated queried object.
	 * @param string $remainder Remaining path, without a leading slash.
	 */
	private function append_path( string $permalink, string $remainder ): string {
		$parts = wp_parse_url( $permalink );
		$path  = untrailingslashit( \is_array( $parts ) ? (string) ( $parts['path'] ?? '' ) : $permalink ) . '/' . $remainder;
		$path  = user_trailingslashit( $path );
		if ( ! \is_array( $parts ) ) {
			return $path;
		}
		$url = '';
		if ( isset( $parts['scheme'] ) ) {
			$url .= $parts['scheme'] . '://';
		}
		if ( isset( $parts['user'] ) ) {
			$url .= $parts['user'];
			if ( isset( $parts['pass'] ) ) {
				$url .= ':' . $parts['pass'];
			}
			$url .= '@';
		}
		if ( isset( $parts['host'] ) ) {
			$url .= $parts['host'];
		}
		if ( isset( $parts['port'] ) ) {
			$url .= ':' . $parts['port'];
		}
		$url .= $path;
		if ( isset( $parts['query'] ) && '' !== $parts['query'] ) {
			$url .= '?' . $parts['query'];
		}
		if ( isset( $parts['fragment'] ) && '' !== $parts['fragment'] ) {
			$url .= '#' . $parts['fragment'];
		}
		return $url;
	}
}
