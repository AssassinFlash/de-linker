<?php
/**
 * PROTOTYPE — throwaway (map #220, ticket #249 "Genie · 主动预览卡").
 *
 * The preview card Genie shows by itself on the homepage, product, category and
 * solution pages. Three looks, switchable with ?pc=A|B|C (or the floating bar).
 * The trigger rules are real (scroll past the main content, then ~8 s; once per
 * visit; closed = hidden for 30 days); ?trigger=now shows the card at once and
 * &dwell=N changes the wait. A suggestion opens the site's real Genie dock with
 * that question. Local instance only; never shipped.
 *
 * @package Linker\Prototype
 */

defined( 'ABSPATH' ) || exit;

add_action(
	'wp_footer',
	static function (): void {
		$ctx = null;
		if ( is_front_page() ) {
			$ctx = array( 'type' => 'home', 'name' => '' );
		} elseif ( function_exists( 'is_product' ) && is_product() ) {
			$ctx = array( 'type' => 'product', 'name' => (string) preg_replace( '/\s*\(.*\)\s*$/', '', get_the_title() ) );
		} elseif ( function_exists( 'is_product_category' ) && is_product_category() ) {
			$ctx = array( 'type' => 'category', 'name' => (string) single_term_title( '', false ) );
		} elseif ( is_page() && 0 === strpos( trim( (string) wp_parse_url( (string) get_permalink(), PHP_URL_PATH ), '/' ), 'solution/' ) ) {
			$ctx = array( 'type' => 'solution', 'name' => get_the_title() );
		}
		if ( null === $ctx ) {
			return;
		}
		echo '<script>window.lppCtx=' . wp_json_encode( $ctx ) . ';</script>';
		echo '<style>' . file_get_contents( __DIR__ . '/preview-prototype.css' ) . '</style>'; // phpcs:ignore -- prototype.
		echo '<script>' . file_get_contents( __DIR__ . '/preview-prototype.js' ) . '</script>'; // phpcs:ignore -- prototype.
	},
	110
);
