<?php
/**
 * Tests for the contact person card.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Account;

use Linker\Commerce\Account\ContactCard;
use Linker\Commerce\Settings\Options;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for ContactCard.
 *
 * @covers \Linker\Commerce\Account\ContactCard
 */
final class ContactCardTest extends TestCase {

	/**
	 * Translation, escaping and email sanitizing return their input.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		WP_Mock::userFunction( 'sanitize_email', array( 'return' => static fn ( string $email ): string => $email ) );
	}

	/**
	 * Name, email and phone of the settings; the phone link has digits only.
	 */
	public function test_contact_person(): void {
		$this->options(
			array(
				Options::CONTACT_NAME  => 'Anna Muster',
				Options::CONTACT_EMAIL => 'anna@de-linker.com',
				Options::CONTACT_PHONE => '+49 39203 123-45',
			)
		);

		ob_start();
		( new ContactCard( new Options() ) )->render();

		$this->assertSame( '<section class="linker-contact-card" aria-labelledby="linker-contact-card-title"><h2 id="linker-contact-card-title">Your contact person</h2><p><strong>Anna Muster</strong><br><a href="mailto:anna@de-linker.com">anna@de-linker.com</a><br><a href="tel:+493920312345">+49 39203 123-45</a></p></section>', ob_get_clean() );
	}

	/**
	 * Without settings the card names the team mailbox.
	 */
	public function test_team_mailbox(): void {
		$this->options( array() );

		ob_start();
		( new ContactCard( new Options() ) )->render();

		$this->assertStringContainsString( '<p><a href="mailto:sales@de-linker.com">sales@de-linker.com</a></p>', (string) ob_get_clean() );
	}
}
