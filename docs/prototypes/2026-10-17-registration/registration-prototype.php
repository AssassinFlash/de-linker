<?php
/**
 * PROTOTYPE — throwaway (map #220, ticket #225 "账号链 · 按研究结论改注册表单").
 *
 * The registration form after the #224 research: 9 inputs, two plain groups,
 * country list Europe first and searchable, website or VAT ID (one of them),
 * honeypot + minimum fill time. Three variants on /my-account/register/?reg=A|B|C.
 * Countries come from WooCommerce itself; nothing is submitted or saved.
 * Local instance only; never shipped.
 *
 * @package Linker\Prototype
 */

defined( 'ABSPATH' ) || exit;

add_action(
	'wp_footer',
	static function (): void {
		if ( ! isset( $_GET['reg'] ) || ! function_exists( 'is_account_page' ) || ! is_account_page() || is_user_logged_in() ) { // phpcs:ignore -- prototype.
			return;
		}
		$countries = WC()->countries->get_countries();
		$continents = WC()->countries->get_continents();
		$data = array(
			'countries' => $countries,
			'europe'    => $continents['EU']['countries'] ?? array(),
			'logo'      => content_url( 'plugins/linker-commerce/assets/linker-logo-wordmark.webp' ),
		);
		echo '<style>' . file_get_contents( __DIR__ . '/registration-prototype.css' ) . '</style>'; // phpcs:ignore -- prototype.
		echo '<script>window.LINKER_REG_PROTO = ' . wp_json_encode( $data ) . ';</script>'; // phpcs:ignore -- prototype.
		echo '<script>' . file_get_contents( __DIR__ . '/registration-prototype.js' ) . '</script>'; // phpcs:ignore -- prototype.
	},
	120
);
