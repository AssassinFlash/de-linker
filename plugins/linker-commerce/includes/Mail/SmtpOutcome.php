<?php
/**
 * Last SMTP result, without server text or configuration values (#297 review).
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Mail;

/**
 * Only the last timestamp, status and fixed reason category are persisted.
 */
final class SmtpOutcome {

	public const OPTION            = 'linker_commerce_internal_smtp_outcome';
	public const SMTP_FAILURE      = 'smtp_failure';
	public const IDENTITY_MISMATCH = 'identity_mismatch';

	/**
	 * Records an SMTP attempt; PHP mail fallback does not overwrite this result.
	 *
	 * @param bool   $success Whether SMTP accepted the message.
	 * @param string $reason Fixed failure category, never a server response.
	 */
	public function record( bool $success, string $reason = self::SMTP_FAILURE ): void {
		update_option(
			self::OPTION,
			array(
				'at'     => time(),
				'status' => $success ? 'success' : 'failure',
				'reason' => $success ? '' : ( self::IDENTITY_MISMATCH === $reason ? self::IDENTITY_MISMATCH : self::SMTP_FAILURE ),
			),
			false
		);
	}

	/**
	 * The last valid result, or null before the first recorded SMTP attempt.
	 *
	 * @return array{at: int, status: string, reason: string}|null
	 */
	public function last(): ?array {
		$value = get_option( self::OPTION );
		if ( ! is_array( $value ) || ! isset( $value['at'], $value['status'], $value['reason'] ) || ! is_int( $value['at'] ) || ! in_array( $value['status'], array( 'success', 'failure' ), true ) || ! in_array( $value['reason'], array( '', self::SMTP_FAILURE, self::IDENTITY_MISMATCH ), true ) ) {
			return null;
		}
		return array(
			'at'     => $value['at'],
			'status' => $value['status'],
			'reason' => $value['reason'],
		);
	}
}
