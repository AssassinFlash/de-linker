<?php
/**
 * The actual archive invitation carries the selection to the Contact consumer.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
namespace Linker\Commerce\Tests\Unit\Contact;

use Linker\Commerce\Contact\SelectionContext;
use Linker\Commerce\Presentation\ProductShortcodes;
use Linker\Commerce\Storefront\ProductFilters;
use Linker\Commerce\Storefront\ProductView;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Exercise the existing shortcode, not a separately recreated URL helper.
 *
 * @covers \Linker\Commerce\Presentation\ProductShortcodes::products_contact
 */
final class SelectionLinkTest extends TestCase {
	/**
	 * The full sanitized navigation selection survives the actual rendered href.
	 *
	 * @dataProvider range_values
	 * @param string     $range Raw public bound.
	 * @param float|null $expected_range Accepted finite bound, if any.
	 */
	public function test_archive_invitation_href_transports_filters_search_and_sort( string $range, ?float $expected_range ): void {
		$this->plain_text();
		WP_Mock::userFunction( 'get_queried_object', array( 'return' => null ) );
		WP_Mock::userFunction( 'wc_get_page_id', array( 'return' => 12 ) );
		WP_Mock::userFunction( 'get_permalink', array( 'return' => 'http://linker.test/products/' ) );
		WP_Mock::userFunction( 'get_the_title', array( 'return' => 'Products' ) );
		WP_Mock::userFunction( 'get_option', array( 'return' => '' ) );
		WP_Mock::passthruFunction( 'sanitize_email' );
		WP_Mock::passthruFunction( 'sanitize_key' );
		WP_Mock::passthruFunction( 'sanitize_text_field' );
		WP_Mock::passthruFunction( 'wp_unslash' );
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => static fn ( $value ) => json_encode( $value ) ) );
		// WordPress expects new values already encoded; it does not encode them for the caller.
		WP_Mock::userFunction( 'add_query_arg', array( 'return' => static fn ( array $query, string $url ): string => $url . '?' . implode( '&', array_map( static fn ( $key, $value ): string => $key . '=' . $value, array_keys( $query ), $query ) ) ) );
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- Read-only navigation fixture; the real GET consumer sanitizes it.
		$original = $_GET;
		$_GET     = array(
			'q'      => 'No matching SAJ',
			'brand'  => 'saj',
			'phase'  => '3',
			'kw_min' => $range,
			'sort'   => 'power-desc',
			'token'  => 'never-carried',
		);
		try {
			$html = ( new ProductShortcodes( new ProductFilters(), new ProductView() ) )->products_contact();
			$this->assertSame( 1, preg_match( '/class="linker-contact-primary" href="([^"]+)"/', $html, $match ) );
			$href = $match[1] ?? '';
			$this->assertNotSame( '', $href );
			parse_str( (string) parse_url( $href, PHP_URL_QUERY ), $query );
			$this->assertIsString( $query[ SelectionContext::FIELD ] );
			$context = json_decode( $query[ SelectionContext::FIELD ], true );
			$this->assertIsArray( $context, 'An invalid range must not erase the other selection values.' );
			$this->assertSame( 'product', $query['intent'] );
			$this->assertSame( 'http://linker.test/products/', $context['source'] );
			$expected = array(
				'brand' => 'saj',
				'phase' => '3',
			);
			if ( null !== $expected_range ) {
				$expected['kw_min'] = $expected_range;
			}
			$expected['q']    = 'No matching SAJ';
			$expected['sort'] = 'power-desc';
			$this->assertSame( $expected, $context['selection'] );
			$this->assertStringNotContainsString( 'never-carried', $href );
		} finally {
			$_GET = $original;
		}
	}

	/**
	 * Public numeric input may overflow even though PHP accepts its scalar shape.
	 *
	 * @return array<string, array{string, float|null}>
	 */
	public function range_values(): array {
		return array(
			'finite-comma-decimal' => array( '5,5', 5.5 ),
			'overflow'             => array( '1e999', null ),
		);
	}
}
