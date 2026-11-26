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

/**
 * Exercise the native page assignments in both languages.
 *
 * @covers \Linker\Commerce\Storefront\PageIndexing
 */
final class PageIndexingTest extends TestCase {

	/** Authored descriptions take precedence over the translated comparison summary. */
	public function test_comparison_fills_only_an_empty_description(): void {
		WP_Mock::userFunction( 'is_page', array( 'return' => true ) );
		WP_Mock::userFunction( '__', array( 'return_arg' => 0 ) );
		$indexing = new PageIndexing();
		$this->assertSame( 'Manual introduction', $indexing->description( 'Manual introduction' ) );
		$this->assertStringStartsWith( 'Compare hybrid inverters', $indexing->description( '' ) );
	}

	/**
	 * Both languages use the source page assignment.
	 *
	 * @dataProvider page_roles
	 * @param int  $source Source page ID.
	 * @param bool $transactional Transaction page.
	 * @param bool $listed Page sitemap membership.
	 */
	public function test_translated_page_role( int $source, bool $transactional, bool $listed ): void {
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
		WP_Mock::userFunction( 'is_tax', array( 'return' => false ) );
		$options = array(
			'woocommerce_cart_page_id'      => 10,
			'woocommerce_myaccount_page_id' => 11,
			'woocommerce_checkout_page_id'  => 12,
			'page_for_posts'                => 13,
			'woocommerce_shop_page_id'      => 14,
		);
		WP_Mock::userFunction( 'get_option', array( 'return' => static fn( $key ) => $options[ $key ] ) );
		$index = new PageIndexing();
		$this->assertSame( $transactional ? '1' : '', $index->noindex( '' ) );
		$this->assertSame( $transactional ? array( 'noindex', 'follow' ) : array( 'index' ), $index->robots( array( 'index' ) ) );
		$this->assertSame( $transactional ? array() : array( 'de' => '/' ), $index->alternates( array( 'de' => '/' ) ) );
		$this->assertSame( ! $transactional, $index->canonical( true ) );
		$this->assertSame( $listed ? 'url' : null, $index->sitemap( 'url', $page ) );
	}

	/**
	 * Verify HTTP and head policies together for discovery surfaces.
	 *
	 * @dataProvider discovery_urls
	 * @param string $path Localized path.
	 * @param string $query Query string.
	 * @param bool   $selected Selection or filter present.
	 * @param bool   $empty_brand Brand with no matching published products.
	 */
	public function test_discovery_policy( string $path, string $query, bool $selected, bool $empty_brand = false ): void {
		$shop    = in_array( $path, array( '/products/', '/de/produkte/' ), true );
		$brand   = str_starts_with( $path, '/brand/' );
		$term    = $brand || str_starts_with( $path, '/product-category/' );
		$compare = ! $shop && ! $term;
		$post    = new WP_Post(
			(object) array(
				'ID'        => 71,
				'post_type' => 'page',
			)
		);
		$url     = 'https://de-linker.test' . $path;
		WP_Mock::userFunction( 'is_admin', array( 'return' => false ) );
		WP_Mock::userFunction( 'is_main_query', array( 'return' => true ) );
		WP_Mock::userFunction( 'is_404', array( 'return' => false ) );
		WP_Mock::userFunction( 'is_tax', array( 'return' => $brand ) );
		WP_Mock::userFunction( 'is_product_taxonomy', array( 'return' => $term ) );
		WP_Mock::userFunction( 'is_shop', array( 'return' => $shop ) );
		WP_Mock::userFunction( 'have_posts', array( 'return' => ! $empty_brand ) );
		WP_Mock::userFunction( 'is_page', array( 'return' => '/compare-products/' === $path ) );
		WP_Mock::userFunction( 'get_queried_object', array( 'return' => $term ? new \WP_Term( (object) array( 'term_id' => 11 ) ) : $post ) );
		WP_Mock::userFunction( 'get_option', array( 'return' => 0 ) );
		WP_Mock::userFunction( 'pll_get_post', array( 'return' => 70 ) );
		WP_Mock::userFunction(
			'get_post',
			array(
				'return' => new WP_Post(
					(object) array(
						'post_name' => $compare ? 'compare-products' : 'products',
						'post_type' => 'page',
					)
				),
			)
		);
		WP_Mock::userFunction( 'get_queried_object_id', array( 'return' => 71 ) );
		WP_Mock::userFunction(
			'get_permalink',
			array(
				'args'   => array( 71 ),
				'return' => $url,
			)
		);
		WP_Mock::userFunction(
			'wc_get_page_permalink',
			array(
				'args'   => array( 'shop' ),
				'return' => $url,
			)
		);
		WP_Mock::userFunction( 'get_term_link', array( 'return' => $url ) );
		WP_Mock::userFunction( 'esc_url', array( 'return_arg' => 0 ) );

		$before = $_GET; // phpcs:ignore WordPress.Security.NonceVerification.Recommended -- Restore request fixture.
		parse_str( $query, $params );
		$_GET = $params;
		try {
			$policy   = new PageIndexing();
			$excluded = $selected || $empty_brand;
			$this->assertSame( $excluded ? '1' : '', $policy->noindex( '' ) );
			$this->assertSame( $excluded ? array( 'noindex', 'follow' ) : array( 'index', 'nofollow' ), $policy->robots( array( 'index', 'nofollow' ) ) );
			$this->assertSame( $excluded ? array( 'X-Robots-Tag' => 'noindex, follow' ) : array(), $policy->headers( array() ) );
			$this->assertSame( $excluded ? array() : array( 'de' => '/' ), $policy->alternates( array( 'de' => '/' ) ) );
			$this->assertSame( $selected, $policy->canonical( false ) );
			$this->assertSame( $selected ? '<link rel="canonical" href="' . $url . '">' : 'native', $policy->canonical_tag( 'native' ) );
		} finally {
			$_GET = $before;
		}
	}

	/**
	 * Selected and clean shop, taxonomy and comparison pages.
	 *
	 * @return array<int,array{string,string,bool,3?:bool}>
	 */
	public static function discovery_urls(): array {
		return array(
			array( '/products/', '', false ),
			array( '/products/', 'product-page=2', false ),
			array( '/products/', 'brand=goodwe', true ),
			array( '/de/produkte/', 'product-page=2&brand=goodwe', true ),
			array( '/product-category/inverters/', 'kw_min=10&sort=power-desc', true ),
			array( '/compare-products/', '', false ),
			array( '/compare-products/', 'ids=6507,6508', true ),
			array( '/compare-products/', 'capped=', true ),
			array( '/de/produkte-vergleichen/', 'ids=6507,6508', true ),
			array( '/brand/ecoflow/', '', false, true ),
			array( '/brand/goodwe/', '', false ),
		);
	}

	/**
	 * Provide the sitemap and index contracts for each native page role.
	 *
	 * @return array<string,array{int,bool,bool}>
	 */
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
