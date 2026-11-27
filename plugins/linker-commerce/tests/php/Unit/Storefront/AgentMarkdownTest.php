<?php
/**
 * Public Markdown representations.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Storefront;

use Linker\Commerce\Storefront\AgentMarkdown;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Verify the alternate public representations.
 *
 * @covers \Linker\Commerce\Storefront\AgentMarkdown
 */
final class AgentMarkdownTest extends TestCase {
	/** Product publication and sales scope decide whether the alternate is advertised. */
	public function test_product_scope(): void {
		WP_Mock::userFunction( 'is_singular' )->andReturnUsing( static fn( string $type ): bool => 'product' === $type );
		WP_Mock::userFunction( 'wp_cache_supports' )->andReturn( true );
		WP_Mock::userFunction( 'wp_cache_flush_runtime' )->andReturn( true );
		WP_Mock::userFunction( 'get_queried_object_id' )->andReturn( 31, 32, 33 );
		WP_Mock::userFunction( 'get_post_type' )->andReturn( 'product' );
		WP_Mock::userFunction( 'get_post_status' )->andReturnUsing( static fn( int $id ): string => 32 === $id ? 'draft' : 'publish' );
		WP_Mock::userFunction( 'get_post_meta' )->andReturnUsing( static fn( int $id ): string => 33 === $id ? 'reference_cable' : '' );
		WP_Mock::userFunction( 'has_filter' )->andReturn( false );
		$markdown = new AgentMarkdown();
		$types    = array( 'page', 'post' );
		$this->assertContains( 'product', $markdown->markdown_post_types( $types ) );
		$this->assertNotContains( 'product', $markdown->markdown_post_types( $types ) );
		$this->assertNotContains( 'product', $markdown->markdown_post_types( $types ) );
	}

	/** Translated WooCommerce transaction pages retain their original representation. */
	public function test_private_page_scope(): void {
		WP_Mock::userFunction( 'is_singular' )->andReturnUsing( static fn( string $type ): bool => 'page' === $type );
		WP_Mock::userFunction( 'get_queried_object' )->andReturn(
			new \WP_Post(
				(object) array(
					'ID'        => 42,
					'post_type' => 'page',
				)
			)
		);
		WP_Mock::userFunction( 'pll_get_post' )->andReturn( 41 );
		WP_Mock::userFunction( 'get_option' )->andReturnUsing( static fn( string $name ): int => 'woocommerce_myaccount_page_id' === $name ? 41 : 1 );
		$this->assertNotContains( 'page', ( new AgentMarkdown() )->markdown_post_types( array( 'page', 'post' ) ) );
	}

	/** All three card filters use decoded site text. The MCP adds unique resources. */
	public function test_discovery_resources(): void {
		WP_Mock::userFunction( 'get_option' )->andReturn( 'https://linker.test' );
		WP_Mock::userFunction( 'trailingslashit' )->andReturnUsing( static fn( $url ) => rtrim( $url, '/' ) . '/' );
		WP_Mock::userFunction( 'rest_url' )->andReturn( 'https://linker.test/wp-json/linker/v1/engineering-feed' );
		$markdown = new AgentMarkdown();
		$card     = array(
			'description' => 'C&amp;I',
			'serverInfo'  => array( 'name' => 'R&amp;D' ),
			'resources'   => array(),
		);
		$clean    = $markdown->mcp_card( $card );
		$this->assertSame( 'C&I', $clean['description'] );
		$this->assertSame( 'R&D', $clean['serverInfo']['name'] );
		$this->assertSame( array( 'llms-full', 'engineering-feed' ), array_column( $clean['resources'], 'name' ) );
		$this->assertSame( $clean, $markdown->mcp_card( $clean ) );
	}

	/** Both planner URLs use the live guide, including its GFM sizing table. */
	public function test_planner_guide_replaces_stored_page_brief(): void {
		if ( ! class_exists( \Linker\Tools\Planner\Application::class ) ) {
			require_once dirname( __DIR__, 5 ) . '/linker-tools/includes/Planner/Application.php';
		}
		WP_Mock::userFunction( 'get_permalink' )->andReturnUsing( static fn( $post ) => 'https://linker.test/' . $post->post_name . '/' );
		WP_Mock::userFunction( 'esc_url_raw', array( 'return_arg' => 0 ) );
		WP_Mock::userFunction( 'get_the_title' )->andReturn( 'Systems &amp; storage' );
		WP_Mock::userFunction( 'get_post_modified_time' )->andReturn( '2026-11-27T00:00:00Z' );
		WP_Mock::userFunction( 'wp_strip_all_tags', array( 'return_arg' => 0 ) );
		WP_Mock::userFunction( 'esc_html__', array( 'return_arg' => 0 ) );
		WP_Mock::userFunction( 'get_page_by_path' )->andReturn( null );
		WP_Mock::userFunction( 'strip_shortcodes', array( 'return_arg' => 0 ) );
		foreach ( array( 'solution-configurator', 'loesungskonfigurator' ) as $slug ) {
			$post = new \WP_Post(
				(object) array(
					'post_type' => 'page',
					'post_name' => $slug,
				)
			);
			$text = ( new AgentMarkdown() )->markdown_body( 'superseded wrapper', $post );
			$this->assertStringStartsWith( "# Systems & storage\n\n> URL: https://linker.test/" . $slug . '/', $text );
			$this->assertStringContainsString( '| Project segment | Typical sizing range |', $text );
			$this->assertStringContainsString( '| Utility-scale storage |', $text );
			$this->assertStringNotContainsString( 'superseded wrapper', $text );
		}
	}

	/** Preserve engineering tables, links and definitions while omitting UI and shortcodes. */
	public function test_semantic_content(): void {
		WP_Mock::userFunction( 'strip_shortcodes', array( 'return_arg' => 0 ) );
		WP_Mock::userFunction( 'esc_url_raw', array( 'return_arg' => 0 ) );
		$html = '<h2>Geräte</h2><nav><a href="/a/">Alpha</a><a href="/b/">Beta</a></nav><table><tr><th>Model</th><th>Power</th></tr><tr><td><a href="/saj/">SAJ</a></td><td>10 kW</td></tr></table><dl><div><dt>Strom</dt><dd>10 A</dd></div></dl><dialog>PRIVATE</dialog><div hidden>HIDDEN</div>[linker_create_account][lc_if x="1"][/lc_if]';
		$text = ( new AgentMarkdown() )->html_to_markdown( null, $html );
		$this->assertStringContainsString( '## Geräte', $text );
		$this->assertStringContainsString( "| Model | Power |\n| --- | --- |\n| [SAJ](/saj/) | 10 kW |", $text );
		$this->assertStringContainsString( '- **Strom**: 10 A', $text );
		$this->assertStringContainsString( '[Alpha](/a/) [Beta](/b/)', $text );
		$this->assertDoesNotMatchRegularExpression( '/PRIVATE|HIDDEN|linker_create|lc_if/', $text );
	}
}
