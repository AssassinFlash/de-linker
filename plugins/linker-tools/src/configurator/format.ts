/**
 * Numbers, ranges and percentages in the page's language (1,234.5 / 1.234,5).
 */

/**
 * Internal dependencies
 */
import type { Locale, Range } from './types';

const LOCALES: Record< Locale, string > = { en: 'en-GB', de: 'de-DE' };

/**
 * A number in the page's language.
 *
 * @param value  The number.
 * @param locale The page's language.
 * @param digits At most this many decimals. By default one from 10 up and two
 *               below, trailing zeros dropped: the rule the engine words its
 *               own numbers by (texts.fmt), so the figures on the screen and
 *               in the engine's sentences agree.
 */
export function formatNumber(
	value: number,
	locale: Locale,
	digits = Math.abs( value ) >= 10 ? 1 : 2
): string {
	return new Intl.NumberFormat( LOCALES[ locale ], {
		maximumFractionDigits: digits,
	} ).format( value );
}

export function formatRange(
	range: Range,
	locale: Locale,
	unit: string,
	digits?: number
): string {
	const low = formatNumber( range.low, locale, digits );
	const high = formatNumber( range.high, locale, digits );
	return low === high ? `${ low } ${ unit }` : `${ low }–${ high } ${ unit }`;
}

export function formatPercentRange( range: Range, locale: Locale ): string {
	const low = formatNumber( Math.round( range.low * 100 ), locale );
	const high = formatNumber( Math.round( range.high * 100 ), locale );
	return low === high ? `${ low } %` : `${ low }–${ high } %`;
}
