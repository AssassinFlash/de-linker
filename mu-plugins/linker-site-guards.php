<?php
/**
 * Plugin Name: Linker site guards
 * Description: The public site's security baseline: the response headers, and the closed REST user list.
 *
 * A must-use plugin: the headers and the guard are properties of the site
 * itself, and they must hold while a regular plugin is being activated,
 * updated or broken.
 *
 * @package Linker\Platform
 */

declare( strict_types = 1 );

/**
 * The security headers every response carries, before any output.
 *
 * HSTS asks for one year and includes subdomains; the host serves HTTPS for
 * this domain only, so the two other headers are the site's own policy:
 * nothing frames the shop, and browsers keep the declared content types and
 * the referrer's origin.
 */
function linker_site_guards_headers(): void {
	if ( headers_sent() ) {
		return;
	}
	header( 'Strict-Transport-Security: max-age=31536000; includeSubDomains' );
	header( 'X-Frame-Options: SAMEORIGIN' );
	header( 'X-Content-Type-Options: nosniff' );
	header( 'Referrer-Policy: strict-origin-when-cross-origin' );
}
add_action( 'send_headers', 'linker_site_guards_headers', 1 );

/**
 * Keeps the REST user list closed to everyone but the people who may list
 * users: anonymous `/wp/v2/users` enumerates login names, which is the first
 * half of a password attack.
 *
 * @param mixed          $result  The pre-dispatch result, untouched unless this guard refuses.
 * @param WP_REST_Server $server  The server handling the request.
 * @param mixed          $request The request being dispatched (checked below: the filter's shape is wp-includes' to keep, not this guard's to trust).
 * @return mixed
 */
function linker_site_guards_rest_users( $result, $server, $request ) {
	unset( $server );
	if ( ! $request instanceof WP_REST_Request ) {
		return $result;
	}
	if ( preg_match( '#^/wp/v2/users(?:/|$)#i', $request->get_route() ) && ! current_user_can( 'list_users' ) ) {
		return new WP_Error( 'rest_forbidden', 'Access denied.', array( 'status' => 403 ) );
	}
	return $result;
}
add_filter( 'rest_pre_dispatch', 'linker_site_guards_rest_users', 10, 3 );
