<?php
/**
 * Seeds a local WordPress with live-products-2026-10-09.json: the product
 * categories, the global attributes and terms the products use, and the 89
 * products under their live IDs with their attributes, figures and document
 * URLs. It gives the REST route and tools/migrate/7-facts.py real WooCommerce
 * data on a local instance until #6's snapshot can be loaded instead. It only
 * runs where wp_get_environment_type() is "local", and skips products whose
 * ID is taken.
 *
 * Usage: wp eval-file --use-include plugins/linker-commerce/tests/fixtures/load-live-products.php
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

defined( 'ABSPATH' ) || exit;

( static function (): void {
	if ( 'local' !== wp_get_environment_type() ) {
		WP_CLI::error( 'This seeds local instances only (WP_ENVIRONMENT_TYPE is not "local").' );
	}
	// phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- a file beside this script.
	$fixture = json_decode( (string) file_get_contents( __DIR__ . '/live-products-2026-10-09.json' ), true, 512, JSON_THROW_ON_ERROR );

	// Categories, parents before children; live term ID => local term ID.
	$categories = array();
	$pending    = $fixture['product_categories'];
	while ( array() !== $pending ) {
		$created = 0;
		foreach ( $pending as $key => $category ) {
			$parent = 0 === $category['parent'] ? 0 : ( $categories[ $category['parent'] ] ?? null );
			if ( null === $parent ) {
				continue;
			}
			$term = get_term_by( 'slug', $category['slug'], 'product_cat' );
			if ( ! $term instanceof WP_Term ) {
				$created_term = wp_insert_term(
					$category['name'],
					'product_cat',
					array(
						'slug'   => $category['slug'],
						'parent' => $parent,
					)
				);
				$term         = get_term( $created_term['term_id'], 'product_cat' );
			}
			$categories[ $category['id'] ] = $term->term_id;
			unset( $pending[ $key ] );
			++$created;
		}
		if ( 0 === $created ) {
			WP_CLI::error( 'A product category has a parent that is not in the fixture.' );
		}
	}
	$category_ids = array();
	foreach ( $fixture['product_categories'] as $category ) {
		$category_ids[ $category['slug'] ] = $categories[ $category['id'] ];
	}

	// Global attributes and their terms.
	foreach ( $fixture['product_attributes'] as $attribute ) {
		$taxonomy = $attribute['taxonomy'];
		if ( 0 === wc_attribute_taxonomy_id_by_name( $taxonomy ) ) {
			wc_create_attribute(
				array(
					'name' => $attribute['name'],
					'slug' => substr( $taxonomy, 3 ),
					'type' => 'select',
				)
			);
		}
		if ( ! taxonomy_exists( $taxonomy ) ) {
			// WooCommerce registers it on the next request; this request needs it now.
			register_taxonomy( $taxonomy, 'product' );
		}
		foreach ( $attribute['terms'] as $term ) {
			if ( null === term_exists( $term['slug'], $taxonomy ) ) {
				wp_insert_term( $term['name'], $taxonomy, array( 'slug' => $term['slug'] ) );
			}
		}
	}

	$loaded = 0;
	foreach ( $fixture['products'] as $row ) {
		if ( null !== get_post( $row['id'] ) ) {
			WP_CLI::log( "Skipped {$row['id']}: the ID is taken." );
			continue;
		}
		$id = wp_insert_post(
			array(
				'import_id'   => $row['id'],
				'post_type'   => 'product',
				'post_status' => $row['status'],
				'post_title'  => $row['name'],
			),
			true
		);
		if ( $id !== $row['id'] ) {
			WP_CLI::error( "Product {$row['id']} could not keep its ID." );
		}

		$product    = new WC_Product_Simple( $id );
		$attributes = array();
		foreach ( $row['attributes'] as $attribute ) {
			$term_ids = array();
			foreach ( $attribute['terms'] as $slug ) {
				$term_ids[] = get_term_by( 'slug', $slug, $attribute['taxonomy'] )->term_id;
			}
			$product_attribute = new WC_Product_Attribute();
			$product_attribute->set_id( wc_attribute_taxonomy_id_by_name( $attribute['taxonomy'] ) );
			$product_attribute->set_name( $attribute['taxonomy'] );
			$product_attribute->set_options( $term_ids );
			$product_attribute->set_position( $attribute['position'] );
			$product_attribute->set_visible( $attribute['visible'] );
			$product_attribute->set_variation( false );
			$attributes[ $attribute['taxonomy'] ] = $product_attribute;
		}
		$product->set_sku( $row['sku'] );
		$product->set_category_ids( array_map( static fn ( string $slug ): int => $category_ids[ $slug ], $row['categories'] ) );
		$product->set_attributes( $attributes );
		$product->save();
		foreach ( $row['meta'] as $key => $value ) {
			if ( null !== $value ) {
				update_post_meta( $id, $key, wp_slash( $value ) );
			}
		}
		++$loaded;
	}
	WP_CLI::success( "{$loaded} products loaded." );
} )();
