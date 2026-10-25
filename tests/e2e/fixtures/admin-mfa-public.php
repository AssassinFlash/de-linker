<?php
/**
 * Explicit local-only provider substitution for #565 Computer Use acceptance.
 *
 * Include through a temporary instance MU loader defining the exact owned root
 * and a private mode file. Never present/deploy this fixture. Native identity,
 * prepare/verify, ledger, preflight, reservation, dispatch and storage stay real.
 *
 * @package Linker\Commerce
 */

if ( ! defined( 'LINKER_MFA_PUBLIC_FIXTURE_ROOT' ) || ! defined( 'LINKER_MFA_PUBLIC_FIXTURE_MODE' )
	|| ! defined( 'LINKER_LOCAL_MAIL_DIR' ) || 'local' !== wp_get_environment_type()
	|| realpath( ABSPATH ) !== realpath( LINKER_MFA_PUBLIC_FIXTURE_ROOT )
	|| '127.0.0.1' !== wp_parse_url( home_url(), PHP_URL_HOST ) ) {
	return;
}
( static function (): void {
	foreach ( array(
		'LINKER_PUBLIC_PROTECTION_MODE' => 'enforce',
		'LINKER_BUSINESS_VERIFICATION'  => 'required',
		'LINKER_TURNSTILE_SITE_KEY'     => '1x00000000000000000000AA',
		'LINKER_TURNSTILE_SECRET_KEY'   => '1x0000000000000000000000000000000AA',
		'LINKER_TURNSTILE_HOSTNAME'     => 'dummy-key-pass',
	) as $name => $value ) {
		if ( defined( $name ) ) {
			throw new RuntimeException( 'Refuse to replace an existing private verification configuration.' );
		}
		// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.VariableConstantNameFound -- Native private configuration names, isolated to this explicit local fixture.
		define( $name, $value );
	}
	// No classifier/model dispatch in this synthetic authentication exercise.
	add_filter( 'pre_option_linker_inquiry_assessment_enabled', static fn() => 'no' );
	add_filter(
		'pre_http_request',
		static function ( $pre, $args, $url ) {
			if ( false !== $pre || 'https://challenges.cloudflare.com/turnstile/v0/siteverify' !== $url ) {
				return $pre;
			}
			if ( '1x0000000000000000000000000000000AA' !== ( $args['body']['secret'] ?? '' ) ) {
				return new WP_Error( 'fixture_wrong_key', 'Synthetic key required.' );
			}
			$mode = trim( file_get_contents( LINKER_MFA_PUBLIC_FIXTURE_MODE ) );
			if ( 'outage' === $mode ) {
				return new WP_Error( 'fixture_outage', 'Synthetic local verification outage.' );
			}
			$input = json_decode( file_get_contents( 'php://input' ), true );
			return array(
				'response' => array( 'code' => 200 ),
				'body'     => wp_json_encode(
					array(
						'success'  => true,
						'hostname' => 'dummy-key-pass',
						'action'   => $input['action'] ?? '',
					)
				),
			);
		},
		PHP_INT_MAX - 1,
		3
	);
	add_action(
		'wp_head',
		static function () {
			// Only the challenge SDK is synthetic; the real form client still obtains
			// and submits a server-signed native proof from same-origin REST.
			echo '<script>window.turnstile={render:function(el,opts){queueMicrotask(function(){opts.callback("mfa565_"+opts.action+"_"+crypto.randomUUID());});return "mfa565";},remove:function(){}};</script>';
		},
		0
	);
} )();
