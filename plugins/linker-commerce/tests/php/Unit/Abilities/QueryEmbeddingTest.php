<?php
/**
 * Tests for the query embedding client's provider law and request shape.
 *
 * @package Linker\Commerce
 */

declare( strict_types=1 );

namespace Linker\Commerce\Tests\Unit\Abilities;

use Linker\Commerce\Abilities\QueryEmbedding;
use Linker\Commerce\Abilities\QueryEmbeddingTestShims;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * OpenRouter by default; AIHubMix only behind the explicit switch; failures
 * retry and surface through error_log.
 *
 * @covers \Linker\Commerce\Abilities\QueryEmbedding
 */
final class QueryEmbeddingTest extends TestCase {

	/**
	 * The lines error_log received, captured through the shim below.
	 *
	 * @var list<string>
	 */
	public static array $logged = array();

	/**
	 * Reset provider credentials to the OpenRouter default.
	 */
	public function setUp(): void {
		parent::setUp();
		require_once __DIR__ . '/../../Support/EmbeddingShimsKnobs.php';
		require_once __DIR__ . '/../../Support/EmbeddingShims.php';
		QueryEmbeddingTestShims::$provider = null;
		QueryEmbeddingTestShims::$logged   = array();
		$_ENV['OPENROUTER_API_KEY']        = 'test-key';
		$_ENV['OPENROUTER_BASE_URL']       = '';
		$_ENV['AIHUBMIX_API_KEY']          = '';
		$_ENV['AIHUBMIX_BASE_URL']         = '';
	}

	/**
	 * A response the wp_remote_post double returns.
	 *
	 * @param string $body Body.
	 * @param int    $code Status.
	 * @return array<string, mixed>
	 */
	private static function response( string $body, int $code ): array {
		return array(
			'body'     => $body,
			'response' => array( 'code' => $code ),
		);
	}

	/**
	 * The default provider posts to OpenRouter with its model id.
	 */
	public function test_the_default_provider_is_openrouter(): void {
		$seen = array();
		WP_Mock::userFunction( 'wp_json_encode' )->andReturnUsing( 'json_encode' );
		WP_Mock::userFunction( 'wp_remote_post' )->andReturnUsing(
			function ( $url, $args ) use ( &$seen ) {
				$seen['url']  = $url;
				$seen['body'] = json_decode( (string) $args['body'], true );
				return QueryEmbeddingTest::response( '{"data":[{"embedding":[0.25]}]}', 200 );
			}
		);
		WP_Mock::userFunction( 'wp_remote_retrieve_body' )->andReturnUsing(
			static fn( $response ) => $response['body']
		);
		WP_Mock::userFunction( 'wp_remote_retrieve_response_code' )->andReturnUsing(
			static fn( $response ) => $response['response']['code']
		);
		WP_Mock::userFunction( 'is_wp_error' )->andReturn( false );

		$vector = $this->embed( 'which battery' );

		$this->assertSame( array( 0.25 ), $vector, 'the embedding decodes' );
		$this->assertSame( 'https://openrouter.ai/api/v1/embeddings', $seen['url'] );
		$this->assertSame( 'google/gemini-embedding-2', $seen['body']['model'] );
		$this->assertSame(
			'task: question answering | query: which battery',
			$seen['body']['input'][0]
		);
	}

	/**
	 * AIHubMix serves only behind the explicit switch, with its model id.
	 */
	public function test_aihubmix_serves_only_behind_the_switch(): void {
		QueryEmbeddingTestShims::$provider = 'aihubmix';
		$_ENV['AIHUBMIX_API_KEY']          = 'legacy-key';
		$_ENV['AIHUBMIX_BASE_URL']         = 'https://aihubmix.example';
		$seen                              = array();
		WP_Mock::userFunction( 'wp_json_encode' )->andReturnUsing( 'json_encode' );
		WP_Mock::userFunction( 'wp_remote_post' )->andReturnUsing(
			function ( $url, $args ) use ( &$seen ) {
				$seen['url']  = $url;
				$seen['body'] = json_decode( (string) $args['body'], true );
				return QueryEmbeddingTest::response( '{"data":[{"embedding":[0.5]}]}', 200 );
			}
		);
		WP_Mock::userFunction( 'wp_remote_retrieve_body' )->andReturnUsing(
			static fn( $response ) => $response['body']
		);
		WP_Mock::userFunction( 'wp_remote_retrieve_response_code' )->andReturnUsing(
			static fn( $response ) => $response['response']['code']
		);
		WP_Mock::userFunction( 'is_wp_error' )->andReturn( false );

		$this->embed( 'q' );

		$this->assertSame( 'https://aihubmix.example/v1/embeddings', $seen['url'] );
		$this->assertSame( 'gemini-embedding-2', $seen['body']['model'] );
	}

	/**
	 * Transport failures retry three times, then surface through error_log.
	 */
	public function test_transport_failures_retry_then_log(): void {
		$calls = 0;
		WP_Mock::userFunction( 'wp_json_encode' )->andReturnUsing( 'json_encode' );
		WP_Mock::userFunction( 'wp_remote_post' )->andReturnUsing(
			function () use ( &$calls ) {
				$calls++;
				return QueryEmbeddingTest::response( '', 503 );
			}
		);
		WP_Mock::userFunction( 'wp_remote_retrieve_body' )->andReturnUsing(
			static fn( $response ) => $response['body']
		);
		WP_Mock::userFunction( 'wp_remote_retrieve_response_code' )->andReturnUsing(
			static fn( $response ) => $response['response']['code']
		);
		WP_Mock::userFunction( 'is_wp_error' )->andReturn( false );

		$vector = $this->embed( 'q' );

		$this->assertNull( $vector );
		$this->assertSame( 3, $calls, 'three attempts before giving up' );
		$this->assertCount( 1, QueryEmbeddingTestShims::$logged );
		$this->assertStringContainsString( '[linker-embedding]', QueryEmbeddingTestShims::$logged[0] );
	}

	/**
	 * Loads the namespace shims once, then runs the client.
	 *
	 * @param string $query Query text.
	 * @return list<float>|null
	 */
	private function embed( string $query ) {
		static $loaded = false;
		if ( ! $loaded ) {
			$loaded = true;
			require_once __DIR__ . '/../../Support/EmbeddingShimsKnobs.php';
			require_once __DIR__ . '/../../Support/EmbeddingShims.php';
		}
		return ( new QueryEmbedding() )->vector( $query );
	}
}
