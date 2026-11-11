<?php
/**
 * The commercial sizing seam carries exactly the engine's own input contract.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Planner\CommercialDesign;
use Linker\Tools\Planner\Principal;
use WP_Error;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * The engine sizes commercial storage only from a load profile plus a target
 * peak, so this seam must carry both and nothing the engine did not declare.
 *
 * @covers \Linker\Tools\Planner\CommercialDesign
 */
final class CommercialDesignTest extends TestCase {

	/**
	 * The engine address this seam reads, per test.
	 *
	 * @var string
	 */
	private string $engine_url = '';

	/** A configured endpoint and service token, without a live host. */
	public function setUp(): void {
		parent::setUp();
		if ( ! defined( 'LINKER_GENIE_SERVICE_TOKEN' ) ) {
			define( 'LINKER_GENIE_SERVICE_TOKEN', 'unit-test-only' ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- Existing native service constant; a synthetic unit-test value only.
		}
		$this->engine_url = 'https://engine.test';
		WP_Mock::userFunction( 'get_option' )->with( 'linker_engine_url', '' )->andReturnUsing(
			fn (): string => $this->engine_url
		);
		WP_Mock::userFunction( '__' )->andReturnUsing( static fn ( string $text ): string => $text );
		WP_Mock::userFunction( 'is_wp_error' )->andReturnUsing( static fn ( $value ): bool => $value instanceof WP_Error );
		WP_Mock::userFunction( 'wp_json_encode' )->andReturnUsing(
			static fn ( $value, $flags = 0 ): string => (string) json_encode( $value, (int) $flags ) // phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- The mock stands in for the WordPress function itself.
		);
		WP_Mock::userFunction( 'wp_remote_retrieve_response_code' )->andReturnUsing( static fn ( array $reply ): int => $reply['status'] );
		WP_Mock::userFunction( 'wp_remote_retrieve_body' )->andReturnUsing( static fn ( array $reply ): string => $reply['body'] );
	}

	/**
	 * One engine reply, recording the request the seam built.
	 *
	 * @param int                 $status Engine status.
	 * @param string              $body   Engine body.
	 * @param array<string,mixed> $sent   Receives the last request.
	 */
	private function replying( int $status, string $body, array &$sent = array() ): CommercialDesign {
		return new CommercialDesign(
			static function ( string $url, array $args ) use ( $status, $body, &$sent ): array {
				$sent = array(
					'url'     => $url,
					'args'    => $args,
					'command' => json_decode( $args['body'], true ),
				);
				return array(
					'status' => $status,
					'body'   => $body,
				);
			}
		);
	}

	/**
	 * The browser command whose exact fields the engine declares.
	 *
	 * @return array<string,mixed>
	 */
	private function command(): array {
		return array(
			'plz'                 => '80331',
			'grid_connection_kva' => 150,
			'annual_kwh'          => 380000,
			'goals'               => array( 'peak_shaving' ),
			'peak_kw'             => 140,
			'target_peak_kw'      => 70,
			'load_profile_csv'    => "40\n60\n80",
			'load_profile_unit'   => 'kW',
			'locale'              => 'en',
		);
	}

	/** Both engine-required inputs reach the engine's own design route. */
	public function test_profile_and_target_peak_reach_the_design_route(): void {
		$sent   = array();
		$design = $this->replying( 200, '{"status":"sized"}', $sent );
		$reply  = $design->forward( new Principal( 'user', 'wp:1:user:1' ), $this->command() );
		self::assertIsArray( $reply );
		self::assertSame( 200, $reply['status'] );
		self::assertSame( 'https://engine.test/design/commercial', $sent['url'] );
		self::assertSame( 70.0, $sent['command']['target_peak_kw'] );
		self::assertSame( "40\n60\n80", $sent['command']['load_profile_csv'] );
		self::assertSame( 'kW', $sent['command']['load_profile_unit'] );
		self::assertSame( array( 'peak_shaving' ), $sent['command']['goals'] );
		self::assertSame( 'unit-test-only', $sent['args']['headers']['X-Linker-Service-Token'] );
		self::assertMatchesRegularExpression(
			'/\A[a-f0-9]{64}\z/',
			$sent['args']['headers']['X-Linker-Resource-Subject']
		);
	}

	/** An undeclared field never reaches the engine. */
	public function test_undeclared_fields_are_not_forwarded(): void {
		$sent   = array();
		$design = $this->replying( 200, '{"status":"indicative"}', $sent );
		$design->forward(
			new Principal( 'guest', 'wp:1:guest:abc' ),
			$this->command() + array(
				'anything_else' => 'x',
				'project_route' => '/admin',
			)
		);
		self::assertArrayNotHasKey( 'anything_else', $sent['command'] );
		self::assertArrayNotHasKey( 'project_route', $sent['command'] );
	}

	/**
	 * The engine names a refused profile; the seam names it in the interface's
	 * own vocabulary instead of forwarding English server text.
	 */
	public function test_a_refused_profile_becomes_a_stable_interface_code(): void {
		$cases = array(
			'a load profile needs at least one week of 15-minute values' => 'profile_too_short',
			'the load profile contains negative values' => 'profile_negative',
			'something else entirely'                   => 'profile_invalid',
		);
		foreach ( $cases as $message => $expected ) {
			$body   = (string) wp_json_encode(
				array(
					'detail' => array(
						'error'   => 'load_profile',
						'message' => $message,
					),
				)
			);
			$design = $this->replying( 422, $body );
			$reply  = $design->forward( new Principal( 'guest', 'wp:1:guest:abc' ), $this->command() );
			self::assertIsArray( $reply, $message );
			self::assertSame( 422, $reply['status'], $message );
			self::assertSame(
				array(
					'error' => array( 'code' => $expected ),
				),
				json_decode( $reply['body'], true ),
				$message
			);
		}
	}

	/** A command outside the engine's own contract is refused before dispatch. */
	public function test_invalid_commands_are_refused_before_dispatch(): void {
		$design = new CommercialDesign(
			static function (): array {
				self::fail( 'an invalid command must not reach the engine' );
			}
		);
		$owner  = new Principal( 'guest', 'wp:1:guest:abc' );
		$cases  = array(
			'a postcode that is not German'  => array( 'plz' => 'SW1A 1AA' ),
			'a missing goal list'            => array( 'goals' => array() ),
			'an unknown goal'                => array( 'goals' => array( 'teleport' ) ),
			'a non-positive grid capacity'   => array( 'grid_connection_kva' => 0 ),
			'a capacity past the bound'      => array( 'grid_connection_kva' => 10001 ),
			'a profile of the wrong type'    => array( 'load_profile_csv' => array( 'x' ) ),
			'a target peak that is a string' => array( 'target_peak_kw' => '70' ),
		);
		foreach ( $cases as $label => $patch ) {
			$refusal = $design->forward( $owner, array_merge( $this->command(), $patch ) );
			self::assertInstanceOf( WP_Error::class, $refusal, $label );
			self::assertSame( 'linker_planner_input', $refusal->get_error_code(), $label );
		}
	}

	/** A profile exactly at the engine's own character bound still fits. */
	public function test_the_engine_profile_bound_is_accepted(): void {
		$sent   = array();
		$design = $this->replying( 200, '{"status":"sized"}', $sent );
		$design->forward(
			new Principal( 'guest', 'wp:1:guest:abc' ),
			array_merge( $this->command(), array( 'load_profile_csv' => str_repeat( '1', CommercialDesign::MAX_PROFILE_CHARS ) ) )
		);
		self::assertSame(
			CommercialDesign::MAX_PROFILE_CHARS,
			strlen( $sent['command']['load_profile_csv'] )
		);
	}

	/** The engine's other refusals keep this gateway's stable codes. */
	public function test_engine_status_classes_keep_stable_codes(): void {
		$cases = array(
			409 => 'publication_changed',
			429 => 'limited',
			503 => 'unavailable',
			500 => 'upstream',
		);
		foreach ( $cases as $status => $expected ) {
			$design  = $this->replying( $status, 'not json at all' );
			$refusal = $design->forward( new Principal( 'guest', 'wp:1:guest:abc' ), $this->command() );
			self::assertInstanceOf( WP_Error::class, $refusal, (string) $status );
			self::assertSame( 'linker_planner_' . $expected, $refusal->get_error_code(), (string) $status );
			self::assertSame( $status, $refusal->get_error_data()['status'], (string) $status );
		}
	}

	/** A successful reply that is not JSON is never presented as a design. */
	public function test_a_non_json_success_is_refused(): void {
		$design  = $this->replying( 200, 'not json at all' );
		$refusal = $design->forward( new Principal( 'guest', 'wp:1:guest:abc' ), $this->command() );
		self::assertInstanceOf( WP_Error::class, $refusal );
		self::assertSame( 'linker_planner_invalid_reply', $refusal->get_error_code() );
	}

	/** An unconfigured engine address is a configuration refusal, not a call. */
	public function test_an_unconfigured_engine_is_refused(): void {
		$this->engine_url = '';
		$design           = $this->replying( 200, '{"status":"sized"}' );
		$refusal          = $design->forward( new Principal( 'guest', 'wp:1:guest:abc' ), $this->command() );
		self::assertInstanceOf( WP_Error::class, $refusal );
		self::assertSame( 'linker_planner_configuration', $refusal->get_error_code() );
	}
}
