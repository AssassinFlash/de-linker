<?php
/**
 * Dates and ages of the digest, read in Berlin time.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Digest;

/**
 * Every time the digest prints is Europe/Berlin (docs/specs/74-daily-digest.md:
 * the timezone of the windows' display, independent of the site's General
 * setting). Dates follow the language the email renders in — "October 11,
 * 2026" in English, "11. Oktober 2026" in German — not the site's date format
 * option, which carries this site's history, not the email's language.
 */
final class Format {

	/**
	 * The timezone of every printed time.
	 */
	public const TIMEZONE = 'Europe/Berlin';

	/**
	 * A timestamp as the email language's date, in Berlin time.
	 *
	 * @param int $timestamp Unix time.
	 */
	public static function date( int $timestamp ): string {
		$locale = determine_locale();
		if ( str_starts_with( $locale, 'zh' ) ) {
			$format = 'Y年n月j日';
		} elseif ( str_starts_with( $locale, 'de' ) ) {
			$format = 'j. F Y';
		} else {
			$format = 'F j, Y';
		}
		return (string) wp_date( $format, $timestamp, new \DateTimeZone( self::TIMEZONE ) );
	}

	/**
	 * Today as the site's date, in Berlin time.
	 */
	public static function today(): string {
		return self::date( time() );
	}

	/**
	 * A timestamp as hour and minute, in Berlin time.
	 *
	 * @param int $timestamp Unix time.
	 */
	public static function time( int $timestamp ): string {
		return (string) wp_date( 'H:i', $timestamp, new \DateTimeZone( self::TIMEZONE ) );
	}

	/**
	 * How long ago a timestamp was: hours below two days, whole days from then on.
	 *
	 * @param int $timestamp Unix time of the moment.
	 * @param int $now       Unix time of the digest.
	 */
	public static function age( int $timestamp, int $now ): string {
		$seconds = max( 0, $now - $timestamp );
		$hours   = (int) floor( $seconds / HOUR_IN_SECONDS );
		if ( $hours < 48 ) {
			$hours = max( 1, $hours );
			/* translators: %d: number of hours. */
			return sprintf( _n( '%d hour ago', '%d hours ago', $hours, 'linker-commerce' ), $hours );
		}
		$days = (int) floor( $seconds / DAY_IN_SECONDS );
		/* translators: %d: number of days. */
		return sprintf( _n( '%d day ago', '%d days ago', $days, 'linker-commerce' ), $days );
	}
}
