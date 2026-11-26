<?php
/**
 * Social preview image selection.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Storefront;

use Linker\Commerce\Storefront\SocialCards;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Select the image group a visitor shares.
 *
 * @covers \Linker\Commerce\Storefront\SocialCards
 */
final class SocialCardsTest extends TestCase {

	/** The posts index uses its journal card for both social networks. */
	public function test_blog_index_uses_journal_card_on_both_networks(): void {
		WP_Mock::userFunction( 'is_home', array( 'return' => true ) );
		WP_Mock::userFunction( 'get_option' )->with( 'linker_social_blog_og_attachment_id' )->andReturn( 42 );
		WP_Mock::userFunction( 'wp_get_attachment_url' )->with( 42 )->andReturn( 'https://example.org/uploads/journal.jpg' );
		WP_Mock::userFunction( 'esc_url', array( 'return' => static fn( $s ) => $s ) );
		WP_Mock::userFunction( 'esc_attr', array( 'return' => 'alt' ) );
		$cards = new SocialCards();
		$tags  = $cards->open_graph( '<meta property="og:image" content="https://example.org/logo.png">' );
		$this->assertStringContainsString( 'content="https://example.org/uploads/journal.jpg"', $tags );
		$this->assertStringContainsString( 'property="og:image:width" content="1200"', $tags );
		$this->assertStringContainsString( 'property="og:image:height" content="630"', $tags );
		$this->assertSame( '<meta name="twitter:image" content="https://example.org/uploads/journal.jpg">', $cards->twitter_image( '' ) );
	}
	/** SEOPress strips the dimensions from an original filename as though it were a crop. */
	public function test_default_card_restores_the_original_url_after_seopress_crop_resolution(): void {
		WP_Mock::userFunction( 'is_home', array( 'return' => false ) );
		WP_Mock::userFunction( 'is_category', array( 'return' => false ) );
		WP_Mock::userFunction( 'is_singular', array( 'return' => false ) );
		WP_Mock::userFunction( 'get_option' )->with( 'linker_social_default_og_attachment_id' )->andReturn( 42 );
		WP_Mock::userFunction( 'wp_get_attachment_url' )->with( 42 )->andReturn( 'https://example.org/uploads/linker-social/og-linker-default-1200x630.jpg' );
		WP_Mock::userFunction( 'esc_url', array( 'return' => static fn( $s ) => $s ) );
		WP_Mock::userFunction( 'esc_attr', array( 'return' => static fn( $s ) => $s ) );
		$cards = new SocialCards();
		$html  = '<meta property="og:image" content="https://example.org/uploads/linker-social/og-linker-default.jpg"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">';
		$tags  = $cards->open_graph( $html );
		$this->assertStringContainsString( '/linker-social/og-linker-default-1200x630.jpg"', $tags );
		$this->assertStringContainsString( 'property="og:image:alt"', $tags );
		$this->assertStringContainsString( '/linker-social/og-linker-default-1200x630.jpg"', $cards->twitter_image( '' ) );
	}

	/** A registered global default must not replace the equipment shown on a product page. */
	public function test_product_keeps_its_own_featured_image_and_dimensions(): void {
		WP_Mock::userFunction( 'is_home', array( 'return' => false ) );
		WP_Mock::userFunction( 'is_category', array( 'return' => false ) );
		WP_Mock::userFunction( 'is_singular' )->with( 'post' )->andReturn( false );
		WP_Mock::userFunction( 'is_singular' )->with( 'product' )->andReturn( true );
		WP_Mock::userFunction( 'get_queried_object_id', array( 'return' => 20 ) );
		WP_Mock::userFunction( 'get_post_thumbnail_id' )->with( 20 )->andReturn( 21 );
		WP_Mock::userFunction( 'wp_get_attachment_image_src' )->with( 21, 'full' )->andReturn( array( 'https://example.org/inverter.webp', 900, 900, false ) );
		WP_Mock::userFunction( 'get_post_meta' )->with( 21, '_wp_attachment_image_alt', true )->andReturn( 'Inverter' );
		WP_Mock::userFunction( 'esc_url', array( 'return' => static fn( $s ) => $s ) );
		WP_Mock::userFunction( 'esc_attr', array( 'return' => static fn( $s ) => $s ) );
		$cards = new SocialCards();
		$tags  = $cards->open_graph( '<meta property="og:image" content="https://example.org/og-linker-default-1200x630.jpg">' );
		$this->assertStringContainsString( 'property="og:image" content="https://example.org/inverter.webp"', $tags );
		$this->assertStringContainsString( 'property="og:image:width" content="900"', $tags );
		$this->assertSame( '<meta name="twitter:image" content="https://example.org/inverter.webp">', $cards->twitter_image( '' ) );
	}

	/** A dedicated landscape card is preserved, and the internal SEOPress URL filter keeps its type. */
	public function test_dedicated_landscape_card_and_raw_urls(): void {
		WP_Mock::userFunction( 'is_home', array( 'return' => false ) );
		WP_Mock::userFunction( 'is_category', array( 'return' => false ) );
		WP_Mock::userFunction( 'is_singular', array( 'return' => false ) );
		WP_Mock::userFunction( 'esc_url', array( 'return' => static fn( $s ) => $s ) );
		$url   = 'https://example.org/solution.jpg';
		$html  = '<meta property="og:image" content="' . $url . '"><meta property="og:image:width" content="1600"><meta property="og:image:height" content="800">';
		$cards = new SocialCards();
		$this->assertSame( $html, $cards->open_graph( $html ) );
		$this->assertStringContainsString( $url, $cards->twitter_image( '' ) );
		$this->assertSame( $url, $cards->open_graph( $url ) );
		$this->assertSame( $url, $cards->twitter_image( $url ) );
	}
}
