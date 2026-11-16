<?php
/**
 * Give the outline back its missing levels on the ten marketing pages.
 *
 * Measured on production 2026-11-15: five English pages and their German twins
 * jump from h1 straight to h4 (and from h2 to h4), which a screen reader
 * announces as a missing level. The levels are hand-written in the stored
 * markup, and each page's own inline <style> names the element that carries
 * them, so a tag rename and the selectors that paint it move together here.
 *
 * Every replacement is exact and counted: a page whose content does not carry
 * the expected number of a substring is refused, unevaluated, before anything
 * is written. A second run is recognised by the page's *outline* — the forms
 * that must no longer appear — because counting the new tag cannot tell the
 * headings this script moved from the ones the page already had.
 *
 * Run: wp eval-file heading-levels.php            (report only)
 *      LINKER_APPLY=1 wp eval-file heading-levels.php   (write)
 *
 * @package Linker\Commerce
 */

defined( 'ABSPATH' ) || exit;

/**
 * A page's edit list.
 *
 * @param int $id Page id.
 * @return array<int, array{0: string, 1: string, 2: int, 3: string}>|null
 */
function linker_commerce_heading_edits( int $id ): ?array {
	$home    = array(
		// The four capability cards sit directly under the h1, before the
		// first h2 (measured 2026-11-15: offsets 34255-35934 against the
		// first h2 at 36906), so their level is h2. The scene card at the
		// foot of the page sits under h2.scene-title and is an h3.
		array( '<h4>Complete Storage Packages</h4>', '<h2>Complete Storage Packages</h2>', 1, 'trust tag' ),
		array( '<h4>Dedicated Trade Supply</h4>', '<h2>Dedicated Trade Supply</h2>', 1, 'trust tag' ),
		array( '<h4>Local Stock &amp; Support</h4>', '<h2>Local Stock &amp; Support</h2>', 1, 'trust tag' ),
		array( '<h4>System Compatibility</h4>', '<h2>System Compatibility</h2>', 1, 'trust tag' ),
		array( '<h4>Start with the products you need.</h4>', '<h3>Start with the products you need.</h3>', 1, 'scene tag' ),
		array( '.home-trust-item h4', '.home-trust-item h2', 3, 'trust size and face' ),
		array( '#home-a [data-capability-card] h4', '#home-a [data-capability-card] h2', 2, 'trust card grid' ),
		array( ':is(#home-a,#about-journal) .scene-card-body h4', ':is(#home-a,#about-journal) .scene-card-body h3', 1, 'scene face' ),
		array( '#home-a .scene-card-body h4{font-size:19px}', '#home-a .scene-card-body h3{font-size:19px}', 1, 'scene size at 760' ),
	);
	$home_de = array(
		array( '<h4>Komplette Speicherpakete</h4>', '<h2>Komplette Speicherpakete</h2>', 1, 'trust tag' ),
		array( '<h4>Versorgung speziell für den Fachhandel</h4>', '<h2>Versorgung speziell für den Fachhandel</h2>', 1, 'trust tag' ),
		array( '<h4>Lokaler Lagerbestand &amp; Support</h4>', '<h2>Lokaler Lagerbestand &amp; Support</h2>', 1, 'trust tag' ),
		array( '<h4>Systemkompatibilität</h4>', '<h2>Systemkompatibilität</h2>', 1, 'trust tag' ),
		array( '<h4>Starten Sie mit den Produkten, die Sie brauchen.</h4>', '<h3>Starten Sie mit den Produkten, die Sie brauchen.</h3>', 1, 'scene tag' ),
		array( '.home-trust-item h4', '.home-trust-item h2', 3, 'trust size and face' ),
		array( '#home-a [data-capability-card] h4', '#home-a [data-capability-card] h2', 2, 'trust card grid' ),
		array( ':is(#home-a,#about-journal) .scene-card-body h4', ':is(#home-a,#about-journal) .scene-card-body h3', 1, 'scene face' ),
		array( '#home-a .scene-card-body h4{font-size:19px}', '#home-a .scene-card-body h3{font-size:19px}', 1, 'scene size at 760' ),
	);
	// The arena headings are the hub's three scale panels: under the h1 with no
	// h2 between them, so their level is h2. The class keeps painting them.
	$hub = array(
		array( '<h3 class="lk-arena-h3">', '<h2 class="lk-arena-h3">', 3, 'arena tag' ),
	);
	// The comparison blocks sit under an h2, so their level is h3.
	$residential = array(
		array( '<h4>', '<h3>', 4, 'comp tag' ),
		array( '</h4>', '</h3>', 4, 'comp close' ),
		array( '#tv-rs-page-v1 .lk-comp-body h4', '#tv-rs-page-v1 .lk-comp-body h3', 3, 'comp body size' ),
		array( '#tv-rs-page-v1 .lk-comp-callout-panel h4', '#tv-rs-page-v1 .lk-comp-callout-panel h3', 1, 'callout size' ),
		// The page's face rule for the moved headings: without moving it too the
		// callout falls through to the page's generic `h3` and grows from 20px to
		// 32px, which is what the first pass shipped (measured 2026-11-15 on
		// /de/loesung/heimspeicher/). The comparison blocks keep their own 18px,
		// which is more specific.
		array( '#tv-rs-page-v1 h4{font-size:20px}', '#tv-rs-page-v1 .lk-comp-callout-panel h3{font-size:20px}', 1, 'callout face' ),
	);
	$commercial = array(
		array( '<h4>', '<h3>', 4, 'comp tag' ),
		array( '</h4>', '</h3>', 4, 'comp close' ),
		array( '#tv-cs-page-v1 .lk-comp-body h4', '#tv-cs-page-v1 .lk-comp-body h3', 2, 'comp body size' ),
		array( '#tv-cs-page-v1 .lk-comp-callout-panel h4', '#tv-cs-page-v1 .lk-comp-callout-panel h3', 1, 'callout size' ),
	);
	$utility    = array(
		array( '<h4>', '<h3>', 4, 'feature tag' ),
		array( '</h4>', '</h3>', 4, 'feature close' ),
		array( '#tv-utility-page-v1 .us-engineering-feature h4', '#tv-utility-page-v1 .us-engineering-feature h3', 2, 'feature size' ),
	);
	$map        = array(
		13   => $home,
		6913 => $home_de,
		746  => $hub,
		6871 => $hub,
		749  => $residential,
		6923 => $residential,
		792  => $commercial,
		6921 => $commercial,
		1755 => $utility,
		6917 => $utility,
	);
	return $map[ $id ] ?? null;
}

/**
 * The forms that must no longer appear once a page's levels are corrected.
 *
 * These are the outline facts the edit list produces, and they are what a
 * second run checks: after the rename the page carries no h4 at all (its cards
 * are h2 or h3), and the hub's arena headings carry their class on h2.
 *
 * @param int $id Page id.
 * @return array<int, string>
 */
function linker_commerce_heading_absent( int $id ): array {
	$hub = array( '<h3 class="lk-arena-h3">' );
	return match ( $id ) {
		746, 6871 => $hub,
		default   => array( '<h4' ),
	};
}

( static function (): void {
	$apply = '1' === getenv( 'LINKER_APPLY' );
	$ids   = array( 13, 6913, 746, 6871, 749, 6923, 792, 6921, 1755, 6917 );
	$total = 0;

	foreach ( $ids as $id ) {
		$edits = linker_commerce_heading_edits( $id );
		$post  = get_post( $id );
		if ( ! $edits || ! $post instanceof WP_Post ) {
			throw new RuntimeException( esc_html( "page {$id}: no edit list or no post" ) );
		}
		$content = $post->post_content;
		$next    = $content;
		$lines   = array();
		foreach ( $edits as [ $old, $new, $count, $why ] ) {
			$before = substr_count( $next, $old );
			if ( 0 === $before ) {
				// Nothing left of the old form: this page is past this edit. The
				// outline check below proves it, rather than the new tag's count,
				// which cannot tell moved headings from the ones already there.
				$lines[] = sprintf( '  %-22s already moved', $why );
				continue;
			}
			if ( $before !== $count ) {
				throw new RuntimeException(
					esc_html(
						sprintf(
							'page %d (%s): %s needs %d of the old form, found %d',
							$id,
							$post->post_name,
							$why,
							$count,
							$before
						)
					)
				);
			}
			$next    = str_replace( $old, $new, $next );
			$lines[] = sprintf( '  %-22s %d', $why, $count );
		}
		foreach ( linker_commerce_heading_absent( $id ) as $absent ) {
			$left = substr_count( $next, $absent );
			if ( 0 !== $left ) {
				throw new RuntimeException(
					esc_html( sprintf( 'page %d (%s): %d of %s survive the edit', $id, $post->post_name, $left, $absent ) )
				);
			}
		}
		$changed = $next !== $content;
		WP_CLI::log( sprintf( '%d %s: %s', $id, $post->post_name, $changed ? 'changes' : 'already correct' ) );
		foreach ( $lines as $line ) {
			WP_CLI::log( $line );
		}
		if ( ! $changed ) {
			continue;
		}
		++$total;
		if ( $apply ) {
			$result = wp_update_post(
				array(
					'ID'           => $id,
					'post_content' => $next,
				),
				true
			);
			if ( is_wp_error( $result ) ) {
				throw new RuntimeException( esc_html( "page {$id}: " . $result->get_error_message() ) );
			}
			clean_post_cache( $id );
		}
	}

	WP_CLI::log( sprintf( '%s: %d page(s) %s', $apply ? 'applied' : 'dry run', $total, $apply ? 'written' : 'would change' ) );
} )();
