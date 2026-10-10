<?php
/**
 * Retired tool entry addresses.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools;

/**
 * Sends the retired tool entry addresses to the Solution Configurator with a
 * permanent redirect (#12: the Site Detail tool folded into the configurator
 * as its roof step, so its addresses no longer have a page of their own; the
 * configurator's own former address was a "has moved" notice page, retired
 * the same way).
 *
 * The live site served the design canvas at /design-canvas/ and, in German,
 * at /de/entwurfsflache/ (its page slug) and /de/design-canvas/ (the old
 * plugin resolved the English slug under /de/ too); the configurator was
 * earlier at /quote-configurator/ (German /de/angebots-konfigurator/), whose
 * pages were interstitial "has moved" notices.
 */
final class Redirects {

	/**
	 * Retired request paths by the configurator page of their language,
	 * without the leading home. The roof-step paths append the step
	 * (docs/specs/12-site-chrome.md item 2: `/linker-planner/?step=roof`);
	 * the configurator's own former address goes to the page itself.
	 */
	private const RETIRED = array(
		'/design-canvas/'            => '/linker-planner/?step=roof',
		'/de/design-canvas/'         => '/de/linker-planer/?step=roof',
		'/de/entwurfsflache/'        => '/de/linker-planer/?step=roof',
		'/quote-configurator/'       => '/linker-planner/',
		'/de/angebots-konfigurator/' => '/de/linker-planer/',
	);

	/**
	 * Adds the plugin's hooks.
	 */
	public function register(): void {
		add_action(
			'template_redirect',
			function (): void {
				$target = $this->target( $this->request_path() );
				if ( null !== $target ) {
					// phpcs:ignore WordPress.Security.SafeRedirect.wp_redirect_wp_redirect -- the target is this site's own home_url(), never visitor input.
					wp_redirect( $target, 301 );
					exit;
				}
			}
		);
	}

	/**
	 * The request path, with one trailing slash, as the site addresses pages.
	 *
	 * @return string The path, '/' when the request names none.
	 */
	private function request_path(): string {
		// phpcs:ignore WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- wp_parse_url() takes the path verbatim; the value only feeds the RETIRED lookup.
		$uri = isset( $_SERVER['REQUEST_URI'] ) ? wp_unslash( $_SERVER['REQUEST_URI'] ) : '/';
		$raw = (string) wp_parse_url( $uri, PHP_URL_PATH );
		return trailingslashit( '' === $raw ? '/' : $raw );
	}

	/**
	 * Where a retired path goes: the address named in the map. Null for
	 * every path that is not retired.
	 *
	 * @param string $path The request path, one trailing slash.
	 * @return string|null The redirect target, null when the path stays.
	 */
	public function target( string $path ): ?string {
		if ( ! isset( self::RETIRED[ $path ] ) ) {
			return null;
		}
		return home_url( self::RETIRED[ $path ] );
	}
}
