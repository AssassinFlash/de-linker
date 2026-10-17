<?php
/**
 * Native dashboard, menu and admin-bar entry points for account review.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration;

use WP_Admin_Bar;

/** Admin-only surfaces. The React app shares cards between native mount points. */
final class AccountsAdmin {

	/** Canonical menu slug, also the stable mail-link contract. */
	public const PAGE = 'linker-accounts';

	/**
	 * The plugin file and shared readers.
	 *
	 * @param string   $file     Main plugin file.
	 * @param Accounts $accounts Account data.
	 * @param Approval $approval Approval authority.
	 */
	public function __construct( private readonly string $file, private readonly Accounts $accounts, private readonly Approval $approval ) {}

	/**
	 * Stable deep link for notification/digest producers.
	 *
	 * @param int $user_id Customer, or zero for the historical list.
	 */
	public static function url( int $user_id = 0 ): string {
		$url = admin_url( 'admin.php?page=' . self::PAGE );
		return $user_id > 0 ? add_query_arg( 'focus', $user_id, $url ) : $url;
	}

	/** Adds native entry points; no frontend/template hooks. */
	public function register(): void {
		add_action( 'wp_dashboard_setup', array( $this, 'dashboard' ) );
		add_action( 'admin_menu', array( $this, 'menu' ) );
		// WP_Admin_Bar::add_menus() puts the core edit link at 80 and secondary
		// groups at 200. 100 appends this review entry after the core left nodes.
		add_action( 'admin_bar_menu', array( $this, 'bar' ), 100 );
		add_action( 'admin_enqueue_scripts', array( $this, 'assets' ) );
		add_action( 'admin_footer', array( $this, 'root' ) );
	}

	/** Places the review widget in WordPress's high-priority dashboard context. */
	public function dashboard(): void {
		if ( current_user_can( 'edit_users' ) ) {
			$count = $this->accounts->counts()[ Approval::PENDING ];
			$title = '<span>' . esc_html__( 'Accounts waiting for you', 'linker-commerce' ) . ' (<span data-linker-account-count="pending">' . $count . '</span>)</span>';
			wp_add_dashboard_widget( 'linker-accounts-widget', $title, array( $this, 'widget' ), null, null, 'normal', 'high' );
		}
	}

	/** The widget's content is the shared queue. */
	public function widget(): void {
		echo '<p><a href="' . esc_url( self::url() ) . '">' . esc_html__( 'All accounts →', 'linker-commerce' ) . '</a></p><div id="linker-accounts-queue"></div>';
	}

	/** The Accounts entry follows Dashboard, with WordPress's native count badge. */
	public function menu(): void {
		if ( ! current_user_can( 'edit_users' ) ) {
			return;
		}
		$count = $this->accounts->counts()[ Approval::PENDING ];
		// Position 3 is immediately after the core Dashboard (position 2), as in
		// the owner-selected prototype; other plugins keep their own positions.
		add_menu_page( __( 'Accounts', 'linker-commerce' ), __( 'Accounts', 'linker-commerce' ) . ' <span class="awaiting-mod" data-linker-account-count="pending">' . $count . '</span>', 'edit_users', self::PAGE, array( $this, 'page' ), 'dashicons-groups', 3 );
	}

	/**
	 * The flag is available on every backend page a reviewing employee visits.
	 *
	 * @param WP_Admin_Bar $bar Native toolbar.
	 */
	public function bar( WP_Admin_Bar $bar ): void {
		if ( ! is_admin() || ! current_user_can( 'edit_users' ) ) {
			return;
		}
		$count = $this->accounts->counts()[ Approval::PENDING ];
		/* translators: %s: number of accounts waiting for review. */
		$label = sprintf( _n( '%s account to review', '%s accounts to review', $count, 'linker-commerce' ), number_format_i18n( $count ) );
		$bar->add_node(
			array(
				'id'    => self::PAGE,
				'title' => '<span class="ab-icon dashicons dashicons-groups" aria-hidden="true"></span><span class="linker-review-label">' . esc_html( $label ) . '</span><span class="linker-review-compact" aria-hidden="true" data-linker-account-count="pending">' . $count . '</span>',
				'href'  => self::url(),
				'meta'  => array(
					'class' => $count > 0 ? 'linker-has-pending' : '',
					'title' => $label,
				),
			)
		);
	}

	/** Historical table, optionally with the focused card above it. */
	public function page(): void {
		if ( ! current_user_can( 'edit_users' ) ) {
			return;
		}
		require_once ABSPATH . 'wp-admin/includes/class-wp-list-table.php';
		$status = $this->query( 'status' );
		$status = in_array( $status, Approval::states(), true ) ? $status : 'all';
		$table  = new AccountsTable( $this->accounts, $this->approval, $status, $this->query( 's' ) );
		$table->prepare_items();
		echo '<div class="wrap" id="linker-accounts-history" data-status="' . esc_attr( $status ) . '"><h1>' . esc_html__( 'Accounts', 'linker-commerce' ) . '</h1><div id="linker-accounts-focus"></div>';
		echo '<section aria-labelledby="linker-restricted-heading"><h2 id="linker-restricted-heading">' . esc_html__( 'Restricted, awaiting customer information', 'linker-commerce' ) . ' (<span data-linker-account-count="restricted">' . esc_html( (string) $this->accounts->counts()[ Approval::RESTRICTED ] ) . '</span>)</h2><div id="linker-accounts-restricted"></div></section>';
		$table->views();
		echo '<form method="get"><input type="hidden" name="page" value="' . esc_attr( self::PAGE ) . '"><input type="hidden" name="status" value="' . esc_attr( $status ) . '">';
		$table->search_box( __( 'Search accounts', 'linker-commerce' ), 'linker-accounts' );
		$table->display();
		echo '</form></div>';
	}

	/** Loads only the narrow admin bundle, using WP's React/i18n dependency handles. */
	public function assets(): void {
		if ( ! current_user_can( 'edit_users' ) ) {
			return;
		}
		$path = plugin_dir_path( $this->file ) . 'build/accounts.asset.php';
		if ( ! is_file( $path ) ) {
			return;
		}
		$asset = require $path;
		$base  = plugin_dir_url( $this->file ) . 'build/';
		wp_enqueue_script( 'linker-accounts', $base . 'accounts.js', $asset['dependencies'], $asset['version'], true );
		wp_enqueue_style( 'linker-accounts', $base . 'style-accounts.css', array(), $asset['version'] );
		wp_set_script_translations( 'linker-accounts', 'linker-commerce', plugin_dir_path( $this->file ) . 'languages' );
	}

	/** One app owns both portals and synchronizes the native entry points. */
	public function root(): void {
		if ( ! current_user_can( 'edit_users' ) ) {
			return;
		}
		echo '<div id="linker-accounts-app" data-api="' . esc_url( rest_url( 'linker/v1/accounts' ) ) . '" data-nonce="' . esc_attr( wp_create_nonce( 'wp_rest' ) ) . '" data-focus="' . esc_attr( $this->query( 'page' ) === self::PAGE ? (string) absint( $this->query( 'focus' ) ) : '0' ) . '"></div>';
	}

	/**
	 * Read-only list/deep-link filters do not perform an action.
	 *
	 * @param string $key Query key.
	 */
	private function query( string $key ): string {
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- read-only table filters and deep links; all writes use the authenticated REST POST.
		return isset( $_GET[ $key ] ) && is_string( $_GET[ $key ] ) ? sanitize_text_field( wp_unslash( $_GET[ $key ] ) ) : '';
	}
}
