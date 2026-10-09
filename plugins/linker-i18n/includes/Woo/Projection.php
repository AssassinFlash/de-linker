<?php
/**
 * The German product's commerce fields, copied from the English product.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Woo;

use Linker\I18n\Languages;

/**
 * Keeps a German product's commerce fields equal to its English product's.
 *
 * Price, tax, stock status, visibility, dimensions, images and the attribute
 * structure belong to the English product: people and the ERP write them
 * there, and this class copies them to the German product, one way. The SKU
 * and the stock quantity stay on the English product alone, so a SKU names
 * one product (`wc_get_product_id_by_sku()` takes the first match) and the
 * German product never manages stock
 * (docs/research/2026-10-09/i18n-opensource-replication.md §0.3, §3.2).
 */
final class Projection {

	/**
	 * Whether a projection is being saved (its own save must not start another).
	 *
	 * @var bool
	 */
	private bool $saving = false;

	/**
	 * Sets up the projection.
	 *
	 * @param Languages $languages The site's languages.
	 */
	public function __construct( private readonly Languages $languages ) {}

	/**
	 * Projects after any save of either product of a pair (actions
	 * `woocommerce_new_product`, `woocommerce_update_product`,
	 * `woocommerce_product_set_stock_status` and
	 * `woocommerce_updated_product_stock`). A save of the German product is
	 * answered with the English values again: they are not edited there.
	 *
	 * @param int|string $product_id Product ID.
	 */
	public function changed( $product_id ): void {
		if ( $this->saving ) {
			return;
		}
		$source = $this->languages->source_post( (int) $product_id );
		if ( null !== $source ) {
			$this->project( $source );
		}
	}

	/**
	 * Copies the commerce fields of an English product to its German product.
	 *
	 * @param int $source_id English product ID.
	 */
	public function project( int $source_id ): void {
		$target_id = $this->languages->post_translation( $source_id, Languages::TARGET );
		$source    = wc_get_product( $source_id );
		$target    = null === $target_id ? null : wc_get_product( $target_id );
		if ( ! $source instanceof \WC_Product || ! $target instanceof \WC_Product ) {
			return;
		}
		$target->set_props(
			array(
				'sku'                => '',
				'manage_stock'       => false,
				'stock_quantity'     => null,
				'stock_status'       => $source->get_stock_status( 'edit' ),
				'backorders'         => $source->get_backorders( 'edit' ),
				'regular_price'      => $source->get_regular_price( 'edit' ),
				'sale_price'         => $source->get_sale_price( 'edit' ),
				'date_on_sale_from'  => $source->get_date_on_sale_from( 'edit' ),
				'date_on_sale_to'    => $source->get_date_on_sale_to( 'edit' ),
				'tax_status'         => $source->get_tax_status( 'edit' ),
				'tax_class'          => $source->get_tax_class( 'edit' ),
				'catalog_visibility' => $source->get_catalog_visibility( 'edit' ),
				'featured'           => $source->get_featured( 'edit' ),
				'sold_individually'  => $source->get_sold_individually( 'edit' ),
				'virtual'            => $source->get_virtual( 'edit' ),
				'downloadable'       => $source->get_downloadable( 'edit' ),
				'weight'             => $source->get_weight( 'edit' ),
				'length'             => $source->get_length( 'edit' ),
				'width'              => $source->get_width( 'edit' ),
				'height'             => $source->get_height( 'edit' ),
				'shipping_class_id'  => $source->get_shipping_class_id( 'edit' ),
				'image_id'           => $source->get_image_id( 'edit' ),
				'gallery_image_ids'  => $source->get_gallery_image_ids( 'edit' ),
				'reviews_allowed'    => $source->get_reviews_allowed( 'edit' ),
				'menu_order'         => $source->get_menu_order( 'edit' ),
				'upsell_ids'         => $this->products( $source->get_upsell_ids( 'edit' ) ),
				'cross_sell_ids'     => $this->products( $source->get_cross_sell_ids( 'edit' ) ),
				'attributes'         => $this->attributes( $source ),
			)
		);
		$this->saving = true;
		try {
			$target->save();
		} finally {
			$this->saving = false;
		}
	}

	/**
	 * The English product's attributes with the terms of translated
	 * attributes swapped for their German terms; brand, model and the other
	 * untranslated attributes keep their terms.
	 *
	 * @param \WC_Product $source English product.
	 * @return array<string, \WC_Product_Attribute>
	 */
	private function attributes( \WC_Product $source ): array {
		$attributes = array();
		foreach ( $source->get_attributes( 'edit' ) as $key => $attribute ) {
			if ( ! $attribute instanceof \WC_Product_Attribute ) {
				continue;
			}
			$copy = clone $attribute;
			if ( $attribute->is_taxonomy() && $this->languages->translates_taxonomy( $attribute->get_name() ) ) {
				$terms = array();
				foreach ( $attribute->get_options() as $term_id ) {
					$german = $this->languages->term_translation( (int) $term_id, Languages::TARGET );
					if ( null !== $german ) {
						$terms[] = $german;
					}
				}
				$copy->set_options( $terms );
			}
			$attributes[ (string) $key ] = $copy;
		}
		return $attributes;
	}

	/**
	 * The German products of English products, where they exist.
	 *
	 * @param array<int|string> $product_ids English product IDs.
	 * @return list<int>
	 */
	private function products( array $product_ids ): array {
		$german = array();
		foreach ( $product_ids as $product_id ) {
			$translation = $this->languages->post_translation( (int) $product_id, Languages::TARGET );
			if ( null !== $translation ) {
				$german[] = $translation;
			}
		}
		return $german;
	}
}
