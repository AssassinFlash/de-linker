<?php
/**
 * Independent local database connection for wake-up races and worker contention.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

use Linker\Commerce\Inquiry\Assessment\AsyncRunner;
use Linker\Commerce\Inquiry\Assessment\Lock;
use Linker\Commerce\Inquiry\Assessment\Result;

$linker_commerce_root = getenv( 'LINKER_WP_ROOT' );
if ( false === $linker_commerce_root ) {
	exit( 2 );
}
define( 'WP_USE_THEMES', false ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- Local integration bootstrap.
$_SERVER['HTTP_HOST']   = 'localhost';
$_SERVER['REQUEST_URI'] = '/';
require $linker_commerce_root . '/wp-load.php';
if ( 'local' !== wp_get_environment_type() ) {
	exit( 3 );
}
add_filter( 'action_scheduler_allow_async_request_runner', '__return_false' );
$linker_commerce_id      = (int) ( $argv[1] ?? 0 );
$linker_commerce_token   = (string) ( $argv[2] ?? '' );
$linker_commerce_barrier = (string) ( $argv[3] ?? '' );
$linker_commerce_mode    = (string) ( $argv[4] ?? 'run' );
if ( 'busy' === $linker_commerce_mode ) {
	Lock::run(
		'async-worker',
		static function () use ( $linker_commerce_barrier ): void {
			file_put_contents( $linker_commerce_barrier, 'busy' );
			usleep( 2000000 );
		}
	);
	exit( 0 );
}
add_filter(
	'pre_http_request',
	static function ( $pre, $args, $url ) use ( $linker_commerce_barrier ) {
		if ( ! str_ends_with( $url, '/inquiries/assess' ) ) {
			return $pre;
		}
		file_put_contents( $linker_commerce_barrier, "called\n", FILE_APPEND | LOCK_EX );
		usleep( 2000000 );
		return array(
			'response' => array( 'code' => 200 ),
			'body'     => wp_json_encode( Result::unknown( 'provider_budget_quota' ) ),
		);
	},
	10,
	3
);
echo ( new AsyncRunner() )->run( $linker_commerce_id, $linker_commerce_token ) ? 'claimed' : 'refused';
