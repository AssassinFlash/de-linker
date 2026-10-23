<?php
/**
 * Tests for the registration confirmation.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Registration;

use Linker\Commerce\Registration\Emails\RegistrationReceivedEmail;
use Linker\Commerce\Registration\Fields;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;
use WP_User;

/**
 * The confirmation goes to the address the customer registered with, and only
 * then. An unknown user sends nothing.
 *
 * @covers \Linker\Commerce\Registration\Emails\RegistrationReceivedEmail
 */
final class RegistrationReceivedEmailTest extends TestCase {

	/**
	 * Preserve the unit runner's native database seam.
	 *
	 * @var mixed
	 */
	private mixed $previous_database = null;

	/** Restore only the test-owned readback seam. */
	public function tearDown(): void {
		$GLOBALS['wpdb'] = $this->previous_database; // phpcs:ignore WordPress.WP.GlobalVariablesOverride.Prohibited -- Unit-only native readback fixture.
		parent::tearDown();
	}

	/**
	 * Translation, escaping and the language switch of one email.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->previous_database = $GLOBALS['wpdb'] ?? null;
		$GLOBALS['wpdb']         = new class() extends \wpdb { // phpcs:ignore WordPress.WP.GlobalVariablesOverride.Prohibited -- Unit-only native metadata readback.
			/**
			 * Native metadata readback succeeded in this legacy-user fixture.
			 *
			 * @var string
			 */
			public $last_error = '';
			/** The unit double opens no connection. */
			public function __construct() {}
		};
		$this->plain_text();
		$this->reload_plugin_textdomain();
		WP_Mock::userFunction( 'plugin_dir_path', array( 'return' => '/plugin/' ) );
		// Legacy/unmanaged native users do not have a registration handoff source.
		WP_Mock::userFunction( 'wp_cache_delete', array( 'return' => true ) );
		WP_Mock::userFunction(
			'metadata_exists',
			array(
				'args'   => array( 'user', WP_Mock\Functions::type( 'int' ), \Linker\Commerce\Registration\RegistrationNotices::META ),
				'return' => false,
			)
		);
		WP_Mock::userFunction( 'get_user_meta', array( 'return' => '' ) );
	}

	/**
	 * A registration queues the confirmation to the registered address, in that customer's language.
	 */
	public function test_a_registration_queues_the_confirmation(): void {
		$this->expect_action_on_any( Fields::REGISTERED_ACTION . '_notification', RegistrationReceivedEmail::class, 'trigger' );
		$email = new RegistrationReceivedEmail( '/plugin/linker-commerce.php' );
		$this->assertSame( 'linker_registration_received', $email->id );
		$this->assertTrue( $email->is_customer_email() );
		$this->assertSame( 'We received your partner registration', $email->get_default_subject() );
		$this->assertSame( 'Registration received', $email->get_default_heading() );

		WP_Mock::userFunction(
			'get_userdata',
			array(
				'return' => static function ( int $id ): ?WP_User {
					if ( 5 !== $id ) {
						return null;
					}
					$user             = new WP_User();
					$user->ID         = 5;
					$user->user_email = 'maria@example.test';
					return $user;
				},
			)
		);
		WP_Mock::userFunction( 'get_user_locale', array( 'return' => 'de_DE_formal' ) );
		$this->allow_locale_switch( 'de_DE_formal' );
		WP_Mock::expectAction( 'linker_test_email_sent', 'linker_registration_received', 'maria@example.test' );

		$email->trigger( 5 );
		$this->assertSame( 'maria@example.test', $email->get_recipient() );
	}

	/**
	 * An unknown user sends nothing.
	 */
	public function test_an_unknown_user_sends_nothing(): void {
		$this->expect_action_on_any( Fields::REGISTERED_ACTION . '_notification', RegistrationReceivedEmail::class, 'trigger' );
			WP_Mock::userFunction( 'get_userdata', array( 'return' => null ) );
			$email = new RegistrationReceivedEmail( '/plugin/linker-commerce.php' );
			$email->trigger( 99 );
			$this->assertSame( '', $email->get_recipient() );
	}
}
