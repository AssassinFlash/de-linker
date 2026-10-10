<?php
/**
 * Inquiries in the admin.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry;

/**
 * Staff see inquiries, not orders: the order screens take their headings from
 * the shop_order type's labels ("Inquiry #123 details", "Inquiries").
 */
final class OrderAdmin {

	/**
	 * Relabels the order type; runs on woocommerce_register_post_type_shop_order.
	 *
	 * @param array<string, mixed> $args Post type arguments.
	 * @return array<string, mixed>
	 */
	public function labels( array $args ): array {
		$labels = is_array( $args['labels'] ?? null ) ? $args['labels'] : array();

		$args['labels'] = array_merge(
			$labels,
			array(
				'name'                  => __( 'Inquiries', 'linker-commerce' ),
				'singular_name'         => __( 'Inquiry', 'linker-commerce' ),
				'menu_name'             => __( 'Inquiries', 'linker-commerce' ),
				'add_new'               => __( 'Add inquiry', 'linker-commerce' ),
				'add_new_item'          => __( 'Add new inquiry', 'linker-commerce' ),
				'edit_item'             => __( 'Edit inquiry', 'linker-commerce' ),
				'new_item'              => __( 'New inquiry', 'linker-commerce' ),
				'view_item'             => __( 'View inquiry', 'linker-commerce' ),
				'search_items'          => __( 'Search inquiries', 'linker-commerce' ),
				'not_found'             => __( 'No inquiries found', 'linker-commerce' ),
				'not_found_in_trash'    => __( 'No inquiries found in trash', 'linker-commerce' ),
				'filter_items_list'     => __( 'Filter inquiries', 'linker-commerce' ),
				'items_list_navigation' => __( 'Inquiries navigation', 'linker-commerce' ),
				'items_list'            => __( 'Inquiries list', 'linker-commerce' ),
			)
		);
		return $args;
	}
}
