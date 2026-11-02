<?php
/**
 * Append the reviewed EHA image note to twelve native product excerpts.
 *
 * WP-CLI eval-file <this-file> [apply|rollback]. Default: read-only preview.
 * Use the normal full database backup before apply; retain stdout as one receipt.
 * No images, product bodies, specifications or other translation units change.
 *
 * @package Linker\Commerce
 */

use Linker\I18n\Translation\Fields;
use Linker\I18n\Translation\HtmlTokenizer;
use Linker\I18n\Translation\Segmenter;
use Linker\I18n\Translation\State;

( static function ( array $args ): void {
	$action = $args[0] ?? 'preview';
	if ( ! defined( 'WP_CLI' ) || ! WP_CLI || ! in_array( $action, array( 'preview', 'apply', 'rollback' ), true ) ) {
		throw new RuntimeException( 'Run with WP-CLI: preview, apply or rollback.' );
	}
	// phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- Reviewed local data next to this CLI batch.
	$pairs  = json_decode( (string) file_get_contents( __DIR__ . '/eha-image-notes.json' ), true, 512, JSON_THROW_ON_ERROR );
	$from   = 'rollback' === $action ? 'after' : 'before';
	$to     = 'rollback' === $action ? 'before' : 'after';
	$state  = new State();
	$split  = new Segmenter( new HtmlTokenizer() );
	$read   = static function ( int $id ): WP_Post {
		$post = get_post( $id );
		if ( ! $post instanceof WP_Post ) {
			throw new RuntimeException( 'Product is missing.' );
		}
		return $post;
	};
	$hash   = static function ( int $id ) use ( $read ): string {
		$parts = array();
		foreach ( ( new Fields() )->of_post( $read( $id ) ) as $key => list( $value ) ) {
			$parts[] = $key . "\0" . $value;
		}
		return sha1( implode( "\1", $parts ) );
	};
	$before = array();
	foreach ( $pairs as $pair ) {
		foreach ( $pair as $row ) {
			$post = get_post( $row['id'] );
			if ( ! $post instanceof WP_Post || 'product' !== $post->post_type || get_post_meta( $post->ID, '_sku', true ) !== $row['sku'] || $post->post_excerpt !== $row[ $from ] ) {
				throw new RuntimeException( 'Reviewed product excerpt changed: ' . (int) $row['id'] );
			}
			$before[ $post->ID ] = $post->post_excerpt;
		}
		if ( (int) pll_get_post( $pair[0]['id'], 'de' ) !== $pair[1]['id'] ) {
			throw new RuntimeException( 'Reviewed product language pair changed.' );
		}
	}
	if ( 'preview' !== $action ) {
		global $wpdb;
		$wpdb->query( 'START TRANSACTION' );
		try {
			foreach ( $pairs as $pair ) {
				list( $en, $de ) = array_column( $pair, 'id' );
				$current         = $state->source_hash( 'post', $de ) === $hash( $en );
				$units           = $state->units( 'post', $de );
				foreach ( $pair as $row ) {
					$result = wp_update_post(
						wp_slash(
							array(
								'ID'           => $row['id'],
								'post_excerpt' => $row[ $to ],
							)
						),
						true,
						false
					);
					if ( is_wp_error( $result ) || $read( $row['id'] )->post_excerpt !== $row[ $to ] ) {
						throw new RuntimeException( 'Native product excerpt write failed.' );
					}
				}
				$units['post_excerpt'] = array(
					'src'      => $split->block_hashes( $pair[0][ $to ], true ),
					'out'      => $split->block_hashes( $pair[1][ $to ], true ),
					'conflict' => false,
				);
				$state->save( 'post', $de, $current ? $hash( $en ) : $state->source_hash( 'post', $de ), $units );
				update_post_meta( $en, '_linker_de_excerpt', wp_slash( $pair[1][ $to ] ) );
				update_post_meta( $en, '_linker_de_excerpt_sha', sha1( $pair[0][ $to ] ) );
			}
			$wpdb->query( 'COMMIT' );
		} catch ( Throwable $error ) {
			$wpdb->query( 'ROLLBACK' );
			throw $error;
		}
	}
	echo wp_json_encode(
		array(
			'action' => $action,
			'before' => $before,
			'after'  => array_map( static fn( array $row ): string => $read( $row['id'] )->post_excerpt, array_merge( ...$pairs ) ),
		)
	);
} )( $args ?? array() );
