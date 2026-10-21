<?php
/**
 * Staff-only observations and a separate human correction.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry\Assessment;

use WC_Order;

/** Native Woo edit-screen meta box; it changes no inquiry or account status. */
final class Admin {
	public const OVERRIDE = '_linker_inquiry_assessment_override';

	/** Add the box and the protected correction endpoint. */
	public function register(): void {
		add_action( 'add_meta_boxes', array( $this, 'boxes' ) );
		add_action( 'admin_post_linker_inquiry_assessment_correct', array( $this, 'correct' ) );
	}

	/** Both native Woo storage modes use the same staff view. */
	public function boxes(): void {
		foreach ( array( 'shop_order', 'woocommerce_page_wc-orders' ) as $screen ) {
			add_meta_box( 'linker-inquiry-assessment', __( 'Jev initial assessment', 'linker-commerce' ), array( $this, 'box' ), $screen, 'normal' );
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
		$data = Queue::data( $order );
		if ( array() === $data ) {
			echo '<p>' . esc_html__( 'No assessment was requested.', 'linker-commerce' ) . '</p>';
			return;
		}
		$result = is_array( $data['result'] ?? null ) ? $data['result'] : Result::unknown( 'pending' );
		echo '<p><strong>' . esc_html( Result::label( (string) $result['label'] ) ) . '</strong><br />' . esc_html( Result::explanation( $result ) ) . '</p>';
		echo '<p>' . esc_html__( 'Initial guidance only. Every inquiry is accepted and notified.', 'linker-commerce' ) . '</p>';
		echo '<dl><dt>' . esc_html__( 'Diagnostic', 'linker-commerce' ) . '</dt><dd>' . esc_html( (string) $result['reason'] ) . '</dd><dt>' . esc_html__( 'Elapsed time', 'linker-commerce' ) . '</dt><dd>' . esc_html( number_format_i18n( (float) ( $data['elapsed'] ?? 0 ), 2 ) ) . ' s</dd><dt>' . esc_html__( 'Model / rubric', 'linker-commerce' ) . '</dt><dd>' . esc_html( (string) $result['model'] . ' / ' . (string) $result['rubric'] ) . '</dd></dl>';
		echo '<details><summary>' . esc_html__( 'Original model result', 'linker-commerce' ) . '</summary><textarea readonly class="large-text code" rows="10" aria-label="' . esc_attr__( 'Original model result', 'linker-commerce' ) . '">' . esc_textarea( (string) wp_json_encode( $result['raw'] ?? array(), JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE ) ) . '</textarea></details>';
		$override = $order->get_meta( self::OVERRIDE );
		if ( is_array( $override ) ) {
			echo '<p><strong>' . esc_html__( 'Staff correction', 'linker-commerce' ) . ': ' . esc_html( Result::label( (string) $override['label'] ) ) . '</strong><br />' . esc_html( (string) $override['note'] ) . '</p>';
		}
		// These controls belong to an external form emitted after Woo's form.
		$id = 'linker-assessment-correction-' . $order->get_id();
		echo '<p><label>' . esc_html__( 'Staff correction', 'linker-commerce' ) . ' <select form="' . esc_attr( $id ) . '" name="label">';
		foreach ( array( 'uncertain', 'normal', 'suspected_spam' ) as $label ) {
			echo '<option value="' . esc_attr( $label ) . '"' . selected( is_array( $override ) ? (string) $override['label'] : 'uncertain', $label, false ) . '>' . esc_html( Result::label( $label ) ) . '</option>';
		}
		echo '</select></label></p><p><label>' . esc_html__( 'Review note', 'linker-commerce' ) . '<br /><textarea form="' . esc_attr( $id ) . '" name="note" rows="2">' . esc_textarea( is_array( $override ) ? (string) $override['note'] : '' ) . '</textarea></label></p>';
		echo '<button class="button" type="submit" form="' . esc_attr( $id ) . '">' . esc_html__( 'Save correction', 'linker-commerce' ) . '</button>';
		add_action(
			'admin_footer',
			static function () use ( $order, $id ): void {
				echo '<form id="' . esc_attr( $id ) . '" method="post" action="' . esc_url( admin_url( 'admin-post.php' ) ) . '"><input type="hidden" name="action" value="linker_inquiry_assessment_correct" /><input type="hidden" name="inquiry" value="' . esc_attr( (string) $order->get_id() ) . '" />';
				wp_nonce_field( 'linker_assessment_' . $order->get_id() );
				echo '</form>';
			}
		);
	}

	/** Correction preserves raw evidence and emits no email or status change. */
	public function correct(): void {
		$id = isset( $_POST['inquiry'] ) ? absint( $_POST['inquiry'] ) : 0; // phpcs:ignore WordPress.Security.NonceVerification -- Verified with the record-specific nonce below.
		check_admin_referer( 'linker_assessment_' . $id );
		if ( ! current_user_can( 'manage_woocommerce' ) ) {
			wp_die( esc_html__( 'You cannot review this inquiry.', 'linker-commerce' ), '', array( 'response' => 403 ) );
		}
		$label = isset( $_POST['label'] ) ? sanitize_key( wp_unslash( $_POST['label'] ) ) : '';
		$note  = isset( $_POST['note'] ) ? sanitize_textarea_field( wp_unslash( $_POST['note'] ) ) : '';
		$order = wc_get_order( $id );
		if ( ! $order instanceof WC_Order || ! in_array( $label, array( 'normal', 'suspected_spam', 'uncertain' ), true ) ) {
			wp_die( esc_html__( 'Please choose a valid assessment.', 'linker-commerce' ), '', array( 'response' => 400 ) );
		}
		$order->update_meta_data(
			self::OVERRIDE,
			array(
				'label' => $label,
				'note'  => $note,
				'user'  => get_current_user_id(),
				'at'    => time(),
			)
		);
		$order->save_meta_data();
		wp_safe_redirect( $order->get_edit_order_url() );
		exit;
	}
}
