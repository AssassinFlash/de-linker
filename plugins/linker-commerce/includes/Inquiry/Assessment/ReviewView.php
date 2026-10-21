<?php
/**
 * Staff correction controls and their private event history.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry\Assessment;

use WC_Order;

/** Controls use an external form, avoiding Woo's surrounding order form. */
final class ReviewView {

	/**
	 * Render the current correction and protected revisioned controls.
	 *
	 * @param WC_Order $order Inquiry.
	 */
	public static function render( WC_Order $order ): void {
		if ( $order->get_meta( Reviews::ERASED ) ) {
			return;
		}
		$override = $order->get_meta( Admin::OVERRIDE );
		if ( is_array( $override ) ) {
			echo '<p><strong>' . esc_html__( 'Staff correction', 'linker-commerce' ) . ': ' . esc_html( Result::label( (string) $override['label'] ) ) . '</strong></p>';
			echo '<textarea readonly class="large-text" rows="2" aria-label="' . esc_attr__( 'Recorded review note', 'linker-commerce' ) . '">' . esc_textarea( (string) $override['note'] ) . '</textarea>';
		}
		$id       = 'linker-assessment-correction-' . $order->get_id();
		$revision = (int) Reviews::state( $order )['revision'];
		$basis    = Reviews::reference( $order );
		echo '<h3>' . esc_html__( 'Staff review', 'linker-commerce' ) . '</h3><p>' . esc_html__( 'Saving a review changes this internal record only. It does not send mail or change the account decision.', 'linker-commerce' ) . '</p>';
		echo '<p><label>' . esc_html__( 'Staff correction', 'linker-commerce' ) . ' <select form="' . esc_attr( $id ) . '" name="label">';
		foreach ( array( 'uncertain', 'normal', 'suspected_spam' ) as $label ) {
			echo '<option value="' . esc_attr( $label ) . '"' . selected( is_array( $override ) ? (string) $override['label'] : 'uncertain', $label, false ) . '>' . esc_html( Result::label( $label ) ) . '</option>';
		}
		echo '</select></label></p><p><label>' . esc_html__( 'Review note', 'linker-commerce' ) . '<br /><textarea class="large-text" form="' . esc_attr( $id ) . '" name="note" rows="3"></textarea></label></p>';
		echo '<p><button class="button" type="submit" form="' . esc_attr( $id ) . '" name="operation" value="correct">' . esc_html__( 'Save correction', 'linker-commerce' ) . '</button> <button class="button" type="submit" form="' . esc_attr( $id ) . '" name="operation" value="withdraw">' . esc_html__( 'Withdraw correction', 'linker-commerce' ) . '</button></p>';
		echo '<details><summary>' . esc_html__( 'Add a source you checked', 'linker-commerce' ) . '</summary><p>' . esc_html__( 'Record your source and finding in the review note. The website does not check this source automatically.', 'linker-commerce' ) . '</p><p><label>' . esc_html__( 'Source type', 'linker-commerce' ) . ' <select form="' . esc_attr( $id ) . '" name="source">';
		foreach ( self::sources() as $key => $label ) {
			echo '<option value="' . esc_attr( $key ) . '">' . esc_html( $label ) . '</option>';
		}
		echo '</select></label></p><p><label>' . esc_html__( 'Source URL', 'linker-commerce' ) . '<br /><input class="large-text" type="url" form="' . esc_attr( $id ) . '" name="source_url" /></label></p><p><label>' . esc_html__( 'Checked at (UTC)', 'linker-commerce' ) . '<br /><input type="datetime-local" form="' . esc_attr( $id ) . '" name="observed_at" /></label></p><button class="button" type="submit" form="' . esc_attr( $id ) . '" name="operation" value="evidence">' . esc_html__( 'Record source and finding', 'linker-commerce' ) . '</button></details>';
		self::history( $order );
		add_action(
			'admin_footer',
			static function () use ( $order, $id, $revision, $basis ): void {
				echo '<form id="' . esc_attr( $id ) . '" method="post" action="' . esc_url( admin_url( 'admin-post.php' ) ) . '"><input type="hidden" name="action" value="linker_inquiry_assessment_correct" /><input type="hidden" name="inquiry" value="' . esc_attr( (string) $order->get_id() ) . '" /><input type="hidden" name="revision" value="' . esc_attr( (string) $revision ) . '" />';
				echo '<input type="hidden" name="basis" value="' . esc_attr( $basis ) . '" />';
				wp_nonce_field( 'linker_assessment_' . $order->get_id() . '_' . $basis );
				echo '</form>';
			}
		);
	}

	/**
	 * Native private notes hold events; raw free text stays in protected metadata.
	 *
	 * @param WC_Order $order Inquiry.
	 */
	private static function history( WC_Order $order ): void {
		echo '<details><summary>' . esc_html__( 'Review history', 'linker-commerce' ) . '</summary><ol>';
		$labels = array(
			'correct'  => __( 'Correction recorded', 'linker-commerce' ),
			'withdraw' => __( 'Correction withdrawn', 'linker-commerce' ),
			'evidence' => __( 'Source recorded by staff', 'linker-commerce' ),
			'legacy'   => __( 'Earlier correction; detailed history starts here', 'linker-commerce' ),
		);
		foreach ( Reviews::history( $order ) as $event ) {
			echo '<li><strong>' . esc_html( $labels[ (string) $event['operation'] ] ?? '' ) . '</strong><p>' . esc_html( EvidenceView::date( (int) $event['at'] ) ) . ' · ' . esc_html__( 'Staff user ID', 'linker-commerce' ) . ': ' . esc_html( (string) $event['user'] ) . '</p>';
			if ( isset( $event['basis'], $event['previous'] ) ) {
				echo '<p>' . esc_html__( 'Previous assessment', 'linker-commerce' ) . ': ' . esc_html( Result::label( (string) $event['previous']['label'] ) ) . '</p><details><summary>' . esc_html__( 'Observation and evidence used for this review', 'linker-commerce' ) . '</summary><textarea readonly class="large-text code" rows="6" aria-label="' . esc_attr__( 'Observation and evidence used for this review', 'linker-commerce' ) . '">' . esc_textarea( (string) wp_json_encode( $event['basis'], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE ) ) . '</textarea></details>';
			}
			if ( '' !== ( $event['label'] ?? '' ) ) {
				echo '<p>' . esc_html( Result::label( (string) $event['label'] ) ) . '</p>';
			}
			if ( 'evidence' === $event['operation'] ) {
				echo '<p>' . esc_html( self::sources()[ (string) $event['source'] ] ?? '' ) . ' · ' . esc_html( EvidenceView::date( (int) $event['observed_at'] ) ) . '</p><textarea readonly class="large-text" rows="2" aria-label="' . esc_attr__( 'Source URL', 'linker-commerce' ) . '">' . esc_textarea( (string) $event['url'] ) . '</textarea>';
			}
			echo '<textarea readonly class="large-text" rows="3" aria-label="' . esc_attr__( 'Recorded review note', 'linker-commerce' ) . '">' . esc_textarea( (string) $event['note'] ) . '</textarea></li>';
		}
		echo '</ol></details>';
	}

	/**
	 * Staff-declared source category; none is promoted to an automatic check.
	 *
	 * @return array<string, string>
	 */
	private static function sources(): array {
		return array(
			'company_website'   => __( 'Company website', 'linker-commerce' ),
			'official_registry' => __( 'Official register', 'linker-commerce' ),
			'official_vat'      => __( 'Official VAT service', 'linker-commerce' ),
			'other'             => __( 'Other source', 'linker-commerce' ),
		);
	}
}
