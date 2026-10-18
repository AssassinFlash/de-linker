<?php
/**
 * A fixed-window allowance, taken in one database statement.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry;

/**
 * Counts how often a caller did something in the current window and refuses
 * past the limit (PR #290, review round 2; same technique as #235). The check and the increment
 * are one UPDATE that matches only while the count is under the limit, so two
 * requests arriving together cannot both take the last unit: the database
 * serialises the row, and the second UPDATE matches nothing.
 *
 * Each window is one row in the options table, named after the limiter, the
 * caller (hashed) and the window number, never autoloaded. The options table
 * is the store because it is the site's own and needs no new table; the
 * object cache is not used, because a cache in front of it (Redis on the
 * instances) is not where the count must live. Rows of earlier windows of the
 * same limiter go on every take.
 */
final class RateLimit {

	/**
	 * Option name prefix of every limiter row.
	 */
	public const PREFIX = 'linker_commerce_limit_';

	/**
	 * The clock.
	 *
	 * @var callable(): int
	 */
	private $clock;

	/**
	 * Sets up one limiter.
	 *
	 * @param string                 $name   Limiter name: letters, digits and underscores, no dot.
	 * @param int                    $limit  Takes allowed per caller per window.
	 * @param int                    $window Window length in seconds.
	 * @param (callable(): int)|null $clock The time, for tests; `time()` when omitted.
	 */
	public function __construct(
		private readonly string $name,
		private readonly int $limit,
		private readonly int $window,
		?callable $clock = null
	) {
		$this->clock = $clock ?? 'time';
	}

	/**
	 * Takes one unit for a caller.
	 *
	 * @param string $who The caller: a connection address, or '' for the whole site.
	 * @return bool Whether the caller was still under the limit.
	 */
	public function take( string $who ): bool {
		global $wpdb;
		$bucket = str_pad( (string) intdiv( ( $this->clock )(), max( 1, $this->window ) ), 10, '0', STR_PAD_LEFT );
		// The dot ends the name: no limiter's rows start with another
		// limiter's prefix, so the purge below never takes a row of a
		// limiter with a longer window ("mail" against "mail_day").
		$own = self::PREFIX . $this->name . '.';
		$row = $own . substr( md5( $who ), 0, 12 ) . '.' . $bucket;
		// phpcs:disable WordPress.DB.DirectDatabaseQuery -- the one-statement check-and-increment is the point; the options API reads before it writes.
		$wpdb->query(
			$wpdb->prepare(
				"DELETE FROM {$wpdb->options} WHERE option_name LIKE %s AND RIGHT(option_name, 10) < %s",
				$wpdb->esc_like( $own ) . '%',
				$bucket
			)
		);
		$wpdb->query( $wpdb->prepare( "INSERT IGNORE INTO {$wpdb->options} (option_name, option_value, autoload) VALUES (%s, '0', 'off')", $row ) );
		$taken = $wpdb->query(
			$wpdb->prepare(
				"UPDATE {$wpdb->options} SET option_value = CAST(option_value AS UNSIGNED) + 1 WHERE option_name = %s AND CAST(option_value AS UNSIGNED) < %d",
				$row,
				$this->limit
			)
		);
		// phpcs:enable
		return 1 === $taken;
	}
}
