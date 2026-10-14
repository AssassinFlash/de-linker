<?php
/**
 * Tests for the contact form's handler.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Contact;

use Linker\Commerce\Contact\Form;
use Linker\Commerce\Contact\Handler;
use Linker\Commerce\Settings\Options;
use Linker\Commerce\Tests\Fixtures;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for Handler::process(): the decisions of a public form — a wrong
 * nonce, a bot, a flood, an incomplete form, a delivered message (ticket #68).
 *
 * @covers \Linker\Commerce\Contact\Handler
 */
final class HandlerTest extends TestCase {


	/**
	 * The three hooks and the WordPress reads the handler makes.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		$this->reload_plugin_textdomain();
		WP_Mock::userFunction( 'get_option', array( 'return' => false ) );
		WP_Mock::userFunction( 'pll_current_language', array( 'return' => false ) );
		WP_Mock::userFunction( 'determine_locale', array( 'return' => 'en_US' ) );
		// Both emails switch to the site's language and back (LocaleSwitch);
		// the refusals never get that far.
		WP_Mock::userFunction(
			'switch_to_locale',
			array(
				'times'  => '0+',
				'return' => true,
			)
		);
		WP_Mock::userFunction(
			'restore_previous_locale',
			array(
				'times'  => '0+',
				'return' => '',
			)
		);
		WP_Mock::userFunction(
			'remove_filter',
			array(
				'times'  => '0+',
				'return' => true,
			)
		);
		WP_Mock::userFunction( 'unload_textdomain', array( 'return' => true ) );
		WP_Mock::userFunction( 'load_textdomain', array( 'return' => true ) );
		WP_Mock::userFunction( 'WC', array( 'return' => new Fixtures\WooCommerce() ) );
		WP_Mock::userFunction( 'get_bloginfo', array( 'return' => 'UTF-8' ) );
		WP_Mock::userFunction( 'apply_filters', array( 'return' => '' ) );
		WP_Mock::userFunction( 'plugin_dir_path', array( 'return' => '/plugin/' ) );
		WP_Mock::userFunction( 'sanitize_text_field', array( 'return' => static fn ( string $value ): string => trim( $value ) ) );
		WP_Mock::userFunction( 'sanitize_email', array( 'return' => static fn ( string $email ): string => trim( $email ) ) );
		WP_Mock::userFunction( 'sanitize_textarea_field', array( 'return' => static fn ( string $value ): string => trim( $value ) ) );
		WP_Mock::userFunction( 'sanitize_key', array( 'return' => static fn ( string $key ): string => strtolower( preg_replace( '/[^a-z0-9_-]/i', '', $key ) ?? '' ) ) );
		WP_Mock::userFunction( 'is_email', array( 'return' => static fn ( string $email ): bool => false !== filter_var( $email, FILTER_VALIDATE_EMAIL ) ) );
	}

	/**
	 * A form without a valid nonce is refused before anything else.
	 */
	public function test_wrong_nonce_is_refused(): void {
		$handler = $this->handler();
		WP_Mock::userFunction( 'wp_verify_nonce', array( 'return' => false ) );

		$this->assertSame( 'invalid', $handler->process( $this->post() ) );
	}

	/**
	 * A filled honeypot reads as a delivery and sends nothing.
	 */
	public function test_honeypot_is_answered_but_sends_nothing(): void {
		$handler = $this->handler();
		WP_Mock::userFunction( 'wp_verify_nonce', array( 'return' => 1 ) );

		$this->assertSame( 'sent', $handler->process( $this->post( array( Form::TRAP_FIELD => 'http://spam.example' ) ) ) );
	}

	/**
	 * More messages than the limit from one connection: refused.
	 */
	public function test_flood_is_throttled(): void {
		$handler = $this->handler();
		WP_Mock::userFunction( 'wp_verify_nonce', array( 'return' => 1 ) );
		WP_Mock::userFunction( 'get_transient', array( 'return' => array( time(), time(), time() ) ) );

		$this->assertSame( 'throttled', $handler->process( $this->post() ) );
	}

	/**
	 * An incomplete form is refused.
	 */
	public function test_incomplete_form_is_refused(): void {
		$handler = $this->handler();
		WP_Mock::userFunction( 'wp_verify_nonce', array( 'return' => 1 ) );
		WP_Mock::userFunction( 'get_transient', array( 'return' => false ) );

		$this->assertSame( 'invalid', $handler->process( $this->post( array( 'email' => 'not-an-address' ) ) ) );
	}

	/**
	 * A complete form sends the receipt to the visitor and the letter to the
	 * team mailbox, counts the attempt and reads as delivered.
	 */
	public function test_complete_form_sends_both_emails(): void {
		$handler = $this->handler();
		WP_Mock::userFunction( 'wp_verify_nonce', array( 'return' => 1 ) );
		WP_Mock::userFunction( 'get_transient', array( 'return' => false ) );
		WP_Mock::userFunction(
			'set_transient',
			array(
				'times'  => 1,
				'return' => true,
			)
		);

		WP_Mock::expectFilterAdded( 'plugin_locale', array( new \WP_Mock\Matcher\AnyInstance( \Linker\Commerce\Mail\LocaleSwitch::class ), 'plugin_locale' ) ); // @phpstan-ignore argument.type
		WP_Mock::expectAction( 'linker_test_email_sent', 'linker_contact_receipt', 'maria@example.test' );
		WP_Mock::expectAction( 'linker_test_email_sent', 'linker_contact_message', 'sales@de-linker.com' );

		$this->assertSame( 'sent', $handler->process( $this->post() ) );
		$this->assertConditionsMet();
	}

	/**
	 * A complete form as posted by the browser.
	 *
	 * @param  array<string, string> $overrides Fields to change.
	 * @return array<string, string>
	 */
	private function post( array $overrides = array() ): array {
		return array_merge(
			array(
				Form::NONCE_FIELD => 'nonce',
				'name'            => 'Maria Weber',
				'email'           => 'maria@example.test',
				'company'         => '',
				'message'         => 'Do you ship the GW5.1 battery?',
				'consent'         => '1',
			),
			$overrides
		);
	}

	/**
	 * The handler under test.
	 */
	private function handler(): Handler {
		return new Handler( '/plugin/linker-commerce.php', new Options() );
	}
}
