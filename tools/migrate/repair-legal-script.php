<?php
/** Narrow content restoration; current copy and language pairing stay intact. */
$payload = json_decode( base64_decode( '__LEGAL_SCRIPT_PAYLOAD__' ), true, 512, JSON_THROW_ON_ERROR );
if ( 'read' === $payload['operation'] ) {
	$out = array( 'home' => home_url(), 'rows' => array() );
	foreach ( $payload['ids'] as $id ) {
		$post = get_post( (int) $id );
		if ( ! $post ) {
			throw new RuntimeException( 'Missing page or reference revision.' );
		}
		$out['rows'][ (string) $id ] = array( 'parent' => (int) $post->post_parent, 'type' => $post->post_type, 'content' => $post->post_content );
	}
	echo '@@legal-script@@' . wp_json_encode( $out );
	return;
}
if ( 'save' !== $payload['operation'] ) {
	throw new RuntimeException( 'Unknown operation.' );
}
// Check every source before writing either language, including an idempotent replay.
foreach ( $payload['changes'] as $change ) {
	if ( get_post( (int) $change['id'] )->post_content !== $change['before'] ) {
		throw new RuntimeException( 'Page changed since backup; nothing written.' );
	}
}
$written = array();
try {
	foreach ( $payload['changes'] as $change ) {
		if ( $change['before'] === $change['after'] ) {
			continue;
		}
		$result = wp_update_post( array( 'ID' => (int) $change['id'], 'post_content' => wp_slash( $change['after'] ) ), true, false );
		if ( is_wp_error( $result ) ) {
			throw new RuntimeException( $result->get_error_message() );
		}
		$written[] = $change;
		clean_post_cache( (int) $change['id'] );
		if ( get_post( (int) $change['id'] )->post_content !== $change['after'] ) {
			throw new RuntimeException( 'Saved page differs from the planned bytes.' );
		}
	}
} catch ( Throwable $error ) {
	foreach ( $written as $change ) {
		$result = wp_update_post( array( 'ID' => (int) $change['id'], 'post_content' => wp_slash( $change['before'] ) ), true, false );
		clean_post_cache( (int) $change['id'] );
		if ( is_wp_error( $result ) || get_post( (int) $change['id'] )->post_content !== $change['before'] ) {
			throw new RuntimeException( 'Restore failed; use the local backup. Original failure: ' . $error->getMessage() );
		}
	}
	throw $error;
}
echo '@@legal-script@@' . wp_json_encode( array( 'saved' => count( $written ) ) );
