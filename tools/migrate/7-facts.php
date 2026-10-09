<?php
/**
 * The WordPress side of tools/migrate/7-facts.py: reads, or writes, the
 * product attributes and figures that tools/migrate/7-facts.json names.
 *
 * 7-facts.py hands this file to `wp eval-file -` with its request (JSON,
 * base64) in place of the placeholder argument at the end. WP-CLI
 * evaluates the file, and evaluated code cannot start with a strict_types
 * declaration, so this file has none. The answer is one JSON line after the
 * request's marker on stdout; a failure is an exception, which WP-CLI reports
 * with a non-zero exit status.
 *
 * @package Linker\Commerce
 */

defined( 'ABSPATH' ) || exit;

( static function ( string $payload ): void {
	// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- base64 keeps the request one shell word over SSH.
	$request  = json_decode( base64_decode( $payload ), true, 512, JSON_THROW_ON_ERROR );
	$meta_key = $request['meta_key'];

	// Slugs of the product's terms in a taxonomy, read from the database, sorted.
	$term_slugs = static function ( int $product_id, string $taxonomy ): array {
		$slugs = wp_get_object_terms( $product_id, $taxonomy, array( 'fields' => 'slugs' ) );
		if ( ! is_array( $slugs ) ) {
			return array();
		}
		$slugs = array_map( 'strval', $slugs );
		sort( $slugs );

		return $slugs;
	};

	// Slugs of the terms of the product's own attribute (null when it has none), sorted.
	$attached_slugs = static function ( WC_Product $product, string $taxonomy ): ?array {
		$attribute = $product->get_attributes()[ $taxonomy ] ?? null;
		if ( ! $attribute instanceof WC_Product_Attribute ) {
			return null;
		}
		$slugs = array();
		foreach ( $attribute->get_options() as $term_id ) {
			$term    = get_term( (int) $term_id, $taxonomy );
			$slugs[] = $term instanceof WP_Term ? $term->slug : '#' . $term_id;
		}
		sort( $slugs );

		return $slugs;
	};

	$read = static function () use ( $request, $meta_key, $term_slugs, $attached_slugs ): array {
		$products = array();
		foreach ( $request['products'] as $product_id ) {
			$product = wc_get_product( $product_id );
			if ( ! $product instanceof WC_Product ) {
				$products[ $product_id ] = null;
				continue;
			}
			$attributes = array();
			foreach ( $request['taxonomies'] as $taxonomy ) {
				$attributes[ $taxonomy ] = array(
					'terms'    => $term_slugs( $product_id, $taxonomy ),
					'attached' => $attached_slugs( $product, $taxonomy ),
				);
			}
			$products[ $product_id ] = array(
				'attributes' => $attributes,
				'figures'    => (string) get_post_meta( $product_id, $meta_key, true ),
				// What the migration must leave as it is (docs/specs/7-selection-facts.md, 不做).
				'protected'  => array(
					'name'              => $product->get_name(),
					'sku'               => $product->get_sku(),
					'status'            => $product->get_status(),
					'description'       => md5( $product->get_description() ),
					'short_description' => md5( $product->get_short_description() ),
					'regular_price'     => $product->get_regular_price(),
					'sale_price'        => $product->get_sale_price(),
					'manage_stock'      => $product->get_manage_stock(),
					'stock_quantity'    => $product->get_stock_quantity(),
					'stock_status'      => $product->get_stock_status(),
					'backorders'        => $product->get_backorders(),
					'low_stock_amount'  => $product->get_low_stock_amount(),
				),
			);
		}

		return array(
			'siteurl'  => get_option( 'siteurl' ),
			'products' => $products,
		);
	};

	$write = static function () use ( $request, $meta_key ): array {
		// Each product is read, checked and saved once, with all its attribute changes.
		$changes  = array();
		$products = array();
		foreach ( $request['attributes'] as $change ) {
			$changes[ $change['product'] ][] = $change;
		}
		foreach ( array_keys( $changes ) as $product_id ) {
			$product = wc_get_product( $product_id );
			if ( ! $product instanceof WC_Product ) {
				throw new RuntimeException( esc_html( "Product {$product_id} does not exist." ) );
			}
			// save() first runs validate_props(), which realigns the stock fields; nothing is written if that would change one.
			$probe = clone $product;
			$probe->validate_props();
			if ( array() !== $probe->get_changes() ) {
				throw new RuntimeException( esc_html( "Saving product {$product_id} would change " . implode( ', ', array_keys( $probe->get_changes() ) ) . '.' ) );
			}
			$products[ $product_id ] = $product;
		}
		foreach ( $products as $product_id => $product ) {
			$attributes = $product->get_attributes();
			foreach ( $changes[ $product_id ] as $change ) {
				$taxonomy = $change['taxonomy'];
				if ( array() === $change['to'] ) {
					unset( $attributes[ $taxonomy ] );
					continue;
				}
				$attribute = $attributes[ $taxonomy ] ?? null;
				if ( $attribute instanceof WC_Product_Attribute ) {
					// A copy: changing the product's own object leaves set_attributes() nothing to compare, and save() skips it.
					$attribute = clone $attribute;
				} else {
					$settings  = $request['new_attribute'][ $taxonomy ];
					$attribute = new WC_Product_Attribute();
					$attribute->set_id( wc_attribute_taxonomy_id_by_name( $taxonomy ) );
					$attribute->set_name( $taxonomy );
					$attribute->set_position( $settings['position'] );
					$attribute->set_visible( $settings['visible'] );
					$attribute->set_variation( false );
				}
				$term_ids = array();
				foreach ( $change['to'] as $slug ) {
					$term = get_term_by( 'slug', $slug, $taxonomy );
					if ( ! $term instanceof WP_Term ) {
						throw new RuntimeException( esc_html( "{$taxonomy} has no term {$slug}." ) );
					}
					$term_ids[] = $term->term_id;
				}
				$attribute->set_options( $term_ids );
				$attributes[ $taxonomy ] = $attribute;
			}
			$product->set_attributes( $attributes );
			$product->save();
		}
		foreach ( $request['figures'] as $change ) {
			$figures = json_decode( (string) get_post_meta( $change['product'], $meta_key, true ), true );
			if ( ! is_array( $figures ) ) {
				throw new RuntimeException( esc_html( "Product {$change['product']} has no readable figures." ) );
			}
			$figures[ $change['key'] ] = $change['to'];
			// The live figures are stored with unescaped Unicode and slashes; the rewrite keeps that form.
			update_post_meta( $change['product'], $meta_key, wp_slash( (string) wp_json_encode( $figures, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) ) );
			wc_delete_product_transients( $change['product'] );
		}

		return array( 'written' => true );
	};

	$answer = 'write' === $request['action'] ? $write() : $read();
	// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- JSON for 7-facts.py on the command line, not HTML.
	echo "\n" . $request['marker'] . wp_json_encode( $answer ) . "\n";
} )( '7-facts-payload' );
