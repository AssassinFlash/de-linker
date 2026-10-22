<?php
/**
 * Local-only transport probes; never deployed as a production MU entry.
 *
 * @package Linker\Mu
 */

defined( 'ABSPATH' ) || exit;

if ( ! defined( 'LINKER_LOCAL_MAIL_DIR' ) || 'local' !== wp_get_environment_type() || '127.0.0.1' !== wp_parse_url( home_url(), PHP_URL_HOST ) ) {
	return;
}

$linker_inventory_binding_file = dirname( ABSPATH ) . '/inventory-access-binding.json';
if ( is_file( $linker_inventory_binding_file ) ) {
	// phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- Known private local file, not a remote URL.
	$linker_inventory_raw = file_get_contents( $linker_inventory_binding_file );
	define( 'LINKER_INVENTORY_ACCESS', false === $linker_inventory_raw ? null : json_decode( $linker_inventory_raw, true ) );
}
unset( $linker_inventory_binding_file, $linker_inventory_raw );

// Revoke only this fixture's synthetic credential after the scope error hook,
// before core's usage write and success hook. No external credential is touched.
$linker_inventory_revocation_subject = static function ( WP_User $user, array $item ): bool {
	$state = get_option( 'linker_inventory_fixture' );
	return '1' === sanitize_text_field( wp_unslash( $_SERVER['HTTP_X_INVENTORY_FIXTURE_REVOKE'] ?? '' ) ) && is_array( $state ) && ( $state['users']['admin']['id'] ?? null ) === $user->ID && ( $item['uuid'] ?? null ) === ( $state['applications']['selected']['uuid'] ?? null );
};
add_action(
	'wp_authenticate_application_password_errors',
	static function ( WP_Error $error, WP_User $user, array $item ) use ( $linker_inventory_revocation_subject ): void {
		if ( $error->has_errors() || ! $linker_inventory_revocation_subject( $user, $item ) ) {
			return;
		}
		update_option(
			'linker_inventory_fixture_revocation',
			array(
				'deleted'      => true === WP_Application_Passwords::delete_application_password( $user->ID, $item['uuid'] ),
				'core_success' => false,
			),
			false
		);
	},
	20,
	3
);
add_action(
	'application_password_did_authenticate',
	static function ( WP_User $user, array $item ) use ( $linker_inventory_revocation_subject ): void {
		if ( ! $linker_inventory_revocation_subject( $user, $item ) ) {
			return;
		}
		$record = get_option( 'linker_inventory_fixture_revocation' );
		if ( is_array( $record ) ) {
			$record['core_success'] = true;
			update_option( 'linker_inventory_fixture_revocation', $record, false );
		}
	},
	20,
	2
);
unset( $linker_inventory_revocation_subject );

// A local probe deliberately exposes a non-REST application-auth consumer.
// The selected credential must still be rejected by core's error hook.
add_filter(
	'application_password_is_api_request',
	static fn( bool $api ): bool => $api || '/inventory-access-native-probe' === wp_parse_url( sanitize_text_field( wp_unslash( $_SERVER['REQUEST_URI'] ?? '' ) ), PHP_URL_PATH )
);
add_action(
	'template_redirect',
	static function (): void {
		if ( '/inventory-access-native-probe' !== wp_parse_url( sanitize_text_field( wp_unslash( $_SERVER['REQUEST_URI'] ?? '' ) ), PHP_URL_PATH ) ) {
			return;
		}
		$authenticated = is_user_logged_in();
		wp_send_json(
			array(
				'authenticated' => $authenticated,
				'rest_nonce'    => $authenticated ? wp_create_nonce( 'wp_rest' ) : null,
			),
			$authenticated ? 200 : 403
		);
	}
);

add_action(
	'rest_api_init',
	static function (): void {
		register_rest_route(
			'linker-inventory-fixture/v1',
			'/mutate',
			array(
				'methods'             => 'POST',
				'permission_callback' => static fn(): bool => current_user_can( 'edit_posts' ),
				'callback'            => static function (): array {
					$count = (int) get_option( 'linker_inventory_fixture_mutations', 0 ) + 1;
					update_option( 'linker_inventory_fixture_mutations', $count, false );
					return array( 'mutations' => $count );
				},
				'allow_batch'         => array( 'v1' => true ),
			)
		);
	}
);

add_filter(
	'rest_request_after_callbacks',
	static function ( $response, array $handler, WP_REST_Request $request ) {
		unset( $handler );
		$probe = $request->get_param( 'inventory_fixture_subrequest' );
		if ( ! is_string( $probe ) || ! in_array( $request->get_route(), array( '/wp/v2/media', '/wc/v3/products' ), true ) || is_wp_error( $response ) ) {
			return $response;
		}
		$child = new WP_REST_Request( 'read' === $probe ? 'GET' : 'POST', 'read' === $probe ? '/wp/v2/users/me' : '/linker-inventory-fixture/v1/mutate' );
		if ( 'batch' === $probe ) {
			$child = new WP_REST_Request( 'POST', '/batch/v1' );
			$child->set_param(
				'requests',
				array(
					array(
						'method' => 'POST',
						'path'   => '/linker-inventory-fixture/v1/mutate',
					),
				)
			);
		} elseif ( 'query_alias' === $probe || 'header_alias' === $probe ) {
			$child = new WP_REST_Request( 'GET', '/wp/v2/media' );
			$child->set_param( 'mime_type', 'application/pdf' );
			if ( 'query_alias' === $probe ) {
				$child->set_param( '_method', 'GET' );
			} else {
				$child->set_header( 'X-HTTP-Method-Override', 'GET' );
			}
		}
		$nested   = rest_do_request( $child );
		$response = rest_ensure_response( $response );
		$response->header( 'X-Inventory-Fixture-Child-Status', (string) $nested->get_status() );
		return $response;
	},
	10,
	3
);
