<?php
/**
 * Current identity comparison and project-brief staging for marketing entries.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

use Linker\Tools\Planner\Failure;
use Linker\Tools\Planner\JsonNumbers;
use Linker\Tools\Planner\NativeIdentity;
use Linker\Tools\Planner\Origin;
use Linker\Tools\Planner\ProjectBriefSource;
use WP_Error;
use WP_REST_Request;
use WP_REST_Response;

/** No cookie, user identity or token is exposed by these auxiliary routes. */
final class EntryContext {
	/** Registers the same-origin auxiliary routes, using native REST authentication. */
	public function register(): void {
		register_rest_route(
			Proxy::NAMESPACE,
			'/genie/entry-context',
			array(
				'methods'             => 'POST',
				'callback'            => array( $this, 'read' ),
				'permission_callback' => '__return_true',
				'args'                => array(
					'tab' => array(
						'type'     => 'string',
						'required' => true,
						'pattern'  => '^[0-9a-f-]{36}$',
					),
				),
			)
		);
		register_rest_route(
			Proxy::NAMESPACE,
			'/genie/project-brief',
			array(
				'methods'             => 'POST',
				'callback'            => array( $this, 'stage_brief' ),
				'permission_callback' => array( $this, 'brief_permission' ),
			)
		);
	}

	/**
	 * Resolves the current server principal before cached text can be displayed.
	 *
	 * @param WP_REST_Request $request Current authenticated request.
	 */
	public function read( WP_REST_Request $request ): WP_REST_Response {
		$response = new WP_REST_Response( array( 'scope' => ( new Conversations() )->entry_scope( (string) $request->get_param( 'tab' ) ) ) );
		$response->header( 'Cache-Control', 'private, no-store' );
		$response->header( 'Vary', 'Cookie' );
		return $response;
	}

	/**
	 * Require a same-origin request before staging a project brief.
	 *
	 * @param WP_REST_Request $request Current request.
	 * @return true|WP_Error
	 */
	public function brief_permission( WP_REST_Request $request ): bool|WP_Error {
		return Origin::allows( $request ) ? true : Failure::make( 'origin', 403 );
	}

	/**
	 * Stage a customer project note under the verified native principal/Woo session.
	 *
	 * @param WP_REST_Request $request Current request.
	 * @return WP_REST_Response|WP_Error
	 */
	public function stage_brief( WP_REST_Request $request ): WP_REST_Response|WP_Error {
		if ( ! Origin::allows( $request ) ) {
			return Failure::make( 'origin', 403 );
		}
		$body = (string) $request->get_body();
		if ( '' === $body || strlen( $body ) > 65536 ) {
			return Failure::make( 'project_brief_input', 422 );
		}
		$decoded = json_decode( $body, false, 8 );
		if ( ! $decoded instanceof \stdClass || ! JsonNumbers::supported( $decoded ) ) {
			return Failure::make( 'project_brief_input', 422 );
		}
		$command = get_object_vars( $decoded );
		$tab     = $command['tab'] ?? null;
		if ( null !== $tab && ( ! is_string( $tab ) || 1 !== preg_match( '/\A[0-9a-f-]{36}\z/', $tab ) ) ) {
			return Failure::make( 'project_brief_input', 422 );
		}
		$context = ( new NativeIdentity() )->bootstrap( $request );
		if ( is_wp_error( $context ) ) {
			return $context;
		}
		$staged = ( new ProjectBriefSource() )->stage( $context['principal'], $command );
		if ( is_wp_error( $staged ) ) {
			return $staged;
		}
		if ( is_string( $tab ) ) {
			$staged['scope'] = ( new Conversations() )->entry_scope( $tab );
		}
		$response = new WP_REST_Response( $staged );
		$response->header( 'Cache-Control', 'private, no-store' );
		$response->header( 'Vary', 'Cookie' );
		return $response;
	}
}
