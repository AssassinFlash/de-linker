<?php
/**
 * The observable count of registrations refused by the bot guard.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration;

/**
 * A blocked registration creates no account and no mail, so its only trace is
 * this counter. The ticket asks that the count be observable (#225); it is
 * stored in one non-autoloaded option and printed by `wp linker-commerce
 * registration-blocks`. The action is the extension point for a future
 * consumer; this branch ships no digest or monitor reader.
 */
final class BlockedRegistrations {

	/**
	 * Option holding the counts and the time of the last block.
	 */
	public const OPTION = 'linker_commerce_registration_blocked';

	/**
	 * Action fired for every block, with its reason.
	 */
	public const ACTION = 'linker_commerce_registration_blocked';

	/**
	 * Counts one refusal.
	 *
	 * @param string $reason Short reason key: honeypot, clock, too_fast or limit.
	 */
	public static function record( string $reason ): void {
		$stored                      = self::stored();
		$stored['counts'][ $reason ] = (int) ( $stored['counts'][ $reason ] ?? 0 ) + 1;
		$stored['last']              = gmdate( 'Y-m-d H:i:s' );
		// No autoload: the counter is read by staff and the CLI, not on every page.
		update_option( self::OPTION, $stored, false );
		/**
		 * Fires when a registration was refused before any account or mail.
		 *
		 * @since 0.1.0
		 *
		 * @param string $reason Short reason key.
		 */
		do_action( self::ACTION, $reason ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- the documented action of this class; its name begins with the plugin prefix.
	}

	/**
	 * The stored counts, total and last block time; empty values when none.
	 *
	 * @return array{counts: array<string, int>, total: int, last: string}
	 */
	public static function counts(): array {
		$stored = self::stored();
		$counts = array();
		foreach ( $stored['counts'] as $reason => $count ) {
			$counts[ (string) $reason ] = (int) $count;
		}
		ksort( $counts );
		return array(
			'counts' => $counts,
			'total'  => array_sum( $counts ),
			'last'   => $stored['last'],
		);
	}

	/**
	 * Removes the counts; the CLI's --reset.
	 */
	public static function reset(): void {
		delete_option( self::OPTION );
	}

	/**
	 * The option in its documented shape, whatever it holds.
	 *
	 * @return array{counts: array<string, mixed>, last: string}
	 */
	private static function stored(): array {
		$option = get_option( self::OPTION, array() );
		$counts = is_array( $option ) && isset( $option['counts'] ) && is_array( $option['counts'] ) ? $option['counts'] : array();
		$last   = is_array( $option ) && isset( $option['last'] ) && is_string( $option['last'] ) ? $option['last'] : '';
		return array(
			'counts' => $counts,
			'last'   => $last,
		);
	}
}
