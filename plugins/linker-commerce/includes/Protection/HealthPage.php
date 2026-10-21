<?php
/**
 * Native staff health and a verification-only diagnostic.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

/** Staff can distinguish configured helpers from integrated and observed doors. */
final class HealthPage {
	public const PAGE = 'linker-public-protection';

	/**
	 * Reuse native WordPress markup and the same client as the actual forms.
	 *
	 * @param Configuration $configuration Current private mode/readiness.
	 * @param Assets        $assets Shared script.
	 */
	public function __construct( private readonly Configuration $configuration, private readonly Assets $assets ) {}

	/** Add under the existing WooCommerce staff menu. */
	public function menu(): void {
		add_submenu_page( 'woocommerce', __( 'Public entry protection', 'linker-commerce' ), __( 'Public entry protection', 'linker-commerce' ), 'manage_woocommerce', self::PAGE, array( $this, 'render' ) );
	}

	/** Load only on this staff page; merely viewing it does not load Cloudflare. */
	public function assets(): void {
		if ( current_user_can( 'manage_woocommerce' ) && isset( $_GET['page'] ) && self::PAGE === sanitize_key( wp_unslash( $_GET['page'] ) ) ) { // phpcs:ignore WordPress.Security.NonceVerification.Recommended -- Read-only native admin page selection.
			$this->assets->enqueue();
		}
	}

	/** Native controls carry no code for business submission. */
	public function render(): void {
		if ( ! current_user_can( 'manage_woocommerce' ) ) {
			return;
		}
		$health  = $this->configuration->health();
		$modes   = array(
			'off'     => __( 'Off', 'linker-commerce' ),
			'observe' => __( 'Observe', 'linker-commerce' ),
			'enforce' => __( 'Enforce', 'linker-commerce' ),
		);
		$summary = false === get_option( Ledger::OPTION ) ? array(
			'counts'   => array(),
			'receipts' => 0,
			'buckets'  => 0,
		) : ( new Ledger() )->summary();
		/**
		 * Actual integration modules identify the native handlers they guard.
		 * This declaration is not evidence of live verification success.
		 *
		 * @since 0.2.0
		 * @param array<string,string> $consumers Action to native handler description.
		 */
		$consumers = apply_filters( 'linker_commerce_public_protection_consumers', array() );
		echo '<div class="wrap"><h1>' . esc_html__( 'Public entry protection', 'linker-commerce' ) . '</h1><h2>' . esc_html__( 'Configuration', 'linker-commerce' ) . '</h2><dl><dt>' . esc_html__( 'Mode', 'linker-commerce' ) . '</dt><dd><strong>' . esc_html( $modes[ $health['mode'] ] ?? __( 'Invalid configuration', 'linker-commerce' ) ) . '</strong></dd><dt>' . esc_html__( 'Validation keys', 'linker-commerce' ) . '</dt><dd>' . esc_html( $health['configured'] ? __( 'Configured', 'linker-commerce' ) : __( 'Not configured', 'linker-commerce' ) ) . '</dd><dt>' . esc_html__( 'Environment', 'linker-commerce' ) . '</dt><dd>' . esc_html( $health['test_keys'] ? __( 'Test keys; not permitted in production', 'linker-commerce' ) : __( 'Live keys or not configured', 'linker-commerce' ) ) . '</dd></dl>';
		echo '<p>' . esc_html__( 'The mode and keys do not prove that every entry is protected. Check the connected handlers and observed results below.', 'linker-commerce' ) . '</p><h2>' . esc_html__( 'Connected handlers', 'linker-commerce' ) . '</h2>';
		if ( array() === $consumers ) {
			echo '<p>' . esc_html__( 'No business or resource handlers have been connected to this shared service.', 'linker-commerce' ) . '</p>';
		} else {
			echo '<ul>';
			foreach ( $consumers as $action => $description ) {
				echo '<li><code>' . esc_html( $action ) . '</code> — ' . esc_html( $description ) . '</li>';
			}
			echo '</ul>';
		}
		echo '<h2>' . esc_html__( 'Verification check', 'linker-commerce' ) . '</h2><p>' . esc_html__( 'This checks the shared verification service. It does not create an inquiry, send mail or call a model.', 'linker-commerce' ) . '</p><div data-linker-protection-check><button class="button" type="button" data-linker-protection-start' . disabled( $health['ready'], false, false ) . '>' . esc_html__( 'Check verification', 'linker-commerce' ) . '</button><p role="status" aria-live="polite" data-linker-protection-status></p><div data-linker-protection-widget></div></div>';
		echo '<h2>' . esc_html__( 'Observed processing', 'linker-commerce' ) . '</h2><p>' . esc_html__( 'Counts cover receipts still in the retry window. They are not a complete traffic history or an exact cost report.', 'linker-commerce' ) . '</p>';
		if ( is_wp_error( $summary ) ) {
			echo '<div class="notice notice-error"><p>' . esc_html__( 'The admission journal is unavailable. No successful protection check can be inferred from this page.', 'linker-commerce' ) . '</p></div>';
		} else {
			echo '<p>' . esc_html__( 'Stored receipts', 'linker-commerce' ) . ': ' . esc_html( number_format_i18n( $summary['receipts'] ) ) . '</p><table class="widefat striped"><thead><tr><th>' . esc_html__( 'Operation', 'linker-commerce' ) . '</th><th>' . esc_html__( 'State', 'linker-commerce' ) . '</th><th>' . esc_html__( 'Count', 'linker-commerce' ) . '</th></tr></thead><tbody>';
			foreach ( $summary['counts'] as $purpose => $states ) {
				foreach ( $states as $status => $count ) {
					echo '<tr><td><code>' . esc_html( $purpose ) . '</code></td><td>' . esc_html( $status ) . '</td><td>' . esc_html( number_format_i18n( $count ) ) . '</td></tr>';
				}
			}
			echo '</tbody></table>';
		}
		echo '</div>';
	}
}
