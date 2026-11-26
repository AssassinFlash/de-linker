<?php
/**
 * Register R3 marketing photographs and convert the featured PNGs in place.
 * Run through batch_r3_pages.py with WP-CLI.
 *
 * @package Linker\Migrate
 */

( static function (): void {
	if ( ! defined( 'WP_CLI' ) || ! WP_CLI ) {
		return;
	}
	require_once ABSPATH . 'wp-admin/includes/image.php';
	global $wpdb;

	$task       = json_decode( base64_decode( '__R3_MEDIA__' ), true, 512, JSON_THROW_ON_ERROR ); // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- JSON payload from the paired WP-CLI command.
	$uploads    = wp_get_upload_dir();
	$dir        = '2026/11/';
	$logo_name  = 'linker-footer-wordmark-r3';
	$photo_file = static fn( string $name ): string => $dir . $name . '-r3.webp';
	$exists     = static function ( string $relative ) use ( $wpdb ): int {
		return (int) $wpdb->get_var( $wpdb->prepare( "SELECT post_id FROM %i WHERE meta_key = '_wp_attached_file' AND meta_value = %s ORDER BY post_id LIMIT 1", $wpdb->postmeta, $relative ) );
	};
	$check      = static function ( $value ) {
		if ( is_wp_error( $value ) ) {
			throw new RuntimeException( esc_html( $value->get_error_message() ) );
		}
		return $value;
	};
	$original   = static function ( int $id ): string {
		$file = get_attached_file( $id );
		if ( ! $file || ! is_file( $file ) ) {
			throw new RuntimeException( esc_html( "Missing original for attachment $id" ) );
		}
		return $file;
	};
	$picture    = static function ( int $id ) use ( $uploads, $original ): ?array {
		if ( ! $id ) {
			return null;
		}
		$meta   = wp_get_attachment_metadata( $id );
		$srcset = wp_get_attachment_image_srcset( $id, 'full' );
		$src    = wp_get_attachment_image_src( $id, 'full' );
		$medium = wp_get_attachment_image_url( $id, 'medium_large' );
		if ( ! $src || ! $medium || ! $srcset || empty( $meta['sizes'] ) || 'image/webp' !== get_post_mime_type( $id ) ) {
			throw new RuntimeException( esc_html( "Missing registered WebP sizes for $id" ) );
		}
		$file = $original( $id );
		foreach ( $meta['sizes'] as $size ) {
			if ( ! is_file( dirname( $file ) . '/' . $size['file'] ) ) {
				throw new RuntimeException( esc_html( 'Missing derivative ' . $size['file'] ) );
			}
		}
		$relative = static fn( string $url ): string => str_replace( $uploads['baseurl'], wp_make_link_relative( $uploads['baseurl'] ), $url );
		return array(
			'id'           => $id,
			'src'          => $relative( $src[0] ),
			'width'        => $src[1],
			'height'       => $src[2],
			'srcset'       => $relative( $srcset ),
			'medium_large' => $relative( $medium ),
			'bytes'        => filesize( $file ),
		);
	};
	$register   = static function ( string $file, string $name ) use ( $check, $uploads, $exists ): int {
		$id = $exists( _wp_relative_upload_path( $file ) );
		if ( ! $id ) {
			$id = $check(
				wp_insert_attachment(
					array(
						'post_title'     => $name,
						'post_mime_type' => 'image/webp',
						'guid'           => $uploads['baseurl'] . '/' . _wp_relative_upload_path( $file ),
					),
					$file,
					0,
					true
				)
			);
		}
		wp_update_attachment_metadata( $id, wp_generate_attachment_metadata( $id, $file ) );
		return (int) $id;
	};

	$result = array();
	switch ( $task['mode'] ) {
		case 'inventory':
		case 'readback':
			$result['site']   = home_url();
			$result['covers'] = array();
			if ( 'inventory' === $task['mode'] ) {
				$ids = $wpdb->get_col( "SELECT DISTINCT thumb.meta_value FROM {$wpdb->posts} p JOIN {$wpdb->postmeta} thumb ON thumb.post_id = p.ID AND thumb.meta_key = '_thumbnail_id' JOIN {$wpdb->postmeta} f ON f.post_id = thumb.meta_value AND f.meta_key = '_wp_attached_file' WHERE p.post_type = 'product' AND p.post_status = 'publish' AND f.meta_value LIKE '%.png' ORDER BY thumb.meta_value" );
				foreach ( $ids as $id ) {
					$result['covers'][] = array(
						'id'    => (int) $id,
						'file'  => get_post_meta( $id, '_wp_attached_file', true ),
						'mime'  => get_post_mime_type( $id ),
						'meta'  => wp_get_attachment_metadata( $id ),
						'bytes' => filesize( $original( (int) $id ) ),
					);
				}
			} else {
				foreach ( $task['ids'] as $id ) {
					$result['covers'][] = $picture( $id );
				}
			}
			foreach ( $task['names'] as $name ) {
				$result['photos'][ $name ] = $picture( $exists( $photo_file( $name ) ) );
			}
			$result['logo'] = $picture( $exists( $dir . $logo_name . '.webp' ) );
			break;
		case 'photo':
		case 'logo':
			$logo     = 'logo' === $task['mode'];
			$name     = $logo ? $logo_name : $task['name'];
			$relative = $logo ? $dir . $logo_name . '.webp' : $photo_file( $name );
			$file     = $uploads['basedir'] . '/' . $relative;
			$id       = $exists( $relative );
			if ( $logo ) {
				add_image_size( 'linker-footer-120', 120, 0, false );
				add_image_size( 'linker-footer-240', 240, 0, false );
			}
			if ( ! $id || empty( wp_get_attachment_metadata( $id )['sizes'] ) ) {
				wp_mkdir_p( dirname( $file ) );
				if ( $logo ) {
					$editor = $check( wp_get_image_editor( $uploads['basedir'] . '/2026/07/linker-logo-wordmark-1.png' ) );
					$check( $editor->resize( 360, null, false ) );
					$check( $editor->save( $file, 'image/webp' ) );
				} else {
					require_once ABSPATH . 'wp-admin/includes/class-wp-filesystem-base.php';
					require_once ABSPATH . 'wp-admin/includes/class-wp-filesystem-direct.php';
					$filesystem = new WP_Filesystem_Direct( null );
					$data       = base64_decode( $task['data'], true ); // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- Decode supplied WebP bytes.
					if ( false === $data || ! $filesystem->put_contents( $file, $data, 0644 ) ) {
						throw new RuntimeException( esc_html( "Could not save $name" ) );
					}
				}
				$id = $register( $file, $name );
			}
			$result = $picture( $id );
			break;
		case 'cover':
		case 'restore_cover':
			$item     = $task['item'];
			$id       = $item['id'];
			$relative = substr( $item['file'], 0, -4 ) . '-r3.webp';
			$file     = $uploads['basedir'] . '/' . $relative;
			$current  = get_post_meta( $id, '_wp_attached_file', true );
			if ( ! in_array( $current, array( $relative, $item['file'] ), true ) ) {
				throw new RuntimeException( esc_html( "Attachment $id has changed" ) );
			}
			if ( 'restore_cover' === $task['mode'] ) {
				if ( $relative === $current ) {
					$meta = wp_get_attachment_metadata( $id );
					update_attached_file( $id, $item['file'] );
					wp_update_attachment_metadata( $id, $item['meta'] );
					$check(
						wp_update_post(
							array(
								'ID'             => $id,
								'post_mime_type' => $item['mime'],
							),
							true
						)
					);
					foreach ( $meta['sizes'] ?? array() as $size ) {
						if ( str_starts_with( $size['file'], basename( $file, '.webp' ) . '-' ) ) {
							wp_delete_file( dirname( $file ) . '/' . $size['file'] );
						}
					}
					wp_delete_file( $file );
				}
				break;
			}
			if ( $current !== $relative || ( wp_get_attachment_metadata( $id )['file'] ?? '' ) !== $relative || empty( wp_get_attachment_metadata( $id )['sizes'] ) ) {
				$editor = $check( wp_get_image_editor( $uploads['basedir'] . '/' . $item['file'] ) );
				$check( $editor->save( $file, 'image/webp' ) );
				$check(
					wp_update_post(
						array(
							'ID'             => $id,
							'post_mime_type' => 'image/webp',
						),
						true
					)
				);
				update_attached_file( $id, $file );
				wp_update_attachment_metadata( $id, wp_generate_attachment_metadata( $id, $file ) );
			}
			$result = $picture( $id );
			break;
		case 'restore_registrations':
			foreach ( $task['names'] as $name ) {
				$id = $exists( $photo_file( $name ) );
				if ( $id && empty( $task['before']['photos'][ $name ] ) ) {
					wp_delete_attachment( $id, true );
				}
			}
			$id = $exists( $dir . $logo_name . '.webp' );
			if ( $id && empty( $task['before']['logo'] ) ) {
				wp_delete_attachment( $id, true );
			}
			break;
	}
	echo '@@r3-media@@' . wp_json_encode( $result, JSON_UNESCAPED_SLASHES );
} )();
