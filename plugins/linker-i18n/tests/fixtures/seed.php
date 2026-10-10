<?php
/**
 * Loads the live fixture into a local instance, as the #6 snapshot would:
 * English objects with the old plugin's German in `_linker_de_*` meta, the
 * old slug map, and dictionary rows for SEO texts and category descriptions.
 * Run without this plugin and Polylang, as the live site has neither:
 * `wp eval-file plugins/linker-i18n/tests/fixtures/seed.php --skip-plugins=linker-i18n,polylang`.
 *
 * Idempotent: objects are found again by `_linker_fixture_id`, the live ID.
 * Live URLs are rewritten to the instance's, as `wp search-replace` does
 * when a snapshot is loaded (docs/specs/6-live-pull.md).
 *
 * The file has no strict_types declaration: wp eval-file evaluates it.
 *
 * @package Linker\I18n
 */

// phpcs:disable WordPress.NamingConventions.PrefixAllGlobals -- a WP-CLI script, not plugin code.
// phpcs:disable WordPress.DB.DirectDatabaseQuery -- the old plugin's dictionary table is created and filled as it is on the live site.

( static function (): void {
	$fixture_dir = __DIR__ . '/live';
	$read        = static function ( string $name ) use ( $fixture_dir ): array {
		// phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- a fixture file.
		$data = json_decode( (string) file_get_contents( $fixture_dir . '/' . $name ), true );
		return is_array( $data ) ? $data : array();
	};
	$local       = static fn( string $text ): string => str_replace( array( 'https://de-linker.com', 'https:\/\/de-linker.com' ), array( untrailingslashit( home_url() ), str_replace( '/', '\/', untrailingslashit( home_url() ) ) ), $text );
	$find_post   = static function ( int $live_id ): int {
		$ids = get_posts(
			array(
				'post_type'   => 'any',
				'post_status' => 'any',
				'meta_key'    => '_linker_fixture_id', // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key -- a handful of fixture posts.
				'meta_value'  => (string) $live_id, // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_value -- a handful of fixture posts.
				'fields'      => 'ids',
				'numberposts' => 1,
			)
		);
		return array() === $ids ? 0 : (int) $ids[0];
	};
	$find_term   = static function ( string $taxonomy, int $live_id ): int {
		$ids = get_terms(
			array(
				'taxonomy'   => $taxonomy,
				'hide_empty' => false,
				// A meta query, not meta_key: WooCommerce sets meta_key itself to order product categories.
				'meta_query' => array( // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_query -- a handful of fixture terms.
					array(
						'key'   => '_linker_fixture_id',
						'value' => (string) $live_id,
					),
				),
				'fields'     => 'ids',
			)
		);
		return is_array( $ids ) && array() !== $ids ? (int) $ids[0] : 0;
	};
	$upsert_term = static function ( string $taxonomy, array $term, int $parent_id ) use ( $find_term ): int {
		$args = array(
			'slug'        => $term['slug'],
			'description' => $term['description'] ?? '',
			'parent'      => $parent_id,
		);
		$id   = $find_term( $taxonomy, (int) $term['id'] );
		if ( $id > 0 ) {
			wp_update_term( $id, $taxonomy, array( 'name' => $term['name'] ) + $args );
			return $id;
		}
		$created = wp_insert_term( $term['name'], $taxonomy, $args );
		if ( is_wp_error( $created ) ) {
			WP_CLI::error( $taxonomy . ' ' . $term['slug'] . ': ' . $created->get_error_message() );
		}
		update_term_meta( (int) $created['term_id'], '_linker_fixture_id', (string) $term['id'] );
		return (int) $created['term_id'];
	};

	kses_remove_filters();

	// The sample content of a new install and the pages WooCommerce creates on
	// activation would take the live pages' slugs (cart, my-account, …).
	foreach ( array( 'hello-world', 'sample-page', 'privacy-policy', 'refund_returns', 'shop', 'cart', 'checkout', 'my-account' ) as $sample ) {
		foreach ( get_posts(
			array(
				'post_type'   => array( 'post', 'page' ),
				'post_status' => 'any',
				'name'        => $sample,
				'numberposts' => -1,
				'fields'      => 'ids',
			)
		) as $post_id ) {
			if ( '' === (string) get_post_meta( (int) $post_id, '_linker_fixture_id', true ) ) {
				wp_delete_post( (int) $post_id, true );
			}
		}
	}

	// The shop: euro, Germany, open to visitors, bank transfer as the one payment
	// method (an inquiry is paid off line; the site has no online payment).
	update_option( 'woocommerce_currency', 'EUR' );
	update_option( 'woocommerce_default_country', 'DE:DE-ST' );
	update_option( 'woocommerce_coming_soon', 'no' );
	update_option( 'woocommerce_store_pages_only', 'no' );
	update_option( 'woocommerce_enable_guest_checkout', 'yes' );
	update_option(
		'woocommerce_bacs_settings',
		array(
			'enabled'      => 'yes',
			'title'        => 'Proforma invoice',
			'description'  => '',
			'instructions' => '',
		)
	);

	// Attributes and the terms the fixture products use; the live attribute IDs
	// differ from the local ones, the slugs do not.
	$attribute_terms = array();
	$attribute_slugs = array();
	foreach ( $read( 'attributes.json' ) as $attribute ) {
		$taxonomy                                  = (string) $attribute['slug'];
		$attribute_slugs[ (int) $attribute['id'] ] = $taxonomy;
		if ( ! taxonomy_exists( $taxonomy ) ) {
			$created = wc_create_attribute(
				array(
					'name'         => $attribute['name'],
					'slug'         => substr( $taxonomy, 3 ),
					'type'         => $attribute['type'],
					'order_by'     => $attribute['order_by'],
					'has_archives' => (bool) $attribute['has_archives'],
				)
			);
			if ( is_wp_error( $created ) ) {
				WP_CLI::error( $taxonomy . ': ' . $created->get_error_message() );
			}
			register_taxonomy( $taxonomy, array( 'product' ), array( 'hierarchical' => false ) );
		}
		foreach ( $attribute['terms'] as $term ) {
			$attribute_terms[ $taxonomy ][ $term['name'] ] = $upsert_term( $taxonomy, $term, 0 );
		}
	}

	// Product categories, parents first.
	$categories = $read( 'product-categories.json' );
	usort( $categories, static fn( array $a, array $b ): int => (int) ( 0 !== $a['parent'] ) <=> (int) ( 0 !== $b['parent'] ) );
	$category_ids = array();
	foreach ( $categories as $category ) {
		$category_ids[ (int) $category['id'] ] = $upsert_term( 'product_cat', $category, $category_ids[ (int) $category['parent'] ] ?? 0 );
	}

	// Post categories.
	$post_category_ids = array();
	foreach ( $read( 'post-categories.json' ) as $category ) {
		$post_category_ids[ (int) $category['id'] ] = $upsert_term( 'category', $category, 0 );
	}

	// Pages and posts, parents first. The German body is the one the live German
	// page shows (pull_live.py); the old plugin keeps it in `_linker_de_content`.
	$items = array_merge( $read( 'pages.json' ), $read( 'posts.json' ) );
	usort( $items, static fn( array $a, array $b ): int => (int) ( 0 !== $a['parent'] ) <=> (int) ( 0 !== $b['parent'] ) );
	$post_ids = array();
	foreach ( $items as $item ) {
		$postarr = array(
			'post_type'      => $item['type'],
			'post_status'    => $item['status'],
			'post_name'      => $item['slug'],
			'post_title'     => $item['title'],
			'post_content'   => $local( $item['content'] ),
			'post_excerpt'   => $item['excerpt'],
			'post_parent'    => $post_ids[ (int) $item['parent'] ] ?? 0,
			'menu_order'     => (int) $item['menu_order'],
			'comment_status' => 'closed',
		);
		$id      = $find_post( (int) $item['id'] );
		if ( $id > 0 ) {
			$postarr['ID'] = $id;
		}
		$saved = wp_insert_post( wp_slash( $postarr ), true );
		if ( is_wp_error( $saved ) ) {
			WP_CLI::error( $item['slug'] . ': ' . $saved->get_error_message() );
		}
		$id = (int) $saved;
		update_post_meta( $id, '_linker_fixture_id', (string) $item['id'] );
		// The live theme's template (the local theme has another set): kept as data, as the snapshot holds it.
		if ( '' !== (string) $item['template'] ) {
			update_post_meta( $id, '_wp_page_template', (string) $item['template'] );
		}
		$post_ids[ (int) $item['id'] ] = $id;
		if ( 'post' === $item['type'] ) {
			wp_set_post_categories( $id, array_values( array_intersect_key( $post_category_ids, array_flip( $item['categories'] ) ) ) );
		}
		foreach ( $item['seo'] as $key => $value ) {
			if ( '' !== $value ) {
				update_post_meta( $id, $key, wp_slash( $value ) );
			}
		}
		update_post_meta( $id, '_linker_de_title', wp_slash( $item['de']['title'] ) );
		if ( null !== $item['de']['content_rendered'] ) {
			update_post_meta( $id, '_linker_de_content', wp_slash( $local( $item['de']['content_rendered'] ) ) );
		}
		if ( '' !== $item['de']['excerpt_rendered'] ) {
			update_post_meta( $id, '_linker_de_excerpt', wp_slash( trim( wp_strip_all_tags( $item['de']['excerpt_rendered'] ) ) ) );
		}
	}

	// Products.
	foreach ( $read( 'products.json' ) as $item ) {
		$id      = $find_post( (int) $item['id'] );
		$product = $id > 0 ? wc_get_product( $id ) : new WC_Product_Simple();
		if ( ! $product instanceof WC_Product ) {
			WP_CLI::error( 'product ' . $item['slug'] );
		}
		$attributes = array();
		foreach ( $item['attributes'] as $position => $attribute ) {
			$taxonomy = $attribute_slugs[ (int) $attribute['id'] ];
			$object   = new WC_Product_Attribute();
			$object->set_id( (int) wc_attribute_taxonomy_id_by_name( $taxonomy ) );
			$object->set_name( $taxonomy );
			$object->set_options( array_values( array_map( static fn( string $name ): int => (int) ( $attribute_terms[ $taxonomy ][ $name ] ?? 0 ), $attribute['options'] ) ) );
			$object->set_position( (int) $attribute['position'] );
			$object->set_visible( (bool) $attribute['visible'] );
			$object->set_variation( false );
			$attributes[ $taxonomy ] = $object;
		}
		$product->set_props(
			array(
				'name'              => $item['name'],
				'slug'              => $item['slug'],
				'status'            => $item['status'],
				'sku'               => $item['sku'],
				'regular_price'     => $item['regular_price'],
				'sale_price'        => $item['sale_price'],
				'tax_status'        => $item['tax_status'],
				'tax_class'         => $item['tax_class'],
				'manage_stock'      => (bool) $item['manage_stock'],
				'stock_status'      => $item['stock_status'],
				'weight'            => $item['weight'],
				'length'            => $item['dimensions']['length'],
				'width'             => $item['dimensions']['width'],
				'height'            => $item['dimensions']['height'],
				'menu_order'        => (int) $item['menu_order'],
				'description'       => $local( $item['description'] ),
				'short_description' => $local( $item['short_description'] ),
				'category_ids'      => array_values( array_intersect_key( $category_ids, array_flip( $item['categories'] ) ) ),
				'attributes'        => $attributes,
			)
		);
		$id = $product->save();
		update_post_meta( $id, '_linker_fixture_id', (string) $item['id'] );
		foreach ( $item['meta'] as $key => $value ) {
			update_post_meta( $id, $key, wp_slash( is_string( $value ) ? $local( $value ) : $value ) );
		}
	}

	// The site's front page, posts page and WooCommerce pages.
	$site = $read( 'site.json' );
	update_option( 'show_on_front', $site['show_on_front'] );
	update_option( 'page_on_front', $post_ids[ (int) $site['page_on_front'] ] ?? 0 );
	update_option( 'page_for_posts', $post_ids[ (int) $site['page_for_posts'] ] ?? 0 );
	foreach ( array( 'shop', 'cart', 'checkout', 'myaccount' ) as $page ) {
		update_option( "woocommerce_{$page}_page_id", $post_ids[ (int) $site[ "woocommerce_{$page}_page_id" ] ] ?? 0 );
	}

	// The old plugin's slug map: English slug => German slug, as the live German
	// URLs show them (pages and posts whose German address differs).
	$slug_map = array();
	foreach ( $items as $item ) {
		$de_url = $item['live']['de_url'];
		if ( ! is_string( $de_url ) || '' === $item['slug'] ) {
			continue;
		}
		$segments = explode( '/', trim( (string) wp_parse_url( $de_url, PHP_URL_PATH ), '/' ) );
		$german   = (string) end( $segments );
		if ( 'de' !== $german && $german !== $item['slug'] ) {
			$slug_map[ $item['slug'] ] = $german;
		}
	}
	update_option( 'linker_i18n_slug_map', $slug_map, false );

	// The old plugin's dictionary (source_sha, context, source, target, status,
	// review_sha, updated_at; status 1 = machine): the German SEO titles and
	// descriptions and category descriptions the live German pages show.
	global $wpdb;
	$table = $wpdb->prefix . 'linker_string';
	$wpdb->query( "CREATE TABLE IF NOT EXISTS {$table} ( source_sha CHAR(40) NOT NULL, context VARCHAR(32) NOT NULL DEFAULT '', source LONGTEXT NOT NULL, target LONGTEXT NOT NULL, status TINYINT NOT NULL DEFAULT 0, review_sha CHAR(40) NULL, updated_at BIGINT NOT NULL DEFAULT 0, UNIQUE KEY source_context (source_sha, context), KEY status (status) ) {$wpdb->get_charset_collate()}" ); // phpcs:ignore WordPress.DB.PreparedSQL.InterpolatedNotPrepared, WordPress.DB.DirectDatabaseQuery.SchemaChange -- a fixture table with a fixed name.
	$pairs = array();
	foreach ( $items as $item ) {
		$german = $item['live']['de'] ?? null;
		if ( ! is_array( $german ) ) {
			continue;
		}
		$pairs[ $item['seo']['_seopress_titles_title'] ] = (string) $german['title'];
		$pairs[ $item['seo']['_seopress_titles_desc'] ]  = (string) $german['description'];
	}
	foreach ( $categories as $category ) {
		$german = $category['live']['de'] ?? null;
		if ( is_array( $german ) ) {
			$pairs[ (string) $category['description'] ] = (string) $german['description'];
		}
	}
	foreach ( $pairs as $source => $target ) {
		if ( '' === trim( (string) $source ) || '' === trim( $target ) ) {
			continue;
		}
		$wpdb->replace(
			$table,
			array(
				'source_sha' => sha1( (string) $source ),
				'context'    => '',
				'source'     => (string) $source,
				'target'     => $target,
				'status'     => 1,
				'updated_at' => time(),
			)
		);
	}

	flush_rewrite_rules( false );
	WP_CLI::success( sprintf( 'Fixture loaded: %d pages and posts, %d products, %d categories, %d dictionary rows.', count( $items ), count( $read( 'products.json' ) ), count( $categories ), count( $pairs ) ) );
} )();
