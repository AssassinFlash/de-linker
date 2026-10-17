<?php
/**
 * Tests for the digest email.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Digest;

use Linker\Commerce\Digest\DigestEmail;
use Linker\Commerce\Settings\Options;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for DigestEmail: the subject and heading, the date placeholder, and
 * the team mailbox as recipient with the blind copies.
 *
 * @covers \Linker\Commerce\Digest\DigestEmail
 * @covers \Linker\Commerce\Mail\TeamEmail
 */
final class DigestEmailTest extends TestCase {

	/**
	 * The digest goes to the team mailbox in the site's language, dated, with
	 * the blind copies; no reply-to (there is no customer to reply to).
	 */
	public function test_sends_dated_to_the_team_mailbox(): void {
		$this->plain_text();
		$this->reload_plugin_textdomain();
		WP_Mock::userFunction( 'plugin_dir_path', array( 'return' => '/plugin/' ) );
		WP_Mock::userFunction( 'sanitize_email', array( 'return' => static fn ( string $email ): string => $email ) );
		WP_Mock::userFunction( 'is_email', array( 'return' => static fn ( string $email ): bool => false !== filter_var( $email, FILTER_VALIDATE_EMAIL ) ) );
		$this->options(
			array(
				Options::TEAM_TO    => 'sales@de-linker.com',
				Options::NOTIFY_BCC => "one@example.test\ntwo@example.test",
				'WPLANG'            => '',
				'date_format'       => 'F j, Y',
			)
		);
		WP_Mock::userFunction(
			'wp_date',
			array(
				'return' => static fn ( string $format ): string => 'H:i' === $format ? '09:00' : 'October 11, 2026',
			)
		);
		$this->allow_locale_switch( 'en_US' );
		WP_Mock::expectAction( 'linker_test_email_sent', 'linker_digest', 'sales@sunriverinverter.com' );

		$email = new DigestEmail( '/plugin/linker-commerce.php', new Options() );
		$email->send_report( array() );

		$this->assertSame( 'linker_digest', $email->id );
		$this->assertSame( '/plugin/templates/', $email->template_base );
		$this->assertFalse( $email->is_customer_email() );
		$this->assertSame( 'October 11, 2026', $email->placeholders['{date}'] );
		$header = "Content-Type: text/html\r\nX-Linker-Internal: yes\r\nBcc: one@example.test, two@example.test\r\n";
		$this->filter_returns( 'woocommerce_email_headers', $header, array( $header, 'linker_digest', false, $email ) );
		$this->assertSame( $header, $email->get_headers() );
		$this->assertConditionsMet();
	}

	/**
	 * Subject and heading defaults; the subject carries the date placeholder.
	 */
	public function test_subject_and_heading(): void {
		$this->plain_text();
		$this->reload_plugin_textdomain();
		WP_Mock::userFunction( 'plugin_dir_path', array( 'return' => '/plugin/' ) );
		$this->options(
			array(
				Options::TEAM_TO => 'sales@de-linker.com',
				'WPLANG'         => '',
			)
		);

		$email = new DigestEmail( '/plugin/linker-commerce.php', new Options() );

		$this->assertSame( 'Daily digest, {date}', $email->get_default_subject() );
		$this->assertSame( 'Daily digest', $email->get_default_heading() );
		$this->assertSame( 'html', $email->get_email_type() );
		$this->assertSame( array( 'html' => 'HTML' ), $email->get_email_type_options() );
	}
}
