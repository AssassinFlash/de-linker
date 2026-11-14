<?php
/**
 * Add the responsive attributes the hand-written homepage images never had.
 *
 * Run with: wp eval-file add-srcset.php [--apply]
 *
 * The homepage markup was authored as plain <img src> tags, so WordPress never
 * printed a srcset or a sizes value for them. The browser therefore downloads
 * the full original (134-387 KB each) to fill a 59-693 px box, while 300-1536 px
 * variants of the same file already exist on disk (17-223 KB).
 *
 * The sizes below are not guesses: each one is the width measured in the live
 * page at 390, 600, 768, 1024, 1280 and 1440 CSS px, rounded up to a stable
 * upper bound for the breakpoint it applies to.
 *
 * @package Linker\Commerce
 */

const TARGET_POSTS = array( 13, 6913 );

/**
 * Display width per image at the breakpoints the page actually uses.
 *
 * Keys are attachment basenames. Each entry is the CSS width the image takes at
 * phone, tablet and desktop, from the measurement pass; `sizes` states the upper
 * bound of each range so the browser never picks a variant smaller than the box.
 */
const IMAGE_SIZES = array(
	// 390 -> 217, 600 -> 353, 768 -> 434, 1024 -> 317, 1280 -> 408, 1440 -> 420.
	'linker-source-solar-and-storage-in-one-place-1' => '(max-width: 768px) 100vw, (max-width: 1024px) 45vw, 460px',
	// 59 / 95 / 117 / 93 / 120 / 124.
	'linker-check-what-works-together-1'             => '(max-width: 768px) 25vw, 140px',
	'linker-trade-support-from-germany-1'            => '(max-width: 768px) 25vw, 140px',
	// 354 / 564 / 688 / 414 / 527 / 545.
	'linker-residential-goodwe-esa-all-in-one'       => '(max-width: 768px) 100vw, (max-width: 1024px) 45vw, 580px',
	// 354 / 564 / 688 / 528 / 671 / 693.
	'linker-commercial-storage-for-contractors-1'    => '(max-width: 768px) 100vw, (max-width: 1024px) 55vw, 720px',
	// 306 / 516 / 363 / 502 / 638 / 659.
	'linker-find-the-system-you-need-1'              => '(max-width: 768px) 90vw, (max-width: 1024px) 55vw, 700px',
	// 354 / 226 / 287 / 298 / 383 / 397.
	'linker-when-demand-gets-bigger'                 => '(max-width: 600px) 100vw, (max-width: 1024px) 35vw, 420px',
	// Full-bleed band: 390 / 600 / 768 / 1024 / 1280 / 1440.
	'linker-utility-scale-bess'                      => '100vw',
	// 91 at <=768, 120 above.
	'linker-logo-wordmark'                           => '(max-width: 768px) 95px, 125px',
);

/**
 * Build a srcset from the attachment metadata WordPress already stored.
 *
 * @param int    $attachment_id Attachment id.
 * @param string $full_url      Original file URL.
 * @return array{srcset:string,sizes:string}|null
 */
function linker_variants( int $attachment_id, string $full_url ): ?array {
	$meta = wp_get_attachment_metadata( $attachment_id );
	if ( ! is_array( $meta ) || empty( $meta['sizes'] ) ) {
		return null;
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
		return null;
	}
	usort( $rows, static fn( array $a, array $b ): int => $a[0] <=> $b[0] );
	$parts = array();
	foreach ( $rows as list( $width, $url ) ) {
		$parts[] = $url . ' ' . $width . 'w';
	}
	return array( 'srcset' => implode( ', ', $parts ) );
}

/**
 * Find the attachment whose original file matches this basename.
 *
 * @param string $stem Basename without a size suffix.
 * @return int Attachment id, or 0.
 */
function linker_attachment_by_file( string $stem ): int {
	global $wpdb;
	$like = '%' . $wpdb->esc_like( $stem ) . '%';
	$ids  = $wpdb->get_col(
		$wpdb->prepare(
			"SELECT post_id FROM {$wpdb->postmeta} WHERE meta_key='_wp_attached_file' AND meta_value LIKE %s LIMIT 5",
			$like
		)
	);
	foreach ( $ids as $id ) {
		$id = (int) $id;
		$attached = (string) get_post_meta( $id, '_wp_attached_file', true );
		$base = preg_replace( '~-\d+x\d+(?=\.[a-z]+$)~', '', basename( $attached ) );
		if ( preg_replace( '~\.[a-z]+$~', '', (string) $base ) === $stem ) {
			return $id;
		}
	}
	return 0;
}

/**
 * Rewrite every targeted <img> in the given content.
 *
 * @param string $content Post content.
 * @param bool   $apply   Write changes when true; report only otherwise.
 * @return array{content:string,changed:int,log:list<string>}
 */
function linker_rewrite( string $content, bool $apply ): array {
	$changed = 0;
	$log     = array();
	$content = preg_replace_callback(
		'~<img\b[^>]*>~i',
		static function ( array $match ) use ( &$changed, &$log ): string {
			$tag = $match[0];
			if ( ! preg_match( '~\bsrc="([^"]+)"~', $tag, $src ) ) {
				return $tag;
			}
			$file = basename( (string) parse_url( $src[1], PHP_URL_PATH ) );
			$stem = preg_replace( '~-\d+x\d+(?=\.[a-z]+$)~', '', $file );
			$stem = preg_replace( '~\.[a-z]+$~', '', (string) $stem );
			$key  = null;
			foreach ( array_keys( IMAGE_SIZES ) as $candidate ) {
				if ( 0 === strpos( (string) $stem, $candidate ) ) {
					$key = $candidate;
					break;
				}
			}
			if ( null === $key || ! empty( $match[0] ) && str_contains( $tag, 'srcset=' ) ) {
				return $tag;
			}
			$attachment_id = attachment_url_to_postid( $src[1] );
			if ( $attachment_id <= 0 ) {
				// The stored guid often names a different host or size; match the
				// attachment by the original file it was created from instead.
				$attachment_id = linker_attachment_by_file( $stem );
			}
			if ( $attachment_id <= 0 ) {
				$log[] = 'no attachment id: ' . $file;
				return $tag;
			}
			$variants = linker_variants( $attachment_id, $src[1] );
			if ( null === $variants ) {
				$log[] = 'no variants: ' . $file;
				return $tag;
			}
			$insert = ' srcset="' . esc_attr( $variants['srcset'] ) . '" sizes="' . esc_attr( IMAGE_SIZES[ $key ] ) . '"';
			$new    = preg_replace( '~\s*/?>$~', $insert . '$0', $tag, 1 );
			if ( ! is_string( $new ) || $new === $tag ) {
				return $tag;
			}
			++$changed;
			$log[] = sprintf(
				'%s -> %d variants',
				$file,
				substr_count( $variants['srcset'], 'w,' ) + 1
			);
			return $new;
		},
		$content
	);
	return array( 'content' => (string) $content, 'changed' => $changed, 'log' => $log );
}

/*
 * Second pass: three cards already carry a srcset but declare
 * sizes="(max-width: 600px) 120vw, 2400px" while they render at 354 px on a
 * phone and 370 px on a desktop card. The declared width sends the browser to
 * the 2400w candidate. Measured: 354 / 564 / 296 / 278 / 358 / 370 at
 * 390/600/768/1024/1280/1440.
 */
const CARD_SIZES = '(max-width: 600px) 100vw, (max-width: 768px) 45vw, 380px';
const CARD_FILES = array(
	'linker-installers-buy-through-linker',
	'linker-contractors-buy-through-linker',
	'linker-grid-projects-buy-through-linker',
);

/**
 * Replace the declared width on the three card images.
 *
 * @param string $content Post content.
 * @return array{content:string,changed:int}
 */
function linker_fix_card_sizes( string $content ): array {
	$changed = 0;
	$content = preg_replace_callback(
		'~<img\b[^>]*>~i',
		static function ( array $match ) use ( &$changed ): string {
			$tag = $match[0];
			if ( ! preg_match( '~\bsrc="([^"]+)"~', $tag, $src ) ) {
				return $tag;
			}
			$stem = preg_replace( '~\.[a-z]+$~', '', basename( (string) parse_url( $src[1], PHP_URL_PATH ) ) );
			$hit  = false;
			foreach ( CARD_FILES as $candidate ) {
				if ( $stem === $candidate || 0 === strpos( (string) $stem, $candidate . '-' ) ) {
					$hit = true;
					break;
				}
			}
			if ( ! $hit || ! str_contains( $tag, 'srcset=' ) ) {
				return $tag;
			}
			$new = preg_replace( '~sizes="[^"]*"~', 'sizes="' . esc_attr( CARD_SIZES ) . '"', $tag, 1 );
			if ( ! is_string( $new ) || $new === $tag ) {
				return $tag;
			}
			++$changed;
			return $new;
		},
		$content
	);
	return array( 'content' => (string) $content, 'changed' => $changed );
}

$apply = '1' === getenv( 'LINKER_SRCSET_APPLY' );
foreach ( TARGET_POSTS as $post_id ) {
	$post = get_post( $post_id );
	if ( ! $post instanceof WP_Post ) {
		echo "post {$post_id}: missing\n";
		continue;
	}
	$result = linker_rewrite( $post->post_content, $apply );
	$cards  = linker_fix_card_sizes( $result['content'] );
	$result['content'] = $cards['content'];
	$result['changed'] += $cards['changed'];
	if ( $cards['changed'] > 0 ) {
		$result['log'][] = sprintf( '%d card images given their measured sizes', $cards['changed'] );
	}
	echo sprintf( "post %d (%s): %d images rewritten\n", $post_id, $post->post_name, $result['changed'] );
	foreach ( $result['log'] as $line ) {
		echo '  ' . $line . "\n";
	}
	if ( ! $apply && $result['changed'] > 0 ) {
		if ( preg_match( '~<img\b[^>]*srcset="[^"]*"[^>]*>~i', $result['content'], $m ) ) {
			echo "  PREVIEW: " . substr( $m[0], 0, 420 ) . "\n";
		}
	}
	if ( $apply && $result['changed'] > 0 ) {
		global $wpdb;
		$wpdb->update( $wpdb->posts, array( 'post_content' => $result['content'] ), array( 'ID' => $post_id ) );
		clean_post_cache( $post_id );
		echo "  written\n";
	}
}
