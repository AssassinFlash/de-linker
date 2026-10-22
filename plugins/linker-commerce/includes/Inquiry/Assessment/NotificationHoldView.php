<?php
/**
 * Native staff controls for a retained notification.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry\Assessment;

use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\NotificationHold;
use WC_Order;

/** The separate footer form avoids nesting inside Woo's order editor form. */
final class NotificationHoldView {
	/**
	 * Show the independent notification state without changing model evidence.
	 *
	 * @param WC_Order $order Staff-visible native inquiry.
	 */
	public static function render( WC_Order $order ): void {
		$released = $order->get_meta( NotificationHold::RELEASED );
		if ( ! NotificationHold::held( $order ) ) {
			if ( is_array( $released ) ) {
				echo '<h3>' . esc_html__( 'Internal notification', 'linker-commerce' ) . '</h3><p><strong>' . esc_html__( 'Released for delivery', 'linker-commerce' ) . '</strong><br />' . esc_html( EvidenceView::date( (int) ( $released['at'] ?? 0 ) ) ) . '</p>';
			}
			return;
		}
		$job  = (int) ( Queue::data( $order )['notification_job'] ?? 0 );
		$hold = $order->get_meta( NotificationHold::META );
		$hold = is_array( $hold ) ? $hold : get_post_meta( $job, NotificationHold::META, true );
		$hold = is_array( $hold ) ? $hold : array();
		echo '<h3>' . esc_html__( 'Internal notification', 'linker-commerce' ) . '</h3><p><strong>' . esc_html__( 'Notification on hold', 'linker-commerce' ) . '</strong></p>';
		echo '<p>' . esc_html( $order->get_meta( \Linker\Commerce\Protection\Intake::META ) ? __( 'The complete inquiry is saved for review. Releasing it queues one internal notification. No customer acknowledgement will be sent.', 'linker-commerce' ) : __( 'The inquiry and its original notification are retained. Releasing the notification queues the same message for delivery.', 'linker-commerce' ) ) . '</p>';
		echo '<dl><dt>' . esc_html__( 'Held since', 'linker-commerce' ) . '</dt><dd>' . esc_html( EvidenceView::date( (int) ( $hold['at'] ?? 0 ) ) ) . '</dd><dt>' . esc_html__( 'Hold reason', 'linker-commerce' ) . '</dt><dd>' . esc_html( 'confirmed_campaign_notification_hold' === ( $hold['reason'] ?? '' ) ? __( 'Confirmed abuse campaign', 'linker-commerce' ) : (string) ( $hold['reason'] ?? '' ) ) . '</dd><dt>' . esc_html__( 'Original notification ID', 'linker-commerce' ) . '</dt><dd>' . esc_html( (string) $job ) . '</dd></dl>';
		if ( ! $order->get_meta( \Linker\Commerce\Protection\Intake::META ) && ( null === ( new JobStore() )->load( $job ) || 'private' !== get_post_status( $job ) ) ) {
			echo '<p>' . esc_html__( 'The original notification is unavailable. It has not been recreated.', 'linker-commerce' ) . '</p>';
			return;
		}
		$id        = 'linker-notification-release-' . $order->get_id();
		$reference = NotificationHold::reference( $order );
		echo '<p><button class="button" type="submit" form="' . esc_attr( $id ) . '">' . esc_html__( 'Release this notification', 'linker-commerce' ) . '</button></p>';
		add_action(
			'admin_footer',
			static function () use ( $order, $id, $reference ): void {
				echo '<form id="' . esc_attr( $id ) . '" method="post" action="' . esc_url( admin_url( 'admin-post.php' ) ) . '"><input type="hidden" name="action" value="linker_inquiry_notification_release" /><input type="hidden" name="inquiry" value="' . esc_attr( (string) $order->get_id() ) . '" /><input type="hidden" name="reference" value="' . esc_attr( $reference ) . '" />';
				wp_nonce_field( 'linker_notification_release_' . $order->get_id() . '_' . $reference );
				echo '</form>';
			}
		);
	}
}
