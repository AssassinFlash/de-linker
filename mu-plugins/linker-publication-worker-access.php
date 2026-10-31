<?php
/**
 * Plugin Name: Linker publication worker credential scope
 * Description: Limits the native publication-purpose application password to leased worker operations.
 *
 * @package Linker\Mu
 */

declare( strict_types = 1 );

namespace Linker\Mu;

use WP_Error;
use WP_REST_Request;
use WP_REST_Server;
use WP_User;

defined( 'ABSPATH' ) || exit;

/** Request-local scope of a native application-password identity. */
final class PublicationWorkerAccess {

	/** The non-secret native application-password purpose, shared by both workers. */
	public const APP_ID = '6c50fdd8-1640-4d5e-9ac8-05fefd9aa290';

	/**
	 * Core verified this purpose's password/user/item, even if later auth fails.
	 *
	 * @var bool
	 */
	private bool $restricted = false;

	/**
	 * Core accepted the native application identity through its success hook.
	 *
	 * @var bool
	 */
	private bool $authenticated = false;

	/**
	 * A native HTTP authentication check permits one top-level dispatch.
	 *
	 * @var bool
	 */
	private bool $http_dispatch_available = false;

	/**
	 * Internal requests cannot renew a consumed HTTP permission.
	 *
	 * @var bool
	 */
	private bool $dispatched = false;

	/** Registers before regular plugins can ask for the current user. */
	public function register(): void {
		add_action( 'wp_authenticate_application_password_errors', array( $this, 'authentication_errors' ), 10, 3 );
		add_action( 'application_password_did_authenticate', array( $this, 'authenticated' ), 10, 2 );
		// Core checks application passwords at 90 and cookies at 100.
		add_filter( 'rest_authentication_errors', array( $this, 'http_authenticated' ), 110 );
		// ACF 6.3.1 initializes at 10 and returns null; enforce after initialization.
		add_filter( 'rest_pre_dispatch', array( $this, 'dispatch' ), 20, 3 );
	}

	/**
	 * Core has checked the password; reject other transports before usage writes.
	 *
	 * @param WP_Error             $error Native mutable authentication errors.
	 * @param WP_User              $user  Core's verified user.
	 * @param array<string, mixed> $item  Core's verified application-password item.
	 */
	public function authentication_errors( WP_Error $error, WP_User $user, array $item ): void {
		if ( $user->ID > 0 && self::APP_ID === ( $item['app_id'] ?? null ) ) {
			// Cookie auth can resolve the user after core's application-error filter
			// and turn a late failure into anonymous access. Keep the restriction
			// from this verified pair; it confers no native capability or success.
			$this->restricted = true;
			if ( ! self::is_worker_transport() ) {
				$error->add( 'rest_forbidden', __( 'Sorry, you are not allowed to do that.' ), array( 'status' => 403 ) );
			}
		}
	}

	/** The workers use native REST POST, without a method alias. */
	private static function is_worker_transport(): bool {
		// phpcs:ignore WordPress.Security.ValidatedSanitizedInput, WordPress.Security.NonceVerification -- Native Basic authentication, not a form: compare method and alias presence; none of these values selects an identity.
		return defined( 'REST_REQUEST' ) && true === REST_REQUEST && ( ! defined( 'XMLRPC_REQUEST' ) || ! XMLRPC_REQUEST ) && 'POST' === ( $_SERVER['REQUEST_METHOD'] ?? '' ) && ! array_key_exists( '_method', $_GET ) && ! array_key_exists( '_method', $_POST ) && ! array_key_exists( 'HTTP_X_HTTP_METHOD_OVERRIDE', $_SERVER );
	}

	/**
	 * Only the natively verified user/item pair selects a purpose credential.
	 *
	 * @param WP_User              $user Core's successfully authenticated user.
	 * @param array<string, mixed> $item Core's successfully authenticated item.
	 */
	public function authenticated( WP_User $user, array $item ): void {
		if ( $user->ID > 0 && self::APP_ID === ( $item['app_id'] ?? null ) ) {
			$this->restricted    = true;
			$this->authenticated = true;
		}
	}

	/**
	 * The native rest_do_request() skips this HTTP authentication boundary.
	 *
	 * @param mixed $result Native REST authentication result.
	 * @return mixed
	 */
	public function http_authenticated( $result ) {
		if ( $this->authenticated && ! $this->dispatched && true === $result ) {
			$this->http_dispatch_available = true;
		}
		return $result;
	}

	/**
	 * Core serve_request() directly calls dispatch() for the HTTP root request.
	 * No native hook exposes that parent; is_dispatching() is true for children
	 * too. Check only the native server frames and object identity. Never collect
	 * arguments, log the trace, or retain any request/credential data from it.
	 *
	 * @param WP_REST_Server $server Native server handling this dispatch.
	 */
	private static function is_native_http_dispatch( WP_REST_Server $server ): bool {
		// phpcs:ignore WordPress.PHP.DevelopmentFunctions.error_log_debug_backtrace -- Permission guard inspects native caller/object identity only; arguments excluded, trace never output or retained.
		$trace     = debug_backtrace( DEBUG_BACKTRACE_PROVIDE_OBJECT | DEBUG_BACKTRACE_IGNORE_ARGS );
		$positions = array();
		foreach ( $trace as $position => $frame ) {
			if ( ( $frame['object'] ?? null ) instanceof WP_REST_Server && in_array( $frame['function'], array( 'dispatch', 'serve_request' ), true ) ) {
				$positions[] = $position;
			}
		}
		// Exactly the one native dispatch/serve pair; another server also counts
		// as nesting. Direct adjacency rules out children during authentication.
		if ( 2 !== count( $positions ) || $positions[1] !== $positions[0] + 1 ) {
			return false;
		}
		$dispatch = $trace[ $positions[0] ];
		$serve    = $trace[ $positions[1] ];
		return 'dispatch' === $dispatch['function'] && 'serve_request' === $serve['function'] && WP_REST_Server::class === ( $dispatch['class'] ?? null ) && WP_REST_Server::class === ( $serve['class'] ?? null ) && ( $dispatch['object'] ?? null ) === $server && ( $serve['object'] ?? null ) === $server;
	}

	/**
	 * Admit only the compiler's JSON batch; its callback still checks capability,
	 * bounded windows and the complete live lease. Public single reads stay outside
	 * this purpose credential's scope.
	 *
	 * @param WP_REST_Request $request Effective native request.
	 */
	private static function is_worker_operation( WP_REST_Request $request ): bool {
		if ( in_array( $request->get_route(), array( '/linker/v1/publication/jobs/claim', '/linker/v1/publication/jobs/ack' ), true ) ) {
			return true;
		}
		if ( '/linker/v1/publication/identify' !== $request->get_route() ) {
			return false;
		}
		$body = $request->get_json_params();
		return is_array( $body['texts'] ?? null ) && ! $request->has_param( 'text' ) && ! $request->has_param( 'models' );
	}

	/**
	 * Limits the selected credential without granting any native capability.
	 *
	 * @param mixed           $result  Earlier dispatch result.
	 * @param WP_REST_Server  $server  Native REST server.
	 * @param WP_REST_Request $request Effective REST request.
	 * @return mixed
	 */
	public function dispatch( $result, WP_REST_Server $server, WP_REST_Request $request ) {
		if ( ! $this->restricted ) {
			return $result;
		}
		$native_http   = self::is_native_http_dispatch( $server );
		$http_dispatch = $native_http && $this->http_dispatch_available;
		if ( $native_http ) {
			$this->http_dispatch_available = false;
			$this->dispatched              = true;
		}
		if ( ! $http_dispatch || ! self::is_worker_transport() || 'POST' !== $request->get_method() || ! self::is_worker_operation( $request ) || $request->has_param( '_method' ) || $request->has_param( '_embed' ) || null !== $request->get_header( 'x-http-method-override' ) ) {
			return new WP_Error( 'rest_forbidden', __( 'Sorry, you are not allowed to do that.' ), array( 'status' => 403 ) );
		}
		return $result;
	}
}

( new PublicationWorkerAccess() )->register();
