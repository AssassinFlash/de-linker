<?php
/**
 * Tests for the catalogue shortcodes' language links.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Presentation\CatalogShortcodes;
use Linker\Commerce\Storefront\CatalogFilters;
use Linker\Commerce\Storefront\ProductView;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;
use WP_Post;
use WP_Term;

/**
 * The language half is the translated permalink of the queried object plus
 * the request path past that object's permalink. The current language's half
 * is the address the visitor is on.
 *
 * @covers \Linker\Commerce\Presentation\CatalogShortcodes
 */
final class CatalogShortcodesTest extends TestCase {

	/**
	 * Translation and escaping return their input; permalink helpers are the
	 * WordPress ones the shortcode calls, reduced to path joining.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		WP_Mock::userFunction(
			'home_url',
			array(
				'return' => static fn( string $path = '/' ): string => 'http://linker.test' . ( '' === $path || '/' === $path ? '/' : $path ),
			)
		);
		WP_Mock::userFunction(
			'wp_parse_url',
			array(
				'return' => static function ( string $url, int $component = -1 ) {
					$parsed = -1 === $component ? parse_url( $url ) : parse_url( $url, $component );
					return false === $parsed ? null : $parsed;
				},
			)
		);
		WP_Mock::userFunction(
			'add_query_arg',
			array(
				'return' => static function ( array $args, string $url ): string {
					$parts = parse_url( $url );
					$query = array();
					if ( is_array( $parts ) && isset( $parts['query'] ) ) {
						parse_str( $parts['query'], $query );
					}
					foreach ( $args as $key => $value ) {
						$query[ $key ] = $value;
					}
					$base = strtok( $url, '?' );
					return array() === $query ? (string) $base : $base . '?' . http_build_query( $query );
				},
			)
		);
		WP_Mock::userFunction(
			'remove_query_arg',
			array(
				'return' => static function ( $keys, string $url ): string {
					$parts = parse_url( $url );
					if ( ! is_array( $parts ) || ! isset( $parts['query'] ) ) {
						return $url;
					}
					parse_str( $parts['query'], $query );
					foreach ( (array) $keys as $key ) {
						unset( $query[ $key ] );
					}
					$base = strtok( $url, '?' );
					return array() === $query ? (string) $base : $base . '?' . http_build_query( $query );
				},
			)
		);
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn( $value ) => $value ) );
		WP_Mock::userFunction( 'sanitize_text_field', array( 'return' => static fn( string $value ): string => $value ) );
		WP_Mock::userFunction( 'user_trailingslashit', array( 'return' => static fn( string $url ): string => rtrim( $url, '/' ) . '/' ) );
		WP_Mock::userFunction( 'untrailingslashit', array( 'return' => static fn( string $url ): string => rtrim( $url, '/' ) ) );
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => static fn( $thing ): bool => $thing instanceof \WP_Error ) );
	}

	/**
	 * An account endpoint, its value and a nested endpoint stay on the translated account permalink.
	 *
	 * @dataProvider account_paths
	 * @param string $request  The visitor's path.
	 * @param string $expected The German half.
	 */
	public function test_account_path_is_appended_to_the_translated_account_permalink( string $request, string $expected ): void {
		$this->page(
			1037,
			'http://linker.test/my-account/',
			array(
				'de' => 6869,
			)
		);
		$this->permalink( 6869, 'http://linker.test/de/mein-konto/' );
		$_SERVER['REQUEST_URI'] = $request;
		$_GET                   = array();

		$this->assertSame( $expected, $this->url( 'de' ) );
		$this->assertSame( 'http://linker.test' . $request, $this->url( 'en' ) );
	}

	/**
	 * The account paths the language half has to keep whole.
	 *
	 * @return array<string, array{string, string}>
	 */
	public function account_paths(): array {
		return array(
			'endpoint'        => array( '/my-account/inquiries/', 'http://linker.test/de/mein-konto/inquiries/' ),
			'endpoint value'  => array( '/my-account/inquiry/1600/', 'http://linker.test/de/mein-konto/inquiry/1600/' ),
			'paging'          => array( '/my-account/inquiries/2/', 'http://linker.test/de/mein-konto/inquiries/2/' ),
			'nested endpoint' => array( '/my-account/company/billing/', 'http://linker.test/de/mein-konto/company/billing/' ),
		);
	}

	/**
	 * A confirmation stays on the translated request page, endpoint and value included.
	 */
	public function test_confirmation_stays_on_the_translated_request_page(): void {
		$this->page(
			1036,
			'http://linker.test/proforma-request/',
			array(
				'de' => 6867,
			)
		);
		$this->permalink( 6867, 'http://linker.test/de/proforma-anfrage/' );
		$_SERVER['REQUEST_URI'] = '/proforma-request/inquiry-received/7021/?key=k';
		$_GET                   = array( 'key' => 'k' );

		// Woo needs the order key on the confirmation page — without it the
		// thank-you page renders without the order's details.
		$this->assertSame( 'http://linker.test/de/proforma-anfrage/inquiry-received/7021/?key=k', $this->url( 'de' ) );
		$this->assertStringNotContainsString( 'mein-konto', $this->url( 'de' ) );
	}

	/**
	 * A category page keeps paging; the query keys the visitor set travel with the link.
	 */
	public function test_category_paging_and_the_visitor_query_are_kept(): void {
		$term = new WP_Term(
			(object) array(
				'term_id'  => 44,
				'slug'     => 'inverters',
				'taxonomy' => 'product_cat',
			)
		);
		WP_Mock::userFunction( 'get_queried_object', array( 'return' => $term ) );
		WP_Mock::userFunction(
			'get_term_link',
			array(
				'args'   => array( $term ),
				'return' => 'http://linker.test/product-category/inverters/',
			)
		);
		WP_Mock::userFunction(
			'pll_get_term',
			array(
				'args'   => array( 44, 'de' ),
				'return' => 88,
			)
		);
		WP_Mock::userFunction(
			'get_term_link',
			array(
				'args'   => array( 88 ),
				'return' => 'http://linker.test/de/produkt-kategorie/wechselrichter/',
			)
		);
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'en' ) );
		$_SERVER['REQUEST_URI'] = '/product-category/inverters/page/2/?step=roof';
		$_GET                   = array( 'step' => 'roof' );

		WP_Mock::userFunction(
			'pll_get_requested_url',
			array(
				'return' => 'http://linker.test/product-category/inverters/page/2/?step=roof',
			)
		);

		$this->assertSame( 'http://linker.test/de/produkt-kategorie/wechselrichter/page/2/?step=roof', $this->url( 'de' ) );
		$this->assertSame( 'http://linker.test/product-category/inverters/page/2/?step=roof', $this->url( 'en' ) );
	}

	/**
	 * A search is not a queried page: the switcher's URL keeps the search query.
	 */
	public function test_search_keeps_the_switcher_url_and_the_query(): void {
		WP_Mock::userFunction( 'get_queried_object', array( 'return' => null ) );
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'en' ) );
		WP_Mock::userFunction(
			'pll_the_languages',
			array(
				'return' => array(
					'de' => array( 'url' => 'http://linker.test/de/?s=inverter' ),
				),
			)
		);
		WP_Mock::userFunction( 'pll_get_requested_url', array( 'return' => 'http://linker.test/?s=inverter' ) );
		$_SERVER['REQUEST_URI'] = '/?s=inverter';
		$_GET                   = array( 's' => 'inverter' );

		$this->assertSame( 'http://linker.test/de/?s=inverter', $this->url( 'de' ) );
		$this->assertSame( 'http://linker.test/?s=inverter', $this->url( 'en' ) );
	}

	/**
	 * Without a queried object the switcher's URL is the answer, query included.
	 * The current language's half is the request, cache-bust key included.
	 */
	public function test_a_page_without_a_queried_object_keeps_the_switcher_url(): void {
		WP_Mock::userFunction( 'get_queried_object', array( 'return' => null ) );
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'en' ) );
		WP_Mock::userFunction(
			'pll_the_languages',
			array(
				'return' => array(
					'de' => array( 'url' => 'http://linker.test/de/linker-planer/?step=roof' ),
				),
			)
		);
		WP_Mock::userFunction(
			'pll_get_requested_url',
			array(
				'return' => 'http://linker.test/linker-planner/?step=roof&cbq=1',
			)
		);
		$_SERVER['REQUEST_URI'] = '/linker-planner/?step=roof&cbq=1';
		$_GET                   = array(
			'step' => 'roof',
			'cbq'  => '1',
		);

		$this->assertSame( 'http://linker.test/de/linker-planer/?step=roof', $this->url( 'de' ) );
		$this->assertSame( 'http://linker.test/linker-planner/?step=roof', $this->url( 'en' ) );
	}

	/**
	 * The fixture's request path, without its query.
	 */
	private function request_path(): string {
		$uri = isset( $_SERVER['REQUEST_URI'] ) ? (string) wp_unslash( $_SERVER['REQUEST_URI'] ) : '/'; // phpcs:ignore WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- the fixture sets this value.
		return (string) strtok( $uri, '?' );
	}

	/**
	 * The queried page, its German twin and that twin's permalink.
	 *
	 * @param int                $id           Queried page id.
	 * @param string             $permalink    Its permalink.
	 * @param array<string, int> $translations Language => translated id.
	 */
	private function page( int $id, string $permalink, array $translations ): void {
		$page = new WP_Post(
			(object) array(
				'ID'        => $id,
				'post_type' => 'page',
			)
		);
		WP_Mock::userFunction( 'get_queried_object', array( 'return' => $page ) );
		WP_Mock::userFunction(
			'get_permalink',
			array(
				'args'   => array( $page ),
				'return' => $permalink,
			)
		);
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'en' ) );
		WP_Mock::userFunction(
			'pll_get_requested_url',
			array(
				'return' => function () {
					return 'http://linker.test' . $this->request_path();
				},
			)
		);
		foreach ( $translations as $language => $translated ) {
			WP_Mock::userFunction(
				'pll_get_post',
				array(
					'args'   => array( $id, $language ),
					'return' => $translated,
				)
			);
		}
	}

	/**
	 * A translated page's permalink.
	 *
	 * @param int    $id   Translated page id.
	 * @param string $link Its permalink.
	 */
	private function permalink( int $id, string $link ): void {
		WP_Mock::userFunction(
			'get_permalink',
			array(
				'args'   => array( $id ),
				'return' => $link,
			)
		);
	}

	/**
	 * The language half for `$lang`.
	 *
	 * @param string $lang Language code.
	 */
	private function url( string $lang ): string {
		$shortcodes = new CatalogShortcodes( new CatalogFilters(), new ProductView() );
		$method     = new \ReflectionMethod( CatalogShortcodes::class, 'language_url' );
		return $method->invoke( $shortcodes, $lang );
	}
}
