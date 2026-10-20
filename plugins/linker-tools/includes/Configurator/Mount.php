<?php
/**
 * The Solution Configurator's mount point.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Configurator;

/**
 * Prints the page's mount point and loads the built app.
 *
 * The LiveCanvas template of the configurator page prints
 * `[linker_configurator]`; the app is the built entry `build/configurator.js`
 * that Assets registers as `linker-tools-configurator`. The markup carries
 * what the app cannot know server-side — the engine's address, the REST root,
 * a REST nonce, and the size-hint fields already on the address (shape:
 * linker-tools src/configurator/config.ts) — and nothing else: zero design,
 * no word of copy, and the app's own stylesheet sizes and colours it.
 *
 * The engine address the app gets is this plugin's own engine route
 * (Configurator\EngineProxy), not the engine's own URL: the production
 * engine's certificate is self-signed and a browser cannot pin it, while
 * the site's PHP can and does (mu-plugins/linker-engine-pin.php — the same
 * hop the Genie already makes). The engine's own URL lives in the option
 * `linker_engine_url` and is read by the proxy, server-side.
 *
 * It prints on the page it is written into and nowhere else. The page is the
 * one place the tool lives; without this mount the page would keep whatever
 * markup it held before, which is what the old site's planner page did.
 */
final class Mount {

	/**
	 * Script and style handle of the built app (Assets registers one per
	 * entry).
	 */
	public const HANDLE = 'linker-tools-configurator';

	/**
	 * Query keys SizeHint::execute writes, in that order.
	 *
	 * The residential form already has each one (ResidentialForm EMPTY).
	 * This mount only carries a key the address already names. It does not
	 * add keys, and a visit with none of them prints the same mount as before.
	 *
	 * @var list<string>
	 */
	private const SIZE_HINT_KEYS = array( 'pv_kwp', 'annual_kwh', 'phase', 'backup', 'plz' );

	/**
	 * Backup values the residential form accepts. `none` equals EMPTY.
	 *
	 * @var list<string>
	 */
	private const BACKUP = array( 'none', 'needed', 'needed_accessory_ok' );

	/**
	 * Hooks the shortcode; runs during plugin registration.
	 */
	public function register(): void {
		add_shortcode( 'linker_configurator', array( $this, 'shortcode' ) );
	}

	/**
	 * The configurator's mount point.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes (none).
	 */
	public function shortcode( $atts = array() ): string {
		unset( $atts );
		if ( is_admin() ) {
			return '';
		}
		wp_enqueue_script( self::HANDLE );
		wp_enqueue_style( self::HANDLE );

		return sprintf(
			'<div data-linker-app="configurator" data-engine-url="%1$s" data-rest-url="%2$s" data-rest-nonce="%3$s"%4$s></div>',
			esc_attr(
				esc_url_raw(
					rest_url( EngineProxy::NAMESPACE . EngineProxy::ROUTE )
				)
			),
			esc_attr( esc_url_raw( rest_url() ) ),
			esc_attr( wp_create_nonce( 'wp_rest' ) ),
			$this->size_hint_attributes()
		);
	}

	/**
	 * Data attributes for a size-hint address, or an empty string.
	 *
	 * The checks are SizeHint::execute's: a positive number for pv_kwp and
	 * annual_kwh (written with the same `(string) (float)` it uses), phase
	 * `1` or `3`, backup in the residential form's set, a five-digit plz.
	 * phase `3` and backup `none` equal ResidentialForm::EMPTY, so they
	 * are not printed: carrying them would not change the form.
	 */
	private function size_hint_attributes(): string {
		$extra = '';
		foreach ( self::SIZE_HINT_KEYS as $key ) {
			$value = $this->carried( $key, $this->query_value( $key ) );
			if ( null === $value ) {
				continue;
			}
			$extra .= sprintf(
				' data-%s="%s"',
				str_replace( '_', '-', $key ),
				esc_attr( $value )
			);
		}
		return $extra;
	}

	/**
	 * One size-hint query value, or null when the address does not carry it as text.
	 *
	 * A public page address, not a state change: the same keys SizeHint writes.
	 *
	 * @param string $key One of SIZE_HINT_KEYS.
	 */
	private function query_value( string $key ): ?string {
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- display prefill on a public address, not a form action.
		if ( ! isset( $_GET[ $key ] ) || ! is_string( $_GET[ $key ] ) ) {
			return null;
		}
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- same public address; sanitized on this line.
		return sanitize_text_field( wp_unslash( $_GET[ $key ] ) );
	}

	/**
	 * The value to carry, or null when it is absent, invalid, or already the form default.
	 *
	 * @param string      $key One of SIZE_HINT_KEYS.
	 * @param string|null $raw The query value, or null when the address omits it.
	 */
	private function carried( string $key, ?string $raw ): ?string {
		if ( null === $raw || '' === $raw ) {
			return null;
		}
		if ( 'pv_kwp' === $key || 'annual_kwh' === $key ) {
			return $this->positive_number( $raw );
		}
		if ( 'phase' === $key ) {
			// EMPTY phase is '3'. SizeHint only writes '1' or '3'.
			return '1' === $raw ? '1' : null;
		}
		if ( 'backup' === $key ) {
			if ( ! in_array( $raw, self::BACKUP, true ) || 'none' === $raw ) {
				return null;
			}
			return $raw;
		}
		if ( 'plz' === $key && 1 === preg_match( '/^[0-9]{5}$/', $raw ) ) {
			return $raw;
		}
		return null;
	}

	/**
	 * SizeHint's positive-number spelling, or null.
	 *
	 * @param string $raw The query value.
	 */
	private function positive_number( string $raw ): ?string {
		if ( ! is_numeric( $raw ) ) {
			return null;
		}
		$number = (float) $raw;
		if ( ! is_finite( $number ) || $number <= 0 ) {
			return null;
		}
		return (string) $number;
	}
}
