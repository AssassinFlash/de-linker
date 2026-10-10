<?php
/**
 * Tests for money, dates and tax labels per language.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Vocabulary;

use Linker\Commerce\Tests\TestCase;
use Linker\Commerce\Vocabulary\LocaleFormat;
use WP_Mock;

/**
 * Tests for LocaleFormat.
 *
 * @covers \Linker\Commerce\Vocabulary\LocaleFormat
 */
final class LocaleFormatTest extends TestCase {

	/**
	 * The current language of a test.
	 *
	 * @var string
	 */
	private string $locale = 'de_DE_formal';

	/**
	 * The language follows $locale; translations return their source.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( 'determine_locale', array( 'return' => fn (): string => $this->locale ) );
		WP_Mock::passthruFunction( '_x' );
	}

	/**
	 * German: 1.680,00 € (DIN 5008); English: the store's own settings.
	 */
	public function test_money(): void {
		$formats = new LocaleFormat();

		$this->assertSame( ',', $formats->decimal_separator( '.' ) );
		$this->assertSame( '.', $formats->thousand_separator( ',' ) );
		$this->assertSame( '%2$s&nbsp;%1$s', $formats->price_format( '%1$s%2$s' ) );

		$this->locale = 'en_US';
		$this->assertSame( '.', $formats->decimal_separator( '.' ) );
		$this->assertSame( ',', $formats->thousand_separator( ',' ) );
		$this->assertSame( '%1$s%2$s', $formats->price_format( '%1$s%2$s' ) );
	}

	/**
	 * One date format for WooCommerce's pages and this plugin, translated per language.
	 */
	public function test_date_format(): void {
		$this->assertSame( 'j F Y', LocaleFormat::date_format() );
		$this->assertSame( 'j F Y', ( new LocaleFormat() )->wc_date_format() );
	}

	/**
	 * A stored "MwSt. 19%" reads "VAT 19%" in English (translated to German as "USt. 19 %"); other names stay.
	 */
	public function test_rate_label(): void {
		$tax = \Mockery::mock( 'alias:WC_Tax' );
		$tax->allows( 'get_rate_percent_value' )->with( 1 )->andReturn( 19.0 );
		$tax->allows( 'get_rate_label' )->with( 1 )->andReturn( 'USt. 19 %' );
		$formats = new LocaleFormat();

		$this->assertSame( 'VAT 19%', $formats->rate_label( 'MwSt. 19%', 1 ) );
		$this->assertSame( 'Reverse charge', $formats->rate_label( 'Reverse charge', 2 ) );

		// An inquiry's VAT line gets its label again from the rate, in the language it is shown in.
		$stored = (object) array(
			'rate_id' => 1,
			'label'   => 'VAT 19%',
		);
		$this->assertSame( 'USt. 19 %', $formats->order_tax_totals( array( 'DE-MWST. 19%-1' => $stored ) )['DE-MWST. 19%-1']->label );
		$kept = (object) array( 'label' => 'Fee tax' );
		$this->assertSame( 'Fee tax', $formats->order_tax_totals( array( 'X' => $kept ) )['X']->label );
	}
}
