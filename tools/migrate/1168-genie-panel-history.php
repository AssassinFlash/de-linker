<?php
/**
 * Correct the published panel label in assistant-authored historical reports.
 *
 * Run through WP-CLI with plan or apply. Each private conversation retains
 * its original meta alongside the corrected transcript. Customer messages,
 * uploaded-label readings, order records and delivered emails stay intact.
 *
 * @package Linker\Commerce
 */

use Linker\Tools\Genie\Conversations;
use Linker\Tools\Genie\Thread;
use Linker\Tools\Protection\Resources;

( static function ( array $args ): void {
	if ( ! in_array( $args, array( array( 'plan' ), array( 'apply' ) ), true ) ) {
		WP_CLI::error( 'Use plan or apply.' );
	}
	global $wpdb;
	$apply    = 'apply' === $args[0];
	$original = 'Trina Solar TSM-460NEG9R.28';
	$archive  = '_linker_genie_panel_history_1168';
	$thread   = new Thread();
	$ids      = $wpdb->get_col(
		$wpdb->prepare(
			"SELECT DISTINCT m.post_id FROM {$wpdb->postmeta} m JOIN {$wpdb->posts} p ON p.ID = m.post_id WHERE p.post_type = %s AND m.meta_key IN (%s,%s) AND m.meta_value LIKE %s",
			Conversations::POST_TYPE,
			Thread::MESSAGES,
			Thread::STREAM,
			'%' . $wpdb->esc_like( $original ) . '%'
		)
	);
	if ( '' !== $wpdb->last_error ) {
		WP_CLI::error( 'Could not read the stored transcripts.' );
	}
	$counts = array(
		'conversations'    => 0,
		'assistant_labels' => 0,
	);
	foreach ( array_map( 'intval', $ids ) as $id ) {
		$lock = $apply ? $thread->lock_name( $id ) : '';
		if ( $apply && '1' !== (string) $wpdb->get_var( $wpdb->prepare( 'SELECT GET_LOCK(%s, 0)', $lock ) ) ) {
			WP_CLI::error( 'A conversation is in use. Re-run after the turn completes.' );
		}
		try {
			wp_cache_delete( $id, 'post_meta' );
			$read     = $thread->read( $id );
			$events   = explode( "\n\n", $read['stream'] );
			$language = '';
			foreach ( $events as $event ) {
				if ( preg_match( '/^event: meta\r?\ndata: ([^\r\n]+)/m', $event, $match ) ) {
					$language = json_decode( $match[1], true )['language'] ?? '';
					break;
				}
			}
			// Only an explicitly identified conversation language can supply the label.
			$labels           = array(
				'en' => 'PV module used for the saved layout',
				'de' => 'PV-Modul der gespeicherten Auslegung',
			);
			$changed          = array();
			$labels_in_thread = 0;
			$messages         = $read['messages'];
			$products         = get_post_meta( $id, Thread::PRODUCTS, true );
			$cards            = $products;
			foreach ( $messages as &$message ) {
				if ( 'assistant' !== ( $message['role'] ?? '' ) || ! str_contains( (string) ( $message['content'] ?? '' ), $original ) ) {
					continue;
				}
				if ( ! isset( $labels[ $language ] ) ) {
					throw new RuntimeException( 'Review the language of a matched assistant answer.' );
				}
				$old                = $message['content'];
				$message['content'] = str_replace( $original, $labels[ $language ], $old, $n );
				$labels_in_thread  += $n;
				$key                = sha1( $old );
				if ( is_array( $cards ) && isset( $cards[ $key ] ) ) {
					$cards[ sha1( $message['content'] ) ] = $cards[ $key ];
					unset( $cards[ $key ] );
				}
			}
			unset( $message );
			foreach ( $events as &$event ) {
				if ( ! str_contains( $event, $original ) || ! preg_match( '/^event: block\r?\ndata: ([^\r\n]+)/m', $event, $match ) ) {
					continue;
				}
				$block = json_decode( $match[1], true );
				if ( 'text' !== ( $block['type'] ?? '' ) || ! str_contains( (string) ( $block['text'] ?? '' ), $original ) ) {
					continue;
				}
				if ( ! isset( $labels[ $language ] ) ) {
					throw new RuntimeException( 'Review the language of a matched assistant answer.' );
				}
				$block['text']     = str_replace( $original, $labels[ $language ], $block['text'], $n );
				$labels_in_thread += $n;
				$event             = str_replace( $match[1], (string) wp_json_encode( $block, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE ), $event );
			}
			unset( $event );
			if ( ! $labels_in_thread ) {
				continue;
			}
			if ( 'private' !== get_post_status( $id ) || metadata_exists( 'post', $id, $archive ) ) {
				throw new RuntimeException( 'Review the owner or previous correction of a matched conversation.' );
			}
			if ( isset( $read['operation_id'], $read['operation_fingerprint'] ) && Resources::completed_genie_operation( $read['operation_id'], $read['operation_fingerprint'] ) ) {
				throw new RuntimeException( 'The original turn still has a live replay receipt.' );
			}
			$next = array(
				Thread::MESSAGES   => $messages,
				Thread::STREAM     => implode( "\n\n", $events ),
				Thread::PRODUCTS   => $cards,
				Thread::COMPLETION => array(),
			);
			foreach ( $next as $key => $value ) {
				$old = get_post_meta( $id, $key, true );
				if ( $old !== $value ) {
					$changed[ $key ] = $old;
				}
			}
			++$counts['conversations'];
			$counts['assistant_labels'] += $labels_in_thread;
			if ( ! $apply ) {
				continue;
			}
			if ( false === $wpdb->query( 'START TRANSACTION' ) ) {
				throw new RuntimeException( 'Could not start the conversation correction.' );
			}
			try {
				if ( ! add_post_meta( $id, $archive, wp_slash( $changed ), true ) ) {
					throw new RuntimeException( 'Could not retain the private original.' );
				}
				foreach ( array_keys( $changed ) as $key ) {
					if ( false === update_post_meta( $id, $key, wp_slash( $next[ $key ] ) ) ) {
						throw new RuntimeException( 'Could not update the conversation.' );
					}
				}
				if ( false === $wpdb->query( 'COMMIT' ) ) {
					throw new RuntimeException( 'Could not commit the conversation.' );
				}
			} catch ( Throwable $error ) {
				$wpdb->query( 'ROLLBACK' );
				wp_cache_delete( $id, 'post_meta' );
				throw $error;
			}
		} finally {
			if ( $apply ) {
				$wpdb->get_var( $wpdb->prepare( 'SELECT RELEASE_LOCK(%s)', $lock ) );
			}
		}
	}
	WP_CLI::log( (string) wp_json_encode( $counts ) );
} )( $args ?? array() );
