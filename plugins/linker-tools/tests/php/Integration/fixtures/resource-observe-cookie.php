<?php
/**
 * Real headers-sent/cookie failure; shadow admission retains native validation.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

require dirname( __DIR__, 2 ) . '/integration-bootstrap.php';
putenv( 'LINKER_PUBLIC_PROTECTION_MODE=observe' ); // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.runtime_configuration_putenv -- Process-local synthetic mode only.
rest_get_server();
unset( $_COOKIE[ \Linker\Commerce\Protection\Identity::COOKIE ] );
echo "synthetic-headers-sent\n";
$linker_tools_cookie_failed = is_wp_error( \Linker\Commerce\Protection\Identity::current() );
$linker_tools_request       = new WP_REST_Request( 'POST', '/linker-ai/v1/genie/turn' );
$linker_tools_calls         = 0;
$linker_tools_callback      = static function () use ( &$linker_tools_calls ): WP_Error {
	++$linker_tools_calls;
	return new WP_Error( 'native_validation', 'Synthetic native refusal.', array( 'status' => 400 ) );
};
$linker_tools_advisory      = ( new \Linker\Tools\Protection\Resources() )->dispatch( null, $linker_tools_request, '', array( 'callback' => $linker_tools_callback ) );
$linker_tools_reply         = null === $linker_tools_advisory ? $linker_tools_callback() : $linker_tools_advisory;
echo wp_json_encode(
	array(
		'cookie_failed' => $linker_tools_cookie_failed,
		'calls'         => $linker_tools_calls,
		'code'          => $linker_tools_reply instanceof WP_Error ? $linker_tools_reply->get_error_code() : 'unexpected',
	)
); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- CLI JSON fixture, no HTML.
