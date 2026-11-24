<?php
/**
 * The Quotation on the inquiry screen.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Quotation;

use Linker\Commerce\Account\PrivateFiles;
use Linker\Commerce\Registration\AccountsAdmin;
use Linker\Commerce\Registration\Approval;
use Linker\Commerce\Registration\VatProfile;
use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Vocabulary\LocaleFormat;
use RuntimeException;
use WC_Admin_Meta_Boxes;
use WC_Order;
use WP_Post;

/**
 * On the inquiry screen staff find one action, "Issue Quotation", in a box
 * that afterwards shows the number, the validity and the PDF. The inquiry list
 * gets a Quotation column. WooCommerce's other order actions (resend order
 * details, regenerate downloads) do not apply to inquiries and are removed
 * (docs/specs/11-commerce.md, journey step 5: "无其他动作").
 */
final class AdminBox {

	/**
	 * Name of the button that issues the Quotation.
	 */
	public const BUTTON  = 'linker_issue_quotation';
	private const REVISE = 'linker_revise_quotation';

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
			add_meta_box( 'linker-quotation', __( 'Quotation', 'linker-commerce' ), array( $this, 'render' ), $screen, 'side', 'high' );
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
		$this->account_context( $order );
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
				esc_url( $this->pdf_url( $order, 'download' ) ),
				esc_html__( 'Download PDF', 'linker-commerce' )
			);
		}
		if ( ! in_array( $order->get_status(), array( Statuses::RECEIVED, Statuses::QUOTATION ), true ) ) {
			return;
		}
		if ( ! $order->get_billing_address_1() || ! $order->get_billing_city() || ! $order->get_billing_postcode() ) {
			echo '<p>' . esc_html__( 'The billing address is incomplete. You can add it under Billing.', 'linker-commerce' ) . '</p>';
		}
		if ( ! $order->get_meta( '_' . VatProfile::VAT_META ) ) {
			echo '<p>' . esc_html__( 'No buyer VAT ID is recorded. Add it under Billing if available.', 'linker-commerce' ) . '</p>';
		}
		printf( '<p><a class="button" href="%s" target="_blank" rel="noopener">%s</a></p>', esc_url( $this->pdf_url( $order, 'preview' ) ), esc_html__( 'Preview PDF', 'linker-commerce' ) );
		$blocker = '' === $number ? $this->issuer->blocker( $order ) : $this->issuer->revision_blocker( $order, $number );
		if ( '' !== $blocker ) {
			printf( '<p>%s</p>', esc_html( $blocker ) );
			return;
		}
		if ( $order->get_customer_id() > 0 ) {
			echo '<p>' . esc_html__( 'Save your changes to prices and quantities, then issue the Quotation. The customer receives an email with the link.', 'linker-commerce' ) . '</p>';
		} else {
			echo '<p>' . esc_html__( 'Issue the PDF for offline delivery. Download it here and send it to the guest yourself.', 'linker-commerce' ) . '</p>';
		}
		if ( '' !== $number ) {
			wp_nonce_field( self::REVISE . $order->get_id() . $number, '_linker_revision_nonce', false );
		}
		printf(
			'<p><button type="submit" class="button button-primary" name="%1$s" value="%2$s">%3$s</button></p>',
			esc_attr( '' === $number ? self::BUTTON : self::REVISE ),
			esc_attr( '' === $number ? '1' : $number ),
			'' === $number ? esc_html__( 'Issue Quotation', 'linker-commerce' ) : esc_html__( 'Issue revised Quotation', 'linker-commerce' )
		);
	}

	/**
	 * Display ownership separately from a guest's matching email address.
	 *
	 * @param WC_Order $order Inquiry.
	 */
	private function account_context( WC_Order $order ): void {
		$id = $order->get_customer_id();
		if ( ! $id ) {
			echo '<p><strong>' . esc_html__( 'Guest inquiry', 'linker-commerce' ) . '</strong></p>';
		}
		$user = $id ? get_userdata( $id ) : get_user_by( 'email', $order->get_billing_email() );
		if ( $user instanceof \WP_User ) {
			$status = ( new Approval() )->status( $user->ID );
			$label  = Approval::PENDING === $status ? __( 'Pending approval', 'linker-commerce' ) : Approval::label( $status );
			if ( ! $id ) {
				echo '<p>' . esc_html__( 'An account uses this email address. This inquiry is still unlinked.', 'linker-commerce' ) . '</p>';
			}
			printf( '<p>%s<br><mark class="order-status"><span>%s</span></mark></p>', esc_html( $user->user_email ), esc_html( $label ) );
			if ( current_user_can( 'edit_users' ) && current_user_can( 'edit_user', $user->ID ) ) {
				printf( '<p><a href="%s">%s</a></p>', esc_url( AccountsAdmin::url( $user->ID ) ), esc_html__( 'Review account', 'linker-commerce' ) );
			}
		}
		printf( '<p>VIES: %s</p>', esc_html( VatProfile::label( (string) $order->get_meta( VatProfile::ORDER_STATUS ) ) ) );
	}

	/**
	 * The staff endpoint also serves issued guest PDFs which have no account owner.
	 *
	 * @param WC_Order $order Inquiry.
	 * @param string   $mode Preview or download.
	 */
	private function pdf_url( WC_Order $order, string $mode ): string {
		return add_query_arg(
			array(
				'action'   => 'linker_staff_quotation',
				'order_id' => $order->get_id(),
				'mode'     => $mode,
				'_wpnonce' => wp_create_nonce( 'linker_quotation_' . $mode . $order->get_id() ),
			),
			admin_url( 'admin-post.php' )
		);
	}

	/** Print the saved draft or the private latest issue to authorized order staff. */
	public function pdf(): void {
		$id   = absint( $_GET['order_id'] ?? 0 );
		$mode = isset( $_GET['mode'] ) ? sanitize_key( wp_unslash( $_GET['mode'] ) ) : '';
		if ( ! current_user_can( 'edit_shop_orders' ) || ! in_array( $mode, array( 'preview', 'download' ), true ) ) {
			wp_die( '', '', array( 'response' => 403 ) );
		}
		check_admin_referer( 'linker_quotation_' . $mode . $id );
		$order = wc_get_order( $id );
		if ( ! $order instanceof WC_Order ) {
			wp_die( '', '', array( 'response' => 404 ) );
		}
		$preview = 'preview' === $mode;
		$name    = $preview ? 'quotation-preview' : (string) $order->get_meta( Issuer::NUMBER_META );
		if ( $preview ) {
			$bytes = $this->issuer->preview( $order );
		} else {
			$file = ( new PrivateFiles( Issuer::DIRECTORY ) )->path( (string) $order->get_meta( Issuer::FILE_META ) );
			if ( ! is_file( $file ) ) {
				wp_die( '', '', array( 'response' => 404 ) );
			}
			$bytes = file_get_contents( $file ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- Local private PDF.
		}
		nocache_headers();
		header( 'Content-Type: application/pdf' );
		header( 'Content-Disposition: ' . ( $preview ? 'inline' : 'attachment' ) . '; filename="' . sanitize_file_name( $name ) . '.pdf"' );
		echo $bytes; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Binary PDF.
		exit;
	}

	/**
	 * Issues the Quotation when the button was pressed; runs on
	 * woocommerce_process_shop_order_meta after WooCommerce saved the inquiry's
	 * items and data (its nonce is checked by then).
	 *
	 * @param int $order_id Inquiry.
	 */
	public function process( int $order_id ): void {
		// phpcs:ignore WordPress.Security.NonceVerification.Missing -- WooCommerce verified the order edit nonce before this action.
		if ( ( empty( $_POST[ self::BUTTON ] ) && empty( $_POST[ self::REVISE ] ) ) || ! current_user_can( 'edit_shop_orders' ) ) {
			return;
		}
		$order = wc_get_order( $order_id );
		if ( ! $order instanceof WC_Order ) {
			return;
		}
		try {
			if ( isset( $_POST[ self::REVISE ] ) ) {
				$previous = sanitize_text_field( wp_unslash( $_POST[ self::REVISE ] ) );
				check_admin_referer( self::REVISE . $order_id . $previous, '_linker_revision_nonce' );
				$this->issuer->revise( $order, $previous );
			} else {
				$this->issuer->issue( $order );
			}
		} catch ( RuntimeException $error ) {
			WC_Admin_Meta_Boxes::add_error( esc_html( $error->getMessage() ) );
		}
	}

	/**
	 * Inquiries have no order actions besides the Quotation button; replaces WooCommerce's.
	 *
	 * @return array<string, string>
	 */
	public function order_actions(): array {
		return array();
	}

	/**
	 * Inquiry list columns: "Inquiry" instead of "Order", and the Quotation number.
	 *
	 * @param array<string, string> $columns Column id → heading.
	 * @return array<string, string>
	 */
	public function columns( array $columns ): array {
		$named = array();
		foreach ( $columns as $id => $heading ) {
			$named[ $id ] = 'order_number' === $id ? esc_html__( 'Inquiry', 'linker-commerce' ) : $heading;
			if ( 'order_status' === $id ) {
				$named['linker_quotation'] = esc_html__( 'Quotation', 'linker-commerce' );
			}
		}
		unset( $named['shipping_address'] );
		return $named;
	}

	/**
	 * Prints the Quotation column of an inquiry.
	 *
	 * @param string       $column        Column id.
	 * @param WC_Order|int $order_or_post Inquiry (HPOS) or its post id.
	 */
	public function column( string $column, $order_or_post ): void {
		if ( 'linker_quotation' !== $column ) {
			return;
		}
		$order = $order_or_post instanceof WC_Order ? $order_or_post : wc_get_order( (int) $order_or_post );
		echo esc_html( $order instanceof WC_Order ? (string) $order->get_meta( Issuer::NUMBER_META ) : '' );
	}
}
