<?php
/**
 * The protections of Genie's contact request, a public form.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

/**
 * A guest may leave an email address for the team in Genie's contact card
 * (#243), so the card is a public form and carries what a public form needs:
 *
 * - a honeypot field (`website`) that people never see and bots fill in;
 * - a signed start time: the card asks for it when it appears, and a request
 *   sent sooner than MIN_SECONDS after it, or with a time this site did not
 *   sign, is refused;
 * - a per-connection limit (LIMIT requests per WINDOW), and a site-wide daily
 *   cap (DAILY): both counted in one SQL statement each, so two requests at
 *   the same moment cannot both take the last place, and a request over
 *   either is refused, never queued, so the host's shared mail quota keeps
 *   its room for the account and inquiry mail.
 *
 * The counters are rows of the options table that WordPress never loads
 * (autoload off, never read through get_option()); a counter of a past hour
 * or day is deleted when the next request counts.
 */
class ContactGuard {

	/**
	 * Seconds between the card's appearance and a guest's request, at least:
	 * the fill-time floor the owner asked for on the site's public inquiry form
	 * (#246); a person reads the card and types an address.
	 */
	public const MIN_SECONDS = 3;

	/**
	 * Requests one connection may send per window: the contact form's limit
	 * (Linker\Commerce\Contact\Handler::LIMIT, three an hour), the site's
	 * other public door to the team.
	 */
	public const LIMIT = 3;

	/**
	 * Length of the per-connection window, in seconds (the contact form's
	 * Handler::WINDOW).
	 */
	public const WINDOW = HOUR_IN_SECONDS;

	/**
	 * Requests the whole site passes on per UTC day. Every request is one team
	 * mail; the site takes at most 80 of the host's 100 mails a day
	 * (Linker\Commerce\Mail\Throttle::PER_DAY), and a quarter of them for
	 * Genie leaves 60 for registrations, inquiries and their receipts. On
	 * 2026-10-17, the busiest day the live mail log holds (the owner's test of
	 * the account chain), the site sent 7.
	 */
	public const DAILY = 20;

	/**
	 * Name prefix of the counters in the options table.
	 */
	public const PREFIX = 'linker_genie_contact_';

	/**
	 * The honeypot field.
	 */
	public const TRAP = 'website';

	/**
	 * A signed start time: `time.signature`.
	 *
	 * @param int|null $now Unix time; the clock when omitted.
	 */
	public function started( ?int $now = null ): string {
		$time = (string) ( $now ?? time() );
		return $time . '.' . $this->sign( $time );
	}

	/**
	 * Why a guest's request must not go on: `trap` (a bot: answer as if sent,
	 * send nothing), `invalid` (no start time this site signed) or `early`;
	 * '' when it may.
	 *
	 * @param mixed    $trap    The honeypot's value.
	 * @param mixed    $started The signed start time the card sent.
	 * @param int|null $now     Unix time; the clock when omitted.
	 */
	public function screen( mixed $trap, mixed $started, ?int $now = null ): string {
		if ( is_string( $trap ) && '' !== trim( $trap ) ) {
			return 'trap';
		}
		if ( ! is_string( $started ) || ! str_contains( $started, '.' ) ) {
			return 'invalid';
		}
		[ $time, $signature ] = explode( '.', $started, 2 );
		if ( ! ctype_digit( $time ) || ! hash_equals( $this->sign( $time ), $signature ) ) {
			return 'invalid';
		}
		if ( ( $now ?? time() ) - (int) $time < self::MIN_SECONDS ) {
			return 'early';
		}
		return '';
	}

	/**
	 * Takes one place of this connection's hour and one of the site's day:
	 * `connection` or `site` when that one is full, '' when both were taken.
	 *
	 * @param string   $address The connection's address (REMOTE_ADDR).
	 * @param int|null $now     Unix time; the clock when omitted.
	 */
	public function take( string $address, ?int $now = null ): string {
		$now = $now ?? time();
		// Fixed-width buckets, so a past counter sorts below the current one.
		$hour = sprintf( 'h%010d_', intdiv( $now, self::WINDOW ) );
		$day  = 'd' . gmdate( 'Ymd', $now );
		$this->forget( 'h', $hour );
		$this->forget( 'd', $day );
		if ( ! $this->count( self::PREFIX . $hour . md5( $address ), self::LIMIT ) ) {
			return 'connection';
		}
		if ( ! $this->count( self::PREFIX . $day, self::DAILY ) ) {
			return 'site';
		}
		return '';
	}

	/**
	 * One more on a counter, unless it holds $limit already: one conditional
	 * UPDATE, which the database applies to the row one request at a time.
	 *
	 * @param string $name  Counter (option name).
	 * @param int    $limit Its ceiling.
	 */
	private function count( string $name, int $limit ): bool {
		global $wpdb;
		// phpcs:disable WordPress.DB.DirectDatabaseQuery -- an atomic counter: get_option()/update_option() read and write in two steps, so two requests could both pass the limit; the row is never cached or loaded by WordPress.
		$wpdb->query( $wpdb->prepare( "INSERT IGNORE INTO {$wpdb->options} (option_name, option_value, autoload) VALUES (%s, '0', 'off')", $name ) );
		$taken = $wpdb->query( $wpdb->prepare( "UPDATE {$wpdb->options} SET option_value = option_value + 1 WHERE option_name = %s AND CAST(option_value AS UNSIGNED) < %d", $name, $limit ) );
		// phpcs:enable
		return 1 === $taken;
	}

	/**
	 * Deletes the counters of past hours or days.
	 *
	 * @param string $kind    `h` or `d`.
	 * @param string $current The current bucket's name part.
	 */
	private function forget( string $kind, string $current ): void {
		global $wpdb;
		// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- see count(): these rows are only the guard's counters.
		$wpdb->query( $wpdb->prepare( "DELETE FROM {$wpdb->options} WHERE option_name LIKE %s AND option_name < %s", $wpdb->esc_like( self::PREFIX . $kind ) . '%', self::PREFIX . $current ) );
	}

	/**
	 * The start time's signature: HMAC-SHA256 with the site's nonce salt.
	 *
	 * @param string $time Unix time as digits.
	 */
	private function sign( string $time ): string {
		return hash_hmac( 'sha256', self::PREFIX . 'started|' . $time, wp_salt( 'nonce' ) );
	}
}
