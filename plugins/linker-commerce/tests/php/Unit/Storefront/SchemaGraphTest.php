<?php
/**
 * Public HTML head and entity contracts.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Storefront;

use Linker\Commerce\Storefront\SchemaGraph;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Verify the head boundary and the public graph shape.
 *
 * @covers \Linker\Commerce\Storefront\SchemaGraph
 */
final class SchemaGraphTest extends TestCase {
	private const ROOT = 'https://example.org/';

	/** The request's canonical organization ID and real JSON encoder. */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( 'get_option' )->with( 'home' )->andReturn( self::ROOT );
		WP_Mock::userFunction( 'trailingslashit' )->andReturnArg( 0 );
		WP_Mock::userFunction( 'wp_json_encode' )->andReturnUsing( static fn( $value, $flags ) => json_encode( $value, $flags ) );
	}

	/**
	 * Build one of the blocks the head publishers emit.
	 *
	 * @param mixed[] $data Entity, list or graph.
	 */
	private static function script( array $data ): string {
		return '<script data-provider="seo" type="application/ld+json">' . json_encode( $data, JSON_HEX_TAG | JSON_THROW_ON_ERROR ) . '</script>';
	}

	/**
	 * Read the sole consolidated output.
	 *
	 * @param string $html Head markup.
	 * @return list<array<string,mixed>>
	 */
	private function nodes( string $html ): array {
		$count = preg_match_all( '~<script id="linker-schema-graph" type="application/ld\+json">(.*?)</script>~s', $html, $matches );
		$this->assertSame( 1, $count );
		$graph = json_decode( $matches[1][0], true, 512, JSON_THROW_ON_ERROR );
		$this->assertSame( 'https://schema.org', $graph['@context'] );
		return $graph['@graph'];
	}

	/** Products, anonymous breadcrumbs and publisher references survive consolidation. */
	public function test_collects_inner_nodes_and_preserves_non_schema_head_markup(): void {
		$org       = self::ROOT . '#organization';
		$group_id  = self::ROOT . '#product-group-esa';
		$product   = array(
			'@type'                => 'Product',
			'@id'                  => self::ROOT . 'model/#product',
			'inProductGroupWithID' => $group_id,
			'isVariantOf'          => array( '@id' => $group_id ),
		);
		$group     = array(
			'@type'          => 'ProductGroup',
			'@id'            => $group_id,
			'productGroupID' => $group_id,
			'hasVariant'     => array( array( '@id' => $product['@id'] ) ),
		);
		$page      = array(
			'@type'     => 'WebPage',
			'publisher' => array( '@id' => $org ),
		);
		$crumb     = array(
			'@type'           => 'BreadcrumbList',
			'itemListElement' => array( 'Home', 'Model' ),
		);
		$other_org = array(
			'@type' => 'Organization',
			'name'  => 'Manufacturer',
		);
		$other     = '<link rel="canonical" href="/model/"><script type="application/json">{"setting":1}</script>';
		$other    .= '<script type="application/json" data-example=\' type="application/ld+json" \'>{"@type":"Thing"}</script>';
		$broken    = "<script TYPE='application/ld+json'>{invalid}</script>";
		$html      = $other . $broken
			. self::script( array( '@context' => 'https://schema.org' ) + $product )
			. self::script( array( '@graph' => array( $group, $product, $crumb ) ) )
			. self::script(
				array(
					$page,
					$crumb,
					$other_org,
					array(
						'@type' => 'Organization',
						'@id'   => $org,
					),
					array( '@type' => 'WebSite' ),
				)
			);
		$output    = ( new SchemaGraph() )->consolidate( $html, false );
		$this->assertStringStartsWith( $other . $broken . '<script id="linker-schema-graph"', $output );
		$this->assertSame( array( $product, $group, $crumb, $page, $other_org ), $this->nodes( $output ) );
	}

	/** The localized homepage keeps its WebSite and the fully described canonical publisher. */
	public function test_front_page_prefers_the_full_publisher_over_a_stub(): void {
		$org   = array(
			'@type' => 'Organization',
			'@id'   => self::ROOT . '#organization',
		);
		$full  = $org + array(
			'legalName' => 'Linker Technology GmbH',
			'sameAs'    => array( 'https://example.com/company' ),
		);
		$site  = array(
			'@type'     => 'WebSite',
			'@id'       => self::ROOT . 'de/#website',
			'publisher' => array( '@id' => $org['@id'] ),
		);
		$input = self::script( array( $org, $site, $full, $org ) );
		$this->assertSame( array( $full, $site ), $this->nodes( ( new SchemaGraph() )->consolidate( $input, true ) ) );
	}

	/** The buffer ends at the head boundary and encodes a script delimiter safely. */
	public function test_flush_preserves_the_outer_buffer_and_escapes_script_text(): void {
		WP_Mock::userFunction( 'is_admin' )->andReturn( false );
		WP_Mock::userFunction( 'wp_doing_ajax' )->andReturn( false );
		WP_Mock::userFunction( 'is_front_page' )->andReturn( false );
		$entity = array(
			'@type' => 'WebPage',
			'name'  => '</script> & München',
		);
		$graph  = new SchemaGraph();
		ob_start();
		$level = ob_get_level();
		$graph->start_buffer();
		echo self::script( $entity ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- JSON-encoded fixture.
		$graph->flush_buffer();
		$this->assertSame( $level, ob_get_level() );
		$output = (string) ob_get_clean();
		$this->assertSame( array( $entity ), $this->nodes( $output ) );
		$this->assertStringContainsString( '\u003C/script', $output );
	}
}
