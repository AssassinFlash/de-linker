<?php
/**
 * Refresh published product FAQ wording using the reviewed vocabulary map.
 *
 * WP-CLI: eval-file wave3-product-faq.php plan|apply <wave3-vocabulary.json path>.
 * Keeps the current FAQ order, quantities, citations and published PDF bindings.
 *
 * @package Linker\Commerce
 */

use Linker\Commerce\Products\Faqs;
use Linker\Commerce\Products\Publication;
use Linker\Commerce\Products\Publication\EvidenceBindings;

( static function ( array $args ): void {
	global $wpdb;
	list( $mode, $file ) = $args;
	if ( ! in_array( $mode, array( 'plan', 'apply' ), true ) ) {
		WP_CLI::error( 'Expected plan or apply.' );
	}
	$input = file_get_contents( $file ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- Local release input.
	if ( false === $input ) {
		WP_CLI::error( 'Could not read the reviewed vocabulary file.' );
	}
	$copy        = json_decode( $input, true, 512, JSON_THROW_ON_ERROR )['product_faq_copy'];
	$changes     = array();
	$product_ids = $wpdb->get_col( "SELECT ID FROM {$wpdb->posts} WHERE post_type='product' AND post_status='publish' ORDER BY ID" );
	foreach ( $product_ids as $id ) {
		$id = (int) $id;
		if ( 'en' !== pll_get_post_language( $id ) ) {
			continue;
		}
		$old = get_post_meta( $id, Faqs::META_KEY, true );
		if ( ! $old ) {
			continue;
		}
		$rows     = json_decode( $old, true, 512, JSON_THROW_ON_ERROR );
		$bindings = get_post_meta( $id, EvidenceBindings::FAQ_META_KEY, true );
		$expected = $bindings;
		$edited   = 0;
		foreach ( $rows as &$row ) {
			$original = $row;
			foreach ( array( 'question', 'answer', 'question_de', 'answer_de' ) as $key ) {
				if ( isset( $row[ $key ] ) ) {
					$row[ $key ] = strtr( $row[ $key ], $copy );
				}
			}
			if ( $original === $row ) {
				continue;
			}
			++$edited;
			$from = Publication::figure_revision( $original );
			$to   = Publication::figure_revision( $row );
			if ( isset( $bindings[ $from ] ) ) {
				unset( $expected[ $from ] );
				$expected[ $to ] = array_merge( $bindings[ $from ], array( 'figure_revision' => $to ) );
			}
		}
		unset( $row );
		if ( ! $edited ) {
			continue;
		}
		$twin = (int) pll_get_post( $id, 'de' );
		if ( ! $twin || get_post_meta( $twin, Faqs::META_KEY, true ) !== $old ) {
			throw new RuntimeException( esc_html( "Review the bilingual FAQ pair for product $id." ) );
		}
		$changes[ $id ] = $edited;
		if ( 'apply' === $mode ) {
			$new = Faqs::encode( $rows );
			$wpdb->query( 'START TRANSACTION' );
			try {
				foreach ( array( $id, $twin ) as $target ) {
					if ( ! update_post_meta( $target, Faqs::META_KEY, wp_slash( $new ), $old ) || get_post_meta( $target, Faqs::META_KEY, true ) !== $new ) {
						throw new RuntimeException( "FAQ changed while updating product $target." );
					}
				}
				$actual = get_post_meta( $id, EvidenceBindings::FAQ_META_KEY, true );
				if ( is_array( $actual ) && is_array( $expected ) ) {
					ksort( $actual );
					ksort( $expected );
				}
				if ( $actual !== $expected ) {
					throw new RuntimeException( "The source documents for product $id changed." );
				}
				$wpdb->query( 'COMMIT' );
			} catch ( Throwable $error ) {
				$wpdb->query( 'ROLLBACK' );
				clean_post_cache( $id );
				clean_post_cache( $twin );
				throw $error;
			}
		}
	}
	WP_CLI::log(
		wp_json_encode(
			array(
				'mode'          => $mode,
				'product_pairs' => count( $changes ),
				'faq_rows'      => array_sum( $changes ),
				'changes'       => $changes,
			)
		)
	);
} )( $args ?? array() );
