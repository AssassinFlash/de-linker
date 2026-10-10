<?php
/**
 * The Proforma invoice on the inquiry screen.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Proforma;

use Linker\Commerce\Account\DocumentDownload;
use Linker\Commerce\Vocabulary\LocaleFormat;
use RuntimeException;
use WC_Admin_Meta_Boxes;
use WC_Order;
use WP_Post;

/**
 * On the inquiry screen staff find one action, "Issue Proforma", in a box
 * that afterwards shows the number, the validity and the PDF. The inquiry list
 * gets a Proforma column. WooCommerce's other order actions (resend order
 * details, regenerate downloads) do not apply to inquiries and are removed
 * (docs/specs/11-commerce.md, journey step 5: "无其他动作").
 */
final class AdminBox {

	/**
	 * Name of the button that issues the Proforma.
	 */
	public const BUTTON = 'linker_issue_proforma';

	/**
	 * Sets up the box.
	 *
	 * @param Issuer $issuer The issuer.
	 */
	public function __construct( private readonly Issuer $issuer ) {}

	/**
	 * Adds the box to the inquiry screen (HPOS and post storage); runs on add_meta_boxes.
	 *
	 * @param string $screen Screen id or post type.
	 */
	public function add( string $screen ): void {
		if ( in_array( $screen, array( 'shop_order', wc_get_page_screen_id( 'shop-order' ) ), true ) ) {
			add_meta_box( 'linker-proforma', __( 'Proforma invoice', 'linker-commerce' ), array( $this, 'render' ), $screen, 'side', 'high' );
		}
	}

	/**
	 * Prints the box.
	 *
	 * @param WP_Post|WC_Order $post_or_order The inquiry.
	 */
	public function render( $post_or_order ): void {
		$order = $post_or_order instanceof WC_Order ? $post_or_order : wc_get_order( $post_or_order->ID );
		if ( ! $order instanceof WC_Order ) {
			return;
		}
		$number = (string) $order->get_meta( Issuer::NUMBER_META );
		if ( '' !== $number ) {
			$issued = (int) $order->get_meta( Issuer::ISSUED_META );
			printf(
				'<p><strong>%1$s</strong><br>%2$s<br>%3$s</p><p><a class="button" href="%4$s">%5$s</a></p>',
				esc_html( $number ),
				/* translators: %s: date. */
				esc_html( sprintf( __( 'Issued %s', 'linker-commerce' ), wp_date( LocaleFormat::date_format(), $issued ) ) ),
				/* translators: %s: date. */
				esc_html( sprintf( __( 'Valid until %s', 'linker-commerce' ), wp_date( LocaleFormat::date_format(), Document::valid_until( ( new \DateTimeImmutable() )->setTimestamp( $issued ) )->getTimestamp() ) ) ),
				esc_url( DocumentDownload::proforma_url( $order ) ),
				esc_html__( 'Download PDF', 'linker-commerce' )
			);
			return;
		}
		$blocker = $this->issuer->blocker( $order );
		if ( '' !== $blocker ) {
			printf( '<p>%s</p>', esc_html( $blocker ) );
			return;
		}
		printf(
			'<p>%1$s</p><p><button type="submit" class="button button-primary" name="%2$s" value="1">%3$s</button></p>',
			esc_html__( 'Save your changes to prices and quantities, then issue the Proforma invoice. The customer receives an email with the link.', 'linker-commerce' ),
			esc_attr( self::BUTTON ),
			esc_html__( 'Issue Proforma', 'linker-commerce' )
		);
	}

	/**
	 * Issues the Proforma when the button was pressed; runs on
	 * woocommerce_process_shop_order_meta after WooCommerce saved the inquiry's
	 * items and data (its nonce is checked by then).
	 *
	 * @param int $order_id Inquiry.
	 */
	public function process( int $order_id ): void {
		// phpcs:ignore WordPress.Security.NonceVerification.Missing -- WooCommerce verified the order edit nonce before this action.
		if ( empty( $_POST[ self::BUTTON ] ) || ! current_user_can( 'edit_shop_orders' ) ) {
			return;
		}
		$order = wc_get_order( $order_id );
		if ( ! $order instanceof WC_Order ) {
			return;
		}
		try {
			$this->issuer->issue( $order );
		} catch ( RuntimeException $error ) {
			WC_Admin_Meta_Boxes::add_error( esc_html( $error->getMessage() ) );
		}
	}

	/**
	 * Inquiries have no order actions besides the Proforma button; replaces WooCommerce's.
	 *
	 * @return array<string, string>
	 */
	public function order_actions(): array {
		return array();
	}

	/**
	 * Inquiry list columns: "Inquiry" instead of "Order", and the Proforma number.
	 *
	 * @param array<string, string> $columns Column id → heading.
	 * @return array<string, string>
	 */
	public function columns( array $columns ): array {
		$named = array();
		foreach ( $columns as $id => $heading ) {
			$named[ $id ] = 'order_number' === $id ? esc_html__( 'Inquiry', 'linker-commerce' ) : $heading;
			if ( 'order_status' === $id ) {
				$named['linker_proforma'] = esc_html__( 'Proforma', 'linker-commerce' );
			}
		}
		unset( $named['shipping_address'] );
		return $named;
	}

	/**
	 * Prints the Proforma column of an inquiry.
	 *
	 * @param string       $column        Column id.
	 * @param WC_Order|int $order_or_post Inquiry (HPOS) or its post id.
	 */
	public function column( string $column, $order_or_post ): void {
		if ( 'linker_proforma' !== $column ) {
			return;
		}
		$order = $order_or_post instanceof WC_Order ? $order_or_post : wc_get_order( (int) $order_or_post );
		echo esc_html( $order instanceof WC_Order ? (string) $order->get_meta( Issuer::NUMBER_META ) : '' );
	}
}
