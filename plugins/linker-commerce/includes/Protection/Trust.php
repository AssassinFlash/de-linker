<?php
/**
 * Session-bound challenge trust for the genie action only.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

/**
 * One solved human challenge admits further genie turns for the same
 * identity without a fresh proof, for a bounded window (owner ruling
 * 2026-10-22: 尽可能不阻碍真实询盘 — do not stand in a real conversation's
 * way). The 2026-10-22 attack was floods of FRESH identities; those still
 * face the challenge on their first turn, and the identity quotas
 * (ResourcePolicy's genie_day/genie_burst) are unchanged, so the trust
 * window only removes the repeated challenge for an identity that already
 * solved one — it grants no additional quota.
 *
 * The record is a private, revocable wp_options row keyed by the same
 * identity binding a Proof binds (Identity::binding()), never a
 * client-supplied flag. Business actions (inquiry/contact and their genie
 * door twins) keep their single-use proofs and never read this trust.
 */
final class Trust {

	/**
	 * How long one solved challenge admits genie turns.
	 *
	 * Twelve hours, deliberately longer than the challenge's own freshness
	 * (Turnstile token lifetime 300 s, Proof::LIFETIME) because this is a
	 * server-side trust decision, not a token lifetime; and deliberately
	 * half the site's longest comparable bound — FormGuard::STAMP_LIFETIME,
	 * a WordPress nonce lifetime (24 h) for one form — because this admits
	 * model turns, not one submission. One challenge per working day: a
	 * daily-returning installer verifies once, an ongoing conversation never
	 * re-challenges mid-session.
	 */
	public const WINDOW = 12 * HOUR_IN_SECONDS;

	/**
	 * Option-name prefix of every trust row; the window bucket ends the name.
	 */
	private const PREFIX = 'linker_commerce_trust_';

	/**
	 * Fixed server clock for expiry fixtures, time() in normal requests.
	 *
	 * @var (callable():int)|null
	 */
	private $clock;

	/**
	 * Sets up one trust store.
	 *
	 * @param (callable():int)|null $clock Server clock, for tests; `time()` when omitted.
	 */
	public function __construct( ?callable $clock = null ) {
		$this->clock = $clock;
	}

	/**
	 * Whether the identity's solved challenge still admits this action.
	 *
	 * @param string   $action Trusted action scope (genie).
	 * @param Identity $identity Current native account/browser binding.
	 */
	public function admitted( string $action, Identity $identity ): bool {
		$now    = $this->now();
		$bucket = $this->bucket( $now );
		foreach ( array( $bucket, $bucket - 1 ) as $row ) {
			$stored = get_option( $this->name( $action, $identity, $row ), false );
			if ( is_array( $stored ) && (int) ( $stored['until'] ?? 0 ) > $now ) {
				return true;
			}
		}
		return false;
	}

	/**
	 * Record one solved challenge: this identity is trusted for the window.
	 *
	 * The window bucket ends the row's name, so every grant also drops every
	 * row two or more buckets old (RateLimit's own write-path purge): those
	 * are expired by construction — a grant in bucket B expires no later
	 * than the end of B+1 — while previous-bucket rows survive, because a
	 * grant late in the previous bucket is still inside its window. Rows of
	 * identities that never return cannot accumulate. At most one live row
	 * per identity exists; a fresh verification within the window starts
	 * the window again.
	 *
	 * @param string   $action Trusted action scope (genie).
	 * @param Identity $identity Current native account/browser binding.
	 */
	public function grant( string $action, Identity $identity ): void {
		global $wpdb;
		$now    = $this->now();
		$bucket = $this->bucket( $now );
		$own    = self::PREFIX . $action . '.';
		// phpcs:disable WordPress.DB.DirectDatabaseQuery -- one bounded write-path purge per grant, the RateLimit pattern; the options API reads before it writes.
		$wpdb->query(
			$wpdb->prepare(
				"DELETE FROM {$wpdb->options} WHERE option_name LIKE %s AND RIGHT(option_name, 10) < %s",
				$wpdb->esc_like( $own ) . '%',
				str_pad( (string) ( $bucket - 1 ), 10, '0', STR_PAD_LEFT )
			)
		);
		$wpdb->query(
			$wpdb->prepare(
				"INSERT IGNORE INTO {$wpdb->options} (option_name, option_value, autoload) VALUES (%s, %s, 'off')",
				$this->name( $action, $identity, $bucket ),
				maybe_serialize( array( 'until' => $now + self::WINDOW ) )
			)
		);
		// phpcs:enable
	}

	/**
	 * Withdraw the trust at once (staff decision, privacy erasure, tests).
	 *
	 * @param string   $action Trusted action scope (genie).
	 * @param Identity $identity Current native account/browser binding.
	 */
	public function revoke( string $action, Identity $identity ): void {
		$bucket = $this->bucket( $this->now() );
		foreach ( array( $bucket, $bucket - 1 ) as $row ) {
			$name = $this->name( $action, $identity, $row );
			delete_option( $name );
			wp_cache_delete( $name, 'options' );
		}
		wp_cache_delete( 'notoptions', 'options' );
	}

	/**
	 * One row's option name: prefix, action, identity hash, window bucket.
	 *
	 * @param string   $action Trusted action scope (genie).
	 * @param Identity $identity Current native account/browser binding.
	 * @param int      $bucket Fixed window bucket the grant landed in.
	 */
	private function name( string $action, Identity $identity, int $bucket ): string {
		return self::PREFIX . $action . '.' . substr( md5( $identity->binding() ), 0, 12 ) . '.' . str_pad( (string) $bucket, 10, '0', STR_PAD_LEFT );
	}

	/**
	 * The fixed window bucket of a timestamp.
	 *
	 * @param int $now Server clock.
	 */
	private function bucket( int $now ): int {
		return intdiv( $now, self::WINDOW );
	}

	/** Current server time; client clocks have no authority. */
	private function now(): int {
		return is_callable( $this->clock ) ? (int) ( $this->clock )() : time();
	}
}
