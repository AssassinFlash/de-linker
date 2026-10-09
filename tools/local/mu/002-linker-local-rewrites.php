<?php
/**
 * Plugin Name: Linker local rewrites
 * Description: Tells WordPress that the local server rewrites URLs, as production's does.
 *
 * WordPress asks got_url_rewrite() whether the server rewrites URLs; under
 * PHP's built-in server the answer is no, and Settings → Permalinks then
 * offers every structure with /index.php/ in front, which would move every
 * URL away from production's. The local server does rewrite (tools/local/router.php),
 * as LiteSpeed does in production.
 *
 * Copied into wp-content/mu-plugins by linker-local (tools/local); never deployed.
 *
 * @package Linker\Local
 */

declare( strict_types = 1 );

defined( 'ABSPATH' ) || exit;

add_filter( 'got_url_rewrite', '__return_true' );
