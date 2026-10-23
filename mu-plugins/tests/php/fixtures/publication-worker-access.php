<?php
/**
 * Native HTTP scope matrix. Owns only synthetic users, keys and canary options.
 * Invoked by PublicationWorkerAccessSmokeTest; no queue, mail or product writes.
 *
 * @package Linker\Mu
 */

declare( strict_types = 1 );

// phpcs:disable WordPress.WP.AlternativeFunctions.json_encode_json_encode -- Strict JSON exceptions in a local CLI transport fixture.
// phpcs:disable WordPress.Security.EscapeOutput.ExceptionNotEscaped -- CLI assertion messages only, never HTML or credential values.

use Linker\Mu\PublicationWorkerAccess;
use WpOrg\Requests\Requests;

defined( 'ABSPATH' ) || exit;

if ( ! defined( 'WP_CLI' ) || ! WP_CLI || ! defined( 'LINKER_LOCAL_MAIL_DIR' ) || 'local' !== wp_get_environment_type() || '127.0.0.1' !== wp_parse_url( home_url(), PHP_URL_HOST ) ) {
	throw new RuntimeException( 'Publication scope fixture requires an owned local CLI instance.' );
}

/**
 * Removes only synthetic identities with the durable fixture ownership marker.
 */
function linker_publication_fixture_cleanup(): void {
	$state = get_option( 'linker_publication_worker_fixture', array() );
	if ( is_array( $state ) ) {
		require_once ABSPATH . 'wp-admin/includes/user.php';
		foreach ( $state['users'] ?? array() as $user_id ) {
			if ( get_user_meta( $user_id, 'linker_publication_fixture_owner', true ) === ( $state['owner'] ?? null ) ) {
				wp_delete_user( $user_id );
			}
		}
	}
	delete_option( 'linker_publication_worker_fixture' );
	delete_option( 'linker_publication_worker_reads' );
	delete_option( 'linker_publication_worker_writes' );
}

/**
 * A literal expected outcome; failures reveal no credential, cookie or nonce.
 *
 * @param bool   $condition Expected outcome.
 * @param string $message Assertion description.
 * @throws RuntimeException On a failed literal expectation.
 */
function linker_publication_fixture_expect( bool $condition, string $message ): void {
	if ( ! $condition ) {
		throw new RuntimeException( $message );
	}
}

/**
 * Reads the two owned options after another HTTP process has updated them.
 * Both options exist before the matrix, so no notoptions/alloptions eviction.
 *
 * @return array{reads:int,writes:int}
 */
function linker_publication_fixture_counts(): array {
	foreach ( array( 'reads', 'writes' ) as $kind ) {
		wp_cache_delete( 'linker_publication_worker_' . $kind, 'options' );
	}
	return array(
		'reads'  => (int) get_option( 'linker_publication_worker_reads', 0 ),
		'writes' => (int) get_option( 'linker_publication_worker_writes', 0 ),
	);
}

/**
 * Requests only the loopback instance using an in-memory synthetic credential.
 *
 * @param string                $path REST path (or a local non-REST probe).
 * @param string                $authorization Synthetic Basic authorization.
 * @param string                $method Raw HTTP method.
 * @param array<string, mixed>  $body Request body.
 * @param array<string, string> $headers Additional headers.
 * @return array{status:int,data:mixed}
 * @throws RuntimeException On a broken local transport.
 */
function linker_publication_fixture_request( string $path, string $authorization, string $method = 'POST', array $body = array(), array $headers = array() ): array {
	$url      = str_starts_with( $path, '/publication-worker-native-probe' ) ? home_url( $path ) : rest_url( ltrim( $path, '/' ) );
	$response = wp_remote_request(
		$url,
		array(
			'method'      => $method,
			'headers'     => array_merge(
				array(
					'Authorization' => $authorization,
					'Content-Type'  => 'application/json',
				),
				$headers
			),
			'body'        => in_array( $method, array( 'GET', 'HEAD' ), true ) ? '' : json_encode( $body, JSON_THROW_ON_ERROR ),
			'timeout'     => 30, // Loopback transport only; bound a broken local fixture.
			'redirection' => 0,
		)
	);
	linker_publication_fixture_expect( ! is_wp_error( $response ), 'The local HTTP fixture did not answer.' );
	if ( is_wp_error( $response ) ) {
		throw new RuntimeException( 'The local HTTP fixture did not answer.' );
	}
	$status = wp_remote_retrieve_response_code( $response );
	if ( ! is_int( $status ) ) {
		throw new RuntimeException( 'The local HTTP fixture returned no status.' );
	}
	return array(
		'status' => $status,
		'data'   => json_decode( wp_remote_retrieve_body( $response ), true ),
	);
}

linker_publication_fixture_cleanup();
if ( 'cleanup' === ( $args[0] ?? '' ) ) {
	echo "publication fixture cleaned\n";
	return;
}

( static function (): void {
	$linker_publication_state = array(
		'owner' => wp_generate_uuid4(),
		'users' => array(),
	);
	update_option( 'linker_publication_worker_fixture', $linker_publication_state, false );
	// Existing non-autoload options permit exact cache eviction across processes.
	add_option( 'linker_publication_worker_reads', 0, '', false );
	add_option( 'linker_publication_worker_writes', 0, '', false );
	$linker_publication_checks = 0;
	try {
		$linker_publication_keys = array();
		foreach ( array(
			'admin'  => 'administrator',
			'reader' => 'subscriber',
		) as $label => $role ) {
			$login = 'publication-fixture-' . $label . '-' . substr( wp_generate_uuid4(), 0, 8 );
			$id    = wp_insert_user(
				array(
					'user_login' => $login,
					'user_pass'  => wp_generate_password( 40 ),
					'user_email' => $login . '@example.invalid',
					'role'       => $role,
				)
			);
			if ( is_wp_error( $id ) ) {
				throw new RuntimeException( 'Synthetic native identity creation failed.' );
			}
			update_user_meta( $id, 'linker_publication_fixture_owner', $linker_publication_state['owner'] );
			$linker_publication_state['users'][ $label ] = $id;
			update_option( 'linker_publication_worker_fixture', $linker_publication_state, false );
			foreach ( array(
				'purpose'  => PublicationWorkerAccess::APP_ID,
				'ordinary' => wp_generate_uuid4(),
			) as $kind => $app_id ) {
				$key = WP_Application_Passwords::create_new_application_password(
					$id,
					array(
						'name'   => 'publication fixture ' . $kind,
						'app_id' => $app_id,
					)
				);
				if ( is_wp_error( $key ) ) {
					throw new RuntimeException( 'Synthetic native application-password creation failed.' );
				}
				$linker_publication_keys[ $label ][ $kind ] = array(
					// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_encode -- Native Basic authentication for synthetic local credentials.
					'authorization' => 'Basic ' . base64_encode( $login . ':' . $key[0] ),
					'uuid'          => $key[1]['uuid'],
				);
			}
		}
		$linker_publication_purpose  = $linker_publication_keys['admin']['purpose']['authorization'];
		$linker_publication_ordinary = $linker_publication_keys['admin']['ordinary']['authorization'];
		foreach ( array( 'claim', 'ack' ) as $operation ) {
			$receipt = linker_publication_fixture_request( '/linker/v1/publication/jobs/' . $operation, $linker_publication_purpose, 'POST', array( 'probe_children' => true ) );
			linker_publication_fixture_expect( 200 === $receipt['status'] && ( $receipt['data']['user_id'] ?? null ) === $linker_publication_state['users']['admin'] && ( $receipt['data']['credential_uuid'] ?? null ) === $linker_publication_keys['admin']['purpose']['uuid'], 'Native purpose authentication did not reach the job callback.' );
			linker_publication_fixture_expect( array( 403, 403, 403 ) === ( $receipt['data']['children'] ?? null ), 'An internal read, write or job inherited purpose authority.' );
			$linker_publication_checks += 2;
		}
		foreach ( array( 'GET', 'HEAD', 'OPTIONS', 'PUT', 'PATCH', 'DELETE' ) as $method ) {
			$response = linker_publication_fixture_request( '/linker/v1/publication/jobs/claim', $linker_publication_purpose, $method );
			linker_publication_fixture_expect( 403 === $response['status'], 'A disallowed raw HTTP method reached the endpoint.' );
			++$linker_publication_checks;
		}
		foreach ( array( '/wp/v2/users/me', '/wp/v2/settings', '/wc/v3/products', '/wc/store/v1/products', '/wc/publication-fixture/v1/public', '/wp/v2/media?mime_type=application/pdf', '/linker/v1/publication/manifest', '/linker-publication-fixture/v1/canary' ) as $route ) {
			foreach ( array( 'GET', 'POST' ) as $method ) {
				// Even a broken scope must not create an actual Woo product: its
				// native schema rejects this non-string name before the callback.
				$body     = '/wc/v3/products' === $route && 'POST' === $method ? array( 'name' => array( 'invalid-fixture-name' ) ) : array();
				$response = linker_publication_fixture_request( $route, $linker_publication_purpose, $method, $body );
				$code     = is_array( $response['data'] ) && is_string( $response['data']['code'] ?? null ) ? $response['data']['code'] : 'no-machine-code';
				linker_publication_fixture_expect( 403 === $response['status'], 'The purpose request did not return the expected refusal: ' . $method . ' ' . $route . ' status=' . $response['status'] . ' code=' . $code . '.' );
				++$linker_publication_checks;
			}
		}
		foreach ( array(
			array( '/linker/v1/publication/jobs/claim?_method=POST', array(), array() ),
			array( '/linker/v1/publication/jobs/claim', array( '_method' => 'POST' ), array() ),
			array( '/linker/v1/publication/jobs/claim', array( '_method' => null ), array() ),
			array( '/linker/v1/publication/jobs/claim', array(), array( 'X-HTTP-Method-Override' => 'POST' ) ),
			array( '/linker/v1/publication/jobs/claim?_embed=1', array(), array() ),
			array( '/linker/v1/publication/jobs/claim', array( '_embed' => false ), array() ),
			array(
				'/batch/v1',
				array(
					'requests' => array(
						array(
							'method' => 'POST',
							'path'   => '/linker/v1/publication/jobs/claim',
						),
					),
				),
				array(),
			),
		) as $alias ) {
			$response = linker_publication_fixture_request( $alias[0], $linker_publication_purpose, 'POST', $alias[1], $alias[2] );
			linker_publication_fixture_expect( 403 === $response['status'], 'A method alias, embed or batch bypassed the scope.' );
			++$linker_publication_checks;
		}
		$response = linker_publication_fixture_request( '/publication-worker-native-probe', $linker_publication_purpose );
		linker_publication_fixture_expect( 403 === $response['status'], 'Non-REST authentication accepted the purpose key.' );
		++$linker_publication_checks;
		$response = linker_publication_fixture_request( '/linker/v1/publication/jobs/claim', $linker_publication_keys['reader']['purpose']['authorization'] );
		linker_publication_fixture_expect( 403 === $response['status'], 'The adapter granted a capability to a native reader.' );
		++$linker_publication_checks;
		$counts = linker_publication_fixture_counts();
		linker_publication_fixture_expect(
			array(
				'reads'  => 0,
				'writes' => 0,
			) === $counts,
			'A forbidden purpose request executed a non-job canary: reads=' . $counts['reads'] . ' writes=' . $counts['writes'] . '.'
		);
		++$linker_publication_checks;

		// Prove that the WC canary actually is public, then reset only its owned
		// counter before the independent concurrent ordinary-credential control.
		$response = linker_publication_fixture_request( '/wc/publication-fixture/v1/public', '', 'GET' );
		linker_publication_fixture_expect( 200 === $response['status'], 'The public WC canary did not execute for an ordinary anonymous request.' );
		$counts = linker_publication_fixture_counts();
		linker_publication_fixture_expect(
			array(
				'reads'  => 1,
				'writes' => 0,
			) === $counts,
			'The public WC canary control did not increment exactly once.'
		);
		update_option( 'linker_publication_worker_reads', 0, false );
		$linker_publication_checks += 2;

		// Requests uses native cURL multiplexing when available; identities remain in memory.
		$parallel = Requests::request_multiple(
			array(
				'job'      => array(
					'url'     => rest_url( 'linker/v1/publication/jobs/claim' ),
					'type'    => 'POST',
					'headers' => array( 'Authorization' => $linker_publication_purpose ),
				),
				'denied'   => array(
					'url'     => rest_url( 'linker-publication-fixture/v1/canary' ),
					'type'    => 'POST',
					'headers' => array( 'Authorization' => $linker_publication_purpose ),
				),
				'ordinary' => array(
					'url'     => rest_url( 'linker-publication-fixture/v1/canary?app_id=' . PublicationWorkerAccess::APP_ID ),
					'type'    => 'POST',
					'headers' => array( 'Authorization' => $linker_publication_ordinary ),
				),
			),
			array( 'timeout' => 30 ) // Same bounded local transport as the sequential matrix.
		);
		foreach ( array(
			'job'      => 200,
			'denied'   => 403,
			'ordinary' => 200,
		) as $label => $status ) {
			linker_publication_fixture_expect( $parallel[ $label ] instanceof \WpOrg\Requests\Response && $status === $parallel[ $label ]->status_code, 'Concurrent credentials leaked or lost their scope.' );
			++$linker_publication_checks;
		}
		$counts = linker_publication_fixture_counts();
		linker_publication_fixture_expect(
			array(
				'reads'  => 0,
				'writes' => 1,
			) === $counts,
			'The concurrent canary count differed from its ordinary-key control: reads=' . $counts['reads'] . ' writes=' . $counts['writes'] . '.'
		);
		++$linker_publication_checks;
		$response = linker_publication_fixture_request( '/publication-worker-native-probe', $linker_publication_ordinary );
		linker_publication_fixture_expect( 200 === $response['status'], 'An unrelated native application key lost non-REST behavior.' );
		++$linker_publication_checks;

		// A native subscriber session proves cookie behavior without bypassing staff MFA.
		$expiration  = time() + HOUR_IN_SECONDS;
		$token       = WP_Session_Tokens::get_instance( $linker_publication_state['users']['reader'] )->create( $expiration );
		$cookie      = wp_generate_auth_cookie( $linker_publication_state['users']['reader'], $expiration, 'logged_in', $token );
		$cookie_name = constant( 'LOGGED_IN_COOKIE' );
		if ( ! is_string( $cookie_name ) ) {
			throw new RuntimeException( 'Native cookie name is unavailable.' );
		}
		$cookie_header = $cookie_name . '=' . $cookie;
		$nonce         = linker_publication_fixture_request( '/publication-worker-native-probe', '', 'GET', array(), array( 'Cookie' => $cookie_header ) );
		linker_publication_fixture_expect( 200 === $nonce['status'] && is_string( $nonce['data']['nonce'] ?? null ), 'Native cookie authentication failed.' );
		$response = linker_publication_fixture_request(
			'/linker-publication-fixture/v1/canary',
			'',
			'GET',
			array(),
			array(
				'Cookie'     => $cookie_header,
				'X-WP-Nonce' => $nonce['data']['nonce'],
			)
		);
		linker_publication_fixture_expect( 200 === $response['status'] && ( $response['data']['user_id'] ?? null ) === $linker_publication_state['users']['reader'], 'The adapter changed native cookie REST behavior.' );
		$linker_publication_checks += 2;

		// Rollback retires only this purpose UUID before removing the adapter.
		$deleted = WP_Application_Passwords::delete_application_password( $linker_publication_state['users']['admin'], $linker_publication_keys['admin']['purpose']['uuid'] );
		linker_publication_fixture_expect( true === $deleted, 'The synthetic purpose credential was not retired.' );
		$response = linker_publication_fixture_request( '/linker/v1/publication/jobs/claim', $linker_publication_purpose );
		linker_publication_fixture_expect( 401 === $response['status'], 'A retired purpose key still authenticated.' );
		$response = linker_publication_fixture_request( '/linker-publication-fixture/v1/canary', $linker_publication_ordinary );
		linker_publication_fixture_expect( 200 === $response['status'], 'Retiring the purpose UUID changed an unrelated native key.' );
		$linker_publication_checks += 3;

		echo wp_json_encode(
			array(
				'checks'                 => $linker_publication_checks,
				'purpose_non_job_reads'  => 0,
				'purpose_non_job_writes' => 0,
				'synthetic_only'         => true,
			)
		) . "\n";
	} catch ( Throwable $failure ) {
		// The WordPress fatal handler hides exception messages with WP_DEBUG off.
		// These fixture assertions contain no credential, cookie or response body.
		$diagnostic = $failure instanceof RuntimeException ? $failure->getMessage() : get_class( $failure ) . ' at fixture line ' . $failure->getLine();
		// phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fwrite -- Local CLI diagnostics only; no private runtime values.
		fwrite( STDERR, 'Publication scope fixture: ' . $diagnostic . "\n" );
		throw $failure;
	} finally {
		linker_publication_fixture_cleanup();
	}
} )();
