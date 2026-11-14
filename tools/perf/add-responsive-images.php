<?php
/**
 * Give every hand-written <img> the responsive attributes WordPress omitted.
 *
 * Run with: LINKER_IMG_APPLY=1 wp eval-file add-responsive-images.php
 * Without the variable it reports only.
 *
 * Why this exists: the marketing pages carry plain <img src> tags with width and
 * height but no srcset and no sizes, so the browser takes the original file for
 * a box a third to a tenth of its size. Measured on production 2026-11-14, the
 * homepage transferred 4.31 MB of images and now transfers 0.80 MB.
 *
 * The sizes values come from `tools/perf/measure-image-boxes.mjs`, which records
 * each image's rendered width at 390/600/768/1024/1280/1440 CSS px on the live
 * page. Nothing here is guessed: a sizes rule states the widest box that image
 * actually takes inside that range, plus 8 px of rasterisation headroom.
 *
 * Only `srcset` (built from the attachment's stored sizes) and `sizes` are
 * appended. `src`, `alt`, `width`, `height`, class and every other byte of the
 * content stay as written.
 *
 * @package Linker\Commerce
 */

/**
 * Measured display width per file, as a sizes attribute.
 *
 * Kept in step with the generator that read the measurement JSON; a file absent
 * here is left untouched rather than given an invented width.
 */
function linker_sizes_table(): array {
	return array(
		'linker-authorised-supply-from-germany'          => '(max-width: 600px) 175px, 231px',
		'linker-bess-layout-for-planning-de-poster'      => '(max-width: 600px) 608px, (max-width: 1024px) 728px, 668px',
		'linker-bess-layout-for-planning-en-poster'      => '(max-width: 600px) 608px, (max-width: 1024px) 728px, 736px',
		'linker-bess-sizing-for-the-site-de-poster'      => '(max-width: 1024px) 477px, 656px',
		'linker-bess-sizing-for-the-site-en-poster'      => '(max-width: 1024px) 477px, 656px',
		'linker-combinations-that-fit-the-site'          => '(max-width: 600px) 560px, (max-width: 1024px) 421px, 579px',
		'linker-genie-lookup-for-installers-de-poster'   => '(max-width: 1024px) 589px, 768px',
		'linker-genie-lookup-for-installers-en-poster'   => '(max-width: 1024px) 589px, 768px',
		'linker-german-technical-and-supply-base'        => '(max-width: 600px) 580px, (max-width: 1024px) 314px, 413px',
		'linker-german-technical-desk'                   => '(max-width: 600px) 580px, (max-width: 1024px) 736px, 517px',
		'linker-grid-certificates-for-registration'      => '(max-width: 600px) 580px, (max-width: 1024px) 465px, 586px',
		'linker-hybrid-storage-for-the-home'             => '(max-width: 600px) 580px, (max-width: 1024px) 736px, 553px',
		'linker-pinouts-for-first-visit'                 => '(max-width: 600px) 580px, (max-width: 1024px) 465px, 586px',
		'linker-storage-built-around-real-projects-1'    => '(max-width: 768px) 100vw, (max-width: 1024px) 393px, 505px',
		'linker-storage-for-business-sites'              => '(max-width: 600px) 580px, (max-width: 1024px) 736px, 553px',
		'linker-technical-answers-when-you-need-them'    => '(max-width: 600px) 580px, (max-width: 1024px) 736px, 553px',
		'linker-the-order-arrives-together'              => '(max-width: 600px) 580px, (max-width: 1024px) 465px, 586px',
		'linker-the-project-takes-shape-on-linker-1'     => '(max-width: 600px) 580px, (max-width: 1024px) 736px, 953px',
		'linker-the-trade-partner-portal-scaled'         => '(max-width: 600px) 175px, 231px',
		'linker-inverter-battery-protocol-desk'          => '(max-width: 600px) 175px, 231px',
	);
}

/**
 * The attachment whose original file matches this basename.
 *
 * @param string $stem Basename without a size suffix or extension.
 * @return int Attachment id, or 0.
 */
function linker_img_attachment( string $stem ): int {
	global $wpdb;
	$like = '%' . $wpdb->esc_like( $stem ) . '%';
	$ids  = $wpdb->get_col(
		$wpdb->prepare(
			"SELECT post_id FROM {$wpdb->postmeta} WHERE meta_key='_wp_attached_file' AND meta_value LIKE %s LIMIT 5",
			$like
		)
	);
	foreach ( $ids as $id ) {
		$id       = (int) $id;
		$attached = (string) get_post_meta( $id, '_wp_attached_file', true );
		$base     = preg_replace( '~-\d+x\d+(?=\.[a-z]+$)~', '', basename( $attached ) );
		if ( preg_replace( '~\.[a-z]+$~', '', (string) $base ) === $stem ) {
			return $id;
		}
	}
	return 0;
}

/**
 * Build a srcset from the attachment metadata WordPress already stored.
 *
 * @param int    $attachment_id Attachment id.
 * @param string $full_url      Original file URL.
 * @return string Empty when the attachment has no usable variants.
 */
function linker_img_srcset( int $attachment_id, string $full_url ): string {
	$meta = wp_get_attachment_metadata( $attachment_id );
	if ( ! is_array( $meta ) || empty( $meta['sizes'] ) ) {
		return '';
	}
	$base = trailingslashit( dirname( $full_url ) );
	$rows = array();
	if ( ! empty( $meta['width'] ) ) {
		$rows[] = array( (int) $meta['width'], $full_url );
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
	foreach ( $rows as list( $width, $url ) ) {
		$parts[] = $url . ' ' . $width . 'w';
	}
	return implode( ', ', $parts );
}

/**
 * Append srcset and sizes to every eligible image in the content.
 *
 * @param string $content Post content.
 * @return array{content:string,changed:int,skipped:list<string>}
 */
function linker_img_rewrite( string $content ): array {
	$sizes   = linker_sizes_table();
	$changed = 0;
	$skipped = array();
	$content = preg_replace_callback(
		'~<img\b[^>]*>~i',
		static function ( array $match ) use ( $sizes, &$changed, &$skipped ): string {
			$tag = $match[0];
			if ( ! preg_match( '~\bsrc="([^"]+)"~', $tag, $src ) ) {
				return $tag;
			}
			if ( str_contains( $tag, 'srcset=' ) ) {
				return $tag;
			}
			$file = basename( (string) parse_url( $src[1], PHP_URL_PATH ) );
			$stem = (string) preg_replace( '~\.[a-z]+$~', '', (string) preg_replace( '~-\d+x\d+(?=\.[a-z]+$)~', '', $file ) );
			$rule = null;
			foreach ( $sizes as $candidate => $value ) {
				if ( $stem === $candidate || 0 === strpos( $stem, $candidate . '-' ) ) {
					$rule = $value;
					$key  = $candidate;
					break;
				}
			}
			if ( null === $rule ) {
				return $tag;
			}
			$attachment_id = attachment_url_to_postid( $src[1] );
			if ( $attachment_id <= 0 ) {
				$attachment_id = linker_img_attachment( (string) $stem );
			}
			if ( $attachment_id <= 0 ) {
				$skipped[] = 'no attachment: ' . $file;
				return $tag;
			}
			$srcset = linker_img_srcset( $attachment_id, $src[1] );
			if ( '' === $srcset ) {
				$skipped[] = 'no variants: ' . $file;
				return $tag;
			}
			$add = ' srcset="' . esc_attr( $srcset ) . '" sizes="' . esc_attr( $rule ) . '"';
			$new = preg_replace( '~\s*/?>$~', $add . '$0', $tag, 1 );
			if ( ! is_string( $new ) || $new === $tag ) {
				return $tag;
			}
			++$changed;
			return $new;
		},
		$content
	);
	return array( 'content' => (string) $content, 'changed' => $changed, 'skipped' => $skipped );
}

// ---------------------------------------------------------------- execution --

$apply = '1' === getenv( 'LINKER_IMG_APPLY' );
$ids   = get_posts(
	array(
		'post_type'      => array( 'page', 'post' ),
		'post_status'    => 'publish',
		'posts_per_page' => -1,
		'fields'         => 'ids',
	)
);
$total_changed = 0;
$total_pages   = 0;
foreach ( $ids as $post_id ) {
	$post = get_post( (int) $post_id );
	if ( ! $post instanceof WP_Post || ! str_contains( $post->post_content, '<img' ) ) {
		continue;
	}
	$result = linker_img_rewrite( $post->post_content );
	if ( $result['changed'] > 0 ) {
		++$total_pages;
		$total_changed += $result['changed'];
		echo sprintf( "%d %s: %d images\n", $post->ID, $post->post_name, $result['changed'] );
		foreach ( array_slice( $result['skipped'], 0, 3 ) as $line ) {
			echo '    skipped ' . $line . "\n";
		}
		if ( $apply ) {
			global $wpdb;
			$wpdb->update( $wpdb->posts, array( 'post_content' => $result['content'] ), array( 'ID' => $post->ID ) );
			clean_post_cache( $post->ID );
		}
	}
}
echo sprintf( "\n%s: %d images across %d pages\n", $apply ? 'applied' : 'dry run', $total_changed, $total_pages );
