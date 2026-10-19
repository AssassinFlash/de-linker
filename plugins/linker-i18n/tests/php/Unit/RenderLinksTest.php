<?php
/**
 * Tests for links in rendered content following the request's language.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Unit;

use Linker\I18n\Languages;
use Linker\I18n\LinkLocalizer;
use Linker\I18n\RenderLinks;
use Linker\I18n\Translation\HtmlTokenizer;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for RenderLinks.
 *
 * @covers \Linker\I18n\RenderLinks
 */
final class RenderLinksTest extends TestCase {

	/**
	 * The site's German pages, with the current language as the request's.
	 *
	 * @param string $current Current language slug.
	 */
	private function renderer( string $current ): RenderLinks {
		PolylangDouble::mock(
			array(
				33 => 'en',
				58 => 'de',
			),
			array( 33 => 58 ),
			array(),
			array(),
			$current
		);
		WP_Mock::userFunction( 'wp_parse_url', array( 'return' => static fn( string $url, int $component = -1 ) => -1 === $component ? parse_url( $url ) : parse_url( $url, $component ) ) ); // phpcs:ignore WordPress.WP.AlternativeFunctions.parse_url_parse_url -- stands in for wp_parse_url.
		WP_Mock::userFunction( 'home_url', array( 'return' => static fn( string $path = '' ) => rtrim( PolylangDouble::HOME, '/' ) . $path ) );
		WP_Mock::userFunction( 'untrailingslashit', array( 'return' => static fn( string $url ): string => rtrim( $url, '/' ) ) );
		WP_Mock::userFunction(
			'url_to_postid',
			array(
				'return' => static fn( string $url ) => array(
					PolylangDouble::HOME . 'contact/'    => 33,
					PolylangDouble::HOME . 'de/kontakt/' => 58,
				)[ $url ] ?? 0,
			)
		);
		WP_Mock::userFunction(
			'get_permalink',
			array(
				'return' => static fn( int $id ) => array(
					33 => PolylangDouble::HOME . 'contact/',
					58 => PolylangDouble::HOME . 'de/kontakt/',
				)[ $id ] ?? false,
			)
		);
		WP_Mock::userFunction( 'get_option', array( 'return' => static fn( string $name ) => 'woocommerce_shop_page_id' === $name ? 0 : '' ) );
		WP_Mock::userFunction( 'wc_get_permalink_structure', array( 'return' => array( 'category_rewrite_slug' => 'product-category' ) ) );

		$languages = new Languages();
		return new RenderLinks( new LinkLocalizer( $languages, new HtmlTokenizer() ), $languages );
	}

	/**
	 * A German request gets German links from English content.
	 */
	public function test_content_follows_the_german_request(): void {
		WP_Mock::userFunction( 'is_admin', array( 'return' => false ) );
		$this->assertSame(
			'<p>Write to <a href="/de/kontakt/">us</a>.</p>',
			$this->renderer( 'de' )->content( '<p>Write to <a href="/contact/">us</a>.</p>' )
		);
	}

	/**
	 * An English request gets English links back from German content.
	 */
	public function test_content_follows_the_english_request(): void {
		WP_Mock::userFunction( 'is_admin', array( 'return' => false ) );
		$this->assertSame(
			'<p>Write to <a href="/contact/">us</a>.</p>',
			$this->renderer( 'en' )->content( '<p>Write to <a href="/de/kontakt/">us</a>.</p>' )
		);
	}

	/**
	 * The editor and other admin screens read the stored content unchanged.
	 */
	public function test_admin_content_is_left_alone(): void {
		WP_Mock::userFunction( 'is_admin', array( 'return' => true ) );
		$this->assertSame(
			'<p>Write to <a href="/contact/">us</a>.</p>',
			$this->renderer( 'de' )->content( '<p>Write to <a href="/contact/">us</a>.</p>' )
		);
	}
}
