<?php
/**
 * PROTOTYPE — throwaway (map #220, ticket #226 "账号链 · 后台账户页长什么样").
 *
 * Three variants of a dedicated accounts page in wp-admin, switchable with
 * admin.php?page=linker-accounts-prototype&variant=A|B|C (or the floating bar,
 * or the ← → keys). Sample applicants only; no button writes to the database.
 * Loaded into a local instance as a must-use plugin (see README.md); never
 * shipped.
 *
 * @package Linker\Prototype
 */

defined( 'ABSPATH' ) || exit;

add_action(
	'admin_menu',
	static function (): void {
		add_menu_page(
			'Accounts',
			'Accounts <span class="awaiting-mod">4</span>',
			'edit_users',
			'linker-accounts-prototype',
			static function (): void {
				echo '<div class="wrap" id="lap-root"></div>';
				echo '<style>' . file_get_contents( __DIR__ . '/accounts-prototype.css' ) . '</style>'; // phpcs:ignore -- prototype.
				echo '<script>' . file_get_contents( __DIR__ . '/accounts-prototype.js' ) . '</script>'; // phpcs:ignore -- prototype.
			},
			'dashicons-groups',
			3
		);
	}
);

add_action(
	'admin_bar_menu',
	static function ( WP_Admin_Bar $bar ): void {
		if ( ! is_admin() || ! current_user_can( 'edit_users' ) ) {
			return;
		}
		$bar->add_node(
			array(
				'id'    => 'linker-accounts-flag',
				'title' => '<span class="lap-flag">4 accounts to review</span>',
				'href'  => admin_url( 'admin.php?page=linker-accounts-prototype&variant=C&drawer=1' ),
			)
		);
	},
	100
);
