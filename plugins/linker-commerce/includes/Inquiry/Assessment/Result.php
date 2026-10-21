<?php
/**
 * Validated observation labels, never admission decisions.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry\Assessment;

/** Fixed labels and safe diagnostics of the owner-approved first stage. */
final class Result {

	public const MODEL  = 'typesafe/jev-1.13';
	public const RUBRIC = 'inquiry-observation-v1';
	public const ABUSE  = array( 'fraud_or_phishing', 'unsolicited_bulk_promotion', 'meaningless_abuse' );
	public const BASES  = array( 'business_request', 'service_or_complaint', 'reporting_abuse', 'fraud_or_phishing', 'unsolicited_bulk_promotion', 'meaningless_abuse', 'insufficient_context' );

	/**
	 * Explicit failure, rather than a false normal verdict.
	 *
	 * @param string $reason Fixed operational code.
	 * @return array<string, mixed>
	 */
	public static function unknown( string $reason ): array {
		return array(
			'label'  => 'uncertain',
			'basis'  => 'insufficient_context',
			'reason' => $reason,
			'model'  => self::MODEL,
			'rubric' => self::RUBRIC,
			'raw'    => array(),
		);
	}

	/**
	 * Validate the authenticated service response again at the storage boundary.
	 *
	 * @param mixed $data Response body.
	 * @return array<string, mixed>
	 */
	public static function validate( mixed $data ): array {
		if ( ! is_array( $data ) || ! is_string( $data['model'] ?? null ) || 1 !== preg_match( '/^typesafe\/jev-1\.13(?:-\d{8})?$/D', $data['model'] ) || self::RUBRIC !== ( $data['rubric'] ?? '' ) ) {
			return self::unknown( 'invalid_response' );
		}
		$label = $data['label'] ?? '';
		$basis = $data['basis'] ?? '';
		if ( ! in_array( $label, array( 'normal', 'suspected_spam', 'uncertain' ), true ) || ! in_array( $basis, self::BASES, true ) ) {
			return self::unknown( 'invalid_response' );
		}
		$conflict = self::conflicts( $label, $basis );
		$reason   = is_string( $data['reason'] ?? null ) ? $data['reason'] : '';
		// Only fixed codes may enter logs/admin; never a provider's response text.
		if ( 1 !== preg_match( '/^(classified|conflict|insufficient_context|missing_credentials|invalid_model|invalid_response|transport_error|deadline|provider_http_[0-9]{3}|provider_budget_(quota|unavailable|configuration|permissions|replayed|provider|attempt))$/D', $reason ) ) {
			return self::unknown( 'invalid_response' );
		}
		$raw = $data['raw'] ?? array();
		if ( in_array( $reason, array( 'classified', 'conflict', 'insufficient_context' ), true ) ) {
			if ( ! is_array( $raw ) || ! is_array( $raw['classification'] ?? null ) || ! is_array( $raw['basis'] ?? null ) || 'choice' !== ( $raw['classification']['type'] ?? '' ) || 'choice' !== ( $raw['basis']['type'] ?? '' ) || ! in_array( $raw['classification']['choice'] ?? '', array( 'normal', 'suspected_spam', 'uncertain' ), true ) || ( $raw['basis']['choice'] ?? '' ) !== $basis ) {
				return self::unknown( 'invalid_response' );
			}
			$raw_label    = $raw['classification']['choice'];
			$raw_conflict = self::conflicts( $raw_label, $basis );
			if ( ! $raw_conflict && $raw_label !== $label ) {
				return self::unknown( 'invalid_response' );
			}
			$conflict = $conflict || $raw_conflict;
			// Keep original typed answers, not arbitrary provider text/metadata.
			$raw = array(
				'classification' => array(
					'type'   => 'choice',
					'choice' => $raw_label,
				),
				'basis'          => array(
					'type'   => 'choice',
					'choice' => $basis,
				),
			);
		}
		$failed = ! in_array( $reason, array( 'classified', 'insufficient_context' ), true );
		return array(
			'label'   => $conflict || $failed ? 'uncertain' : $label,
			'basis'   => $basis,
			'reason'  => $conflict ? 'conflict' : $reason,
			'model'   => $data['model'],
			'rubric'  => self::RUBRIC,
			'raw'     => is_array( $raw ) ? $raw : array(),
			'seconds' => is_numeric( $data['seconds'] ?? null ) ? max( 0.0, (float) $data['seconds'] ) : 0.0,
		);
	}

	/**
	 * The two typed decisions must express a consistent purpose.
	 *
	 * @param string $label Classification.
	 * @param string $basis Evidence category.
	 */
	private static function conflicts( string $label, string $basis ): bool {
		return ( 'normal' === $label && ( in_array( $basis, self::ABUSE, true ) || 'insufficient_context' === $basis ) ) || ( 'suspected_spam' === $label && ! in_array( $basis, self::ABUSE, true ) );
	}

	/**
	 * The same conservative terms in the staff view and internal email.
	 *
	 * @param string $label Observation label.
	 */
	public static function label( string $label ): string {
		return match ( $label ) {
			'normal' => __( 'Likely genuine', 'linker-commerce' ),
			'suspected_spam' => __( 'Suspected spam', 'linker-commerce' ),
			default => __( 'Unable to assess', 'linker-commerce' ),
		};
	}

	/**
	 * Fixed reasons; no generated allegations about a sender.
	 *
	 * @param array<string, mixed> $result Verdict.
	 */
	public static function explanation( array $result ): string {
		if ( 'uncertain' === ( $result['label'] ?? 'uncertain' ) ) {
			return __( 'No reliable assessment was available. Please review the inquiry.', 'linker-commerce' );
		}
		return match ( $result['basis'] ?? '' ) {
			'fraud_or_phishing' => __( 'Possible fraud or phishing.', 'linker-commerce' ),
			'unsolicited_bulk_promotion' => __( 'Possible unsolicited bulk promotion.', 'linker-commerce' ),
			'meaningless_abuse' => __( 'Repeated content with no clear request.', 'linker-commerce' ),
			'service_or_complaint' => __( 'Service request or complaint.', 'linker-commerce' ),
			'reporting_abuse' => __( 'Report of suspected abuse.', 'linker-commerce' ),
			default => __( 'Plausible business or contact request.', 'linker-commerce' ),
		};
	}
}
