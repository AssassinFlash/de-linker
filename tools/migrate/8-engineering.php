<?php
/**
 * The WordPress side of tools/migrate/8-engineering.py: reads, or writes, the
 * engineering data that tools/migrate/8-engineering.json names — the pa_series
 * attribute, the figures of ticket #8's engine keys (new entries and citation
 * completions), and the per-product document list.
 *
 * 8-engineering.py hands this file to `wp eval-file -` with its request (JSON,
 * base64) in place of the placeholder argument at the end. WP-CLI evaluates
 * the file, and evaluated code cannot start with a strict_types declaration,
 * so this file has none. The answer is one JSON line after the request's
 * marker on stdout; a failure is an exception, which WP-CLI reports with a
 * non-zero exit status.
 *
 * @package Linker\Commerce
 */

defined( 'ABSPATH' ) || exit;

( static function ( string $payload ): void {
	// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- base64 lets any request JSON sit in the single-quoted literal 8-engineering.py writes into this file.
	$request = json_decode( base64_decode( $payload ), true, 512, JSON_THROW_ON_ERROR );

	$figures_key   = '_tv_b2b_figures';
	$documents_key = '_linker_documents';

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

	$read_product = static function ( int $product_id ) use ( $term_slugs, $attached_slugs, $figures_key, $documents_key ): ?array {
		$product = wc_get_product( $product_id );
		if ( ! $product instanceof WC_Product ) {
			return null;
		}

		return array(
			'attributes' => array(
				'pa_series' => array(
					'terms'    => $term_slugs( $product_id, 'pa_series' ),
					'attached' => $attached_slugs( $product, 'pa_series' ),
				),
			),
			'figures'    => (string) get_post_meta( $product_id, $figures_key, true ),
			'documents'  => (string) get_post_meta( $product_id, $documents_key, true ),
			// What the migration must leave as it is (docs/specs/8-engineering-data.md, 不做).
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
	};

	$read = static function () use ( $request, $read_product ): array {
		$products = array();
		foreach ( $request['products'] as $product_id ) {
			$products[ $product_id ] = $read_product( (int) $product_id );
		}

		$term_counts = array();
		foreach ( ( $request['remove_terms'] ?? array() ) as $entry ) {
			foreach ( $entry['slugs'] as $slug ) {
				$term = get_term_by( 'slug', $slug, $entry['taxonomy'] );
				if ( $term instanceof WP_Term ) {
					$term_counts[ $entry['taxonomy'] . ':' . $slug ] = (int) $term->count;
				}
			}
		}

		return array(
			'siteurl'     => get_option( 'siteurl' ),
			// An empty PHP array would encode as a list; the caller reads it by key.
			'term_counts' => (object) $term_counts,
			'products'    => $products,
			'series_attr' => wc_attribute_taxonomy_id_by_name( 'pa_series' ),
		);
	};

	$decode_figures = static function ( int $product_id ) use ( $figures_key ): array {
		$figures = json_decode( (string) get_post_meta( $product_id, $figures_key, true ), true );
		if ( ! is_array( $figures ) ) {
			throw new RuntimeException( esc_html( "Product {$product_id} has no readable figures." ) );
		}

		return $figures;
	};

	$save_figures = static function ( int $product_id, array $figures ) use ( $figures_key ): void {
		// The live figures are stored with unescaped Unicode and slashes; the rewrite keeps that form.
		update_post_meta( $product_id, $figures_key, wp_slash( (string) wp_json_encode( $figures, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) ) );
		wc_delete_product_transients( $product_id );
	};

	$write = static function () use ( $request, $decode_figures, $save_figures, $documents_key ): array {
		// The pa_series attribute must exist as a global attribute before anything is written.
		$settings = $request['new_attribute']['pa_series'];
		if ( wc_attribute_taxonomy_id_by_name( 'pa_series' ) === 0 ) {
			$added = wc_create_attribute(
				array(
					'name'         => 'Series',
					'slug'         => 'series',
					'type'         => 'select',
					'order_by'     => 'menu_order',
					'has_archives' => false,
				)
			);
			if ( is_wp_error( $added ) ) {
				throw new RuntimeException( esc_html( $added->get_error_message() ) );
			}
		}
		register_taxonomy( 'pa_series', array( 'product' ) );

		// Terms the plan removes: only when nothing uses them (the plan states 0 products).
		foreach ( $request['remove_terms'] as $entry ) {
			foreach ( $entry['slugs'] as $slug ) {
				$term = get_term_by( 'slug', $slug, $entry['taxonomy'] );
				if ( $term instanceof WP_Term ) {
					if ( $term->count > 0 ) {
						throw new RuntimeException( esc_html( "Term {$entry['taxonomy']}/{$slug} is in use ({$term->count}); refusing to delete." ) );
					}
					wp_delete_term( $term->term_id, $entry['taxonomy'] );
				}
			}
		}

		// Attributes: one read-check-save per product, with all its term changes.
		$changes = array();
		foreach ( $request['attributes'] as $change ) {
			$changes[ $change['product'] ][] = $change;
		}
		foreach ( $changes as $product_id => $product_changes ) {
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
			$attributes = $product->get_attributes();
			foreach ( $product_changes as $change ) {
				$taxonomy = $change['taxonomy'];
				if ( array() === $change['to'] ) {
					unset( $attributes[ $taxonomy ] );
					continue;
				}
				$term_ids = array();
				foreach ( $change['to'] as $slug ) {
					$term = get_term_by( 'slug', $slug, $taxonomy );
					if ( ! $term instanceof WP_Term ) {
						$made = wp_insert_term( $slug, $taxonomy );
						if ( is_wp_error( $made ) ) {
							throw new RuntimeException( esc_html( "Creating {$taxonomy}/{$slug} failed: " . $made->get_error_message() ) );
						}
						$term = get_term( (int) $made['term_id'], $taxonomy );
					}
					if ( ! $term instanceof WP_Term ) {
						throw new RuntimeException( esc_html( "{$taxonomy} has no term {$slug}." ) );
					}
					$term_ids[] = $term->term_id;
				}
				$attribute = $attributes[ $taxonomy ] ?? null;
				if ( $attribute instanceof WC_Product_Attribute ) {
					// A copy: changing the product's own object leaves set_attributes() nothing to compare, and save() skips it.
					$attribute = clone $attribute;
				} else {
					$attribute = new WC_Product_Attribute();
					$attribute->set_id( wc_attribute_taxonomy_id_by_name( $taxonomy ) );
					$attribute->set_name( $taxonomy );
					$attribute->set_position( $settings['position'] );
					$attribute->set_visible( $settings['visible'] );
					$attribute->set_variation( false );
				}
				$attribute->set_options( $term_ids );
				$attributes[ $taxonomy ] = $attribute;
			}
			$product->set_attributes( $attributes );
			$product->save();
		}

		// Figures: whole entries for absent keys.
		foreach ( $request['figures'] as $change ) {
			$figures                   = $decode_figures( $change['product'] );
			$figures[ $change['key'] ] = $change['to'];
			$save_figures( $change['product'], $figures );
		}

		// Citations: the citation of an existing entry; value, unit and value_de stay as they are.
		foreach ( $request['citations'] as $change ) {
			$figures = $decode_figures( $change['product'] );
			$entry   = $figures[ $change['key'] ] ?? null;
			if ( ! is_array( $entry ) ) {
				throw new RuntimeException( esc_html( "Product {$change['product']} has no figure {$change['key']} to cite." ) );
			}
			if ( (string) $entry['value'] !== (string) $change['value'] ) {
				throw new RuntimeException( esc_html( "Product {$change['product']} figure {$change['key']} holds {$entry['value']}, the citation is for {$change['value']}." ) );
			}
			$entry['citation']         = $change['citation'];
			$figures[ $change['key'] ] = $entry;
			$save_figures( $change['product'], $figures );
		}

		// Documents: the product's list, once.
		foreach ( $request['documents'] as $change ) {
			update_post_meta( $change['product'], $documents_key, wp_slash( (string) wp_json_encode( $change['to'], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) ) );
		}

		return array( 'written' => true );
	};

	$answer = 'write' === $request['action'] ? $write() : $read();
	// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- JSON for 8-engineering.py on the command line, not HTML.
	echo "\n" . $request['marker'] . wp_json_encode( $answer ) . "\n";
} )( '8-engineering-payload' );
