<?php
/**
 * Tests for the catalogue's structured data.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Storefront;

use Linker\Commerce\Storefront\ArchiveSchema;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;
use WP_Term;

/**
 * Tests for ArchiveSchema: the blocks carry the page's own facts — the shop's
 * link and word, the category's name — and appear only on the catalogue.
 *
 * @covers \Linker\Commerce\Storefront\ArchiveSchema
 */
final class ArchiveSchemaTest extends TestCase {

	private const SHOP = 'https://de-linker.com/products/';

	/**
	 * JSON encoding is the real one; everything else the class touches is mocked per test.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction(
			'wp_json_encode',
			array( 'return' => static fn( $value, $flags = 0 ) => json_encode( $value, $flags ) )
		);
		WP_Mock::userFunction(
			'home_url',
			array( 'return' => 'https://de-linker.com/' )
		);
		WP_Mock::userFunction(
			'get_bloginfo',
			array( 'return' => 'Linker' )
		);
		WP_Mock::userFunction(
			'wc_get_page_permalink',
			array( 'return' => self::SHOP )
		);
		WP_Mock::passthruFunction( '__' );
		WP_Mock::passthruFunction( '_x' );
	}

	/**
	 * The hook the blocks are printed on.
	 */
	public function test_register_adds_the_blocks_to_the_head(): void {
		$schema = new ArchiveSchema();
		WP_Mock::expectActionAdded( 'wp_head', array( $schema, 'print_block' ) );

		$schema->register();

		$this->assertConditionsMet();
	}

	/**
	 * The shop archive: the collection node carries the shop's own link and
	 * word, and the site's name under isPartOf.
	 */
	public function test_the_shop_collection_mirrors_the_head(): void {
		$this->on_shop();
		$schema = new ArchiveSchema();

		$data = $schema->collection();

		$this->assertSame( 'https://schema.org', $data['@context'] );
		$this->assertSame( 'CollectionPage', $data['@type'] );
		$this->assertSame( 'Products', $data['name'] );
		$this->assertSame( self::SHOP, $data['url'] );
		$this->assertSame( 'Search products or filter by category and project requirements.', $data['description'] );
		$this->assertSame(
			array(
				'@type' => 'WebSite',
				'name'  => 'Linker',
				'url'   => 'https://de-linker.com/',
			),
			$data['isPartOf']
		);
		$this->assertConditionsMet();
	}

	/**
	 * The shop's breadcrumb: Home, then Products; the shop itself carries no
	 * third item.
	 */
	public function test_the_shop_breadcrumb_is_two_items(): void {
		$this->on_shop();
		$schema = new ArchiveSchema();

		$data = $schema->breadcrumb();

		$this->assertSame( 'BreadcrumbList', $data['@type'] );
		$this->assertSame(
			array(
				array(
					'@type'    => 'ListItem',
					'position' => 1,
					'name'     => 'Home',
					'item'     => 'https://de-linker.com/',
				),
				array(
					'@type'    => 'ListItem',
					'position' => 2,
					'name'     => 'Products',
					'item'     => self::SHOP,
				),
			),
			$data['itemListElement']
		);
		$this->assertConditionsMet();
	}

	/**
	 * A category archive: the term's own name and link, as its H1 uses them,
	 * and the same breadcrumb with a third item.
	 */
	public function test_a_category_carries_the_terms_own_facts(): void {
		$term = new WP_Term(
			(object) array(
				'name'     => 'Wechselrichter',
				'taxonomy' => 'product_cat',
				'slug'     => 'wechselrichter',
				'term_id'  => 31,
			)
		);
		$this->on_category( $term, 'https://de-linker.com/de/produkt-kategorie/wechselrichter/' );
		$schema = new ArchiveSchema();

		$data = $schema->collection();

		$this->assertSame( 'Wechselrichter', $data['name'] );
		$this->assertSame( 'https://de-linker.com/de/produkt-kategorie/wechselrichter/', $data['url'] );

		$items = $schema->breadcrumb()['itemListElement'];
		$this->assertCount( 3, $items );
		$this->assertSame( 'Wechselrichter', $items[2]['name'] );
		$this->assertSame( 'https://de-linker.com/de/produkt-kategorie/wechselrichter/', $items[2]['item'] );
		$this->assertConditionsMet();
	}

	/**
	 * Anywhere else — a product page, a blog post — the blocks print nothing.
	 */
	public function test_other_pages_carry_no_blocks(): void {
		WP_Mock::userFunction( 'is_product_category', array( 'return' => false ) );
		WP_Mock::userFunction( 'is_post_type_archive', array( 'return' => false ) );
		$schema = new ArchiveSchema();

		ob_start();
		$schema->print_block();
		$printed = (string) ob_get_clean();

		$this->assertSame( '', $printed );
		$this->assertSame( array(), $schema->collection() );
		$this->assertSame( array(), $schema->breadcrumb() );
		$this->assertConditionsMet();
	}

	/**
	 * A `<` in a term's name must not end the script element.
	 */
	public function test_a_name_with_a_angle_bracket_is_escaped(): void {
		$term = new WP_Term(
			(object) array(
				'name'     => 'Wechselrichter <3',
				'taxonomy' => 'product_cat',
			)
		);
		$this->on_category( $term, 'https://de-linker.com/de/produkt-kategorie/wechselrichter/' );
		$schema = new ArchiveSchema();

		$json = $schema->encoded( $schema->collection() );

		$this->assertStringNotContainsString( '<', $json );
		$this->assertStringContainsString( 'Wechselrichter \u003C3', $json );
		$this->assertConditionsMet();
	}

	/**
	 * The request is the product archive.
	 */
	private function on_shop(): void {
		WP_Mock::userFunction( 'is_product_category', array( 'return' => false ) );
		WP_Mock::userFunction(
			'is_post_type_archive',
			array( 'return' => static fn( string $type ): bool => 'product' === $type )
		);
	}

	/**
	 * The request is a product-category archive.
	 *
	 * @param WP_Term $term The queried term.
	 * @param string  $link Its permalink.
	 */
	private function on_category( WP_Term $term, string $link ): void {
		WP_Mock::userFunction( 'is_product_category', array( 'return' => true ) );
		WP_Mock::userFunction( 'get_queried_object', array( 'return' => $term ) );
		WP_Mock::userFunction( 'get_term_link', array( 'return' => $link ) );
	}
}
