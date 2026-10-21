<?php
/**
 * Native staff markup for the three-part evidence card.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry\Assessment;

use Linker\Commerce\Registration\Approval;
use Linker\Commerce\Registration\CustomerRole;
use Linker\Commerce\Registration\VatProfile;
use WC_Order;

/** No client scoring, external lookup, links to untrusted sites, or CSS. */
final class EvidenceView {

	/**
	 * Render only the frozen evidence, never today's account values.
	 *
	 * @param WC_Order $order Inquiry.
	 */
	public static function render( WC_Order $order ): void {
		if ( ! current_user_can( 'manage_woocommerce' ) ) {
			return;
		}
		echo '<h3>' . esc_html__( 'Customer evidence', 'linker-commerce' ) . '</h3>';
		$data = $order->get_meta( CustomerEvidence::META );
		if ( ! is_array( $data ) || ! isset( $data['request'], $data['vat'] ) ) {
			echo '<p>' . esc_html__( 'No frozen customer evidence is available for this inquiry.', 'linker-commerce' ) . '</p>';
			return;
		}
		echo '<p>' . esc_html__( 'Details saved when this inquiry arrived. Account approval remains a staff decision.', 'linker-commerce' ) . '</p>';
		self::field( __( 'Saved at', 'linker-commerce' ), self::date( (int) $data['captured_at'] ), __( 'Site record', 'linker-commerce' ) );
		echo '<h4>' . esc_html__( '1. This request', 'linker-commerce' ) . '</h4>';
		$request = (array) $data['request'];
		$billing = (array) ( $request['billing'] ?? array() );
		$stated  = __( 'Customer statement', 'linker-commerce' );
		$source  = match ( $request['source'] ?? '' ) {
			'contact' => __( 'Contact form', 'linker-commerce' ),
			'proforma' => __( 'Proforma request', 'linker-commerce' ),
			default => '',
		};
		self::field( __( 'Source', 'linker-commerce' ), $source, __( 'Site record', 'linker-commerce' ) );
		$topic = (string) ( $request['topic'] ?? '' );
		self::field(
			__( 'This is about', 'linker-commerce' ),
			'general' === $topic ? __( 'General enquiry (default form option)', 'linker-commerce' ) : ( '' !== $topic ? \Linker\Commerce\Contact\Form::intent_label( $topic ) : '' ),
			'general' === $topic ? __( 'Form value; no selection history recorded', 'linker-commerce' ) : $stated,
			2
		);
		echo '<details><summary>' . esc_html__( 'Contact details as submitted', 'linker-commerce' ) . '</summary>';
		self::field( __( 'Name', 'linker-commerce' ), trim( (string) ( $billing['first_name'] ?? '' ) . ' ' . (string) ( $billing['last_name'] ?? '' ) ), $stated );
		self::field( __( 'Email', 'linker-commerce' ), (string) ( $billing['email'] ?? '' ), $stated );
		self::field( __( 'Company', 'linker-commerce' ), (string) ( $billing['company'] ?? '' ), $stated );
		echo '</details>';
		self::field( __( 'Message', 'linker-commerce' ), (string) ( $request['message'] ?? '' ), $stated, 4 );
		foreach ( (array) ( $data['products'] ?? array() ) as $product ) {
			self::field( __( 'Product', 'linker-commerce' ), (string) $product['name'] . ' × ' . (string) $product['quantity'], __( 'Products in the submitted solution draft', 'linker-commerce' ) );
		}
		self::context( (array) ( $data['context'] ?? array() ) );
		echo '<h4>' . esc_html__( '2. Company and account records', 'linker-commerce' ) . '</h4>';
		$account = (array) ( $data['account'] ?? array() );
		if ( array() === $account ) {
			echo '<p>' . esc_html( 'unavailable' === ( $data['account_record'] ?? '' ) ? __( 'The linked account record was unavailable when this inquiry arrived.', 'linker-commerce' ) : __( 'Guest inquiry. An account and VAT ID are optional.', 'linker-commerce' ) ) . '</p>';
		} else {
			echo '<details><summary>' . esc_html__( 'Saved account details', 'linker-commerce' ) . '</summary>';
			$saved = __( 'Account value at submission; supplied by the customer', 'linker-commerce' );
			self::field( __( 'Company', 'linker-commerce' ), (string) $account['company'], $saved );
			self::field( __( 'Company website', 'linker-commerce' ), (string) $account['website'], $saved );
			self::field( __( 'Business type', 'linker-commerce' ), CustomerRole::label( (string) $account['role'] ), $saved );
			self::field( __( 'Country', 'linker-commerce' ), (string) $account['country'], $saved );
			$approval = (array) $account['approval'];
			self::field( __( 'Account status', 'linker-commerce' ), Approval::label( (string) $approval['status'] ), __( 'Site decision; this does not verify company identity', 'linker-commerce' ) );
			$change = (array) $approval['change'];
			self::field( __( 'Decision recorded at', 'linker-commerce' ), self::date( (int) $change['at'] ), __( 'Site record', 'linker-commerce' ) );
			self::field( __( 'Staff user ID', 'linker-commerce' ), (int) $change['by'] > 0 ? (string) $change['by'] : '', __( 'Site record', 'linker-commerce' ) );
			self::field( __( 'Recorded reason', 'linker-commerce' ), (string) $approval['reason'], __( 'Site record', 'linker-commerce' ), 2 );
			echo '</details>';
		}
		$vat = (array) $data['vat'];
		echo '<details><summary>' . esc_html__( 'VAT numbers and check records', 'linker-commerce' ) . '</summary>';
		self::field( __( 'VAT ID in this request', 'linker-commerce' ), (string) $vat['submitted'], $stated );
		self::field( __( 'VAT ID saved on the account', 'linker-commerce' ), (string) $vat['account_number'], $stated );
		self::field( __( 'VAT ID actually checked', 'linker-commerce' ), (string) $vat['checked_number'], __( 'Recorded VAT check', 'linker-commerce' ) );
		self::field( __( 'Original check time', 'linker-commerce' ), self::date( (int) $vat['checked_at'] ), __( 'Recorded VAT check', 'linker-commerce' ) );
		self::field( __( 'Recorded check result', 'linker-commerce' ), '' !== $vat['status'] ? VatProfile::label( (string) $vat['status'] ) : '', __( 'Recorded VAT check', 'linker-commerce' ) );
		self::field( __( 'VAT result on this inquiry', 'linker-commerce' ), '' !== $vat['order_status'] ? VatProfile::label( (string) $vat['order_status'] ) : '', __( 'Site record', 'linker-commerce' ) );
		self::field( __( 'Check detail', 'linker-commerce' ), (string) $vat['detail'], __( 'Recorded VAT check', 'linker-commerce' ), 2 );
		echo '</details>';
		echo '<h4>' . esc_html__( '3. Points to review', 'linker-commerce' ) . '</h4><p>' . esc_html( self::vat_message( CustomerEvidence::vat_state( $vat ) ) ) . '</p>';
		if ( '' !== ( $billing['company'] ?? '' ) && '' !== ( $account['company'] ?? '' ) && 0 !== strcasecmp( trim( (string) $billing['company'] ), trim( (string) $account['company'] ) ) ) {
			echo '<p>' . esc_html__( 'The company name in this request differs from the saved account value. Both are shown above.', 'linker-commerce' ) . '</p>';
		}
		echo '<p>' . esc_html__( 'No automatic company lookup was made. Missing optional details are not a spam finding.', 'linker-commerce' ) . '</p>';
		echo '<details><summary>' . esc_html__( 'Frozen source references', 'linker-commerce' ) . '</summary><ul>';
		foreach ( array( 'request', 'products', 'context', 'account', 'vat' ) as $key ) {
			echo '<li><code>' . esc_html( CustomerEvidence::reference( $key, $data[ $key ] ?? array() ) ) . '</code></li>';
		}
		echo '</ul><p>' . esc_html__( 'References identify the saved record. They do not verify a company.', 'linker-commerce' ) . '</p></details>';
	}

	/**
	 * Explicit labels keep unavailable, invalid and missing evidence separate.
	 *
	 * @param string $state Evidence state.
	 */
	public static function vat_message( string $state ): string {
		return match ( $state ) {
			'valid_at_check' => __( 'The recorded VAT check was valid for the number and time shown. It does not verify the contact person or authority to buy.', 'linker-commerce' ),
			'invalid_at_check' => __( 'The recorded VAT check returned invalid. Review the number with the customer; this is not a spam decision.', 'linker-commerce' ),
			'number_differs' => __( 'The submitted, saved or checked VAT numbers differ. The stored result cannot confirm the current number.', 'linker-commerce' ),
			'status_differs' => __( 'The request and account VAT results differ. Review the underlying records before relying on either result.', 'linker-commerce' ),
			'provenance_incomplete' => __( 'The checked number or original check time is missing. VAT verification cannot be confirmed.', 'linker-commerce' ),
			'outside_scope' => __( 'This number is outside the EU VIES check. Company verification remains open.', 'linker-commerce' ),
			'not_provided' => __( 'No VAT ID was provided. It is optional for this inquiry.', 'linker-commerce' ),
			default => __( 'VAT verification was unavailable or inconclusive. Review the recorded detail if needed.', 'linker-commerce' ),
		};
	}

	/**
	 * Related messages preserve customer versus AI attribution.
	 *
	 * @param array<string, mixed> $context Frozen, ownership-checked context.
	 */
	private static function context( array $context ): void {
		if ( 'available' !== ( $context['status'] ?? '' ) ) {
			echo '<p>' . esc_html__( 'No related Genie context was available at submission.', 'linker-commerce' ) . '</p>';
			return;
		}
		echo '<details><summary>' . esc_html__( 'Related Genie context at submission', 'linker-commerce' ) . '</summary>';
		foreach ( (array) ( $context['conversation'] ?? array() ) as $message ) {
			$source = 'assistant' === $message['role'] ? __( 'Genie AI response', 'linker-commerce' ) : __( 'Customer statement', 'linker-commerce' );
			self::field( $source, (string) $message['content'], $source, 4 );
		}
		if ( array() !== ( $context['attachments'] ?? array() ) ) {
			self::field( __( 'Attachment readings', 'linker-commerce' ), (string) wp_json_encode( $context['attachments'], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE ), __( 'AI extraction from customer attachments; verify against the original', 'linker-commerce' ), 6 );
		}
		echo '</details>';
	}

	/**
	 * Native large-text controls contain even unbroken spam text on phones.
	 *
	 * @param string $label Field label.
	 * @param string $value Untrusted plain value.
	 * @param string $source Source kind.
	 * @param int    $rows Native textarea rows, presentation only.
	 */
	private static function field( string $label, string $value, string $source, int $rows = 1 ): void {
		echo '<p><label><strong>' . esc_html( $label ) . '</strong><br /><textarea readonly class="large-text" rows="' . esc_attr( (string) $rows ) . '">' . esc_textarea( '' !== $value ? $value : __( 'Not recorded', 'linker-commerce' ) ) . '</textarea></label><br /><small>' . esc_html( $source ) . '</small></p>';
	}

	/**
	 * UTC is explicit so old check times are never mistaken for a new check.
	 *
	 * @param int $at Original epoch, zero means absent.
	 */
	public static function date( int $at ): string {
		return $at > 0 ? gmdate( 'Y-m-d H:i:s', $at ) . ' UTC' : '';
	}
}
