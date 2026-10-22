<?php
/**
 * An isolated PHP connection for release/crash fixtures; local instances only.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

register_shutdown_function(
	static function (): void {
		$error = error_get_last();
		if ( null !== $error && in_array( $error['type'], array( E_ERROR, E_PARSE, E_CORE_ERROR, E_COMPILE_ERROR ), true ) ) {
			fwrite( STDERR, $error['message'] . ' in ' . $error['file'] . ':' . $error['line'] );
		}
	}
);

$linker_commerce_root = getenv( 'LINKER_WP_ROOT' );
if ( false === $linker_commerce_root ) {
	exit( 2 );
}
define( 'WP_USE_THEMES', false ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- Same local CLI bootstrap as the integration suite.
$_SERVER['HTTP_HOST']   = 'localhost';
$_SERVER['REQUEST_URI'] = '/';
require $linker_commerce_root . '/wp-load.php';
if ( 'local' !== wp_get_environment_type() ) {
	exit( 3 );
}
add_filter( 'action_scheduler_allow_async_request_runner', '__return_false' );
$linker_commerce_id      = (int) ( $argv[1] ?? 0 );
$linker_commerce_barrier = (string) ( $argv[2] ?? '' );
$linker_commerce_mode    = (string) ( $argv[3] ?? 'finish' );
require_once __DIR__ . '/AssessmentFixtureEnvironment.php';
require_once __DIR__ . '/NormalMailAuthorizationFixture.php';
\Linker\Commerce\Tests\Fixtures\AssessmentFixtureEnvironment::configure();
add_filter(
	'pre_http_request',
	static function ( $pre, $args, $url ) {
		if ( ! str_ends_with( $url, '/inquiries/assess' ) ) {
			return $pre; }
		$request = json_decode( $args['body'], true );
		return array(
			'response' => array( 'code' => 200 ),
			'body'     => wp_json_encode( \Linker\Commerce\Tests\Fixtures\NormalMailAuthorizationFixture::verdict( $request['binding'] ) ),
		);
	},
	10,
	3
);
$linker_commerce_queue = new \Linker\Commerce\Inquiry\Assessment\Queue();
try {
	if ( 'hold' === $linker_commerce_mode || 'crash' === $linker_commerce_mode ) {
		\Linker\Commerce\Inquiry\Assessment\Lock::run(
			'send-process-' . $linker_commerce_id,
			static function () use ( $linker_commerce_barrier, $linker_commerce_mode, $linker_commerce_queue, $linker_commerce_id ): void {
				file_put_contents( $linker_commerce_barrier, 'locked' );
				if ( 'crash' === $linker_commerce_mode ) {
					exit( 0 ); // The DB connection dies without a notification handoff.
				}
				usleep( 2000000 ); // Deliberately overlap two real PHP connections.
				$linker_commerce_queue->process( $linker_commerce_id );
			}
		);
	} else {
		$linker_commerce_queue->process( $linker_commerce_id );
	}
} catch ( \Throwable $linker_commerce_error ) {
	fwrite( STDERR, get_class( $linker_commerce_error ) . ': ' . $linker_commerce_error->getMessage() . ' in ' . $linker_commerce_error->getFile() . ':' . $linker_commerce_error->getLine() );
	exit( 4 );
}
