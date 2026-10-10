<?php
/**
 * The four states of an inquiry.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry;

use WC_Order;

/**
 * An inquiry is received, gets a Proforma invoice, and is then completed or
 * cancelled (AGENTS.md §3). The first two are statuses of this plugin; they lie
 * outside WooCommerce's paid and payable statuses, so nothing asks for or
 * records a payment. The site never reduces stock: stock is only ever "in
 * stock" (owner ruling 2026-10-02) and deliveries happen offline.
 */
final class Statuses {

	/**
	 * Status slugs, without WooCommerce's "wc-" prefix.
	 */
	public const RECEIVED = 'inquiry-received';
	public const PROFORMA = 'proforma-issued';

	/**
	 * Admin list colours of the two statuses: WooCommerce 11.1's own colours of
	 * its on-hold and processing badges (assets/css/admin.css, .order-status).
	 */
	private const COLOURS = array(
		self::RECEIVED => array( '#f8dda7', '#573b00' ),
		self::PROFORMA => array( '#c6e1c6', '#2c4700' ),
	);

	/**
	 * Registers the two post statuses; runs on init.
	 */
	public function register(): void {
		register_post_status(
			'wc-' . self::RECEIVED,
			array(
				'label'                     => _x( 'Inquiry received', 'Inquiry status', 'linker-commerce' ),
				'public'                    => false,
				'exclude_from_search'       => false,
				'show_in_admin_all_list'    => true,
				'show_in_admin_status_list' => true,
				/* translators: %s: number of inquiries. */
				'label_count'               => _n_noop( 'Inquiry received <span class="count">(%s)</span>', 'Inquiry received <span class="count">(%s)</span>', 'linker-commerce' ),
			)
		);
		register_post_status(
			'wc-' . self::PROFORMA,
			array(
				'label'                     => _x( 'Proforma invoice issued', 'Inquiry status', 'linker-commerce' ),
				'public'                    => false,
				'exclude_from_search'       => false,
				'show_in_admin_all_list'    => true,
				'show_in_admin_status_list' => true,
				/* translators: %s: number of inquiries. */
				'label_count'               => _n_noop( 'Proforma invoice issued <span class="count">(%s)</span>', 'Proforma invoice issued <span class="count">(%s)</span>', 'linker-commerce' ),
			)
		);
	}

	/**
	 * The status list with the two inquiry statuses after "pending", and the
	 * names customers read for completed and cancelled.
	 *
	 * @param array<string, string> $statuses Status key → name.
	 * @return array<string, string>
	 */
	public function names( array $statuses ): array {
		$named = array();
		foreach ( $statuses as $key => $name ) {
			$named[ $key ] = $name;
			if ( 'wc-pending' === $key ) {
				$named[ 'wc-' . self::RECEIVED ] = _x( 'Inquiry received', 'Inquiry status', 'linker-commerce' );
				$named[ 'wc-' . self::PROFORMA ] = _x( 'Proforma invoice issued', 'Inquiry status', 'linker-commerce' );
			}
		}
		$named[ 'wc-' . self::RECEIVED ] ??= _x( 'Inquiry received', 'Inquiry status', 'linker-commerce' );
		$named[ 'wc-' . self::PROFORMA ] ??= _x( 'Proforma invoice issued', 'Inquiry status', 'linker-commerce' );
		// An inquiry WooCommerce created but could not send stays "pending"; it never reads "pending payment".
		$named['wc-pending']   = _x( 'Not sent', 'Inquiry status', 'linker-commerce' );
		$named['wc-completed'] = _x( 'Completed', 'Inquiry status', 'linker-commerce' );
		$named['wc-cancelled'] = _x( 'Cancelled', 'Inquiry status', 'linker-commerce' );
		return $named;
	}

	/**
	 * Staff may still change items and prices of a received inquiry.
	 *
	 * @param bool     $editable WooCommerce's verdict.
	 * @param WC_Order $order    Order.
	 */
	public function editable( bool $editable, WC_Order $order ): bool {
		return $editable || self::RECEIVED === $order->get_status();
	}

	/**
	 * Every inquiry can be requested again ("Request again" puts its products
	 * into a new solution draft).
	 *
	 * @param string[] $statuses Statuses WooCommerce allows.
	 * @return list<string>
	 */
	public function request_again( array $statuses ): array {
		return array_values( array_unique( array_merge( $statuses, array( self::RECEIVED, self::PROFORMA, 'completed', 'cancelled' ) ) ) );
	}

	/**
	 * Open inquiries are not revenue in WooCommerce Analytics
	 * (docs/research/2026-10-09/account-workspace.md §4.2).
	 *
	 * @param string[] $statuses Excluded statuses.
	 * @return list<string>
	 */
	public function analytics_excluded( array $statuses ): array {
		return array_values( array_unique( array_merge( $statuses, array( self::RECEIVED, self::PROFORMA ) ) ) );
	}

	/**
	 * Prints the colours of the two statuses in the admin order list; runs on admin_head.
	 */
	public function admin_colours(): void {
		$css = '';
		foreach ( self::COLOURS as $status => [ $background, $text ] ) {
			$css .= sprintf( '.order-status.status-%1$s{background:%2$s;color:%3$s}', $status, $background, $text );
		}
		printf( '<style id="linker-inquiry-statuses">%s</style>', $css ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- built above from constants.
	}
}
