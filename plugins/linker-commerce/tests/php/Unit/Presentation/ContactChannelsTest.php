<?php
/**
 * Public social identities in profile and contact links.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Presentation;

use Linker\Commerce\Presentation\ContactChannels;
use Linker\Commerce\Tests\TestCase;

/**
 * Keep official company profiles and Chester's professional links distinct.
 *
 * @covers \Linker\Commerce\Presentation\ContactChannels
 */
final class ContactChannelsTest extends TestCase {
	/** Render the original text and URLs in unit markup. */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
	}

	/** Only the company's verified profiles are official channels. */
	public function test_company_channels_match_the_organization(): void {
		$this->assertSame(
			array( 'https://www.youtube.com/@linkerenergystorage', 'https://www.facebook.com/profile.php?id=61596580037537' ),
			ContactChannels::company_same_as()
		);
		$html = ContactChannels::social_links( 'company', 'footer-socials' );
		$this->assertStringContainsString( 'class="footer-socials"', $html );
		$this->assertSame( 2, substr_count( $html, 'target="_blank" rel="noopener noreferrer"' ) );
		$this->assertSame( 2, substr_count( $html, 'aria-label="Linker Energy Storage on ' ) );
		foreach ( ContactChannels::company_same_as() as $url ) {
			$this->assertStringContainsString( $url, $html );
		}
		$this->assertStringNotContainsString( 'LinkedIn', $html );
		$this->assertStringNotContainsString( 'sales@', $html );
	}

	/** Chester's card shows the technical channels and his Person has the wider profile set. */
	public function test_chester_channels_are_separate_from_the_company(): void {
		$profiles = ContactChannels::chester_same_as();
		$this->assertSame(
			array(
				'https://www.linkedin.com/in/chester-john-linker/',
				'https://www.youtube.com/@chesterjohn.linker',
				'https://x.com/chester_linker',
				'https://www.facebook.com/chesterjohn.linker/',
				'https://www.instagram.com/chesterjohn.linker/',
				'https://www.tiktok.com/@chesterjohn.linker',
				'https://www.reddit.com/user/Beginning-Ship8918/',
			),
			$profiles
		);
		$html = ContactChannels::social_links( 'chester' );
		$this->assertSame( 3, substr_count( $html, 'aria-label="Chester John on ' ) );
		$this->assertSame( 3, substr_count( $html, 'aria-hidden="true" focusable="false"' ) );
		foreach ( array_slice( $profiles, 0, 3 ) as $url ) {
			$this->assertStringContainsString( $url, $html );
		}
		$this->assertStringNotContainsString( 'facebook.com', $html );
	}
}
