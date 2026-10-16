<?php
/**
 * The WordPress side of tools/migrate/7-facts.py: reads, or writes, the
 * product attributes, the figures and the product page copy that the facts
 * plan names. A figure whose "to" is null is removed; any other "to" replaces
 * the stored entry. A copy change writes one string at its path inside a
 * legacy ACF JSON meta (the English table `_tv_legacy_acf_json`, the German
 * twin `_linker_de_acf_json` on the English product).
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

if ( ! function_exists( 'seven_facts_drop_legacy_row' ) ) {
	/**
	 * Removes one spec row, matched by its English or German label, from the
	 * legacy tables the product page still renders.
	 *
	 * The English table is `_tv_legacy_acf_json`. The German table is
	 * `_linker_de_acf_json` on the English source row. The source copy
	 * `_linker_de_source_acf_json` is what the translation was made from; it
	 * is not rendered, and it stays.
	 *
	 * A drop may leave a group with no rows. Removing that group is a change
	 * of the table's structure (a whole tab leaves the product page), so it
	 * happens only where the drop names the group in `remove_groups`:
	 * otherwise the write is refused before it touches a meta — the drop must
	 * say out loud that the group leaves, or the group stays.
	 *
	 * @param int                  $product_id Product ID.
	 * @param array<string, mixed> $drop       titles, labels and remove_groups, each a string or a list of strings.
	 *
	 * @throws RuntimeException When the drop would remove a group it does not name.
	 */
	function seven_facts_drop_legacy_row( int $product_id, array $drop ): void { // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedFunctionFound -- This helper exists only inside this wp eval-file script; it is never part of the plugin's namespace.
		$titles = array_map( 'strval', (array) ( $drop['titles'] ?? array() ) );
		$labels = array_map( 'strval', (array) ( $drop['labels'] ?? array() ) );
		$remove = array_map( 'strval', (array) ( $drop['remove_groups'] ?? array() ) );
		$keys   = array( '_tv_legacy_acf_json', '_linker_de_acf_json' );
		$write  = static function ( int $product_id, string $meta_key, array $decoded, array $titles, array $labels ): void {
			$groups = array();
			foreach ( $decoded['spec_groups'] as $group ) {
				if ( ! is_array( $group ) || ! isset( $group['spec_rows'] ) || ! is_array( $group['spec_rows'] ) ) {
					$groups[] = $group;
					continue;
				}
				$rows = array();
				foreach ( $group['spec_rows'] as $row ) {
					$row_label = is_array( $row ) ? (string) ( $row['spec_label'] ?? '' ) : '';
					if ( in_array( (string) ( $group['spec_group_title'] ?? '' ), $titles, true ) && in_array( $row_label, $labels, true ) ) {
						continue;
					}
					$rows[] = $row;
				}
				if ( array() === $rows ) {
					continue;
				}
				$group['spec_rows'] = $rows;
				$groups[]           = $group;
			}
			$decoded['spec_groups'] = $groups;
			update_post_meta(
				$product_id,
				$meta_key,
				wp_slash( (string) wp_json_encode( $decoded, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) )
			);
		};
		// The refusal walks both tables before the first meta is written, so
		// a drop that refuses leaves the product as it was.
		$tables = array();
		foreach ( $keys as $meta_key ) {
			$decoded = json_decode( (string) get_post_meta( $product_id, $meta_key, true ), true );
			if ( ! is_array( $decoded ) || ! isset( $decoded['spec_groups'] ) || ! is_array( $decoded['spec_groups'] ) ) {
				continue;
			}
			foreach ( $decoded['spec_groups'] as $group ) {
				if ( ! is_array( $group ) || ! isset( $group['spec_rows'] ) || ! is_array( $group['spec_rows'] ) ) {
					continue;
				}
				$title = (string) ( $group['spec_group_title'] ?? '' );
				if ( ! in_array( $title, $titles, true ) ) {
					continue;
				}
				$left = array_filter(
					$group['spec_rows'],
					static fn( $row ): bool => ! in_array( is_array( $row ) ? (string) ( $row['spec_label'] ?? '' ) : '', $labels, true )
				);
				if ( array() === $left && ! in_array( $title, $remove, true ) ) {
					$refusal = "Dropping these rows would remove the spec group \"{$title}\" of product {$product_id} ({$meta_key}). Name the group in drop_legacy.remove_groups to remove it with the row.";
					// An uncaught exception reaches the operator as WordPress's
					// generic critical-error line; the reason goes to stderr first.
					// phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fwrite -- CLI refusal; there is no WP_Filesystem at this point.
					fwrite( STDERR, $refusal . "\n" );
					throw new RuntimeException( esc_html( $refusal ) );
				}
			}
			$tables[ $meta_key ] = $decoded;
		}
		foreach ( $tables as $meta_key => $decoded ) {
			$write( $product_id, $meta_key, $decoded, $titles, $labels );
		}
	}
}

if ( ! function_exists( 'seven_facts_set_legacy_path' ) ) {
	/**
	 * One string of a legacy ACF JSON meta, replaced at its path.
	 *
	 * The meta keys and sides are the same map tools/migrate/7-facts.py reads:
	 * the English table `_tv_legacy_acf_json`, the German twin
	 * `_linker_de_acf_json` on the English source row, both read from the
	 * English product. A path that is not there is a refusal, not a create:
	 * the plan's "from" described the site as it is, so the path must exist.
	 *
	 * @param int                  $product_id Product ID.
	 * @param array<string, mixed> $change     meta_key, path and the new value.
	 *
	 * @throws RuntimeException When the meta is not readable JSON, or the path is not there.
	 */
	function seven_facts_set_legacy_path( int $product_id, array $change ): void { // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedFunctionFound -- This helper exists only inside this wp eval-file script; it is never part of the plugin's namespace.
		$meta_key = (string) ( $change['meta_key'] ?? '' );
		$path     = array_values( (array) ( $change['path'] ?? array() ) );
		if ( '' === $meta_key || array() === $path ) {
			throw new RuntimeException( 'A legacy copy change needs a meta_key and a path.' );
		}
		$decoded = json_decode( (string) get_post_meta( $product_id, $meta_key, true ), true );
		if ( ! is_array( $decoded ) ) {
			throw new RuntimeException( esc_html( "Product {$product_id} has no readable {$meta_key}." ) );
		}
		$last = array_pop( $path );
		$node = &$decoded;
		foreach ( $path as $step ) {
			if ( ! is_array( $node ) || ! array_key_exists( $step, $node ) ) {
				throw new RuntimeException( esc_html( "Product {$product_id} has no {$meta_key} at that path." ) );
			}
			$node = &$node[ $step ];
		}
		if ( ! is_array( $node ) || ! array_key_exists( $last, $node ) ) {
			throw new RuntimeException( esc_html( "Product {$product_id} has no {$meta_key} at that path." ) );
		}
		$node[ $last ] = $change['to'];
		unset( $node );
		update_post_meta(
			$product_id,
			$meta_key,
			wp_slash( (string) wp_json_encode( $decoded, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) )
		);
	}
}

( static function ( string $payload ): void {
	// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- base64 lets any request JSON sit in the single-quoted literal 7-facts.py writes into this file.
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
					'legacy'     => array(
						'en' => (string) get_post_meta( $product_id, '_tv_legacy_acf_json', true ),
						'de' => (string) get_post_meta( $product_id, '_linker_de_acf_json', true ),
					),
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
			if ( null === $change['to'] ) {
				unset( $figures[ $change['key'] ] );
				// The product page still reads the legacy spec table. A key the
				// datasheet does not support must not stay there as a cited row.
				if ( isset( $change['drop_legacy'] ) && is_array( $change['drop_legacy'] ) ) {
					seven_facts_drop_legacy_row( (int) $change['product'], $change['drop_legacy'] );
				}
			} else {
				$figures[ $change['key'] ] = $change['to'];
			}
			// The live figures are stored with unescaped Unicode and slashes; the rewrite keeps that form.
			update_post_meta( $change['product'], $meta_key, wp_slash( (string) wp_json_encode( $figures, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) ) );
			wc_delete_product_transients( $change['product'] );
		}
		foreach ( $request['legacy_copy'] ?? array() as $change ) {
			seven_facts_set_legacy_path( (int) $change['product'], $change );
		}

		return array( 'written' => true );
	};

	$answer = 'write' === $request['action'] ? $write() : $read();
	// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- JSON for 7-facts.py on the command line, not HTML.
	echo "\n" . $request['marker'] . wp_json_encode( $answer ) . "\n";
} )( '7-facts-payload' );
