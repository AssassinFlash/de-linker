<?php
/**
 * Money, dates and the tax label in the reader's language.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Vocabulary;

/**
 * WooCommerce stores one money format, one date format and one tax label for
 * the whole store, in one language. German pages, emails and Proforma invoices
 * show German forms: 1.680,00 €, 9. Oktober 2026, USt. 19 % (DIN 5008 puts the
 * currency after the amount and a space before the percent sign); English ones
 * keep the store's settings (€1,680.00) and read "VAT 19%".
 */
final class LocaleFormat {

	/**
	 * The date format of this plugin and of WooCommerce's pages and emails, in the
	 * current language (English "9 October 2026", German "9. Oktober 2026").
	 */
	public static function date_format(): string {
		return _x( 'j F Y', 'date format, see https://www.php.net/manual/datetime.format.php', 'linker-commerce' );
	}

	/**
	 * Runs on woocommerce_date_format.
	 */
	public function wc_date_format(): string {
		return self::date_format();
	}

	/**
	 * Decimal separator; runs on wc_get_price_decimal_separator.
	 *
	 * @param mixed $separator The store's separator.
	 * @return mixed
	 */
	public function decimal_separator( $separator ) {
		return self::is_german() ? ',' : $separator;
	}

	/**
	 * Thousands separator; runs on wc_get_price_thousand_separator.
	 *
	 * @param mixed $separator The store's separator.
	 * @return mixed
	 */
	public function thousand_separator( $separator ) {
		return self::is_german() ? '.' : $separator;
	}

	/**
	 * Amount before the currency symbol in German; runs on woocommerce_price_format.
	 *
	 * @param string $format WooCommerce's format (%1$s symbol, %2$s amount).
	 */
	public function price_format( string $format ): string {
		return self::is_german() ? '%2$s&nbsp;%1$s' : $format;
	}

	/**
	 * The label of a VAT rate in the reader's language; other rate names stay as
	 * staff entered them. Runs on woocommerce_rate_label.
	 *
	 * @param string     $label   Stored rate name.
	 * @param int|string $rate_id Rate id.
	 */
	public function rate_label( string $label, $rate_id ): string {
		if ( 1 !== preg_match( '/^(MwSt|USt|VAT)\b/i', trim( $label ) ) ) {
			return $label;
		}
		$percent = (float) \WC_Tax::get_rate_percent_value( $rate_id );
		/* translators: %s: VAT rate, e.g. 19. */
		return sprintf( _x( 'VAT %s%%', 'tax rate label', 'linker-commerce' ), (string) ( 0 + round( $percent, 2 ) ) );
	}

	/**
	 * The VAT lines of an inquiry in the language it is shown in. WooCommerce
	 * stores each line's label in the language of the request that calculated
	 * it (the customer's when the inquiry was sent, staff's when they
	 * recalculate), so the label is made again from the rate, through
	 * rate_label(). Runs on woocommerce_order_get_tax_totals.
	 *
	 * @param array<string, \stdClass> $totals Tax lines by code, as WooCommerce builds them.
	 * @return array<string, \stdClass>
	 */
	public function order_tax_totals( array $totals ): array {
		foreach ( $totals as $total ) {
			$rate_id = (int) ( $total->rate_id ?? 0 );
			if ( $rate_id > 0 ) {
				$total->label = \WC_Tax::get_rate_label( $rate_id );
			}
		}
		return $totals;
	}

	/**
	 * Whether the current language is German.
	 */
	private static function is_german(): bool {
		return str_starts_with( determine_locale(), 'de' );
	}
}
