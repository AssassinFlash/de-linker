<?php
/**
 * Human-confirmed, narrowly scoped incident rule; no model classification.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

/** A whole-message match never generalizes language, email or shared hosting. */
final class Campaign {

	public const VERSION  = 'transfer-confirmed-20261022-v2';
	public const DISABLED = 'linker_confirmed_campaign_disabled';

	/**
	 * Only the exact activity independently confirmed in the incident evidence.
	 *
	 * @param string $message Validated, sanitized message.
	 */
	public static function matches( string $message ): bool {
		if ( 'yes' === get_option( self::DISABLED, 'no' ) ) {
			return false;
		}
		if ( 1 !== preg_match( '~\AВам перевод\s+[0-9]+\s+руб\.\s+(?:получить|забрать)\s+тут\s+(https?://\S+)\s*\z~u', $message, $match ) ) {
			return false;
		}
		$host = wp_parse_url( $match[1], PHP_URL_HOST );
		// Exact hosts independently confirmed from the saved incident messages; see docs/acceptance/2026-10-22/542-campaign-extension/README.md.
		return is_string( $host ) && in_array( strtolower( $host ), array( 'fredmer.buzz', 'xtimex.buzz' ), true );
	}
}
