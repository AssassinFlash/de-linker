<?php
/**
 * Publish reversible WebP copies of the six GoodWe commercial product galleries.
 *
 * @package Linker\Migrate
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Migrate\T3;

use Linker\Commerce\Products\Materials;
use RuntimeException;

const MEDIA_MODELS = array( 'goodwe-gw50k-et-10', 'goodwe-gw100k-ht', 'goodwe-gw120k-ht', 'goodwe-lx-c101-10', 'goodwe-lx-c138-10', 'goodwe-lx-c156-10' );
const MEDIA_FIELDS = array( '_thumbnail_id', '_product_image_gallery', '_tv_legacy_acf_json', '_linker_de_acf_json' );

/**
 * Identify an existing derivative by its source attachment ID.
 *
 * @param int $source Original PNG attachment.
 */
function media_derivative( int $source ): int {
	$ids = get_posts(
		array(
			'post_type'        => 'attachment',
			'post_status'      => 'inherit',
			'post_mime_type'   => 'image/webp',
			'fields'           => 'ids',
			'numberposts'      => 1,
			'lang'             => '',
			'meta_key'         => '_linker_t3_png_source', // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key -- One-time lookup of the seven migration-owned attachments, independent of the admin locale.
			'meta_value'       => (string) $source, // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_value -- Stable original media ID.
			'suppress_filters' => true,
		)
	);
	return $ids ? (int) $ids[0] : 0;
}

/**
 * Snapshot exact product metadata and original media, including shared galleries.
 *
 * @return array<string,array<int,mixed>>
 * @throws RuntimeException When a model, language twin, or source is missing.
 */
function media_snapshot(): array {
	$products = array();
	$sources  = array();
	foreach ( MEDIA_MODELS as $slug ) {
		$page = get_page_by_path( $slug, OBJECT, 'product' );
		$pair = $page ? pll_get_post_translations( $page->ID ) : array();
		if ( ! isset( $pair['en'], $pair['de'] ) ) {
			throw new RuntimeException( 'The bilingual GoodWe product pair is missing.' );
		}
		foreach ( array( $pair['en'], $pair['de'] ) as $id ) {
			$product = wc_get_product( $id );
			if ( ! $product || 'publish' !== $product->get_status() ) {
				throw new RuntimeException( 'A selected GoodWe product is no longer published.' );
			}
			foreach ( MEDIA_FIELDS as $key ) {
				$products[ $id ][ $key ] = get_post_meta( $id, $key, false );
			}
			foreach ( Materials::gallery_ids( $product, Materials::acf( $id ) ) as $image ) {
				if ( isset( $sources[ $image ] ) || 'image/png' !== get_post_mime_type( $image ) ) {
					continue;
				}
				$file = get_attached_file( $image );
				if ( ! $file || ! is_file( $file ) ) {
					throw new RuntimeException( 'The original gallery PNG is missing.' );
				}
				$sources[ $image ] = array(
					'file'     => (string) get_post_meta( $image, '_wp_attached_file', true ),
					'existing' => media_derivative( $image ),
				);
			}
		}
	}
	return array(
		'products' => $products,
		'sources'  => $sources,
	);
}

/**
 * Return a current derivative, or generate and register its responsive sources.
 *
 * @param int    $source Original attachment ID.
 * @param string $relative Original file relative to uploads.
 * @throws RuntimeException When the image conversion or registration fails.
 */
function media_webp( int $source, string $relative ): int {
	require_once ABSPATH . 'wp-admin/includes/image.php';
	$png = get_attached_file( $source );
	if ( ! $png || ! is_file( $png ) || get_post_meta( $source, '_wp_attached_file', true ) !== $relative || 'image/png' !== wp_get_image_mime( $png ) ) {
		throw new RuntimeException( 'Original GoodWe image changed since the snapshot.' );
	}
	$webp = substr( $png, 0, -4 ) . '.webp';
	$id   = media_derivative( $source );
	if ( ! $id ) {
		if ( file_exists( $webp ) ) {
			throw new RuntimeException( 'The target filename already belongs to another image.' );
		}
		$id = wp_insert_attachment(
			array(
				'post_mime_type' => 'image/webp',
				'post_title'     => get_the_title( $source ),
				'post_status'    => 'inherit',
				'meta_input'     => array(
					'_linker_t3_png_source'    => $source,
					'_wp_attachment_image_alt' => get_post_meta( $source, '_wp_attachment_image_alt', true ),
				),
			),
			$webp,
			0,
			true
		);
		if ( is_wp_error( $id ) ) {
			throw new RuntimeException( esc_html( $id->get_error_message() ) );
		}
	}
	if ( get_attached_file( $id ) !== $webp ) {
		throw new RuntimeException( 'Registered WebP no longer uses the expected file.' );
	}
	if ( ! is_file( $webp ) ) {
		$editor = wp_get_image_editor( $png );
		if ( is_wp_error( $editor ) ) {
			throw new RuntimeException( esc_html( $editor->get_error_message() ) );
		}
		$quality = $editor->set_quality( 88 );
		if ( is_wp_error( $quality ) ) {
			throw new RuntimeException( esc_html( $quality->get_error_message() ) );
		}
		$result = $editor->save( $webp, 'image/webp' );
		if ( is_wp_error( $result ) ) {
			throw new RuntimeException( esc_html( $result->get_error_message() ) );
		}
	}
	$original  = wp_getimagesize( $png );
	$converted = wp_getimagesize( $webp );
	if ( ! $original || ! $converted || 'image/webp' !== $converted['mime'] || $original[0] !== $converted[0] || $original[1] !== $converted[1] || filesize( $webp ) >= filesize( $png ) ) {
		throw new RuntimeException( 'WebP must preserve the PNG dimensions and use fewer bytes.' );
	}
	$meta = wp_get_attachment_metadata( $id );
	if ( empty( $meta['sizes'] ) ) {
		$meta = wp_generate_attachment_metadata( $id, $webp );
		wp_update_attachment_metadata( $id, $meta );
	}
	if ( empty( $meta['sizes'] ) ) {
		throw new RuntimeException( 'Missing responsive WebP sizes.' );
	}
	foreach ( $meta['sizes'] as $size ) {
		$file = dirname( $webp ) . '/' . $size['file'];
		if ( ! is_file( $file ) || 'image/webp' !== wp_get_image_mime( $file ) || filesize( $file ) >= filesize( $png ) ) {
			throw new RuntimeException( 'Incomplete responsive WebP image.' );
		}
	}
	return $id;
}

/**
 * Rebind only the image fields consumed by Materials::gallery_ids().
 *
 * @param string         $key Native or legacy metadata field.
 * @param mixed          $value Original stored value.
 * @param array<int,int> $map Original ID to WebP attachment.
 * @return mixed
 */
function media_rebind( string $key, $value, array $map ) {
	if ( '_thumbnail_id' === $key ) {
		return (string) ( $map[ (int) $value ] ?? $value );
	}
	if ( '_product_image_gallery' === $key ) {
		$ids = is_array( $value ) ? $value : explode( ',', $value );
		$ids = array_map( static fn( $id ) => $map[ (int) $id ] ?? $id, $ids );
		return is_array( $value ) ? $ids : implode( ',', $ids );
	}
	if ( ! is_string( $value ) || '' === $value ) {
		return $value;
	}
	$fields  = json_decode( $value, true, 512, JSON_THROW_ON_ERROR );
	$changed = false;
	foreach ( array(
		'product_gallery'       => 'gallery_image',
		'feature_cards'         => 'feature_image',
		'application_scenarios' => 'scenario_image',
	) as $group => $name ) {
		foreach ( $fields[ $group ] ?? array() as $index => $row ) {
			$source = (int) ( $row[ $name ] ?? 0 );
			if ( isset( $map[ $source ] ) ) {
				$fields[ $group ][ $index ][ $name ] = $map[ $source ];
				$changed                             = true;
			}
		}
	}
	return $changed ? wp_json_encode( $fields, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR ) : $value;
}

/**
 * Update only snapshotted gallery fields; refuse to overwrite intervening edits.
 *
 * @param array<int,array<string,array<int,mixed>>> $products Snapshotted fields.
 * @param array<int,int>                            $map Original ID to WebP attachment.
 * @param bool                                      $restore Restore original values.
 * @throws RuntimeException When the current gallery differs from both known versions.
 */
function media_write_fields( array $products, array $map, bool $restore ): void {
	foreach ( $products as $id => $fields ) {
		foreach ( $fields as $key => $values ) {
			if ( ! $values ) {
				continue;
			}
			$old  = $values[0];
			$next = media_rebind( $key, $old, $map );
			if ( $old === $next ) {
				continue;
			}
			$current = get_post_meta( $id, $key, false );
			$target  = $restore ? $old : $next;
			if ( array( $target ) === $current ) {
				continue;
			}
			if ( array( $restore ? $next : $old ) !== $current ) {
				throw new RuntimeException( 'The GoodWe gallery was edited after the snapshot.' );
			}
			update_post_meta( $id, $key, wp_slash( $target ) );
			if ( array( $target ) !== get_post_meta( $id, $key, false ) ) {
				throw new RuntimeException( 'The new gallery reference could not be read back.' );
			}
		}
	}
}

/**
 * Convert shared photos once and publish them on both product languages.
 *
 * @param array<string,array<int,mixed>> $snapshot Original gallery state.
 */
function media_apply( array $snapshot ): void {
	$map = array();
	foreach ( $snapshot['sources'] as $id => $source ) {
		$map[ $id ] = media_webp( $id, $source['file'] );
	}
	media_write_fields( $snapshot['products'], $map, false );
}

/**
 * A restored gallery can release its copy only if no other post adopted it.
 *
 * @param int $id Migration-owned WebP attachment ID.
 */
function media_in_use( int $id ): bool {
	global $wpdb;
	if ( wp_get_post_parent_id( $id ) ) {
		return true;
	}
	// phpcs:disable WordPress.DB.DirectDatabaseQuery -- One-time rollback checks the native media consumers, including unpublished work.
	$references = $wpdb->get_results(
		$wpdb->prepare(
			"SELECT meta_key, meta_value FROM {$wpdb->postmeta}
			WHERE meta_key IN ('_thumbnail_id', '_product_image_gallery', '_tv_legacy_acf_json', '_linker_de_acf_json')
			AND meta_value LIKE %s",
			'%' . $id . '%'
		)
	);
	foreach ( $references as $reference ) {
		$value = maybe_unserialize( $reference->meta_value );
		if ( media_rebind( $reference->meta_key, $value, array( $id => 0 ) ) !== $value ) {
			return true;
		}
	}
	if ( $wpdb->get_var( $wpdb->prepare( "SELECT term_id FROM {$wpdb->termmeta} WHERE meta_key = 'thumbnail_id' AND meta_value = %s LIMIT 1", (string) $id ) ) ) {
		return true;
	}
	$image = (string) get_attached_file( $id );
	$stem  = pathinfo( $image, PATHINFO_FILENAME );
	$texts = $wpdb->get_col(
		$wpdb->prepare(
			"SELECT post_content FROM {$wpdb->posts} WHERE post_content LIKE %s OR post_content LIKE %s",
			'%' . $wpdb->esc_like( $stem ) . '%',
			'%' . $id . '%'
		)
	);
	// phpcs:enable WordPress.DB.DirectDatabaseQuery
	$metadata = wp_get_attachment_metadata( $id );
	$files    = array_merge( array( basename( $image ) ), wp_list_pluck( $metadata['sizes'] ?? array(), 'file' ) );
	foreach ( $texts as $text ) {
		foreach ( $files as $file ) {
			if ( str_contains( $text, $file ) ) {
				return true;
			}
		}
		if ( preg_match( '/\bwp-image-' . $id . '\b|<!-- wp:image\s+\{[^}]*"id"\s*:\s*' . $id . '\b/', $text ) ) {
			return true;
		}
		if ( has_shortcode( $text, 'gallery' ) && preg_match_all( '/' . get_shortcode_regex( array( 'gallery' ) ) . '/s', $text, $matches ) ) {
			foreach ( $matches[3] as $attributes ) {
				$gallery = shortcode_parse_atts( $attributes );
				if ( in_array( $id, wp_parse_id_list( $gallery['ids'] ?? $gallery['include'] ?? array() ), true ) ) {
					return true;
				}
			}
		}
	}
	return false;
}

/**
 * Restore original galleries and delete only this rollout's generated attachments.
 *
 * @param array<string,array<int,mixed>> $snapshot Original gallery state.
 * @throws RuntimeException When an owned attachment cannot be removed.
 */
function media_restore( array $snapshot ): void {
	$map = array();
	foreach ( $snapshot['sources'] as $id => $source ) {
		$derivative = media_derivative( $id );
		if ( $derivative ) {
			$map[ $id ] = $derivative;
		}
	}
	media_write_fields( $snapshot['products'], $map, true );
	foreach ( $map as $id => $derivative ) {
		if ( ! $snapshot['sources'][ $id ]['existing'] && ! media_in_use( $derivative ) && ! wp_delete_attachment( $derivative, true ) ) {
			throw new RuntimeException( 'Cannot remove a generated WebP attachment.' );
		}
	}
}
