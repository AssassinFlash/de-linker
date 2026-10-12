<?php
/**
 * Tests for the product gallery's image list.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Catalog;

use Linker\Commerce\Catalog\Materials;
use Mockery;
use WC_Product;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for Materials::gallery_ids: the featured image first, then the
 * editor's gallery field, as the live order has them.
 *
 * @covers \Linker\Commerce\Catalog\Materials::gallery_ids
 */
final class MaterialsGalleryTest extends TestCase {


	/**
	 * Product id of the fixture.
	 */
	private const PRODUCT = 6530;

	/**
	 * The product under test.
	 *
	 * @var WC_Product
	 */
	private WC_Product $product;

	/**
	 * WooCommerce stores the gallery as one comma-separated list. Reading it
	 * as a single value kept only the first id, so the product page rendered
	 * one image fewer than the editor holds and, with two ids, no thumbnail
	 * strip at all (measured 2026-10-13 on the review instance: one image on
	 * the page where the live site shows three).
	 */
	public function test_every_id_of_the_editor_gallery_is_kept(): void {
		$this->mock_product( 6503 );
		$this->mock_gallery_field( '6504,6505', array( 6503, 6504, 6505 ) );

		$this->assertSame( array( 6503, 6504, 6505 ), Materials::gallery_ids( $this->product, array() ) );
	}

	/**
	 * Without a featured image the gallery field is still the whole list.
	 */
	public function test_the_gallery_field_stands_alone_when_the_product_has_no_featured_image(): void {
		$this->mock_product( 0 );
		$this->mock_gallery_field( '6504,6505', array( 6504, 6505 ) );

		$this->assertSame( array( 6504, 6505 ), Materials::gallery_ids( $this->product, array() ) );
	}

	/**
	 * An id the media library cannot resolve is dropped, not printed: the
	 * page would render a broken image.
	 */
	public function test_ids_that_are_not_images_are_dropped(): void {
		$this->mock_product( 0 );
		$this->mock_gallery_field( '6504,9999', array( 6504, 6505 ) );

		$this->assertSame( array( 6504 ), Materials::gallery_ids( $this->product, array() ) );
	}

	/**
	 * The field has held arrays; both shapes name ids and both are read.
	 */
	public function test_an_array_shaped_gallery_field_is_read_too(): void {
		$this->mock_product( 6503 );
		$this->mock_gallery_field( array( 6504, 6505 ), array( 6503, 6504, 6505 ) );

		$this->assertSame( array( 6503, 6504, 6505 ), Materials::gallery_ids( $this->product, array() ) );
	}

	/**
	 * The featured image leads, and the ACF rows follow before the editor
	 * field: an id named twice appears once.
	 */
	public function test_the_order_is_featured_then_acf_rows_then_the_gallery_field(): void {
		$this->mock_product( 6503 );
		$this->mock_gallery_field( '6503,6504', array( 6503, 6504, 6505 ) );

		$acf = array(
			'product_gallery' => array(
				array( 'gallery_image' => 6505 ),
				array( 'gallery_image' => 6504 ),
			),
		);

		$this->assertSame( array( 6503, 6505, 6504 ), Materials::gallery_ids( $this->product, $acf ) );
	}

	/**
	 * The product double.
	 *
	 * @param int $featured The featured image id, 0 when the product has none.
	 */
	private function mock_product( int $featured ): void {
		$product = Mockery::mock( WC_Product::class );
		$product->allows( 'get_id' )->andReturn( self::PRODUCT );
		$product->allows( 'get_image_id' )->andReturn( (string) $featured );
		$this->product = $product;
	}

	/**
	 * The editor's gallery field and the attachments that exist.
	 *
	 * @param string|list<int> $field       Value of `_product_image_gallery`.
	 * @param array<int, int>  $attachments Ids `wp_attachment_is_image` answers yes for.
	 */
	private function mock_gallery_field( $field, array $attachments ): void {
		WP_Mock::userFunction(
			'get_post_meta',
			array(
				'args'   => array( self::PRODUCT, '_product_image_gallery', true ),
				'return' => $field,
			)
		);
		WP_Mock::userFunction(
			'wp_attachment_is_image',
			array(
				'return' => static fn( int $id ): bool => in_array( $id, $attachments, true ),
			)
		);
	}
}
