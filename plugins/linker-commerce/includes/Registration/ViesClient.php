<?php
/**
 * The European Commission's VAT number check.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration;

/**
 * Asks VIES whether a VAT ID is valid. The answer is one of VatProfile's
 * statuses; when VIES cannot answer (service or member state down, too many
 * requests, no connection) the number counts as not checked, never as invalid.
 */
final class ViesClient {

	/**
	 * VIES REST API, check-vat-number (POST {countryCode, vatNumber} → {valid, …}).
	 * Contract: swagger_publicVAT.yaml of the European Commission; base URL and
	 * answers verified via Apify on 2026-10-09.
	 */
	public const ENDPOINT = 'https://ec.europa.eu/taxation_customs/vies/rest-api/check-vat-number';

	/**
	 * Checks a number.
	 *
	 * @param VatNumber $vat The number.
	 * @return array{status: string, detail: string} Status and, when not checked, the reason.
	 */
	public function check( VatNumber $vat ): array {
		// WordPress's default timeout (5 seconds, WP_Http::request()) applies.
		$response = wp_remote_post(
			self::ENDPOINT,
			array(
				'headers' => array(
					'Content-Type' => 'application/json',
					'Accept'       => 'application/json',
				),
				'body'    => (string) wp_json_encode(
					array(
						'countryCode' => $vat->country,
						'vatNumber'   => $vat->number,
					)
				),
			)
		);
		if ( is_wp_error( $response ) ) {
			return self::unverified( $response->get_error_message() );
		}
		$body = json_decode( wp_remote_retrieve_body( $response ), true );
		if ( is_array( $body ) && isset( $body['valid'] ) && is_bool( $body['valid'] ) ) {
			return array(
				'status' => $body['valid'] ? VatProfile::VALID : VatProfile::INVALID,
				'detail' => '',
			);
		}
		$error = is_array( $body ) && is_array( $body['errorWrappers'][0] ?? null ) ? (string) ( $body['errorWrappers'][0]['error'] ?? '' ) : '';
		// INVALID_INPUT: "The provided CountryCode is invalid or the VAT number is empty" (WSDL).
		if ( 'INVALID_INPUT' === $error ) {
			return array(
				'status' => VatProfile::INVALID,
				'detail' => $error,
			);
		}
		return self::unverified( '' !== $error ? $error : 'HTTP ' . wp_remote_retrieve_response_code( $response ) );
	}

	/**
	 * The answer for a number VIES did not check.
	 *
	 * @param string $reason Why.
	 * @return array{status: string, detail: string}
	 */
	private static function unverified( string $reason ): array {
		return array(
			'status' => VatProfile::UNVERIFIED,
			'detail' => $reason,
		);
	}
}
