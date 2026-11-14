<?php
/**
 * Give the About/Über uns body images the responsive attributes WordPress omitted,
 * and stop the mobile-only photo layer from downloading on desktop.
 *
 * Measured on production 2026-11-14 at 1440 and 390:
 *  - .mt-visual is display:none above 800px, yet the JS-created <img> downloads
 *    2048-2560px originals: 1,395,060 bytes no desktop visitor can see.
 *  - Three body images have no srcset and transfer their original file for a
 *    564-719px box.
 *
 * Run: wp eval-file about-images.php            (report only)
 *      LINKER_ABOUT_APPLY=1 wp eval-file about-images.php  (write)
 *
 * @package Linker\Commerce
 */

$apply = '1' === getenv( 'LINKER_ABOUT_APPLY' );

/**
 * Measured display box per file, as a sizes attribute.
 *
 * @return array<string,string>
 */
function linker_about_sizes(): array {
	return array(
		'linker-residential-hybrid-from-linker'     => '(max-width: 600px) 360px, (max-width: 768px) 418px, (max-width: 1024px) 566px, 719px',
		'linker-trusted-on-commercial-bess'         => '(max-width: 600px) 360px, (max-width: 1024px) 444px, 564px',
		'linker-trusted-on-microgrid-projects'      => '(max-width: 600px) 360px, (max-width: 1024px) 444px, 564px',
		'linker-outdoor-cabinets-from-linker'       => '(max-width: 600px) 360px, (max-width: 1024px) 444px, 564px',
		'linker-container-bess-from-linker'         => '(max-width: 600px) 360px, (max-width: 1024px) 444px, 564px',
	);
}

/**
 * srcset from the attachment metadata WordPress already stored.
 *
 * @param int    $id   Attachment id.
 * @param string $full Original URL.
 * @return string
 */
function linker_about_srcset( int $id, string $full ): string {
	$meta = wp_get_attachment_metadata( $id );
	if ( ! is_array( $meta ) || empty( $meta['sizes'] ) ) {
		return '';
	}
	$base = trailingslashit( dirname( $full ) );
	$rows = array();
	if ( ! empty( $meta['width'] ) ) {
		$rows[] = array( (int) $meta['width'], $full );
	}
	foreach ( $meta['sizes'] as $size ) {
		if ( empty( $size['file'] ) || empty( $size['width'] ) ) {
			continue;
		}
		$rows[] = array( (int) $size['width'], $base . $size['file'] );
	}
	if ( count( $rows ) < 2 ) {
		return '';
	}
	usort( $rows, static fn( array $a, array $b ): int => $a[0] <=> $b[0] );
	$parts = array();
	$seen  = array();
	foreach ( $rows as list( $width, $url ) ) {
		if ( isset( $seen[ $width ] ) ) {
			continue;
		}
		$seen[ $width ] = true;
		$parts[]        = $url . ' ' . $width . 'w';
	}
	return implode( ', ', $parts );
}

/**
 * Rewrite the body of one page.
 *
 * @param string $content Post content.
 * @param array  $log     Collector.
 * @return string
 */
function linker_about_rewrite( string $content, array &$log ): string {
	$sizes = linker_about_sizes();

	// 1. Body images that still lack srcset.
	$content = preg_replace_callback(
		'~<img\b[^>]*>~i',
		static function ( array $m ) use ( $sizes, &$log ): string {
			$tag = $m[0];
			if ( str_contains( $tag, 'srcset=' ) ) {
				return $tag;
			}
			if ( ! preg_match( '~\bsrc="([^"]+)"~', $tag, $src ) ) {
				return $tag;
			}
			$file = basename( (string) parse_url( $src[1], PHP_URL_PATH ) );
			$stem = (string) preg_replace( '~\.[a-z]+$~', '', (string) preg_replace( '~-\d+x\d+(?=\.[a-z]+$)~', '', $file ) );
			if ( ! isset( $sizes[ $stem ] ) ) {
				return $tag;
			}
			$id = attachment_url_to_postid( $src[1] );
			if ( $id <= 0 ) {
				foreach ( array(
					'linker-residential-hybrid-from-linker' => 5548,
					'linker-outdoor-cabinets-from-linker'   => 5549,
					'linker-container-bess-from-linker'     => 5550,
					'linker-trusted-on-commercial-bess'     => 5552,
					'linker-trusted-on-microgrid-projects'  => 5553,
				) as $known_stem => $known_id ) {
					if ( $stem === $known_stem ) {
						$id = $known_id;
						break;
					}
				}
			}
			if ( $id <= 0 ) {
				$log[] = 'no attachment: ' . $file;
				return $tag;
			}
			$srcset = linker_about_srcset( $id, $src[1] );
			if ( '' === $srcset ) {
				$log[] = 'no variants: ' . $file;
				return $tag;
			}
			$add = ' srcset="' . esc_attr( $srcset ) . '" sizes="' . esc_attr( $sizes[ $stem ] ) . '"';
			if ( ! str_contains( $tag, 'loading=' ) ) {
				$add .= ' loading="lazy" decoding="async"';
			}
			$out = preg_replace( '~\s*/?>$~', $add . '$0', $tag, 1 );
			if ( is_string( $out ) && $out !== $tag ) {
				$log[] = 'srcset: ' . $file;
				return $out;
			}
			return $tag;
		},
		$content
	);

	// 2. The mobile-only photo layer must not fetch on desktop.
	$content = str_replace(
		"var photo = document.createElement('img');",
		"var photo = document.createElement('img'); photo.loading = 'lazy'; photo.decoding = 'async';",
		$content,
		$count_photo
	);
	if ( $count_photo > 0 ) {
		$log[] = 'lazy photo x' . $count_photo;
	}
	$content = str_replace(
		"var thumbnail = document.createElement('img');",
		"var thumbnail = document.createElement('img'); thumbnail.loading = 'lazy'; thumbnail.decoding = 'async';",
		$content,
		$count_thumb
	);
	if ( $count_thumb > 0 ) {
		$log[] = 'lazy thumbnail x' . $count_thumb;
	}

	return $content;
}

$ids = get_posts(
	array(
		'post_type'      => array( 'page', 'post' ),
		'post_status'    => 'publish',
		'posts_per_page' => -1,
		'fields'         => 'ids',
	)
);

foreach ( $ids as $id ) {
	$content = get_post_field( 'post_content', $id );
	if ( ! is_string( $content ) || ! str_contains( $content, 'mt-photo' ) ) {
		continue;
	}
	$log   = array();
	$next  = linker_about_rewrite( $content, $log );
	$delta = strlen( $next ) - strlen( $content );
	printf( "%d %s: %s (delta %+d)\n", $id, get_post_field( 'post_name', $id ), implode( ', ', $log ), $delta );
	if ( $apply && $next !== $content ) {
		wp_update_post( array( 'ID' => $id, 'post_content' => $next ) );
		clean_post_cache( $id );
	}
}
echo $apply ? "applied\n" : "dry run\n";
