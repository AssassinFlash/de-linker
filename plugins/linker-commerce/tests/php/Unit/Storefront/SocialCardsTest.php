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
		WP_Mock::userFunction( 'get_the_title' )->with( 20 )->andReturn( 'Inverter (5 kW)' );
		WP_Mock::userFunction( 'wp_strip_all_tags' )->andReturnUsing( 'strip_tags' );
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

	/** A dedicated series photograph must describe the model whose card is shared. */
	public function test_dedicated_product_alt_names_the_current_model(): void {
		WP_Mock::userFunction( 'is_home' )->andReturn( false );
		WP_Mock::userFunction( 'is_category' )->andReturn( false );
		WP_Mock::userFunction( 'is_singular' )->andReturnUsing( static fn ( string $type ): bool => 'product' === $type );
		WP_Mock::userFunction( 'get_queried_object_id' )->andReturn( 80 );
		WP_Mock::userFunction( 'get_post_thumbnail_id' )->with( 80 )->andReturn( 100 );
		WP_Mock::userFunction( 'get_the_title' )->andReturn( 'GoodWe GW80K-ETR-G10 (80 kW)' );
		WP_Mock::userFunction( 'wp_strip_all_tags' )->andReturnUsing( 'strip_tags' );
		WP_Mock::userFunction( 'esc_attr' )->andReturnArg( 0 );
		$html = ( new SocialCards() )->open_graph( '<meta property="og:image" content="https://linker.test/etr.webp"><meta property="og:image:alt" content="Shared 125 kW inverter">' );
		$this->assertStringContainsString( 'content="GoodWe GW80K-ETR-G10 (80 kW)"', $html );
		$this->assertStringNotContainsString( '125 kW', $html );
	}

	/** A German share card displays the article's own translated cover caption. */
	public function test_dedicated_blog_uses_its_localized_post_cover_description(): void {
		require_once dirname( __DIR__, 5 ) . '/linker-i18n/includes/CoverAlt.php';
		WP_Mock::userFunction( 'is_home' )->andReturn( false );
		WP_Mock::userFunction( 'is_category' )->andReturn( false );
		WP_Mock::userFunction( 'is_singular' )->with( 'post' )->andReturn( true );
		WP_Mock::userFunction( 'get_queried_object_id' )->andReturn( 80 );
		WP_Mock::userFunction( 'get_post_thumbnail_id' )->with( 80 )->andReturn( 100 );
		WP_Mock::userFunction( 'get_post_meta' )->with( 80, '_linker_i18n_cover_alt_display', true )->andReturn( 'Speicher im Technikraum' );
		WP_Mock::userFunction( 'esc_attr' )->andReturnArg( 0 );
		$html = ( new SocialCards() )->open_graph( '<meta property="og:image" content="/cover.webp"><meta property="og:image:alt" content="Unrelated cover">' );
		$this->assertStringContainsString( 'content="Speicher im Technikraum"', $html );
		$this->assertStringNotContainsString( 'Unrelated cover', $html );
	}

	/** A native social creator tag belongs only to a journal entry written by Chester. */
	public function test_creator_uses_the_queried_posts_own_author(): void {
		$chester                = new \WP_User();
		$chester->user_nicename = 'chester-john';
		$team                   = new \WP_User();
		$team->user_nicename    = 'linker-team';
		$post                   = new \WP_Post( (object) array( 'post_author' => '12' ) );
		WP_Mock::userFunction( 'is_singular' )->with( 'post' )->andReturn( true, true, false );
		WP_Mock::userFunction( 'get_queried_object_id' )->andReturn( 55 );
		WP_Mock::userFunction( 'get_post' )->with( 55 )->andReturn( $post );
		WP_Mock::userFunction( 'get_userdata' )->with( 12 )->andReturn( $chester, $team );
		$cards = new SocialCards();
		$this->assertSame(
			array( '<meta name="twitter:creator" content="@chester_linker">', '', '' ),
			array( $cards->creator(), $cards->creator(), $cards->creator() )
		);
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
	/** SEOPress's object placeholder on archives is a website card. */
	public function test_archive_type_preserves_other_card_types(): void {
		WP_Mock::userFunction( 'is_shop', array( 'return' => true ) );
		$cards = new SocialCards();
		$this->assertSame( '<meta property="og:type" content="website">', $cards->open_graph_type( '<meta property="og:type" content="object">' ) );
		$this->assertSame( '<meta property="og:type" content="product">', $cards->open_graph_type( '<meta property="og:type" content="product">' ) );
	}

	/** Icons declare the dimensions of their actual PNG resources. */
	public function test_icons_offer_exact_raster_sizes_and_one_root_ico(): void {
		WP_Mock::userFunction( 'get_option' )->with( 'home' )->andReturn( 'https://linker.test' );
		WP_Mock::userFunction( 'trailingslashit', array( 'return' => static fn( $s ) => rtrim( $s, '/' ) . '/' ) );
		WP_Mock::userFunction( 'plugins_url', array( 'return' => 'https://linker.test/plugin/assets/icons/' ) );
		WP_Mock::userFunction( 'esc_url', array( 'return_arg' => 0 ) );
		$tags = ( new SocialCards() )->site_icons( array( '<link rel="icon" sizes="32x32" href="old.png">', '<meta name="msapplication-TileImage" content="tile.png">' ) );
		$html = implode( '', $tags );
		$this->assertStringContainsString( 'https://linker.test/favicon.ico', $html );
		$this->assertStringNotContainsString( 'old.png', $html );
		$this->assertStringContainsString( 'tile.png', $html );
		foreach ( array( 48, 96, 192, 180 ) as $size ) {
			$this->assertStringContainsString( 'sizes="' . $size . 'x' . $size . '"', $html );
		}
	}

	/** Meta reads its verification tag from the front page head. */
	public function test_front_page_outputs_domain_verification(): void {
		WP_Mock::userFunction( 'is_front_page' )->andReturn( true );
		WP_Mock::userFunction( 'esc_attr' )->andReturnArg( 0 );
		$this->expectOutputString( '<meta name="facebook-domain-verification" content="wmuo0z9zanm2ye6l5fpzqywavsy6v2" />' . "\n" );
		( new SocialCards() )->domain_verification();
	}

	/** Inner pages omit the verification tag. */
	public function test_inner_page_omits_domain_verification(): void {
		WP_Mock::userFunction( 'is_front_page' )->andReturn( false );
		$this->expectOutputString( '' );
		( new SocialCards() )->domain_verification();
	}
}
