<?php
/**
 * Isolated WordPress boundary doubles for the credential-scope unit test.
 * The integration fixture exercises these hooks with native WordPress types.
 *
 * @package Linker\Mu
 */

declare( strict_types = 1 );

// phpcs:disable WordPress.NamingConventions.PrefixAllGlobals, WordPress.WP.AlternativeFunctions -- isolated process doubles for WordPress's public hook boundary.
// phpcs:disable WooCommerce.Commenting.CommentHooks -- invokes existing core hooks in a boundary double, not new product hooks.

/**
 * Hooks registered by the actual module.
 *
 * @var array<string, array<int, list<callable>>> $linker_worker_hooks
 */
$linker_worker_hooks = array();

/**
 * WordPress's action registration boundary.
 *
 * @param string   $hook Hook name.
 * @param callable $callback Native listener.
 * @param int      $priority Native priority.
 * @param int      $accepted_args Native arity.
 */
function add_action( string $hook, callable $callback, int $priority = 10, int $accepted_args = 1 ): void {
	add_filter( $hook, $callback, $priority, $accepted_args );
}

/**
 * WordPress's filter registration boundary.
 *
 * @param string   $hook Hook name.
 * @param callable $callback Native listener.
 * @param int      $priority Native priority.
 * @param int      $accepted_args Native arity.
 */
function add_filter( string $hook, callable $callback, int $priority = 10, int $accepted_args = 1 ): void {
	global $linker_worker_hooks;
	unset( $accepted_args );
	$linker_worker_hooks[ $hook ][ $priority ][] = $callback;
}

/**
 * Runs registered hooks in WordPress priority order.
 *
 * @param string $hook Hook name.
 * @param mixed  $value Initial value.
 * @param mixed  ...$arguments Native listener arguments.
 */
function apply_filters( string $hook, mixed $value, mixed ...$arguments ): mixed {
	global $linker_worker_hooks;
	$callbacks = $linker_worker_hooks[ $hook ] ?? array();
	ksort( $callbacks );
	foreach ( $callbacks as $priority ) {
		foreach ( $priority as $callback ) {
			$value = $callback( $value, ...$arguments );
		}
	}
	return $value;
}

/**
 * The untranslated native generic refusal.
 *
 * @param string $message Native message.
 */
function __( string $message ): string {
	return $message;
}

/**
 * WordPress error detection boundary.
 *
 * @param mixed $value The candidate native error.
 * @phpstan-assert-if-true WP_Error $value
 * @phpstan-assert-if-false !WP_Error $value
 */
function is_wp_error( mixed $value ): bool {
	return $value instanceof WP_Error;
}

class_alias(
	get_class(
		new class() {
			/**
			 * Native user ID.
			 *
			 * @var int
			 */
			public int $ID = 7;
		}
	),
	'WP_User'
);
class_alias(
	get_class(
		new class() {
			/**
			 * Error code.
			 *
			 * @var string
			 */
			public string $code = '';

			/**
			 * Native error construction.
			 *
			 * @param string $code Native error code.
			 */
			public function __construct( string $code = '' ) {
				$this->code = $code;
			}

			/**
			 * The native mutable-error hook boundary.
			 *
			 * @param string $code Error code.
			 * @param string $message Error message.
			 * @param mixed  $data Error data.
			 */
			public function add( string $code, string $message, mixed $data = null ): void {
				unset( $message, $data );
				$this->code = $code;
			}

			/** Native error code. */
			public function get_error_code(): string {
				return $this->code;
			}
		}
	),
	'WP_Error'
);
class_alias( get_class( new class() {} ), 'WP_REST_Server' );
class_alias(
	get_class(
		new class() {
			/**
			 * Effective request method.
			 *
			 * @var string
			 */
			private string $method;

			/**
			 * Effective request route.
			 *
			 * @var string
			 */
			private string $route;

			/**
			 * Effective parameters.
			 *
			 * @var array<string, mixed>
			 */
			private array $params = array();

			/**
			 * Effective headers.
			 *
			 * @var array<string, string>
			 */
			private array $headers = array();

			/**
			 * A native REST request boundary double.
			 *
			 * @param string $method Effective method.
			 * @param string $route Effective route.
			 */
			public function __construct( string $method = 'POST', string $route = '/linker-test/v1/write' ) {
				$this->method = $method;
				$this->route  = $route;
			}

			/**
			 * Native query parameters.
			 *
			 * @param array<string, mixed> $params Parameters.
			 */
			public function set_query_params( array $params ): void {
				$this->params = $params;
			}

			/**
			 * Native headers.
			 *
			 * @param array<string, string> $headers Headers.
			 */
			public function set_headers( array $headers ): void {
				$this->headers = $headers;
			}

			/** Effective method. */
			public function get_method(): string {
				return $this->method;
			}

			/** Effective route. */
			public function get_route(): string {
				return $this->route;
			}

			/**
			 * Effective parameter presence.
			 *
			 * @param string $name Parameter name.
			 */
			public function has_param( string $name ): bool {
				return array_key_exists( $name, $this->params );
			}

			/**
			 * Effective header presence.
			 *
			 * @param string $name Header name.
			 */
			public function get_header( string $name ): ?string {
				return $this->headers[ $name ] ?? null;
			}
		}
	),
	'WP_REST_Request'
);

define( 'ABSPATH', __DIR__ );
$linker_worker_config = json_decode( stream_get_contents( STDIN ), true, 512, JSON_THROW_ON_ERROR );
define( 'REST_REQUEST', $linker_worker_config['rest'] ?? true );
$_SERVER['REQUEST_METHOD'] = $linker_worker_config['raw_method'] ?? 'POST';
$_GET                      = $linker_worker_config['query'] ?? array();
$_POST                     = $linker_worker_config['body'] ?? array();
$_SERVER                   = array_merge( $_SERVER, $linker_worker_config['server'] ?? array() );
require dirname( __DIR__, 3 ) . '/linker-publication-worker-access.php';

$linker_worker_user  = new WP_User();
$linker_worker_item  = array(
	'app_id' => $linker_worker_config['app_id'] ?? '6c50fdd8-1640-4d5e-9ac8-05fefd9aa290',
	'uuid'   => '73868f2f-9f95-4dd2-ab5f-cfd2ab655167',
);
$linker_worker_error = new WP_Error();
if ( $linker_worker_config['verified'] ?? true ) {
	apply_filters( 'wp_authenticate_application_password_errors', $linker_worker_error, $linker_worker_user, $linker_worker_item );
}
if ( '' !== $linker_worker_error->get_error_code() && ! ( $linker_worker_config['late_failure'] ?? false ) ) {
	echo json_encode(
		array(
			'authentication_denied' => true,
			'denied'                => array(),
			'writes'                => 0,
		),
		JSON_THROW_ON_ERROR
	);
	exit;
}
if ( $linker_worker_config['native_success'] ?? true ) {
	apply_filters( 'application_password_did_authenticate', $linker_worker_user, $linker_worker_item );
}
if ( $linker_worker_config['http_authentication'] ?? true ) {
	apply_filters( 'rest_authentication_errors', true );
}
// ACF's priority-10 initialization deliberately returns null.
add_filter(
	'rest_pre_dispatch',
	static function ( mixed $result, mixed $server, mixed $request ): mixed {
		unset( $result, $server, $request );
		return null;
	},
	10,
	3
);
$linker_worker_denied = array();
$linker_worker_writes = 0;
foreach ( $linker_worker_config['requests'] ?? array( array( 'route' => '/linker-test/v1/write' ) ) as $linker_worker_request ) {
	if ( $linker_worker_request['reauthenticate'] ?? false ) {
		apply_filters( 'rest_authentication_errors', true );
	}
	$linker_worker_effective = new WP_REST_Request( $linker_worker_request['method'] ?? 'POST', $linker_worker_request['route'] );
	$linker_worker_effective->set_query_params( $linker_worker_request['params'] ?? array() );
	$linker_worker_effective->set_headers( $linker_worker_request['headers'] ?? array() );
	$linker_worker_result   = apply_filters( 'rest_pre_dispatch', null, new WP_REST_Server(), $linker_worker_effective );
	$linker_worker_denied[] = $linker_worker_result instanceof WP_Error;
	if ( ! $linker_worker_result instanceof WP_Error ) {
		++$linker_worker_writes;
	}
}
echo json_encode(
	array(
		'authentication_denied' => false,
		'denied'                => $linker_worker_denied,
		'writes'                => $linker_worker_writes,
	),
	JSON_THROW_ON_ERROR
);
