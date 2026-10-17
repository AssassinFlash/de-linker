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
 *   cap (DAILY): both RateLimit (#235), one SQL statement each, so two
 *   requests at the same moment cannot both take the last place, and a
 *   request over either is refused, never queued, so the host's shared mail
 *   quota keeps its room for the account and inquiry mail.
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
	 * Requests the whole site passes on per day. Every request is one team
	 * mail; the site takes at most 80 of the host's 100 mails a day
	 * (Linker\Commerce\Mail\Throttle::PER_DAY). With Genie's own
	 * conversation mail (ConversationMail::DAILY_CAP, 10) Genie takes at most
	 * 30 of them, which leaves 50 for registrations, inquiries and their
	 * receipts. On 2026-10-17, the busiest day the live mail log holds (the
	 * owner's test of the account chain), the site sent 7.
	 */
	public const DAILY = 20;

	/**
	 * Name of the signature's purpose, so a start time signed for this card
	 * proves nothing elsewhere.
	 */
	public const PREFIX = 'linker_genie_contact_';

	/**
	 * Per-connection hourly limit.
	 *
	 * @var RateLimit
	 */
	private readonly RateLimit $connection;

	/**
	 * Site-wide daily cap.
	 *
	 * @var RateLimit
	 */
	private readonly RateLimit $site;

	/**
	 * Sets up the guard.
	 *
	 * @param RateLimit|null $connection Per-connection hourly limit; the default when omitted.
	 * @param RateLimit|null $site       Site-wide daily cap; the default when omitted.
	 */
	public function __construct( ?RateLimit $connection = null, ?RateLimit $site = null ) {
		$this->connection = $connection ?? new RateLimit( 'genie_contact', self::LIMIT, self::WINDOW );
		$this->site       = $site ?? new RateLimit( 'genie_contact_day', self::DAILY, DAY_IN_SECONDS );
	}

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
	 * Each is one statement of RateLimit (#235), so two requests at the same
	 * moment cannot both take the last place.
	 *
	 * @param string $address The connection's address (REMOTE_ADDR).
	 */
	public function take( string $address ): string {
		if ( ! $this->connection->take( $address ) ) {
			return 'connection';
		}
		if ( ! $this->site->take( '' ) ) {
			return 'site';
		}
		return '';
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
