<?php
/**
 * Renders a #405 probe post as a small page whose `<main>` is the post.
 *
 * PageCacheChainTest copies this into the instance's mu-plugins for the test
 * and deletes it afterwards. The theme is not the copy the cache stores; the
 * GET is still this post, served by WordPress.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

add_action(
	'template_redirect',
	static function (): void {
		if ( ! is_singular() ) {
			return;
		}
		$linker_probe_id = (int) get_queried_object_id();
		if ( $linker_probe_id <= 0 || '1' !== (string) get_post_meta( $linker_probe_id, '_linker_page_cache_probe', true ) ) {
			return;
		}
		$linker_probe_post = get_post( $linker_probe_id );
		if ( ! $linker_probe_post instanceof WP_Post ) {
			return;
		}
		status_header( 200 );
		header( 'Content-Type: text/html; charset=utf-8' );
		echo '<!DOCTYPE html><html><body><main><h1>' . esc_html( get_the_title( $linker_probe_id ) ) . '</h1><p>' . esc_html( (string) $linker_probe_post->post_content ) . '</p></main></body></html>';
		exit; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- the two values above are escaped; exit ends the probe render.
	},
	0
);
