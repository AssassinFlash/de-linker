<?php
/**
 * Origin probe privacy, verification and consumer contract.
 *
 * @package Linker\Mu
 */

declare( strict_types = 1 );

namespace Linker\Mu\Tests\Unit;

use Linker\Mu\CrawlerTelemetry;
use PHPUnit\Framework\TestCase;

// phpcs:disable WordPress.WP.AlternativeFunctions -- Unit fixtures use isolated local files.
/**
 * Crawler Telemetry Contract v1.
 *
 * @covers \Linker\Mu\CrawlerTelemetry
 * @runTestsInSeparateProcesses
 * @preserveGlobalState disabled
 */
final class CrawlerTelemetryTest extends TestCase {
	/** Directory isolated to this UTC bucket test.
	 *
	 * @var string
	 */
	private string $dir;

	/** Load the plugin for a normal browser before creating fixture storage. */
	protected function setUp(): void {
		parent::setUp();
		require dirname( __DIR__ ) . '/fixtures/crawler-telemetry.php';
		if ( ! defined( 'DAY_IN_SECONDS' ) ) {
			define( 'DAY_IN_SECONDS', 86400 ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- WordPress time constant.
		}
		$_SERVER['HTTP_USER_AGENT'] = 'Mozilla/5.0 Chrome/143.0.0.0 Safari/537.36';
		require dirname( __DIR__, 3 ) . '/linker-crawler-telemetry.php';
		$this->dir = sys_get_temp_dir() . '/linker-crawler-unit-' . bin2hex( random_bytes( 8 ) );
	}

	/** Remove only the current test’s bucket and protection files. */
	protected function tearDown(): void {
		if ( is_dir( $this->dir ) ) {
			foreach ( array_diff( (array) scandir( $this->dir ), array( '.', '..' ) ) as $file ) {
				unlink( $this->dir . '/' . $file );
			}
			rmdir( $this->dir );
		}
		parent::tearDown();
	}

	/** A human request does not initialize the store; unrelated agents remain untracked. */
	public function test_human_exits_before_storage(): void {
		self::assertSame( '', CrawlerTelemetry::agent( 'Mozilla/5.0 Safari/537.36' ) );
		self::assertSame( '', CrawlerTelemetry::agent( 'Applebot-Extended/1.0' ) );
		CrawlerTelemetry::record( $this->dir, '', '/contact/', '192.0.2.77', 200, 10, false );
		self::assertDirectoryDoesNotExist( $this->dir );
	}

	/** All aliases are normalized, counts and percentiles survive aggregation, private input is dropped. */
	public function test_contract(): void {
		mkdir( $this->dir );
		$cutoff = gmdate( 'Y-m-d', time() - 35 * DAY_IN_SECONDS );
		$keep   = gmdate( 'Y-m-d', time() - 34 * DAY_IN_SECONDS );
		file_put_contents( "$this->dir/$cutoff.json", '{}' );
		file_put_contents( "$this->dir/$keep.json", '{}' );
		file_put_contents( "$this->dir/cidrs.json", '{"Googlebot":["192.0.2.0/24"]}' );
		$agents = array( 'Googlebot', 'bingbot', 'Applebot', 'OAI-SearchBot', 'ChatGPT-User', 'GPTBot', 'ClaudeBot', 'Claude-SearchBot', 'Claude-User', 'PerplexityBot', 'Perplexity-User' );
		$codes  = array( 200, 206, 301, 404, 410, 429, 503, 400, 200, 200, 200 );
		foreach ( $agents as $i => $agent ) {
			$detected = CrawlerTelemetry::agent( "Mozilla/5.0 (compatible; $agent/1.0)" );
			self::assertSame( $agent, $detected );
			CrawlerTelemetry::record( $this->dir, $detected, '/sku/?secret=private#fragment', '192.0.2.77', $codes[ $i ], ( $i + 1 ) * 10, false );
		}

		self::assertFileDoesNotExist( "$this->dir/$cutoff.json" );
		self::assertFileExists( "$this->dir/$keep.json" );
		self::assertStringContainsString( 'Require all denied', (string) file_get_contents( "$this->dir/.htaccess" ) );
		self::assertSame( '', file_get_contents( "$this->dir/index.html" ) );
		$result = CrawlerTelemetry::report( $this->dir, 15, time() );
		self::assertSame( '1.0', $result['contractVersion'] );
		self::assertCount( 8, $result['byFamily'] );
		self::assertCount( 15, $result['daily'] );
		self::assertSame( 0, $result['daily'][0]['totalRequests'] );
		self::assertSame( 11, $result['totals']['requests'] );
		self::assertSame( 9.1, $result['totals']['verifiedRatioPct'] );
		self::assertSame( 60, $result['totals']['p50Ms'] );
		self::assertSame( 110, $result['totals']['p95Ms'] );
		self::assertSame( array( 200, 206, 301, 404, 410, 429, '5xx', 'other' ), array_keys( $result['totals']['statusBuckets'] ) );
		self::assertSame( 3, $result['daily'][14]['byFamily']['ClaudeBot'] );
		self::assertSame( 2, $result['daily'][14]['byFamily']['PerplexityBot'] );
		self::assertSame( '/sku/', $result['topCrawledPaths'][0]['path'] );
		self::assertSame( 11, $result['topCrawledPaths'][0]['hits'] );
		self::assertCount( 5, $result['topErrorPaths'] );
		self::assertFalse( $result['privacyGuarantees']['storesVisitorIp'] );
		foreach ( array_diff( (array) scandir( $this->dir ), array( '.', '..' ) ) as $file ) {
			$data = (string) file_get_contents( "$this->dir/$file" );
			self::assertStringNotContainsString( '192.0.2.77', $data );
			self::assertStringNotContainsString( 'private', $data );
			self::assertStringNotContainsString( 'fragment', $data );
		}
	}

	/** Saturated buckets keep accepting new frequent paths and drop contended samples. */
	public function test_bounded_storage(): void {
		for ( $i = 0; $i < 160; ++$i ) {
			CrawlerTelemetry::record( $this->dir, 'GPTBot', '/old-' . $i, '192.0.2.1', 404, 1, false );
		}
		for ( $i = 0; $i < 260; ++$i ) {
			CrawlerTelemetry::record( $this->dir, 'GPTBot', '/frequent', '192.0.2.1', 404, $i, false );
		}
		$file = $this->dir . '/' . gmdate( 'Y-m-d' ) . '.json';
		$data = json_decode( (string) file_get_contents( $file ), true );
		self::assertCount( 150, $data['paths'] );
		self::assertCount( 100, $data['errors'] );
		self::assertCount( 256, $data['families']['GPTBot']['durations'] );
		self::assertCount( 32, $data['paths']['/frequent']['durations'] );
		$lock = fopen( $file, 'r' );
		self::assertIsResource( $lock );
		flock( $lock, LOCK_SH );
		try {
			CrawlerTelemetry::record( $this->dir, 'GPTBot', '/contended', '192.0.2.1', 503, 1, false );
		} finally {
			fclose( $lock );
		}
		$result = CrawlerTelemetry::report( $this->dir, 1, time() );
		self::assertSame( 420, $result['totals']['requests'] );
		self::assertSame( 260, $result['topErrorPaths'][0]['hits'] );
		self::assertCount( 25, $result['topCrawledPaths'] );
	}

	/** Missing configuration, missing or incorrect keys and valid requests keep the private cache policy. */
	public function test_permission_and_headers(): void {
		$request = new \WP_REST_Request( 'GET', '/linker/v1/crawler-telemetry' );
		$result  = CrawlerTelemetry::permission( $request );
		self::assertInstanceOf( \WP_Error::class, $result );
		self::assertSame( 403, $result->get_error_data()['status'] );
		$key = bin2hex( random_bytes( 32 ) );
		define( 'LINKER_CRAWLER_TELEMETRY_KEY', $key ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- Synthetic origin configuration.
		foreach ( array( '', 'wrong' ) as $wrong ) {
			$request->set_header( 'x-linker-telemetry-key', $wrong );
			$result = CrawlerTelemetry::permission( $request );
			self::assertInstanceOf( \WP_Error::class, $result );
			self::assertSame( 403, $result->get_error_data()['status'] );
		}
		$request->set_header( 'x-linker-telemetry-key', $key );
		self::assertTrue( CrawlerTelemetry::permission( $request ) );
		$response = CrawlerTelemetry::headers( new \WP_REST_Response(), new \WP_REST_Server(), $request );
		self::assertSame( 'no-store, private, max-age=0', $response->get_headers()['Cache-Control'] );
		self::assertSame( 'no-cache', $response->get_headers()['X-LiteSpeed-Cache-Control'] );
		self::assertSame( 'noindex, nofollow', $response->get_headers()['X-Robots-Tag'] );
	}

	/** CIDR matching, forward-confirmed DNS and the daily query budget. */
	public function test_verification(): void {
		self::assertTrue( CrawlerTelemetry::matches( '2001:db8:8000::1', array( '2001:db8:8000::/33' ) ) );
		self::assertFalse( CrawlerTelemetry::matches( '2001:db8:7fff::1', array( '2001:db8:8000::/33' ) ) );
		$check   = new \ReflectionMethod( CrawlerTelemetry::class, 'dns_verdict' );
		$lookups = array();
		$lookup  = static function ( array $query ) use ( &$lookups ): array {
			$lookups[] = $query;
			return '-x' === $query[0] ? array( 'sample.googlebot.com.' ) : array( '2001:db8::f' );
		};
		self::assertTrue( $check->invoke( null, 'Googlebot', '2001:db8::f', $lookup ) );
		self::assertSame( array( 'sample.googlebot.com.', 'AAAA' ), $lookups[1] );
		self::assertFalse( $check->invoke( null, 'Googlebot', '2001:db8::10', $lookup ) );
		self::assertFalse( $check->invoke( null, 'Applebot', '2001:db8::f', $lookup ) );

		mkdir( $this->dir );
		$cache = array(
			'date'    => gmdate( 'Y-m-d' ),
			'salt'    => 'unit-salt',
			'results' => array_fill_keys( range( 1, 50 ), false ),
		);
		file_put_contents( "$this->dir/rdns.json", (string) json_encode( $cache ) );
		CrawlerTelemetry::record( $this->dir, 'Googlebot', '/sku/', '8.8.8.8', 200, 1, true );
		self::assertSame( $cache, json_decode( (string) file_get_contents( "$this->dir/rdns.json" ), true ) );
		self::assertSame( 0, CrawlerTelemetry::report( $this->dir, 1, time() )['totals']['verifiedRequests'] );
	}

	/** Failed or invalid feeds retain previous prefixes and the same day never refetches. */
	public function test_refresh(): void {
		mkdir( $this->dir );
		$file = "$this->dir/cidrs.json";
		file_put_contents( $file, '{"GPTBot":["2001:db8::/32"],"Applebot":["192.0.2.0/25"]}' );
		touch( $file, time() - 2 * DAY_IN_SECONDS );
		// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals -- Isolated native HTTP double.
		$GLOBALS['linker_crawler_fixture_reads'] = 0;
		// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals -- Isolated native HTTP double.
		$GLOBALS['linker_crawler_fixture_feeds'] = array(
			'https://openai.com/searchbot.json' => '{"prefixes":[{"ipv4Prefix":"198.51.100.0/26"}]}',
			'https://openai.com/gptbot.json'    => '{"prefixes":[{"ipv4Prefix":"invalid"}]}',
		);
		CrawlerTelemetry::refresh( $this->dir );
		$cached = json_decode( (string) file_get_contents( $file ), true );
		self::assertSame( array( '198.51.100.0/26' ), $cached['OAI-SearchBot'] );
		self::assertSame( array( '2001:db8::/32' ), $cached['GPTBot'] );
		self::assertSame( array( '192.0.2.0/25' ), $cached['Applebot'] );
		$reads = $GLOBALS['linker_crawler_fixture_reads'];
		self::assertGreaterThan( 0, $reads );
		CrawlerTelemetry::refresh( $this->dir );
		self::assertSame( $reads, $GLOBALS['linker_crawler_fixture_reads'] );
	}
}
