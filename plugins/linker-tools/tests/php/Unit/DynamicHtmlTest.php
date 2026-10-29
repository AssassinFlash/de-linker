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
		DynamicHtml::register();
		$this->assertConditionsMet();
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
