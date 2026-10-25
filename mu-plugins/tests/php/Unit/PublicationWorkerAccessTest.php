<?php
/**
 * Publication worker scope through the native authentication/dispatch hooks.
 *
 * @package Linker\Mu
 */

declare( strict_types = 1 );

namespace Linker\Mu\Tests\Unit;

use PHPUnit\Framework\TestCase;

// phpcs:disable WordPress.WP.AlternativeFunctions, WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open -- an isolated hook boundary keeps WordPress doubles out of the PHPUnit process.

/**
 * Scope behavior through the native public hook seam.
 *
 * @covers \Linker\Mu\PublicationWorkerAccess
 */
final class PublicationWorkerAccessTest extends TestCase {

	/** A native purpose credential cannot inherit the administrator's unrelated writes. */
	public function test_a_verified_purpose_key_cannot_write_a_non_job_route(): void {
		self::assertSame(
			array(
				'authentication_denied' => false,
				'denied'                => array( true ),
				'writes'                => 0,
			),
			self::run_scope( array() )
		);
	}

	/** Internal same-job and non-job calls cannot reuse top-level authority. */
	public function test_only_one_top_level_http_job_dispatch_is_allowed(): void {
		self::assertSame(
			array(
				'authentication_denied' => false,
				'denied'                => array( false, true, true ),
				'writes'                => 1,
			),
			self::run_scope(
				array(
					'requests' => array(
						array( 'route' => '/linker/v1/publication/jobs/claim' ),
						array(
							'route'          => '/linker/v1/publication/jobs/ack',
							'reauthenticate' => true,
						),
						array( 'route' => '/linker-test/v1/write' ),
					),
				)
			)
		);
		self::assertSame(
			array(
				'authentication_denied' => false,
				'denied'                => array( true ),
				'writes'                => 0,
			),
			self::run_scope(
				array(
					'http_authentication' => false,
					'requests'            => array( array( 'route' => '/linker/v1/publication/jobs/claim' ) ),
				)
			)
		);
	}

	/**
	 * Raw transport cannot be disguised as an allowed jobs POST.
	 *
	 * @dataProvider raw_transports
	 * @param array<string, mixed> $transport The raw native request boundary.
	 */
	public function test_raw_transport_aliases_are_refused_before_success( array $transport ): void {
		self::assertSame(
			array(
				'authentication_denied' => true,
				'denied'                => array(),
				'writes'                => 0,
			),
			self::run_scope( $transport + array( 'requests' => array( array( 'route' => '/linker/v1/publication/jobs/claim' ) ) ) )
		);
	}

	/**
	 * Raw native transport cases.
	 *
	 * @return array<string, array{array<string, mixed>}>
	 */
	public static function raw_transports(): array {
		return array(
			'non REST'           => array( array( 'rest' => false ) ),
			'GET'                => array( array( 'raw_method' => 'GET' ) ),
			'HEAD'               => array( array( 'raw_method' => 'HEAD' ) ),
			'OPTIONS'            => array( array( 'raw_method' => 'OPTIONS' ) ),
			'PUT'                => array( array( 'raw_method' => 'PUT' ) ),
			'PATCH'              => array( array( 'raw_method' => 'PATCH' ) ),
			'DELETE'             => array( array( 'raw_method' => 'DELETE' ) ),
			'query method'       => array( array( 'query' => array( '_method' => 'POST' ) ) ),
			'empty query method' => array( array( 'query' => array( '_method' => null ) ) ),
			'body method'        => array( array( 'body' => array( '_method' => 'POST' ) ) ),
			'header method'      => array( array( 'server' => array( 'HTTP_X_HTTP_METHOD_OVERRIDE' => '' ) ) ),
		);
	}

	/**
	 * Effective method/route/parameter changes cannot widen the purpose scope.
	 *
	 * @dataProvider effective_requests
	 * @param array<string, mixed> $request Effective native request.
	 */
	public function test_effective_requests_are_checked_after_initialization( array $request ): void {
		self::assertSame(
			array(
				'authentication_denied' => false,
				'denied'                => array( true ),
				'writes'                => 0,
			),
			self::run_scope( array( 'requests' => array( $request + array( 'route' => '/linker/v1/publication/jobs/claim' ) ) ) )
		);
	}

	/**
	 * Effective native request cases.
	 *
	 * @return array<string, array{array<string, mixed>}>
	 */
	public static function effective_requests(): array {
		return array(
			'effective GET'  => array( array( 'method' => 'GET' ) ),
			'JSON method'    => array( array( 'params' => array( '_method' => 'POST' ) ) ),
			'null method'    => array( array( 'params' => array( '_method' => null ) ) ),
			'header method'  => array( array( 'headers' => array( 'x-http-method-override' => '' ) ) ),
			'embed'          => array( array( 'params' => array( '_embed' => false ) ) ),
			'batch'          => array( array( 'route' => '/batch/v1' ) ),
			'manifest GET'   => array(
				array(
					'method' => 'GET',
					'route'  => '/linker/v1/publication/manifest',
				),
			),
			'prefix sibling' => array( array( 'route' => '/linker/v1/publication/jobs/claim/extra' ) ),
			'trailing slash' => array( array( 'route' => '/linker/v1/publication/jobs/claim/' ) ),
			'case alias'     => array( array( 'route' => '/linker/v1/publication/jobs/Claim' ) ),
		);
	}

	/** A verified key's late native refusal cannot fall through to an anonymous public endpoint. */
	public function test_late_authentication_refusal_still_restricts_the_verified_purpose(): void {
		self::assertSame(
			array(
				'authentication_denied' => false,
				'denied'                => array( true ),
				'writes'                => 0,
			),
			self::run_scope(
				array(
					'raw_method'     => 'GET',
					'native_success' => false,
					'late_failure'   => true,
					'requests'       => array(
						array(
							'method' => 'GET',
							'route'  => '/wc/store/v1/products',
						),
					),
				)
			)
		);
	}

	/**
	 * Internal calls before the main scope filter cannot spend its HTTP permission.
	 *
	 * @dataProvider early_children
	 * @param array<string, mixed> $timing Native filter timing.
	 */
	public function test_early_internal_jobs_are_refused_without_blocking_the_http_job( array $timing ): void {
		self::assertSame(
			array(
				'authentication_denied' => false,
				'denied'                => array( false ),
				'writes'                => 1,
				'children_denied'       => array( true ),
			),
			self::run_scope( $timing + array( 'requests' => array( array( 'route' => '/linker/v1/publication/jobs/claim' ) ) ) )
		);
	}

	/**
	 * Native pre-dispatch and post-authentication entry timings.
	 *
	 * @return array<string, array{array<string, mixed>}>
	 */
	public static function early_children(): array {
		return array(
			'pre-dispatch at 15' => array(
				array(
					'early_phase'    => 'dispatch',
					'early_priority' => 15,
				),
			),
			'pre-dispatch at -1' => array(
				array(
					'early_phase'    => 'dispatch',
					'early_priority' => -1,
				),
			),
			'after auth at 115'  => array( array( 'early_phase' => 'authentication' ) ),
			'same request'       => array(
				array(
					'early_phase' => 'dispatch',
					'early_kind'  => 'same_request',
				),
			),
			'new server'         => array(
				array(
					'early_phase' => 'dispatch',
					'early_kind'  => 'new_server',
				),
			),
			'nested serve'       => array(
				array(
					'early_phase' => 'dispatch',
					'early_kind'  => 'nested_serve',
				),
			),
			'auth new server'    => array(
				array(
					'early_phase' => 'authentication',
					'early_kind'  => 'new_server',
				),
			),
			'auth nested serve'  => array(
				array(
					'early_phase' => 'authentication',
					'early_kind'  => 'nested_serve',
				),
			),
		);
	}

	/** Unrelated native credentials/cookies retain their behavior, even with forged purpose input. */
	public function test_scope_comes_only_from_the_native_successful_item(): void {
		foreach ( array(
			array( 'app_id' => '8a48d024-fb4d-4fd0-87a8-f9f74d3c1841' ),
			array(
				'native_success' => false,
				'verified'       => false,
			),
		) as $identity ) {
			self::assertSame(
				array(
					'authentication_denied' => false,
					'denied'                => array( false, false ),
					'writes'                => 2,
				),
				self::run_scope(
					$identity + array(
						'query'    => array( 'app_id' => '6c50fdd8-1640-4d5e-9ac8-05fefd9aa290' ),
						'requests' => array(
							array( 'route' => '/linker-test/v1/write' ),
							array(
								'route'  => '/linker-test/v1/read',
								'method' => 'GET',
							),
						),
					)
				)
			);
		}
		self::assertSame(
			array(
				'authentication_denied' => false,
				'denied'                => array( false ),
				'writes'                => 1,
			),
			self::run_scope( array( 'requests' => array( array( 'route' => '/linker/v1/publication/jobs/ack' ) ) ) )
		);
	}

	/**
	 * Runs the public hook seam in an isolated PHP process.
	 *
	 * @param array<string, mixed> $scenario Native authentication and requests.
	 * @return array<string, mixed>
	 */
	private static function run_scope( array $scenario ): array {
		$pipes   = array();
		$process = proc_open(
			array( PHP_BINARY, dirname( __DIR__ ) . '/fixtures/publication-worker-unit.php' ),
			array(
				0 => array( 'pipe', 'r' ),
				1 => array( 'pipe', 'w' ),
				2 => array( 'pipe', 'w' ),
			),
			$pipes
		);
		self::assertIsResource( $process );
		fwrite( $pipes[0], json_encode( $scenario, JSON_THROW_ON_ERROR ) );
		fclose( $pipes[0] );
		$output = stream_get_contents( $pipes[1] );
		$error  = stream_get_contents( $pipes[2] );
		fclose( $pipes[1] );
		fclose( $pipes[2] );
		self::assertSame( 0, proc_close( $process ), $error );
		return json_decode( $output, true, 512, JSON_THROW_ON_ERROR );
	}
}
