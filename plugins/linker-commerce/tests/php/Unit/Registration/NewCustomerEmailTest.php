<?php
/**
 * Tests for the new-customer notification.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Registration;

use Linker\Commerce\Registration\Emails\NewCustomerEmail;
use Linker\Commerce\Registration\Fields;
use Linker\Commerce\Registration\RegistrationInformation;
use Linker\Commerce\Registration\VatProfile;
use Linker\Commerce\Registration\ViesClient;
use Linker\Commerce\Settings\Options;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;
use WP_User;

/**
 * Tests for NewCustomerEmail and, through it, the TeamEmail base.
 *
 * @covers \Linker\Commerce\Registration\Emails\NewCustomerEmail
 * @covers \Linker\Commerce\Mail\TeamEmail
 */
final class NewCustomerEmailTest extends TestCase {

	/**
	 * Settings: team mailbox and two blind copies; the customer is Maria Beispiel of Solarbau GmbH.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		$this->reload_plugin_textdomain();
		WP_Mock::userFunction( 'plugin_dir_path', array( 'return' => '/plugin/' ) );
		WP_Mock::userFunction( 'sanitize_email', array( 'return' => static fn ( string $email ): string => $email ) );
		WP_Mock::userFunction( 'is_email', array( 'return' => static fn ( string $email ): bool => false !== filter_var( $email, FILTER_VALIDATE_EMAIL ) ) );
		$this->options(
			array(
				Options::TEAM_TO     => 'sales@de-linker.com',
				Options::NOTIFY_FROM => 'alerts@example.test',
				Options::NOTIFY_BCC  => "one@example.test\ntwo@example.test",
				'WPLANG'             => '',
			)
		);
		WP_Mock::userFunction(
			'get_user_meta',
			array(
				'return' => static fn ( int $id, string $key ) => array(
					'billing_company'    => 'Solarbau GmbH',
					'billing_first_name' => 'Maria',
					'billing_last_name'  => 'Beispiel',
				)[ $key ] ?? '',
			)
		);
	}

	/**
	 * A customer.
	 */
	private static function customer(): WP_User {
		$user               = new WP_User();
		$user->ID           = 5;
		$user->user_email   = 'maria@example.test';
		$user->display_name = 'maria';
		return $user;
	}

	/**
	 * The email with the same field reader the accounts page uses.
	 */
	private static function email(): NewCustomerEmail {
		return new NewCustomerEmail( '/plugin/linker-commerce.php', new Options(), new RegistrationInformation( new Fields( new VatProfile( new ViesClient() ) ) ) );
	}

	/**
	 * The email listens for registrations and goes to the team mailbox in the site's language,
	 * with the blind copies and a reply address of the customer.
	 */
	public function test_notifies_the_team(): void {
		$this->expect_action_on_any( Fields::REGISTERED_ACTION . '_notification', NewCustomerEmail::class, 'trigger' );
		$email = self::email();
		$this->assertSame( 'linker_new_customer', $email->id );
		$this->assertSame( '/plugin/templates/', $email->template_base );
		$this->assertFalse( $email->is_customer_email() );
		$this->assertSame( 'Linker', $email->get_from_name() );
		$this->assertSame( 'alerts@example.test', $email->get_from_address() );

		WP_Mock::userFunction(
			'get_userdata',
			array(
				'args'   => array( 5 ),
				'return' => self::customer(),
			)
		);
		$this->allow_locale_switch( 'en_US' );
		WP_Mock::expectAction( 'linker_test_email_sent', 'linker_new_customer', 'sales@sunriverinverter.com' );

		$email->trigger( 5 );

		$this->assertSame( 'Solarbau GmbH', $email->placeholders['{company}'] );
		$header = "Content-Type: text/html\r\nX-Linker-Internal: yes\r\nReply-to: Maria Beispiel <maria@example.test>\r\nBcc: one@example.test, two@example.test\r\n";
		$this->filter_returns( 'woocommerce_email_headers', $header, array( $header, 'linker_new_customer', $email->object, $email ) );
		$this->assertSame( $header, $email->get_headers() );
		$this->assertConditionsMet();
	}

	/**
	 * Without a user nothing is sent; the email is HTML only.
	 */
	public function test_unknown_user_and_format(): void {
		$this->expect_action_on_any( Fields::REGISTERED_ACTION . '_notification', NewCustomerEmail::class, 'trigger' );
		WP_Mock::userFunction( 'get_userdata', array( 'return' => false ) );
		$email = self::email();

		$email->trigger( 99 );

		$this->assertSame( 'html', $email->get_email_type() );
		$this->assertSame( array( 'html' => 'HTML' ), $email->get_email_type_options() );
		$this->assertSame( 'New customer: {company}', $email->get_default_subject() );
	}
}
