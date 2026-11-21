<?php
/**
 * Native staff view of the Turnstile configuration.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

/** Only the hostname and configuration status are displayed. */
final class HealthPage {
	public const PAGE = 'linker-public-protection';

	/**
	 * Show the current server-side configuration.
	 *
	 * @param Configuration $configuration Native public form settings.
	 */
	public function __construct( private readonly Configuration $configuration ) {}

	/** Add under the existing WooCommerce staff menu. */
	public function menu(): void {
		add_submenu_page( 'woocommerce', __( 'Public entry protection', 'linker-commerce' ), __( 'Public entry protection', 'linker-commerce' ), 'manage_woocommerce', self::PAGE, array( $this, 'render' ) );
	}

	/** Public verification stays on the customer forms that submit it. */
	public function render(): void {
		if ( ! current_user_can( 'manage_woocommerce' ) ) {
			return;
		}
		$health = $this->configuration->health();
		echo '<div class="wrap"><h1>' . esc_html__( 'Public entry protection', 'linker-commerce' ) . '</h1><dl>';
		echo '<dt>' . esc_html__( 'Validation keys', 'linker-commerce' ) . '</dt><dd>' . esc_html( $health['configured'] ? __( 'Configured', 'linker-commerce' ) : __( 'Not configured', 'linker-commerce' ) ) . '</dd>';
		echo '<dt>' . esc_html__( 'Hostname', 'linker-commerce' ) . '</dt><dd>' . esc_html( $this->configuration->hostname ) . '</dd></dl></div>';
	}
}
