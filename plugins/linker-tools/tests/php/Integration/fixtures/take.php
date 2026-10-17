<?php
/**
 * One process taking from a RateLimit: `php take.php <wp root> <name> <limit> <who>`.
 * Prints 1 when the take was allowed, 0 when refused. RateLimitTest starts
 * several of these at once.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

// phpcs:disable WordPress.Security.ValidatedSanitizedInput, WordPress.Security.EscapeOutput -- a command-line fixture.
[ , $linker_tools_root, $linker_tools_name, $linker_tools_limit, $linker_tools_who ] = $argv;
define( 'WP_USE_THEMES', false ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- WordPress's own constant.
$_SERVER['HTTP_HOST']   = 'localhost';
$_SERVER['REQUEST_URI'] = '/';
require_once $linker_tools_root . '/wp-load.php';
echo ( new Linker\Tools\Genie\RateLimit( $linker_tools_name, (int) $linker_tools_limit, HOUR_IN_SECONDS ) )->take( $linker_tools_who ) ? '1' : '0';
