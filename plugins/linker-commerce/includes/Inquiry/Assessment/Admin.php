<?php
/**
 * Staff-only observations and a separate human correction.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry\Assessment;

use WC_Order;
use Linker\Commerce\Mail\NotificationHold;

/** Native Woo edit-screen meta box; it changes no inquiry or account status. */
final class Admin {
	public const OVERRIDE = '_linker_inquiry_assessment_override';

	/** Add the box and the protected correction endpoint. */
	public function register(): void {
		add_action( 'add_meta_boxes', array( $this, 'boxes' ) );
		add_action( 'admin_post_linker_inquiry_assessment_correct', array( $this, 'correct' ) );
		add_action( 'admin_post_linker_inquiry_notification_release', array( $this, 'release' ) );
	}

	/** Both native Woo storage modes use the same staff view. */
	public function boxes(): void {
		foreach ( array( 'shop_order', 'woocommerce_page_wc-orders' ) as $screen ) {
			add_meta_box( 'linker-inquiry-assessment', __( 'Inquiry review', 'linker-commerce' ), array( $this, 'box' ), $screen, 'normal' );
		}
	}

	/**
	 * Read-only model evidence; correction has a separate, non-nested form.
	 *
	 * @param mixed $subject Woo order or WP post.
	 */
	public function box( mixed $subject ): void {
		$order = $subject instanceof WC_Order ? $subject : wc_get_order( is_object( $subject ) && isset( $subject->ID ) ? (int) $subject->ID : 0 );
		if ( ! $order instanceof WC_Order || ! current_user_can( 'manage_woocommerce' ) ) {
			return;
		}
		NotificationHoldView::render( $order );
		EvidenceView::render( $order );
		$data = Queue::data( $order );
		if ( array() === $data ) {
			echo '<p>' . esc_html__( 'No assessment was requested.', 'linker-commerce' ) . '</p>';
			return;
		}
		$result = is_array( $data['result'] ?? null ) ? $data['result'] : Result::unknown( 'pending' );
		echo '<h3>' . esc_html__( 'Jev initial assessment', 'linker-commerce' ) . '</h3>';
		echo '<p><strong>' . esc_html( Result::label( (string) $result['label'] ) ) . '</strong><br />' . esc_html( Result::explanation( $result ) ) . '</p>';
		$authorization = AuthorizationStore::read( $order->get_id() );
		echo '<p><strong>' . esc_html__( 'Diagnostic', 'linker-commerce' ) . '</strong>: ' . esc_html( is_array( $authorization ) ? (string) ( $authorization['status'] ?? 'pending' ) : 'authorization_storage_unavailable' ) . '</p>';
		echo '<dl><dt>' . esc_html__( 'Diagnostic', 'linker-commerce' ) . '</dt><dd>' . esc_html( (string) $result['reason'] ) . '</dd><dt>' . esc_html__( 'Elapsed time', 'linker-commerce' ) . '</dt><dd>' . esc_html( number_format_i18n( (float) ( $data['elapsed'] ?? 0 ), 2 ) ) . ' s</dd><dt>' . esc_html__( 'Model / rubric', 'linker-commerce' ) . '</dt><dd>' . esc_html( (string) $result['model'] . ' / ' . (string) $result['rubric'] ) . '</dd></dl>';
		echo '<details><summary>' . esc_html__( 'Original model result', 'linker-commerce' ) . '</summary><textarea readonly class="large-text code" rows="10" aria-label="' . esc_attr__( 'Original model result', 'linker-commerce' ) . '">' . esc_textarea( (string) wp_json_encode( $result['raw'] ?? array(), JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE ) ) . '</textarea></details>';
		ReviewView::render( $order );
	}

	/** Only a staff member with the record-bound nonce can release a hold. */
	public function release(): void {
		$id        = isset( $_POST['inquiry'] ) ? absint( $_POST['inquiry'] ) : 0; // phpcs:ignore WordPress.Security.NonceVerification -- Bound to the record-specific nonce below.
		$reference = isset( $_POST['reference'] ) && is_string( $_POST['reference'] ) ? sanitize_text_field( wp_unslash( $_POST['reference'] ) ) : ''; // phpcs:ignore WordPress.Security.NonceVerification -- Bound into the nonce action below.
		check_admin_referer( 'linker_notification_release_' . $id . '_' . $reference );
		$result = NotificationHold::release( $id, $reference );
		if ( is_wp_error( $result ) ) {
			$status = 'forbidden' === $result->get_error_code() ? 403 : 409;
			wp_die(
				esc_html( $result->get_error_message() ),
				'',
				array(
					'response'  => (int) $status,
					'back_link' => true,
				)
			);
		}
		$order = wc_get_order( $id );
		if ( ! $order instanceof WC_Order ) {
			wp_die( esc_html__( 'This inquiry is unavailable.', 'linker-commerce' ), '', array( 'response' => 404 ) );
		}
		wp_safe_redirect( $order->get_edit_order_url() );
		exit;
	}

	/** Correction preserves raw evidence and emits no email or status change. */
	public function correct(): void {
		$id    = isset( $_POST['inquiry'] ) ? absint( $_POST['inquiry'] ) : 0; // phpcs:ignore WordPress.Security.NonceVerification -- Verified with the record-specific nonce below.
		$basis = isset( $_POST['basis'] ) && is_string( $_POST['basis'] ) ? sanitize_text_field( wp_unslash( $_POST['basis'] ) ) : ''; // phpcs:ignore WordPress.Security.NonceVerification -- This exact reference is bound into the nonce action below.
		check_admin_referer( 'linker_assessment_' . $id . '_' . $basis );
		if ( ! current_user_can( 'manage_woocommerce' ) ) {
			wp_die( esc_html__( 'You cannot review this inquiry.', 'linker-commerce' ), '', array( 'response' => 403 ) );
		}
		$label     = isset( $_POST['label'] ) ? sanitize_key( wp_unslash( $_POST['label'] ) ) : '';
		$note      = isset( $_POST['note'] ) ? sanitize_textarea_field( wp_unslash( $_POST['note'] ) ) : '';
		$revision  = isset( $_POST['revision'] ) ? filter_var( wp_unslash( $_POST['revision'] ), FILTER_VALIDATE_INT ) : false;
		$operation = isset( $_POST['operation'] ) ? sanitize_key( wp_unslash( $_POST['operation'] ) ) : '';
		$source    = isset( $_POST['source'] ) ? sanitize_key( wp_unslash( $_POST['source'] ) ) : '';
		$url       = isset( $_POST['source_url'] ) && is_string( $_POST['source_url'] ) ? esc_url_raw( wp_unslash( $_POST['source_url'] ) ) : '';
		$observed  = isset( $_POST['observed_at'] ) ? sanitize_text_field( wp_unslash( $_POST['observed_at'] ) ) : '';
		$date      = 1 === preg_match( '/\A[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}\z/', $observed ) ? \DateTimeImmutable::createFromFormat( '!Y-m-d\TH:i', $observed, new \DateTimeZone( 'UTC' ) ) : false;
		$at        = false !== $date && $date->format( 'Y-m-d\TH:i' ) === $observed ? $date->getTimestamp() : 0;
		if ( false === $revision || $revision < 0 ) {
			wp_die(
				esc_html__( 'Reload this inquiry before saving a review.', 'linker-commerce' ),
				'',
				array(
					'response'  => 409,
					'back_link' => true,
				)
			);
		}
		$result = Reviews::save(
			$id,
			$revision,
			$operation,
			array(
				'basis'       => $basis,
				'label'       => $label,
				'note'        => $note,
				'source'      => $source,
				'url'         => $url,
				'observed_at' => $at,
			)
		);
		if ( is_wp_error( $result ) ) {
			$status = in_array( $result->get_error_code(), array( 'review_busy', 'review_stale', 'review_write_failed' ), true ) ? 409 : 400;
			wp_die(
				esc_html( $result->get_error_message() ),
				'',
				array(
					'response'  => (int) $status,
					'back_link' => true,
				)
			);
		}
		$order = wc_get_order( $id );
		if ( ! $order instanceof WC_Order ) {
			wp_die( esc_html__( 'This inquiry is unavailable.', 'linker-commerce' ), '', array( 'response' => 404 ) );
		}
		wp_safe_redirect( $order->get_edit_order_url() );
		exit;
	}
}
