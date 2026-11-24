<?php
/**
 * Proportional brand marks from the WordPress media library.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

/** The PDP and document library display the same mark at different heights. */
final class BrandLogo {

	/**
	 * Read the native uncropped media image and give the browser the mark's rendered width.
	 *
	 * @param string $slug Brand term slug.
	 * @param int    $height Display height in CSS pixels.
	 * @return array{src:string,srcset:string,sizes:string,width:int,height:int}|null
	 */
	public static function image( string $slug, int $height ): ?array {
		if ( '' === $slug ) {
			return null;
		}
		$attachments = get_posts(
			array(
				'post_type'      => 'attachment',
				'posts_per_page' => 1,
				'fields'         => 'ids',
				'no_found_rows'  => true,
				'post_status'    => 'inherit',
				'meta_key'       => '_wp_attached_file', // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key -- Native media file lookup.
				's'              => 'our-brand-' . $slug . '-mono-light',
			)
		);
		$id          = (int) ( $attachments[0] ?? 0 );
		$image       = $id ? wp_get_attachment_image_src( $id, 'medium' ) : false;
		if ( ! $image ) {
			return null;
		}
		return array(
			'src'    => $image[0],
			'srcset' => (string) wp_get_attachment_image_srcset( $id, 'medium' ),
			'sizes'  => (int) ceil( $height * $image[1] / $image[2] ) . 'px',
			'width'  => $image[1],
			'height' => $image[2],
		);
	}
}
