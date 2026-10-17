<?php
/**
 * A customer's VAT ID and its VIES verdict.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration;

use WC_Order;

/**
 * The one place that checks a customer's VAT ID and keeps the verdict. A number
 * is checked when it is new or changed, never again for the same number, and
 * the team hears about it only when the verdict changes (docs/specs/11-commerce.md,
 * Mail; mail-root-cause.md §5 M5). A failed or impossible check never blocks the
 * customer; the account is flagged instead.
 */
final class VatProfile {

	/**
	 * Verdicts.
	 */
	public const VALID      = 'valid';
	public const INVALID    = 'invalid';
	public const UNVERIFIED = 'unverified';
	public const NONE       = 'none';

	/**
	 * Customer meta: the VAT ID is WooCommerce's billing field billing_vat_id
	 * (BillingVatField); the verdict, its detail, the number it is for and when.
	 */
	public const VAT_META       = 'billing_vat_id';
	public const STATUS_META    = 'linker_vat_status';
	public const DETAIL_META    = 'linker_vat_detail';
	public const NUMBER_META    = 'linker_vat_checked_number';
	public const CHECKED_META   = 'linker_vat_checked_at';
	public const ORDER_STATUS   = '_linker_vat_status';
	public const CHANGED_ACTION = 'linker_commerce_vat_status_changed';

	/**
	 * Detail of a number VIES cannot check because it is not an EU VAT ID.
	 */
	public const NOT_EU = 'not an EU VAT ID';

	/**
	 * Sets up the profile.
	 *
	 * @param ViesClient $vies The VIES client.
	 */
	public function __construct( private readonly ViesClient $vies ) {}

	/**
	 * Checks the customer's VAT ID if it is new or changed, or if VIES could not
	 * answer last time, and keeps the verdict.
	 *
	 * @param int    $user_id Customer.
	 * @param string $input   VAT ID as entered.
	 * @param bool   $notify  Whether a changed verdict is announced (false at registration,
	 *                        whose notification carries the first verdict).
	 * @return string The verdict.
	 */
	public function update( int $user_id, string $input, bool $notify ): string {
		$normalized = VatNumber::normalize( $input );
		$previous   = $this->status( $user_id );
		if ( $this->is_final( $user_id, $previous ) && get_user_meta( $user_id, self::NUMBER_META, true ) === $normalized ) {
			return $previous;
		}

		$result = $this->verdict( $normalized );
		update_user_meta( $user_id, self::STATUS_META, $result['status'] );
		update_user_meta( $user_id, self::DETAIL_META, $result['detail'] );
		update_user_meta( $user_id, self::NUMBER_META, $normalized );
		update_user_meta( $user_id, self::CHECKED_META, time() );

		if ( $notify && '' !== $previous && $previous !== $result['status'] ) {
			/**
			 * Fires when the VIES verdict of a customer's VAT ID changes;
			 * WooCommerce sends the team notification on it (VatReviewEmail).
			 *
			 * @since 0.1.0
			 *
			 * @param int    $user_id  Customer.
			 * @param string $previous Verdict before.
			 * @param string $current  Verdict now.
			 */
			do_action( 'linker_commerce_vat_status_changed', $user_id, $previous, $result['status'] );
		}
		return $result['status'];
	}

	/**
	 * The customer's current verdict, '' before any check.
	 *
	 * @param int $user_id Customer.
	 */
	public function status( int $user_id ): string {
		$status = get_user_meta( $user_id, self::STATUS_META, true );
		return is_string( $status ) ? $status : '';
	}

	/**
	 * Stores the verdict for this inquiry's VAT. Reuse a final account verdict
	 * only for the same number; an inquiry edit never updates the account.
	 *
	 * @param WC_Order $order Inquiry.
	 */
	public function snapshot( WC_Order $order ): void {
		$input       = $order->get_meta( '_' . self::VAT_META );
		$number      = VatNumber::normalize( is_string( $input ) ? $input : '' );
		$customer_id = $order->get_customer_id();
		$status      = $this->status( $customer_id );
		if ( $customer_id <= 0 || ! $this->is_final( $customer_id, $status ) || $number !== get_user_meta( $customer_id, self::NUMBER_META, true ) ) {
			$status = $this->verdict( $number )['status'];
		}
		$order->update_meta_data( self::ORDER_STATUS, $status );
	}

	/**
	 * The name of a verdict, for staff.
	 *
	 * @param string $status Verdict.
	 */
	public static function label( string $status ): string {
		$labels = array(
			self::VALID      => __( 'Valid (VIES)', 'linker-commerce' ),
			self::INVALID    => __( 'Not valid according to VIES – review', 'linker-commerce' ),
			self::UNVERIFIED => __( 'Not checked (VIES unavailable or not an EU VAT ID) – review', 'linker-commerce' ),
			self::NONE       => __( 'No VAT ID given', 'linker-commerce' ),
		);
		return $labels[ $status ] ?? __( 'Not checked yet', 'linker-commerce' );
	}

	/**
	 * Whether a stored verdict stands for its number: every verdict except a
	 * check VIES could not answer (service or member state unavailable).
	 *
	 * @param int    $user_id Customer.
	 * @param string $status  Stored verdict.
	 */
	private function is_final( int $user_id, string $status ): bool {
		if ( self::UNVERIFIED === $status ) {
			return self::NOT_EU === get_user_meta( $user_id, self::DETAIL_META, true );
		}
		return '' !== $status;
	}

	/**
	 * The verdict for a normalized number.
	 *
	 * @param string $normalized VAT ID without spaces, dots and hyphens.
	 * @return array{status: string, detail: string}
	 */
	private function verdict( string $normalized ): array {
		if ( '' === $normalized ) {
			return array(
				'status' => self::NONE,
				'detail' => '',
			);
		}
		$vat = VatNumber::parse( $normalized );
		if ( null === $vat || ! $vat->is_checkable() ) {
			return array(
				'status' => self::UNVERIFIED,
				'detail' => self::NOT_EU,
			);
		}
		return $this->vies->check( $vat );
	}
}
