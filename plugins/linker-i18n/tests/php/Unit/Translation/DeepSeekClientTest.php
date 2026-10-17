<?php
/**
 * Tests for the DeepSeek client.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit\Translation;

use Linker\I18n\Translation\DeepSeekClient;
use Linker\I18n\Translation\Rules;
use Linker\I18n\Translation\TranslationFailed;
use Mockery;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for DeepSeekClient.
 *
 * @covers \Linker\I18n\Translation\DeepSeekClient
 * @covers \Linker\I18n\Translation\TranslationFailed
 */
final class DeepSeekClientTest extends TestCase {

	/**
	 * Mocks the JSON and escaping helpers.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::passthruFunction( 'esc_html' );
		WP_Mock::userFunction(
			'wp_json_encode',
			array(
				'return' => static fn( $data, int $flags = 0 ) => json_encode( $data, $flags ), // phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- stands in for wp_json_encode.
			)
		);
	}

	/**
	 * A client with the plugin's rules.
	 *
	 * @param string $key API key.
	 */
	private function client( string $key = 'test-key' ): DeepSeekClient {
		return new DeepSeekClient( Rules::load( dirname( __DIR__, 4 ) . '/data' ), $key );
	}

	/**
	 * Without a key nothing is sent and the failure is not passing.
	 */
	public function test_without_key_nothing_is_sent(): void {
		WP_Mock::userFunction( 'wp_remote_post', array( 'times' => 0 ) );
		$client = $this->client( '' );

		$this->assertFalse( $client->available() );
		try {
			$client->translate( array( 'Hello' ) );
			$this->fail( 'No exception.' );
		} catch ( TranslationFailed $failure ) {
			$this->assertSame( 'DEEPSEEK_API_KEY is not set', $failure->getMessage() );
			$this->assertFalse( $failure->transient );
		}
	}

	/**
	 * The request: DeepSeek's endpoint and model, thinking off, JSON output,
	 * the key as bearer token, the segments as JSON; the answer's translations come back.
	 */
	public function test_request_and_answer(): void {
		$sent = null;
		WP_Mock::userFunction(
			'wp_remote_post',
			array(
				'times'  => 1,
				'return' => static function ( string $url, array $args ) use ( &$sent ) {
					$sent = array( $url, $args );
					return array( 'response' => array( 'code' => 200 ) );
				},
			)
		);
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => false ) );
		WP_Mock::userFunction( 'wp_remote_retrieve_response_code', array( 'return' => 200 ) );
		WP_Mock::userFunction(
			'wp_remote_retrieve_body',
			array( 'return' => (string) json_encode( array( 'choices' => array( array( 'message' => array( 'content' => '{"translations":["<t1>AC-Nennleistung:</t1> 10 kW"]}' ) ) ) ) ) ) // phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- a canned answer.
		);

		$this->assertSame( array( '<t1>AC-Nennleistung:</t1> 10 kW' ), $this->client()->translate( array( '<t1>Rated AC power:</t1> 10 kW' ) ) );

		$this->assertIsArray( $sent );
		list( $url, $args ) = $sent;
		$body               = json_decode( $args['body'], true );
		$this->assertSame( 'https://api.deepseek.com/chat/completions', $url );
		$this->assertSame( 'Bearer test-key', $args['headers']['Authorization'] );
		$this->assertSame( 'deepseek-flash', $body['model'] );
		$this->assertSame( array( 'type' => 'disabled' ), $body['thinking'] );
		$this->assertSame( array( 'type' => 'json_object' ), $body['response_format'] );
		$this->assertStringContainsString( 'json', $body['messages'][0]['content'] );
		$this->assertStringContainsString( 'datasheet → Datenblatt', $body['messages'][0]['content'] );
		$this->assertSame( array( 'segments' => array( '<t1>Rated AC power:</t1> 10 kW' ) ), json_decode( $body['messages'][1]['content'], true ) );
	}

	/**
	 * Production always uses the official endpoint, even with a stale test override.
	 *
	 * @runInSeparateProcess
	 * @preserveGlobalState disabled
	 */
	public function test_production_ignores_endpoint_override(): void {
		define( 'LINKER_I18N_DEEPSEEK_ENDPOINT', 'http://127.0.0.1:9999/' );
		WP_Mock::userFunction( 'wp_get_environment_type', array( 'return' => 'production' ) );
		$this->test_request_and_answer();
	}

	/**
	 * HTTP status and answer shape decide whether a later attempt may succeed.
	 *
	 * @return array<string, array{int, string, bool}>
	 */
	public function provide_failures(): array {
		return array(
			'rate limit'    => array( 429, '', true ),
			'server error'  => array( 503, '', true ),
			'no balance'    => array( 402, '', false ),
			'bad key'       => array( 401, '', false ),
			'empty content' => array( 200, '{"choices":[{"message":{"content":""}}]}', true ),
			'wrong count'   => array( 200, '{"choices":[{"message":{"content":"{\"translations\":[\"a\",\"b\"]}"}}]}', true ),
		);
	}

	/**
	 * A failed answer.
	 *
	 * @dataProvider provide_failures
	 *
	 * @param int    $status    HTTP status.
	 * @param string $body      Body.
	 * @param bool   $transient Whether the failure may pass.
	 */
	public function test_failed_answers( int $status, string $body, bool $transient ): void {
		WP_Mock::userFunction( 'wp_remote_post', array( 'return' => array() ) );
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => false ) );
		WP_Mock::userFunction( 'wp_remote_retrieve_response_code', array( 'return' => $status ) );
		WP_Mock::userFunction( 'wp_remote_retrieve_body', array( 'return' => $body ) );

		try {
			$this->client()->translate( array( 'Hello' ) );
			$this->fail( 'No exception.' );
		} catch ( TranslationFailed $failure ) {
			$this->assertSame( $transient, $failure->transient );
		}
	}

	/**
	 * A network error may pass.
	 */
	public function test_network_error_is_transient(): void {
		$error = Mockery::mock( 'WP_Error' );
		$error->shouldReceive( 'get_error_message' )->andReturn( 'timed out' );
		WP_Mock::userFunction( 'wp_remote_post', array( 'return' => $error ) );
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => true ) );

		$this->expectException( TranslationFailed::class );
		$this->expectExceptionMessage( 'DeepSeek unreachable' );

		$this->client()->translate( array( 'Hello' ) );
	}
}
