<?php
/**
 * Plugin Name: Linker inventory credential scope
 * Description: Limits the privately bound native application credential to the two inventory collections.
 *
 * @package Linker\Mu
 */

declare( strict_types = 1 );

namespace Linker\Mu;

use WP_Application_Passwords;
use WP_Error;
use WP_REST_Request;
use WP_REST_Server;
use WP_User;

defined( 'ABSPATH' ) || exit;

/**
 * Request-local authority comes only from native successful authentication.
 */
final class InventoryAccess {

	/**
	 * Whether this request authenticated the selected native credential.
	 *
	 * @var bool
	 */
	private bool $selected = false;

	/**
	 * Binding matched after core checked the password; keep it through usage writes.
	 *
	 * @var array{state:string,user_id?:int,uuid?:string}|null
	 */
	private ?array $candidate = null;

	/** Registers constraints without changing roles, credentials or cookies. */
	public function register(): void {
		add_action( 'wp_authenticate_application_password_errors', array( $this, 'authentication_errors' ), 10, 3 );
		add_action( 'application_password_did_authenticate', array( $this, 'authenticated' ), 10, 2 );
		add_filter( 'rest_pre_dispatch', array( $this, 'dispatch' ), 10, 3 );
	}

	/** Explicit operational status; never exposes the private identity binding. */
	public static function status(): string {
		return self::binding()['state'];
	}

	/**
	 * The private server binding must still resolve to a native credential.
	 *
	 * @return array{state:string,user_id?:int,uuid?:string}
	 */
	private static function binding(): array {
		if ( ! defined( 'LINKER_INVENTORY_ACCESS' ) ) {
			return array( 'state' => 'unconfigured' );
		}
		$value = constant( 'LINKER_INVENTORY_ACCESS' );
		if ( is_array( $value ) && false === ( $value['active'] ?? null ) ) {
			return array( 'state' => 'inactive' );
		}
		if ( ! is_array( $value ) || true !== ( $value['active'] ?? null ) || ! is_int( $value['user_id'] ?? null ) || $value['user_id'] <= 0 || ! is_string( $value['uuid'] ?? null ) || ! wp_is_uuid( $value['uuid'] ) ) {
			return array( 'state' => 'invalid' );
		}
		$item = WP_Application_Passwords::get_user_application_password( $value['user_id'], $value['uuid'] );
		if ( null === $item ) {
			return array( 'state' => 'invalid' );
		}
		return array(
			'state'   => 'active',
			'user_id' => $value['user_id'],
			'uuid'    => $value['uuid'],
		);
	}

	/**
	 * Only core's validated user/item pair can match the private binding.
	 *
	 * @param WP_User                                       $user    The natively authenticated user.
	 * @param array<string, mixed>                          $item    The native application-password item.
	 * @param array{state:string,user_id?:int,uuid?:string} $binding The request's already-resolved private binding.
	 */
	private static function matches( WP_User $user, array $item, array $binding ): bool {
		return 'active' === $binding['state'] && ( $binding['user_id'] ?? 0 ) === $user->ID && ( $item['uuid'] ?? null ) === ( $binding['uuid'] ?? null );
	}

	/**
	 * Rejects other protocols before native credential-use metadata is recorded.
	 *
	 * @param WP_Error             $error Native mutable authentication errors.
	 * @param WP_User              $user  The user after successful password checking.
	 * @param array<string, mixed> $item  The native application-password item.
	 */
	public function authentication_errors( WP_Error $error, WP_User $user, array $item ): void {
		$binding = self::binding();
		$matches = self::matches( $user, $item, $binding );
		if ( $matches ) {
			$this->candidate = $binding;
		}
		// phpcs:ignore WordPress.Security.ValidatedSanitizedInput, WordPress.Security.NonceVerification.Recommended -- Native Basic authentication, not a form; compare the exact raw method and alias presence, never output or use them as identity.
		if ( 'invalid' === $binding['state'] || ( $matches && ( ! defined( 'REST_REQUEST' ) || true !== REST_REQUEST || 'GET' !== ( $_SERVER['REQUEST_METHOD'] ?? '' ) || isset( $_GET['_method'] ) || isset( $_SERVER['HTTP_X_HTTP_METHOD_OVERRIDE'] ) ) ) ) {
			$error->add( 'rest_forbidden', __( 'Sorry, you are not allowed to do that.' ), array( 'status' => 403 ) );
		}
	}

	/**
	 * Successful authentication is sticky across internal dispatch/subrequests.
	 *
	 * @param WP_User              $user Core's successful user.
	 * @param array<string, mixed> $item Core's successful credential item.
	 */
	public function authenticated( WP_User $user, array $item ): void {
		$this->selected = $this->selected || ( null !== $this->candidate && self::matches( $user, $item, $this->candidate ) );
	}

	/**
	 * Checks every effective REST request, including embeds and batch children.
	 *
	 * @param mixed           $result  Any earlier pre-dispatch result.
	 * @param WP_REST_Server  $server  Native REST server.
	 * @param WP_REST_Request $request Effective native REST request.
	 * @return mixed
	 */
	public function dispatch( $result, WP_REST_Server $server, WP_REST_Request $request ) {
		unset( $server );
		if ( ! $this->selected ) {
			return $result;
		}
		if ( 'GET' !== $request->get_method() || ! in_array( $request->get_route(), array( '/wp/v2/media', '/wc/v3/products' ), true ) || ( '/wp/v2/media' === $request->get_route() && 'application/pdf' !== $request->get_param( 'mime_type' ) ) || $request->has_param( '_method' ) || null !== $request->get_header( 'x-http-method-override' ) ) {
			return new WP_Error( 'rest_forbidden', __( 'Sorry, you are not allowed to do that.' ), array( 'status' => 403 ) );
		}
		return $result;
	}
}

( new InventoryAccess() )->register();
