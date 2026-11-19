<?php
/**
 * Retire audited non-supply Woo identities and their public taxonomy entries.
 *
 * Run with WP-CLI:
 * wp eval-file tools/migrate/1168-retire-pv-supply.php plan
 * wp eval-file tools/migrate/1168-retire-pv-supply.php apply
 *
 * Take the normal database/uploads backup before apply. Orders are immutable;
 * records referenced by an order, and their language partners, remain private.
 *
 * @package Linker\Migrate
 */

use Linker\Commerce\Products\Publication;
use Linker\Commerce\Products\Publication\PreparationJobs;

( static function ( array $args ): void {
	if ( ! in_array( $args, array( array( 'plan' ), array( 'apply' ) ), true ) ) {
		WP_CLI::error( 'Use plan or apply.' );
	}

	global $wpdb;
	$write    = 'apply' === $args[0];
	$qa       = 'linker-publication-618-00accee8-c638-4ac7-9cce-1b49694ab7fd';
	$pairs    = array(
		'trina-solar-ts4-f2'                  => array( 4135, 6603 ),
		'trina-solar-ts4-m2'                  => array( 4136, 6602 ),
		'trina-vertex-s-plus-tsm-460neg9r-28' => array( 4137 ),
		'trina-solar-tsm-460neg9r-28'         => array( 8349, 8350 ),
		'qa-unpriced-article-188'             => array( 6561, 6564 ),
		$qa                                   => array( 8351, 8352 ),
	);
	$ids      = array_merge( ...array_values( $pairs ) );
	$products = array();
	foreach ( $pairs as $slug => $pair ) {
		$lines = 0;
		foreach ( $pair as $id ) {
			// Historical Woo order items retain their original product IDs, including HPOS.
			$count = $wpdb->get_var( $wpdb->prepare( "SELECT COUNT(*) FROM {$wpdb->prefix}woocommerce_order_itemmeta WHERE meta_key IN ('_product_id','_variation_id') AND meta_value = %s", (string) $id ) );
			if ( null === $count ) {
				WP_CLI::error( "Could not read order history for product {$id}." );
			}
			$lines += (int) $count;
		}
		foreach ( $pair as $id ) {
			$post = get_post( $id );
			if ( ! $post ) {
				continue;
			}
			$name = preg_replace( '/__trashed$/D', '', $post->post_name );
			if ( 'product' !== $post->post_type || $name !== $slug || ( 'publish' === $post->post_status && ! in_array( $id, array( 8349, 8350 ), true ) ) ) {
				WP_CLI::error( "Unexpected product at {$id}; verify its supply status and identity." );
			}
			if ( 0 === $lines || 'private' !== $post->post_status ) {
				$products[ $id ] = $lines > 0 ? 'retain_private' : 'remove';
			}
		}
	}
	$remove_terms = array();
	$taxonomies   = array(
		'pa_brand'      => array( 'trina-solar' ),
		'product_brand' => array( 'trina-solar' ),
		'pa_model'      => array( 'ts4-f2', 'ts4-m2', 'tsm-460neg9r-28', 'tsm-450neg9r-28' ),
	);
	foreach ( $taxonomies as $taxonomy => $slugs ) {
		foreach ( $slugs as $slug ) {
			$term = get_term_by( 'slug', $slug, $taxonomy );
			if ( ! $term ) {
				continue;
			}
			$objects = get_objects_in_term( $term->term_id, $taxonomy );
			if ( is_wp_error( $objects ) || array_diff( array_map( 'intval', $objects ), $ids ) ) {
				WP_CLI::error( "The {$taxonomy}/{$slug} term has another owner; review it before removing the archive." );
			}
			$remove_terms[ $taxonomy ][ $term->term_id ] = $slug;
		}
	}
	$manuals         = array(
		5267 => '2026/09/240916_Datasheet_Vertex-S_NEG9R.28_DE_2024_C_web.pdf',
		5268 => '2026/09/240831_Datasheet_Vertex-S_NEG9R.28_EN_2024_C_web.pdf',
		5273 => '2026/09/TS4-Connector-Trina-Solar.pdf',
	);
	$withdraw        = array();
	$protected_paths = array();
	foreach ( $manuals as $id => $file ) {
		if ( ! get_post( $id ) ) {
			continue;
		}
		if ( 'attachment' !== get_post_type( $id ) || get_post_meta( $id, '_wp_attached_file', true ) !== $file ) {
			WP_CLI::error( "Unexpected media identity at {$id}." );
		}
		if ( '0' !== get_post_meta( $id, '_linker_document_public', true ) ) {
			$withdraw[]        = $id;
			$protected_paths[] = wp_parse_url( (string) wp_get_attachment_url( $id ), PHP_URL_PATH );
		}
	}
	$uploads       = wp_get_upload_dir();
	$fixture_files = array();
	foreach ( array( 'original.pdf', 'alias.pdf' ) as $filename ) {
		$relative = $qa . '/' . $filename;
		if ( is_file( $uploads['basedir'] . '/' . $relative ) ) {
			$fixture_files[]   = $relative;
			$protected_paths[] = wp_parse_url( $uploads['baseurl'] . '/' . $relative, PHP_URL_PATH );
		}
	}
	if ( $protected_paths ) {
		// Include drafts and language partners. An inactive association still belongs to its product.
		$stored = $wpdb->get_col( "SELECT ID FROM {$wpdb->posts} WHERE post_type = 'product'" );
		if ( '' !== $wpdb->last_error ) {
			WP_CLI::error( 'Could not check current document associations.' );
		}
		foreach ( array_diff( array_map( 'intval', $stored ), $ids ) as $other ) {
			foreach ( Publication::document_rows( $other ) as $row ) {
				foreach ( array_merge( array( $row['url'] ?? '' ), $row['aliases'] ?? array() ) as $url ) {
					if ( in_array( wp_parse_url( $url, PHP_URL_PATH ), $protected_paths, true ) ) {
						WP_CLI::error( "Product {$other} shares a document; review the association before withdrawal." );
					}
				}
			}
		}
	}
	$report = array(
		'products'            => $products,
		'terms'               => $remove_terms,
		'withdraw_documents'  => $withdraw,
		'remove_fixture_pdfs' => $fixture_files,
	);
	if ( $write && array_filter( $report ) ) {
		foreach ( $products as $id => $action ) {
			if ( 'retain_private' === $action ) {
				$result = wp_update_post(
					array(
						'ID'          => $id,
						'post_status' => 'private',
					),
					true
				);
				if ( is_wp_error( $result ) ) {
					WP_CLI::error( $result->get_error_message() );
				}
			} elseif ( get_post( $id ) && ! wp_delete_post( $id, true ) ) {
				WP_CLI::error( "Could not remove product {$id}." );
			}
		}
		foreach ( $withdraw as $id ) {
			update_post_meta( $id, '_linker_document_public', '0' );
		}
		foreach ( $remove_terms as $taxonomy => $terms ) {
			foreach ( $terms as $id => $slug ) {
				if ( ! term_exists( $id, $taxonomy ) ) {
					continue;
				}
				$result = wp_delete_term( $id, $taxonomy );
				if ( is_wp_error( $result ) || false === $result ) {
					WP_CLI::error( "Could not remove {$taxonomy}/{$slug}." );
				}
			}
		}
		foreach ( $fixture_files as $relative ) {
			if ( ! wp_delete_file_from_directory( $uploads['basedir'] . '/' . $relative, $uploads['basedir'] . '/' . $qa ) ) {
				WP_CLI::error( "Could not remove the fixture file {$relative}." );
			}
		}
		( new PreparationJobs() )->changed();
	}
	WP_CLI::log( (string) wp_json_encode( $report, JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT ) );
} )( $args ?? array() );
