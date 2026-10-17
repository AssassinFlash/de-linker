<?php
/**
 * PROTOTYPE — throwaway (map #220, ticket #231 "Genie · 首页 hero 打字之后怎样").
 *
 * Three variants on the real homepage, switchable with /?variant=A|B|C (or the
 * floating bar, or the ← → keys). The hero's untouched look stays as it is; only
 * what happens after typing, a chip, photo, attachment or voice changes. Answers
 * are scripted (not the real Genie); product cards come from the site's own
 * Store API, read-only. Loaded into a local instance as a must-use plugin (see
 * README.md); never shipped.
 *
 * @package Linker\Prototype
 */

defined( 'ABSPATH' ) || exit;

add_action(
	'wp_footer',
	static function (): void {
		if ( ! is_front_page() ) {
			return;
		}
		echo '<style>' . file_get_contents( __DIR__ . '/hero-prototype.css' ) . '</style>'; // phpcs:ignore -- prototype.
		echo '<script>' . file_get_contents( __DIR__ . '/hero-prototype.js' ) . '</script>'; // phpcs:ignore -- prototype.
	},
	100
);
