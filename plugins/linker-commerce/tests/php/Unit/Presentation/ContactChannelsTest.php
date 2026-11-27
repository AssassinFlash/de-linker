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
			array(
				'https://www.youtube.com/@linkerenergystorage',
				'https://www.facebook.com/profile.php?id=61596580037537',
				'https://www.europages.de/de/firma/linker-technology-gmbh-22436516',
				'https://www.wlw.de/de/firma/linker-technology-gmbh-22436518',
				'https://www.provenexpert.com/de-de/linker-technology-gmbh/',
				'https://www.marktplatz-mittelstand.de/barleben/linker-technology-gmbh-aYGE9H.html',
				'https://de.trustpilot.com/review/de-linker.com',
				'https://www.northdata.de/Linker%20Technology%20GmbH,%20Barleben/Amtsgericht%20Stendal%20HRB%2033824',
				'https://www.11880.com/branchenbuch/barleben/250424085B114309018/linker-technology-gmbh.html',
			),
			ContactChannels::company_same_as()
		);
		$html = ContactChannels::social_links( 'company', 'footer-socials' );
		$this->assertStringContainsString( 'class="footer-socials"', $html );
		$this->assertSame( 2, substr_count( $html, 'target="_blank" rel="noopener noreferrer"' ) );
		$this->assertSame( 2, substr_count( $html, 'aria-label="Linker Energy Storage on ' ) );
		foreach ( array_slice( ContactChannels::company_same_as(), 0, 2 ) as $url ) {
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
