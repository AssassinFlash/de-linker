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
	$engine = $wpdb->get_var( $wpdb->prepare( 'SELECT ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s', $wpdb->posts ) );
	if ( 'InnoDB' !== $engine ) {
		throw new RuntimeException( 'Transactional post storage is required.' );
	}
	$written = array();
	$ids     = array_map( static fn( array $change ): int => (int) $change['id'], $payload['changes'] );
	sort( $ids );
	if ( false === $wpdb->query( 'START TRANSACTION' ) ) {
		throw new RuntimeException( 'Could not begin the content transaction.' );
	}
	try {
		// Lock both rows before checking their source, so concurrent saves wait.
		$locked = array();
		foreach ( $ids as $id ) {
			$locked[ $id ] = $wpdb->get_var( $wpdb->prepare( "SELECT post_content FROM {$wpdb->posts} WHERE ID = %d FOR UPDATE", $id ) );
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
		if ( false === $wpdb->query( 'COMMIT' ) ) {
			throw new RuntimeException( 'Could not commit the content transaction.' );
		}
	} catch ( Throwable $error ) {
		$wpdb->query( 'ROLLBACK' );
		foreach ( $ids as $id ) {
			clean_post_cache( $id );
		}
		throw $error;
	}
	foreach ( $ids as $id ) {
		clean_post_cache( $id );
	}
	echo '@@legal-script@@' . wp_json_encode( array( 'saved' => count( $written ) ) );
} )();
