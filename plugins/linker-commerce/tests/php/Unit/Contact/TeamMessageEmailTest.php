<?php
/**
 * Tests for the contact form's internal sender.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Contact;

use Linker\Commerce\Contact\Emails\TeamMessageEmail;
use Linker\Commerce\Settings\Options;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * The contact form's team letter follows the internal sender setting.
 *
 * @covers \Linker\Commerce\Contact\Emails\TeamMessageEmail
 */
final class TeamMessageEmailTest extends TestCase {

	/**
	 * Contact notifications use the configured internal sender (#286).
	 *
	 * @testWith ["", "sales@sunriverinverter.com"]
	 *           ["alerts@example.test", "alerts@example.test"]
	 *
	 * @param string $saved    Saved sender.
	 * @param string $expected Effective sender.
	 */
	public function test_internal_sender( string $saved, string $expected ): void {
		$this->plain_text();
		$this->options( array( Options::NOTIFY_FROM => $saved ) );
		WP_Mock::userFunction( 'plugin_dir_path', array( 'return' => '/plugin/' ) );
		WP_Mock::userFunction( 'sanitize_email', array( 'return' => static fn ( string $email ): string => $email ) );
		WP_Mock::userFunction( 'is_email', array( 'return' => static fn ( string $email ): bool => false !== filter_var( $email, FILTER_VALIDATE_EMAIL ) ) );
		$email = new TeamMessageEmail( '/plugin/linker-commerce.php', new Options() );
		$this->assertSame( 'Linker', $email->get_from_name() );
		$this->assertSame( $expected, $email->get_from_address() );
	}
}
