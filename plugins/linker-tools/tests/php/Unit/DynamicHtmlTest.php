<?php
/**
 * Public HTML cache policy for dynamic pages and query strings.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Cache\DynamicHtml;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Ordinary pages stay cacheable. Query strings and dynamic HTML do not.
 *
 * @covers \Linker\Tools\Cache\DynamicHtml
 */
final class DynamicHtmlTest extends TestCase {

	/**
	 * Homepage and product URLs stay cacheable; query variants do not.
	 */
	public function test_homepage_and_products_stay_cacheable_and_query_strings_do_not(): void {
		$this->assertFalse( DynamicHtml::blocks_public_cache( false, false, false, '/' ) );
		$this->assertFalse( DynamicHtml::blocks_public_cache( false, false, false, '/products/' ) );
		$this->assertFalse( DynamicHtml::blocks_public_cache( false, false, false, '/products/h2-10k-t3/' ) );
		$this->assertFalse( DynamicHtml::blocks_public_cache( false, false, false, '/de/produkte/' ) );

		$this->assertTrue( DynamicHtml::blocks_public_cache( false, false, false, '/?foo=cacheprobe' ) );
		$this->assertTrue( DynamicHtml::blocks_public_cache( false, false, false, '/products/?q=saj' ) );
		$this->assertTrue( DynamicHtml::blocks_public_cache( false, false, false, '/de/produkte/?page=2' ) );
		$this->assertTrue( DynamicHtml::blocks_public_cache( false, false, false, '/solution-configurator/?pv_kwp=5' ) );
	}

	/**
	 * The query check runs after LiteSpeed marks a front-end request cacheable.
	 */
	public function test_query_check_is_hooked_after_the_default_cacheable_mark(): void {
		WP_Mock::expectActionAdded( 'wp', array( DynamicHtml::class, 'front_request' ), 6 );
		WP_Mock::expectFilterAdded( 'rest_post_dispatch', array( DynamicHtml::class, 'history_response' ), 20, 3 );
		DynamicHtml::register();
		$this->assertConditionsMet();
	}

	/**
	 * Standalone Genie history must bypass the full-page cache for every identity.
	 *
	 * @runInSeparateProcess
	 * @preserveGlobalState disabled
	 */
	public function test_genie_history_reads_reach_their_request_owner(): void {
		define( 'REST_REQUEST', true ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- Direct WordPress REST request.
		$native = new \WP_REST_Response( array( 'conversations' => array() ) );
		$public = new \WP_REST_Request( 'GET', '/wc/store/v1/products' );
		$this->assertSame( $native, DynamicHtml::history_response( $native, null, $public ) );
		$this->assertArrayNotHasKey( 'Cache-Control', $native->get_headers() );
		$this->assertFalse( defined( 'DONOTCACHEPAGE' ) );
		foreach ( array( '/linker-ai/v1/genie/conversations', '/linker-ai/v1/genie/conversation/' ) as $path ) {
			$request = new \WP_REST_Request( 'GET', $path );
			$this->assertSame( $native, DynamicHtml::history_response( $native, null, $request ) );
			$this->assertSame( 'no-cache', $native->get_headers()['X-LiteSpeed-Cache-Control'] );
			$this->assertSame( 'no-store, private, max-age=0', $native->get_headers()['Cache-Control'] );
		}
		$this->assertTrue( defined( 'DONOTCACHEPAGE' ) && DONOTCACHEPAGE );
	}

	/**
	 * WordPress can preload route data during an ordinary page render.
	 *
	 * @runInSeparateProcess
	 * @preserveGlobalState disabled
	 */
	public function test_history_preload_does_not_disable_the_enclosing_page_cache(): void {
		$response = new \WP_REST_Response();
		DynamicHtml::history_response( $response, null, new \WP_REST_Request( 'GET', '/linker-ai/v1/genie/conversations' ) );
		$this->assertArrayHasKey( 'X-LiteSpeed-Cache-Control', $response->get_headers() );
		$this->assertFalse( defined( 'DONOTCACHEPAGE' ) );
	}

	/**
	 * Admin, AJAX and REST do not inherit the HTML query exclusion.
	 */
	public function test_admin_ajax_and_rest_are_not_marked_by_the_html_query_rule(): void {
		$this->assertFalse( DynamicHtml::blocks_public_cache( true, false, false, '/wp-admin/edit.php?post_type=page' ) );
		$this->assertFalse( DynamicHtml::blocks_public_cache( false, true, false, '/wp-admin/admin-ajax.php?action=rest-nonce' ) );
		$this->assertFalse( DynamicHtml::blocks_public_cache( false, false, true, '/wp-json/wp/v2/pages?per_page=1' ) );
	}
}
