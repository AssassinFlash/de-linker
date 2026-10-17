<?php
/**
 * Tests for the settings tab.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Settings;

use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Settings\Options;
use Linker\Commerce\Settings\SettingsTab;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WP_Mock;

/**
 * Tests for SettingsTab. WooCommerce's settings API reports through test actions (tests/php/Doubles).
 *
 * @covers \Linker\Commerce\Settings\SettingsTab
 */
final class SettingsTabTest extends TestCase {

	/**
	 * Translations return their source.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
	}

	/**
	 * The tab joins WooCommerce's settings tabs.
	 */
	public function test_adds_the_tab(): void {
		$this->assertSame(
			array(
				'general'        => 'General',
				SettingsTab::TAB => 'Inquiries',
			),
			( new SettingsTab( new JobStore() ) )->add_tab( array( 'general' => 'General' ) )
		);
	}

	/**
	 * Internal mail has its own sender field beside its recipient (#286).
	 */
	public function test_internal_sender_setting(): void {
		$fields = ( new SettingsTab( new JobStore() ) )->fields();
		$ids    = array_column( $fields, 'id' );
		$index  = array_search( Options::NOTIFY_TO, $ids, true );
		$this->assertIsInt( $index );
		$this->assertSame( Options::NOTIFY_FROM, $fields[ $index + 1 ]['id'] );
		$this->assertSame( 'email', $fields[ $index + 1 ]['type'] );
		$this->assertSame( 'sales@sunriverinverter.com', $fields[ $index + 1 ]['default'] );
	}

	/**
	 * The envelope setting applies site-wide, outside the internal mail section.
	 */
	public function test_envelope_sender_setting(): void {
		$fields = array_column( ( new SettingsTab( new JobStore() ) )->fields(), null, 'id' );
		$this->assertArrayHasKey( Options::ENVELOPE_SENDER, $fields );
		$this->assertSame( 'email', $fields[ Options::ENVELOPE_SENDER ]['type'] );
		$this->assertSame( 'sales@sunriverinverter.com', $fields[ Options::ENVELOPE_SENDER ]['default'] );
	}

	/**
	 * Every option of Options has a field, each section is opened and closed, and output and save use the same fields.
	 */
	public function test_fields_cover_every_option(): void {
		$tab           = new SettingsTab( new JobStore() );
		$counts        = new \stdClass();
		$counts->draft = 0;
		WP_Mock::userFunction( 'wp_count_posts', array( 'return' => $counts ) );
		$fields = $tab->fields();
		$ids    = array_column( array_filter( $fields, static fn ( array $field ): bool => ! in_array( $field['type'], array( 'title', 'sectionend' ), true ) ), 'id' );

		foreach ( ( new \ReflectionClass( Options::class ) )->getConstants() as $name => $value ) {
			if ( ! str_starts_with( $name, 'DEFAULT_' ) ) {
				$this->assertContains( $value, $ids, $name );
			}
		}
		$types = array_column( $fields, 'type' );
		$this->assertSame( count( array_keys( $types, 'title', true ) ), count( array_keys( $types, 'sectionend', true ) ) );

		WP_Mock::expectAction( 'linker_test_settings_output', $fields );
		WP_Mock::expectAction( 'linker_test_settings_saved', $fields );
		$tab->output();
		$tab->save();
		$this->assertConditionsMet();
	}

	/**
	 * IBAN check digits (ISO 13616 MOD 97-10): published example IBANs pass, a changed digit fails.
	 *
	 * @testWith ["DE89370400440532013000", true]
	 *           ["GB82WEST12345698765432", true]
	 *           ["NL91ABNA0417164300", true]
	 *           ["AT611904300234573201", true]
	 *           ["DE89370400440532013001", false]
	 *           ["DE8937040044", false]
	 *           ["1289370400440532013000", false]
	 *
	 * @param string $iban  IBAN.
	 * @param bool   $valid Whether it is valid.
	 */
	public function test_iban_check_digits( string $iban, bool $valid ): void {
		$this->assertSame( $valid, SettingsTab::is_valid_iban( $iban ) );
	}

	/**
	 * A valid IBAN is stored without spaces, upper case; an invalid one keeps the saved IBAN and reports why.
	 */
	public function test_sanitize_iban(): void {
		$this->options( array( Options::BANK_IBAN => 'DE89370400440532013000' ) );
		$tab = new SettingsTab( new JobStore() );

		$this->assertSame( 'GB82WEST12345698765432', $tab->sanitize_iban( 'gb82 west 1234 5698 7654 32' ) );
		$this->assertSame( '', $tab->sanitize_iban( '' ) );

		WP_Mock::expectAction( 'linker_test_settings_error', 'The IBAN is not valid (check digits do not match); the previous IBAN is kept.' );
		$this->assertSame( 'DE89370400440532013000', $tab->sanitize_iban( 'DE00 3704 0044 0532 0130 00' ) );
		$this->assertConditionsMet();
	}

	/**
	 * A BIC is 8 or 11 characters (ISO 9362); otherwise the saved BIC stays.
	 */
	public function test_sanitize_bic(): void {
		$this->options( array( Options::BANK_BIC => 'COBADEFFXXX' ) );
		$tab = new SettingsTab( new JobStore() );

		$this->assertSame( 'MARKDEF1100', $tab->sanitize_bic( 'markdef1100' ) );
		$this->assertSame( 'DEUTDEFF', $tab->sanitize_bic( 'DEUT DEFF' ) );
		WP_Mock::expectAction( 'linker_test_settings_error', 'The BIC is not valid (8 or 11 characters); the previous BIC is kept.' );
		$this->assertSame( 'COBADEFFXXX', $tab->sanitize_bic( 'COBA' ) );
		$this->assertConditionsMet();
	}

	/**
	 * Only addresses are kept in the blind copy list; the rest is reported.
	 */
	public function test_sanitize_bcc(): void {
		WP_Mock::userFunction( 'is_email', array( 'return' => static fn ( string $email ): bool => false !== filter_var( $email, FILTER_VALIDATE_EMAIL ) ) );
		WP_Mock::passthruFunction( 'sanitize_email' );
		WP_Mock::expectAction( 'linker_test_settings_error', 'Not an email address, left out: nope' );

		$this->assertSame( "a@example.test\nb@example.test", ( new SettingsTab( new JobStore() ) )->sanitize_bcc( "a@example.test, b@example.test\nnope\na@example.test" ) );
		$this->assertConditionsMet();
	}

	/**
	 * The number prefix keeps letters, digits and hyphens, upper case.
	 */
	public function test_sanitize_prefix(): void {
		$this->assertSame( 'P-I', ( new SettingsTab( new JobStore() ) )->sanitize_prefix( 'p-i !' ) );
	}

	/**
	 * Saving an internal sender must preserve the site's existing DLK-PF prefix.
	 */
	public function test_saving_settings_preserves_the_default_prefix(): void {
		$this->assertSame( 'DLK-PF', ( new SettingsTab( new JobStore() ) )->sanitize_prefix( 'DLK-PF' ) );
	}

	/**
	 * Leading or trailing hyphens cannot create a doubled separator in the number.
	 *
	 * @testWith ["--dlk-pf--", "DLK-PF"]
	 *           [" -p-i !- ", "P-I"]
	 *           ["---", ""]
	 *           [["DLK"], ""]
	 *
	 * @param mixed  $value    Submitted prefix.
	 * @param string $expected Stored prefix.
	 */
	public function test_prefix_trims_edge_hyphens( $value, string $expected ): void {
		$this->assertSame( $expected, ( new SettingsTab( new JobStore() ) )->sanitize_prefix( $value ) );
	}

	/**
	 * Above the fields stands the number of emails no retry could deliver (review 2026-10-10, S3).
	 */
	public function test_shows_the_undelivered_count(): void {
		$this->plain_text();
		$counts        = new \stdClass();
		$counts->draft = 2;
		WP_Mock::userFunction( 'wp_count_posts', array( 'return' => $counts ) );
		$tab = new SettingsTab( new JobStore() );
		WP_Mock::expectAction( 'linker_test_settings_output', $tab->fields() );

		ob_start();
		$tab->output();
		$printed = (string) ob_get_clean();

		$this->assertStringContainsString( '2 emails could not be delivered', $printed );
	}
}
