<?php
/**
 * Proforma numbers.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Proforma;

/**
 * Numbers PREFIX-YYYY-NNNN, counting from 1 in each calendar year
 * (docs/specs/11-commerce.md: 编号 PREFIX-YYYY-NNNN，默认前缀 DLK-PF，按年计数，选项存储).
 * A number is taken only when its document exists: the caller renders the
 * document with next(), then commit() claims the number atomically. If another
 * request claimed it meanwhile, commit() fails and the caller renders again with
 * the following number, so numbers have no gaps and no duplicates.
 */
final class Sequence {

	/**
	 * Option name of a year's last number: this prefix and the year.
	 */
	public const OPTION_PREFIX = 'linker_commerce_proforma_seq_';

	/**
	 * The number the next document of the year gets.
	 *
	 * @param int $year Calendar year.
	 */
	public function next( int $year ): int {
		global $wpdb;
		$last = $wpdb->get_var( $wpdb->prepare( "SELECT option_value FROM {$wpdb->options} WHERE option_name = %s", self::OPTION_PREFIX . $year ) ); // phpcs:ignore WordPress.DB.DirectDatabaseQuery -- read past the option cache: another request may have claimed a number.
		return (int) $last + 1;
	}

	/**
	 * Claims a number: succeeds only if it directly follows the last claimed one.
	 *
	 * @param int $year   Calendar year.
	 * @param int $number Number to claim.
	 * @return bool Whether the number is now taken by the caller.
	 */
	public function commit( int $year, int $number ): bool {
		global $wpdb;
		$name = self::OPTION_PREFIX . $year;
		add_option( $name, '0', '', false );
		// One UPDATE compares and sets in a single statement, so two requests cannot both claim the same number.
		$claimed = $wpdb->query( $wpdb->prepare( "UPDATE {$wpdb->options} SET option_value = %s WHERE option_name = %s AND option_value = %s", (string) $number, $name, (string) ( $number - 1 ) ) ); // phpcs:ignore WordPress.DB.DirectDatabaseQuery -- an atomic compare-and-set is not possible through update_option().
		wp_cache_delete( $name, 'options' );
		return 1 === $claimed;
	}

	/**
	 * A number as printed.
	 *
	 * @param string $prefix Prefix from the settings.
	 * @param int    $year   Calendar year.
	 * @param int    $number Number within the year.
	 */
	public static function format( string $prefix, int $year, int $number ): string {
		return sprintf( '%s-%04d-%04d', $prefix, $year, $number );
	}
}
