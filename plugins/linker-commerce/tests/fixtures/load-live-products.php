<?php
/**
 * Seeds a local WordPress with live-products-2026-10-09.json: the product
 * categories, the global attributes and terms the products use, and the 89
 * products under their live IDs with their attributes, figures and document
 * URLs. It reproduces the catalogue the selection-facts expectations were
 * converted against, so the REST route and tools/migrate/7-facts.py can be run
 * on real WooCommerce data of that day. It runs only where
 * wp_get_environment_type() is "local" and skips products whose ID is taken.
 *
 * Usage: wp eval-file --use-include plugins/linker-commerce/tests/fixtures/load-live-products.php
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

defined( 'ABSPATH' ) || exit;

( static function (): void {
	if ( 'local' !== wp_get_environment_type() ) {
		throw new RuntimeException( 'This seeds local instances only (WP_ENVIRONMENT_TYPE is not "local").' );
	}
	// phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- a file beside this script.
	$fixture = json_decode( (string) file_get_contents( __DIR__ . '/live-products-2026-10-09.json' ), true, 512, JSON_THROW_ON_ERROR );

	// The term of a slug, created with the name when the taxonomy lacks it.
	$term_id = static function ( string $taxonomy, string $slug, string $name, int $parent_id = 0 ): int {
		$term = get_term_by( 'slug', $slug, $taxonomy );
		if ( $term instanceof WP_Term ) {
			return $term->term_id;
		}
		$created = wp_insert_term(
			$name,
			$taxonomy,
			array(
				'slug'   => $slug,
				'parent' => max( 0, $parent_id ),
			)
		);
		if ( is_wp_error( $created ) ) {
			throw new RuntimeException( esc_html( "{$taxonomy} {$slug}: " . $created->get_error_message() ) );
		}

		return (int) $created['term_id'];
	};

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
			$categories[ $category['id'] ] = $term_id( 'product_cat', $category['slug'], $category['name'], $parent );
			unset( $pending[ $key ] );
			++$created;
		}
		if ( 0 === $created ) {
			throw new RuntimeException( 'A product category has a parent that is not in the fixture.' );
		}
	}
	$category_ids = array();
	foreach ( $fixture['product_categories'] as $category ) {
		$category_ids[ $category['slug'] ] = $categories[ $category['id'] ];
	}

	// Global attributes and their terms; slug => term ID per taxonomy.
	$attribute_terms = array();
	foreach ( $fixture['product_attributes'] as $attribute ) {
		$taxonomy = $attribute['taxonomy'];
		if ( 0 === wc_attribute_taxonomy_id_by_name( $taxonomy ) ) {
			$created = wc_create_attribute(
				array(
					'name' => $attribute['name'],
					'slug' => substr( $taxonomy, 3 ),
					'type' => 'select',
				)
			);
			if ( is_wp_error( $created ) ) {
				throw new RuntimeException( esc_html( "{$taxonomy}: " . $created->get_error_message() ) );
			}
		}
		if ( ! taxonomy_exists( $taxonomy ) ) {
			// WooCommerce registers it on the next request; this request needs it now.
			register_taxonomy( $taxonomy, 'product' );
		}
		foreach ( $attribute['terms'] as $term ) {
			$attribute_terms[ $taxonomy ][ $term['slug'] ] = $term_id( $taxonomy, $term['slug'], $term['name'] );
		}
	}

	$loaded = 0;
	foreach ( $fixture['products'] as $row ) {
		if ( null !== get_post( $row['id'] ) ) {
			echo esc_html( "Skipped {$row['id']}: the ID is taken." ) . "\n";
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
		if ( is_wp_error( $id ) || $id !== $row['id'] ) {
			throw new RuntimeException( esc_html( "Product {$row['id']} could not keep its ID." ) );
		}

		$attributes = array();
		foreach ( $row['attributes'] as $attribute ) {
			$product_attribute = new WC_Product_Attribute();
			$product_attribute->set_id( wc_attribute_taxonomy_id_by_name( $attribute['taxonomy'] ) );
			$product_attribute->set_name( $attribute['taxonomy'] );
			$product_attribute->set_options( array_map( static fn ( string $slug ): int => $attribute_terms[ $attribute['taxonomy'] ][ $slug ], $attribute['terms'] ) );
			$product_attribute->set_position( $attribute['position'] );
			$product_attribute->set_visible( $attribute['visible'] );
			$product_attribute->set_variation( false );
			$attributes[ $attribute['taxonomy'] ] = $product_attribute;
		}
		$product = new WC_Product_Simple( $id );
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
	echo esc_html( "{$loaded} products loaded." ) . "\n";
} )();
