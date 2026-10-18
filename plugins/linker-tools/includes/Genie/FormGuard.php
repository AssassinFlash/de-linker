<?php
/**
 * The bot guard of Genie's public forms.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

/**
 * Genie has two forms a guest can send to the site: "email me this
 * conversation" (ConversationMail, #235) and "Let Linker contact me"
 * (ContactRequest, #243). Both carry what a public form needs, and this is
 * the one place it lives:
 *
 * - a honeypot field (`website`) that people never see and bots fill in;
 * - a start time signed by the site (`started`, `started_nonce`): a request
 *   sooner than MIN_SECONDS after it, or older than STAMP_LIFETIME, or with a
 *   time this door did not sign, does not pass;
 * - an hourly limit per connection and a daily cap for the whole site, each a
 *   RateLimit (one SQL statement each, so two requests at the same moment
 *   cannot both take the last place). Each door gives its own caps, with
 *   their sources.
 *
 * The signature is an HMAC with the site's nonce salt, not a WordPress nonce:
 * a guest's nonce follows WooCommerce's session cookie
 * (`nonce_user_logged_out`), which the page may not have had yet when it was
 * made and has by the time the guest sends (seen on g235: every guest request
 * failed the nonce). The door's name is part of what is signed, so a stamp of
 * one door proves nothing at the other.
 */
final class FormGuard {

	/**
	 * Seconds between the form's appearance and a guest's request, at least:
	 * the fill-time floor the owner asked for on the site's public inquiry
	 * form (#246); a person reads the form and types an address.
	 */
	public const MIN_SECONDS = 3;

	/**
	 * How long a start time stays good: a WordPress nonce's lifetime
	 * (DAY_IN_SECONDS, `nonce_life`), which this stamp stands in for.
	 */
	public const STAMP_LIFETIME = DAY_IN_SECONDS;

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
	 * Sets up the guard of one door.
	 *
	 * @param string         $name       The door (`genie_mail`, `genie_contact`): names its limits and its signature.
	 * @param int            $hourly     Requests one connection may send per hour.
	 * @param int            $daily      Requests the whole site takes per day.
	 * @param RateLimit|null $connection The hourly limit; built from $name and $hourly when omitted.
	 * @param RateLimit|null $site       The daily cap; built from $name and $daily when omitted.
	 */
	public function __construct(
		private readonly string $name,
		int $hourly,
		int $daily,
		?RateLimit $connection = null,
		?RateLimit $site = null
	) {
		$this->connection = $connection ?? new RateLimit( $name, $hourly, HOUR_IN_SECONDS );
		$this->site       = $site ?? new RateLimit( $name . '_day', $daily, DAY_IN_SECONDS );
	}

	/**
	 * A signed start time: when the form appeared, and its signature.
	 *
	 * @param int|null $at Unix time of the stamp; now when omitted.
	 * @return array{started: string, nonce: string}
	 */
	public function stamp( ?int $at = null ): array {
		$started = (string) ( $at ?? time() );
		return array(
			'started' => $started,
			'nonce'   => $this->signature( $started ),
		);
	}

	/**
	 * Whether a guest's request passes: the honeypot empty, the start time
	 * signed by this door, at least MIN_SECONDS and at most STAMP_LIFETIME old.
	 *
	 * @param array<string, mixed> $guard `website`, `started`, `started_nonce`.
	 * @param int|null             $now   Unix time; the clock when omitted.
	 */
	public function passes( array $guard, ?int $now = null ): bool {
		$started = $guard['started'] ?? '';
		$nonce   = $guard['started_nonce'] ?? '';
		$age     = ( $now ?? time() ) - (int) $started;
		return ! $this->trapped( $guard )
			&& is_string( $started ) && ctype_digit( $started )
			&& is_string( $nonce )
			&& $age >= self::MIN_SECONDS
			&& $age <= self::STAMP_LIFETIME
			&& hash_equals( $this->signature( $started ), $nonce );
	}

	/**
	 * Whether the honeypot is filled: a bot, answered as if it were a person.
	 *
	 * @param array<string, mixed> $guard `website`.
	 */
	public function trapped( array $guard ): bool {
		$trap = $guard['website'] ?? '';
		return ! is_string( $trap ) || '' !== trim( $trap );
	}

	/**
	 * Takes one place of this connection's hour and one of the site's day.
	 *
	 * @return string `connection` or `site` when that one is full, '' when both were taken.
	 */
	public function take(): string {
		if ( ! $this->connection->take( self::address() ) ) {
			return 'connection';
		}
		return $this->site->take( '' ) ? '' : 'site';
	}

	/**
	 * Takes one place of the site's day alone (a confirmation link, #235).
	 */
	public function take_site(): bool {
		return $this->site->take( '' );
	}

	/**
	 * The address this connection came from, never a forwarded header a
	 * sender sets freely.
	 */
	public static function address(): string {
		return isset( $_SERVER['REMOTE_ADDR'] ) ? sanitize_text_field( wp_unslash( (string) $_SERVER['REMOTE_ADDR'] ) ) : '';
	}

	/**
	 * The signature of one start time at this door.
	 *
	 * @param string $started Unix time, as sent.
	 */
	private function signature( string $started ): string {
		return hash_hmac( 'sha256', 'linker_tools_' . $this->name . '|' . $started, wp_salt( 'nonce' ) );
	}
}
