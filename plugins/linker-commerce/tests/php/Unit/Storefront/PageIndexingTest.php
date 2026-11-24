<?php
/**
 * Commerce sitemap and indexing contracts.
 *
 * @package Linker\Commerce
 */

namespace Linker\Commerce\Tests\Unit\Storefront;

use Linker\Commerce\Storefront\PageIndexing;
use WP_Mock;
use WP_Mock\Tools\TestCase;
use WP_Post;

/** @covers \Linker\Commerce\Storefront\PageIndexing */
final class PageIndexingTest extends TestCase {
	/**
	 * @dataProvider page_roles
	 * @param int  $source Source page ID.
	 * @param bool $private Transaction page.
	 * @param bool $listed Page sitemap membership.
	 */
	public function test_translated_page_role( int $source, bool $private, bool $listed ): void {
		$page = new WP_Post(
			(object) array(
				'ID'        => 70,
				'post_type' => 'page',
			)
		);
		WP_Mock::userFunction( 'get_queried_object', array( 'return' => $page ) );
		WP_Mock::userFunction(
			'pll_get_post',
			array(
				'args'   => array( 70, 'en' ),
				'return' => $source,
			)
		);
		$options = array(
			'woocommerce_cart_page_id'      => 10,
			'woocommerce_myaccount_page_id' => 11,
			'woocommerce_checkout_page_id'  => 12,
			'page_for_posts'                => 13,
			'woocommerce_shop_page_id'      => 14,
		);
		WP_Mock::userFunction( 'get_option', array( 'return' => static fn( $key ) => $options[ $key ] ) );
		$index = new PageIndexing();
		$this->assertSame( $private ? '1' : '', $index->noindex( '' ) );
		$this->assertSame( $private ? array( 'noindex', 'follow' ) : array( 'index' ), $index->robots( array( 'index' ) ) );
		$this->assertSame( $private ? array() : array( 'de' => '/' ), $index->alternates( array( 'de' => '/' ) ) );
		$this->assertSame( ! $private, $index->canonical( true ) );
		$this->assertSame( $listed ? 'url' : null, $index->sitemap( 'url', $page ) );
	}

	/** @return array<string,array{int,bool,bool}> */
	public static function page_roles(): array {
		return array(
			'cart'    => array( 10, true, false ),
			'account' => array( 11, true, false ),
			'inquiry' => array( 12, true, false ),
			'blog'    => array( 13, false, false ),
			'shop'    => array( 14, false, false ),
			'content' => array( 15, false, true ),
		);
	}
}
