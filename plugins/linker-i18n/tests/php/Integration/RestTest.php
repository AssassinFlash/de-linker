<?php
/**
 * REST and the Store API in one language.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Integration;

/**
 * Lists answer in the language of `?lang=` (English without it, both with
 * `all`), with the German names, links, categories and texts; a product by
 * slug is the one of the language asked for.
 *
 * @coversNothing
 */
final class RestTest extends SiteTestCase {

	/**
	 * The product pairs: English and German ID, slug, German name, English
	 * price (in minor units, as the Store API gives it) and stock.
	 *
	 * @var list<array{en: int, de: int, slug: string, name: string, price: string, in_stock: bool}>
	 */
	private static array $pairs = array();

	/**
	 * Reads the product pairs.
	 */
	public static function setUpBeforeClass(): void {
		parent::setUpBeforeClass();
		$pairs = self::php(
			'
			$out = array();
			foreach ( get_posts( array( "post_type" => "product", "post_status" => "publish", "numberposts" => -1, "lang" => "en", "fields" => "ids" ) ) as $id ) {
				$german = pll_get_post( $id, "de" );
				if ( $german ) {
					$product = wc_get_product( $id );
					$out[]   = array(
						"en"       => $id,
						"de"       => $german,
						"slug"     => get_post_field( "post_name", $id ),
						"name"     => get_post_field( "post_title", $german ),
						"price"    => (string) (int) round( (float) $product->get_price() * 10 ** wc_get_price_decimals() ),
						"in_stock" => $product->is_in_stock(),
					);
				}
			}
			return $out;
			'
		);
		self::assertIsArray( $pairs );
		self::assertNotEmpty( $pairs );
		foreach ( $pairs as $pair ) {
			self::assertIsArray( $pair );
			self::assertIsInt( $pair['en'] );
			self::assertIsInt( $pair['de'] );
			self::assertIsString( $pair['slug'] );
			self::assertIsString( $pair['name'] );
			self::assertIsString( $pair['price'] );
			self::assertIsBool( $pair['in_stock'] );
			self::$pairs[] = array(
				'en'       => $pair['en'],
				'de'       => $pair['de'],
				'slug'     => $pair['slug'],
				'name'     => $pair['name'],
				'price'    => $pair['price'],
				'in_stock' => $pair['in_stock'],
			);
		}
	}

	/**
	 * The IDs of a list, sorted.
	 *
	 * @param mixed $items REST items.
	 * @return list<int>
	 */
	private static function ids( $items ): array {
		self::assertIsArray( $items );
		$ids = array_map( static fn( array $item ): int => (int) $item['id'], $items );
		sort( $ids );
		return $ids;
	}

	/**
	 * The IDs of the pairs in one language, sorted.
	 *
	 * @param string $language en or de.
	 * @return list<int>
	 */
	private static function column( string $language ): array {
		$ids = array_map( static fn( array $pair ): int => 'de' === $language ? $pair['de'] : $pair['en'], self::$pairs );
		sort( $ids );
		return $ids;
	}

	/**
	 * The Store API lists English products without `lang`, German ones with
	 * `lang=de`, both with `lang=all`.
	 */
	public function test_store_api_lists_one_language(): void {
		$english = self::rest( '/wc/store/v1/products?per_page=100' );
		$this->assertSame( self::column( 'en' ), self::ids( $english ) );
		$this->assertSame( 'Add to cart', $english[0]['add_to_cart']['text'] );
		foreach ( $english as $product ) {
			$this->assertStringStartsWith( self::$site . '/product/', $product['permalink'] );
		}

		$german = self::rest( '/wc/store/v1/products?per_page=100&lang=de' );
		$this->assertSame( self::column( 'de' ), self::ids( $german ) );

		$all  = self::rest( '/wc/store/v1/products?per_page=100&lang=all' );
		$both = array_merge( self::column( 'en' ), self::column( 'de' ) );
		sort( $both );
		$this->assertSame( $both, self::ids( $all ) );
	}

	/**
	 * A German product of the Store API: German name, link and categories,
	 * the English price and stock, German button texts.
	 */
	public function test_store_api_german_products(): void {
		$names = self::php(
			'
			$out = array();
			foreach ( get_terms( array( "taxonomy" => "product_cat", "hide_empty" => false, "lang" => "de" ) ) as $term ) {
				$out[ $term->term_id ] = html_entity_decode( $term->name, ENT_QUOTES | ENT_HTML5, "UTF-8" );
			}
			return $out;
			'
		);
		$this->assertIsArray( $names );
		$by_id = array();
		foreach ( self::rest( '/wc/store/v1/products?per_page=100&lang=de' ) as $product ) {
			$by_id[ (int) $product['id'] ] = $product;
		}
		foreach ( self::$pairs as $pair ) {
			$product = $by_id[ $pair['de'] ];
			$this->assertSame( $pair['name'], html_entity_decode( $product['name'], ENT_QUOTES | ENT_HTML5, 'UTF-8' ), $pair['slug'] );
			$this->assertSame( self::$site . '/de/produkt/' . $pair['slug'] . '/', $product['permalink'] );
			$this->assertSame( $pair['price'], $product['prices']['price'], $pair['slug'] . ': price in minor units' );
			$this->assertSame( $pair['in_stock'], $product['is_in_stock'], $pair['slug'] . ': stock' );
			$this->assertSame( 'In den Warenkorb', $product['add_to_cart']['text'] );
			$this->assertNotEmpty( $product['categories'] );
			foreach ( $product['categories'] as $category ) {
				$this->assertSame( $names[ $category['id'] ] ?? null, html_entity_decode( $category['name'], ENT_QUOTES | ENT_HTML5, 'UTF-8' ), $pair['slug'] . ': category' );
				$this->assertStringStartsWith( self::$site . '/de/produkt-kategorie/', $category['link'] );
			}
		}
	}

	/**
	 * A product by slug is the one of the language asked for, on both routes.
	 */
	public function test_store_api_product_by_slug(): void {
		foreach ( self::$pairs as $pair ) {
			$this->assertSame( $pair['en'], self::rest( '/wc/store/v1/products/' . $pair['slug'] )['id'] );
			$this->assertSame( $pair['de'], self::rest( '/wc/store/v1/products/' . $pair['slug'] . '?lang=de' )['id'] );
			$this->assertSame( array( $pair['de'] ), self::ids( self::rest( '/wc/store/v1/products?slug=' . $pair['slug'] . '&lang=de' ) ) );
		}
	}

	/**
	 * Store API categories and wp/v2 pages follow `lang` too.
	 */
	public function test_categories_and_pages_follow_lang(): void {
		$expected = self::php(
			'
			$out = array();
			foreach ( array( "en", "de" ) as $language ) {
				$out[ $language ] = array(
					"categories" => array_map( "intval", get_terms( array( "taxonomy" => "product_cat", "hide_empty" => false, "lang" => $language, "fields" => "ids" ) ) ),
					"pages"      => array_map( "intval", get_posts( array( "post_type" => "page", "post_status" => "publish", "numberposts" => -1, "lang" => $language, "fields" => "ids" ) ) ),
				);
				sort( $out[ $language ]["categories"] );
				sort( $out[ $language ]["pages"] );
			}
			return $out;
			'
		);
		$this->assertIsArray( $expected );
		$this->assertSame( $expected['en']['categories'], self::ids( self::rest( '/wc/store/v1/products/categories?hide_empty=false' ) ) );
		$this->assertSame( $expected['de']['categories'], self::ids( self::rest( '/wc/store/v1/products/categories?hide_empty=false&lang=de' ) ) );
		$this->assertSame( $expected['en']['pages'], self::ids( self::rest( '/wp/v2/pages?per_page=100' ) ) );
		$this->assertSame( $expected['de']['pages'], self::ids( self::rest( '/wp/v2/pages?per_page=100&lang=de' ) ) );
	}
}
