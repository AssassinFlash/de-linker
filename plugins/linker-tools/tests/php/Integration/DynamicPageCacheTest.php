<?php
/**
 * A real front-end request does not publicly cache dynamic HTML.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Integration;

use PHPUnit\Framework\TestCase;
use WC_Product_Simple;

/**
 * Dynamic shortcodes and query strings send no-cache; home and a product do not.
 *
 * @coversNothing
 */
final class DynamicPageCacheTest extends TestCase {

	/**
	 * Pages created for this test.
	 *
	 * @var list<int>
	 */
	private array $pages = array();

	/**
	 * Product created for this test.
	 *
	 * @var int
	 */
	private int $product = 0;

	/**
	 * Removes the fixtures.
	 */
	public function tearDown(): void {
		foreach ( $this->pages as $id ) {
			wp_delete_post( $id, true );
		}
		if ( $this->product > 0 ) {
			wp_delete_post( $this->product, true );
		}
		parent::tearDown();
	}

	/**
	 * Representative dynamic shortcode pages, a product, and query strings.
	 */
	public function test_dynamic_pages_and_query_strings_are_not_cached(): void {
		$home = home_url( '/' );
		$this->assert_cacheable( $home );

		$product = new WC_Product_Simple();
		$product->set_name( 'Cache probe product' );
		$product->set_slug( 'cache-probe-product' );
		$product->set_status( 'publish' );
		$product->set_regular_price( '10' );
		$product->set_catalog_visibility( 'visible' );
		$this->product = $product->save();
		$this->assertGreaterThan( 0, $this->product );
		$this->assert_cacheable( (string) get_permalink( $this->product ) );

		$contact = $this->page( 'cache-probe-contact', '[linker_contact_form]' );
		$genie   = $this->page( 'cache-probe-genie', '[linker_genie_workspace]' );
		$planner = $this->page( 'cache-probe-configurator', '[linker_planner]' );
		flush_rewrite_rules( false );

		$contact_url = (string) get_permalink( $contact );
		$shell       = $this->document( $contact_url );
		$this->assertStringNotContainsString( 'no-cache', $shell['header'] );
		$this->assertStringNotContainsString( 'no-store', $shell['header'] );
		$this->assertStringNotContainsString( 'linker_public_browser=', $shell['cookies'] );
		$this->assertStringContainsString( 'data-linker-contact-shell="1"', $shell['body'] );
		$this->assertStringContainsString( 'name="linker_contact_nonce" value=""', $shell['body'] );
		$this->assertStringContainsString( 'name="linker_request_id" value=""', $shell['body'] );
		foreach ( array(
			'intent'          => 'project',
			'contact'         => 'invalid',
			'article_contact' => '1',
		) as $key => $value ) {
			$this->assert_uncacheable( add_query_arg( $key, $value, $contact_url ) );
		}
		$this->assert_uncacheable( (string) get_permalink( $genie ) );
		$this->assert_uncacheable( (string) get_permalink( $planner ) );
		$this->assert_uncacheable( add_query_arg( 'foo', 'cacheprobe', $home ) );
		$this->assert_uncacheable( add_query_arg( 'q', 'saj', (string) get_permalink( $this->product ) ) );
		$this->assert_anonymous_dock_has_no_nonce( $home, (string) get_permalink( $this->product ) );
	}

	/**
	 * Cached pages omit signed-in REST credentials for anonymous visitors.
	 *
	 * @param string $home    Clean homepage URL.
	 * @param string $product Clean product URL.
	 */
	private function assert_anonymous_dock_has_no_nonce( string $home, string $product ): void {
		$first        = $this->document( $home, 'pll_language=en' );
		$second       = $this->document( $home, 'pll_language=de' );
		$product_page = $this->document( $product, 'wp_woocommerce_session_probe=1' );
		$this->assertStringNotContainsString( 'no-cache', $first['header'], $home );
		$this->assertStringNotContainsString( 'no-store', $first['header'], $home );
		$this->assertStringNotContainsString( 'no-cache', $product_page['header'], $product );
		foreach ( array( $first, $second, $product_page ) as $document ) {
			$this->assertSame( '', $this->attr( $document['body'], 'data-rest-nonce' ) );
			$this->assertStringNotContainsString( 'data-genie-nonce-url=', $document['body'] );
			$this->assertStringNotContainsString( 'admin-ajax.php?action=rest-nonce', $document['body'] );
		}

		$this->assertStringNotContainsString( 'data-mail-started', $first['body'] );
	}

	/**
	 * Publishes one probe page.
	 *
	 * @param string $slug    Page slug.
	 * @param string $content Shortcode content.
	 */
	private function page( string $slug, string $content ): int {
		$id = wp_insert_post(
			array(
				'post_type'    => 'page',
				'post_status'  => 'publish',
				'post_title'   => $slug,
				'post_name'    => $slug,
				'post_content' => $content,
			),
			true
		);
		$this->assertIsInt( $id );
		$this->pages[] = $id;
		return $id;
	}

	/**
	 * The response must not carry the public no-cache mark.
	 *
	 * @param string $url Front-end URL.
	 */
	private function assert_cacheable( string $url ): void {
		$header = $this->cache_control( $url );
		$this->assertStringNotContainsString( 'no-cache', $header, $url );
		$this->assertStringNotContainsString( 'no-store', $header, $url );
	}

	/**
	 * The response must carry WordPress's no-cache header.
	 *
	 * @param string $url Front-end URL.
	 */
	private function assert_uncacheable( string $url ): void {
		$this->assertStringContainsString( 'no-cache', $this->cache_control( $url ), $url );
	}

	/**
	 * Cache-Control of one front-end GET, or an empty string.
	 *
	 * @param string $url Front-end URL.
	 */
	private function cache_control( string $url ): string {
		return $this->document( $url )['header'];
	}

	/**
	 * One anonymous front-end document.
	 *
	 * @param string $url    Front-end URL.
	 * @param string $cookie Cookie header for an independent anonymous jar.
	 * @return array{header: string, body: string, cookies: string}
	 */
	private function document( string $url, string $cookie = '' ): array {
		$args = array(
			'timeout'     => 20,
			'redirection' => 0,
		);
		if ( '' !== $cookie ) {
			$args['headers'] = array( 'Cookie' => $cookie );
		}
		$response = wp_remote_get( $url, $args );
		$this->assertFalse( is_wp_error( $response ), is_wp_error( $response ) ? $response->get_error_message() : $url );
		$this->assertSame( 200, (int) wp_remote_retrieve_response_code( $response ), $url );
		$header  = wp_remote_retrieve_header( $response, 'cache-control' );
		$cookies = wp_remote_retrieve_header( $response, 'set-cookie' );
		return array(
			'cookies' => is_array( $cookies ) ? implode( ', ', $cookies ) : (string) $cookies,
			'header'  => is_array( $header ) ? implode( ', ', $header ) : (string) $header,
			'body'    => (string) wp_remote_retrieve_body( $response ),
		);
	}

	/**
	 * One dock attribute.
	 *
	 * @param string $html Front-end HTML.
	 * @param string $name Attribute name.
	 */
	private function attr( string $html, string $name ): string {
		$found = preg_match( '/\s' . preg_quote( $name, '/' ) . '="([^"]*)"/', $html, $matches );
		if ( 1 !== $found ) {
			$this->fail( $name );
		}
		return $matches[1];
	}
}
