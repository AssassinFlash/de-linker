<?php
/**
 * PROTOTYPE — throwaway (map #220, owner 2026-10-17: try Knocket locally and review it).
 *
 * Only on the local instance and only with ?knocket=1: loosens the local isolation CSP
 * for that one response so Knocket's script and connections load, prints the owner's
 * install snippet right before </body> as Knocket instructs, and hides Genie's launcher
 * so the page shows Knocket alone. Never shipped; the live site is untouched.
 *
 * @package Linker\Prototype
 */

defined( 'ABSPATH' ) || exit;

if ( isset( $_GET['knocket'] ) && ! is_admin() ) { // phpcs:ignore -- prototype.
	header( "Content-Security-Policy: default-src 'self' http://127.0.0.1:* https: wss: data: blob: 'unsafe-inline' 'unsafe-eval'", true );
	add_action(
		'wp_footer',
		static function (): void {
			echo '<style>.linker-genie{display:none!important}</style>';
			echo '<script src="https://trtc.io/knocket-sdk/sdk.js?identifier=f145fd3b67d64f4704&v=1792224006909" async></script>'; // the owner's snippet, verbatim
		},
		9999
	);
}
