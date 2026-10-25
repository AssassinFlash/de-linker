<?php
/**
 * Narrow content restoration; current copy and language pairing stay intact.
 *
 * @package Linker\Commerce
 */

( static function (): void {
	// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- Local JSON transport, never executable payload data.
	$payload = json_decode( base64_decode( '__LEGAL_SCRIPT_PAYLOAD__' ), true, 512, JSON_THROW_ON_ERROR );
	if ( 'read' === $payload['operation'] ) {
		$out = array(
			'home' => home_url(),
			'rows' => array(),
		);
		foreach ( $payload['ids'] as $id ) {
			$post = get_post( (int) $id );
			if ( ! $post ) {
				throw new RuntimeException( 'Missing page or reference revision.' );
			}
			$out['rows'][ (string) $id ] = array(
				'parent'  => (int) $post->post_parent,
				'type'    => $post->post_type,
				'content' => $post->post_content,
			);
		}
		echo '@@legal-script@@' . wp_json_encode( $out );
		return;
	}
	if ( 'save' !== $payload['operation'] ) {
		throw new RuntimeException( 'Unknown operation.' );
	}
	global $wpdb;
	if ( 'wpdb' !== get_class( $wpdb ) ) {
		throw new RuntimeException( 'The native WordPress mysqli connection is required.' );
	}
	// The native public compatibility accessors expose these protected
	// properties without reflection, subclass replacement or a new connection.
	$connection = $wpdb->__get( 'dbh' );
	$reconnects = $wpdb->__get( 'reconnect_retries' );
	if ( ! $connection instanceof mysqli || ! is_int( $reconnects ) ) {
		throw new RuntimeException( 'The native WordPress mysqli connection is required.' );
	}
	$engine = $wpdb->get_var( $wpdb->prepare( 'SELECT ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s', $wpdb->posts ) );
	if ( 'InnoDB' !== $engine ) {
		throw new RuntimeException( 'Transactional post storage is required.' );
	}
	$written = array();
	$ids     = array_map( static fn( array $change ): int => (int) $change['id'], $payload['changes'] );
	// A replay on a fresh connection has neither this transaction nor its
	// locks. Native mysqli exceptions must escape before wpdb can reconnect.
	$thread           = mysqli_thread_id( $connection ); // phpcs:ignore WordPress.DB.RestrictedFunctions.mysql_mysqli_thread_id -- Inspect the existing native handle; do not create or reconnect a connection.
	$driver           = new mysqli_driver();
	$report_mode      = $driver->report_mode;
	$commit_attempted = false;
	$guard            = static function ( string $query ) use ( $wpdb, $connection, $thread ): string {
		if ( $wpdb->__get( 'dbh' ) !== $connection || mysqli_thread_id( $connection ) !== $thread ) { // phpcs:ignore WordPress.DB.RestrictedFunctions.mysql_mysqli_thread_id -- A changed transaction connection must fail before another query.
			throw new RuntimeException( 'Database connection changed during content transaction.' );
		}
		mysqli_report( MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT ); // phpcs:ignore WordPress.DB.RestrictedFunctions.mysql_mysqli_report -- Prevent wpdb's disconnected write replay for this CLI transaction only.
		return $query;
	};
	sort( $ids );
	try {
		$wpdb->__set( 'reconnect_retries', 0 );
		mysqli_report( MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT ); // phpcs:ignore WordPress.DB.RestrictedFunctions.mysql_mysqli_report -- Restored in finally; no persistent connection setting changes.
		add_filter( 'query', $guard, PHP_INT_MAX );
		if ( false === $wpdb->query( 'START TRANSACTION' ) ) {
			throw new RuntimeException( 'Could not begin the content transaction.' );
		}
		// Lock both rows before checking their source, so concurrent saves wait.
		$locked = array();
		foreach ( $ids as $id ) {
			$locked[ $id ] = $wpdb->get_var( $wpdb->prepare( 'SELECT post_content FROM %i WHERE ID = %d FOR UPDATE', $wpdb->posts, $id ) );
			clean_post_cache( $id );
		}
		foreach ( $payload['changes'] as $change ) {
			if ( $locked[ $change['id'] ] !== $change['before'] ) {
				throw new RuntimeException( 'Page changed since backup; nothing written.' );
			}
		}
		foreach ( $payload['changes'] as $change ) {
			if ( $change['before'] === $change['after'] ) {
				continue;
			}
			$result = wp_update_post(
				array(
					'ID'           => (int) $change['id'],
					'post_content' => wp_slash( $change['after'] ),
				),
				true,
				false
			);
			if ( is_wp_error( $result ) ) {
				throw new RuntimeException( $result->get_error_message() );
			}
			$written[] = $change;
			clean_post_cache( (int) $change['id'] );
			$saved = get_post( (int) $change['id'] );
			if ( ! $saved instanceof WP_Post || $saved->post_content !== $change['after'] ) {
				throw new RuntimeException( 'Saved page differs from the planned bytes.' );
			}
		}
		$commit_attempted = true;
		if ( false === $wpdb->query( 'COMMIT' ) ) {
			throw new RuntimeException( 'Could not commit the content transaction.' );
		}
	} catch ( Throwable $error ) {
		try {
			$wpdb->query( 'ROLLBACK' );
		} catch ( Throwable $rollback_error ) {
			// Keep the first failure authoritative, without logging page data.
			error_log( 'Content transaction rollback unavailable: ' . get_class( $rollback_error ) . ' (' . $rollback_error->getCode() . ').' ); // phpcs:ignore WordPress.PHP.DevelopmentFunctions.error_log_error_log -- CLI failure diagnostic contains only exception type/code, never content.
		}
		foreach ( $ids as $id ) {
			// clean_post_cache can query a post. These native cache operations
			// also work after a disconnect, without hiding the first failure.
			wp_cache_delete( $id, 'posts' );
			wp_cache_delete( $id, 'post_meta' );
		}
		if ( $commit_attempted ) {
			throw new RuntimeException( 'Commit outcome is unknown. Independently read both pages before retrying or rolling back.', 0, $error ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Preserve the original exception as cause, not interpolated output.
		}
		throw $error;
	} finally {
		remove_filter( 'query', $guard, PHP_INT_MAX );
		$wpdb->__set( 'reconnect_retries', $reconnects );
		mysqli_report( $report_mode ); // phpcs:ignore WordPress.DB.RestrictedFunctions.mysql_mysqli_report -- Restore the caller's original report mode.
	}
	foreach ( $ids as $id ) {
		clean_post_cache( $id );
	}
	echo '@@legal-script@@' . wp_json_encode( array( 'saved' => count( $written ) ) );
} )();
