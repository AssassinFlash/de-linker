<?php
/**
 * Local-only native authentication and REST canaries; never deployed.
 *
 * @package Linker\Mu
 */

declare( strict_types = 1 );

defined( 'ABSPATH' ) || exit;

if ( ! defined( 'LINKER_LOCAL_MAIL_DIR' ) || 'local' !== wp_get_environment_type() || '127.0.0.1' !== wp_parse_url( home_url(), PHP_URL_HOST ) ) {
	return;
}

/**
 * ACF's initialization return on bare CI, without replacing a real ACF hook.
 *
 * @param mixed           $result Earlier result.
 * @param WP_REST_Server  $server Native server.
 * @param WP_REST_Request $request Native request.
 * @return null
 */
function linker_publication_fixture_initialize( $result, WP_REST_Server $server, WP_REST_Request $request ) {
	unset( $result, $server, $request );
	return null;
}

/**
 * Synthetic identities are owned by this fixture; no existing user qualifies.
 *
 * @return bool
 */
function linker_publication_fixture_user(): bool {
	$state = get_option( 'linker_publication_worker_fixture', array() );
	return is_array( $state ) && in_array( get_current_user_id(), $state['users'] ?? array(), true );
}

/**
 * Native read/write canaries observe only successful endpoint callbacks.
 *
 * @param WP_REST_Request $request Effective request.
 * @return array<string, mixed>
 */
function linker_publication_fixture_canary( WP_REST_Request $request ): array {
	$kind   = 'GET' === $request->get_method() ? 'reads' : 'writes';
	$option = 'linker_publication_worker_' . $kind;
	$count  = (int) get_option( $option, 0 ) + 1;
	update_option( $option, $count, false );
	return array(
		'kind'    => $kind,
		'count'   => $count,
		'user_id' => get_current_user_id(),
	);
}

/**
 * Attempts internal jobs before the outer native dispatch reaches the scope.
 *
 * @return list<int> Native status of two ordinary and one other-server child.
 */
function linker_publication_fixture_early_children(): array {
	$children = array();
	foreach ( array( 'claim', 'ack' ) as $operation ) {
		$children[] = rest_do_request( new WP_REST_Request( 'POST', '/linker/v1/publication/jobs/' . $operation ) )->get_status();
	}
	$children[] = ( new WP_REST_Server() )->dispatch( new WP_REST_Request( 'POST', '/linker/v1/publication/jobs/ack' ) )->get_status();
	return $children;
}

/**
 * The callback replaces queue mutation with an authenticated native receipt.
 * Children deliberately exercise inherited native current-user authority.
 *
 * @param WP_REST_Request $request Effective request.
 * @return array<string, mixed>
 */
function linker_publication_fixture_job( WP_REST_Request $request ): array {
	global $linker_publication_fixture_early;
	$children = array();
	if ( true === $request->get_param( 'probe_children' ) ) {
		foreach ( array( array( 'GET', '/linker-publication-fixture/v1/canary' ), array( 'POST', '/linker-publication-fixture/v1/canary' ), array( 'POST', '/linker/v1/publication/jobs/ack' ) ) as $child ) {
			$children[] = rest_do_request( new WP_REST_Request( $child[0], $child[1] ) )->get_status();
		}
	}
	return array(
		'user_id'         => get_current_user_id(),
		'credential_uuid' => rest_get_authenticated_app_password(),
		'route'           => $request->get_route(),
		'children'        => $children,
		'early_children'  => $linker_publication_fixture_early ?? array(),
	);
}

add_filter(
	'rest_pre_dispatch',
	static function ( mixed $result, WP_REST_Server $server, WP_REST_Request $request ): mixed {
		global $linker_publication_fixture_early;
		unset( $server );
		if ( 'dispatch' === $request->get_header( 'x-publication-fixture-early' ) && linker_publication_fixture_user() ) {
			$linker_publication_fixture_early = linker_publication_fixture_early_children();
		}
		return $result;
	},
	15,
	3
);
add_filter(
	'rest_authentication_errors',
	static function ( mixed $result ): mixed {
		global $linker_publication_fixture_early;
		if ( 'authentication' === sanitize_text_field( wp_unslash( $_SERVER['HTTP_X_PUBLICATION_FIXTURE_EARLY'] ?? '' ) ) && linker_publication_fixture_user() ) {
			$linker_publication_fixture_early = linker_publication_fixture_early_children();
		}
		return $result;
	},
	115
);

add_action(
	'rest_api_init',
	static function (): void {
		global $wp_filter;
		$acf = false;
		foreach ( $wp_filter['rest_pre_dispatch']->callbacks[10] ?? array() as $callback ) {
			$function = $callback['function'];
			if ( is_array( $function ) && is_object( $function[0] ) && is_a( $function[0], 'ACF_Rest_Api' ) && 'initialize' === $function[1] ) {
				$acf = true;
			}
		}
		if ( ! $acf ) {
			add_filter( 'rest_pre_dispatch', 'linker_publication_fixture_initialize', 10, 3 );
		}
		foreach ( array( 'claim', 'ack' ) as $operation ) {
			register_rest_route(
				'linker/v1',
				'/publication/jobs/' . $operation,
				array(
					'methods'             => 'POST',
					'permission_callback' => static fn(): bool => linker_publication_fixture_user() && current_user_can( 'manage_options' ),
					'callback'            => 'linker_publication_fixture_job',
					'allow_batch'         => array( 'v1' => true ),
				),
				true
			);
		}
		register_rest_route(
			'linker-publication-fixture/v1',
			'/canary',
			array(
				'methods'             => 'GET,POST',
				'permission_callback' => static fn(): bool => linker_publication_fixture_user() && current_user_can( 'read' ),
				'callback'            => 'linker_publication_fixture_canary',
				'allow_batch'         => array( 'v1' => true ),
			)
		);
		// Woo's wc/ prefix exercises the real early-current-user/late-auth path.
		// Its public callback would execute as anonymous without sticky restriction.
		register_rest_route(
			'wc/publication-fixture/v1',
			'/public',
			array(
				'methods'             => 'GET,POST',
				'permission_callback' => '__return_true',
				'callback'            => 'linker_publication_fixture_canary',
				'allow_batch'         => array( 'v1' => true ),
			)
		);
	},
	PHP_INT_MAX
);

// A non-REST consumer explicitly asks core to authenticate an application key.
// Only this local probe is enabled; production authentication is unchanged.
add_filter(
	'application_password_is_api_request',
	static fn( bool $api ): bool => $api || '/publication-worker-native-probe' === wp_parse_url( sanitize_text_field( wp_unslash( $_SERVER['REQUEST_URI'] ?? '' ) ), PHP_URL_PATH )
);
add_action(
	'template_redirect',
	static function (): void {
		if ( '/publication-worker-native-probe' !== wp_parse_url( sanitize_text_field( wp_unslash( $_SERVER['REQUEST_URI'] ?? '' ) ), PHP_URL_PATH ) ) {
			return;
		}
		$authenticated = is_user_logged_in() && linker_publication_fixture_user();
		wp_send_json(
			array(
				'authenticated' => $authenticated,
				'nonce'         => $authenticated ? wp_create_nonce( 'wp_rest' ) : '',
			),
			$authenticated ? 200 : 403
		);
	}
);
