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

		$this->assertSame( '<section class="linker-account-panel linker-account-contact" aria-labelledby="linker-contact-card-title"><header class="linker-account-panel-heading"><h2 id="linker-contact-card-title">Your contact person</h2></header><div class="linker-account-panel-body"><p class="linker-account-contact-line"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg><span><strong>Anna Muster</strong><br><a href="mailto:anna@de-linker.com">anna@de-linker.com</a><br><a href="tel:+493920312345">+49 39203 123-45</a></span></p></div></section>', ob_get_clean() );
	}

	/**
	 * Without settings the card names the team mailbox.
	 */
	public function test_team_mailbox(): void {
		$this->options( array() );

		ob_start();
		( new ContactCard( new Options() ) )->render();

		$this->assertStringContainsString( '<p class="linker-account-contact-line"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg><span><a href="mailto:sales@de-linker.com">sales@de-linker.com</a></span></p>', (string) ob_get_clean() );
	}
}
