<?php
/**
 * Local, frozen customer evidence; never part of the provider request.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry\Assessment;

use Linker\Commerce\Registration\Approval;
use Linker\Commerce\Registration\CustomerRole;
use Linker\Commerce\Registration\VatNumber;
use Linker\Commerce\Registration\VatProfile;
use Linker\Commerce\Registration\Website;
use WC_Order;

/** Reads existing records only, without a VIES, website or model request. */
final class CustomerEvidence {

	public const META = '_linker_inquiry_customer_evidence';

	/**
	 * Freeze current account values alongside the accepted request.
	 *
	 * @param WC_Order             $order Accepted inquiry.
	 * @param array<string, mixed> $snapshot Existing owned business context.
	 * @param float                $at Acceptance timestamp.
	 * @return array<string, mixed>
	 */
	public static function capture( WC_Order $order, array $snapshot, float $at ): array {
		$id       = $order->get_customer_id();
		$present  = get_user_by( 'id', $id ) instanceof \WP_User;
		$approval = new Approval();
		$account  = $present ? array(
			'id'       => $id,
			'company'  => (string) get_user_meta( $id, 'billing_company', true ),
			'country'  => (string) get_user_meta( $id, 'billing_country', true ),
			'website'  => (string) get_user_meta( $id, Website::META, true ),
			'role'     => (string) get_user_meta( $id, CustomerRole::META, true ),
			'approval' => array(
				'status' => $approval->status( $id ),
				'reason' => $approval->reason( $id ),
				'change' => $approval->changed_by( $id ),
			),
		) : array();
		return array(
			'captured_at'    => $at,
			'account_record' => 0 === $id ? 'guest' : ( $present ? 'available' : 'unavailable' ),
			'request'        => $snapshot['submission'] ?? array(),
			'products'       => $snapshot['products'] ?? array(),
			'context'        => $snapshot['context'] ?? array( 'status' => 'unavailable' ),
			'account'        => $account,
			'vat'            => array(
				'submitted'      => (string) $order->get_meta( '_billing_vat_id' ),
				'order_status'   => (string) $order->get_meta( VatProfile::ORDER_STATUS ),
				'account_number' => $present ? (string) get_user_meta( $id, VatProfile::VAT_META, true ) : '',
				'checked_number' => $present ? (string) get_user_meta( $id, VatProfile::NUMBER_META, true ) : '',
				'checked_at'     => $present ? (int) get_user_meta( $id, VatProfile::CHECKED_META, true ) : 0,
				'status'         => $present ? (string) get_user_meta( $id, VatProfile::STATUS_META, true ) : '',
				'detail'         => $present ? (string) get_user_meta( $id, VatProfile::DETAIL_META, true ) : '',
			),
		);
	}

	/**
	 * Interpret only exact number-bound evidence, with no invented expiry.
	 *
	 * @param array<string, mixed> $vat Frozen VAT fields.
	 */
	public static function vat_state( array $vat ): string {
		$submitted = VatNumber::normalize( (string) ( $vat['submitted'] ?? '' ) );
		$saved     = VatNumber::normalize( (string) ( $vat['account_number'] ?? '' ) );
		$checked   = VatNumber::normalize( (string) ( $vat['checked_number'] ?? '' ) );
		$target    = '' !== $submitted ? $submitted : $saved;
		if ( '' === $target ) {
			return 'not_provided';
		}
		if ( ( '' !== $submitted && '' !== $saved && $submitted !== $saved ) || ( '' !== $checked && $checked !== $target ) ) {
			return 'number_differs';
		}
		if ( '' === $checked || (int) ( $vat['checked_at'] ?? 0 ) <= 0 ) {
			return 'provenance_incomplete';
		}
		$order_status = (string) ( $vat['order_status'] ?? '' );
		if ( '' !== $submitted && in_array( $order_status, array( VatProfile::VALID, VatProfile::INVALID ), true ) && ( $vat['status'] ?? '' ) !== $order_status ) {
			return 'status_differs';
		}
		if ( VatProfile::NOT_EU === ( $vat['detail'] ?? '' ) ) {
			return 'outside_scope';
		}
		return match ( $vat['status'] ?? '' ) {
			VatProfile::VALID => 'valid_at_check',
			VatProfile::INVALID => 'invalid_at_check',
			default => 'unverified',
		};
	}

	/**
	 * Fixed source references bind a displayed record to the frozen value.
	 * This hash is a reference, not authentication of a company's identity.
	 *
	 * @param string $path Field in the frozen evidence.
	 * @param mixed  $value Frozen value.
	 */
	public static function reference( string $path, mixed $value ): string {
		return $path . ' · ' . substr( hash( 'sha256', (string) wp_json_encode( $value ) ), 0, 12 );
	}
}
