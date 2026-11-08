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
