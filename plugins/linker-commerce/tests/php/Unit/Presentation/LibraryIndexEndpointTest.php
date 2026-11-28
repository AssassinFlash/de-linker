<?php
/**
 * Origin-cache eligibility for the public document search index.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Presentation\LibraryIndexEndpoint;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Public cache permission and WordPress credentials.
 *
 * @covers \Linker\Commerce\Presentation\LibraryIndexEndpoint
 */
final class LibraryIndexEndpointTest extends TestCase {
	/**
	 * Requests accepted by the REST server do not all select a public cache entry.
	 *
	 * @return array<string,array{string,string,bool,string,bool}>
	 */
	public static function requests(): array {
		return array(
			'english'         => array( '/wp-json/linker/v1/library-index?lang=en', 'en', false, '', true ),
			'german'          => array( '/wp-json/linker/v1/library-index?lang=de', 'de', false, '', true ),
			'other parameter' => array( '/wp-json/linker/v1/library-index?lang=en&_fields=skus', 'en', false, '', false ),
			'other route'     => array( '/wp-json/other/v1/page?lang=en', 'en', false, '', false ),
			'logged in'       => array( '/wp-json/linker/v1/library-index?lang=en', 'en', true, '', false ),
			'credential'      => array( '/wp-json/linker/v1/library-index?lang=en', 'en', false, 'authorization', false ),
			'cookie'          => array( '/wp-json/linker/v1/library-index?lang=en', 'en', false, 'cookie', false ),
			'nonce'           => array( '/wp-json/linker/v1/library-index?lang=en', 'en', false, 'x-wp-nonce', false ),
		);
	}

	/**
	 * Only the two uncredentialed browser GET URLs opt into LiteSpeed's public tag and TTL.
	 *
	 * @dataProvider requests
	 * @param string $uri Exact URI.
	 * @param string $lang Validated language.
	 * @param bool   $logged_in Active WordPress user.
	 * @param string $header Credential header.
	 * @param bool   $cacheable Whether the shared cache may store this response.
	 */
	public function test_index_cache( string $uri, string $lang, bool $logged_in, string $header, bool $cacheable ): void {
		$server                    = $_SERVER;
		$_SERVER['REQUEST_URI']    = $uri;
		$_SERVER['REQUEST_METHOD'] = 'GET';
		WP_Mock::passthruFunction( 'wp_unslash' );
		WP_Mock::userFunction( 'rest_url' )->andReturn( 'https://linker.test/wp-json/linker/v1/library-index' );
		WP_Mock::userFunction( 'wp_parse_url' )->andReturnUsing( 'parse_url' );
		WP_Mock::userFunction( 'is_user_logged_in' )->andReturn( $logged_in );
		if ( $cacheable ) {
			WP_Mock::expectAction( 'litespeed_tag_add', 'PT.product' );
			WP_Mock::expectAction( 'litespeed_control_force_public', 'Public library index' );
			WP_Mock::expectAction( 'litespeed_control_set_ttl', HOUR_IN_SECONDS );
		}
		$request  = new \WP_REST_Request( 'GET', '/linker/v1/library-index' );
		$response = new \WP_REST_Response( array() );
		if ( '' !== $header ) {
			$request->set_header( $header, 'present' );
		}
		try {
			( new \ReflectionMethod( LibraryIndexEndpoint::class, 'cache_policy' ) )->invoke( null, $request, $response, $lang );
			$headers = $response->get_headers();
			$this->assertSame( $cacheable ? 'public, max-age=3600' : 'no-cache', $headers['X-LiteSpeed-Cache-Control'] );
			$this->assertSame( $cacheable ? 'public, max-age=3600, stale-while-revalidate=600' : 'private, no-store, max-age=0', $headers['Cache-Control'] );
			$this->assertConditionsMet();
		} finally {
			$_SERVER = $server;
		}
	}
}
