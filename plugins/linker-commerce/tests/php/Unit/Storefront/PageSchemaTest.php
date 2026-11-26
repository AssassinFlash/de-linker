<?php
/**
 * Public page graph contracts.
 *
 * @package Linker\Commerce
 */

namespace Linker\Commerce\Tests\Unit\Storefront;

use Linker\Commerce\Storefront\PageSchema;
use WP_Mock;
use WP_Mock\Tools\TestCase;
use WP_Post;

/**
 * Keep translated navigation and visible labels in the structured data.
 *
 * @covers \Linker\Commerce\Storefront\PageSchema
 */
final class PageSchemaTest extends TestCase {

	/** The public publisher keeps SEOPress's identity and both ways to reach the team. */
	public function test_organization_retains_the_graph_id_and_public_contacts(): void {
		WP_Mock::userFunction( 'is_front_page', array( 'return' => false ) );
		WP_Mock::userFunction( 'get_option', array( 'return' => 'sales@de-linker.com' ) );
		WP_Mock::userFunction( 'sanitize_email', array( 'return_arg' => 0 ) );
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'en' ) );
		WP_Mock::userFunction( 'pll_home_url', array( 'return' => 'https://example.org/' ) );
		WP_Mock::userFunction( 'trailingslashit', array( 'return_arg' => 0 ) );
		$node = ( new PageSchema() )->organization( array( '@id' => 'https://example.org/#organization' ) );
		$this->assertSame( 'https://example.org/#organization', $node['@id'] );
		$this->assertSame( 'DE367367711', $node['vatID'] );
		$this->assertSame( 'Amtsgericht Stendal HRB 33824', $node['identifier']['value'] );
		$this->assertSame( array( 'sales@de-linker.com', 'chester@de-linker.com' ), array_column( $node['contactPoint'], 'email' ) );
	}

	/**
	 * The public comparison landing is discoverable; shared selections keep their noindex contract.
	 *
	 * @dataProvider comparison_queries
	 * @param array<string,string> $query Selection query.
	 */
	public function test_comparison_schema_only_for_clean_landing( array $query ): void {
		$post = new WP_Post(
			(object) array(
				'ID'        => 25,
				'post_name' => 'produkte-vergleichen',
				'post_type' => 'page',
			)
		);
		$url  = 'https://example.org/de/produkte-vergleichen/';
		WP_Mock::userFunction( 'get_queried_object' )->andReturn( $post );
		WP_Mock::userFunction( 'get_permalink' )->andReturn( $url );
		WP_Mock::userFunction( 'get_the_title' )->andReturn( 'Produkte vergleichen' );
		WP_Mock::userFunction( 'wp_strip_all_tags' )->andReturnArg( 0 );
		WP_Mock::userFunction( 'pll_current_language' )->andReturn( 'de' );
		WP_Mock::userFunction( 'pll_home_url' )->andReturn( 'https://example.org/de/' );
		WP_Mock::userFunction( 'trailingslashit' )->andReturnArg( 0 );
		WP_Mock::userFunction( 'is_singular' )->andReturn( false );
		WP_Mock::userFunction( 'is_page' )->andReturnUsing( static fn( $names ): bool => in_array( $post->post_name, (array) $names, true ) );
		WP_Mock::userFunction( 'get_post_meta' )->andReturn( 'Modelle vergleichen' );
		WP_Mock::userFunction( '_x' )->andReturn( 'Startseite' );
		WP_Mock::userFunction( 'wp_json_encode' )->andReturnUsing( 'json_encode' );
		$previous = $_GET; // phpcs:ignore WordPress.Security.NonceVerification.Recommended -- Restore the test’s query fixture.
		try {
			$_GET = $query;
			ob_start();
			( new PageSchema() )->print_blocks();
			$html = (string) ob_get_clean();
		} finally {
			$_GET = $previous;
		}
		if ( $query ) {
			$this->assertSame( '', $html );
			return;
		}
		$this->assertStringContainsString( '"@type":"WebPage"', $html );
		$this->assertStringContainsString( '"@type":"BreadcrumbList"', $html );
		$this->assertStringContainsString( '"name":"Startseite"', $html );
		$this->assertStringContainsString( '"name":"Produkte vergleichen"', $html );
	}

	/**
	 * Clean and shared comparison URLs.
	 *
	 * @return array<string,array{array<string,string>}>
	 */
	public static function comparison_queries(): array {
		return array(
			'landing'   => array( array() ),
			'selection' => array( array( 'ids' => '12,19' ) ),
			'empty cap' => array( array( 'capped' => '' ) ),
		);
	}

	/** A breadcrumb names what the browser displays, including decoded ampersands. */
	public function test_article_breadcrumb_follows_the_localized_journal(): void {
		$post = new WP_Post(
			(object) array(
				'ID'        => 20,
				'post_type' => 'post',
			)
		);
		$blog = new WP_Post(
			(object) array(
				'ID'        => 14,
				'post_type' => 'page',
			)
		);
		WP_Mock::userFunction( 'get_queried_object', array( 'return' => $post ) );
		WP_Mock::userFunction(
			'get_the_title',
			array(
				'args'   => array( $post ),
				'return' => 'C&#038;I-Speicher',
			)
		);
		WP_Mock::userFunction(
			'get_the_title',
			array(
				'args'   => array( 14 ),
				'return' => 'Blog',
			)
		);
		WP_Mock::userFunction(
			'get_permalink',
			array(
				'args'   => array( $post ),
				'return' => 'https://example.org/de/ci/',
			)
		);
		WP_Mock::userFunction(
			'get_permalink',
			array(
				'args'   => array( 15 ),
				'return' => 'https://example.org/de/blog/',
			)
		);
		WP_Mock::userFunction(
			'get_page_by_path',
			array(
				'args'   => array( 'blog' ),
				'return' => $blog,
			)
		);
		WP_Mock::userFunction(
			'get_option',
			array(
				'args'   => array( 'page_for_posts' ),
				'return' => 14,
			)
		);
		WP_Mock::userFunction(
			'is_singular',
			array(
				'args'   => array( 'product' ),
				'return' => false,
			)
		);
		WP_Mock::userFunction(
			'is_singular',
			array(
				'args'   => array( 'post' ),
				'return' => true,
			)
		);
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => 'de' ) );
		WP_Mock::userFunction(
			'pll_home_url',
			array(
				'args'   => array( 'de' ),
				'return' => 'https://example.org/de/',
			)
		);
		WP_Mock::userFunction(
			'pll_get_post',
			array(
				'args'   => array( 14, 'de' ),
				'return' => 15,
			)
		);
		WP_Mock::userFunction( 'trailingslashit', array( 'return_arg' => 0 ) );
		WP_Mock::userFunction( 'wp_strip_all_tags', array( 'return_arg' => 0 ) );
		WP_Mock::userFunction( '_x', array( 'return' => 'Startseite' ) );
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => static fn( $v, $flags ) => json_encode( $v, $flags ) ) );

		ob_start();
		( new PageSchema() )->print_blocks();
		$json  = trim( strip_tags( (string) ob_get_clean() ) );
		$trail = json_decode( $json, true, 512, JSON_THROW_ON_ERROR )['itemListElement'];
		$this->assertSame( array( 'Startseite', 'Blog', 'C&I-Speicher' ), array_column( $trail, 'name' ) );
		$this->assertSame( array( 'https://example.org/de/', 'https://example.org/de/blog/', 'https://example.org/de/ci/' ), array_column( $trail, 'item' ) );
	}
}
