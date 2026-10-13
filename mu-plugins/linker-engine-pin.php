<?php
/**
 * Plugin Name: Linker engine certificate pin
 * Description: Pins the services VPS's self-signed TLS certificate on the site's server-to-server calls to the engine and the Genie, exactly as the plugin the switch replaced did (`pin_certificate`, linker-ai-assistant). Without it wp_remote_post verifies against the public CA bundle and every call to https://72.62.97.95:8443 fails ("Genie did not answer", measured 2026-10-14).
 *
 * The certificate beside this file, wp-content/mu-plugins/linker-engine-ca.pem,
 * ships with the repository (`mu-plugins/linker-engine-ca.pem`) and is replaced
 * with the engine host's own `/etc/linker-engine/engine.crt`. A NAMED host is left
 * alone: a name can hold a publicly trusted certificate (Let's Encrypt on a
 * subdomain whose DNS is managed outside this repository), and the day the engine
 * moves behind one this pin steps aside instead of rejecting it.
 *
 * @package Linker
 */

declare( strict_types = 1 );

defined( 'ABSPATH' ) || exit;

/**
 * Adds the pinned certificate to every server-to-server call whose URL starts
 * with one of the two service addresses.
 *
 * `sslverify` stays true: the call is verified, against the pinned certificate
 * rather than the public bundle — a pin, not a downgrade.
 */
add_filter(
	'http_request_args',
	static function ( array $args, string $url ): array {
		$pem = __DIR__ . '/linker-engine-ca.pem';
		if ( ! is_readable( $pem ) ) {
			return $args;
		}
		foreach ( array( 'linker_genie_url', 'linker_engine_url' ) as $option ) {
			$base = (string) get_option( $option, '' );
			if ( '' === $base || ! str_starts_with( $url, rtrim( $base, '/' ) ) ) {
				continue;
			}
			$host = (string) wp_parse_url( $base, PHP_URL_HOST );
			if ( '' === $host || ! filter_var( $host, FILTER_VALIDATE_IP ) ) {
				continue;
			}
			$args['sslverify']       = true;
			$args['sslcertificates'] = $pem;
		}
		return $args;
	},
	10,
	2
);
