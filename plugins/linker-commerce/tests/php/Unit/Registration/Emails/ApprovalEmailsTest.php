<?php
/**
 * Tests for the three approval emails and their base.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Registration;

use Linker\Commerce\Registration\Approval;
use Linker\Commerce\Registration\Emails\ApprovedEmail;
use Linker\Commerce\Registration\Emails\CustomerApprovalEmail;
use Linker\Commerce\Registration\Emails\RejectedEmail;
use Linker\Commerce\Registration\Emails\RestrictedEmail;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;
use WP_User;

/**
 * Tests for the three customer emails about the approval state. Each speaks
 * only when the state changes to its own, in the customer's own language, and
 * carries the team's reason.
 *
 * @covers \Linker\Commerce\Registration\Emails\CustomerApprovalEmail
 * @covers \Linker\Commerce\Registration\Emails\ApprovedEmail
 * @covers \Linker\Commerce\Registration\Emails\RestrictedEmail
 * @covers \Linker\Commerce\Registration\Emails\RejectedEmail
 */
final class ApprovalEmailsTest extends TestCase {

	/**
	 * Translation, escaping, the user and the language switch of one email.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		$this->reload_plugin_textdomain();
		WP_Mock::userFunction( 'plugin_dir_path', array( 'return' => '/plugin/' ) );
		WP_Mock::userFunction(
			'get_userdata',
			array(
				'return' => static function ( int $id ): ?WP_User {
					if ( 5 !== $id ) {
						return null;
					}
					$user               = new WP_User();
					$user->ID           = 5;
					$user->user_email   = 'maria@example.test';
					$user->display_name = 'Maria';
					return $user;
				},
			)
		);
		WP_Mock::userFunction( 'get_user_locale', array( 'return' => static fn ( int $user_id ): string => 5 === $user_id ? 'de_DE_formal' : 'en_US' ) );
	}

	/**
	 * Each email listens on the change action and sends only for its own
	 * state, to the customer's address, in the customer's language.
	 */
	public function test_each_email_speaks_for_its_own_state(): void {
		$this->expect_action_on_any( Approval::CHANGED_ACTION . '_notification', ApprovedEmail::class, 'trigger', 10, 4 );
		$email = new ApprovedEmail( '/plugin/linker-commerce.php' );
		$this->assertSame( 'linker_approval_approved', $email->id );
		$this->assertTrue( $email->is_customer_email() );
		$this->assertSame( 'Your partner account is approved', $email->get_default_subject() );

		// A change to another state stays silent; nothing observes an email here.
		$email->trigger( 5, Approval::PENDING, Approval::RESTRICTED, '' );

		$this->allow_locale_switch( 'de_DE_formal' );
		WP_Mock::expectAction( 'linker_test_email_sent', 'linker_approval_approved', 'maria@example.test' );
		$email->trigger( 5, Approval::PENDING, Approval::APPROVED, '' );
		$this->assertSame( 'maria@example.test', $email->get_recipient() );
	}

	/**
	 * The restriction email carries the team's reason to the template.
	 */
	public function test_the_restriction_email_carries_the_reason(): void {
		$this->expect_action_on_any( Approval::CHANGED_ACTION . '_notification', RestrictedEmail::class, 'trigger', 10, 4 );
		$email = new RestrictedEmail( '/plugin/linker-commerce.php' );
		$this->assertSame( 'linker_approval_restricted', $email->id );
		$this->assertSame( 'Your partner account access is limited', $email->get_default_subject() );

		$this->allow_locale_switch( 'de_DE_formal' );
		WP_Mock::expectAction( 'linker_test_email_sent', 'linker_approval_restricted', 'maria@example.test' );
		$email->trigger( 5, Approval::APPROVED, Approval::RESTRICTED, 'Nettopreise gibt es für Unternehmen.' );
		$this->assertSame( 'Nettopreise gibt es für Unternehmen.', $this->template_args_of( $email )['reason'] );
	}

	/**
	 * The rejection email speaks for the rejected state; an unknown user sends
	 * nothing.
	 */
	public function test_the_rejection_email_and_an_unknown_user(): void {
		$this->expect_action_on_any( Approval::CHANGED_ACTION . '_notification', RejectedEmail::class, 'trigger', 10, 4 );
		$email = new RejectedEmail( '/plugin/linker-commerce.php' );
		$this->assertSame( 'linker_approval_rejected', $email->id );
		$this->assertSame( 'Your partner account was not approved', $email->get_default_subject() );
		$this->assertSame( 'html', $email->get_email_type() );

		$email->trigger( 99, Approval::PENDING, Approval::REJECTED, 'No answer.' );
		// Strict WP_Mock fails on any function the send would have called, so a
		// passing run means nothing went out for the unknown user.

		$this->allow_locale_switch( 'de_DE_formal' );
		WP_Mock::expectAction( 'linker_test_email_sent', 'linker_approval_rejected', 'maria@example.test' );
		$email->trigger( 5, Approval::PENDING, Approval::REJECTED, 'No answer.' );
	}

	/**
	 * The template arguments of an email.
	 *
	 * @param CustomerApprovalEmail $email The email.
	 * @return array<string, mixed>
	 */
	private function template_args_of( CustomerApprovalEmail $email ): array {
		$method = new \ReflectionMethod( $email, 'template_args' );
		return (array) $method->invoke( $email );
	}
}
