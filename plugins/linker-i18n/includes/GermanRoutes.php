<?php
/**
 * German aliases using the existing native rewrite and permalink pipeline.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n;

/** German bases and paging without changing global English settings. */
final class GermanRoutes {

	/**
	 * Native language access stays behind the shared Polylang door.
	 *
	 * @param Languages $languages Shared language and translation access.
	 */
	public function __construct( private readonly Languages $languages = new Languages() ) {}

	/**
	 * Preserve each translated endpoint in native language alternates.
	 *
	 * @param array<string,string> $urls Native language alternates.
	 * @return array<string,string>
	 */
	public function hreflangs( array $urls ): array {
		if ( get_option( GermanUrlMigration::ACTIVE ) ) {
			foreach ( $urls as &$url ) {
				$url = $this->endpoint_url( $url );
			}
			unset( $url );
		}
		return $urls;
	}

	/**
	 * Append the native endpoint only to a translated account or confirmation root.
	 *
	 * @param string $url Native translated page URL.
	 */
	private function endpoint_url( string $url ): string {
		if ( ! is_account_page() && ! is_wc_endpoint_url( 'order-received' ) ) {
			return $url;
		}
		$key = WC()->query->get_current_endpoint();
		if ( '' === $key ) {
			return $url;
		}
		$option = 'order-received' === $key ? 'woocommerce_checkout_page_id' : 'woocommerce_myaccount_page_id';
		$path   = wp_parse_url( $url, PHP_URL_PATH );
		// Both Polylang filters can see this link; append only to the page root.
		if ( ! in_array( $path, array( $this->page_path( $option, 'en' ), $this->page_path( $option, 'de' ) ), true ) ) {
			return $url;
		}
		return wc_get_endpoint_url( $key, (string) get_query_var( $key ), $url );
	}

	/** Native Woo address types retain their internal names. */
	private const ADDRESSES = array(
		'billing'  => 'rechnungsadresse',
		'shipping' => 'lieferadresse',
	);

	/**
	 * Uses Woo's native address translation seam in German requests.
	 *
	 * @param array<string,string> $slugs Native translated address slugs.
	 * @return array<string,string>
	 */
	public function addresses( array $slugs ): array {
		return get_option( GermanUrlMigration::ACTIVE ) && 'de' === $this->languages->current() ? self::ADDRESSES : $slugs;
	}

	/** Public path vocabulary; Woo's internal query keys are unchanged. */
	public const ENDPOINTS = array(
		'register'         => 'registrieren',
		'lost-password'    => 'passwort-zuruecksetzen',
		'inquiries'        => 'anfragen',
		'inquiry'          => 'anfrage',
		'saved-solutions'  => 'gespeicherte-loesungen',
		'documents'        => 'dokumente',
		'company'          => 'unternehmen',
		'edit-account'     => 'kontodaten',
		'customer-logout'  => 'abmelden',
		'inquiry-received' => 'anfrage-eingegangen',
	);

	/** Native pagination recognises the translated base before building links. */
	public function pagination(): void {
		if ( get_option( GermanUrlMigration::ACTIVE ) && 'de' === $this->languages->current() ) {
			global $wp_rewrite;
			$wp_rewrite->pagination_base = 'seite';
		}
	}

	/**
	 * Polylang has no translation URL for an unknown page.
	 *
	 * @param string|null $url Native language-switch destination.
	 */
	public function translation_url( ?string $url ): ?string {
		if ( null === $url || ! get_option( GermanUrlMigration::ACTIVE ) ) {
			return $url;
		}
		$url = $this->endpoint_url( $url );
		// Polylang resolves the translated archive identity without its page number.
		$page = (int) get_query_var( 'paged' );
		if ( $page > 1 ) {
			$parts = preg_split( '/(?=[?#])/', $url, 2 );
			$base  = (string) preg_replace( '#/(?:page|seite)/[0-9]+/?$#', '/', $parts[0] ?? $url );
			$url   = trailingslashit( $base ) . 'page/' . $page . '/' . ( $parts[1] ?? '' );
		}
		return $this->link( $url );
	}

	/**
	 * Applies German bases to links already resolved to German objects.
	 *
	 * @param string $url Native permalink.
	 */
	public function link( string $url ): string {
		if ( ! get_option( GermanUrlMigration::ACTIVE ) ) {
			return $url;
		}
		return $this->translated_link( $url );
	}

	/**
	 * Resolves native path vocabulary without enabling migration state during a preview.
	 *
	 * @param string $url Native absolute URL.
	 */
	private function translated_link( string $url ): string {
		$home = untrailingslashit( $this->languages->home_url( 'en' ) );
		if ( ! str_starts_with( $url, $home . '/' ) ) {
			return $url;
		}
		$parts  = preg_split( '/(?=[?#])/', substr( $url, strlen( $home ) ), 2 );
		$path   = is_array( $parts ) ? $parts[0] : '';
		$german = str_starts_with( $path, '/de/' );
		if ( $german ) {
			$path = (string) preg_replace( '#^/de/category/#', '/de/kategorie/', $path );
			$path = (string) preg_replace( '#/page/([0-9]+)(/|$)#', '/seite/$1$2', $path );
		} else {
			$path = (string) preg_replace( '#/seite/([0-9]+)(/|$)#', '/page/$1$2', $path );
		}
		foreach ( array( 'woocommerce_myaccount_page_id', 'woocommerce_checkout_page_id' ) as $option ) {
			$base = $this->page_path( $option, $german ? 'de' : 'en' );
			if ( '' === $base || ! str_starts_with( $path, $base ) ) {
				continue;
			}
			$segments    = explode( '/', substr( $path, strlen( $base ) ) );
			$map         = $german ? self::ENDPOINTS : array_flip( self::ENDPOINTS );
			$segments[0] = $map[ $segments[0] ] ?? $segments[0];
			if ( in_array( $segments[0], array( 'company', 'unternehmen' ), true ) && isset( $segments[1] ) ) {
				$addresses   = $german ? self::ADDRESSES : array_flip( self::ADDRESSES );
				$segments[1] = $addresses[ $segments[1] ] ?? $segments[1];
			}
			$path = $base . implode( '/', $segments );
		}
		return $home . $path . ( $parts[1] ?? '' );
	}

	/**
	 * Desired path for a reviewed native German object, also available in previews.
	 *
	 * @param string $url Current absolute or root-relative German URL.
	 */
	public function desired( string $url ): string {
		$home     = untrailingslashit( $this->languages->home_url( 'en' ) );
		$relative = str_starts_with( $url, '/de/' );
		if ( $relative ) {
			$url = $home . $url;
		}
		if ( ! str_starts_with( $url, $home . '/de/' ) ) {
			return $url;
		}
		$parts    = preg_split( '/(?=[?#])/', substr( $url, strlen( $home ) ), 2 );
		$segments = explode( '/', is_array( $parts ) ? $parts[0] : '' );
		foreach ( $segments as &$segment ) {
			$segment = match ( $segment ) {
				'category' => 'kategorie', 'page' => 'seite', default => GermanSlugs::translated( $segment ) };
		}
		unset( $segment );
		$translated = $this->translated_link( $home . implode( '/', $segments ) . ( $parts[1] ?? '' ) );
		return $relative ? substr( $translated, strlen( $home ) ) : $translated;
	}

	/**
	 * Rewrites whole URL references without altering external hosts or opaque queries.
	 *
	 * @param string $content German HTML, text or embedded navigation strings.
	 */
	public function rewrite_links( string $content ): string {
		return (string) preg_replace_callback(
			'~https?://[^\s"\'<>]+|(?<![a-zA-Z0-9:/])/de/[^\s"\'<>]*~',
			fn( array $reference ): string => $this->desired( $reference[0] ),
			$content
		);
	}

	/**
	 * Adds aliases using Woo's existing query keys and native pagination rules.
	 *
	 * @param array<string,string> $rules Existing rules.
	 * @return array<string,string>
	 */
	public function rules( array $rules ): array {
		if ( ! get_option( GermanUrlMigration::ACTIVE ) ) {
			return $rules;
		}
		$aliases = array();
		foreach ( $rules as $rule => $target ) {
			if ( ( str_starts_with( $rule, 'de/' ) || str_starts_with( $rule, '(de)/' ) ) && str_contains( $rule, '/page/' ) ) {
				$aliases[ str_replace( '/page/', '/seite/', $rule ) ] = $target;
			}
		}
		foreach ( WC()->query->get_query_vars() as $key => $slug ) {
			if ( ! isset( self::ENDPOINTS[ $slug ] ) ) {
				continue;
			}
			$option = 'order-received' === $key ? 'woocommerce_checkout_page_id' : 'woocommerce_myaccount_page_id';
			$base   = $this->page_path( $option, 'de' );
			if ( '' !== $base ) {
				$aliases[ preg_quote( trim( $base, '/' ), '#' ) . '/' . self::ENDPOINTS[ $slug ] . '(?:/([^/]+))?/?$' ] = 'index.php?pagename=' . substr( trim( $base, '/' ), 3 ) . '&' . $slug . '=$matches[1]&lang=de';
			}
		}
		return array(
			'de/kategorie/(.+?)/seite/?([0-9]{1,})/?$' => 'index.php?category_name=$matches[1]&paged=$matches[2]&lang=de',
			'de/kategorie/(.+?)/?$'                    => 'index.php?category_name=$matches[1]&lang=de',
		) + $aliases + $rules;
	}

	/**
	 * Native page identity in a language, independent of its current slug.
	 *
	 * @param string $option Woo page option.
	 * @param string $language Language slug.
	 */
	private function page_path( string $option, string $language ): string {
		$id  = (int) $this->languages->post_translation( (int) get_option( $option ), $language );
		$uri = $id > 0 ? get_page_uri( $id ) : false;
		return is_string( $uri ) ? ( 'de' === $language ? '/de/' : '/' ) . trim( $uri, '/' ) . '/' : '';
	}

	/**
	 * Canonicalises retired endpoint and pagination aliases before Woo dispatch.
	 *
	 * @param string $path Requested full path.
	 */
	public function endpoint_history( string $path ): ?string {
		$home = untrailingslashit( $this->languages->home_url( 'en' ) );
		$url  = $this->link( $home . $path );
		return $url === $home . $path ? null : ( new GermanUrlMigration() )->old_url( $url );
	}

	/**
	 * Resolves current and previously broken category addresses by German term.
	 *
	 * @param string $path Requested path.
	 */
	public function category_history( string $path ): ?string {
		if ( 1 !== preg_match( '#^/de/category/([^/]+)/(.*)$#', $path, $match ) ) {
			return null;
		}
		$slug  = 'uberwachung-energiemanagement' === $match[1] ? 'ueberwachung-energiemanagement' : GermanSlugs::translated( $match[1] );
		$terms = get_terms(
			array(
				'taxonomy'   => 'category',
				'lang'       => 'de',
				'slug'       => $slug,
				'hide_empty' => false,
			)
		);
		if ( is_wp_error( $terms ) || array() === $terms ) {
			return null;
		}
		$url = get_term_link( $terms[0] );
		return is_string( $url ) ? ( new GermanUrlMigration() )->old_url( $this->link( $url . $match[2] ) ) : null;
	}
}
