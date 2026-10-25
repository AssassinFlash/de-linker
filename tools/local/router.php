<?php
/**
 * Router of PHP's built-in web server for a local instance
 * (`php -S 127.0.0.1:<port> -t <docroot> router.php`, started by linker-local).
 *
 * It does what the rewrite rules of the production server do: an existing
 * file is served as it is (a PHP file is run), a directory is addressed with a
 * trailing slash, and every other path goes to WordPress's index.php.
 *
 * @package Linker\Local
 */

declare( strict_types = 1 );

// phpcs:disable WordPress.Security.ValidatedSanitizedInput -- the router only maps the request path to a file; WordPress is not loaded yet.
$linker_local_root = (string) $_SERVER['DOCUMENT_ROOT'];
// phpcs:ignore WordPress.WP.AlternativeFunctions.parse_url_parse_url -- WordPress (wp_parse_url) is not loaded yet.
$linker_local_path = rawurldecode( (string) parse_url( (string) $_SERVER['REQUEST_URI'], PHP_URL_PATH ) );
$linker_local_file = $linker_local_root . $linker_local_path;

// A path that climbs out of the document root is not a WordPress URL.
if ( str_contains( $linker_local_path, '/..' ) ) {
	http_response_code( 400 );
	return true;
}

// As Apache's mod_dir does: /wp-admin becomes /wp-admin/.
if ( is_dir( $linker_local_file ) && ! str_ends_with( $linker_local_path, '/' ) ) {
	$linker_local_query = (string) ( $_SERVER['QUERY_STRING'] ?? '' );
	header( 'Location: ' . $linker_local_path . '/' . ( '' === $linker_local_query ? '' : '?' . $linker_local_query ), true, 301 );
	return true;
}
// phpcs:enable

// Match the production technical-document gate before the static-file shortcut.
// Private reports still stream through their logged-in owner routes.
if ( preg_match( '#^/wp-content/uploads/(.+\\.pdf)$#iD', $linker_local_path, $linker_local_pdf ) ) {
	$_GET['linker_public_document'] = $linker_local_pdf[1];
	chdir( $linker_local_root );
	require $linker_local_root . '/index.php';
	return true;
}

if ( is_file( $linker_local_file ) || is_file( $linker_local_file . 'index.php' ) ) {
	return false;
}

chdir( $linker_local_root );
require $linker_local_root . '/index.php';
